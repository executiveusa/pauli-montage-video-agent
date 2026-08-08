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
New-Item -ItemType Directory -Force -Path $ModelCache | Out-Null

Ensure-Command "python" "Python.Python.3.12" "Python 3.12"
Ensure-Command "ffmpeg" "Gyan.FFmpeg" "FFmpeg"
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
  throw "ffprobe is required but was not found after FFmpeg installation. Restart PowerShell and rerun setup."
}

$PythonCommand = Get-Command python -ErrorAction Stop
$SystemPython = $PythonCommand.Source
if (-not $SystemPython) { $SystemPython = "python" }
Write-Host "Python:     $SystemPython"

$Venv = Join-Path $RuntimeRoot ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$FallbackPackages = Join-Path $RuntimeRoot "python-packages"
$RuntimePythonFile = Join-Path $RuntimeRoot "python-executable.txt"
$UseFallback = $false

function Test-VenvReady {
  if (-not (Test-Path $VenvPython)) { return $false }
  & $VenvPython -m pip --version *> $null
  return ($LASTEXITCODE -eq 0)
}

if (-not (Test-VenvReady)) {
  if (Test-Path $Venv) {
    Write-Host "Removing incomplete local virtual environment."
    Remove-Item -Recurse -Force $Venv
  }
  Write-Step "Creating isolated Python environment on the runtime drive"
  & $SystemPython -m venv $Venv
  if ($LASTEXITCODE -ne 0 -or -not (Test-VenvReady)) {
    Write-Warning "Windows venv/ensurepip did not complete. Falling back to an isolated E-drive package directory."
    if (Test-Path $Venv) {
      Remove-Item -Recurse -Force $Venv
    }
    New-Item -ItemType Directory -Force -Path $FallbackPackages | Out-Null
    $UseFallback = $true
  }
}

if (-not $UseFallback -and (Test-VenvReady)) {
  $RuntimePython = $VenvPython
  Set-Content -Path $RuntimePythonFile -Value $RuntimePython -Encoding utf8
  Write-Step "Installing local transcription dependency into the virtual environment"
  Invoke-Checked $RuntimePython @("-m", "pip", "install", "--upgrade", "pip") "Could not upgrade pip in the Montage virtual environment"
  Invoke-Checked $RuntimePython @("-m", "pip", "install", "--upgrade", "faster-whisper") "Could not install Faster-Whisper in the Montage virtual environment"
} else {
  $RuntimePython = $SystemPython
  New-Item -ItemType Directory -Force -Path $FallbackPackages | Out-Null
  Set-Content -Path $RuntimePythonFile -Value $RuntimePython -Encoding utf8
  Write-Step "Installing local transcription dependency into the E-drive fallback package directory"
  & $RuntimePython -m pip --version *> $null
  if ($LASTEXITCODE -ne 0) {
    throw "The base Python installation does not provide pip. Repair/reinstall Python 3.12 with pip enabled, then rerun setup."
  }
  Invoke-Checked $RuntimePython @("-m", "pip", "install", "--upgrade", "--target", $FallbackPackages, "faster-whisper") "Could not install Faster-Whisper into the E-drive fallback package directory"
  $env:PYTHONPATH = $FallbackPackages
}

$env:HF_HOME = $ModelCache
$env:MONTAGE_MODEL_CACHE = $ModelCache
# Some Windows/external-drive filesystems reject symbolic links even when Hugging Face
# detects Windows correctly. Force its documented copy-based cache mode so model files
# stay on the configured media drive without requiring Developer Mode or admin elevation.
$env:HF_HUB_DISABLE_SYMLINKS = "1"
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
Write-Host "Whisper cache: $ModelCache"
Write-Host "Runtime Python: $RuntimePython"
if ($UseFallback) { Write-Host "Python packages: $FallbackPackages (venv fallback mode)" }
Write-Host "Launcher: $Launcher"
Write-Host "`nNext: double-click Start-Montage.cmd, open/create the ASC3ND project, choose vc(1).mp4 from E:, and click Transcribe locally."
