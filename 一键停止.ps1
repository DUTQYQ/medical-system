<#
康养系统 · 一键停止
关闭由「一键启动.ps1」启动的后端与前端进程。

用法（在项目根目录）：
    & './一键停止.ps1'
#>
param(
    [switch]$强制,
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$StateName = 'run'
)

$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
. (Join-Path $root '04.编码/启动进程工具.ps1')
$stateFile = Join-Path $root "04.编码/后端/config.local.$StateName.json"

function Write-Ok($t)  { Write-Host "  [OK] $t" -ForegroundColor Green }
function Write-Info($t) { Write-Host "  $t" }

if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host ''
    Write-Host '  未找到运行状态文件，可能不是通过一键启动脚本启动的。' -ForegroundColor Yellow
    Write-Host '  可在占用端口 8000 / 5173 的窗口中按 Ctrl+C 停止。' -ForegroundColor Yellow
    Write-Host ''
    exit 0
}

$state = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json

# 收集启动脚本创建的进程及其后代。PowerShell/npm 会再启动 Python/Node 子进程，
# 只结束最外层窗口会留下端口仍被占用的服务。
$roots = @()
foreach ($key in @('backend', 'frontend')) {
    $pid0 = $state.$key
    if ($pid0 -and $pid0 -ne 'reused') {
        $proc = Get-Process -Id ([int]$pid0) -ErrorAction SilentlyContinue
        if ($proc -and (Get-SavedProjectPid $state $key $root)) { $roots += @{ Id=[int]$pid0; StartedAt=$state.($key+'StartedAt') } }
    }
}


# 一键启动时若复用了已存在的服务，这里不负责结束它们，避免误关用户手动开的进程
Write-Host ''
Write-Host '  正在停止康养系统服务 ...' -ForegroundColor Cyan

if ($roots.Count -eq 0) {
    Write-Info '没有由本脚本启动的进程（启动时复用了已运行的服务，未作改动）。'
} else {
    foreach ($entry in $roots) {
        try {
            Stop-ProjectProcessTree $entry.Id $entry.StartedAt $root
            Write-Ok "已结束本项目进程树 PID $($entry.Id)"
        } catch {
            Write-Host "  [!] 未能停止 PID $($entry.Id)：$($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue

# 确认端口已释放
Start-Sleep -Milliseconds 800
foreach ($port in @($state.backendPort, $state.frontendPort)) {
    if (-not $port) { continue }
    $client = New-Object System.Net.Sockets.TcpClient
    $busy = $false
    try {
        $task = $client.ConnectAsync('127.0.0.1', [int]$port)
        $busy = $task.Wait(600) -and $client.Connected
    } catch { $busy = $false } finally { $client.Close() }
    if ($busy) {
        Write-Host "  [!] 端口 $port 仍在监听，可能有其他进程占用。" -ForegroundColor Yellow
    } else {
        Write-Ok "端口 $port 已释放"
    }
}

Write-Host ''
Write-Host '  停止完成。' -ForegroundColor Cyan
Write-Host ''
