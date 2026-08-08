[CmdletBinding()]
param(
  [string]$Workspace = "E:\MONTAGE_MEDIA",
  [string]$RuntimeRoot = "E:\MONTAGE_RUNTIME",
  [int]$Port = 4788,
  [string]$StudioUrl = "https://pauli-montage-video-agent.vercel.app/studio"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Worker = Join-Path $RepoRoot "scripts\montage_local_service.py"
$VenvPython = Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
$RuntimePythonFile = Join-Path $RuntimeRoot "python-executable.txt"
$FallbackPackages = Join-Path $RuntimeRoot "python-packages"
$ModelCache = Join-Path $RuntimeRoot "models\whisper"

if (Test-Path $VenvPython) {
  $RuntimePython = $VenvPython
} elseif (Test-Path $RuntimePythonFile) {
  $RuntimePython = (Get-Content $RuntimePythonFile -Raw).Trim()
  if (-not $RuntimePython -or -not (Test-Path $RuntimePython)) {
    throw "Montage runtime Python reference is invalid. Rerun scripts\setup_montage_windows.ps1."
  }
  if (Test-Path $FallbackPackages) {
    $env:PYTHONPATH = $FallbackPackages
  }
} else {
  throw "Montage runtime is not installed. Run scripts\setup_montage_windows.ps1 first."
}

if (-not (Test-Path $Worker)) { throw "Montage worker not found at $Worker" }
if (-not (Test-Path $Workspace)) { New-Item -ItemType Directory -Force -Path $Workspace | Out-Null }
if (-not (Test-Path $ModelCache)) { New-Item -ItemType Directory -Force -Path $ModelCache | Out-Null }

$env:MONTAGE_LOCAL_WORKSPACE = $Workspace
$env:MONTAGE_MODEL_CACHE = $ModelCache
$env:HF_HOME = $ModelCache

try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 1
  if ($health.service -eq "montage-local") {
    Write-Host "Montage local worker is already running on port $Port."
    Start-Process $StudioUrl
    exit 0
  }
} catch {
  # Expected when the worker is not running yet.
}

Write-Host "Starting Montage local worker..." -ForegroundColor Cyan
Write-Host "Workspace: $Workspace"
Write-Host "Model cache: $ModelCache"
Write-Host "Runtime Python: $RuntimePython"
Write-Host "Studio: $StudioUrl"
Write-Host "`nKeep this window open while editing. Press Ctrl+C to stop the local worker.`n"

Start-Process $StudioUrl
& $RuntimePython $Worker --host 127.0.0.1 --port $Port --workspace $Workspace
