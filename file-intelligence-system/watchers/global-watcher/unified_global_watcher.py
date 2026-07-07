import argparse
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha1sum(path: Path, max_bytes: int) -> str:
    total = 0
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                return "skipped_large_file"
            h.update(chunk)
    return h.hexdigest()


def safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        return path.is_relative_to(base)
    except AttributeError:
        try:
            return str(path).lower().startswith(str(base).lower() + os.sep)
        except Exception:
            return False


def should_ignore(path: Path, cfg: "Config", root: Path | None = None) -> bool:
    name = path.name

    if cfg.ignore_hidden and name.startswith("."):
        return True

    if name in cfg.ignore_names:
        return True

    for pfx in cfg.ignore_paths:
        try:
            if path.resolve().is_relative_to(Path(pfx).resolve()):
                return True
        except Exception:
            nfp = str(path).lower()
            fp = str(Path(pfx)).lower()
            if nfp.startswith(fp.lower()):
                return True

    if root is not None:
        return not is_relative_to(path, root)

    return False


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    ensure_dir(path.parent)
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def write_jsonl(path: Path, data: dict):
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@dataclass(frozen=True)
class Config:
    watch_roots: list
    ignore_paths: list
    ignore_names: list
    dedupe_window_seconds: float
    scan_interval_seconds: int
    max_files_per_scan: int
    job_batch_size: int
    ignore_hidden: bool
    state_file: str
    job_dir: str
    request_dir: str
    inventory_dir: str
    max_file_size_bytes: int


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config(**data)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


