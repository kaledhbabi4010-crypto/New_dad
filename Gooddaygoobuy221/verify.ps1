$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "GooddayGoodbay221"
$Exe = Join-Path $InstallDir "GooddayGoodbay220.exe"
$Shortcut = Join-Path $env:APPDATA `
    "Microsoft\Windows\Start Menu\Programs\GooddayGoodbay221.lnk"

$result = @{
    install_dir = $InstallDir
    exe_exists = Test-Path $Exe
    shortcut_exists = Test-Path $Shortcut
}

$result | ConvertTo-Json -Depth 5
