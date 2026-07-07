"""
FIS Folder Triage — Apply Renames
Reads a rated CSV from folder_export.py and applies renames on disk.
Logs every action to Postgres (fis_db) in the folder_triage_log table.

Usage:
    python folder_rename_apply.py --csv exports/folder_triage_20240101_120000.csv
    python folder_rename_apply.py --csv exports/folder_triage_20240101_120000.csv --dry-run

Ratings handled:
    keep    → no action, logged as confirmed
    rename  → renames folder, requires new_name column
    delete  → SKIPPED (safety — you do this manually)
    merge   → logged as pending, no action (manual merge)
    review  → logged, no action
    (blank) → skipped entirely
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

DB_CONFIG = {
    "host": "192.168.1.97",
    "port": 5432,
    "dbname": "fis_db",
    "user": "postgres",
    "password": "Moss9pep28$",
}

VALID_RATINGS = {"keep", "rename", "delete", "merge", "review"}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS folder_triage_log (
                id              SERIAL PRIMARY KEY,
                triage_id       INTEGER,
                full_path       TEXT NOT NULL,
                folder_name     TEXT,
                rating          TEXT,
                new_name        TEXT,
                notes           TEXT,
                action_taken    TEXT,
                new_full_path   TEXT,
                error_msg       TEXT,
                processed_at    TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
    print("  [DB] folder_triage_log table ready")


def log_action(conn, row: dict, action: str, new_full_path: str = None, error: str = None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO folder_triage_log
                (triage_id, full_path, folder_name, rating, new_name, notes,
                 action_taken, new_full_path, error_msg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row.get("id"),
            row.get("full_path"),
            row.get("folder_name"),
            row.get("rating"),
            row.get("new_name"),
            row.get("notes"),
            action,
            new_full_path,
            error,
        ))
        conn.commit()


def apply_renames(csv_path: Path, dry_run: bool):
    conn = get_conn()
    ensure_table(conn)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rated = [r for r in rows if r.get("rating", "").strip().lower() in VALID_RATINGS]
    print(f"\n  {len(rows)} total rows | {len(rated)} with ratings | {len(rows)-len(rated)} skipped (blank)")

    stats = {"keep": 0, "renamed": 0, "skipped": 0, "error": 0, "dry": 0}

    # Sort renames deepest-first to avoid path conflicts
    rated_sorted = sorted(rated, key=lambda r: -int(r.get("depth", 0)))

    for row in rated_sorted:
        rating = row["rating"].strip().lower()
        full_path = row["full_path"].strip()
        new_name = row["new_name"].strip()
        folder = Path(full_path)

        print(f"\n  [{rating.upper()}] {folder.name}", end="")

        if rating == "keep":
            print(" → no action")
            stats["keep"] += 1
            log_action(conn, row, "kept")

        elif rating == "rename":
            if not new_name:
                print(f" → SKIP (no new_name provided)")
                stats["skipped"] += 1
                log_action(conn, row, "skipped_no_new_name")
                continue

            if not folder.exists():
                print(f" → SKIP (path not found)")
                stats["skipped"] += 1
                log_action(conn, row, "skipped_not_found")
                continue

            new_path = folder.parent / new_name

            if new_path.exists():
                print(f" → SKIP (target exists: {new_name})")
                stats["skipped"] += 1
                log_action(conn, row, "skipped_target_exists", error=f"Target already exists: {new_path}")
                continue

            print(f" → {new_name}", end="")

            if dry_run:
                print(" [DRY RUN]")
                stats["dry"] += 1
                log_action(conn, row, "dry_run_rename", new_full_path=str(new_path))
            else:
                try:
                    folder.rename(new_path)
                    print(" ✓")
                    stats["renamed"] += 1
                    log_action(conn, row, "renamed", new_full_path=str(new_path))
                except Exception as e:
                    print(f" ERROR: {e}")
                    stats["error"] += 1
                    log_action(conn, row, "error", error=str(e))

        elif rating == "delete":
            print(" → SKIPPED (delete is manual — do this yourself)")
            stats["skipped"] += 1
            log_action(conn, row, "delete_flagged_manual")

        elif rating in ("merge", "review"):
            print(f" → logged as {rating}, no action")
            stats["skipped"] += 1
            log_action(conn, row, f"flagged_{rating}")

    conn.close()

    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"  kept:    {stats['keep']}")
    print(f"  renamed: {stats['renamed']}")
    print(f"  skipped: {stats['skipped']}")
    print(f"  errors:  {stats['error']}")
    if dry_run:
        print(f"  dry run: {stats['dry']} (nothing written to disk)")
    print(f"  All actions logged to folder_triage_log in fis_db")


def main():
    parser = argparse.ArgumentParser(description="FIS Folder Triage — Apply Renames")
    parser.add_argument("--csv", required=True, help="Path to rated CSV from folder_export.py")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview renames without touching disk")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"\nFIS Folder Triage — Apply ({mode})")
    print(f"CSV: {csv_path}")

    apply_renames(csv_path, args.dry_run)


if __name__ == "__main__":
    main()
