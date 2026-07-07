# Memory Buckets

The memory system is folder-based on disk and permission-based through the hub.

```text
Folders store memory.
SQLite indexes memory.
Hub API controls who gets memory.
```

## Disk Layout

```text
data/memory/TopOfMind_Memory/
  00_Inbox/
  10_Agents/
  20_Projects/
  30_Shared/
  40_Knowledge_Banks/
  80_Archive/
  90_System/
```

## Bucket Config

Each bucket can contain `_bucket.json`.

```json
{
  "bucket_id": "claude-private",
  "label": "Claude Private",
  "owner": "operator",
  "visibility": "private",
  "allowed_agents": ["claude"],
  "vector_namespace": "claude-private",
  "requires_approval_to_share": true
}
```

## Access Rule

If Gemini asks for memory, the hub only searches:

- `gemini-private`
- approved shared buckets
- current project buckets where Gemini is allowed

The hub blocks:

- `claude-private`
- `codex-private`
- `operator-private`

Vector search must use the same namespace and permission checks.

