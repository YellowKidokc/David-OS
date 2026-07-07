# Memory and Vectorization

Memory is the hub's searchable knowledge layer.

The first version stores:

- title
- body
- source
- folder
- tags
- metadata
- optional embedding vector

API:

- `POST /memory/items`
- `GET /memory/items`
- `GET /memory/items/{item_id}`
- `GET /memory/search?q=...`
- `GET /memory/search?q=...&mode=vector`
- `POST /memory/embed-pending`

CLI:

- `fihub-top memory-add --title "..." --body "..." --tag prompt --embed`
- `fihub-top memory-search "query text"`
- `fihub-top memory-search "query text" --mode vector`
- `fihub-top memory-embed-pending`

## Vectorization Plan

The database already has an `embedding_json` slot so the API shape can stay stable.

Next steps:

1. Add an embedding provider integration.
2. Generate embeddings for memory items, prompts, transcripts, and selected chat messages.
3. Replace or supplement text search with vector similarity search.
4. Attach the most relevant memories to outbound agent prompts.

For now, `/memory/search` supports simple text scoring and a local deterministic vector mode. The local vectorizer is good enough to test the control loop without sending private text to an outside API.
