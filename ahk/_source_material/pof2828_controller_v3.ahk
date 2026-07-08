#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; ============================================================
; POF 2828 — UNIFIED AI CHAT CONTROLLER v3
; Merges claude_chat_controller + ai_chat_controller
; Adds: Multi-AI Task Coordinator (Win+T)
; Adds: Prompt Assembler bridge (Win+P)
; 
; CORE HOTKEYS:
;   Ctrl+Shift+V  — Paste clipboard into chat + send
;   Ctrl+Shift+S  — Send (Enter only)
;   Ctrl+Shift+M  — Click mic/voice
;   Ctrl+Shift+B  — Re-anchor to current window
;   Ctrl+Shift+A  — Toggle auto-scroll
;   Ctrl+Shift+Q  — Quit
;   Ctrl+1-5      — Switch AI profile
;   Win+T         — Open Task Coordinator
;   Win+C         — Open main controller
;
; FILE DROP (optional — works without it for basic ops):
;   Ctrl+Shift+R  — Pull latest file → clipboard
;   Ctrl+Shift+P  — Push clipboard → drop
;
; COMMAND LINE (type in box, Enter to run):
;   /send <text>  /paste  /push  /pull
;   /scroll       /speed <n>
;   /profile <1-5>
;   /shell <cmd>  /help
; ============================================================

; ── CONFIG ──────────────────────────────────────────────────
FILE_DROP_URL  := "http://localhost:8100/file-drop"
FIS_HUB_URL    := "http://127.0.0.1:10000"
COMMS_URL      := "https://comms.dlowehomelab.com"
COMMS_TOKEN    := "theophysics-opus-2026"
SOURCE_NAME    := "ahk-controller"
FOLLOW_MS      := 100
SCROLL_MS      := 80

; ── AI PROFILES ─────────────────────────────────────────────
class Profile {
    __New(name, proc, title, offR, offB, inpH) {
        this.name := name
        this.proc := proc
        this.title := title
        this.offR := offR
        this.offB := offB
        this.inpH := inpH
    }
}

profiles := [
    Profile("Claude",     "chrome.exe",  "Claude",      420, 180, 50),
    Profile("GPT",        "chrome.exe",  "ChatGPT",     420, 180, 50),
    Profile("Codex",      "Codex.exe",   "Codex",       420, 160, 110),
    Profile("Kimi",       "kimi.exe",    "Kimi",        420, 180, 50),
    Profile("Gemini",     "chrome.exe",  "Gemini",      420, 180, 50),
]

activeIdx     := 1
activeProfile := profiles[activeIdx]
isAnchored    := false
anchorHwnd    := 0
isScrolling   := false
scrollSpeed   := 3

