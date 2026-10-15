# A saved PID is usable only while the original process and project identity match.
function Get-ProjectProcessTree([int]$RootId, $ExpectedStart, [string]$ProjectRoot) {
    $process = Get-Process -Id $RootId -ErrorAction SilentlyContinue
    if (-not $process) { return @() }
    if ($ExpectedStart) {
        $savedStart = if ($ExpectedStart -is [DateTime]) { $ExpectedStart } else { [DateTime]::Parse($ExpectedStart, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind) }
        if ([Math]::Abs(($process.StartTime.ToUniversalTime() - $savedStart.ToUniversalTime()).TotalSeconds) -gt 2) { return @() }
    }
    $all = @(Get-CimInstance Win32_Process)
    $depth = @{}; $depth[$RootId] = 0
    $queue = New-Object System.Collections.Queue; $queue.Enqueue($RootId)
    while ($queue.Count) {
        $parent = [int]$queue.Dequeue()
        foreach ($child in @($all | Where-Object { [int]$_.ParentProcessId -eq $parent })) {
            $childId = [int]$child.ProcessId
            if (-not $depth.ContainsKey($childId)) { $depth[$childId] = $depth[$parent] + 1; $queue.Enqueue($childId) }
        }
    }
    $tree = @($all | Where-Object { $depth.ContainsKey([int]$_.ProcessId) })
    # Do not print command lines: they may include private configuration.
    $normalizedRoot = $ProjectRoot.Replace('\', '/').TrimEnd('/') + '/'
    if (-not @($tree | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\', '/').IndexOf($normalizedRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 }).Count) { return @() }
    return @($tree | Sort-Object { $depth[[int]$_.ProcessId] } -Descending)
}

function Get-SavedProjectPid($State, [string]$Key, [string]$ProjectRoot, [int]$ExpectedPort = 0) {
    if (-not $State) { return $null }
    if ($ExpectedPort -and [int]$State.($Key + 'Port') -ne $ExpectedPort) { return $null }
    $value = $State.$Key
    if (-not $value -or $value -eq 'reused') { return $null }
    $tree = @(Get-ProjectProcessTree ([int]$value) $State.($Key + 'StartedAt') $ProjectRoot)
    if ($tree.Count) { return [int]$value }
    return $null
}

function Stop-ProjectProcessTree([int]$RootId, $ExpectedStart, [string]$ProjectRoot) {
    $tree = @(Get-ProjectProcessTree $RootId $ExpectedStart $ProjectRoot)
    if (-not $tree.Count) { throw '保存的进程已退出或身份不匹配，未结束任何其他程序。' }
    foreach ($item in $tree) {
        $current = Get-Process -Id ([int]$item.ProcessId) -ErrorAction SilentlyContinue
        if ($current -and [Math]::Abs(($current.StartTime.ToUniversalTime() - $item.CreationDate.ToUniversalTime()).TotalSeconds) -lt 2) {
            Stop-Process -Id ([int]$item.ProcessId) -Force -ErrorAction SilentlyContinue
        }
    }
}
