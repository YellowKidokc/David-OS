; ============================================================
; AI Chat Controller v2 — AutoHotkey v2
; Window-anchored overlay with per-app profiles,
; auto-scroll, and a command line.
;
; PROFILES: Claude, Kimi, Codex, TypingMind, GPT (Ctrl+1-5)
;
; HOTKEYS:
;   Ctrl+Shift+V  — Paste clipboard into chat + send
;   Ctrl+Shift+R  — Pull latest file from File Drop API
;   Ctrl+Shift+S  — Send (Enter)
;   Ctrl+Shift+M  — Click mic/voice area
;   Ctrl+Shift+P  — Push clipboard → File Drop API
;   Ctrl+Shift+B  — Recalibrate anchor
;   Ctrl+Shift+A  — Toggle auto-scroll
;   Ctrl+Shift+Q  — Quit
;   Ctrl+1-5      — Switch profile
;
; COMMAND LINE (type in the box at bottom):
;   /send <text>     — Type text into chat + send
;   /paste            — Paste clipboard into chat
;   /push <text>      — Push text to File Drop API as .md
;   /pull             — Pull latest file from drop → clipboard
;   /scroll           — Toggle auto-scroll
;   /speed <n>        — Set scroll speed (1=slow, 10=fast)
;   /profile <1-5>    — Switch profile
;   /anchor           — Recalibrate
;   /mic              — Toggle voice
;   /shell <cmd>      — Run a shell command, result → clipboard
;   /api <json>       — POST raw JSON to File Drop /create
;   /list             — List files in drop folder → clipboard
;   /quit             — Exit
; ============================================================

#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; ── CONFIG ──────────────────────────────────────────────────
FILE_DROP_URL := "http://localhost:8100/file-drop"
SOURCE_NAME  := "ahk-controller"
FOLLOW_INTERVAL := 100
SCROLL_INTERVAL := 80
scrollSpeed := 3  ; lines per tick
isScrolling := false

; ── APP PROFILES ────────────────────────────────────────────
class Profile {
    __New(name, proc, title, offR, offB, inpW, inpH) {
        this.name  := name
        this.proc  := proc
        this.title := title
        this.offR  := offR
        this.offB  := offB
        this.inpW  := inpW
        this.inpH  := inpH
    }
}

profiles := [
    Profile("Claude",     "chrome.exe",  "Claude",      420, 220, 600, 50),
    Profile("Kimi",       "kimi.exe",    "Kimi",        420, 220, 600, 50),
    Profile("Codex",      "Codex.exe",   "Codex",       420, 200, 700, 110),
    Profile("TypingMind", "chrome.exe",  "TypingMind",  420, 220, 600, 50),
    Profile("GPT",        "chrome.exe",  "ChatGPT",     420, 220, 600, 50),
]

activeIdx := 1
activeProfile := profiles[activeIdx]
isAnchored := false
anchorHwnd := 0

; ── GUI ─────────────────────────────────────────────────────
g := Gui("+AlwaysOnTop +ToolWindow -Caption +Border")
g.BackColor := "14171e"
g.MarginX := 5
g.MarginY := 3

; ── Row 1: Profile buttons ──
g.SetFont("s7 Bold c" "d9a441", "Consolas")
g.Add("Text", "x5 y3 w30 h16", "APP:")

g.SetFont("s7 c" "e9e6dd", "Consolas")
profileBtns := []
xp := 38
for idx, p in profiles {
    btn := g.Add("Button", "x" xp " y1 w50 h18", p.name)
    btn.OnEvent("Click", MakeProfileSwitcher(idx))
    profileBtns.Push(btn)
    xp += 52
}

; ── Row 2: Anchor status ──
g.SetFont("s7 c" "5fb3ae", "Consolas")
anchorLabel := g.Add("Text", "x5 y20 w290 h13", "Not anchored — Ctrl+Shift+B")

; ── Row 3: Action buttons ──
g.SetFont("s8 c" "e9e6dd", "Segoe UI")
y3 := 35
btnPaste  := g.Add("Button", "x5   y" y3 " w65 h26", "📋Paste")
btnSend   := g.Add("Button", "x73  y" y3 " w55 h26", "▶Send")
btnPull   := g.Add("Button", "x131 y" y3 " w55 h26", "📥Pull")
btnPush   := g.Add("Button", "x189 y" y3 " w55 h26", "📤Push")
btnMic    := g.Add("Button", "x247 y" y3 " w40 h26", "🎤")

