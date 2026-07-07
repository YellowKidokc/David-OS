; ============================================================
; AI Chat Controller — AutoHotkey v2
; Window-anchored overlay with per-app profiles.
; Follows the target window, docks near its chat input.
;
; PROFILES: Claude, Kimi, Codex, TypingMind, GPT
; Switch with Ctrl+1 through Ctrl+5, or click the profile bar.
;
; HOTKEYS:
;   Ctrl+Shift+V  — Paste clipboard into chat + send
;   Ctrl+Shift+R  — Pull latest file from File Drop API → clipboard
;   Ctrl+Shift+S  — Send (Enter)
;   Ctrl+Shift+M  — Click mic/voice area
;   Ctrl+Shift+P  — Push clipboard → File Drop API as .md
;   Ctrl+Shift+B  — Recalibrate: re-anchor to current window
;   Ctrl+1-5      — Switch profile
;   Ctrl+Shift+Q  — Quit
; ============================================================

#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; ── CONFIG ──────────────────────────────────────────────────
FILE_DROP_URL := "http://localhost:8100/file-drop"
SOURCE_NAME  := "claude-ahk"
FOLLOW_INTERVAL := 100  ; ms

; ── APP PROFILES ────────────────────────────────────────────
; Each profile: [processName, windowTitle, xOffsetFromRight, yOffsetFromBottom, inputWidth, inputHeight]
; Offsets are measured FROM the bottom-right of the target window
; so they survive resizes reasonably well.

class Profile {
    __New(name, proc, title, offR, offB, inpW, inpH) {
        this.name  := name
        this.proc  := proc      ; ahk_exe match
        this.title := title     ; window title substring
        this.offR  := offR      ; overlay X = winX + winW - offR
        this.offB  := offB      ; overlay Y = winY + winH - offB
        this.inpW  := inpW      ; approximate input box width
        this.inpH  := inpH      ; approximate input box height
        this.hwnd  := 0
    }
}

profiles := [
    Profile("Claude",     "chrome.exe",    "Claude",      500, 180, 600, 50),
    Profile("Kimi",       "kimi.exe",      "Kimi",        500, 180, 600, 50),
    Profile("Codex",      "Codex.exe",     "Codex",       500, 160, 700, 110),
    Profile("TypingMind", "chrome.exe",    "TypingMind",   500, 180, 600, 50),
    Profile("GPT",        "chrome.exe",    "ChatGPT",     500, 180, 600, 50),
]

activeIdx := 1
activeProfile := profiles[activeIdx]
isAnchored := false
anchorHwnd := 0

; ── OVERLAY GUI ─────────────────────────────────────────────
g := Gui("+AlwaysOnTop +ToolWindow -Caption +Border")
g.BackColor := "1a1e26"
g.MarginX := 6
g.MarginY := 4

; Profile selector row
g.SetFont("s8 Bold c" "d9a441", "Segoe UI")
profileLabel := g.Add("Text", "x6 y4 w50 h18", "App:")

g.SetFont("s8 c" "e9e6dd", "Segoe UI")
profileBtns := []
xPos := 56
for idx, p in profiles {
    btn := g.Add("Button", "x" xPos " y2 w55 h20", p.name)
    btn.OnEvent("Click", MakeProfileSwitcher(idx))
    profileBtns.Push(btn)
    xPos += 57
}

; Status / anchor info
g.SetFont("s7 c" "5fb3ae", "Consolas")
anchorLabel := g.Add("Text", "x6 y24 w330 h14", "Not anchored — press Ctrl+Shift+B or click a profile")

; Separator
g.SetFont("s1 c" "2c3240")
g.Add("Text", "x6 y39 w330 h1 +0x10")  ; SS_ETCHEDHORZ