; ============================================================
; MAIN CONTROLLER GUI
; ============================================================
BuildMainGUI() {
    global g, anchorLabel, status, cmdInput, profileBtns, speedCtrl, btnScroll

    g := Gui("+AlwaysOnTop +ToolWindow -Caption +Border")
    g.BackColor := "14171e"

    ; ── Profile row ─────────────────────────────────────────
    g.SetFont("s7 Bold cD9A441", "Consolas")
    g.AddText("x5 y3 w30 h16", "AI:")
    g.SetFont("s7 cE9E6DD", "Consolas")
    profileBtns := []
    xp := 36
    for idx, p in profiles {
        b := g.AddButton("x" xp " y1 w58 h18", p.name)
        b.OnEvent("Click", MakeSwitcher(idx))
        profileBtns.Push(b)
        xp += 60
    }

    ; ── Anchor status ───────────────────────────────────────
    g.SetFont("s7 c5FB3AE", "Consolas")
    anchorLabel := g.AddText("x5 y22 w330 h13", "Not anchored — Ctrl+Shift+B")

    ; ── Row 1 buttons ───────────────────────────────────────
    g.SetFont("s8 cE9E6DD", "Segoe UI")
    g.AddButton("x5   y37 w75 h26", "📋 Paste").OnEvent("Click", DoPasteSend)
    g.AddButton("x83  y37 w60 h26", "▶ Send").OnEvent("Click", DoSend)
    g.AddButton("x146 y37 w65 h26", "🎤 Voice").OnEvent("Click", DoVoice)
    g.AddButton("x214 y37 w60 h26", "📥 Pull").OnEvent("Click", DoPullFile)
    g.AddButton("x277 y37 w60 h26", "📤 Push").OnEvent("Click", DoPushClip)

    ; ── Row 2 buttons ───────────────────────────────────────
    btnScroll := g.AddButton("x5   y66 w90 h26", "⏬ Scroll")
    btnScroll.OnEvent("Click", DoToggleScroll)
    g.SetFont("s7 c9AA1B0", "Consolas")
    g.AddText("x100 y72 w28 h16", "Spd:")
    speedCtrl := g.AddEdit("x130 y69 w28 h20 Number Center", String(scrollSpeed))
    speedCtrl.SetFont("s7 cE9E6DD", "Consolas")
    speedCtrl.OnEvent("Change", DoSpeedChange)
    g.SetFont("s8 cE9E6DD", "Segoe UI")
    g.AddButton("x163 y66 w80 h26", "🎯 Anchor").OnEvent("Click", DoCalibrate)
    g.AddButton("x247 y66 w45 h26", "🔧 Task").OnEvent("Click", (*) => ShowTaskCoord())
    g.AddButton("x295 y66 w42 h26", "✕").OnEvent("Click", DoQuit)

    ; ── Command line ────────────────────────────────────────
    g.SetFont("s7 cD9A441", "Consolas")
    g.AddText("x5 y98 w12 h16", ">")
    g.SetFont("s8 cE9E6DD", "Consolas")
    cmdInput := g.AddEdit("x18 y95 w290 h22 Background1A1E26", "")
    g.SetFont("s8 cE9E6DD", "Segoe UI")
    g.AddButton("x312 y95 w22 h22", "↵").OnEvent("Click", DoRunCmd)

    ; ── Status bar ──────────────────────────────────────────
    g.SetFont("s6 c6A7080", "Consolas")
    status := g.AddText("x5 y120 w330 h12", "Ready — Win+C to show/hide, Win+T = Task Coordinator")

    ; Draggable
    OnMessage(0x0201, WM_LBtn)
    ; Enter in command line
    OnMessage(0x0100, OnKey)

    g.OnEvent("Close", (*) => g.Hide())
    g.Show("w338 h135 x100 y100")
}

WM_LBtn(wParam, lParam, msg, hwnd) {
    global g
    if (hwnd = g.Hwnd)
        PostMessage(0xA1, 2, 0, , g.Hwnd)
}

OnKey(wParam, lParam, msg, hwnd) {
    global cmdInput
    if (hwnd = cmdInput.Hwnd && wParam = 13) {
        DoRunCmd()
        return 0
    }
}

