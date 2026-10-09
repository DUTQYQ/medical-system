param([switch]$Demo, [int]$Port = 8000, [switch]$Install)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 virtual environment creation failed.' }
    $Install = $true
}
if ($Install) {
    & $pythonPath -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if ($Demo) {
    $demoDbPath = (Join-Path $PSScriptRoot 'config.local.demo.db').Replace('\', '/')
    $env:DATABASE_URL = "sqlite:///$demoDbPath"
    $env:DEMO_MODE = 'true'
    $secretPath = Join-Path $PSScriptRoot 'config.local.demo-secret'
    if (-not (Test-Path -LiteralPath $secretPath)) {
        $secretBytes = New-Object byte[] 48
        $crypto = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $crypto.GetBytes($secretBytes) } finally { $crypto.Dispose() }
        [System.IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($secretBytes))
    }
    $env:SECRET_KEY = [System.IO.File]::ReadAllText($secretPath)
    & $pythonPath -m scripts.seed --demo
    if ($LASTEXITCODE -ne 0) { throw 'Demo database initialization failed.' }
} else {
    & $pythonPath -m scripts.configure_local
    if ($LASTEXITCODE -ne 0) { throw 'Local database configuration is required, or use -Demo.' }
}
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Backend startup failed.' }
