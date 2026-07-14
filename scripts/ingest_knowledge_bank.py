#!/usr/bin/env python3
"""Ingest knowledge bank markdown files into the hub's memory + graph layers.

Purpose: Scan a bucket folder for .md files, extract frontmatter, generate
lightweight embeddings, and create both memory_items (vector search) and
kg_nodes (graph traversal) entries. Also parses wikilinks [[...]] to create edges.

Usage:
    python scripts/ingest_knowledge_bank.py --bucket API_Docs --db .data/file-intelligence-hub.sqlite3
    python scripts/ingest_knowledge_bank.py --bucket Personal_Notes --db .data/file-intelligence-hub.sqlite3 --dry-run
    python scripts/ingest_knowledge_bank.py --all --db .data/file-intelligence-hub.sqlite3

Date: 2026-07-14
codex: scripts/ingest_knowledge_bank.py — knowledge bank ingestion + vectorization + graphing
Status: TESTED (manual run on API_Docs bucket)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Add repo root so we can import the hub
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "api"))

from file_intelligence_hub.storage.db import connect, initialize, current_version
from file_intelligence_hub.storage.memory_repo import MemoryRepo
from graphs.store import GraphStore


# ── Config ─────────────────────────────────────────────────────────

BUCKETS_ROOT = REPO_ROOT / "memory" / "40_Knowledge_Banks"
KNOWN_BUCKETS = ["API_Docs", "File_Intelligence", "Personal_Notes", "Vectorized_Docs"]
HUB_MAP = {
    "API_Docs": "operations",
    "File_Intelligence": "operations",
    "Personal_Notes": "framework",
    "Vectorized_Docs": "ai-hub",
}


# ── Embedding (lightweight local) ──────────────────────────────────

def _generate_embedding(text: str, dim: int = 384) -> list[float]:
    """Generate a lightweight content fingerprint.

    Uses a deterministic hash-based embedding that works without external
    dependencies. If sentence-transformers is installed, it will be used
    instead for proper semantic embeddings.
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text, normalize_embeddings=True).tolist()
    except Exception:
        pass

    # Fallback: deterministic hash-based embedding (not semantic, but stable)
    h = hashlib.sha256(text.encode()).hexdigest()
    vec = []
    for i in range(dim):
        chunk = h[i % 64 : i % 64 + 4] or "0"
        val = int(chunk, 16) / 65535.0
        vec.append(val)
    return vec


# ── Frontmatter parser ─────────────────────────────────────────────

def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and return (metadata, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        import yaml
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return meta, parts[2].strip()


# ── Wikilink extraction ────────────────────────────────────────────

def _extract_wikilinks(body: str) -> list[str]:
    """Extract [[...]] wikilinks from markdown body."""
    return re.findall(r"\[\[([^\]]+)\]\]", body)


def _extract_tags(body: str) -> list[str]:
    """Extract #hashtags from markdown body."""
    return list(set(re.findall(r"#([a-zA-Z0-9_\-]+)", body)))


# ── Ingestion logic ────────────────────────────────────────────────

def _load_bucket_config(bucket_name: str) -> dict:
    config_path = BUCKETS_ROOT / bucket_name / "_bucket.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "bucket": bucket_name,
        "hub": HUB_MAP.get(bucket_name, "ai-hub"),
        "node_types": ["doc"],
        "auto_vectorize": True,
        "tags": [bucket_name.lower()],
    }


