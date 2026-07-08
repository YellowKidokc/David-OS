param(
  [string]$BaseUrl = "http://127.0.0.1:10000",
  [string]$TokenFile = ".data\remote-api-token.txt",
  [string]$Token = ""
)

$ErrorActionPreference = "Stop"

$ApiRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ApiRoot

if (-not $Token -and (Test-Path $TokenFile)) {
  $Token = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
}

$headers = @{}
if ($Token) {
  $headers["X-API-Token"] = $Token
}

Write-Host "Testing $BaseUrl"

$openapi = Invoke-RestMethod -Uri "$BaseUrl/openapi.json" -Method Get
Write-Host "OpenAPI: ok ($($openapi.info.title) $($openapi.info.version))"

$stats = Invoke-RestMethod -Uri "$BaseUrl/jobs/stats" -Method Get -Headers $headers
Write-Host "Jobs stats: ok"
$stats | ConvertTo-Json -Depth 6
