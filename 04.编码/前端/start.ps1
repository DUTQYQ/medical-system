param([int]$Port = 5173, [switch]$Install)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Install -or -not (Test-Path -LiteralPath 'node_modules')) {
    npm.cmd install
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
}
npm.cmd run dev -- --host 127.0.0.1 --port $Port
