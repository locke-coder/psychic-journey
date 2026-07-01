param(
    [int]$Port = 8501,
    [string]$Address = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$Url = "http://$Address`:$Port"

try {
    $Response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 5
    Write-Host "RUNNING $Url status=$($Response.StatusCode)"
}
catch {
    Write-Host "STOPPED $Url"
    exit 1
}