; ── Row 4: Scroll + Anchor ──
y4 := 63
btnScroll := g.Add("Button", "x5   y" y4 " w90 h26", "⏬ AutoScroll")
g.SetFont("s7 c" "9aa1b0", "Consolas")
g.Add("Text", "x100 y" (y4+6) " w30 h16", "Spd:")
speedCtrl := g.Add("Edit", "x132 y" (y4+3) " w30 h20 Number Center", String(scrollSpeed))
speedCtrl.SetFont("s7 c" "e9e6dd", "Consolas")
btnCalib  := g.Add("Button", "x170 y" y4 " w60 h26", "🎯Anchor")
btnQuit   := g.Add("Button", "x237 y" y4 " w50 h26", "✕Quit")

; ── Row 5: Command line ──
y5 := 93
g.SetFont("s7 c" "d9a441", "Consolas")
g.Add("Text", "x5 y" (y5+3) " w12 h16", ">")
g.SetFont("s8 c" "e9e6dd", "Consolas")
cmdInput := g.Add("Edit", "x18 y" y5 " w250 h22 Background" "1a1e26", "")
g.SetFont("s8 c" "e9e6dd", "Segoe UI")
btnRun := g.Add("Button", "x272 y" y5 " w20 h22", "↵")

; ── Row 6: Status ──
g.SetFont("s6 c" "6a7080", "Consolas")
status := g.Add("Text", "x5 y118 w285 h12", "Ready. Type /help in the command line.")

; ── Wire events ─────────────────────────────────────────────
btnPaste.OnEvent("Click", DoPasteSend)
btnSend.OnEvent("Click", DoSend)
btnPull.OnEvent("Click", DoPullFile)
btnPush.OnEvent("Click", DoPushClip)
btnMic.OnEvent("Click", DoVoice)
btnScroll.OnEvent("Click", DoToggleScroll)
btnCalib.OnEvent("Click", DoCalibrate)
btnQuit.OnEvent("Click", DoQuit)
btnRun.OnEvent("Click", DoRunCmd)

speedCtrl.OnEvent("Change", DoSpeedChange)

g.OnEvent("Close", DoQuit)
g.Title := "AI Chat Controller"
g.Show("w298 h133 x100 y100")

; Draggable
OnMessage(0x0201, WM_LBUTTONDOWN)
WM_LBUTTONDOWN(wParam, lParam, msg, hwnd) {
    if (hwnd = g.Hwnd)
        PostMessage(0xA1, 2, 0, , g.Hwnd)
}

; Enter key in command line triggers run
cmdInput.OnEvent("Change", (*) => 0)  ; placeholder
OnMessage(0x0100, OnKeyDown)
OnKeyDown(wParam, lParam, msg, hwnd) {
    if (hwnd = cmdInput.Hwnd && wParam = 13) {  ; VK_RETURN
        DoRunCmd()
        return 0
    }
}

; ── TIMERS ──────────────────────────────────────────────────
SetTimer(FollowTarget, FOLLOW_INTERVAL)

FollowTarget() {
    global isAnchored, anchorHwnd, activeProfile, g
    if !isAnchored
        return
    if !WinExist("ahk_id " anchorHwnd) {
        isAnchored := false
        anchorLabel.Text := "⚠ Window lost"
        return
    }
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        newX := wx + ww - activeProfile.offR
        newY := wy + wh - activeProfile.offB
        g.Move(newX, newY)
    }
}

DoAutoScroll() {
    global isScrolling, scrollSpeed, anchorHwnd, isAnchored
    if !isScrolling
        return
    if isAnchored && WinExist("ahk_id " anchorHwnd) {
        try WinActivate("ahk_id " anchorHwnd)
        ; Scroll down by sending mouse wheel
        loop scrollSpeed
            Send("{WheelDown}")
    }
}

; ── PROFILE SWITCHING ───────────────────────────────────────
MakeProfileSwitcher(idx) {
    return (*) => SwitchProfile(idx)
}

