# CODEX BUILD PROMPT — ahk
## Location: D:\GitHub\David-OS\ahk (+ bridges\ahk for the v3 controller lineage)

## Current State
- `overlay\ai_input_overlay.ahk` (July 7, Fabel, UNTESTED) — draggable always-on-top box;
  whatever sits under its center receives pasted text + Enter. Position IS the target.
- `overlay\bridge_listener.ps1` — HTTP front door, POST /send port 8765, token
  `davidos-bridge-2026`, writes JSON to `_inbox\`, overlay polls at 200ms.
- `overlay\start_bridge.bat` — launches both.
- `bridges\ahk\` — AI Chat Controller v3 lineage + 13 API_CALL prompt files +
  routing manifest (from tom_fis_api). Timer-polling era. Reference, being superseded.

## What Works (don't touch)
- The overlay's geometric targeting concept. David designed it; it stays.
- The token auth pattern on the listener.

## What Needs Rewriting (after David's first live test — coordinate in town-square)
- Per-app Enter behavior: some Electron apps send on Enter, some need Ctrl+Enter.
  Add `"send_key"` field to the /send payload ("enter" | "ctrl-enter" | "shift-enter"),
  default "enter". Overlay right-click menu gets a per-session override.
- Reliability: replace fixed Sleeps with clipboard-set verification and a retry
  (max 2) if the paste-length check fails.

## What Needs Building — response capture (the missing half)
The bridge sends INTO the apps; nothing comes back out. Build the capture side:
`overlay\response_capture.ahk` — hotkey (Ctrl+Alt+C) copies the AI's latest response
region: user drags a SECOND overlay ("capture box") over the response area once;
on trigger, the script clicks-drags-selects within that box OR uses triple-click+
Ctrl+A-scoped selection, copies, and POSTs the clipboard to the hub:
`POST http://localhost:2828/top-of-mind/messages` with `{source: "<app-label>", text: ...}`.
App-label set when the capture box is placed (small input prompt).
NOTE: a DAVID_OS_ARCHITECTURE.md Section 9 exists in concept (SetWinEventHook binding,
Chrome extension capture) but is NOT on disk. Until it lands, build ONLY the manual
capture-box version above. Do not architect the extension yourself.

## Dependencies
- Needs: hub running (port 2828) for capture POSTs; api\ prompt done for message routes.
- Feeds: Mattermost crew (via hub relay), the message wall in apps\desk.

## Tests — kill condition
```
start_bridge.bat -> right-click overlay -> "Send test line" lands in Notepad under it
curl POST /send with 500-word text -> arrives complete, single Enter fires
capture box over a Notepad region -> Ctrl+Alt+C -> text appears via hub API
```
DONE = all three manual tests pass on Claude Desktop + one more Electron app,
demonstrated to David live.

## Priority
1. David's live test of the existing overlay (blocks everything).
2. send_key + retry hardening. 3. response_capture.ahk.
