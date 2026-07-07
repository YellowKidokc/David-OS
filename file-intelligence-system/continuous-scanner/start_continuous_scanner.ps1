# low-resource continuous scanner (run from David-OS)
$cfg = Join-Path (Split-Path $PSScriptRoot -Parent) 'config.json'
if (-not (Test-Path $cfg)) {
  Copy-Item (Join-Path (Split-Path $PSScriptRoot -Parent) 'config.example.json') $cfg
}
Start-Process -WindowStyle Hidden -FilePath 'python' -ArgumentList @(
  (Join-Path (Split-Path $PSScriptRoot -Parent) 'continuous_scanner.py'),
  '--config', $cfg,
  '--log-dir', (Join-Path (Split-Path $PSScriptRoot -Parent) 'run')
) -Priority BelowNormal