SwitchProfile(idx) {
    global activeIdx, activeProfile
    activeIdx := idx
    activeProfile := profiles[idx]
    for i, btn in profileBtns {
        if (i = idx)
            btn.Opt("Background" "2c3240")
        else
            btn.Opt("BackgroundDefault")
    }
    TryAnchor()
    SetStatus(activeProfile.name " active")
}

TryAnchor() {
    global activeProfile, isAnchored, anchorHwnd
    hwnd := 0
    if (activeProfile.title != "")
        try hwnd := WinExist(activeProfile.title)
    if (!hwnd && activeProfile.proc != "")
        try hwnd := WinExist("ahk_exe " activeProfile.proc)
    if hwnd {
        anchorHwnd := hwnd
        isAnchored := true
        try {
            WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " hwnd)
            anchorLabel.Text := "🔗 " activeProfile.name " (" ww "x" wh ")"
        }
    } else {
        isAnchored := false
        anchorLabel.Text := "⚠ " activeProfile.name " not found"
    }
}

; ── HOTKEYS ─────────────────────────────────────────────────
^+v::DoPasteSend()
^+r::DoPullFile()
^+s::DoSend()
^+m::DoVoice()
^+p::DoPushClip()
^+b::DoCalibrate()
^+a::DoToggleScroll()
^+q::DoQuit()
^1::SwitchProfile(1)
^2::SwitchProfile(2)
^3::SwitchProfile(3)
^4::SwitchProfile(4)
^5::SwitchProfile(5)

; ── ACTION FUNCTIONS ────────────────────────────────────────
SetStatus(msg) {
    status.Text := SubStr(msg, 1, 60)
}

ActivateTarget() {
    global anchorHwnd, isAnchored
    if isAnchored && WinExist("ahk_id " anchorHwnd) {
        WinActivate("ahk_id " anchorHwnd)
        Sleep(150)
    }
}

ClickInputArea() {
    global anchorHwnd, activeProfile
    if !anchorHwnd
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
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
    SetStatus("Sent clipboard.")
}

DoSend(*) {
    ActivateTarget()
    Send("{Enter}")
    SetStatus("Sent.")
}

DoVoice(*) {
    ActivateTarget()
    global anchorHwnd
    if !anchorHwnd
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        Click(wx + ww - 60, wy + wh - 45)
        SetStatus("Clicked mic.")
    }
}

DoCalibrate(*) {
    TryAnchor()
}

DoToggleScroll(*) {
    global isScrolling
    isScrolling := !isScrolling
    if isScrolling {
        SetTimer(DoAutoScroll, SCROLL_INTERVAL)
        btnScroll.Text := "⏸ Stop Scroll"
        SetStatus("Auto-scrolling ON (speed " scrollSpeed ")")
    } else {
        SetTimer(DoAutoScroll, 0)
        btnScroll.Text := "⏬ AutoScroll"
        SetStatus("Auto-scroll OFF")
    }
}

DoSpeedChange(*) {
    global scrollSpeed
    val := speedCtrl.Value
    if (val != "" && IsInteger(val) && val > 0 && val <= 20)
        scrollSpeed := Integer(val)
}

; ── FILE DROP API ───────────────────────────────────────────
DoPullFile(*) {
    SetStatus("Pulling...")
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", FILE_DROP_URL "/list?limit=1", false)
        whr.Send()
        resp := whr.ResponseText
        if RegExMatch(resp, '"path"\s*:\s*"([^"]+)"', &m) {
            body := '{"path":"' m[1] '"}'
            whr2 := ComObject("WinHttp.WinHttpRequest.5.1")
            whr2.Open("POST", FILE_DROP_URL "/read", false)
            whr2.SetRequestHeader("Content-Type", "application/json")
            whr2.Send(body)
            A_Clipboard := whr2.ResponseText
            SetStatus("📥 " m[1] " → clip")
        } else {
            SetStatus("No files.")
        }
    } catch as e {
        SetStatus("❌ " e.Message)
    }
}

