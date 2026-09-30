$ErrorActionPreference = "Stop"

$Evidence = Join-Path $env:TEMP "GOODDAY221_EVIDENCE"
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null

$Install = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "install.ps1"
$Uninstall = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "uninstall.ps1"

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Install `
    *> (Join-Path $Evidence "install.txt")

$InstallDir = Join-Path $env:LOCALAPPDATA "GooddayGoodbay221"
$Exe = Join-Path $InstallDir "GooddayGoodbay220.exe"
$Shortcut = Join-Path $env:APPDATA `
    "Microsoft\Windows\Start Menu\Programs\GooddayGoodbay221.lnk"

if (!(Test-Path $Exe)) { throw "Installed EXE missing." }
if (!(Test-Path $Shortcut)) { throw "Shortcut missing." }

$before = (Get-FileHash $Exe -Algorithm SHA256).Hash.ToLower()

$p = Start-Process `
    -FilePath $Exe `
    -WorkingDirectory $InstallDir `
    -RedirectStandardOutput (Join-Path $Evidence "stdout.txt") `
    -RedirectStandardError (Join-Path $Evidence "stderr.txt") `
    -PassThru

Start-Sleep -Seconds 8

$running = !$p.HasExited

if ($running) {
    Stop-Process -Id $p.Id -Force
}

if ($p.HasExited) {
    $exitCode = $p.ExitCode
} else {
    $exitCode = "TERMINATED_AFTER_RUNTIME_WINDOW"
}

$after = (Get-FileHash $Exe -Algorithm SHA256).Hash.ToLower()

$shortcutTarget = ""
try {
    $ws = New-Object -ComObject WScript.Shell
    $shortcutTarget = $ws.CreateShortcut($Shortcut).TargetPath
} catch {}

$runtime = @{
    executable_exists = $true
    executable_sha256_before = $before
    executable_sha256_after = $after
    expected_sha256 = "2d59428f34a9e613c51b0b770e6839e85abb5ecd9efbf3d9a6cf2e8edc28c350"
    runtime_window_seconds = 8
    process_was_running_after_window = $running
    exit_code = $exitCode
    shortcut_exists = Test-Path $Shortcut
    shortcut_target = $shortcutTarget
    stdout = Get-Content (Join-Path $Evidence "stdout.txt") -Raw -ErrorAction SilentlyContinue
    stderr = Get-Content (Join-Path $Evidence "stderr.txt") -Raw -ErrorAction SilentlyContinue
}

$runtime | ConvertTo-Json -Depth 10 |
    Set-Content (Join-Path $Evidence "runtime.json")

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Uninstall `
    *> (Join-Path $Evidence "uninstall.txt")

$cleanup = @{
    install_dir_exists_after_uninstall = Test-Path $InstallDir
    shortcut_exists_after_uninstall = Test-Path $Shortcut
}

$cleanup | ConvertTo-Json |
    Set-Content (Join-Path $Evidence "cleanup.json")

if ($cleanup.install_dir_exists_after_uninstall) {
    throw "Install directory was not removed."
}

if ($cleanup.shortcut_exists_after_uninstall) {
    throw "Shortcut was not removed."
}

Write-Output "WINDOWS_RUNTIME_TEST_COMPLETED"
