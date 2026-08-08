[CmdletBinding()]
param(
  [string]$Drive = "E:"
)

$ErrorActionPreference = "Stop"
$u = [char]95
$RepoRoot = $PSScriptRoot
$Setup = Get-ChildItem (Join-Path $RepoRoot "scripts") -Filter "setup*montage*windows.ps1" -File | Select-Object -First 1
if (-not $Setup) { throw "Montage setup script was not found under $RepoRoot\scripts" }

$Workspace = "$Drive\MONTAGE${u}MEDIA"
$Runtime = "$Drive\MONTAGE${u}RUNTIME"

Write-Host "Montage workspace: $Workspace" -ForegroundColor Cyan
Write-Host "Montage runtime:   $Runtime" -ForegroundColor Cyan

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Setup.FullName -Workspace $Workspace -RuntimeRoot $Runtime
if ($LASTEXITCODE -ne 0) { throw "Montage setup failed with exit code $LASTEXITCODE" }

$Launcher = Get-ChildItem $Drive\ -Filter "Start-Montage.cmd" -File -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -like "*$($u)RUNTIME*" } |
  Select-Object -First 1

if (-not $Launcher) {
  $Expected = Join-Path $Runtime "Start-Montage.cmd"
  if (Test-Path $Expected) { $Launcher = Get-Item $Expected }
}

if (-not $Launcher) { throw "Montage setup finished but Start-Montage.cmd was not found." }

Write-Host "Starting Montage: $($Launcher.FullName)" -ForegroundColor Green
& $Launcher.FullName