; Action buttons
g.SetFont("s9 c" "e9e6dd", "Segoe UI")
btnPaste  := g.Add("Button", "x6   y44 w105 h30", "📋 Paste+Send")
btnVoice  := g.Add("Button", "x115 y44 w105 h30", "🎤 Voice")
btnPull   := g.Add("Button", "x224 y44 w105 h30", "📥 Pull File")

btnPush   := g.Add("Button", "x6   y78 w105 h30", "📤 Push Clip")
btnSend   := g.Add("Button", "x115 y78 w105 h30", "▶ Send")
btnCalib  := g.Add("Button", "x224 y78 w105 h30", "🎯 Anchor")

; Bottom status
g.SetFont("s7 c" "9aa1b0", "Consolas")
status := g.Add("Text", "x6 y112 w325 h14", "Ready. Ctrl+1-5 = profiles. Ctrl+Shift+B = anchor.")

btnPaste.OnEvent("Click", DoPasteSend)
btnVoice.OnEvent("Click", DoVoice)
btnPull.OnEvent("Click", DoPullFile)
btnPush.OnEvent("Click", DoPushClip)
btnSend.OnEvent("Click", DoSend)
btnCalib.OnEvent("Click", DoCalibrate)

g.OnEvent("Close", DoQuit)
g.Title := "AI Chat Controller"
g.Show("w336 h130 x100 y100")

; Allow dragging by clicking anywhere
OnMessage(0x0201, WM_LBUTTONDOWN)
WM_LBUTTONDOWN(wParam, lParam, msg, hwnd) {
    if (hwnd = g.Hwnd)
        PostMessage(0xA1, 2, 0, , g.Hwnd)
}

; ── FOLLOW TIMER ────────────────────────────────────────────
SetTimer(FollowTarget, FOLLOW_INTERVAL)

FollowTarget() {
    global isAnchored, anchorHwnd, activeProfile, g

    if !isAnchored
        return

    ; Check if anchor window still exists
    if !WinExist("ahk_id " anchorHwnd) {
        isAnchored := false
        anchorLabel.Text := "⚠ Window lost — click profile or Ctrl+Shift+B"
        return
    }

    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        ; Position overlay relative to bottom-right of target
        newX := wx + ww - activeProfile.offR
        newY := wy + wh - activeProfile.offB
        g.Move(newX, newY)
    }
}

; ── PROFILE SWITCHING ───────────────────────────────────────

MakeProfileSwitcher(idx) {
    return (*) => SwitchProfile(idx)
}

SwitchProfile(idx) {
    global activeIdx, activeProfile, isAnchored, anchorHwnd

    activeIdx := idx
    activeProfile := profiles[idx]

    ; Highlight active button
    for i, btn in profileBtns {
        if (i = idx)
            btn.Opt("Background" "2c3240")
        else
            btn.Opt("BackgroundDefault")
    }

    ; Try to find the window
    TryAnchor()
    SetStatus(activeProfile.name " selected.")
}

TryAnchor() {
    global activeProfile, isAnchored, anchorHwnd

    ; Try by title first, then by process
    hwnd := 0
    if (activeProfile.title != "") {
        try hwnd := WinExist(activeProfile.title)
    }
    if (!hwnd && activeProfile.proc != "") {
        try hwnd := WinExist("ahk_exe " activeProfile.proc)
    }

    if hwnd {
        anchorHwnd := hwnd
        isAnchored := true
        try {
            WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " hwnd)
            anchorLabel.Text := "🔗 Anchored: " activeProfile.name " (" ww "x" wh ")"
        }
    } else {
        isAnchored := false
        anchorLabel.Text := "⚠ " activeProfile.name " window not found"
    }
}

; ── HOTKEYS ─────────────────────────────────────────────────
^+v::DoPasteSend()
^+r::DoPullFile()
^+s::DoSend()
^+m::DoVoice()
^+p::DoPushClip()
^+b::DoCalibrate()
^+q::DoQuit()

^1::SwitchProfile(1)
^2::SwitchProfile(2)
^3::SwitchProfile(3)
^4::SwitchProfile(4)
^5::SwitchProfile(5)

