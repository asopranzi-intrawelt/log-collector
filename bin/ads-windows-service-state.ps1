<#
Controllo di sola lettura del servizio Fluent Bit sul pilota Windows.
Non stampa percorsi, nome macchina, identita' o riga di comando del processo.
Exit 0: servizio coerente; 2: servizio assente o diverso; 3: misura impossibile.
#>
param(
    [string]$BundleDir,
    [string]$FluentBitExe
)

$ErrorActionPreference = 'Stop'

function Test-WindowsPilotService {
    param([string]$BundleDir, [string]$FluentBitExe)

    if ($BundleDir -notmatch '^[A-Za-z]:[\\/]' -or
        $FluentBitExe -notmatch '^[A-Za-z]:[\\/]') {
        return [pscustomobject]@{ status = 'read_error'; reason = 'arguments' }
    }

    try {
        $bundle = Get-Item -LiteralPath $BundleDir -Force -ErrorAction Stop
        $exe = Get-Item -LiteralPath $FluentBitExe -Force -ErrorAction Stop
        $config = Get-Item -LiteralPath (Join-Path $bundle.FullName 'fluent-bit.conf') `
            -Force -ErrorAction Stop
        if ($bundle -isnot [System.IO.DirectoryInfo] -or
            $exe -isnot [System.IO.FileInfo] -or
            $config -isnot [System.IO.FileInfo] -or
            (($bundle.Attributes -bor $exe.Attributes -bor $config.Attributes) -band
                [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            return [pscustomobject]@{ status = 'read_error'; reason = 'files' }
        }
    } catch {
        return [pscustomobject]@{ status = 'read_error'; reason = 'files' }
    }

    try {
        $services = @(Get-CimInstance -ClassName Win32_Service `
            -Filter "Name='fluent-bit'" -ErrorAction Stop)
    } catch {
        return [pscustomobject]@{ status = 'read_error'; reason = 'service_query' }
    }
    if ($services.Count -eq 0) {
        return [pscustomobject]@{ status = 'incomplete'; reason = 'not_installed' }
    }
    if ($services.Count -ne 1) {
        return [pscustomobject]@{ status = 'read_error'; reason = 'service_query' }
    }
    $service = $services[0]
    if ([string]::IsNullOrWhiteSpace([string]$service.PathName) -or
        [string]::IsNullOrWhiteSpace([string]$service.StartName) -or
        [string]::IsNullOrWhiteSpace([string]$service.StartMode) -or
        [string]::IsNullOrWhiteSpace([string]$service.State)) {
        return [pscustomobject]@{ status = 'read_error'; reason = 'service_query' }
    }
    $expectedCommand = '"' + $exe.FullName + '" -c "' + $config.FullName + '"'
    if (-not [string]::Equals(([string]$service.PathName).Trim(), $expectedCommand,
        [StringComparison]::OrdinalIgnoreCase)) {
        return [pscustomobject]@{ status = 'incomplete'; reason = 'command' }
    }
    if ([string]$service.StartName -notin @('LocalSystem', 'NT AUTHORITY\SYSTEM')) {
        return [pscustomobject]@{ status = 'incomplete'; reason = 'identity' }
    }
    if ($service.StartMode -ne 'Auto') {
        return [pscustomobject]@{ status = 'incomplete'; reason = 'startup' }
    }
    $runningPid = 0
    if (-not [int]::TryParse([string]$service.ProcessId, [ref]$runningPid)) {
        return [pscustomobject]@{ status = 'read_error'; reason = 'service_query' }
    }
    if ($service.State -ne 'Running' -or $runningPid -le 0) {
        return [pscustomobject]@{ status = 'incomplete'; reason = 'stopped' }
    }

    try {
        $processes = @(Get-CimInstance -ClassName Win32_Process `
            -Filter "ProcessId=$runningPid" -ErrorAction Stop)
    } catch {
        return [pscustomobject]@{ status = 'read_error'; reason = 'process_query' }
    }
    if ($processes.Count -ne 1 -or
        [string]::IsNullOrWhiteSpace([string]$processes[0].ExecutablePath) -or
        [string]::IsNullOrWhiteSpace([string]$processes[0].CommandLine)) {
        return [pscustomobject]@{ status = 'read_error'; reason = 'process_query' }
    }
    if (
        -not [string]::Equals([string]$processes[0].ExecutablePath, $exe.FullName,
            [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([string]$processes[0].CommandLine, $expectedCommand,
            [StringComparison]::OrdinalIgnoreCase)) {
        return [pscustomobject]@{ status = 'incomplete'; reason = 'process' }
    }
    return [pscustomobject]@{ status = 'ok'; reason = 'matched' }
}

if ($MyInvocation.InvocationName -ne '.') {
    $report = Test-WindowsPilotService -BundleDir $BundleDir -FluentBitExe $FluentBitExe
    "status=$($report.status) reason=$($report.reason)"
    if ($report.status -eq 'ok') { exit 0 }
    if ($report.status -eq 'incomplete') { exit 2 }
    exit 3
}
