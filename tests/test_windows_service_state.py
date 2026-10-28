"""Il controllo del servizio confronta la configurazione realmente eseguita."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "bin/ads-windows-service-state.ps1"
pytestmark = pytest.mark.skipif(os.name != "nt", reason="richiede Windows PowerShell")


def quoted(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def run_fixture(tmp_path: Path, *, scenario: str = "ok", direct: bool = False):
    bundle = tmp_path / "Program Data" / "conf"
    bundle.mkdir(parents=True, exist_ok=True)
    config = bundle / "fluent-bit.conf"
    config.write_text("[SERVICE]\n", encoding="ascii")
    binary_dir = tmp_path / "Program Files"
    binary_dir.mkdir(exist_ok=True)
    exe = binary_dir / "fluent-bit.exe"
    exe.write_bytes(b"fixture")
    script = tmp_path / "fixture.ps1"
    invocation = (
        f"& {quoted(CHECK)} -BundleDir {quoted(bundle)} "
        f"-FluentBitExe {quoted(exe)}\nexit $LASTEXITCODE"
        if direct
        else f"$report = Test-WindowsPilotService -BundleDir {quoted(bundle)} "
        f"-FluentBitExe {quoted(exe)}\n$report | ConvertTo-Json -Compress"
    )
    script.write_text(
        f"""
. {quoted(CHECK)}
$expected = '"' + {quoted(exe)} + '" -c "' + {quoted(config)} + '"'
$scenario = '{scenario}'
function Get-CimInstance {{
    param($ClassName, $Filter)
    if ($scenario -eq 'query_error') {{ throw 'private-query-error' }}
    if ($ClassName -eq 'Win32_Service') {{
        if ($scenario -eq 'not_installed') {{ return }}
        $command = $expected
        if ($scenario -eq 'wrong_command') {{
            $command = '"C:\\private-host\\other.exe" -c "private"'
        }}
        $state = 'Running'
        if ($scenario -eq 'stopped') {{ $state = 'Stopped' }}
        $startName = 'LocalSystem'
        if ($scenario -eq 'wrong_identity') {{ $startName = 'private-user' }}
        $startMode = 'Auto'
        if ($scenario -eq 'manual_start') {{ $startMode = 'Manual' }}
        $pidValue = 1234
        if ($scenario -eq 'bad_pid') {{ $pidValue = 'private-invalid-pid' }}
        return [pscustomobject]@{{
            PathName = $command
            StartName = $startName
            StartMode = $startMode
            State = $state
            ProcessId = $pidValue
        }}
    }}
    if ($Filter -ne 'ProcessId=1234') {{ throw 'private-pid-filter-error' }}
    if ($scenario -eq 'missing_process') {{ return }}
    $command = $expected
    if ($scenario -eq 'wrong_process') {{ $command = '"C:\\private-host\\other.exe"' }}
    if ($scenario -eq 'hidden_process_command') {{ $command = $null }}
    return [pscustomobject]@{{
        ExecutablePath = {quoted(exe)}
        CommandLine = $command
    }}
}}
{invocation}
""",
        encoding="utf-8",
    )
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_running_service_uses_expected_binary_and_config(tmp_path):
    result = run_fixture(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "ok", "reason": "matched"}


@pytest.mark.parametrize(
    ("scenario", "reason"),
    [
        ("not_installed", "not_installed"),
        ("wrong_command", "command"),
        ("wrong_process", "process"),
        ("stopped", "stopped"),
        ("wrong_identity", "identity"),
        ("manual_start", "startup"),
    ],
)
def test_missing_or_stale_service_is_not_green(tmp_path, scenario, reason):
    result = run_fixture(tmp_path, scenario=scenario)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "incomplete", "reason": reason}
    assert "private-host" not in result.stdout


def test_unreadable_service_is_distinct_from_absence(tmp_path):
    for scenario in ("query_error", "bad_pid"):
        result = run_fixture(tmp_path / scenario, scenario=scenario)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {
            "status": "read_error",
            "reason": "service_query",
        }
        assert "private" not in result.stdout


def test_process_measurement_missing_is_read_error(tmp_path):
    for scenario in ("missing_process", "hidden_process_command"):
        result = run_fixture(tmp_path / scenario, scenario=scenario)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {
            "status": "read_error",
            "reason": "process_query",
        }


def test_command_exit_codes_are_stable(tmp_path):
    for scenario, code in (("ok", 0), ("not_installed", 2), ("query_error", 3)):
        result = run_fixture(tmp_path / scenario, scenario=scenario, direct=True)
        assert result.returncode == code, result.stderr
        assert "private" not in result.stdout


def test_missing_arguments_fail_without_prompt():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(CHECK)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 3, result.stderr
    assert result.stdout.strip() == "status=read_error reason=arguments"
