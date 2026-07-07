"""
logger.py

Handles structured, timestamped logging of integrity events to a log file,
and generating a human-readable summary report from logged events.
"""

import os
import json
from datetime import datetime

LOG_FILE = "integrity_log.txt"


def log_event(event_type, rel_path, critical=False, details=""):
    """
    Append a single structured event to the log file.

    event_type: one of "MODIFIED", "DELETED", "NEW", "RESTORED", "BASELINE_CREATED"
    rel_path: the relative file path the event concerns
    critical: whether this file is marked critical
    details: optional extra context (e.g. old/new hash snippet)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    severity = "CRITICAL" if critical else "INFO"

    line = f"[{timestamp}] [{severity}] [{event_type}] {rel_path}"
    if details:
        line += f" - {details}"

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

    return line


def read_log(limit=None):
    """
    Read the log file and return a list of log lines, most recent last.
    If limit is given, only the last `limit` lines are returned.
    """
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, "r") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    if limit:
        return lines[-limit:]
    return lines


def export_report(comparison_result, output_path="integrity_report.txt"):
    """
    Generate a human-readable summary report from a comparison result
    (as returned by integrity_engine.compare_to_baseline) and save it
    to a text file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("=" * 60)
    lines.append("FILE INTEGRITY REPORT")
    lines.append(f"Generated: {timestamp}")
    lines.append("=" * 60)

    modified = comparison_result.get("modified", [])
    deleted = comparison_result.get("deleted", [])
    new = comparison_result.get("new", [])

    lines.append(f"\nModified files: {len(modified)}")
    for item in modified:
        flag = " [CRITICAL]" if item.get("critical") else ""
        lines.append(f"  - {item['path']}{flag}")

    lines.append(f"\nDeleted files: {len(deleted)}")
    for item in deleted:
        flag = " [CRITICAL]" if item.get("critical") else ""
        lines.append(f"  - {item['path']}{flag}")

    lines.append(f"\nNew files: {len(new)}")
    for item in new:
        flag = " [CRITICAL]" if item.get("critical") else ""
        lines.append(f"  - {item['path']}{flag}")

    lines.append("\n" + "=" * 60)

    report_text = "\n".join(lines)
    with open(output_path, "w") as f:
        f.write(report_text)

    return output_path