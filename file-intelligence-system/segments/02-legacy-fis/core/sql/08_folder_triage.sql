-- FIS Folder Triage Table
-- Run once: psql -h 192.168.1.97 -U postgres -d fis_db -f sql/08_folder_triage.sql

CREATE TABLE IF NOT EXISTS folder_triage (
    id              SERIAL PRIMARY KEY,
    full_path       TEXT UNIQUE NOT NULL,
    folder_name     TEXT NOT NULL,
    parent_path     TEXT,
    depth           INT,
    root            TEXT,
    rating          TEXT DEFAULT NULL,   -- keep | rename | delete | merge | review
    new_name        TEXT DEFAULT NULL,   -- filled in when rating = rename
    notes           TEXT DEFAULT NULL,
    action_taken    TEXT DEFAULT NULL,   -- applied | skipped | error | pending
    new_full_path   TEXT DEFAULT NULL,
    error_msg       TEXT DEFAULT NULL,
    scanned_at      TIMESTAMPTZ DEFAULT NOW(),
    rated_at        TIMESTAMPTZ DEFAULT NULL,
    applied_at      TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_ft_rating  ON folder_triage(rating);
CREATE INDEX IF NOT EXISTS idx_ft_root    ON folder_triage(root);
CREATE INDEX IF NOT EXISTS idx_ft_depth   ON folder_triage(depth);
CREATE INDEX IF NOT EXISTS idx_ft_action  ON folder_triage(action_taken);
