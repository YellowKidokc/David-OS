param(
  [string]$HostName = "0.0.0.0",
  [int]$Port = 10000,
  [string]$DbPath = "D:\TopOfMind\data\top-of-mind.sqlite3",
  [string]$TokenFile = ".data\remote-api-token.txt",
  [switch]$NoToken
)

$ErrorActionPreference = "Stop"

$ApiRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ApiRoot

if (-not (Test-Path ".data")) {
  New-Item -ItemType Directory -Path ".data" | Out-Null
}

$dbDir = Split-Path -Parent $DbPath
if ($dbDir -and -not (Test-Path $dbDir)) {
  New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
}

$env:FIHUB_DB_PATH = $DbPath

if ($NoToken) {
  Remove-Item Env:\FIHUB_API_TOKEN -ErrorAction SilentlyContinue
  Write-Warning "Starting without FIHUB_API_TOKEN. Use this only on a trusted machine."
} else {
  if (-not (Test-Path $TokenFile)) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $token = [Convert]::ToBase64String($bytes).TrimEnd("=")
    Set-Content -LiteralPath $TokenFile -Value $token -Encoding ASCII
  }
  $env:FIHUB_API_TOKEN = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
}

$ips = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
  Select-Object -ExpandProperty IPAddress

Write-Host ""
Write-Host "Top of Mind API remote mode"
Write-Host "API root: $ApiRoot"
Write-Host "Host:     $HostName"
Write-Host "Port:     $Port"
Write-Host "DB:       $env:FIHUB_DB_PATH"
if (-not $NoToken) {
  Write-Host "Token:    $TokenFile"
}
foreach ($ip in $ips) {
  Write-Host "LAN URL:  http://$ip`:$Port"
}
Write-Host ""
Write-Host "Stop with Ctrl+C."
Write-Host ""

py -3.12 -m uvicorn file_intelligence_hub.api.app:app --host $HostName --port $Port
