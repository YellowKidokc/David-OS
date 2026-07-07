; ============================================================
; AI INPUT OVERLAY - David-OS AHK Bridge v1.0
; Fabel (Opus) | 2026-07-07 | AutoHotkey v2 | UNTESTED - first live run pending
;
; WHAT IT DOES
;   A draggable, resizable, always-on-top overlay you park over the
;   input box of ANY Electron AI app (Claude Desktop, Kimi, GPT, etc).
;   It runs a local HTTP API. POST text to it -> it clicks the spot
;   under the overlay, pastes the text, presses Enter. Done.
;
;   The overlay's position IS the target. Move it, resize it, put it
;   on another monitor - whatever is under its center gets the text.
;
; API (shown live on the overlay):
;   POST http://<machine>:8765/send    body: {"text":"...","enters":1}
;   GET  http://<machine>:8765/health
;   LAN access (laptop): first run once as admin:
;     netsh http add urlacl url=http://+:8765/ user=Everyone
;   Token required on /send: header  X-Bridge-Token: davidos-bridge-2026
; ============================================================
#Requires AutoHotkey v2.0
#SingleInstance Force
CoordMode "Mouse", "Screen"

CFG_PORT  := 8765
CFG_TOKEN := "davidos-bridge-2026"
INBOX     := A_ScriptDir "\_inbox"
DirCreate(INBOX)

; ---------- Overlay GUI ----------
ov := Gui("+AlwaysOnTop -Caption +ToolWindow +Resize", "AI Input Overlay")
ov.BackColor := "1a1a2e"
ov.SetFont("s10 cWhite", "Segoe UI")
lbl := ov.Add("Text", "w260 h60 Center vStatus", "AI BRIDGE`nport " CFG_PORT " | idle")
ov.OnEvent("Close", (*) => ExitApp())
ov.Show("w280 h80 x" (A_ScreenWidth-360) " y" (A_ScreenHeight-200))
WinSetTransparent(180, ov.Hwnd)

; drag anywhere on the overlay body
OnMessage(0x201, DragHandler)
DragHandler(wParam, lParam, msg, hwnd) {
    global ov, lbl
    if (hwnd = ov.Hwnd || hwnd = lbl.Hwnd)
        PostMessage(0xA1, 2, 0,, "ahk_id " ov.Hwnd)
}

; right-click menu
ovMenu := Menu()
ovMenu.Add("Send test line", (*) => Deliver("Bridge test " A_Now, 1))
ovMenu.Add("Exit", (*) => ExitApp())
ov.OnEvent("ContextMenu", (*) => ovMenu.Show())

; ---------- Inbox poller: listener writes file -> deliver ----------
SetTimer(CheckInbox, 200)
CheckInbox() {
    global INBOX
    Loop Files INBOX "\*.json" {
        raw := FileRead(A_LoopFileFullPath, "UTF-8")
        FileDelete(A_LoopFileFullPath)
        text := "", enters := 1
        if RegExMatch(raw, '"text"\s*:\s*"((?:[^"\\]|\\.)*)"', &m) {
            text := m[1]
            text := StrReplace(text, '\r\n', "`n")
            text := StrReplace(text, '\n', "`n")
            text := StrReplace(text, '\"', '"')
            text := StrReplace(text, '\\', '\')
        }
        if RegExMatch(raw, '"enters"\s*:\s*(\d+)', &e)
            enters := Integer(e[1])
        if (text != "")
            Deliver(text, enters)
    }
}

; ---------- Delivery: click under overlay center, paste, enter ----------
Deliver(text, enters := 1) {
    global ov, lbl, CFG_PORT
    lbl.Text := "AI BRIDGE`nport " CFG_PORT " | SENDING"
    ov.GetPos(&ox, &oy, &ow, &oh)
    cx := ox + ow//2, cy := oy + oh//2
    WinSetTransparent(0, ov.Hwnd)                  ; ghost the overlay so the click lands beneath
    Sleep 60
    pt := (cy << 32) | (cx & 0xFFFFFFFF)
    target := DllCall("WindowFromPoint", "Int64", pt, "Ptr")
    root := DllCall("GetAncestor", "Ptr", target, "UInt", 2, "Ptr")   ; GA_ROOT
    WinActivate("ahk_id " root)
    WinWaitActive("ahk_id " root,, 2)
    Click cx, cy
    Sleep 120
    saved := ClipboardAll()
    A_Clipboard := text
    ClipWait(1)
    Send "^v"
    Sleep 150 + Min(StrLen(text), 2000)//4         ; settle time scales with paste size
    Loop enters {
        Send "{Enter}"
        Sleep 120
    }
    A_Clipboard := saved
    WinSetTransparent(180, ov.Hwnd)
    lbl.Text := "AI BRIDGE`nport " CFG_PORT " | idle | last " FormatTime(, "HH:mm:ss")
}