class UnifiedWatcherService:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.roots = [Path(r) for r in cfg.watch_roots]
        self.job_dir = Path(cfg.job_dir)
        self.request_dir = Path(cfg.request_dir)
        self.inventory_dir = Path(cfg.inventory_dir)
        self.state_file = Path(cfg.state_file)

        self.stop_event = Event()
        self.last_events: dict[str, float] = {}
        self.state = load_state(self.state_file)

        ensure_dir(self.job_dir)
        ensure_dir(self.request_dir)
        ensure_dir(self.inventory_dir)

    def _emit(self, root: Path, path: Path, action: str, reason: str, *, is_dir: bool) -> None:
        try:
            st = path.stat()
            signature = {
                "size": st.st_size,
                "mtime": st.st_mtime,
                "is_dir": is_dir,
            }
        except Exception:
            signature = None

        payload = {
            "event": "inspect",
            "action": action,
            "source": "global_watcher",
            "reason": reason,
            "path": str(path),
            "root": str(root),
            "relative_path": safe_rel(path, root),
            "signature": signature,
        }
        write_json(self.job_dir / f"{uuid.uuid4()}.json", payload)

    def _can_emit(self, key: str) -> bool:
        now = time.time()
        last = self.last_events.get(key, 0.0)
        if now - last < self.cfg.dedupe_window_seconds:
            return False
        self.last_events[key] = now
        return True

    def on_path_event(self, root: Path, raw_path: str, action: str) -> None:
        p = Path(raw_path)
        if should_ignore(p, self.cfg, root):
            return
        is_dir = p.is_dir()
        if (not is_dir) and p.exists():
            try:
                if p.stat().st_size > self.cfg.max_file_size_bytes:
                    return
            except Exception:
                return

        key = f"{action}:{str(p)}"
        if not self._can_emit(key):
            return

        self._emit(root, p, action, "live_event", is_dir=is_dir)

    def full_scan_once(self) -> None:
        new_state = {}
        processed = 0
        inv_file = self.inventory_dir / f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson"

        with inv_file.open("a", encoding="utf-8") as inv:
            for root in self.roots:
                if not root.exists():
                    continue
                for cur_root, dirs, files in os.walk(root):
                    cur_path = Path(cur_root)

                    dirs[:] = [
                        d for d in dirs
                        if not should_ignore(cur_path / d, self.cfg, root)
                    ]

                    for d in dirs:
                        dpath = cur_path / d
                        if should_ignore(dpath, self.cfg, root):
                            continue
                        entry = {
                            "type": "directory",
                            "path": str(dpath),
                            "root": str(root),
                        }
                        inv.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        k = f"DIR:{entry['path']}"
                        try:
                            st = dpath.stat()
                            sig = ("DIR", st.st_size, int(st.st_mtime))
                        except Exception:
                            sig = ("DIR", 0, 0)

                        if self.state.get(k) != sig:
                            self.on_path_event(root, str(dpath), "discovered")
                        new_state[k] = sig
                        processed += 1
                        if processed >= self.cfg.max_files_per_scan:
                            break

                    if processed >= self.cfg.max_files_per_scan:
                        break

                    for fn in files:
                        fpath = cur_path / fn
                        if should_ignore(fpath, self.cfg, root):
                            continue
                        if fpath.exists():
                            try:
                                st = fpath.stat()
                                if st.st_size > self.cfg.max_file_size_bytes:
                                    continue
                                h = sha1sum(fpath, self.cfg.max_file_size_bytes)
                            except Exception:
                                continue

                            entry = {
                                "type": "file",
                                "path": str(fpath),
                                "root": str(root),
                                "size": st.st_size,
                                "mtime": st.st_mtime,
                                "sha1": h,
                            }
                            inv.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            k = f"FILE:{entry['path']}"
                            sig = ("FILE", st.st_size, int(st.st_mtime), h)
                            if self.state.get(k) != sig:
                                action = "discovered" if k not in self.state else "changed"
                                self.on_path_event(root, str(fpath), action)
                            new_state[k] = sig
                            processed += 1
                            if processed >= self.cfg.max_files_per_scan:
                                break

                    if processed >= self.cfg.max_files_per_scan:
                        break

                    if processed >= self.cfg.max_files_per_scan:
                        break

        save_state(self.state_file, new_state)
        self.state = new_state

    def process_requests(self) -> None:
        for req_file in sorted(self.request_dir.glob("*.json")):
            req = read_json(req_file)
            if not isinstance(req, dict):
                try:
                    req_file.unlink()
                except Exception:
                    pass
                continue

            p = Path(str(req.get("path", "")))
            reason = req.get("reason", "manual_request")

            target_root = None
            for r in self.roots:
                if p.exists() and is_relative_to(p, r):
                    target_root = r
                    break
            if target_root is None:
                target_root = self.roots[0] if self.roots else Path(".")

            if not p.exists():
                self._emit(target_root, p, "missing", reason, is_dir=p.suffix == "")
            else:
                self._emit(target_root, p, "manual_inspect", reason, is_dir=p.is_dir())

            try:
                req_file.unlink()
            except Exception:
                pass

    def run(self) -> None:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        service = self

        class _Handler(FileSystemEventHandler):
            def on_created(self, event):
                p = Path(event.src_path)
                for r in service.roots:
                    if is_relative_to(p, r):
                        service.on_path_event(r, event.src_path, "created")
                        return

            def on_modified(self, event):
                if event.is_directory:
                    return
                p = Path(event.src_path)
                for r in service.roots:
                    if is_relative_to(p, r):
                        service.on_path_event(r, event.src_path, "modified")
                        return

            def on_deleted(self, event):
                p = Path(event.src_path)
                for r in service.roots:
                    if is_relative_to(p, r):
                        service.on_path_event(r, event.src_path, "deleted")
                        return

            def on_moved(self, event):
                psrc = Path(event.src_path)
                pdst = Path(event.dest_path)
                for r in service.roots:
                    if is_relative_to(psrc, r):
                        service.on_path_event(r, event.src_path, "moved_out")
                        break
                for r in service.roots:
                    if is_relative_to(pdst, r):
                        service.on_path_event(r, event.dest_path, "moved_in")
                        break

        observer = Observer()
        for r in self.roots:
            if r.exists():
                observer.schedule(_Handler(), str(r), recursive=True)

        observer.start()
        next_scan = time.time() + 2
        try:
            while not self.stop_event.is_set():
                self.process_requests()
                now = time.time()
                if now >= next_scan:
                    self.full_scan_once()
                    next_scan = now + self.cfg.scan_interval_seconds
                time.sleep(0.5)
        finally:
            observer.stop()
            observer.join(timeout=3)

    def stop(self):
        self.stop_event.set()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Global recursive watcher that emits inspect jobs")
    p.add_argument("--config", default="config.example.json")
    p.add_argument("--once", action="store_true", help="Run one-time scan and request drain, then exit")
    p.add_argument("--scan-now", action="store_true", help="Force immediate full scan")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    svc = UnifiedWatcherService(cfg)

    if args.once:
        svc.process_requests()
        svc.full_scan_once()
        return

    if args.scan_now:
        svc.full_scan_once()

    svc.run()


if __name__ == "__main__":
    main()