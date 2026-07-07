# Hub Overview

TOP AI FIS is the mainframe for file intelligence.

```text
Desktop / Laptop / Synology watchers
  -> POST file events to hub
  -> heartbeat status to hub

Central hub API
  -> store events and API history
  -> enforce memory permissions
  -> scan folders/files
  -> label metadata
  -> classify and predict
  -> propose actions
  -> execute approved safe actions

Agents
  -> scanner
  -> labeler
  -> organizer
  -> converter
  -> NLP/AI helper
```

## Core Concepts

- `node`: A machine or service that can report events or run jobs.
- `file_event`: A created/moved/renamed/deleted/modified event.
- `file_record`: The hub cache for a known file path or hash.
- `folder_scan`: Scanner output for a folder.
- `sidecar`: Protected metadata files such as `.chi`, `.fmeta`, `.fisnote`, `.fistag`, `.fisdead`.
- `action_proposal`: A suggested move, rename, archive, convert, label, or ignore action.
- `preference`: A learned or explicit rule about naming, folders, actions, or automation.
- `transition`: A history record used for simple Markov-style prediction.
- `knowledge_bank`: A named searchable memory collection.
- `vector_namespace`: A permission-bounded embedding space for a bucket or project.
- `dispatch_job`: A routed message or command sent to an agent, command worker, or bridge.
- `command_job`: A command-line request with approval and captured stdout/stderr.

## First API Shape

```text
GET  /health
GET  /nodes/status
POST /nodes/heartbeat

POST /events/file
POST /scan/folder
POST /classify/file
POST /rename/suggest
POST /actions/propose
POST /actions/approve
POST /clipboard/save
GET  /clipboard/latest
POST /api-calls/log
GET  /api-calls/recent
POST /commands/jobs
POST /dispatch/jobs
POST /knowledge-banks
POST /knowledge-banks/{id}/items
GET  /knowledge-banks/{id}/search
POST /vectors/chunk
POST /vectors/embed
GET  /vectors/search
POST /mcp/tools/call
```

## Memory Backbone

```text
data/memory/TopOfMind_Memory
  00_Inbox
  10_Agents
  20_Projects
  30_Shared
  40_Knowledge_Banks
  80_Archive
  90_System
```

Each bucket can have `_bucket.json`. The hub reads that file, stores the
bucket in SQLite, and enforces access based on `allowed_agents`,
`visibility`, and `requires_approval_to_share`.
