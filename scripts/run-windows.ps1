$ErrorActionPreference = "Stop"

$HostName = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$Port = if ($env:PORT) { $env:PORT } else { "8000" }

if (-not (Test-Path ".env")) {
    Write-Error "Missing .env. Copy .env.example to .env and fill your token first."
    exit 1
}

python -m uvicorn electricitybill.app:app --host $HostName --port $Port
