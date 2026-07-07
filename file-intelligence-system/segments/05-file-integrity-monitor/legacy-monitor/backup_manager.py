"""
backup_manager.py

Handles backing up the contents of critical files at baseline time, and
restoring them later if they get modified or deleted. This turns the
monitor from a pure detection tool into a basic recovery tool as well.
"""

import os
import shutil
from datetime import datetime

BACKUP_DIR = "backups"


def _backup_path_for(rel_path):
    """
    Build a safe backup file path for a given relative path, preserving
    folder structure inside the backups directory so nothing collides.
    """
    return os.path.join(BACKUP_DIR, rel_path)


def backup_file(root_path, rel_path):
    """
    Copy a file's current contents into the backups folder, preserving
    its relative path structure. Should be called when a file is first
    added to the baseline (i.e. it's in a known-good state).
    """
    source = os.path.join(root_path, rel_path)
    destination = _backup_path_for(rel_path)

    os.makedirs(os.path.dirname(destination) or BACKUP_DIR, exist_ok=True)

    try:
        shutil.copy2(source, destination)
        return True
    except (FileNotFoundError, PermissionError, OSError):
        return False


def backup_all_critical(root_path, snapshot):
    """
    Back up every file in a snapshot that's marked as critical.
    Called right after a baseline is created or refreshed.
    """
    backed_up = []
    for rel_path, info in snapshot.items():
        if info.get("critical"):
            success = backup_file(root_path, rel_path)
            if success:
                backed_up.append(rel_path)
    return backed_up


def has_backup(rel_path):
    """Check whether a backup copy exists for a given relative path."""
    return os.path.exists(_backup_path_for(rel_path))


def restore_file(root_path, rel_path):
    """
    Restore a file from its backup copy back into the monitored directory,
    overwriting whatever is currently there (or recreating it if deleted).
    Returns True on success, False if no backup exists or restore failed.
    """
    backup_source = _backup_path_for(rel_path)
    destination = os.path.join(root_path, rel_path)

    if not os.path.exists(backup_source):
        return False

    try:
        os.makedirs(os.path.dirname(destination) or root_path, exist_ok=True)
        shutil.copy2(backup_source, destination)
        return True
    except (PermissionError, OSError):
        return False


def list_backups():
    """Return a list of all relative paths currently backed up."""
    backed_up = []
    if not os.path.exists(BACKUP_DIR):
        return backed_up
    for current_root, _dirs, files in os.walk(BACKUP_DIR):
        for filename in files:
            full_path = os.path.join(current_root, filename)
            rel_path = os.path.relpath(full_path, BACKUP_DIR)
            backed_up.append(rel_path)
    return backed_up