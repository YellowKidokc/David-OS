; AutoHotkey v2 bridge example for File Intelligence Hub.
; Ctrl+Alt+C posts the current clipboard into Top of Mind.
; Ctrl+Alt+M appends the current clipboard to a Markdown inbox file through the operator API.

#Requires AutoHotkey v2.0

HubBaseUrl := "http://127.0.0.1:8000"
MarkdownInbox := A_MyDocuments "\Top of Mind\inbox.md"

^!c::PostClipboardMessage()
^!m::AppendClipboardToMarkdown()

PostClipboardMessage() {
    global HubBaseUrl
    text := A_Clipboard
    if !StrLen(text)
        return
    payload := "{""source_id"":""clipboard"",""source_label"":""Clipboard"",""role"":""user"",""folder"":""Clipboard"",""body"":" JsonString(text) "}"
    HttpPost(HubBaseUrl "/top-of-mind/messages", payload)
}

AppendClipboardToMarkdown() {
    global HubBaseUrl, MarkdownInbox
    text := A_Clipboard
    if !StrLen(text)
        return
    entry := "`n`n## Clipboard " FormatTime(, "yyyy-MM-dd HH:mm:ss") "`n`n" text "`n"
    payload := "{""action"":""append_text"",""target_path"":" JsonString(MarkdownInbox) ",""text"":" JsonString(entry) ",""review_required"":false}"
    HttpPost(HubBaseUrl "/operator/file-actions", payload)
}

HttpPost(url, body) {
    request := ComObject("WinHttp.WinHttpRequest.5.1")
    request.Open("POST", url, false)
    request.SetRequestHeader("Content-Type", "application/json")
    request.Send(body)
}

JsonString(value) {
    output := StrReplace(value, "\", "\\")
    output := StrReplace(output, """", "\""")
    output := StrReplace(output, "`r", "\r")
    output := StrReplace(output, "`n", "\n")
    output := StrReplace(output, "`t", "\t")
    return """" output """"
}