def ingest_file(
    file_path: Path,
    bucket_name: str,
    memory_repo: MemoryRepo,
    graph_store: GraphStore,
    dry_run: bool = False,
) -> dict:
    """Ingest a single markdown file into memory + graph."""
    content = file_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(content)
    bucket_config = _load_bucket_config(bucket_name)
    hub = bucket_config.get("hub", "ai-hub")
    default_tags = bucket_config.get("tags", [])

    title = meta.get("title", file_path.stem)
    tags = meta.get("tags", []) or _extract_tags(body)
    tags = list(set(tags + default_tags))

    # 1. Memory item (vector search)
    embedding = None
    if bucket_config.get("auto_vectorize", True):
        embedding = _generate_embedding(body[:4000])  # First 4k chars for speed

    memory_id = None
    if not dry_run:
        memory_id = memory_repo.create(
            title=title,
            body=body[:8000],  # Store first 8k chars in memory_items
            source=f"knowledge_bank:{bucket_name}",
            folder=bucket_name,
            tags=tags,
            metadata={
                "file_path": str(file_path),
                "bucket": bucket_name,
                "hub": hub,
                **{k: v for k, v in meta.items() if k not in ("title", "tags")},
            },
            embedding=embedding,
        )

    # 2. Graph node
    node_id = None
    if not dry_run:
        node_id = graph_store.create_node(
            hub=hub,
            type=meta.get("type", "doc"),
            label=title,
            path=str(file_path),
            summary=body[:500],
            chi_score=meta.get("chi_score"),
            props={
                "memory_id": memory_id,
                "bucket": bucket_name,
                "tags": tags,
                "file_size": file_path.stat().st_size,
            },
        )
        graph_store.upsert_index(
            node_id=node_id,
            keywords=" ".join(tags + [title]),
            one_liner=body[:120] + "..." if len(body) > 120 else body,
        )

    # 3. Edges from wikilinks
    wikilinks = _extract_wikilinks(body)
    edge_count = 0
    if not dry_run and node_id:
        for link in wikilinks:
            target_node = graph_store.conn.execute(
                "SELECT id FROM kg_nodes WHERE label = ? OR path LIKE ?",
                (link, f"%{link}%"),
            ).fetchone()
            if target_node:
                graph_store.create_edge(
                    src=node_id,
                    dst=target_node["id"],
                    type="references",
                    force="F1",
                    weight=1.0,
                    evidence=[{"source": str(file_path), "context": f"wikilink to [[{link}]]"}],
                )
                edge_count += 1

    return {
        "file": str(file_path),
        "title": title,
        "hub": hub,
        "memory_id": memory_id,
        "node_id": node_id,
        "tags": tags,
        "wikilinks": wikilinks,
        "edges_created": edge_count,
        "dry_run": dry_run,
    }


def ingest_bucket(
    bucket_name: str,
    db_path: str,
    dry_run: bool = False,
) -> list[dict]:
    """Ingest all markdown files in a bucket."""
    bucket_dir = BUCKETS_ROOT / bucket_name
    if not bucket_dir.exists():
        print(f"Bucket directory not found: {bucket_dir}")
        return []

    conn = connect(db_path)
    initialize(conn)

    memory_repo = MemoryRepo(conn)
    graph_store = GraphStore(conn)

    results = []
    for md_file in sorted(bucket_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        result = ingest_file(md_file, bucket_name, memory_repo, graph_store, dry_run=dry_run)
        results.append(result)
        status = "[DRY-RUN]" if dry_run else "[INGESTED]"
        print(f"{status} {result['title']} → memory_id={result['memory_id']} node_id={result['node_id']} edges={result['edges_created']}")

    conn.close()
    return results


# ── CLI ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest knowledge bank markdown into hub memory + graph")
    parser.add_argument("--bucket", choices=KNOWN_BUCKETS, help="Which bucket to ingest")
    parser.add_argument("--all", action="store_true", help="Ingest all buckets")
    parser.add_argument("--db", default=".data/file-intelligence-hub.sqlite3", help="Path to hub SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    args = parser.parse_args()

    if not args.bucket and not args.all:
        parser.error("Specify --bucket or --all")

    buckets = KNOWN_BUCKETS if args.all else [args.bucket]
    total = 0
    for bucket in buckets:
        print(f"\n=== Ingesting bucket: {bucket} ===")
        results = ingest_bucket(bucket, args.db, dry_run=args.dry_run)
        total += len(results)

    print(f"\n=== Done. {total} files processed. ===")
    if args.dry_run:
        print("This was a dry run. No data was written.")


if __name__ == "__main__":
    main()
