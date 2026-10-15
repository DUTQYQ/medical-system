<#
康养系统 · 四角色多窗口演示启动
使用独立 SQLite 演示库和独立端口，不覆盖正常 MySQL 站点。
#>
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '一键启动.ps1') -Demo -MultiWindow -ApiPort 8001 -WebPort 5174 -StateName demo
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