; ============================================================
; TASK COORDINATOR GUI
; Assign folders/blocks to AIs, track completion, route checks
; ============================================================
ShowTaskCoord(*) {
    tc := Gui("+Resize +AlwaysOnTop", "📋 Task Coordinator — POF 2828")
    tc.SetFont("s10", "Segoe UI")
    tc.BackColor := "1a1e2e"

    ; ── Header ──────────────────────────────────────────────
    tc.SetFont("s12 Bold cFFD700", "Segoe UI")
    tc.AddText("x10 y8 w760", "MULTI-AI TASK COORDINATOR")
    tc.SetFont("s8 c808080", "Segoe UI")
    tc.AddText("x10 y30 w760", "Assign work blocks to AIs. They pull from comms hub. Mark done. Route checks.")

    ; ── Project name ────────────────────────────────────────
    tc.SetFont("s9 cFFD700", "Segoe UI")
    tc.AddText("x10 y55 w80 h20", "Project:")
    tc.SetFont("s9 cE9E6DD", "Segoe UI")
    projEdit := tc.AddEdit("x95 y53 w400 h22 Background1A2040", "")

    tc.SetFont("s9 cFFD700", "Segoe UI")
    tc.AddText("x10 y83 w80 h20", "Goal:")
    goalEdit := tc.AddEdit("x95 y80 w660 h22 Background1A2040", "")

    ; ── Work block table ────────────────────────────────────
    tc.SetFont("s9 Bold cFFD700", "Segoe UI")
    tc.AddText("x10 y115 w760", "WORK BLOCKS")

    ; Column headers
    tc.SetFont("s8 Bold c90EE90", "Consolas")
    tc.AddText("x10  y133 w60",  "Block")
    tc.AddText("x75  y133 w200", "Description / Folder")
    tc.AddText("x280 y133 w100", "Assigned AI")
    tc.AddText("x385 y133 w80",  "Status")
    tc.AddText("x470 y133 w100", "Checker AI")
    tc.AddText("x575 y133 w100", "Check Status")

    aiChoices := ["(unassigned)", "Claude", "GPT", "Codex", "Kimi", "Gemini", "Opus", "Sonnet", "Haiku"]
    statusChoices := ["pending", "in-progress", "done", "needs-check", "approved", "blocked"]

    ; 8 work block rows
    blockRows := []
    loop 8 {
        y := 153 + (A_Index - 1) * 28
        row := {}
        row.num  := tc.AddEdit("x10  y" y " w55 h22 Background1A2040 Center", "Block " A_Index)
        row.desc := tc.AddEdit("x70  y" y " w205 h22 Background1A2040", "")
        row.ai   := tc.AddDropDownList("x280 y" y " w95 h22", aiChoices)
        row.stat := tc.AddDropDownList("x380 y" y " w95 h22", statusChoices)
        row.chk  := tc.AddDropDownList("x480 y" y " w95 h22", aiChoices)
        row.chkst := tc.AddDropDownList("x580 y" y " w95 h22", statusChoices)
        blockRows.Push(row)
    }

    ; ── Comms message composer ──────────────────────────────
    tc.SetFont("s9 Bold cFFD700", "Segoe UI")
    tc.AddText("x10 y393 w760", "BROADCAST TO COMMS HUB")
    tc.SetFont("s8 c9AA1B0", "Segoe UI")
    tc.AddText("x10 y411 w760", "Posts task assignment to broadcast channel so all AIs see it.")
    tc.SetFont("s9 cE9E6DD", "Segoe UI")
    msgEdit := tc.AddEdit("x10 y430 w750 h60 Background1A2040 Multi", "")

    ; ── Action buttons ──────────────────────────────────────
    tc.SetFont("s9 cE9E6DD", "Segoe UI")
    btnBuild := tc.AddButton("x10 y500 w180 h30", "🔧 Build Assignment Msg")
    btnPost  := tc.AddButton("x198 y500 w160 h30", "📡 Post to Comms Hub")
    btnCopy  := tc.AddButton("x366 y500 w120 h30", "📋 Copy Message")
    btnSave  := tc.AddButton("x494 y500 w120 h30", "💾 Save Plan")
    btnClose := tc.AddButton("x622 y500 w80 h30", "Close")

    ; ── Status bar ──────────────────────────────────────────
    tc.SetFont("s7 c6A7080", "Consolas")
    tcStatus := tc.AddText("x10 y540 w760 h16", "Ready.")

    ; Wire buttons
    btnBuild.OnEvent("Click", BuildAssignmentMsg.Bind(projEdit, goalEdit, blockRows, msgEdit, tcStatus))
    btnPost.OnEvent("Click", PostToComms.Bind(msgEdit, tcStatus))
    btnCopy.OnEvent("Click", (*) => (A_Clipboard := msgEdit.Value, tcStatus.Text := "Copied."))
    btnSave.OnEvent("Click", SavePlan.Bind(projEdit, goalEdit, blockRows, tcStatus))
    btnClose.OnEvent("Click", (*) => tc.Destroy())

    tc.OnEvent("Close", (*) => tc.Destroy())
    tc.Show("w780 h565")
}

