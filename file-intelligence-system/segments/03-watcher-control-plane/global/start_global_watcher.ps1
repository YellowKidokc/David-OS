Write-Host "Starting global watcher..."
$base = Split-Path $PSScriptRoot -Parent
$cfg = Join-Path $base 'config.example.json'
$cfgOut = Join-Path $base 'config.json'
if (-not (Test-Path $cfgOut) -and (Test-Path $cfg)) { Copy-Item $cfg $cfgOut }

Start-Process -WindowStyle Hidden -FilePath 'python' -ArgumentList @(
  (Join-Path $base 'unified_global_watcher.py'),
  '--config', $cfgOut
) -Priority BelowNormal