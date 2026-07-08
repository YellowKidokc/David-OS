param(
  [string]$Branch = "codex/deep-research-captures",
  [string]$Remote = "origin",
  [switch]$NoPush
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$exportsRoot = Join-Path $scriptDir "research_exports"

if (-not (Test-Path $exportsRoot)) {
  throw "No research_exports folder found. Run export_gemini_research.bat first."
}

$latest = Get-ChildItem $exportsRoot -Directory |
  Where-Object { Test-Path (Join-Path $_.FullName "gemini_research_capture.txt") } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if (-not $latest) {
  throw "No complete research capture folders found. Run export_gemini_research.bat first."
}

$captureText = Join-Path $latest.FullName "gemini_research_capture.txt"
$captureLength = (Get-Item $captureText).Length
if ($captureLength -lt 100) {
  throw "Latest capture text is very small. Open Gemini, sign in if needed, and capture the completed research first."
}

Push-Location $repoRoot
try {
  $currentBranch = (git branch --show-current).Trim()
  if (-not $currentBranch) {
    throw "Could not determine the current Git branch."
  }

  if ($currentBranch -ne $Branch) {
    $exists = git rev-parse --verify $Branch 2>$null
    if ($LASTEXITCODE -eq 0) {
      git switch $Branch
    } else {
      git switch -c $Branch
    }
  }

  $dest = Join-Path $repoRoot ("docs\research-captures\" + $latest.Name)
  New-Item -ItemType Directory -Force -Path $dest | Out-Null

  foreach ($name in @("gemini_research_capture.txt", "gemini_research_page.html", "gemini_research_page.png", "metadata.json")) {
    $src = Join-Path $latest.FullName $name
    if (Test-Path $src) {
      Copy-Item -LiteralPath $src -Destination (Join-Path $dest $name) -Force
    }
  }

  $metadataPath = Join-Path $dest "metadata.json"
  $sourceUrl = "unknown"
  $title = "Gemini Deep Research Capture"
  if (Test-Path $metadataPath) {
    $metadata = Get-Content $metadataPath -Raw | ConvertFrom-Json
    if ($metadata.url) { $sourceUrl = $metadata.url }
    if ($metadata.title) { $title = $metadata.title }
  }

  $indexPath = Join-Path $dest "README.md"
  @(
    "# Gemini Deep Research Capture"
    ""
    "- Title: $title"
    "- Source URL: $sourceUrl"
    "- Captured folder: $($latest.Name)"
    "- Text bytes: $captureLength"
    ""
    "Files:"
    ""
    "- gemini_research_capture.txt"
    "- gemini_research_page.html"
    "- gemini_research_page.png"
    "- metadata.json"
  ) | Set-Content -LiteralPath $indexPath -Encoding UTF8

  git add -- docs/research-captures .gitignore tools/prompt-launcher/README.md tools/prompt-launcher/export_gemini_research.bat tools/prompt-launcher/export_gemini_research.mjs tools/prompt-launcher/publish_latest_research_to_github.bat tools/prompt-launcher/publish_latest_research_to_github.ps1

  $status = git status --short
  if (-not $status) {
    Write-Host "Nothing new to commit."
  } else {
    git commit -m "docs: add Gemini deep research capture $($latest.Name)"
  }

  if (-not $NoPush) {
    git push -u $Remote HEAD:$Branch
  }

  Write-Host "Published research capture folder:"
  Write-Host $dest
  Write-Host "Branch:"
  Write-Host $Branch
} finally {
  Pop-Location
}
