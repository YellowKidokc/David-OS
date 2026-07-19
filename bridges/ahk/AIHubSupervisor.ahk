#Requires AutoHotkey v2.0
#SingleInstance Force
; ============================================================================
; AI Hub Supervisor — one lifecycle for the AHK layer.
;
; Starts ExtraClipboard, LLM-Assistant, and stratum together, keeps
; LLM-Assistant off the taskbar, and shuts ALL of them down when any one
; dies or when the supervisor exits. Run this instead of the three scripts
; individually; put a shortcut to it in shell:startup to launch at login.
;
; Tray menu: Restart All / Exit All.
; ============================================================================

HUB_ROOT := "\\192.168.2.50\h_hp\Desktop\AI HUB DAVID\AHK"

; entry: leave "" to auto-detect (<folder>\<folder name>.ahk, then main.ahk,
;        then the first *.ahk in the folder). Set explicitly if detection
;        picks the wrong file.
; hideTaskbar: strip the app's windows from the taskbar (WS_EX_TOOLWINDOW).
APPS := [
    { name: "ExtraClipboard", dir: HUB_ROOT "\ExtraClipboard", entry: "", hideTaskbar: false },
    { name: "LLM-Assistant",  dir: HUB_ROOT "\LLM-Assistant",  entry: "", hideTaskbar: true  },
    { name: "stratum",        dir: HUB_ROOT "\stratum",        entry: "", hideTaskbar: false },
]

; Optional: report the AHK layer to the File Intelligence Hub. Fails silently
; when the hub is not running.
HUB_HEARTBEAT_URL := "http://127.0.0.1:10000/nodes/heartbeat"
HEARTBEAT_EVERY_MS := 30000

WATCHDOG_EVERY_MS := 2000
shuttingDown := false

FindEntry(app) {
    if (app.entry != "" && FileExist(app.dir "\" app.entry))
        return app.dir "\" app.entry
    SplitPath app.dir, &leaf
    for cand in [app.dir "\" leaf ".ahk", app.dir "\main.ahk"] {
        if FileExist(cand)
            return cand
    }
    loop files app.dir "\*.ahk" {
        return A_LoopFileFullPath  ; first match, alphabetical
    }
    return ""
}

StartApp(app) {
    entry := FindEntry(app)
    if (entry = "") {
        TrayTip "AI Hub Supervisor", "No .ahk entry found in " app.dir
        return false
    }
    Run '"' A_AhkPath '" "' entry '"', app.dir, , &pid
    app.pid := pid
    app.entryPath := entry
    if (app.hideTaskbar)
        SetTimer(HideTaskbarFactory(app), -400)  ; windows appear async
    return true
}

HideTaskbarFactory(app) {
    ; Sweep the app's windows a few times as they appear and strip the
    ; taskbar button. Re-runs briefly rather than polling forever.
    sweeps := 0
    hide() {
        sweeps += 1
        for hwnd in WinGetList("ahk_pid " app.pid) {
            try {
                ex := WinGetExStyle(hwnd)
                if !(ex & 0x80)  ; WS_EX_TOOLWINDOW
                    WinSetExStyle "+0x80", hwnd
            }
        }
        if (sweeps < 15 && ProcessExist(app.pid))
            SetTimer(hide, -1000)
    }
    return hide
}

StartAll() {
    global shuttingDown := false
    ok := true
    for app in APPS
        ok := StartApp(app) && ok
    TrayTip "AI Hub Supervisor", ok ? "All three apps started." : "Started with warnings — check tray tips."
    SetTimer Watchdog, WATCHDOG_EVERY_MS
    SetTimer Heartbeat, HEARTBEAT_EVERY_MS
}

StopAll(*) {
    global shuttingDown := true
    SetTimer Watchdog, 0
    SetTimer Heartbeat, 0
    for app in APPS {
        if (app.HasOwnProp("pid") && ProcessExist(app.pid)) {
            try ProcessClose(app.pid)
        }
    }
}

Watchdog() {
    global shuttingDown
    if shuttingDown
        return
    for app in APPS {
        if (app.HasOwnProp("pid") && !ProcessExist(app.pid)) {
            ; One member died -> the whole layer dies together.
            TrayTip "AI Hub Supervisor", app.name " exited — shutting the AHK layer down."
            StopAll()
            Sleep 500
            ExitApp
        }
    }
}

Heartbeat() {
    ; Best-effort: lets the hub's node health see the AHK layer.
    try {
        req := ComObject("WinHttp.WinHttpRequest.5.1")
        req.SetTimeouts(800, 800, 800, 800)
        req.Open("POST", HUB_HEARTBEAT_URL, false)
        req.SetRequestHeader("Content-Type", "application/json")
        req.Send('{"node_id":"ahk-supervisor"}')
    }
}

RestartAll(*) {
    StopAll()
    Sleep 800
    StartAll()
}

; ── Tray ────────────────────────────────────────────────────────────────
A_TrayMenu.Delete()
A_TrayMenu.Add("Restart All", RestartAll)
A_TrayMenu.Add("Exit All", (*) => (StopAll(), ExitApp()))
A_TrayMenu.Default := "Restart All"
A_IconTip := "AI Hub Supervisor — ExtraClipboard + LLM-Assistant + stratum"

OnExit((*) => (StopAll(), 0))

StartAll()
