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
    [switch]$MultiWindow,
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$StateName = 'run',
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'
if ($Demo) {
    if (-not $PSBoundParameters.ContainsKey('ApiPort')) { $ApiPort = 8001 }
    if (-not $PSBoundParameters.ContainsKey('WebPort')) { $WebPort = 5174 }
    if (-not $PSBoundParameters.ContainsKey('StateName')) { $StateName = 'demo' }
}
if ($MultiWindow -and -not $Demo) {
    throw '多角色窗口使用独立演示账号，请通过 ./一键演示多窗口.ps1 启动。'
}

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
$stateFile = Join-Path $backendDir "config.local.$StateName.json"
$backendLog = Join-Path $backendDir "config.local.$StateName.backend.log"
$frontendLog = Join-Path $frontendDir "config.local.$StateName.frontend.log"
. (Join-Path $root '04.编码/启动进程工具.ps1')
$previousState = $null
if (Test-Path -LiteralPath $stateFile) {
    try { $previousState = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
}
$expectedMode = if ($Demo) { 'DEMO_SQLITE' } else { 'MYSQL' }
$expectedRevision = $null
$pythonPath = Join-Path $backendDir '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $pythonPath) {
    Push-Location -LiteralPath $backendDir
    try { $expectedRevision = (& $pythonPath -m scripts.runtime_info | Select-Object -Last 1) } finally { Pop-Location }
}

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

function Get-BackendHealth([int]$port) {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/healthz" -TimeoutSec 2
        if ($r.code -eq 0 -and $r.data.service -eq 'kangyang') { return $r.data }
    } catch { }
    return $null
}

function Test-Backend([int]$port) {
    $health = Get-BackendHealth $port
    return ($health -and $health.database_mode -eq $expectedMode -and
            $health.runtime_revision -and (-not $expectedRevision -or $health.runtime_revision -eq $expectedRevision))
}

function Test-Frontend([int]$port) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -ne 200 -or $r.Content -notmatch '康养系统') { return $false }
        $proxy = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/healthz" -TimeoutSec 2
        $api = Get-BackendHealth $ApiPort
        return ($api -and $proxy.code -eq 0 -and $proxy.data.service -eq 'kangyang' -and
                $proxy.data.process_id -eq $api.process_id -and $proxy.data.runtime_revision -eq $api.runtime_revision -and
                $proxy.data.database_mode -eq $expectedMode)
    } catch { return $false }
}

