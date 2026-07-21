"""David-OS watcher control plane.

Purpose: observe configured roots, normalize file events, heartbeat as a watcher
node, and ask the File Intelligence Hub for worker help when watcher inspection is
not enough.
Date: 2026-07-08
Author: codex
Status: TESTED with `python watchers/control_plane.py --status` and
`pytest watchers/tests/ -x`.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from file_intelligence_hub.watchers.event_normalizer import normalize_file_event

VALID_EVENTS = {"created", "modified", "moved", "deleted"}
DANGER_MARKERS = {".git", "package.json", ".env", ".key", "id_rsa", "id_dsa", "credentials", "secrets"}
UNKNOWN_EXTENSIONS = {"", ".bin", ".dat", ".tmp", ".unknown"}
FORBIDDEN_ROOTS = [Path("D:/DONT TOUCH BOOT UP"), Path("D:\\DONT TOUCH BOOT UP")]
READ_ONLY_ROOTS = [Path("D:/GitHub/_ARCHIVE_FIS_20260707"), Path("D:\\GitHub\\_ARCHIVE_FIS_20260707")]
DEFAULT_CONFIG = Path(__file__).with_name("watch_config.json")
DEFAULT_QUEUE = Path(__file__).with_name("runtime") / "control_plane_queue.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class FileSignature:
    size_bytes: int
    mtime_ns: int
    is_directory: bool


class HubClient:
    def __init__(self, base_url: str, token: str | None = None, timeout: float = 5.0, *, dry_run: bool = False, offline: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.dry_run = dry_run
        self.offline = offline

    def request(self, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.offline:
            raise ConnectionError("hub client is offline")
        if self.dry_run:
            print(json.dumps({"method": method, "url": f"{self.base_url}{endpoint}", "payload": payload}, sort_keys=True))
            return {"dry_run": True}
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-API-Token"] = self.token
        req = Request(f"{self.base_url}{endpoint}", data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as response:  # noqa: S310 - configured local/LAN API
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(str(exc)) from exc

    def get(self, endpoint: str) -> dict[str, Any]:
        return self.request("GET", endpoint)

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", endpoint, payload)


class JsonlQueue:
    def __init__(self, path: Path = DEFAULT_QUEUE) -> None:
        self.path = path

    def append(self, item: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, sort_keys=True) + "\n")

    def depth(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def is_forbidden(path: Path) -> bool:
    return any(is_relative_to(path, root) for root in FORBIDDEN_ROOTS)


def is_read_only_archive(path: Path) -> bool:
    return any(is_relative_to(path, root) for root in READ_ONLY_ROOTS)


def iter_watch_roots(config: dict[str, Any]) -> list[Path]:
    roots = [Path(str(root["path"])).expanduser() for root in config.get("roots", []) if root.get("enabled", True)]
    safe: list[Path] = []
    for root in roots:
        if is_forbidden(root):
            continue
        safe.append(root)
    return safe


def ignored(path: Path, config: dict[str, Any]) -> bool:
    if is_forbidden(path):
        return True
    patterns = list(config.get("ignore_globs", []))
    if is_read_only_archive(path):
        # Read-only means the control plane may observe but must not write local state there.
        return False
    text = str(path).replace("\\", "/")
    return any(fnmatch.fnmatch(path.name, pat) or fnmatch.fnmatch(text, pat) for pat in patterns)


def cheap_labels(path: Path, is_directory: bool) -> list[str]:
    if is_directory:
        return ["folder"]
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".pdf", ".doc", ".docx"}:
        return ["document"]
    if ext in {".jpg", ".jpeg", ".png", ".gif"}:
        return ["image"]
    if ext in {".py", ".js", ".ts", ".json", ".toml", ".yaml", ".yml"}:
        return ["code_or_config"]
    return ["unknown"]


def danger_markers(path: Path) -> list[str]:
    lowered = [part.lower() for part in path.parts] + [path.name.lower(), path.suffix.lower()]
    return sorted(marker for marker in DANGER_MARKERS if marker in lowered or marker in path.name.lower())


def build_event(event_type: str, path: Path, *, source_node_id: str, old_path: Path | None = None, is_directory: bool | None = None) -> dict[str, Any]:
    is_dir = path.is_dir() if is_directory is None and path.exists() else bool(is_directory)
    raw = {"event_type": event_type, "path": str(path), "is_directory": is_dir}
    if old_path:
        raw["dest_path"] = str(path)
        raw["path"] = str(old_path)
    normalized = normalize_file_event(raw, source="watcher_control_plane")
    current_path = path
    try:
        size = 0 if event_type == "deleted" or is_dir else current_path.stat().st_size
    except OSError:
        size = 0
    normalized.update({
        "source_node_id": source_node_id,
        "old_path": str(old_path) if old_path else None,
        "extension": current_path.suffix.lower(),
        "size_bytes": size,
        "parent_path": str(current_path.parent),
        "observed_at": utc_now(),
        "cheap_labels": cheap_labels(current_path, is_dir),
        "danger_markers": danger_markers(current_path),
    })
    return normalized


class WatcherControlPlane:
    def __init__(self, config: dict[str, Any], client: HubClient, queue: JsonlQueue | None = None) -> None:
        self.config = config
        self.client = client
        self.queue = queue or JsonlQueue(Path(str(config.get("queue_file", DEFAULT_QUEUE))))
        self.source_node_id = str(config.get("source_node_id") or socket.gethostname())
        self.roots = iter_watch_roots(config)
        self.snapshot: dict[str, FileSignature] = {}
        self.event_times: list[float] = []
        self.last_reconciliation: str | None = None
        self.stop_event = Event()

    def heartbeat(self) -> None:
        payload = {
            "node_id": self.source_node_id,
            "hostname": socket.gethostname(),
            "role": "watcher",
            "capabilities": ["watch_files"],
            "status": "isolated_but_running",
            "hub_url": self.client.base_url,
            "leader_status": "helper",
            "resources": {"watched_roots": [str(root) for root in self.roots]},
            "local_queue_depth": self.queue.depth(),
            "version": "control-plane-002",
            "build_signature": "watcher-control-plane-2026-07-08",
        }
        self.client.post("/nodes/heartbeat", payload)

    def emit(self, event: dict[str, Any]) -> None:
        self.event_times.append(time.time())
        try:
            self.client.post("/jobs/file-events", {
                "event_type": event["event_type"],
                "path": event.get("old_path") or event["path"],
                "dest_path": event.get("path") if event["event_type"] == "moved" else None,
                "is_directory": event.get("is_directory", False),
                "source": "watcher_control_plane",
            })
            if self.needs_help(event):
                self.create_help_request(event, "unreadable_or_unknown_path")
        except ConnectionError:
            self.queue.append({"kind": "file_event", "payload": event})

    def needs_help(self, event: dict[str, Any]) -> bool:
        path = Path(str(event["path"]))
        if event["event_type"] == "deleted":
            return False
        if event.get("danger_markers") or event.get("extension") in UNKNOWN_EXTENSIONS:
            return True
        try:
            if path.exists():
                if path.is_dir():
                    next(path.iterdir(), None)
                else:
                    path.stat()
        except OSError:
            return True
        return False

    def create_help_request(self, event: dict[str, Any], reason: str) -> None:
        path = Path(str(event["path"]))
        payload = {
            "requested_capability": "inspect_path",
            "source_node_id": self.source_node_id,
            "file_path": None if event.get("is_directory") else str(path),
            "folder_path": str(path) if event.get("is_directory") else None,
            "reason": reason,
            "payload": {"watcher_event": event},
            "status": "queued",
            "priority": 90,
        }
        try:
            self.client.post("/jobs/help-requests", payload)
        except ConnectionError:
            self.queue.append({"kind": "help_request", "payload": payload})

    def scan(self) -> dict[str, FileSignature]:
        state: dict[str, FileSignature] = {}
        for root in self.roots:
            if not root.exists() or ignored(root, self.config):
                continue
            walker = [root] if root.is_file() else root.rglob("*")
            for path in walker:
                if ignored(path, self.config):
                    continue
                try:
                    st = path.stat()
                except OSError:
                    event = build_event("modified", path, source_node_id=self.source_node_id)
                    self.create_help_request(event, "unreadable_path")
                    continue
                state[str(path)] = FileSignature(st.st_size, st.st_mtime_ns, path.is_dir())
        return state

    def reconcile_once(self) -> list[dict[str, Any]]:
        current = self.scan()
        events: list[dict[str, Any]] = []
        old_keys, new_keys = set(self.snapshot), set(current)
        for path in sorted(new_keys - old_keys):
            events.append(build_event("created", Path(path), source_node_id=self.source_node_id, is_directory=current[path].is_directory))
        for path in sorted(old_keys - new_keys):
            events.append(build_event("deleted", Path(path), source_node_id=self.source_node_id, is_directory=self.snapshot[path].is_directory))
        for path in sorted(old_keys & new_keys):
            if self.snapshot[path] != current[path]:
                events.append(build_event("modified", Path(path), source_node_id=self.source_node_id, is_directory=current[path].is_directory))
        self.snapshot = current
        self.last_reconciliation = utc_now()
        for event in events:
            self.emit(event)
        return events

    def status_lines(self) -> list[str]:
        try:
            self.client.get("/nodes/status")
            hub = "reachable"
        except ConnectionError as exc:
            hub = f"unreachable ({exc})"
        cutoff = time.time() - 3600
        events_hour = sum(1 for t in self.event_times if t >= cutoff)
        return [
            "David-OS Watcher Control Plane",
            f"node: {self.source_node_id}",
            f"hub: {self.client.base_url} ({hub})",
            "watched roots:",
            *[f"  - {root}" for root in self.roots],
            f"events/hour: {events_hour}",
            f"last reconciliation: {self.last_reconciliation or 'never'}",
            f"local queue depth: {self.queue.depth()}",
        ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="David-OS watcher control plane")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--base-url", default=os.environ.get("FIHUB_BASE_URL", "http://127.0.0.1:10000"))
    parser.add_argument("--token", default=os.environ.get("FIHUB_API_TOKEN"))
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    client = HubClient(args.base_url, args.token, float(config.get("hub_timeout_seconds", 5)), dry_run=args.dry_run, offline=args.offline)
    plane = WatcherControlPlane(config, client)
    plane.snapshot = plane.scan()
    if args.status:
        print("\n".join(plane.status_lines()))
        return 0
    try:
        plane.heartbeat()
    except ConnectionError:
        pass
    if args.once or not args.watch:
        plane.reconcile_once()
        return 0
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as exc:
        raise SystemExit("watchdog is required for --watch") from exc
    class Handler(FileSystemEventHandler):
        def _handle(self, event_type: str, event: Any) -> None:
            if ignored(Path(event.src_path), config):
                return
            plane.emit(build_event(event_type, Path(event.src_path), source_node_id=plane.source_node_id, is_directory=event.is_directory))
        def on_created(self, event: Any) -> None: self._handle("created", event)
        def on_modified(self, event: Any) -> None: self._handle("modified", event)
        def on_deleted(self, event: Any) -> None: self._handle("deleted", event)
        def on_moved(self, event: Any) -> None:
            plane.emit(build_event("moved", Path(event.dest_path), old_path=Path(event.src_path), source_node_id=plane.source_node_id, is_directory=event.is_directory))
    observer = Observer()
    for root in plane.roots:
        if root.exists():
            observer.schedule(Handler(), str(root), recursive=True)
    observer.start()
    interval = float(config.get("scan_interval_seconds", 300))
    try:
        while True:
            plane.heartbeat()
            plane.reconcile_once()
            time.sleep(interval)
    finally:
        observer.stop(); observer.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
