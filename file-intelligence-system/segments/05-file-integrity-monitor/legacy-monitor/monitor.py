"""
monitor.py

Live, real-time file monitoring using the `watchdog` library. Watches a
directory and reports modify/delete/create events as they happen, with
basic duplicate-event filtering since watchdog often fires multiple
events for what is, from a user's perspective, a single file save.
"""

import os
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from integrity_engine import hash_file, is_critical

# Minimum seconds between accepting two events for the same path,
# used to collapse duplicate/rapid-fire events into one.
DEDUPE_WINDOW_SECONDS = 1.0


class IntegrityEventHandler(FileSystemEventHandler):
    """
    Translates raw watchdog filesystem events into clean, deduplicated
    integrity events, then hands them off to a callback function provided
    by whoever is using this monitor (e.g. the GUI).
    """

    def __init__(self, root_path, on_event_callback):
        super().__init__()
        self.root_path = root_path
        self.on_event_callback = on_event_callback
        self._last_event_time = {}  # rel_path -> timestamp, for dedupe

    def _rel_path(self, full_path):
        return os.path.relpath(full_path, self.root_path)

    def _should_process(self, rel_path):
        """Return False if we've already processed an event for this path very recently."""
        now = time.time()
        last_time = self._last_event_time.get(rel_path, 0)
        if now - last_time < DEDUPE_WINDOW_SECONDS:
            return False
        self._last_event_time[rel_path] = now
        return True

    def on_modified(self, event):
        if event.is_directory:
            return
        rel_path = self._rel_path(event.src_path)
        if not self._should_process(rel_path):
            return
        new_hash = hash_file(event.src_path)
        self.on_event_callback(
            event_type="MODIFIED",
            rel_path=rel_path,
            critical=is_critical(event.src_path),
            new_hash=new_hash,
        )

    def on_deleted(self, event):
        if event.is_directory:
            return
        rel_path = self._rel_path(event.src_path)
        if not self._should_process(rel_path):
            return
        self.on_event_callback(
            event_type="DELETED",
            rel_path=rel_path,
            critical=is_critical(event.src_path),
            new_hash=None,
        )

    def on_created(self, event):
        if event.is_directory:
            return
        rel_path = self._rel_path(event.src_path)
        if not self._should_process(rel_path):
            return
        new_hash = hash_file(event.src_path)
        self.on_event_callback(
            event_type="NEW",
            rel_path=rel_path,
            critical=is_critical(event.src_path),
            new_hash=new_hash,
        )


class LiveMonitor:
    """
    Wraps a watchdog Observer to start/stop live monitoring of a directory.
    Designed to be controlled by GUI Start/Stop buttons.
    """

    def __init__(self, root_path, on_event_callback):
        self.root_path = root_path
        self.event_handler = IntegrityEventHandler(root_path, on_event_callback)
        self.observer = Observer()
        self._running = False

    def start(self):
        if self._running:
            return
        self.observer = Observer()  # fresh observer in case of restart after stop
        self.observer.schedule(self.event_handler, self.root_path, recursive=True)
        self.observer.start()
        self._running = True

    def stop(self):
        if not self._running:
            return
        self.observer.stop()
        self.observer.join(timeout=3)
        self._running = False

    def is_running(self):
        return self._running