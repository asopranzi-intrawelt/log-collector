<#
Preflight statico del bundle Fluent Bit Windows, senza installazione o rete.
Exit 0: controlli statici superati. Exit 3: controllo non riuscito.
Non verifica eventi Security, servizio, ACL o consegna degli allarmi.
#>
param(
    [string]$BundleDir,
    [string]$FluentBitExe
)

$ErrorActionPreference = 'Stop'
$phase = 'arguments'

function Require-LocalPath {
    param([string]$Path)
    if ($Path -notmatch '^[A-Za-z]:[\\/]') { throw 'percorso non locale assoluto' }
}

function Require-File {
    param([string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    if ($item -isnot [System.IO.FileInfo]) { throw 'file assente' }
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'file collegato'
    }
    return $item
}

function Get-Values {
    param([string]$Text, [string]$Key, [int]$Count)
    $pattern = '(?im)^[ \t]*' + [regex]::Escape($Key) + '[ \t]+([^\r\n#]+?)[ \t]*\r?$'
    $found = [regex]::Matches($Text, $pattern)
    if ($found.Count -ne $Count) { throw 'voce mancante o duplicata' }
    return @($found | ForEach-Object { $_.Groups[1].Value.Trim() })
}

try {
    Require-LocalPath $BundleDir
    Require-LocalPath $FluentBitExe
    $phase = 'bundle'
    $bundle = Get-Item -LiteralPath $BundleDir -Force
    if ($bundle -isnot [System.IO.DirectoryInfo]) { throw 'bundle assente' }
    if (($bundle.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'bundle collegato'
    }
    $config = Require-File (Join-Path $bundle.FullName 'fluent-bit.conf')
    $null = Require-File (Join-Path $bundle.FullName 'ads.lua')
    $null = Require-File (Join-Path $bundle.FullName 'ads-windows-queue-health.ps1')
    $null = Require-File (Join-Path $bundle.FullName 'ads-windows-service-state.ps1')
    $exe = Require-File $FluentBitExe

    $phase = 'configuration'
    $content = [System.IO.File]::ReadAllText($config.FullName)
    $outputs = [regex]::Matches(
        $content,
        '(?ms)^[ \t]*\[OUTPUT\][ \t]*\r?\n(?<body>.*?)(?=^[ \t]*\[[A-Za-z]+\]|\z)'
    )
    if ($outputs.Count -ne 2) { throw 'numero output inatteso' }
    $computerNames = @()
    $caPaths = @()
    foreach ($output in $outputs) {
        $body = $output.Groups['body'].Value
        $computerNames += (Get-Values $body 'Syslog_Hostname_Preset' 1)
        $caPaths += (Get-Values $body 'tls.ca_file' 1)
        foreach ($key in @('tls', 'tls.verify', 'tls.verify_hostname')) {
            if ((Get-Values $body $key 1) -ne 'on') { throw 'TLS non verificato' }
        }
        if ((Get-Values $body 'Retry_Limit' 1) -ne 'no_limits') {
            throw 'retry limitato'
        }
    }
    $storage = @(Get-Values $content 'storage.path' 1)
    $channels = @(Get-Values $content 'Channels' 1)
    $scripts = @(Get-Values $content 'Script' 1)
    if ($content -match '(?im)^[ \t]*storage\.total_limit_size[ \t]+') {
        throw 'limite di coda con possibile scarto'
    }
    if ($storage[0] -notmatch '^[A-Za-z]:[\\/]') { throw 'storage.path non assoluto' }
    if ($channels[0] -ne 'Security' -or $scripts[0] -ne 'ads.lua') {
        throw 'input o filtro inatteso'
    }
    if ($caPaths[0] -ne $caPaths[1]) { throw 'CA diverse nei due output' }

    $phase = 'computer'
    if (@($computerNames | Where-Object { $_ -ne [Environment]::MachineName }).Count -ne 0) {
        throw 'bundle per altra macchina'
    }

    $phase = 'ca'
    Require-LocalPath $caPaths[0]
    $ca = Require-File $caPaths[0]
    $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ca.FullName)
    try {
        $now = [datetime]::Now
        if ($certificate.NotBefore -gt $now -or $certificate.NotAfter -lt $now) {
            throw 'CA fuori validita'
        }
        $basic = @($certificate.Extensions | Where-Object {
            $_ -is [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]
        })
        if ($basic.Count -ne 1 -or -not $basic[0].CertificateAuthority) {
            throw 'certificato non CA'
        }
    } finally {
        $certificate.Dispose()
    }

    $phase = 'version'
    $nativePreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $versionOutput = & $exe.FullName --version 2>&1
        $versionExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $nativePreference
    }
    if ($versionExit -ne 0 -or ($versionOutput | Out-String) -notmatch '(?m)^Fluent Bit v5\.1\.3\s*$') {
        throw 'versione diversa'
    }

    $phase = 'dry_run'
    Push-Location -LiteralPath $bundle.FullName
    try {
        $nativePreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $dryOutput = & $exe.FullName --dry-run -c $config.FullName 2>&1
            $dryExit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $nativePreference
        }
    } finally {
        Pop-Location
    }
    if ($dryExit -ne 0 -or ($dryOutput | Out-String) -notmatch 'configuration test is successful') {
        throw 'configurazione rifiutata'
    }

    Write-Output 'status=static_ok version=5.1.3 service=unverified security=unverified delivery=unverified'
    exit 0
} catch {
    Write-Output "status=error phase=$phase"
    exit 3
}
