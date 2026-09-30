$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "GooddayGoodbay221"
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$Shortcut = Join-Path $StartMenu "GooddayGoodbay221.lnk"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item (Join-Path $Root "app\GooddayGoodbay220.exe") `
          (Join-Path $InstallDir "GooddayGoodbay220.exe") -Force

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($Shortcut)
$sc.TargetPath = Join-Path $InstallDir "GooddayGoodbay220.exe"
$sc.WorkingDirectory = $InstallDir
$sc.Description = "GooddayGoodbay221"
$sc.Save()

$installed = Join-Path $InstallDir "GooddayGoodbay220.exe"

if (!(Test-Path $installed)) {
    throw "Installed executable does not exist."
}

if (!(Test-Path $Shortcut)) {
    throw "Start Menu shortcut was not created."
}

Write-Output "INSTALL_OK"
Write-Output "INSTALL_DIR=$InstallDir"
Write-Output "SHORTCUT=$Shortcut"