; ── Build the assignment message ────────────────────────────
BuildAssignmentMsg(projEdit, goalEdit, blockRows, msgEdit, tcStatus, *) {
    proj := Trim(projEdit.Value)
    goal := Trim(goalEdit.Value)
    ts   := FormatTime(, "yyyy-MM-dd HH:mm")

    msg := "TASK ASSIGNMENT — " ts "`n"
    msg .= "Project: " (proj ? proj : "(unnamed)") "`n"
    msg .= "Goal: " (goal ? goal : "(not specified)") "`n`n"
    msg .= "WORK BLOCKS:`n"

    for row in blockRows {
        blockName := Trim(row.num.Value)
        desc      := Trim(row.desc.Value)
        ai        := row.ai.Text
        stat      := row.stat.Text
        chk       := row.chk.Text
        chkst     := row.chkst.Text

        if (desc = "" && ai = "(unassigned)")
            continue  ; skip empty rows

        msg .= "  [" blockName "] → " (ai != "(unassigned)" ? ai : "UNASSIGNED")
        if desc
            msg .= " | " desc
        msg .= " | Status: " stat
        if (chk != "(unassigned)")
            msg .= " | Checker: " chk " (" chkst ")"
        msg .= "`n"
    }

    msg .= "`nRULES:`n"
    msg .= "  1. Claim your block by posting to your channel: 'CLAIMED [BlockName]'`n"
    msg .= "  2. When done, post: 'DONE [BlockName] — ready for check'`n"
    msg .= "  3. Checker posts: 'APPROVED [BlockName]' or 'NEEDS-WORK [BlockName]: [reason]'`n"
    msg .= "  4. After your check is approved, move to next available block`n"
    msg .= "  5. All comms go through comms hub — not direct messages to David`n"

    msgEdit.Value := msg
    tcStatus.Text := "Message built — post to comms or copy."
}

; ── Post to comms broadcast ─────────────────────────────────
PostToComms(msgEdit, tcStatus, *) {
    msg := Trim(msgEdit.Value)
    if (msg = "") {
        tcStatus.Text := "Nothing to post."
        return
    }

    ; Escape for JSON
    safe := StrReplace(msg, '\', '\\')
    safe := StrReplace(safe, '"', '\"')
    safe := StrReplace(safe, "`n", '\n')
    safe := StrReplace(safe, "`r", '')
    safe := StrReplace(safe, "`t", '\t')

    body := '{"content":"' safe '","category":"task-assignment","priority":"high"}'

    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", COMMS_URL "/broadcast", false)
        whr.SetRequestHeader("Content-Type", "application/json")
        whr.SetRequestHeader("Authorization", "Bearer " COMMS_TOKEN)
        whr.Send(body)
        resp := whr.ResponseText
        if InStr(resp, '"ok":true') or InStr(resp, '"id"')
            tcStatus.Text := "✅ Posted to comms broadcast."
        else
            tcStatus.Text := "⚠ Response: " SubStr(resp, 1, 80)
    } catch as e {
        tcStatus.Text := "❌ " e.Message
    }
}

; ── Save plan to disk ────────────────────────────────────────
SavePlan(projEdit, goalEdit, blockRows, tcStatus, *) {
    proj := Trim(projEdit.Value)
    safeName := RegExReplace(proj ? proj : "task", "[^\w]", "_")
    ts   := FormatTime(, "yyyyMMdd_HHmmss")
    path := "O:\_Theophysics_v5\David\TASK_PLANS\" ts "_" safeName ".md"

    try DirCreate("O:\_Theophysics_v5\David\TASK_PLANS")

    content := "# Task Plan: " (proj ? proj : "(unnamed)") "`n"
    content .= "Created: " FormatTime(, "yyyy-MM-dd HH:mm") "`n`n"
    content .= "## Goal`n" Trim(goalEdit.Value) "`n`n"
    content .= "## Blocks`n`n"
    content .= "| Block | Description | AI | Status | Checker | Check Status |`n"
    content .= "|-------|-------------|-----|--------|---------|-------------|`n"

    for row in blockRows {
        b := Trim(row.num.Value)
        d := Trim(row.desc.Value)
        if (d = "" && row.ai.Text = "(unassigned)")
            continue
        content .= "| " b " | " d " | " row.ai.Text " | " row.stat.Text
        content .= " | " row.chk.Text " | " row.chkst.Text " |`n"
    }

    try {
        FileAppend(content, path)
        tcStatus.Text := "Saved: " path
    } catch as e {
        tcStatus.Text := "Save failed: " e.Message
    }
}

