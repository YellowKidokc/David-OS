# Remote / LAN Mode

Remote mode lets other computers on the same network talk to the Top of Mind API.

Use this first for LAN access. Do not expose this API directly to the public internet.

## Start The API On The Hub Machine

```powershell
cd D:\GitHub\Top-of-Mind-API\apps\api

.\scripts\remote\start_remote_api.ps1
```

The script starts Uvicorn on:

```text
0.0.0.0:10000
```

It prints LAN URLs such as:

```text
http://192.168.2.50:10000
```

It also creates a token file:

```text
D:\GitHub\Top-of-Mind-API\apps\api\.data\remote-api-token.txt
```

That file is under `.data/`, which is ignored by git.

## Test From The Hub Machine

```powershell
cd D:\GitHub\Top-of-Mind-API\apps\api

.\scripts\remote\test_remote_api.ps1 -BaseUrl http://127.0.0.1:10000
```

## Test From Another Computer

Copy the token from the hub machine, then run:

```powershell
$token = "PASTE_TOKEN_HERE"
$headers = @{ "X-API-Token" = $token }

Invoke-RestMethod -Uri "http://192.168.2.50:10000/jobs/stats" -Headers $headers
```

## AutoHotkey Shape

AutoHotkey should call the remote API with the token header.

```ahk
baseUrl := "http://192.168.2.50:10000"
token := "PASTE_TOKEN_HERE"

http := ComObject("WinHttp.WinHttpRequest.5.1")
http.Open("GET", baseUrl "/jobs/stats", false)
http.SetRequestHeader("X-API-Token", token)
http.Send()
MsgBox http.ResponseText
```

## Firewall

If another machine cannot connect, allow TCP port `10000` through Windows Firewall on the hub machine for private networks only.

PowerShell as administrator:

```powershell
New-NetFirewallRule `
  -DisplayName "Top of Mind API 10000" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 10000 `
  -Profile Private
```

## Security Rules

- Keep `FIHUB_API_TOKEN` set for LAN mode.
- Do not commit token files.
- Do not put the live SQLite database on a NAS/network share.
- Use the NAS for backups and shared files, not as the active SQLite writer.
- Keep dangerous actions review-gated.
- Public internet access should go through a real auth/proxy layer first.
