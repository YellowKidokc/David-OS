"""SQLite connection, schema management, and tiny migrations for the hub ledger."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

SCHEMA_VERSION = 6

BASE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    payload_json TEXT NOT NULL,
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id),
    action TEXT NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TRIGGER IF NOT EXISTS jobs_updated_at
AFTER UPDATE ON jobs
BEGIN
    UPDATE jobs SET updated_at = datetime('now') WHERE id = NEW.id;
END;
"""

Migration = Callable[[sqlite3.Connection], None]


def _migration_2(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (1)")
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (2)")


def _migration_3(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS file_records (
            file_id TEXT PRIMARY KEY,
            full_path TEXT NOT NULL,
            normalized_path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            parent_folder_id TEXT,
            node_id TEXT NOT NULL,
            source_machine TEXT,
            raw_json TEXT NOT NULL,
            deterministic_json TEXT NOT NULL,
            ai_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            operational_json TEXT NOT NULL,
            policy_json TEXT NOT NULL,
            relationships_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS folder_summaries (
            folder_id TEXT PRIMARY KEY,
            folder_path TEXT NOT NULL UNIQUE,
            folder_profile_json TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            action_pressure_json TEXT NOT NULL,
            last_scan TEXT NOT NULL DEFAULT (datetime('now')),
            last_summary_version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            node_role TEXT NOT NULL,
            capabilities_json TEXT NOT NULL,
            status TEXT NOT NULL,
            last_seen TEXT NOT NULL DEFAULT (datetime('now')),
            resource_json TEXT NOT NULL,
            local_queue_depth INTEGER NOT NULL DEFAULT 0,
            version TEXT NOT NULL,
            build_signature TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS repair_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repair_type TEXT NOT NULL,
            scope TEXT NOT NULL,
            transfer_mode TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            outcome TEXT NOT NULL,
            error TEXT,
            source_node TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (3)")


def _migration_4(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    additions = {
        "attempts": "ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
        "max_attempts": "ALTER TABLE jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3",
        "last_error_at": "ALTER TABLE jobs ADD COLUMN last_error_at TEXT",
        "leased_by": "ALTER TABLE jobs ADD COLUMN leased_by TEXT",
        "lease_expires_at": "ALTER TABLE jobs ADD COLUMN lease_expires_at TEXT",
    }
    for column, sql in additions.items():
        if column not in existing:
            conn.execute(sql)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL REFERENCES jobs(id),
            from_status TEXT,
            to_status TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (4)")


def _migration_5(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS top_sources (
            source_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            kind TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            priority INTEGER NOT NULL DEFAULT 5,
            muted INTEGER NOT NULL DEFAULT 0,
            paused INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS top_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            source_label TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'assistant',
            body TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 5,
            wall TEXT NOT NULL DEFAULT 'main',
            folder TEXT NOT NULL DEFAULT 'Main',
            pinned INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            combined_from_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TRIGGER IF NOT EXISTS top_sources_updated_at
        AFTER UPDATE ON top_sources
        BEGIN
            UPDATE top_sources SET updated_at = datetime('now') WHERE source_id = NEW.source_id;
        END;
        """
    )
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (5)")


def _migration_6(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'api',
            folder TEXT NOT NULL DEFAULT 'Memory',
            tags_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            embedding_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TRIGGER IF NOT EXISTS memory_items_updated_at
        AFTER UPDATE ON memory_items
        BEGIN
            UPDATE memory_items SET updated_at = datetime('now') WHERE id = NEW.id;
        END;
        """
    )
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (6)")


MIGRATIONS: dict[int, Migration] = {2: _migration_2, 3: _migration_3, 4: _migration_4, 5: _migration_5, 6: _migration_6}


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection configured for small local control-plane writes."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
    return int(row["value"]) if row else 0


def migrate(conn: sqlite3.Connection, *, target_version: int = SCHEMA_VERSION) -> None:
    version = current_version(conn)
    for next_version in range(version + 1, target_version + 1):
        migration = MIGRATIONS.get(next_version)
        if migration:
            migration(conn)
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', ?)",
            (str(next_version),),
        )
    conn.commit()


def initialize(conn: sqlite3.Connection) -> None:
    """Create the v1 ledger schema and apply simple forward migrations."""
    conn.executescript(BASE_SCHEMA)
    migrate(conn)


class Database:
    """Tiny connection owner used by scripts, tests, and API handlers."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.conn = connect(self.db_path)
        initialize(self.conn)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