DoPushClip(*) {
    SetStatus("Pushing...")
    try {
        content := A_Clipboard
        if (content = "") {
            SetStatus("Clipboard empty.")
            return
        }
        DoAPIPush(content, "clip_" FormatTime(, "yyyyMMdd_HHmmss") ".md")
    } catch as e {
        SetStatus("❌ " e.Message)
    }
}

DoAPIPush(content, filename, source := "") {
    global SOURCE_NAME, FILE_DROP_URL
    if (source = "")
        source := SOURCE_NAME
    content := StrReplace(content, '\', '\\')
    content := StrReplace(content, '"', '\"')
    content := StrReplace(content, "`n", '\n')
    content := StrReplace(content, "`r", '')
    content := StrReplace(content, "`t", '\t')
    body := '{"filename":"' filename '","content":"' content '","source":"' source '"}'
    whr := ComObject("WinHttp.WinHttpRequest.5.1")
    whr.Open("POST", FILE_DROP_URL "/create", false)
    whr.SetRequestHeader("Content-Type", "application/json")
    whr.Send(body)
    SetStatus("📤 " filename)
}

; ── COMMAND LINE PROCESSOR ──────────────────────────────────
DoRunCmd(*) {
    global cmdInput
    raw := Trim(cmdInput.Value)
    if (raw = "")
        return
    cmdInput.Value := ""

    ; Parse command
    if (SubStr(raw, 1, 1) != "/") {
        ; No slash = just type it into the chat
        A_Clipboard := raw
        DoPasteSend()
        return
    }

    parts := StrSplit(raw, " ", , 2)
    cmd := StrLower(parts[1])
    arg := (parts.Length > 1) ? parts[2] : ""

    switch cmd {
        case "/send":
            if (arg != "") {
                A_Clipboard := arg
                DoPasteSend()
            } else {
                DoSend()
            }

        case "/paste":
            DoPasteSend()

        case "/push":
            if (arg != "") {
                ts := FormatTime(, "yyyyMMdd_HHmmss")
                DoAPIPush(arg, "cmd_" ts ".md")
            } else {
                DoPushClip()
            }

        case "/pull":
            DoPullFile()

        case "/scroll":
            DoToggleScroll()

        case "/speed":
            if (arg != "" && IsInteger(arg)) {
                global scrollSpeed := Integer(arg)
                speedCtrl.Value := arg
                SetStatus("Scroll speed: " arg)
            }

        case "/profile":
            if (arg != "" && IsInteger(arg) && Integer(arg) >= 1 && Integer(arg) <= 5)
                SwitchProfile(Integer(arg))

        case "/anchor":
            DoCalibrate()

        case "/mic":
            DoVoice()

        case "/shell":
            if (arg != "") {
                SetStatus("Running: " SubStr(arg, 1, 40))
                try {
                    shell := ComObject("WScript.Shell")
                    exec := shell.Exec("cmd.exe /c " arg)
                    output := exec.StdOut.ReadAll()
                    A_Clipboard := output
                    SetStatus("Shell done → clipboard (" StrLen(output) " chars)")
                } catch as e {
                    SetStatus("Shell error: " e.Message)
                }
            }

        case "/api":
            if (arg != "") {
                try {
                    whr := ComObject("WinHttp.WinHttpRequest.5.1")
                    whr.Open("POST", FILE_DROP_URL "/create", false)
                    whr.SetRequestHeader("Content-Type", "application/json")
                    whr.Send(arg)
                    SetStatus("API: " SubStr(whr.ResponseText, 1, 50))
                } catch as e {
                    SetStatus("API error: " e.Message)
                }
            }

        case "/list":
            try {
                whr := ComObject("WinHttp.WinHttpRequest.5.1")
                whr.Open("GET", FILE_DROP_URL "/list?limit=20", false)
                whr.Send()
                A_Clipboard := whr.ResponseText
                SetStatus("File list → clipboard")
            } catch as e {
                SetStatus("❌ " e.Message)
            }

        case "/help":
            help := "/send /paste /push /pull /scroll /speed /profile /anchor /mic /shell /api /list /quit"
            SetStatus(help)

        case "/quit":
            DoQuit()

        default:
            SetStatus("Unknown: " cmd " — try /help")
    }
}

DoQuit(*) {
    ExitApp()
}
