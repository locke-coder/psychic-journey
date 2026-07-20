param(
    [int]$Port = 8501,
    [string]$Address = "127.0.0.1",
    [ValidateSet("private", "local_demo")]
    [string]$DataMode = "local_demo",
    [switch]$UseSavedLocalData
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Secrets = Join-Path $RepoRoot ".streamlit\secrets.toml"
$LoopbackAddresses = @("127.0.0.1", "localhost", "::1")
$IsLoopback = $LoopbackAddresses -contains $Address

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python runtime not found: $Python"
}

if ($DataMode -eq "local_demo" -and -not $IsLoopback) {
    throw "local_demo mode is restricted to a loopback address. Use -DataMode private for shared or remote access."
}

if (-not $IsLoopback -and -not (Test-Path -LiteralPath $Secrets) -and -not $env:APP_ACCESS_PASSWORD -and -not $env:APP_ACCESS_PASSWORD_SHA256) {
    throw "Set .streamlit\secrets.toml, APP_ACCESS_PASSWORD, or APP_ACCESS_PASSWORD_SHA256 before starting the server."
}

$env:PRIVATE_DATA_MODE = $DataMode
$env:LOCAL_DEMO_FRESH_START = if ($DataMode -eq "local_demo" -and -not $UseSavedLocalData) { "1" } else { "0" }

Write-Host "Starting sales closing forecast app"
Write-Host "URL: http://$Address`:$Port"
Write-Host "Data mode: $DataMode"
Write-Host "Use saved local data: $($UseSavedLocalData.IsPresent)"
Write-Host "Keep this terminal open while using the local preview server."
Write-Host ""

Set-Location -LiteralPath $RepoRoot
& $Python -m streamlit run app.py `
    --server.headless=true `
    --server.port=$Port `
    --server.address=$Address `
    --browser.gatherUsageStats=false
