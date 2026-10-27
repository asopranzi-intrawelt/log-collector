<#
Ricognizione di sola lettura dell'audit e dello schema Security.
L'output JSON contiene solo GUID, bit di audit, ID, nomi di campo fissi e misure aggregate.
Non stampa i valori degli eventi, il nome del computer o l'output grezzo dei comandi.
Exit 0: policy, log e campioni osservati; 2: requisito incompleto; 3: lettura impossibile.
#>
param(
    [ValidateRange(1, 168)][int]$Hours = 24,
    [ValidateRange(1, 10)][int]$MaxEventsPerId = 3
)

$ErrorActionPreference = 'Stop'

function Get-EventFieldNames {
    param([string]$EventXml)
    $document = New-Object System.Xml.XmlDocument
    $document.XmlResolver = $null
    $document.LoadXml($EventXml)
    $names = @()
    foreach ($node in $document.SelectNodes("//*[local-name()='EventData']/*[local-name()='Data']")) {
        if ($node.HasAttribute('Name')) { $names += $node.GetAttribute('Name') }
    }
    return $names
}

function Get-AuditPolicySetting {
    param([string]$ReportCsv, [string]$Guid)
    $columns = @('machine', 'target', 'name', 'guid', 'inclusion', 'exclusion', 'setting')
    $rows = @(($ReportCsv -split '\r?\n' | Where-Object { $_.Trim() }) |
        ConvertFrom-Csv -Header $columns)
    $matchingRows = @($rows | Where-Object {
        $_.target -eq 'System' -and
        (($_.guid -replace '^\{', '') -replace '\}$', '') -ieq $Guid
    })
    if ($matchingRows.Count -ne 1) { throw 'riga GUID assente o duplicata' }
    $value = [string]$matchingRows[0].setting
    if ($value -notmatch '^[0-3]$') { throw 'valore audit non valido' }
    return [int]$value
}

