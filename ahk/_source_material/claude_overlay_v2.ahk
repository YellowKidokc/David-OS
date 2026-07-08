#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent
#NoTrayIcon

; ─────────────────────────────────────────────────────────────────────────────
; claude_overlay_v2.ahk
; Ghost overlay — always on top, no taskbar, no focus steal
; Ctrl+Shift+H = toggle | Ctrl+Shift+Q = quit
; ─────────────────────────────────────────────────────────────────────────────

BTN_H := 24
BTN_W := 52
StartX := A_ScreenWidth - 240
StartY := 10

; ── Main overlay bar ─────────────────────────────────────────────────────────
ov := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x08000000")
ov.BackColor := "1A1A2E"
ov.MarginX := 2
ov.MarginY := 4
ov.SetFont("s8 cE9E6DD", "Segoe UI")

ov.AddButton("x2   y4 w" BTN_W " h" BTN_H, "Copy").OnEvent("Click",     DoCopy)
ov.AddButton("x56  y4 w" BTN_W " h" BTN_H, "New").OnEvent("Click",      DoShowInputBox)
ov.AddButton("x110 y4 w" BTN_W " h" BTN_H, "Artifact").OnEvent("Click", DoArtifact)
ov.AddButton("x164 y4 w" BTN_W " h" BTN_H, "Projects").OnEvent("Click", DoBookmarks)

ov.Show("x" StartX " y" StartY " w230 h34 NoActivate")
WinSetAlwaysOnTop(1, ov.Hwnd)
OnMessage(0x0201, WM_LBtn)

; ── Floating input box ────────────────────────────────────────────────────────
inputBox := Gui("+AlwaysOnTop -Caption +ToolWindow +Resize +E0x08000000")
inputBox.BackColor := "0D1117"
inputBox.MarginX := 6
inputBox.MarginY := 6
inputBox.SetFont("s10 cE9E6DD", "Consolas")

global txtInput := inputBox.AddEdit("x6 y6 w460 h80 Multi Background1A2040 +Wrap")
inputBox.SetFont("s8 cE9E6DD", "Segoe UI")
btnSend  := inputBox.AddButton("x6   y92 w80 h24", "▶ Send")
btnClear := inputBox.AddButton("x90  y92 w80 h24", "Clear")
btnClose := inputBox.AddButton("x390 y92 w76 h24", "✕ Close")

btnSend.OnEvent("Click",  DoSendFromBox)
btnClear.OnEvent("Click", (*) => txtInput.Value := "")
btnClose.OnEvent("Click", (*) => inputBox.Hide())
inputBox.OnEvent("Close", (*) => inputBox.Hide())

; Position input box just below overlay bar
inputBox.Show("x" StartX " y" (StartY + 40) " w476 h122 Hide")

; ── Hotkeys ───────────────────────────────────────────────────────────────────
^+h:: {
    global ov
    if WinExist("ahk_id " ov.Hwnd)
        ov.Hide()
    else
        ov.Show("NoActivate")
}
^+q::ExitApp()

; ── Button actions ────────────────────────────────────────────────────────────
DoCopy(*) {
    WinActivate("ahk_exe chrome.exe")
    Sleep(80)
    Send("^c")
}

DoShowInputBox(*) {
    global inputBox
    if WinExist("ahk_id " inputBox.Hwnd) && WinGetMinMax("ahk_id " inputBox.Hwnd) != -1
        inputBox.Hide()
    else
        inputBox.Show("NoActivate")
    txtInput.Focus()
}

DoSendFromBox(*) {
    global txtInput
    text := Trim(txtInput.Value)
    if (text = "")
        return
    A_Clipboard := text
    WinActivate("ahk_exe chrome.exe")
    Sleep(120)
    Send("^v")
    Sleep(200)
    Send("{Enter}")
    txtInput.Value := ""
    inputBox.Hide()
}

DoArtifact(*) {
    WinActivate("ahk_exe chrome.exe")
    Sleep(80)
    Send("^+a")
}

DoBookmarks(*) {
    WinActivate("ahk_exe chrome.exe")
    Sleep(80)
    Send("^+o")  ; Chrome bookmarks manager
}

; ── Drag support (both windows) ───────────────────────────────────────────────
WM_LBtn(wParam, lParam, msg, hwnd) {
    global ov, inputBox
    if (hwnd = ov.Hwnd || hwnd = inputBox.Hwnd)
        PostMessage(0xA1, 2, 0, , hwnd)
}

ov.OnEvent("Close", (*) => ExitApp())
