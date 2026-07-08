"""Safe filesystem watcher/API bridge for TOP AI FIS.

The watcher observes file changes, normalizes them, and sends cache/job/message
payloads to the File Intelligence Hub API. It never moves, renames, deletes,
archives, converts, or writes sidecars next to watched files. The only local
writes are optional offline queue JSONL files under runtime/queue (or a configured
queue directory).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VALID_EVENTS = {"created", "modified", "moved", "deleted"}
SAFE_SEMANTIC_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log", ".py", ".ps1", ".ahk"}
PROTECTED_DIR_NAMES = {".git", ".svn", ".hg", "node_modules", ".venv", "venv", "__pycache__"}
SECRET_NAME_PARTS = {"secret", "password", "passwd", "token", "apikey", "api_key", "credential", ".env", "id_rsa"}
PROGRAM_MARKERS = {".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "composer.json", "pom.xml", "build.gradle"}
DEFAULT_CONFIG_PATH = Path("config/watchers/hub_watcher.example.json")
DEFAULT_QUEUE_DIR = Path("runtime/queue")


@dataclass(frozen=True)
class FileState:
    mtime_ns: int
    size_bytes: int


class HubApiError(RuntimeError):
    """Raised when the Hub API cannot accept a watcher payload."""


class HubClient:
    def __init__(self, base_url: str, token: str | None = None, *, timeout: float = 5.0, dry_run: bool = False, offline: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.dry_run = dry_run
        self.offline = offline

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run or self.offline:
            print(json.dumps({"method": "POST", "url": f"{self.base_url}{endpoint}", "payload": payload}, sort_keys=True))
            return {"dry_run": self.dry_run, "offline": self.offline}
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-API-Token"] = self.token
        request = Request(f"{self.base_url}{endpoint}", data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - configured local/LAN endpoint
                data = response.read().decode("utf-8")
                return json.loads(data) if data else {}
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise HubApiError(str(exc)) from exc


class JsonlQueue:
    def __init__(self, queue_dir: Path) -> None:
        self.queue_dir = queue_dir
        self.queue_file = queue_dir / "hub_watcher_events.jsonl"

    def append(self, event: dict[str, Any]) -> None:
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        with self.queue_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.queue_file.exists():
            return []
        items: list[dict[str, Any]] = []
        with self.queue_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items

    def replace(self, items: list[dict[str, Any]]) -> None:
        if not items:
            if self.queue_file.exists():
                self.queue_file.unlink()
            return
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        with self.queue_file.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item, sort_keys=True) + "\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"watcher config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def iter_profiles(config: dict[str, Any]) -> list[dict[str, Any]]:
    if "profiles" in config:
        return list(config.get("profiles", []))
    return list(config.get("watched_folders", []))


def profile_for(path: Path, profiles: Iterable[dict[str, Any]]) -> dict[str, Any]:
    best: tuple[int, dict[str, Any]] | None = None
    resolved = path.expanduser().resolve(strict=False)
    for profile in profiles:
        root = Path(str(profile.get("path", ""))).expanduser().resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        score = len(root.parts)
        if best is None or score > best[0]:
            best = (score, profile)
    return best[1] if best else {"folder_role": "unknown", "review_only": True, "protected": False}


def is_program_root(path: Path) -> bool:
    directory = path if path.is_dir() else path.parent
    return any((directory / marker).exists() for marker in PROGRAM_MARKERS)


def contains_secret_hint(path: Path) -> bool:
    lowered = path.name.lower()
    return any(part in lowered for part in SECRET_NAME_PARTS)


def blocked_reason(path: Path, profile: dict[str, Any]) -> str | None:
    if bool(profile.get("protected")):
        return "protected_folder_profile"
    if any(part in PROTECTED_DIR_NAMES for part in path.parts):
        return "protected_directory"
    if contains_secret_hint(path):
        return "secret_or_credential_name"
    if is_program_root(path):
        return "program_root"
    return None


def stat_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.exists() and path.is_file() else 0
    except OSError:
        return 0


def normalize_event(event_type: str, path: Path, *, old_path: Path | None, source_node_id: str, profiles: list[dict[str, Any]]) -> dict[str, Any]:
    event_type = event_type if event_type in VALID_EVENTS else "modified"
    profile = profile_for(path, profiles)
    reason = blocked_reason(path, profile)
    return {
        "source_node_id": source_node_id,
        "event_type": event_type,
        "path": str(path),
        "old_path": str(old_path) if old_path else None,
        "extension": path.suffix.lower(),
        "size_bytes": 0 if event_type == "deleted" else stat_size(path),
        "timestamp": utc_now(),
        "folder_profile": profile.get("folder_role", profile.get("name", "unknown")),
        "review_status": "block" if reason else ("review" if profile.get("review_only", True) else "candidate"),
        "blocked_reason": reason,
    }


def build_payloads(event: dict[str, Any]) -> list[tuple[str, dict[str, Any], bool]]:
    metadata = {"watcher_event": event, "source_node_id": event["source_node_id"], "folder_profile": event["folder_profile"]}
    payloads: list[tuple[str, dict[str, Any], bool]] = []
    if event["event_type"] != "deleted":
        payloads.append(("/files/cache", {"full_path": event["path"], "size_bytes": event["size_bytes"], "tags": ["watcher", event["review_status"]], "metadata": metadata}, True))
    job_payload = {"event_type": event["event_type"], "path": event.get("old_path") or event["path"], "dest_path": event["path"] if event["event_type"] == "moved" else None, "source": "hub_watcher", "is_directory": False}
    payloads.append(("/jobs/file-events", job_payload, True))
    if event["review_status"] != "block" and event["extension"] in SAFE_SEMANTIC_EXTENSIONS and event["event_type"] != "deleted":
        payloads.append(("/semantic/score", {"path": event["path"], "metadata": metadata}, False))
    payloads.append(("/top-of-mind/messages", {"source_id": "hub_watcher", "source_label": "Hub Watcher", "body": f"{event['event_type']} {event['path']} [{event['review_status']}]", "metadata": metadata}, True))
    return payloads


class HubWatcher:
    def __init__(self, config: dict[str, Any], client: HubClient, queue: JsonlQueue) -> None:
        self.config = config
        self.client = client
        self.queue = queue
        self.profiles = iter_profiles(config)
        self.source_node_id = str(config.get("source_node_id") or socket.gethostname())
        self.roots = [Path(str(p["path"])).expanduser() for p in self.profiles if p.get("watch_enabled", True) and p.get("path")]
        self._snapshot = self._scan()

    def replay_queue(self) -> None:
        if self.client.offline or self.client.dry_run:
            return
        remaining: list[dict[str, Any]] = []
        for event in self.queue.read_all():
            try:
                self.send_event(event)
            except HubApiError:
                remaining.append(event)
        self.queue.replace(remaining)

    def handle_event(self, event: dict[str, Any]) -> None:
        if self.client.offline:
            self.queue.append(event)
            print(json.dumps({"queued": event}, sort_keys=True))
            return
        try:
            self.send_event(event)
        except HubApiError:
            self.queue.append(event)
            print(json.dumps({"queued_after_api_error": event}, sort_keys=True))

    def send_event(self, event: dict[str, Any]) -> None:
        for endpoint, payload, required in build_payloads(event):
            try:
                self.client.post(endpoint, payload)
            except HubApiError:
                if required:
                    raise
                print(json.dumps({"optional_endpoint_unavailable": endpoint, "path": event["path"]}, sort_keys=True))

    def emit_existing(self) -> list[dict[str, Any]]:
        events = [
            normalize_event("created", Path(path), old_path=None, source_node_id=self.source_node_id, profiles=self.profiles)
            for path in sorted(self._snapshot)
        ]
        for event in events:
            self.handle_event(event)
        return events

    def poll_once(self) -> list[dict[str, Any]]:
        current = self._scan()
        previous_paths = set(self._snapshot)
        current_paths = set(current)
        events: list[dict[str, Any]] = []
        created = sorted(current_paths - previous_paths)
        deleted = sorted(previous_paths - current_paths)
        moved_sources: set[str] = set()
        moved_targets: set[str] = set()
        for old in deleted:
            for new in created:
                if new not in moved_targets and self._snapshot[old] == current[new]:
                    events.append(normalize_event("moved", Path(new), old_path=Path(old), source_node_id=self.source_node_id, profiles=self.profiles))
                    moved_sources.add(old); moved_targets.add(new); break
        for path in created:
            if path not in moved_targets:
                events.append(normalize_event("created", Path(path), old_path=None, source_node_id=self.source_node_id, profiles=self.profiles))
        for path in deleted:
            if path not in moved_sources:
                events.append(normalize_event("deleted", Path(path), old_path=None, source_node_id=self.source_node_id, profiles=self.profiles))
        for path in sorted(current_paths & previous_paths):
            if current[path] != self._snapshot[path]:
                events.append(normalize_event("modified", Path(path), old_path=None, source_node_id=self.source_node_id, profiles=self.profiles))
        self._snapshot = current
        for event in events:
            self.handle_event(event)
        return events

    def run_forever(self, interval: float) -> None:
        self.replay_queue()
        while True:
            self.poll_once()
            time.sleep(interval)

    def _scan(self) -> dict[str, FileState]:
        snapshot: dict[str, FileState] = {}
        for root in self.roots:
            if not root.exists():
                continue
            paths = [root] if root.is_file() else root.rglob("*")
            for path in paths:
                if path.is_file():
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                    snapshot[str(path)] = FileState(stat.st_mtime_ns, stat.st_size)
        return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe TOP AI FIS watcher/API bridge")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--base-url", default=os.environ.get("FIHUB_BASE_URL", "http://127.0.0.1:10000"))
    parser.add_argument("--token", default=os.environ.get("FIHUB_API_TOKEN"))
    parser.add_argument("--queue-dir", default=str(DEFAULT_QUEUE_DIR))
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--emit-existing", action="store_true", help="emit current files as created events for demos/bootstrap")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    client = HubClient(args.base_url, args.token, dry_run=args.dry_run, offline=args.offline)
    watcher = HubWatcher(config, client, JsonlQueue(Path(args.queue_dir)))
    if args.once or not args.watch:
        watcher.replay_queue()
        if args.emit_existing:
            watcher.emit_existing()
        else:
            watcher.poll_once()
        return 0
    watcher.run_forever(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