; ── ACTIONS ─────────────────────────────────────────────────

SetStatus(msg) {
    status.Text := msg
}

ActivateTarget() {
    global anchorHwnd, isAnchored
    if isAnchored && WinExist("ahk_id " anchorHwnd) {
        WinActivate("ahk_id " anchorHwnd)
        Sleep(150)
    }
}

ClickInputArea() {
    ; Click in the approximate input box area of the target window
    global anchorHwnd, activeProfile
    if !anchorHwnd
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        ; Input box is near bottom center
        clickX := wx + (ww // 2)
        clickY := wy + wh - (activeProfile.inpH + 30)
        Click(clickX, clickY)
        Sleep(100)
    }
}

DoPasteSend(*) {
    SetStatus("Pasting + sending...")
    ActivateTarget()
    ClickInputArea()
    Send("^v")
    Sleep(300)
    Send("{Enter}")
    SetStatus("Sent clipboard content.")
}

DoSend(*) {
    SetStatus("Sending...")
    ActivateTarget()
    Send("{Enter}")
    SetStatus("Sent.")
}

DoVoice(*) {
    SetStatus("Toggling voice...")
    ActivateTarget()
    global anchorHwnd, activeProfile
    if !anchorHwnd
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        ; Mic icon is typically near bottom-right of input bar
        clickX := wx + ww - 60
        clickY := wy + wh - 45
        Click(clickX, clickY)
        SetStatus("Clicked mic area.")
    }
}

DoCalibrate(*) {
    SetStatus("Calibrating...")
    TryAnchor()
}

DoPullFile(*) {
    SetStatus("Pulling from File Drop...")
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", FILE_DROP_URL "/list?limit=1", false)
        whr.Send()
        resp := whr.ResponseText

        if RegExMatch(resp, '"path"\s*:\s*"([^"]+)"', &m) {
            filePath := m[1]
            body := '{"path":"' filePath '"}'
            whr2 := ComObject("WinHttp.WinHttpRequest.5.1")
            whr2.Open("POST", FILE_DROP_URL "/read", false)
            whr2.SetRequestHeader("Content-Type", "application/json")
            whr2.Send(body)
            resp2 := whr2.ResponseText

            if RegExMatch(resp2, '"content"\s*:\s*"([\s\S]*?)"(?=\s*,\s*"size)', &m2) {
                content := m2[1]
                content := StrReplace(content, "\n", "`n")
                content := StrReplace(content, "\t", "`t")
                content := StrReplace(content, '\"', '"')
                A_Clipboard := content
                SetStatus("📥 " filePath " → clipboard. Ctrl+V to paste.")
            } else {
                A_Clipboard := resp2
                SetStatus("📥 Raw response → clipboard.")
            }
        } else {
            SetStatus("No files in drop folder.")
        }
    } catch as e {
        SetStatus("❌ " e.Message)
    }
}

DoPushClip(*) {
    SetStatus("Pushing clipboard...")
    try {
        content := A_Clipboard
        if (content = "") {
            SetStatus("Clipboard empty.")
            return
        }
        content := StrReplace(content, '\', '\\')
        content := StrReplace(content, '"', '\"')
        content := StrReplace(content, "`n", '\n')
        content := StrReplace(content, "`r", '')
        content := StrReplace(content, "`t", '\t')

        ts := FormatTime(, "yyyyMMdd_HHmmss")
        filename := "clip_" ts ".md"

        body := '{"filename":"' filename '","content":"' content '","source":"' SOURCE_NAME '"}'

        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", FILE_DROP_URL "/create", false)
        whr.SetRequestHeader("Content-Type", "application/json")
        whr.Send(body)

        SetStatus("📤 Pushed: " filename)
    } catch as e {
        SetStatus("❌ " e.Message)
    }
}

DoQuit(*) {
    ExitApp()
}
