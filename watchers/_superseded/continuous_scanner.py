#!/usr/bin/env python3
"""Low-resource continuous scanner

Moves file-change events into low-rate destination sync writes.
Designed to be simple and low CPU/RAM:
- event-driven updates via watchdog when available
- in-memory dedupe (collapse rapid duplicate events)
- batched worker loop with short sleeps
- no full-tree scans unless configured
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from threading import Event, Thread

from typing import Dict, Iterable, List, Optional


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256sum(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Config:
    watch_roots: List[str]
    ignore_roots: List[str]
    target_drive_root: str
    state_file: str
    scan_interval_seconds: float
    batch_limit: int
    dedupe_seconds: float
    max_file_size_bytes: int
    include_extensions: List[str]
    exclude_extensions: List[str]
    fallback_full_scan_hours: int


def load_config(path: str) -> Config:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)

    return Config(
        watch_roots=list(data.get("watch_roots", [])),
        ignore_roots=list(data.get("ignore_roots", [])),
        target_drive_root=data.get("target_drive_root", ""),
        state_file=data.get("state_file", "run/state.json"),
        scan_interval_seconds=float(data.get("scan_interval_seconds", 2.0)),
        batch_limit=int(data.get("batch_limit", 100)),
        dedupe_seconds=float(data.get("dedupe_seconds", 1.25)),
        max_file_size_bytes=int(data.get("max_file_size_bytes", 200 * 1024 * 1024)),
        include_extensions=[str(x).lower() for x in data.get("include_extensions", [])],
        exclude_extensions=[str(x).lower() for x in data.get("exclude_extensions", [])],
        fallback_full_scan_hours=int(data.get("fallback_full_scan_hours", 0)),
    )


def should_ignore(path: Path, watch_root: Path, ignore_roots: Iterable[str]) -> bool:
    lower = str(path).lower()
    for root in ignore_roots:
        r = Path(root)
        if str(r).lower() in lower:
            return True
        try:
            if path.resolve().is_relative_to(r.resolve()):
                return True
        except Exception:
            pass
        if lower.startswith(str(r).lower() + os.sep):
            return True
    return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Low-resource continuous scanner")
    p.add_argument("--config", default="config.json", help="Path to config json")
    p.add_argument("--once", action="store_true", help="Start, run one pass, exit")
    p.add_argument("--log-dir", default="run", help="Directory for runtime logs")
    return p.parse_args()


def load_state(state_file: Path) -> Dict[str, Dict[str, object]]:
    if not state_file.exists():
        return {}
    try:
        with state_file.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return {}


def save_state(state_file: Path, state: Dict[str, Dict[str, object]]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(state_file)


def is_file_allowed(path: Path, config: Config) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in (config.exclude_extensions or []):
        return False
    if config.include_extensions and path.suffix.lower() not in config.include_extensions:
        return False
    return path.stat().st_size <= config.max_file_size_bytes


def should_sync(candidate: Dict[str, object], state: Dict[str, Dict[str, object]], config: Config) -> bool:
    rel = candidate["rel_path"]
    src = Path(candidate["src"])
    try:
        stat = src.stat()
    except FileNotFoundError:
        return False

    key = rel
    old = state.get(key)
    if old is None:
        return True

    if old.get("size") != stat.st_size:
        return True
    if abs(float(old.get("mtime", 0)) - stat.st_mtime) > 0.5:
        return True
    return False


def queue_to_path(queue_item: dict) -> str:
    return queue_item.get("abs_path", "")


def safe_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    shutil.copy2(src, dst)


class ScannerService:
    def __init__(self, config: Config, log_dir: Path):
        self.config = config
        self.stop_event = Event()
        self.queue: Queue[dict] = Queue()
        self.last_event: Dict[str, float] = {}
        self.log_file = log_dir / "scanner.log"
        self.state_file = Path(config.state_file)
        self.state = load_state(self.state_file)

    def log(self, message: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{now_utc_iso()}] {message}\n")

    def ingest_event(self, src_path: str, event_type: str) -> None:
        p = Path(src_path)
        now = time.time()

        for root in self.config.watch_roots:
            root_path = Path(root)
            if p.is_relative_to(root_path):
                rel = str(p.relative_to(root_path))
                break
        else:
            return

        if should_ignore(p, root_path, self.config.ignore_roots):
            return

        if event_type in ("created", "modified", "moved", "deleted"):
            last = self.last_event.get(src_path, 0)
            if now - last < self.config.dedupe_seconds:
                return
            self.last_event[src_path] = now

            self.queue.put({
                "event": event_type,
                "abs_path": str(p),
                "rel_path": rel,
                "root": str(root_path),
                "ts": now,
            })

    def sync_loop(self, watch_once: bool = False) -> None:
        watch_roots = [Path(x) for x in self.config.watch_roots]
        target = Path(self.config.target_drive_root)

        pending: Dict[str, dict] = {}
        last_flush = 0.0

        while not self.stop_event.is_set():
            while not self.queue.empty():
                item = self.queue.get()
                pending[item["abs_path"]] = item

            if pending and (time.time() - last_flush >= self.config.scan_interval_seconds or watch_once):
                to_process = list(pending.values())[: self.config.batch_limit]
                for item in to_process:
                    abs_path = Path(item["abs_path"])
                    root = Path(item["root"])
                    rel = Path(item["rel_path"])
                    dst = target / rel
                    event = item["event"]
                    key = str(rel)

                    try:
                        if event == "deleted" or not abs_path.exists():
                            if dst.exists():
                                dst.unlink()
                                self.state.pop(key, None)
                                self.log(f"DELETED -> {dst}")
                        else:
                            if not is_file_allowed(abs_path, self.config):
                                continue
                            if not should_sync(item, self.state, self.config):
                                continue

                            src_stat = abs_path.stat()
                            safe_copy(abs_path, dst)
                            h = sha256sum(abs_path)
                            self.state[key] = {
                                "size": src_stat.st_size,
                                "mtime": src_stat.st_mtime,
                                "sha256": h,
                                "synced_at": now_utc_iso(),
                            }
                            self.log(f"SYNC {event.upper()} -> {dst}")
                    except Exception:
                        self.log(f"ERROR syncing {abs_path}: {traceback.format_exc()}".replace("\n", " | "))

                    pending.pop(abs_path.as_posix(), None)
                    pending.pop(str(abs_path), None)
                    self.queue.task_done()

                save_state(self.state_file, self.state)
                last_flush = time.time()

                if watch_once:
                    break

            if watch_once:
                break

            # periodic no-op wait
            time.sleep(0.25)

    def run(self) -> None:
        try:
            self.sync_loop()
        finally:
            save_state(self.state_file, self.state)

    def stop(self) -> None:
        self.stop_event.set()


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config(args.config)
    log_dir = Path(args.log_dir)

    service = ScannerService(cfg, log_dir)

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class _FH(FileSystemEventHandler):
            def on_created(self, ev):
                if not ev.is_directory:
                    service.ingest_event(ev.src_path, "created")

            def on_modified(self, ev):
                if not ev.is_directory:
                    service.ingest_event(ev.src_path, "modified")

            def on_moved(self, ev):
                if not ev.is_directory:
                    service.ingest_event(ev.dest_path, "moved")
                    service.ingest_event(ev.src_path, "deleted")

            def on_deleted(self, ev):
                if not ev.is_directory:
                    service.ingest_event(ev.src_path, "deleted")

        observer = Observer()
        handler = _FH()

        for root in cfg.watch_roots:
            observer.schedule(handler, root, recursive=True)

        observer.start()
        try:
            service.run()
        finally:
            observer.stop()
            observer.join(timeout=2)

    except Exception as ex:
        # fallback mode: keep process alive and wait for manual restart if watchdog missing
        service.log(f"FALLBACK scan mode: {ex}")
        service.log("Install watchdog for live mode: pip install watchdog")
        while True:
            if args.once:
                break
            time.sleep(5)