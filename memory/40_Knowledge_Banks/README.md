# Knowledge Banks — 40_Knowledge_Banks

This directory holds the four primary knowledge repositories for David-OS. Each bucket is a folder with a `_bucket.json` config that tells the ingestion system how to vectorize, tag, and graph its contents.

## Buckets

| Bucket | Hub | Purpose |
|--------|-----|---------|
| `API_Docs` | `operations` | API docs, endpoint specs, integration guides |
| `File_Intelligence` | `operations` | FIS docs, watcher configs, hub architecture |
| `Personal_Notes` | `framework` | Personal notes, insights, journal entries |
| `Vectorized_Docs` | `ai-hub` | Already-embedded docs for semantic search |

## How to add a document

1. Drop a `.md` file into the appropriate bucket folder.
2. Run `python scripts/ingest_knowledge_bank.py --bucket <name>` to vectorize and graph it.
3. The script creates a `memory_items` entry (for vector search) and a `kg_nodes` entry (for graph traversal).

## Bucket config (`_bucket.json`)

Each `_bucket.json` specifies:
- `hub`: Which graph hub the bucket feeds (`ai-hub`, `cross-domain`, `framework`, `operations`)
- `node_types`: What types of nodes to create from files in this bucket
- `auto_vectorize`: Whether to auto-generate embeddings on ingestion
- `tags`: Default tags applied to all items from this bucket

## Integration

- **SQLite**: All indexing happens through the hub's `memory_items` and `kg_*` tables.
- **Graph**: The `graphs/store.py` module provides CRUD over nodes, edges, and the index.
- **Search**: The `memory_repo.py` handles semantic search over embeddings; `graph_index` handles keyword + one-liner search.

---
*David Lowe | POF 2828 | July 14, 2026*
