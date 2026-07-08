# CODEX BUILD PROMPT — ahk (Overlay v2: THE definitive assembly)
## Location: D:\GitHub\David-OS\ahk
**Fabel (Opus) | 2026-07-07 rev2 | Supersedes rev1. All source pieces identified; this is assembly, not invention.**

## The verdict that produced this spec
Five sources each solved one piece. Nobody merged them. Overlay v2 is the merge:

| Piece | Source | What it contributes |
|---|---|---|
| Window-attached rendering | `ShinsOverlayClass` (C:\Users\David\Downloads\Compressed\ShinsOverlayClass-main.zip, AHK V2 subfolder) | Direct2D `AttachToWindow(client_area)` — overlay lives in the target window's coordinate space; survives resize/maximize/monitor-drag with ZERO tracking code. GPU-drawn, click-through. |
| Per-AI profiles | `\\192.168.2.50\h_hp\Desktop\pof2828_controller_v3.ahk` | Profile class: {name, proc, title, offR, offB, inpH} — input-box position as offsets from right/bottom edges, re-anchor hotkey, Ctrl+1-5 profile switch. |
| Button bar + input UI | `\\192.168.2.50\h_hp\Desktop\claude_overlay_v2.ahk` | The layout David wants: ghost bar (Copy/New/Artifact/Projects, no-focus-steal E0x08000000), floating multi-line input with Send/Clear/Close. |
| HTTP bridge | `D:\GitHub\David-OS\ahk\overlay\` (rev1, built 07-07) | POST /send port 8765, X-Bridge-Token auth, inbox-file handoff, LAN reachable. Keep listener as-is. |
| Packaging + settings | Blog pattern (Window Center & Resizer, in David's doc drop) | settings.json is THE contract: profiles, keybinds, sizes. Script self-reloads on change. Electron (apps\desk) spawns portable AutoHotkey64.exe from resources — one install. |
| Prompt assembler | `\\192.168.2.50\h_hp\Desktop\prompt_assembler.ahk` | Reference for the command palette (/send /paste /profile). Port commands, not code. |

**EXCLUDED: ShinsMemoryClass.** Memory scanning is for stable game structs; Electron/V8
heap addresses shuffle constantly. Do not attempt memory-read capture. Receive = capture
box (below), UIA investigation is a stretch goal only.

## Build: `overlay\overlay_v2.ahk` (one script + ShinsOverlayClass.ahk as lib)
**LIVE-TEST RESULT 2026-07-07 20:17:03 — v1 delivery mechanics VERIFIED on Claude Desktop:
click-through targeting, clipboard paste, plain Enter sends. Build on that Deliver path.**
0. **David's three core requirements (design authority: David, 07-07 voice session):**
   a. **Window binding** — attach by ahk_exe + window class, NOT screen coords. Overlay
      rides the window through move/resize/minimize/monitor changes.
   b. **Ghost toggle** — one hotkey flips interactive <-> click-through translucent
      (mouse and voice pass through; overlay still visible and API-live).
   c. **Mapping mode** — David clicks "Map", then clicks a real control in the target app
      (send, mic, new-chat...), names it. Stored as window-RELATIVE offsets in
      settings.json keyed by exe/class, with an action per button (click | click+enter |
      paste-here | capture-from-here). Layout auto-loads for every future window of that
      class. API can invoke named buttons: POST /send {"button":"mic","profile":"claude"}.
1. **Anchor**: on profile select (Ctrl+1-5 or /profile), find window by proc/title,
   `AttachToWindow` client area. Input target point = (right-offR, bottom-offB) from
   profile. Re-anchor = Ctrl+Shift+B. Unknown app fallback = rev1 geometric mode
   (overlay position IS the target).
2. **UI** (drawn via Shins DrawText/FillRectangle, hit-tested manually): v2's button
   bar + input box. Buttons: Send, Copy, New, Capture, Profiles. Enter=send,
   Shift+Enter=newline. send_key per profile (enter|ctrl-enter|shift-enter).
3. **Send path**: HTTP /send inbox (rev1 listener unchanged) AND local input box both
   funnel through one Deliver(text, profile): focus target point, clipboard paste,
   length-verify, retry x2, send_key.
4. **Receive path**: capture box — user drags a region over the response area once per
   profile (stored in settings.json). Ctrl+Alt+C or Capture button: select-all within
   region (triple-click + drag or Ctrl+A scoped), copy, POST to hub
   `http://localhost:2828/top-of-mind/messages {source: profile.name, text}`.
5. **Settings**: `overlay\settings.json` — profiles[], keybinds{}, bridge{port,token}.
   FileWatch it; self-reload on change (blog pattern). NO hardcoded values in the script.
6. **Packaging**: `apps\desk` gets a settings editor page writing the same settings.json,
   and Electron main spawns AutoHotkey64.exe + overlay_v2.ahk from resources
   (blog's autohotkey.ts pattern, port it).

## Tests — kill condition (live, demonstrated to David)
- Attach to Claude Desktop; resize, maximize, drag to second monitor — input target
  and buttons stay glued. Repeat on Kimi + GPT desktop.
- 500-word POST /send from another machine lands complete and sends.
- Capture box round-trip: response text appears in hub message stream with source label.
- Edit settings.json by hand -> overlay reloads within 2s, new keybind live.
- Profiles survive script restart. Zero focus steal while typing in other apps.

## Dependencies
Needs hub on 2828 (running). apps\desk settings page can lag the AHK build — don't block on it.

## Priority
Anchor+UI first (this is what David touches daily), send path, settings reload,
capture box, Electron packaging last.
