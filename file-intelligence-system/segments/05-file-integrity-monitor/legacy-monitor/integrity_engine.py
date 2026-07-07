"""
integrity_engine.py

Core logic for the File Integrity Monitor:
- Hashing files using SHA-256
- Building and persisting a baseline (a snapshot of known-good file states)
- Comparing the current filesystem state against the baseline to detect
  modified, deleted, and newly created files
"""

import os
import json
import hashlib
from datetime import datetime

BASELINE_FILE = "baseline.json"

# File extensions considered "critical" by default.
# Changes to these will be flagged with higher severity in the GUI.
DEFAULT_CRITICAL_EXTENSIONS = {".exe", ".dll", ".sys", ".ini", ".conf", ".bat", ".sh"}


def hash_file(filepath):
    """
    Compute the SHA-256 hash of a file's contents.
    Reads in chunks so large files don't get fully loaded into memory.
    Returns None if the file can't be read (e.g. permission error, file in use).
    """
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def is_critical(filepath, critical_extensions=None):
    """Check if a file's extension marks it as critical."""
    if critical_extensions is None:
        critical_extensions = DEFAULT_CRITICAL_EXTENSIONS
    _, ext = os.path.splitext(filepath)
    return ext.lower() in critical_extensions


def scan_directory(root_path):
    """
    Walk a directory recursively and build a dictionary mapping
    each file's relative path to its hash and metadata.
    """
    snapshot = {}
    for current_root, _dirs, files in os.walk(root_path):
        for filename in files:
            full_path = os.path.join(current_root, filename)
            rel_path = os.path.relpath(full_path, root_path)
            file_hash = hash_file(full_path)
            if file_hash is None:
                continue  # skip unreadable files rather than crashing
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = None
            snapshot[rel_path] = {
                "hash": file_hash,
                "size": size,
                "critical": is_critical(full_path),
                "last_seen": datetime.now().isoformat(),
            }
    return snapshot


def save_baseline(snapshot, root_path, baseline_path=BASELINE_FILE):
    """Persist the baseline snapshot to a JSON file, alongside the root path it covers."""
    data = {
        "root_path": root_path,
        "created_at": datetime.now().isoformat(),
        "files": snapshot,
    }
    with open(baseline_path, "w") as f:
        json.dump(data, f, indent=2)


def load_baseline(baseline_path=BASELINE_FILE):
    """Load a previously saved baseline. Returns None if no baseline exists yet."""
    if not os.path.exists(baseline_path):
        return None
    with open(baseline_path, "r") as f:
        return json.load(f)


def compare_to_baseline(root_path, baseline):
    """
    Compare the current state of root_path against a loaded baseline.
    Returns a dict with three lists: modified, deleted, and new files.
    """
    current_snapshot = scan_directory(root_path)
    baseline_files = baseline["files"]

    modified = []
    deleted = []
    new = []

    for rel_path, old_info in baseline_files.items():
        if rel_path not in current_snapshot:
            deleted.append({"path": rel_path, "critical": old_info.get("critical", False)})
        elif current_snapshot[rel_path]["hash"] != old_info["hash"]:
            modified.append({
                "path": rel_path,
                "critical": current_snapshot[rel_path]["critical"],
                "old_hash": old_info["hash"],
                "new_hash": current_snapshot[rel_path]["hash"],
            })

    for rel_path, info in current_snapshot.items():
        if rel_path not in baseline_files:
            new.append({"path": rel_path, "critical": info["critical"]})

    return {
        "modified": modified,
        "deleted": deleted,
        "new": new,
        "current_snapshot": current_snapshot,
    }