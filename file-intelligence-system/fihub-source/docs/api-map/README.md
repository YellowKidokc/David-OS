# API Map

This map keeps track of the different API ranges in the Top of Mind / File Intelligence Hub system.

The goal is to avoid a pile of scripts by knowing which layer owns each kind of action.

## Range 1: Hub Brain APIs

These are the core FastAPI endpoints in this repo.

Purpose:

- store messages
- route agent work
- store memory
- create file and command jobs
- keep review and ledger records

Current endpoints:

- `/top-of-mind/sources`
- `/top-of-mind/messages`
- `/top-of-mind/combine`
- `/top-of-mind/controls/end-all`
- `/memory/items`
- `/memory/search`
- `/operator/file-actions`
- `/operator/commands`
- `/jobs`
- `/reviews`
- `/nodes`
- `/intelligence/files`
- `/intelligence/folders/summary`

## Range 2: Desktop Bridge APIs

These talk to local programs that do not have good APIs of their own.

Examples:

- AutoHotkey bridge
- OCR capture around a selected box
- window-follow profiles
- type/click/send/stop/start actions
- command-line Kimi or other CLI AI windows

Pattern:

1. The bridge polls the hub.
2. The hub tells it what to type/click/read.
3. The bridge posts results back to the hub.

## Range 3: File and Storage APIs

These move, sync, archive, and publish files.

Examples:

- local filesystem file actions
- NAS API
- Syncthing API
- WebDAV
- Cloudflare R2
- GitHub repository contents API
- future S3-compatible storage

Pattern:

1. Hub creates a file/storage job.
2. Dangerous actions go through review.
3. Connector performs the operation.
4. Ledger records the result.

## Range 4: Knowledge and Vector APIs

These turn text/files/chats into searchable knowledge.

Examples:

- local memory store
- embedding provider
- vector database
- document parsers
- transcript indexers
- prompt library

Pattern:

1. Text or file enters the hub.
2. Hub stores memory metadata.
3. Embeddings are generated later.
4. Search returns relevant memory for frontend or agent prompts.

## Range 5: External AI and Tool APIs

These are model/tool providers and app platforms.

Examples:

- OpenAI API
- Kimi API or Kimi CLI bridge
- Claude browser/desktop bridge
- local LLM servers
- TypingMind/self-hosted frontend
- GitHub API

Pattern:

1. Hub decides what source/agent should receive a task.
2. Direct API agents receive HTTP calls.
3. Desktop-only agents receive bridge tasks.
4. Responses return to `/top-of-mind/messages`.

## Security Rule Across All Ranges

Configs store `secret_ref`, not raw passwords or tokens.

Real secrets belong in:

- Windows Credential Manager
- environment variables
- local ignored `.env`
- future vault service

## Open Inventory

Use this table as we discover more APIs.

| System | Range | Talks To | Capabilities | Auth | Status |
| --- | --- | --- | --- | --- | --- |
| File Intelligence Hub | 1 | local/LAN clients | messages, memory, jobs, reviews | local/network | active |
| AutoHotkey bridge | 2 | desktop apps + hub | hotkeys, type, click, clipboard | none/local | starter |
| Local filesystem | 3 | hub worker | write, append, copy, move, archive, delete, open | OS permissions | active |
| Syncthing | 3 | sync folders | folder sync, device status | API key | planned |
| Cloudflare R2 | 3 | public media/site assets | upload, publish manifest | API token | planned |
| Memory store | 4 | hub/frontend/agents | store/search memory | local DB | active |
| Embedding provider | 4 | memory pipeline | vectorization | API key/local model | planned |
| Kimi CLI | 5 | AHK/CLI bridge | coding/chat agent | local session | planned |