function Invoke-WindowsSecurityProbe {
    param([int]$WindowHours, [int]$Limit)

    $expectedGuids = @(
        '0CCE9215-69AE-11D9-BED3-505054503030',
        '0CCE9216-69AE-11D9-BED3-505054503030',
        '0CCE921B-69AE-11D9-BED3-505054503030',
        '0CCE9237-69AE-11D9-BED3-505054503030',
        '0CCE922F-69AE-11D9-BED3-505054503030'
    )
    $requiredMasks = @(3, 1, 1, 1, 1)
    $required = [ordered]@{
        '4624' = @('TargetUserName', 'TargetDomainName', 'LogonType', 'IpAddress')
        '4625' = @('TargetUserName', 'TargetDomainName', 'LogonType', 'IpAddress')
        '4634' = @('TargetUserName', 'TargetDomainName', 'LogonType')
        '4647' = @('TargetUserName', 'TargetDomainName')
        '4648' = @('TargetUserName', 'TargetDomainName', 'SubjectUserName', 'SubjectDomainName')
        '4672' = @('SubjectUserName', 'SubjectDomainName')
    }

    $policyStatus = 'read_error'
    $policyText = ''
    try {
        $policyText = (& auditpol.exe /list /subcategory:* /v 2>$null | Out-String)
        if ($LASTEXITCODE -eq 0 -and $policyText.Length -gt 0) { $policyStatus = 'read' }
    } catch { }
    $policyReportStatus = 'read_error'
    $policyReport = ''
    try {
        $policyReport = (& auditpol.exe /get /subcategory:* /r 2>$null | Out-String)
        if ($LASTEXITCODE -eq 0 -and $policyReport.Length -gt 0) {
            $policyReportStatus = 'read'
        }
    } catch { }
    $guids = @()
    for ($index = 0; $index -lt $expectedGuids.Count; $index++) {
        $guid = $expectedGuids[$index]
        $present = $false
        if ($policyStatus -eq 'read') {
            $present = [regex]::IsMatch(
                $policyText,
                '(?i)(?<![0-9a-f])\{?' + [regex]::Escape($guid) + '\}?(?![0-9a-f])'
            )
        }
        $observedMask = $null
        if ($policyReportStatus -eq 'read') {
            try {
                $observedMask = Get-AuditPolicySetting -ReportCsv $policyReport -Guid $guid
            } catch {
                $policyReportStatus = 'parse_error'
            }
        }
        $enabled = $false
        if ($null -ne $observedMask) {
            $enabled = ($observedMask -band $requiredMasks[$index]) -eq $requiredMasks[$index]
        }
        $guids += [pscustomobject]@{
            guid = $guid
            present = $present
            required_mask = $requiredMasks[$index]
            observed_mask = $observedMask
            enabled = $enabled
        }
    }

    $policyEnabled = 'unknown'
    if ($policyReportStatus -eq 'read') {
        $policyEnabled = 'yes'
        if (@($guids | Where-Object { -not $_.enabled }).Count -gt 0) {
            $policyEnabled = 'no'
        }
    }

    $logMinimum = [long]268435456
    $logMaximum = $null
    $logFileSize = $null
    $logRecordCount = $null
    $logMode = 'unknown'
    $logStatus = 'read_error'
    try {
        $logConfiguration = Get-WinEvent -ListLog Security -ErrorAction Stop
        $logMaximum = [long]$logConfiguration.MaximumSizeInBytes
        if ($null -ne $logConfiguration.FileSize) {
            $logFileSize = [long]$logConfiguration.FileSize
        }
        if ($null -ne $logConfiguration.RecordCount) {
            $logRecordCount = [long]$logConfiguration.RecordCount
        }
        if ([string]$logConfiguration.LogMode -in @('Circular', 'AutoBackup', 'Retain')) {
            $logMode = [string]$logConfiguration.LogMode
        }
        if (-not $logConfiguration.IsEnabled) { $logStatus = 'disabled' }
        elseif ($logMaximum -lt $logMinimum) { $logStatus = 'below_minimum' }
        else { $logStatus = 'configured' }
    } catch {
        $logMaximum = $null
    }

    $observedAt = Get-Date
    $since = $observedAt.AddHours(-$WindowHours)
    $eventResults = @()
    foreach ($id in $required.Keys) {
        $status = 'observed'
        $sampleCount = 0
        $completeCount = 0
        $seen = @()
        try {
            $events = @(Get-WinEvent -FilterHashtable @{ LogName = 'Security'; Id = [int]$id; StartTime = $since } -MaxEvents $Limit -ErrorAction Stop)
            foreach ($eventRecord in $events) {
                $sampleCount++
                $fields = @(Get-EventFieldNames -EventXml $eventRecord.ToXml())
                $presentFields = @($required[$id] | Where-Object { $fields -ccontains $_ })
                $seen += $presentFields
                if ($presentFields.Count -eq $required[$id].Count) { $completeCount++ }
            }
            if ($sampleCount -eq 0) { $status = 'not_observed' }
            elseif ($completeCount -ne $sampleCount) { $status = 'schema_incomplete' }
        } catch {
            if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') {
                $status = 'not_observed'
            } else {
                $status = 'read_error'
            }
            $sampleCount = 0
            $completeCount = 0
            $seen = @()
        }
        $seen = @($required[$id] | Where-Object { $seen -ccontains $_ })
        $eventResults += [pscustomobject]@{
            id = [int]$id
            status = $status
            sample_count = $sampleCount
            complete_count = $completeCount
            required_fields = @($required[$id])
            seen_fields = $seen
        }
    }

    $historyStatus = 'read_error'
    $oldestAgeHours = $null
    $observedSpanHours = $null
    if ($logStatus -ne 'read_error') {
        try {
            $oldestRecords = @(Get-WinEvent -LogName Security -Oldest -MaxEvents 1 -ErrorAction Stop)
            $newestRecords = @(Get-WinEvent -LogName Security -MaxEvents 1 -ErrorAction Stop)
            if ($oldestRecords.Count -eq 0 -and $newestRecords.Count -eq 0 -and
                $logRecordCount -eq 0) {
                $historyStatus = 'empty'
            } elseif ($oldestRecords.Count -eq 1 -and $newestRecords.Count -eq 1 -and
                $null -ne $oldestRecords[0].TimeCreated -and
                $null -ne $newestRecords[0].TimeCreated) {
                $oldestTime = ([datetime]$oldestRecords[0].TimeCreated).ToUniversalTime()
                $newestTime = ([datetime]$newestRecords[0].TimeCreated).ToUniversalTime()
                $age = ($observedAt.ToUniversalTime() - $oldestTime).TotalHours
                $span = ($newestTime - $oldestTime).TotalHours
                if ($age -ge 0 -and $span -ge 0) {
                    $oldestAgeHours = [math]::Round($age, 2)
                    $observedSpanHours = [math]::Round($span, 2)
                    $historyStatus = 'observed'
                } else {
                    $historyStatus = 'time_inconsistent'
                }
            }
        } catch {
            if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*' -and
                $logRecordCount -eq 0) {
                $historyStatus = 'empty'
            }
        }
    }

    $status = 'observed'
    if ($policyStatus -ne 'read' -or $policyEnabled -ne 'yes' -or
        $logStatus -ne 'configured' -or $historyStatus -in @('empty', 'time_inconsistent') -or
        @($guids | Where-Object { -not $_.present }).Count -gt 0) {
        $status = 'incomplete'
    }
    if (@($eventResults | Where-Object { $_.status -ne 'observed' }).Count -gt 0) {
        $status = 'incomplete'
    }
    if ($policyStatus -eq 'read_error' -or $policyReportStatus -in @('read_error', 'parse_error') -or
        $logStatus -eq 'read_error' -or $historyStatus -eq 'read_error' -or
        @($eventResults | Where-Object { $_.status -eq 'read_error' }).Count -gt 0) {
        $status = 'read_error'
    }
    return [pscustomobject]@{
        mode = 'live_read_only'
        status = $status
        window_hours = $WindowHours
        max_events_per_id = $Limit
        audit_guid_list_status = $policyStatus
        audit_policy_query_status = $policyReportStatus
        system_audit_policy_enabled = $policyEnabled
        audit_guids = $guids
        security_log_capacity = [pscustomobject]@{
            status = $logStatus
            configured_max_bytes = $logMaximum
            required_min_bytes = $logMinimum
            file_size_bytes = $logFileSize
            record_count = $logRecordCount
            log_mode = $logMode
        }
        security_log_history = [pscustomobject]@{
            status = $historyStatus
            oldest_age_hours = $oldestAgeHours
            observed_span_hours = $observedSpanHours
        }
        security_events = $eventResults
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $report = Invoke-WindowsSecurityProbe -WindowHours $Hours -Limit $MaxEventsPerId
    $report | ConvertTo-Json -Depth 6 -Compress
    if ($report.status -eq 'observed') { exit 0 }
    if ($report.status -eq 'read_error') { exit 3 }
    exit 2
}
