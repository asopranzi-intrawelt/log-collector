<#
Controllo di sola lettura della coda Fluent Bit Windows per un monitor locale.
Exit 0: sotto le soglie. Exit 2: soglia superata. Exit 3: misura non valida.
#>
param(
    [string]$RuntimeDir = 'C:\ProgramData\fluent-bit',
    [Parameter(Mandatory = $true)][long]$MaxQueueBytes,
    [Parameter(Mandatory = $true)][long]$MinFreeBytes,
    [Parameter(Mandatory = $true)][int]$MaxOldestChunkMinutes
)

$ErrorActionPreference = 'Stop'

function Measure-Storage {
    param(
        [System.IO.DirectoryInfo]$Directory,
        [hashtable]$State,
        [datetime]$NowUtc
    )
    foreach ($entry in $Directory.EnumerateFileSystemInfos()) {
        $State.Items++
        if ($State.Items -gt 200000) { throw 'troppi elementi nella coda' }
        if (($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'reparse point nella coda'
        }
        if ($entry -is [System.IO.DirectoryInfo]) {
            Measure-Storage -Directory $entry -State $State -NowUtc $NowUtc
            continue
        }
        if ($entry -isnot [System.IO.FileInfo]) { throw 'elemento non classificabile' }
        $State.Bytes += $entry.Length
        $State.Files++
        if ($entry.Extension -ne '.flb') { continue }
        if ($entry.LastWriteTimeUtc -gt $NowUtc.AddMinutes(5)) {
            throw 'data futura di un chunk'
        }
        $State.Chunks++
        if ($null -eq $State.OldestUtc -or $entry.LastWriteTimeUtc -lt $State.OldestUtc) {
            $State.OldestUtc = $entry.LastWriteTimeUtc
        }
    }
}

try {
    if ($MaxQueueBytes -le 0 -or $MinFreeBytes -le 0 -or $MaxOldestChunkMinutes -le 0) {
        throw 'soglie assenti o non positive'
    }
    if ($RuntimeDir -notmatch '^[A-Za-z]:[\\/]') {
        throw 'runtime non su disco locale assoluto'
    }
    $runtime = [System.IO.Path]::GetFullPath($RuntimeDir)
    $storage = Join-Path $runtime 'storage'
    $directory = Get-Item -LiteralPath $storage -Force
    if ($directory -isnot [System.IO.DirectoryInfo]) { throw 'storage non e una directory' }
    if (($directory.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'storage e un reparse point'
    }

    $now = [datetime]::UtcNow
    $state = @{ Bytes = [long]0; Files = 0; Chunks = 0; Items = 0; OldestUtc = $null }
    Measure-Storage -Directory $directory -State $state -NowUtc $now

    $drive = New-Object System.IO.DriveInfo($runtime.Substring(0, 3))
    if (-not $drive.IsReady) { throw 'volume non disponibile' }
    $freeBytes = $drive.AvailableFreeSpace
    $oldestMinutes = -1
    if ($null -ne $state.OldestUtc) {
        $oldestMinutes = [math]::Max(0, [int][math]::Floor(($now - $state.OldestUtc).TotalMinutes))
    }
    $reasons = New-Object System.Collections.Generic.List[string]
    if ($state.Bytes -ge $MaxQueueBytes) { $reasons.Add('queue_bytes') }
    if ($freeBytes -le $MinFreeBytes) { $reasons.Add('free_bytes') }
    if ($oldestMinutes -ge $MaxOldestChunkMinutes) { $reasons.Add('oldest_chunk') }
    $status = if ($reasons.Count -gt 0) { 'alert' } else { 'ok' }
    $reason = if ($reasons.Count -gt 0) { $reasons -join ',' } else { '-' }
    Write-Output "status=$status reason=$reason queue_bytes=$($state.Bytes) files=$($state.Files) chunks=$($state.Chunks) oldest_chunk_minutes=$oldestMinutes free_bytes=$freeBytes"
    if ($reasons.Count -gt 0) { exit 2 }
    exit 0
} catch {
    Write-Output 'status=error reason=measurement_failed'
    exit 3
}
