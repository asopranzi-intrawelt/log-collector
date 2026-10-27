"""Il probe Windows misura solo schema e disponibilità, senza esportare valori."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "bin" / "ads-windows-security-probe.ps1"


def run_ps(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_ps_file(code: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "probe-fixture.ps1"
    path.write_text(code, encoding="utf-8")
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def fixture(
    *,
    missing: int | None = None,
    fail: int | None = None,
    no_match_error: int | None = None,
    wrong_field_case: bool = False,
    audit_braces: bool = True,
    direct: bool = False,
) -> str:
    behavior = ""
    if missing is not None:
        behavior += f"if ($FilterHashtable.Id -eq {missing}) {{ return }}\n"
    if fail is not None:
        behavior += f"if ($FilterHashtable.Id -eq {fail}) {{ throw 'private-error' }}\n"
    if no_match_error is not None:
        behavior += f"""
    if ($FilterHashtable.Id -eq {no_match_error}) {{
        $problem = New-Object System.Management.Automation.ErrorRecord `
            (New-Object System.Exception('private-no-match')), `
            'NoMatchingEventsFound', `
            ([System.Management.Automation.ErrorCategory]::ObjectNotFound), $null
        throw $problem
    }}
"""
    ip_field = "ipaddress" if wrong_field_case else "IpAddress"
    guids = (
        "0CCE9215-69AE-11D9-BED3-505054503030",
        "0CCE9216-69AE-11D9-BED3-505054503030",
        "0CCE921B-69AE-11D9-BED3-505054503030",
        "0CCE9237-69AE-11D9-BED3-505054503030",
        "0CCE922F-69AE-11D9-BED3-505054503030",
    )
    audit_guid_literals = ",\n      ".join(
        repr("{" + guid + "}" if audit_braces else guid) for guid in guids
    )
    final = (
        f"& '{PROBE.as_posix()}' -Hours 24 -MaxEventsPerId 2\nexit $LASTEXITCODE"
        if direct
        else "$report = Invoke-WindowsSecurityProbe -WindowHours 24 -Limit 2\n"
        "$report | ConvertTo-Json -Depth 6 -Compress"
    )
    return f"""
. '{PROBE.as_posix()}'
function auditpol.exe {{
    $global:LASTEXITCODE = 0
    @({audit_guid_literals})
}}
function Get-WinEvent {{
    param($FilterHashtable, $MaxEvents)
    {behavior}
    $eventRecord = [pscustomobject]@{{ Payload = @'
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><EventData>
<Data Name="TargetUserName">secret-account</Data>
<Data Name="TargetDomainName">secret-domain</Data>
<Data Name="SubjectUserName">secret-actor</Data>
<Data Name="SubjectDomainName">secret-subject-domain</Data>
<Data Name="LogonType">3</Data>
<Data Name="{ip_field}">192.0.2.42</Data>
</EventData></Event>
'@ }}
    $eventRecord | Add-Member -MemberType ScriptMethod -Name ToXml `
        -Value {{ $this.Payload }} -PassThru
}}
{final}
"""


def test_probe_reports_schema_without_identifying_values():
    result = run_ps(fixture())
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "observed"
    assert report["max_events_per_id"] == 2
    assert report["audit_policy_enabled"] == "not_checked"
    assert len(report["audit_guids"]) == 5
    assert all(item["present"] for item in report["audit_guids"])
    assert len(report["security_events"]) == 6
    assert all(item["complete_count"] == 1 for item in report["security_events"])
    assert all(item["required_fields"] for item in report["security_events"])
    assert report["security_events"][-1]["required_fields"] == [
        "SubjectUserName",
        "SubjectDomainName",
    ]
    assert "secret" not in result.stdout
    assert "192.0.2.42" not in result.stdout


def test_absent_event_is_incomplete_not_success():
    result = run_ps(fixture(missing=4648))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "incomplete"
    event = next(item for item in report["security_events"] if item["id"] == 4648)
    assert event["status"] == "not_observed"
    assert event["complete_count"] == 0


def test_field_name_case_mismatch_is_incomplete():
    result = run_ps(fixture(wrong_field_case=True))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "incomplete"
    event = next(item for item in report["security_events"] if item["id"] == 4624)
    assert event["status"] == "schema_incomplete"
    assert "IpAddress" not in event["seen_fields"]


def test_audit_guid_without_braces_is_detected():
    result = run_ps(fixture(audit_braces=False))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "observed"
    assert all(item["present"] for item in report["audit_guids"])


def test_no_matching_events_exception_is_not_read_error():
    result = run_ps(fixture(no_match_error=4648))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    event = next(item for item in report["security_events"] if item["id"] == 4648)
    assert event["status"] == "not_observed"
    assert "private-no-match" not in result.stdout


def test_security_read_error_is_not_mistaken_for_absence():
    result = run_ps(fixture(fail=4624))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "read_error"
    event = next(item for item in report["security_events"] if item["id"] == 4624)
    assert event["status"] == "read_error"
    assert "private-error" not in result.stdout


def test_command_exit_codes_match_observed_missing_and_read_error(tmp_path):
    for code, kwargs in ((0, {}), (2, {"missing": 4648}), (3, {"fail": 4624})):
        result = run_ps_file(fixture(direct=True, **kwargs), tmp_path)
        assert result.returncode == code, result.stderr
        assert "secret" not in result.stdout
        assert "private-error" not in result.stdout
