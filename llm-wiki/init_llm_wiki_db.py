"""
LLM Wiki SQLite Database Initializer
Theophysics Exploration Layer

Run once to create the database. Safe to re-run (uses IF NOT EXISTS).
Location: D:\DONT TOUCH BOOT UP\llm-wiki.db

Usage: python init_llm_wiki_db.py
Optional: python init_llm_wiki_db.py --scan-vault
  (scans O:\_Theophysics_v5 and populates the pages table)
"""

import sqlite3
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

DB_PATH = r"D:\DONT TOUCH BOOT UP\llm-wiki.db"
VAULT_ROOT = r"O:\_Theophysics_v5"

# Folders to skip when scanning for explorable pages
SKIP_DIRS = {
    '.obsidian', '.smart-env', '.stfolder', '.stversions',
    '.git', '.claude', '.claudian', 'node_modules',
    '_EXPLORATIONS', '_ARCHIVE', 'ZZZ_DUPLICATES',
    'Excalidraw', '00_MEDIA', '00_SYSTEM', '00_OS',
    '00_KANBAN', 'Templates', '_templates',
}

# Only explore markdown files
EXPLORABLE_EXT = {'.md'}

# Classification detection from YAML frontmatter
CLASSIFICATION_PATTERNS = {
    'axiom': r'classification:\s*["\']?axiom',
    'theorem': r'classification:\s*["\']?theorem',
    'claim': r'classification:\s*["\']?claim',
    'hypothesis': r'classification:\s*["\']?hypothesis',
    'definition': r'classification:\s*["\']?definition',
    'postulate': r'classification:\s*["\']?postulate',
    'corollary': r'classification:\s*["\']?corollary',
    'boundary_condition': r'classification:\s*["\']?boundary',
}

TIER_MAP = {
    'axiom': 1, 'postulate': 1, 'definition': 1,
    'theorem': 2, 'corollary': 2, 'hypothesis': 2, 'claim': 2,
    'boundary_condition': 3,
}


def create_database():
    """Create the SQLite database and tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vault_path TEXT UNIQUE NOT NULL,
            title TEXT,
            classification TEXT,
            tier INTEGER,
            tags TEXT,
            exploration_count INTEGER DEFAULT 0,
            last_explored TEXT,
            priority REAL DEFAULT 0.5
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS explorations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            verdict TEXT,
            confidence REAL,
            summary TEXT,
            file_path TEXT,
            created_at TEXT NOT NULL,
            session_id TEXT,
            FOREIGN KEY (page_id) REFERENCES pages(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            next_type TEXT NOT NULL,
            reason TEXT,
            priority REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            FOREIGN KEY (page_id) REFERENCES pages(id)
        )
    """)

    # Indexes for fast lookup
    c.execute("CREATE INDEX IF NOT EXISTS idx_pages_vault_path ON pages(vault_path)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_explorations_page_id ON explorations(page_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_explorations_type ON explorations(type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_explorations_verdict ON explorations(verdict)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_queue_priority ON queue(priority DESC)")

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")


def extract_yaml(filepath):
    """Extract YAML frontmatter from a markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(4096)  # only need the top
    except Exception:
        return {}

    if not content.startswith('---'):
        return {}

    end = content.find('---', 3)
    if end == -1:
        return {}

    yaml_block = content[3:end].strip()
    result = {}

    # Simple YAML parsing (no dependency on pyyaml)
    for line in yaml_block.split('\n'):
        if ':' in line and not line.strip().startswith('-'):
            key, _, val = line.partition(':')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                result[key] = val

    # Detect classification
    for cls, pattern in CLASSIFICATION_PATTERNS.items():
        if re.search(pattern, yaml_block, re.IGNORECASE):
            result['classification'] = cls
            result['tier'] = TIER_MAP.get(cls, 2)
            break

    return result


def scan_vault():
    """Scan the vault and populate the pages table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    count = 0
    skipped = 0

    vault = Path(VAULT_ROOT)

    for md_file in vault.rglob('*.md'):
        # Skip excluded directories
        parts = md_file.relative_to(vault).parts
        if any(p in SKIP_DIRS for p in parts):
            skipped += 1
            continue

        # Skip very small files (likely stubs)
        try:
            fsize = md_file.stat().st_size
        except (OSError, FileNotFoundError):
            skipped += 1
            continue
        if fsize < 100:
            skipped += 1
            continue

        rel_path = str(md_file.relative_to(vault))
        try:
            yaml_data = extract_yaml(md_file)
        except (OSError, FileNotFoundError):
            yaml_data = {}
        title = yaml_data.get('title', md_file.stem.replace('-', ' ').replace('_', ' '))
        classification = yaml_data.get('classification', None)
        tier = yaml_data.get('tier', None)
        tags = yaml_data.get('tags', None)

        # Priority: axioms and theorems get higher priority
        priority = 0.5
        if classification == 'axiom':
            priority = 0.9
        elif classification == 'theorem':
            priority = 0.8
        elif classification in ('claim', 'hypothesis'):
            priority = 0.7

        try:
            c.execute("""
                INSERT OR IGNORE INTO pages (vault_path, title, classification, tier, tags, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rel_path, title, classification, tier, tags, priority))
            if c.rowcount > 0:
                count += 1
        except Exception as e:
            print(f"  Error on {rel_path}: {e}")

    conn.commit()
    conn.close()
    print(f"Scanned vault: {count} pages indexed, {skipped} skipped")


def print_stats():
    """Print database statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM pages")
    total_pages = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM explorations")
    total_explorations = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM queue")
    queue_size = c.fetchone()[0]

    c.execute("SELECT classification, COUNT(*) FROM pages WHERE classification IS NOT NULL GROUP BY classification")
    classifications = c.fetchall()

    c.execute("SELECT COUNT(*) FROM pages WHERE exploration_count = 0")
    unexplored = c.fetchone()[0]

    conn.close()

    print(f"\n--- LLM Wiki Database Stats ---")
    print(f"Total pages indexed: {total_pages}")
    print(f"Unexplored pages:    {unexplored}")
    print(f"Total explorations:  {total_explorations}")
    print(f"Queue size:          {queue_size}")
    if classifications:
        print(f"\nBy classification:")
        for cls, cnt in classifications:
            print(f"  {cls}: {cnt}")


if __name__ == '__main__':
    create_database()

    if '--scan-vault' in sys.argv:
        scan_vault()

    print_stats()
