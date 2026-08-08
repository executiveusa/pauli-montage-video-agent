[CmdletBinding()]
param(
  [string]$Workspace = "E:\MONTAGE_MEDIA",
  [string]$RuntimeRoot = "E:\MONTAGE_RUNTIME",
  [string]$WhisperModel = "base",
  [switch]$SkipModelDownload
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Message) {
  Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Refresh-Path {
  $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $user = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machine;$user"
}

function Require-Winget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "Windows Package Manager (winget) is required for automatic dependency installation. Install App Installer from Microsoft, then rerun this script."
  }
}

function Ensure-Command([string]$Command, [string]$PackageId, [string]$Label) {
  if (Get-Command $Command -ErrorAction SilentlyContinue) {
    Write-Host "$Label already available."
    return
  }
  Require-Winget
  Write-Step "Installing $Label"
  winget install --id $PackageId -e --accept-package-agreements --accept-source-agreements
  Refresh-Path
  if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
    throw "$Label installation completed but '$Command' is not on PATH yet. Restart PowerShell and rerun this script."
  }
}

function Invoke-Checked([string]$Exe, [string[]]$CommandArgs, [string]$FailureMessage) {
  & $Exe @CommandArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$FailureMessage (exit code $LASTEXITCODE)"
  }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Worker = Join-Path $RepoRoot "scripts\montage_local_service.py"
$Prewarm = Join-Path $RepoRoot "scripts\prewarm_whisper.py"
if (-not (Test-Path $Worker)) { throw "Montage worker not found at $Worker" }
if (-not (Test-Path $Prewarm)) { throw "Whisper prewarm script not found at $Prewarm" }

Write-Step "Preparing owner-controlled Montage runtime"
Write-Host "Repository: $RepoRoot"
Write-Host "Workspace:  $Workspace"
Write-Host "Runtime:    $RuntimeRoot"

New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
$ModelCache = Join-Path $RuntimeRoot "models\whisper"
$Packages = Join-Path $RuntimeRoot "python-packages"
$RuntimePythonFile = Join-Path $RuntimeRoot "python-executable.txt"
$OldVenv = Join-Path $RuntimeRoot ".venv"
New-Item -ItemType Directory -Force -Path $ModelCache | Out-Null
New-Item -ItemType Directory -Force -Path $Packages | Out-Null

Ensure-Command "python" "Python.Python.3.12" "Python"
Ensure-Command "ffmpeg" "Gyan.FFmpeg" "FFmpeg"
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
  throw "ffprobe is required but was not found after FFmpeg installation. Restart PowerShell and rerun setup."
}

$PythonCommand = Get-Command python -ErrorAction Stop
$RuntimePython = $PythonCommand.Source
if (-not $RuntimePython) { $RuntimePython = "python" }
Write-Host "Python:     $RuntimePython"

# Older installer versions used a venv here. Real owner-machine testing showed
# ensurepip/setuptools corruption on some Windows/external-drive combinations.
# Montage does not need a venv: keep dependencies isolated with pip --target on E:.
if (Test-Path $OldVenv) {
  Write-Host "Removing obsolete/broken Montage .venv only."
  Remove-Item -Recurse -Force $OldVenv
}
Set-Content -Path $RuntimePythonFile -Value $RuntimePython -Encoding utf8
$env:PYTHONPATH = $Packages

Write-Step "Installing local transcription dependency into the isolated E-drive package directory"
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $RuntimePython -m pip --version 1>$null 2>$null
$pipReady = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $previousPreference
if (-not $pipReady) {
  throw "The selected Python installation does not provide pip. Install/repair Python with pip enabled, then rerun setup."
}
Invoke-Checked $RuntimePython @("-m", "pip", "install", "--upgrade", "--target", $Packages, "faster-whisper") "Could not install Faster-Whisper into the E-drive package directory"

$env:HF_HOME = $ModelCache
$env:MONTAGE_MODEL_CACHE = $ModelCache
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
if (-not $SkipModelDownload) {
  Write-Step "Downloading and prewarming Faster-Whisper '$WhisperModel' on CPU/int8"
  Invoke-Checked $RuntimePython @($Prewarm, "--model", $WhisperModel, "--cache", $ModelCache) "Could not prewarm the local Whisper model"
}

$Launcher = Join-Path $RuntimeRoot "Start-Montage.cmd"
$StartScript = Join-Path $RepoRoot "scripts\start_montage_windows.ps1"
$launcherText = @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$StartScript" -Workspace "$Workspace" -RuntimeRoot "$RuntimeRoot"
"@
Set-Content -Path $Launcher -Value $launcherText -Encoding ASCII

Write-Step "Setup complete"
Write-Host "Large footage files stay on this computer and upload directly to the loopback worker; they do not pass through Vercel."
Write-Host "The worker writes project media beneath: $Workspace"
Write-Host "Whisper model root: $ModelCache"
Write-Host "Runtime Python: $RuntimePython"
Write-Host "Python packages: $Packages"
Write-Host "Launcher: $Launcher"
Write-Host "`nNext: double-click Start-Montage.cmd, open/create the ASC3ND project, choose vc(1).mp4 from E:, and click Transcribe locally."
