# Watchers

This lane observes folders and reports file events to the hub.

## Active Tools

| Tool | Purpose |
| --- | --- |
| `filetagger_daemon.py` | Always-on local watcher/catalog daemon lineage |
| `salvaged_file_watcher.py` | Earlier watcher prototype |

## Desired Shape

Watchers should report events to the hub API:

```json
{
  "event_type": "created",
  "path": "D:/example/file.pdf",
  "source_node_id": "desktop",
  "folder_profile": "downloads"
}
```

The watcher should not decide large actions. The hub decides, queues, and asks
for approval when needed.

## Permanent Scanner Rule

The permanent scanner should:

1. Start with an incremental scan.
2. Watch for create, modify, move, and delete events.
3. Update SQLite/hub state.
4. Trigger labeler/scanner jobs through the API.
5. Never delete or move files directly.

