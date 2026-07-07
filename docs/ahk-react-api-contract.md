# AHK ↔ React ↔ Top-of-Mind Hub Contract

This document defines the intended control path for the Top-of-Mind cockpit UI and AutoHotkey bridge. React must only send intent to the Top-of-Mind API hub through `topOfMindApi`; it must not call provider APIs directly. The hub owns routing decisions for API providers, desktop/AHK targets, memory, clipboard, and message stream delivery.

## Ownership boundary

| Layer | Owns | Does not own |
| --- | --- | --- |
| React app | Last-clicked active agent, composer text, button intent, display status | Provider credentials, desktop automation details, route selection |
| Hub API | Agent registry/config, route mode (`api`, `desktop`, `auto`), provider key status, window titles, job queue, memory/clipboard/message persistence | Browser local UI state |
| AHK bridge | Desktop window focus/paste/send/scroll/mic actions, delivery status events | Provider API calls, durable route config |

`localStorage` may remember `topOfMind.activeAgentId` such as “I last clicked Gemini”. The hub should remain the source of truth for whether Gemini exists, how it routes, its provider key status, desktop window title, priority, folder, and wall.

## Required hub routes

| Route | Purpose | React can call now? | AHK can call now? | Notes |
| --- | --- | --- | --- | --- |
| `GET /jobs/stats` | Hub health, queue depth, worker state | Yes | Optional | Used by Hub Health. |
| `POST /clipboard/save` | Save clipboard text/snapshot or clipboard push intent | Yes | Optional | Should persist/log; no provider send. |
| `POST /top-of-mind/messages` | Persist message stream entries | Yes | Optional | Send composer text into hub stream. |
| `POST /agents/send` | Create a routed send intent for the active agent | Yes | Optional | Hub decides API vs desktop vs auto. |
| `POST /top-of-mind/controls/end-all` | Cancel/stop active jobs and desktop runs safely | Yes | Optional | Should be idempotent. |
| `POST /memory/items` | Save memory item from selected text/composer | Yes | Optional | Should persist and optionally enqueue embedding. |
| `POST /bridge/heartbeat` | AHK reports liveness and current profile/window | No | Yes | Updates worker lease/status. |
| `GET /bridge/jobs?worker=ahk-main` | AHK polls next desktop job | No | Yes | Returns pending jobs assigned to/claimable by worker. |
| `POST /bridge/events` | AHK reports delivered/failed/status events | No | Yes | App can surface events from hub status. |
| `POST /bridge/jobs` | Hub/React creates desktop bridge job intent | Yes | Optional | Used for paste, pull, push, mic, scroll as desktop-safe actions. |

## Payloads and expected results

### `POST /agents/send`

Request:

```json
{
  "action": "send_to_active",
  "target": { "id": "gemini", "name": "Gemini", "source_code": 20020 },
  "message": "user text",
  "folder_code": 60002,
  "wall": "main",
  "route_only": true,
  "dry_run": true
}
```

Expected response:

```json
{
  "status": "queued",
  "job_id": "job_123",
  "route": "desktop",
  "target": "gemini"
}
```

### `POST /bridge/jobs`

Request:

```json
{
  "worker": "ahk-main",
  "action": "toggle_scroll",
  "target": { "id": "gemini", "name": "Gemini" },
  "payload": { "enabled": true },
  "source": "react-controlbar"
}
```

Expected response:

```json
{
  "status": "queued",
  "job_id": "bridge_123",
  "worker": "ahk-main"
}
```

### `POST /bridge/heartbeat`

Request:

```json
{
  "worker": "ahk-main",
  "profile": "TopMind",
  "active_window": "Top of Mind",
  "version": "ahk-v2",
  "ts": "2026-07-03T00:00:00Z"
}
```

Expected response:

```json
{ "status": "ok", "lease_seconds": 30 }
```

### `GET /bridge/jobs?worker=ahk-main`

Expected response when a job is available:

```json
{
  "status": "ok",
  "job": {
    "id": "bridge_123",
    "action": "paste_to_active",
    "target": { "id": "gemini", "name": "Gemini" },
    "payload": { "text": "optional text" }
  }
}
```

Expected response when idle:

```json
{ "status": "idle", "job": null }
```

### `POST /bridge/events`

Request:

```json
{
  "worker": "ahk-main",
  "job_id": "bridge_123",
  "event": "delivered",
  "detail": "Pasted text and sent Enter",
  "ok": true
}
```

Expected response:

```json
{ "status": "recorded" }
```

## Button mapping

| AHK hotkey | React button | Action | API endpoint | Status/error behavior |
| --- | --- | --- | --- | --- |
| `Ctrl+V Ctrl+V` | Paste | `paste_to_active` | `POST /clipboard/save`, then optionally `POST /bridge/jobs` | If clipboard route fails, show route unavailable. If bridge route fails, keep local paste text and show job unavailable. |
| `Enter Enter` | Send | `send_to_active` | `POST /top-of-mind/messages` and/or `POST /agents/send` | Persist stream entry; hub queues delivery or returns route-only status. |
| `Ctrl+Alt+Shift+P` | Pull | `pull_latest` | `POST /bridge/jobs` | Queue desktop/API pull job; otherwise show route unavailable. |
| `Ctrl+Alt+Shift+U` | Push | `push_clipboard` | `POST /agents/send` or `POST /bridge/jobs` | Hub chooses active target route. |
| `Ctrl+Alt+Shift+M` | Mic | `mic_toggle` | `POST /bridge/jobs` | Queue AHK desktop toggle; local UI may show pending/toggled. |
| `Ctrl+Alt+Shift+S` | Scroll | `toggle_scroll` | `POST /bridge/jobs` | Queue AHK desktop toggle; local UI may show pending/toggled. |
| `Ctrl+Alt+Shift+R` | Save Memory | `save_memory` | `POST /memory/items` | Save memory item; embedding may be separate. |
| `Ctrl+Alt+Shift+E` | End All | `end_all` | `POST /top-of-mind/controls/end-all` | Idempotent stop/cancel; show success even if no active jobs. |
| `Ctrl+Alt+Shift+H` | Hub Health | `hub_health` | `GET /jobs/stats` | Show queue/worker health or offline status. |
| n/a | Agent Send | `agent_send` | `POST /agents/send` | Hub creates delivery job; no direct provider send from React. |
| n/a | Clipboard Save | `clipboard_save` | `POST /clipboard/save` | Persist clipboard snapshot. |

## Recommended implementation notes

1. Backend route stubs should be thin and safe: validate payload, insert a row into SQLite/job/event tables, and return a clear `status` plus `job_id` when queued.
2. `POST /agents/send` should create a delivery job. It should not synchronously call external providers from the React request path.
3. `POST /bridge/jobs` should create desktop jobs for AHK, including `paste_to_active`, `pull_latest`, `push_clipboard`, `toggle_scroll`, and `mic_toggle`.
4. AHK should poll with `GET /bridge/jobs?worker=ahk-main`, execute only known safe actions, and report via `POST /bridge/events`.
5. React should surface hub responses and errors but should not own retry policy beyond showing current status.