function Wait-Ready($check, $port, $process) {
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($watch.Elapsed.TotalSeconds -lt 45) {
        if ($process) { $process.Refresh(); if ($process.HasExited) { return $false } }
        if (& $check $port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# Prepare in this shell, then launch Python directly. Avoid a second PowerShell
# console hiding bootstrap errors or leaving the launcher waiting on a dead child.
function Start-BackendSvc {
    $script = Join-Path $backendDir 'start.ps1'
    $saved = @{}
    foreach ($name in @('DATABASE_URL', 'DEMO_MODE', 'SECRET_KEY')) { $saved[$name] = [Environment]::GetEnvironmentVariable($name) }
    Push-Location -LiteralPath $backendDir
    try {
        & $script -Demo:$Demo -Install:$Install -PrepareOnly | Out-Host
        if ($LASTEXITCODE -ne 0) { throw '后端准备失败，请查看上方具体错误。' }
        return Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort") -WorkingDirectory $backendDir `
            -WindowStyle Hidden -RedirectStandardOutput $backendLog -RedirectStandardError "$backendLog.err" -PassThru
    } finally {
        Pop-Location
        foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name]) }
    }
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
    $a = @('run', 'dev', '--', '--host', '127.0.0.1', '--port', "$WebPort", '--strictPort')
    $oldBackendUrl = $env:VITE_BACKEND_URL
    $env:VITE_BACKEND_URL = "http://127.0.0.1:$ApiPort"
    try {
        if ($Background -or $MultiWindow) {
            return Start-Process -FilePath $npm.Source -ArgumentList $a -WorkingDirectory $frontendDir `
                -WindowStyle Hidden -RedirectStandardOutput $frontendLog -RedirectStandardError "$frontendLog.err" -PassThru
        }
        return Start-Process -FilePath $npm.Source -ArgumentList $a -WorkingDirectory $frontendDir -WindowStyle Normal -PassThru
    } finally {
        if ($null -eq $oldBackendUrl) { Remove-Item Env:VITE_BACKEND_URL -ErrorAction SilentlyContinue }
        else { $env:VITE_BACKEND_URL = $oldBackendUrl }
    }
}

function Find-Chromium {
    $candidates = @(
        'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    foreach ($name in @('chrome.exe', 'msedge.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    return $null
}

try {
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
function Save-RunState {
    $state = @{ backend = $started['backend']; frontend = $started['frontend'];
       backendPort = $ApiPort; frontendPort = $WebPort; demo = [bool]$Demo;
       startedAt = (Get-Date).ToString('s') }
    foreach ($key in @('backend', 'frontend')) {
        if ($started[$key] -and $started[$key] -ne 'reused') {
            $process = Get-Process -Id ([int]$started[$key]) -ErrorAction SilentlyContinue
            if ($process) { $state[$key + 'StartedAt'] = $process.StartTime.ToUniversalTime().ToString('o') }
        }
    }
    $state | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
}

# ---------- 后端 ----------
foreach ($key in @('backend', 'frontend')) {
    $port = if ($key -eq 'backend') { $ApiPort } else { $WebPort }
    if ($previousState -and $previousState.($key + 'Port') -ne $port -and (Get-SavedProjectPid $previousState $key $root)) {
        throw "状态 $StateName 已管理另一组端口。请先停止该状态的服务，或用新的 -StateName 启动另一组服务。"
    }
}
if ((Get-BackendHealth $ApiPort) -and -not (Test-Backend $ApiPort)) {
    $owned = Get-SavedProjectPid $previousState 'backend' $root $ApiPort
    if (-not $owned) { throw "端口 $ApiPort 的后端版本或数据库模式不同，且不是当前脚本管理的进程。请停止原服务或使用其他端口。" }
    Say-Warn '检测到本项目后端代码或模式已变化，正在重启受管理进程。'
    Stop-ProjectProcessTree $owned $previousState.backendStartedAt $root
    Start-Sleep -Milliseconds 500
}
if (Test-Backend $ApiPort) {
    Say-Ok "后端已在运行（端口 $ApiPort 就绪），直接复用"
    $owned = Get-SavedProjectPid $previousState 'backend' $root $ApiPort
    $started['backend'] = if ($owned) { $owned } else { 'reused' }
} else {
    if (Test-PortBusy $ApiPort) {
        Say-Err "端口 $ApiPort 被其他程序占用，且不是本项目后端。请关闭占用程序，或用 -ApiPort 指定其他端口。"
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }
    Write-Host '  正在启动后端 ...'
    $p = Start-BackendSvc
    $started['backend'] = $p.Id
    Save-RunState
    if (Wait-Ready 'Test-Backend' $ApiPort $p) {
        Say-Ok "后端就绪（PID $($p.Id)）"
    } else {
        Say-Err '后端进程已退出，或在 45 秒内未就绪。'
        Write-Host "       详细日志：$backendLog.err"
        foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }
        exit 1
    }
}

# ---------- 前端 ----------
if ((Test-PortBusy $WebPort) -and -not (Test-Frontend $WebPort)) {
    $owned = Get-SavedProjectPid $previousState 'frontend' $root $WebPort
    if ($owned) {
        Say-Warn '前端代理与当前后端不一致，正在重启受管理进程。'
        Stop-ProjectProcessTree $owned $previousState.frontendStartedAt $root
        Start-Sleep -Milliseconds 500
    }
}
if (Test-Frontend $WebPort) {
    Say-Ok "前端已在运行（端口 $WebPort 就绪），直接复用"
    $owned = Get-SavedProjectPid $previousState 'frontend' $root $WebPort
    $started['frontend'] = if ($owned) { $owned } else { 'reused' }
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
    Save-RunState
    if (Wait-Ready 'Test-Frontend' $WebPort $p) {
        Say-Ok "前端就绪（PID $($p.Id)）"
    } else {
        Say-Err '前端进程已退出，或在 45 秒内未就绪。'
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
Save-RunState

# ---------- 恢复环境变量 ----------
foreach ($k in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($k, $savedProxy[$k]) }

# ---------- 打开浏览器 ----------
$url = "http://127.0.0.1:$WebPort"
if (-not $NoBrowser) {
    if ($MultiWindow) {
        $browser = Find-Chromium
        if (-not $browser) {
            Say-Warn '没有找到 Chrome 或 Edge，请手动打开下方四个地址并登录对应演示账号。'
        } else {
            $profileRoot = Join-Path $env:LOCALAPPDATA '康养系统实训项目\演示浏览器'
            $rolePages = @(
                @{ Name = 'elder'; Label = '老人端'; Path = '/elder/home' },
                @{ Name = 'family'; Label = '家属端'; Path = '/family/home' },
                @{ Name = 'care'; Label = '护工端'; Path = '/care/elders' },
                @{ Name = 'admin'; Label = '管理员端'; Path = '/admin/statistics' }
            )
            foreach ($rolePage in $rolePages) {
                $profile = Join-Path $profileRoot $rolePage.Name
                New-Item -ItemType Directory -Path $profile -Force | Out-Null
                $roleUrl = "$url$($rolePage.Path)"
                Start-Process -FilePath $browser -ArgumentList @("--user-data-dir=`"$profile`"", '--new-window', $roleUrl) | Out-Null
                Say-Ok "已打开$($rolePage.Label)窗口：$roleUrl"
            }
            Write-Host "  每个窗口使用独立浏览器资料：$profileRoot"
        }
    } else {
        try { Start-Process $url; Say-Ok "已打开浏览器：$url" }
        catch { Say-Warn "未能自动打开浏览器，请手动访问 $url" }
    }
} else {
    Write-Host "  请手动访问：$url"
}

Write-Host ''
Say-Head '=============================================='
if ($Demo) {
    Write-Host '  演示账号（仅限独立演示库，密码均为 Abc123456）'
    Say-Head '=============================================='
    Write-Host '    管理员  13000000001'
    Write-Host '    老人    13000000002      主演示从这个账号进'
    Write-Host '    家属    13000000003'
    Write-Host '    护工    13000000004'
    Write-Host ''
    Say-Warn '四个账号首次使用健康数据、阈值和咨询词条前，需在个人中心确认健康数据授权。'
} else {
    Write-Host '  当前连接本机 MySQL，请使用已存在的正式账号登录。'
}
Write-Host ''
if ($StateName -eq 'run') { Write-Host "  停止服务：& './一键停止.ps1'" }
else { Write-Host "  停止此服务：& './一键停止.ps1' -StateName $StateName" }
Write-Host ''
} finally {
    foreach ($name in $savedProxy.Keys) { [System.Environment]::SetEnvironmentVariable($name, $savedProxy[$name]) }
}
