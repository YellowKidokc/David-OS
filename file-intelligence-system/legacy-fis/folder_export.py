"""
FIS Folder Triage — Export
Walks target folders and outputs a CSV for human rating.

Usage:
    python folder_export.py
    python folder_export.py --roots "O:\\_Theophysics_v4" "D:\\GitHub"
    python folder_export.py --max-depth 3

Columns in output CSV:
    id            - sequential integer (stable reference)
    parent_path   - parent folder path
    folder_name   - just the folder name
    full_path     - full absolute path
    depth         - depth relative to root (root=0)
    root          - which root this came from
    rating        - FILL IN: keep | rename | delete | merge | review
    new_name      - FILL IN: new folder name (only needed if rating=rename)
    notes         - FILL IN: optional notes
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# --- Default roots from settings.ini ---
DEFAULT_ROOTS = [
    r"B:\transfer\Desktop STAY",
    r"C:\Users\lowes\Documents",
    r"D:\GitHub",
    r"O:\_Theophysics_v4",
]

SKIP_DIRS = {".git", "__pycache__", ".obsidian", "node_modules", ".vs", "venv", ".venv"}

OUTPUT_DIR = Path(r"D:\GitHub\file-intelligence-system\exports")


def walk_folders(roots: list[str], max_depth: int) -> list[dict]:
    rows = []
    row_id = 1

    for root_str in roots:
        root = Path(root_str)
        if not root.exists():
            print(f"  [SKIP] Not found: {root}", file=sys.stderr)
            continue

        print(f"  [SCAN] {root}")

        for folder in sorted(_walk(root, max_depth=max_depth, current_depth=0)):
            depth = len(folder.relative_to(root).parts)
            rows.append({
                "id": row_id,
                "parent_path": str(folder.parent),
                "folder_name": folder.name,
                "full_path": str(folder),
                "depth": depth,
                "root": str(root),
                "rating": "",
                "new_name": "",
                "notes": "",
            })
            row_id += 1

    return rows


def _walk(path: Path, max_depth: int, current_depth: int):
    """Yield all subdirectory Paths recursively, skipping known noise dirs."""
    try:
        children = sorted(path.iterdir())
    except PermissionError:
        return

    for child in children:
        if not child.is_dir():
            continue
        if child.name in SKIP_DIRS or child.name.startswith("."):
            continue

        yield child

        if current_depth < max_depth - 1:
            yield from _walk(child, max_depth, current_depth + 1)


def export_csv(rows: list[dict], output_path: Path):
    fieldnames = ["id", "parent_path", "folder_name", "full_path", "depth", "root",
                  "rating", "new_name", "notes"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n  [DONE] {len(rows)} folders → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="FIS Folder Triage Export")
    parser.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS,
                        help="Root folders to scan")
    parser.add_argument("--max-depth", type=int, default=4,
                        help="Max folder depth to walk (default: 4)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output CSV path (default: exports/folder_triage_TIMESTAMP.csv)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"folder_triage_{timestamp}.csv"

    print(f"\nFIS Folder Triage Export")
    print(f"Roots: {args.roots}")
    print(f"Max depth: {args.max_depth}")
    print()

    rows = walk_folders(args.roots, args.max_depth)
    export_csv(rows, output_path)

    print(f"\nNext step:")
    print(f"  1. Open {output_path} in Excel")
    print(f"  2. Fill in 'rating' column:  keep | rename | delete | merge | review")
    print(f"  3. Fill in 'new_name' for any row rated 'rename'")
    print(f"  4. Save the CSV")
    print(f"  5. Run:  python folder_rename_apply.py --csv \"{output_path}\"")


if __name__ == "__main__":
    main()
