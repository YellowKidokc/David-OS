; ─────────────────────────────────────────────────────────────────────────────
; claude_overlay.ahk
; Ghost overlay for Claude.ai / browser
; Sits over your browser — always on top, no taskbar icon, no focus steal.
; Buttons fire actions on the browser without pulling you away from it.
;
; HOW TO USE:
;   1. Open Claude.ai in Chrome/Edge
;   2. Run this script
;   3. Tiny button bar appears — click any button
;   4. Press Ctrl+Shift+H to toggle show/hide overlay
;   5. Press Ctrl+Shift+Q to quit
;
; POSITION: Top-right of screen by default. Drag to reposition.
; ─────────────────────────────────────────────────────────────────────────────

#NoEnv
#SingleInstance Force
#NoTrayIcon
SetWinDelay, 0
SendMode Input

; ── Config ────────────────────────────────────────────────────────────────────
OVERLAY_W  := 220   ; Width of overlay bar
OVERLAY_H  := 32    ; Height (single row of buttons)
OPACITY    := 220   ; 0=invisible, 255=solid. 220 = mostly visible
BTN_H      := 24
BTN_W      := 50

; Position: top-right corner, small margin from edge
SysGet, ScreenW, 78   ; SM_CXVIRTUALSCREEN
SysGet, ScreenH, 79
StartX := ScreenW - OVERLAY_W - 10
StartY := 10

; ── Build GUI ─────────────────────────────────────────────────────────────────
Gui, Overlay:New, +AlwaysOnTop -Caption +ToolWindow +LastFound +E0x08000000
; +E0x08000000 = WS_EX_NOACTIVATE — clicking buttons won't steal focus from browser

Gui, Overlay:Color, 1A1A2E   ; Dark navy background
WinSet, Transparent, %OPACITY%

; Buttons — add/remove/rename freely
Gui, Overlay:Add, Button, x2   y4 w%BTN_W% h%BTN_H% gDoCopy,     Copy
Gui, Overlay:Add, Button, x54  y4 w%BTN_W% h%BTN_H% gDoNewChat,  New
Gui, Overlay:Add, Button, x106 y4 w%BTN_W% h%BTN_H% gDoArtifact, Artifact
Gui, Overlay:Add, Button, x158 y4 w%BTN_W% h%BTN_H% gDoProjects, Projects

Gui, Overlay:Show, x%StartX% y%StartY% w%OVERLAY_W% h%OVERLAY_H% NoActivate, ClaudeOverlay
WinSet, AlwaysOnTop, On, ClaudeOverlay ahk_class AutoHotkeyGUI

; ── Hotkeys ───────────────────────────────────────────────────────────────────
^+h::Gosub, ToggleOverlay   ; Ctrl+Shift+H = hide/show
^+q::ExitApp                ; Ctrl+Shift+Q = quit

; ── Button Actions ────────────────────────────────────────────────────────────

DoCopy:
    ; Click the Copy button on the last artifact in Claude.ai
    ; Sends Ctrl+C after briefly focusing the browser
    WinActivate, ahk_exe chrome.exe
    Sleep, 80
    Send ^c
    WinActivate, ClaudeOverlay ahk_class AutoHotkeyGUI
Return

DoNewChat:
    ; Open a new Claude chat — Ctrl+Shift+O is Claude's new chat shortcut
    WinActivate, ahk_exe chrome.exe
    Sleep, 80
    Send ^+o
    Sleep, 100
    WinActivate, ClaudeOverlay ahk_class AutoHotkeyGUI
Return

DoArtifact:
    ; Toggle artifact panel — adjust key combo to match actual Claude shortcut
    WinActivate, ahk_exe chrome.exe
    Sleep, 80
    Send ^+a
    Sleep, 100
    WinActivate, ClaudeOverlay ahk_class AutoHotkeyGUI
Return

DoProjects:
    ; Navigate to Projects — adjust URL or shortcut as needed
    WinActivate, ahk_exe chrome.exe
    Sleep, 80
    Send ^l                          ; Focus address bar
    Sleep, 80
    Send claude.ai/projects{Enter}
    Sleep, 100
    WinActivate, ClaudeOverlay ahk_class AutoHotkeyGUI
Return

; ── Toggle visibility ─────────────────────────────────────────────────────────
ToggleOverlay:
    Gui, Overlay:Show, Toggle
Return

; ── Allow dragging the overlay ────────────────────────────────────────────────
OverlayGuiClick:
    PostMessage, 0xA1, 2,,, A   ; WM_NCLBUTTONDOWN — lets user drag titleless window
Return

OverlayGuiClose:
OverlayGuiEscape:
    ExitApp
Return
