$ErrorActionPreference = "Stop"
$years = 2016..2027
New-Item -ItemType Directory -Force -Path evidence | Out-Null
$items = @()
foreach ($year in $years) {
  $revit = "C:\Program Files\Autodesk\Revit $year\Revit.exe"
  $acad = "C:\Program Files\Autodesk\AutoCAD $year\acad.exe"
  $core = "C:\Program Files\Autodesk\AutoCAD $year\accoreconsole.exe"
  if (!(Test-Path -LiteralPath $revit)) { $revit = $null }
  if (!(Test-Path -LiteralPath $acad)) { $acad = $null }
  if (!(Test-Path -LiteralPath $core)) { $core = $null }
  $revitApi = $null
  if ($revit) {
    $apiPath = Join-Path (Split-Path $revit) "RevitAPI.dll"
    if (Test-Path $apiPath) { $revitApi = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($apiPath).FileVersion }
  }
  $acadManaged = $null
  if ($acad) {
    $managedPath = Join-Path (Split-Path $acad) "AcMgd.dll"
    if (Test-Path $managedPath) { $acadManaged = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($managedPath).FileVersion }
  }
  $items += [ordered]@{
    year = $year
    revit_exe_found = [bool]$revit
    revit_exe = $revit
    revit_api_file_version = $revitApi
    autocad_exe_found = [bool]$acad
    autocad_exe = $acad
    autocad_managed_api_file_version = $acadManaged
    autocad_core_console_found = [bool]$core
    autocad_core_console = $core
    functional_api_test = "NOT_RUN"
    reason = "Inventory only; no Autodesk app was launched and no model/drawing was changed."
  }
}
$result = [ordered]@{
  generated_utc = (Get-Date).ToUniversalTime().ToString("o")
  machine = $env:COMPUTERNAME
  runner_os = $env:RUNNER_OS
  scope = "Installed binary and API assembly inventory only; not functional validation."
  required_years = $years
  versions = $items
  revit_versions_found = @($items | Where-Object revit_exe_found).Count
  autocad_versions_found = @($items | Where-Object autocad_exe_found).Count
  all_12_revit_versions_found = (@($items | Where-Object revit_exe_found).Count -eq 12)
  all_12_autocad_versions_found = (@($items | Where-Object autocad_exe_found).Count -eq 12)
  verdict = "INVENTORY_ONLY"
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "evidence/autodesk-host-inventory.json" -Encoding utf8
$result | ConvertTo-Json -Depth 8
"INVENTORY_ONLY: no Autodesk API command was executed by this inventory step."