; ============================================================
; PROFILE + ANCHOR
; ============================================================
MakeSwitcher(idx) => (*) => SwitchProfile(idx)

SwitchProfile(idx) {
    global activeIdx, activeProfile, profileBtns
    activeIdx := idx
    activeProfile := profiles[idx]
    for i, b in profileBtns
        b.Opt(i = idx ? "Background2C3240" : "BackgroundDefault")
    TryAnchor()
    SetStatus(activeProfile.name " active")
}

TryAnchor() {
    global isAnchored, anchorHwnd, activeProfile, anchorLabel
    hwnd := 0
    try hwnd := WinExist(activeProfile.title)
    if !hwnd
        try hwnd := WinExist("ahk_exe " activeProfile.proc)
    if hwnd {
        anchorHwnd := hwnd
        isAnchored := true
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " hwnd)
        anchorLabel.Text := "🔗 " activeProfile.name " (" ww "×" wh ")"
    } else {
        isAnchored := false
        anchorLabel.Text := "⚠ " activeProfile.name " — window not found"
    }
}

SetTimer(FollowTarget, FOLLOW_MS)
FollowTarget() {
    global isAnchored, anchorHwnd, activeProfile, g
    if !isAnchored || !WinExist("ahk_id " anchorHwnd)
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        g.Move(wx + ww - activeProfile.offR, wy + wh - activeProfile.offB)
    }
}

; ============================================================
; CORE ACTIONS
; ============================================================
SetStatus(msg) {
    global status
    status.Text := SubStr(msg, 1, 65)
}

ActivateTarget() {
    global isAnchored, anchorHwnd
    if isAnchored && WinExist("ahk_id " anchorHwnd) {
        WinActivate("ahk_id " anchorHwnd)
        Sleep(150)
    }
}

ClickInput() {
    global anchorHwnd, activeProfile
    if !anchorHwnd
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        Click(wx + ww // 2, wy + wh - (activeProfile.inpH + 30))
        Sleep(100)
    }
}

DoPasteSend(*) {
    SetStatus("Pasting + sending...")
    ActivateTarget()
    ClickInput()
    Send("^v")
    Sleep(300)
    Send("{Enter}")
    SetStatus("Sent.")
}

DoSend(*) {
    ActivateTarget()
    Send("{Enter}")
    SetStatus("Sent.")
}

DoVoice(*) {
    global anchorHwnd
    ActivateTarget()
    if !anchorHwnd
        return
    try {
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_id " anchorHwnd)
        Click(wx + ww - 60, wy + wh - 45)
        SetStatus("Mic clicked.")
    }
}

DoCalibrate(*) {
    TryAnchor()
    SetStatus("Anchor refreshed.")
}

DoToggleScroll(*) {
    global isScrolling, scrollSpeed, btnScroll
    isScrolling := !isScrolling
    if isScrolling {
        SetTimer(DoScroll, SCROLL_MS)
        btnScroll.Text := "⏸ Stop"
        SetStatus("Scrolling ON (speed " scrollSpeed ")")
    } else {
        SetTimer(DoScroll, 0)
        btnScroll.Text := "⏬ Scroll"
        SetStatus("Scrolling OFF")
    }
}

DoScroll() {
    global isScrolling, scrollSpeed, isAnchored, anchorHwnd
    if !isScrolling
        return
    if isAnchored && WinExist("ahk_id " anchorHwnd)
        try { WinActivate("ahk_id " anchorHwnd) ; loop scrollSpeed ; Send("{WheelDown}") }
}

