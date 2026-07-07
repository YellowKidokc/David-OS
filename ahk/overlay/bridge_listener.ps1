# bridge_listener.ps1 - HTTP front door for the AI Input Overlay
# Receives POST /send, writes JSON to the overlay's _inbox folder.
# Run alongside ai_input_overlay.ahk (start_bridge.bat launches both).
param([int]$Port = 8765, [string]$Token = "davidos-bridge-2026")
$inbox = Join-Path $PSScriptRoot "_inbox"
New-Item -ItemType Directory -Path $inbox -Force | Out-Null
$l = New-Object Net.HttpListener
$l.Prefixes.Add("http://+:$Port/")
try { $l.Start() } catch {
    Write-Host "Bind failed. Run once as admin:  netsh http add urlacl url=http://+:$Port/ user=Everyone"
    $l = New-Object Net.HttpListener; $l.Prefixes.Add("http://localhost:$Port/"); $l.Start()
    Write-Host "Fell back to localhost-only."
}
Write-Host "Bridge listener up on port $Port -> $inbox"
while ($true) {
    $c = $l.GetContext(); $q = $c.Request; $r = $c.Response
    try {
        if ($q.Url.AbsolutePath -eq "/health") {
            $b = [Text.Encoding]::UTF8.GetBytes('{"ok":true,"service":"davidos-ahk-bridge"}')
        } elseif ($q.Url.AbsolutePath -eq "/send" -and $q.HttpMethod -eq "POST") {
            if ($q.Headers["X-Bridge-Token"] -ne $Token) {
                $r.StatusCode = 401
                $b = [Text.Encoding]::UTF8.GetBytes('{"ok":false,"err":"bad token"}')
            } else {
                $body = (New-Object IO.StreamReader($q.InputStream, $q.ContentEncoding)).ReadToEnd()
                $f = Join-Path $inbox ((Get-Date).Ticks.ToString() + ".json")
                [IO.File]::WriteAllText($f, $body, [Text.Encoding]::UTF8)
                $b = [Text.Encoding]::UTF8.GetBytes('{"ok":true,"queued":true}')
            }
        } else {
            $r.StatusCode = 404
            $b = [Text.Encoding]::UTF8.GetBytes('{"ok":false,"err":"not found"}')
        }
    } catch {
        $r.StatusCode = 500
        $b = [Text.Encoding]::UTF8.GetBytes('{"ok":false,"err":"server"}')
    }
    $r.ContentType = "application/json"
    $r.OutputStream.Write($b, 0, $b.Length)
    $r.Close()
}
