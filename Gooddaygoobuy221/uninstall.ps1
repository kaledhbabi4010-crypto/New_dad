$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "GooddayGoodbay221"
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$Shortcut = Join-Path $StartMenu "GooddayGoodbay221.lnk"

Get-Process -Name "GooddayGoodbay220" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
}

if (Test-Path $Shortcut) {
    Remove-Item $Shortcut -Force
}

if (Test-Path $InstallDir) {
    throw "Installation directory still exists."
}

if (Test-Path $Shortcut) {
    throw "Shortcut still exists."
}

Write-Output "UNINSTALL_OK"