DoSpeedChange(*) {
    global scrollSpeed, speedCtrl
    v := speedCtrl.Value
    if (v != "" && IsInteger(v) && Integer(v) > 0 && Integer(v) <= 20)
        scrollSpeed := Integer(v)
}

DoQuit(*) => ExitApp()

; ── File Drop (graceful fail if service not running) ─────────
DoPullFile(*) {
    SetStatus("Pulling...")
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", FILE_DROP_URL "/list?limit=1", false)
        whr.Send()
        if RegExMatch(whr.ResponseText, '"path"\s*:\s*"([^"]+)"', &m) {
            whr2 := ComObject("WinHttp.WinHttpRequest.5.1")
            whr2.Open("POST", FILE_DROP_URL "/read", false)
            whr2.SetRequestHeader("Content-Type", "application/json")
            whr2.Send('{"path":"' m[1] '"}')
            A_Clipboard := whr2.ResponseText
            SetStatus("📥 " m[1] " → clip")
        } else {
            SetStatus("No files in drop.")
        }
    } catch {
        SetStatus("⚠ File Drop offline — basic paste still works")
    }
}

DoPushClip(*) {
    SetStatus("Pushing...")
    content := A_Clipboard
    if (content = "") { SetStatus("Clipboard empty.") ; return }
    safe := JSONEsc(content)
    ts   := FormatTime(, "yyyyMMdd_HHmmss")
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", FILE_DROP_URL "/create", false)
        whr.SetRequestHeader("Content-Type", "application/json")
        whr.Send('{"filename":"clip_' ts '.md","content":"' safe '","source":"' SOURCE_NAME '"}')
        SetStatus("📤 clip_" ts ".md pushed")
    } catch {
        SetStatus("⚠ File Drop offline — clipboard unchanged")
    }
}

JSONEsc(s) {
    s := StrReplace(s, '\', '\\')
    s := StrReplace(s, '"', '\"')
    s := StrReplace(s, "`n", '\n')
    s := StrReplace(s, "`r", '')
    s := StrReplace(s, "`t", '\t')
    return s
}

; ── Command line processor ───────────────────────────────────
DoRunCmd(*) {
    global cmdInput
    raw := Trim(cmdInput.Value)
    if !raw
        return
    cmdInput.Value := ""

    if SubStr(raw, 1, 1) != "/" {
        A_Clipboard := raw
        DoPasteSend()
        return
    }

    parts := StrSplit(raw, " ", , 2)
    cmd := StrLower(parts[1])
    arg := parts.Length > 1 ? parts[2] : ""

    switch cmd {
        case "/send":   A_Clipboard := arg ; DoPasteSend()
        case "/paste":  DoPasteSend()
        case "/push":   arg ? (A_Clipboard := arg, DoPushClip()) : DoPushClip()
        case "/pull":   DoPullFile()
        case "/scroll": DoToggleScroll()
        case "/speed":
            if IsInteger(arg) {
                global scrollSpeed := Integer(arg)
                speedCtrl.Value := arg
                SetStatus("Speed: " arg)
            }
        case "/profile":
            if IsInteger(arg) && Integer(arg) >= 1 && Integer(arg) <= 5
                SwitchProfile(Integer(arg))
        case "/shell":
            if arg {
                try {
                    exec := ComObject("WScript.Shell").Exec("cmd.exe /c " arg)
                    A_Clipboard := exec.StdOut.ReadAll()
                    SetStatus("Shell done → clip")
                } catch as e {
                    SetStatus("Shell: " e.Message)
                }
            }
        case "/help":
            SetStatus("/send /paste /push /pull /scroll /speed /profile /shell")
        case "/quit":   DoQuit()
        default:        SetStatus("Unknown: " cmd)
    }
}

; ============================================================
; HOTKEYS
; ============================================================
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

#t::ShowTaskCoord()    ; Win+T = Task Coordinator
#c:: {                 ; Win+C = show/hide controller
    global g
    if WinActive("ahk_id " g.Hwnd)
        g.Hide()
    else
        g.Show()
}

; ============================================================
; INIT
; ============================================================
BuildMainGUI()
SwitchProfile(1)  ; default to Claude
