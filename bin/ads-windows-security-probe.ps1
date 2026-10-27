<#
Ricognizione di sola lettura dei GUID di audit e dello schema Security.
L'output JSON contiene solo GUID, ID evento, nomi di campo fissi e conteggi.
Non stampa i valori degli eventi, il nome del computer o l'output grezzo dei comandi.
Exit 0: tutti i campioni osservati; 2: campioni assenti; 3: lettura impossibile.
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

function Invoke-WindowsSecurityProbe {
    param([int]$WindowHours, [int]$Limit)

    $expectedGuids = @(
        '0CCE9215-69AE-11D9-BED3-505054503030',
        '0CCE9216-69AE-11D9-BED3-505054503030',
        '0CCE921B-69AE-11D9-BED3-505054503030',
        '0CCE9237-69AE-11D9-BED3-505054503030',
        '0CCE922F-69AE-11D9-BED3-505054503030'
    )
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
    $guids = @()
    foreach ($guid in $expectedGuids) {
        $present = $false
        if ($policyStatus -eq 'read') {
            $present = [regex]::IsMatch(
                $policyText,
                '(?i)(?<![0-9a-f])\{?' + [regex]::Escape($guid) + '\}?(?![0-9a-f])'
            )
        }
        $guids += [pscustomobject]@{ guid = $guid; present = $present }
    }

    $since = (Get-Date).AddHours(-$WindowHours)
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

    $status = 'observed'
    if ($policyStatus -ne 'read' -or @($guids | Where-Object { -not $_.present }).Count -gt 0) {
        $status = 'incomplete'
    }
    if (@($eventResults | Where-Object { $_.status -ne 'observed' }).Count -gt 0) {
        $status = 'incomplete'
    }
    if ($policyStatus -eq 'read_error' -or @($eventResults | Where-Object { $_.status -eq 'read_error' }).Count -gt 0) {
        $status = 'read_error'
    }
    return [pscustomobject]@{
        mode = 'live_read_only'
        status = $status
        window_hours = $WindowHours
        max_events_per_id = $Limit
        audit_guid_list_status = $policyStatus
        audit_policy_enabled = 'not_checked'
        audit_guids = $guids
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
