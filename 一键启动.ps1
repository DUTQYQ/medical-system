<#
康养系统 · 一键启动
自动启动后端与前端，等待服务就绪后打开浏览器。

用法（在项目根目录）：
    & './一键启动.ps1'                 # 正常模式（MySQL）
    & './一键启动.ps1' -Demo           # 独立演示库（SQLite，不动现有 MySQL）
    & './一键启动.ps1' -Background     # 静默后台启动，日志写入文件
    & './一键启动.ps1' -Install        # 先装依赖再启动
    & './一键启动.ps1' -NoBrowser      # 不自动打开浏览器

停止服务：
    & './一键停止.ps1'
#>
param(
    [switch]$Demo,
    [switch]$Background,
    [switch]$Install,
    [switch]$NoBrowser,
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------
# 关键环境修复：清除仅大小写不同的重复环境变量。
# 本机同时存在 https_proxy 与 HTTPS_PROXY（http_proxy/HTTP_PROXY 同理），
# Windows PowerShell 5.1 创建子进程时用不区分大小写的字典合并环境，
# 会抛「已添加项。字典中的关键字:"https_proxy"所添加的关键字:"HTTPS_PROXY"」，
# 导致后端与前端进程根本起不来。这里先移除小写副本，脚本结束时恢复。
# ---------------------------------------------------------------
$savedProxy = @{}
foreach ($dup in @('http_proxy', 'https_proxy')) {
    $upperName = $dup.ToUpper()
    $lowerVal = [System.Environment]::GetEnvironmentVariable($dup)
    $upperVal = [System.Environment]::GetEnvironmentVariable($upperName)
    if ($null -ne $lowerVal -and $null -ne $upperVal) {
        $savedProxy[$dup] = $lowerVal
        [System.Environment]::SetEnvironmentVariable($dup, $null)
    }
}

$root = $PSScriptRoot
$backendDir = Join-Path $root '04.编码/后端'
$frontendDir = Join-Path $root '04.编码/前端'
$stateFile = Join-Path $backendDir 'config.local.run.json'
$backendLog = Join-Path $backendDir 'config.local.backend.log'
$frontendLog = Join-Path $frontendDir 'config.local.frontend.log'

function Say-Head($t) { Write-Host $t -ForegroundColor Cyan }
function Say-Ok($t)   { Write-Host "  [OK] $t" -ForegroundColor Green }
function Say-Warn($t) { Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Say-Err($t)  { Write-Host "  [X]  $t" -ForegroundColor Red }

function Test-PortBusy([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync('127.0.0.1', $port)
        if (-not $task.Wait(800)) { return $false }
        return $client.Connected
    } catch { return $false } finally { $client.Close() }
}

function Test-Backend([int]$port) {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/healthz" -TimeoutSec 4
        return ($r.code -eq 0)
    } catch { return $false }
}

function Test-Frontend([int]$port) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/" -TimeoutSec 4 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Wait-Ready($check, $port) {
    for ($i = 1; $i -le 60; $i++) {
        if (& $check $port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# 后端：调用后端 start.ps1。用 -File 传参比 -Command 稳，避免嵌套引号被吞。
function Start-BackendSvc {
    $psExe = (Get-Process -Id $PID).Path
    $script = Join-Path $backendDir 'start.ps1'
    $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $script, '-Port', "$ApiPort")
    if ($Demo) { $a += '-Demo' }
    if ($Install) { $a += '-Install' }
    if ($Background) {
        return Start-Process -FilePath $psExe -ArgumentList $a -WorkingDirectory $backendDir `
            -WindowStyle Hidden -RedirectStandardOutput $backendLog -RedirectStandardError "$backendLog.err" -PassThru
    }
    return Start-Process -FilePath $psExe -ArgumentList $a -WorkingDirectory $backendDir -WindowStyle Normal -PassThru
}

# 前端：调用 npm.cmd
function Start-FrontendSvc {
    $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue)
    if (-not $npm) { return $null }
    $winStyle = 'Normal'
    if ($Background) { $winStyle = 'Hidden' }
    if ($Install) {
        $p1 = Start-Process -FilePath $npm.Source -ArgumentList @('install') -WorkingDirectory $frontendDir `
            -WindowStyle $winStyle -Wait -PassThru
        if ($p1.ExitCode -ne 0) { return $null }
    }
    $a = @('run', 'dev', '--', '--host', '127.0.0.1', '--port', "$WebPort")
    if ($Background) {
        return Start-Process -FilePath $npm.Source -ArgumentList $a -WorkingDirectory $frontendDir `
            -WindowStyle Hidden -RedirectStandardOutput $frontendLog -RedirectStandardError "$frontendLog.err" -PassThru
    }
    return Start-Process -FilePath $npm.Source -ArgumentList $a -WorkingDirectory $frontendDir -WindowStyle Normal -PassThru
}

Write-Host ''
Say-Head '=============================================='
Say-Head '   康养系统 · 一键启动'
Say-Head '=============================================='
$modeText = if ($Demo) { '独立演示库（SQLite）' } else { '正常模式（MySQL）' }
Write-Host "  模式：$modeText"
Write-Host "  后端：http://127.0.0.1:$ApiPort"
Write-Host "  前端：http://127.0.0.1:$WebPort"
Write-Host ''

$started = @{}

# ---------- 后端 ----------
if (Test-Backend $ApiPort) {
    Say-Ok "后端已在运行（端口 $ApiPort 就绪），直接复用"
    $started['backend'] = 'reused'
} else {
    if (Test-PortBusy $ApiPort) {
        Say-Err "端口 $ApiPort 被其他程序占用，且不是本项目后端。请关闭占用程序，或用 -ApiPort 指定其他端口。"
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }
    Write-Host '  正在启动后端 ...'
    $p = Start-BackendSvc
    $started['backend'] = $p.Id
    if (Wait-Ready 'Test-Backend' $ApiPort) {
        Say-Ok "后端就绪（PID $($p.Id)）"
    } else {
        Say-Err '后端启动失败或超时（30 秒）。'
        if ($Background) { Write-Host "       日志：$backendLog" } else { Write-Host '       请查看后端窗口中的报错。' }
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }
}

# ---------- 前端 ----------
if (Test-Frontend $WebPort) {
    Say-Ok "前端已在运行（端口 $WebPort 就绪），直接复用"
    $started['frontend'] = 'reused'
} else {
    if (Test-PortBusy $WebPort) {
        Say-Err "端口 $WebPort 被其他程序占用，且不是本项目前端。请关闭占用程序，或用 -WebPort 指定其他端口。"
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        Say-Err '未找到 npm，请先安装 Node.js 18 或以上。'
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }

    Write-Host '  正在启动前端 ...'
    $p = Start-FrontendSvc
    if (-not $p) { Say-Err '前端启动命令执行失败（依赖安装可能未成功）。'; exit 1 }
    $started['frontend'] = $p.Id
    if (Wait-Ready 'Test-Frontend' $WebPort) {
        Say-Ok "前端就绪（PID $($p.Id)）"
    } else {
        Say-Err '前端启动失败或超时（30 秒）。'
        if ($Background) { Write-Host "       日志：$frontendLog" } else { Write-Host '       请查看前端窗口中的报错。' }
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }
}

# ---------- 代理连通性 ----------
try {
    $px = Invoke-RestMethod -Uri "http://127.0.0.1:$WebPort/api/healthz" -TimeoutSec 6
    if ($px.code -eq 0) { Say-Ok '前端到后端的 /api 代理连通正常' }
    else { Say-Warn '前端已启动，但 /api 代理返回异常，请检查后端。' }
} catch {
    Say-Warn '前端已启动，但 /api 代理未连通。若后端端口不是 8000，请为前端进程设置 VITE_BACKEND_URL 后重试。'
}

# ---------- 保存运行状态 ----------
@{ backend = $started['backend']; frontend = $started['frontend']
   backendPort = $ApiPort; frontendPort = $WebPort; demo = [bool]$Demo
   startedAt = (Get-Date).ToString('s') } |
    ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

# ---------- 恢复环境变量 ----------
foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }

# ---------- 打开浏览器 ----------
$url = "http://127.0.0.1:$WebPort"
if (-not $NoBrowser) {
    try { Start-Process $url; Say-Ok "已打开浏览器：$url" }
    catch { Say-Warn "未能自动打开浏览器，请手动访问 $url" }
} else {
    Write-Host "  请手动访问：$url"
}

Write-Host ''
Say-Head '=============================================='
Write-Host '  演示账号（仅限独立演示库，密码均为 Abc123456）'
Say-Head '=============================================='
Write-Host '    管理员  13000000001'
Write-Host '    老人    13000000002      主演示从这个账号进'
Write-Host '    家属    13000000003'
Write-Host '    护工    13000000004'
Write-Host ''
Say-Warn '重要：四个账号首次登录后，都要先在个人中心确认健康数据授权，否则通知中心等页面会提示未授权。'
Write-Host ''
Write-Host "  停止服务：& './一键停止.ps1'"
Write-Host ''
