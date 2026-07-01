param(
    [int]$Port = 8501,
    [string]$Address = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Secrets = Join-Path $RepoRoot ".streamlit\secrets.toml"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python runtime not found: $Python"
}

if (-not (Test-Path -LiteralPath $Secrets) -and -not $env:APP_ACCESS_PASSWORD -and -not $env:APP_ACCESS_PASSWORD_SHA256) {
    throw "Set .streamlit\secrets.toml, APP_ACCESS_PASSWORD, or APP_ACCESS_PASSWORD_SHA256 before starting the server."
}

Write-Host "Starting sales closing forecast app"
Write-Host "URL: http://$Address`:$Port"
Write-Host "Keep this terminal open while using the local preview server."
Write-Host ""

Set-Location -LiteralPath $RepoRoot
& $Python -m streamlit run app.py `
    --server.headless=true `
    --server.port=$Port `
    --server.address=$Address `
    --browser.gatherUsageStats=false
