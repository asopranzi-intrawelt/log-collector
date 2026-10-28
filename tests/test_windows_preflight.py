"""Il preflight Windows rifiuta bundle e binario non coerenti prima del pilota."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import load_script

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "bin/ads-windows-pilot-preflight.ps1"
CA_FIXTURE = ROOT / "tests/fixtures/windows-preflight-ca.pem"
render = load_script("ads-render-windows.py")

pytestmark = pytest.mark.skipif(os.name != "nt", reason="richiede Windows PowerShell")


def bundle_for(tmp_path: Path, params_text: str) -> tuple[Path, Path]:
    params = tmp_path / "parametri.yaml"
    params.write_text(
        params_text.replace("elenco_approvato: []", 'elenco_approvato: ["EXAMPLE/ads_a"]'),
        encoding="utf-8",
    )
    ca = tmp_path / "ca.pem"
    ca.write_bytes(CA_FIXTURE.read_bytes())
    bundle = tmp_path / "bundle"
    code = render.main(
        [
            "--parametri", str(params),
            "--computer-name", os.environ["COMPUTERNAME"],
            "--destinazione", str(bundle),
            "--runtime-dir", (tmp_path / "runtime").as_posix(),
            "--ca-file", ca.as_posix(),
        ]
    )
    assert code == 0
    return bundle, ca


def fake_fluent_bit(path: Path, *, version: str = "5.1.3", dry_run: bool = True) -> Path:
    exe = path / "fluent-bit.cmd"
    dry = "echo configuration test is successful& exit /b 0" if dry_run else "exit /b 1"
    exe.write_text(
        "@echo off\n"
        f'if "%~1"=="--version" (echo Fluent Bit v{version}& exit /b 0)\n'
        'if not "%~1"=="--dry-run" exit /b 1\n'
        'if not "%~2"=="-c" exit /b 1\n'
        'if not exist "%~3" exit /b 1\n'
        'echo %~3 > "%ADS_TEST_PROBE%"\n'
        "echo Fluent Bit banner 1>&2\n"
        f"{dry}\n",
        encoding="ascii",
    )
    return exe


def preflight(bundle: Path | None, exe: Path | None, probe: Path):
    cmd = [
        shutil.which("powershell") or "powershell",
        "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", str(PREFLIGHT),
    ]
    if bundle is not None:
        cmd.extend(["-BundleDir", str(bundle)])
    if exe is not None:
        cmd.extend(["-FluentBitExe", str(exe)])
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env={**os.environ, "ADS_TEST_PROBE": str(probe)},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_bundle_valido_e_dry_run_raggiunto(tmp_path, params_text):
    bundle, _ = bundle_for(tmp_path, params_text)
    exe = fake_fluent_bit(tmp_path)
    probe = tmp_path / "seen.txt"

    result = preflight(bundle, exe, probe)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == (
        "status=static_ok version=5.1.3 service=unverified "
        "security=unverified delivery=unverified"
    )
    assert probe.read_text(encoding="utf-8").strip().casefold() == str(
        bundle / "fluent-bit.conf"
    ).casefold()
    assert "ads_a" not in result.stdout


def test_identita_ca_versione_e_dry_run_errati_falliscono(tmp_path, params_text):
    bundle, ca = bundle_for(tmp_path, params_text)
    exe = fake_fluent_bit(tmp_path)
    probe = tmp_path / "seen.txt"
    config = bundle / "fluent-bit.conf"
    original = config.read_text(encoding="utf-8")

    config.write_text(original.replace(os.environ["COMPUTERNAME"], "OTHER-PILOT"), encoding="utf-8")
    wrong_computer = preflight(bundle, exe, probe)
    assert wrong_computer.returncode == 3
    assert "phase=computer" in wrong_computer.stdout
    assert not probe.exists()
    config.write_text(original, encoding="utf-8")

    ca.write_text("invalid", encoding="ascii")
    wrong_ca = preflight(bundle, exe, probe)
    assert wrong_ca.returncode == 3
    assert "phase=ca" in wrong_ca.stdout
    ca.write_bytes(CA_FIXTURE.read_bytes())

    fake_fluent_bit(tmp_path, version="5.0.0")
    wrong_version = preflight(bundle, exe, probe)
    assert wrong_version.returncode == 3
    assert "phase=version" in wrong_version.stdout

    fake_fluent_bit(tmp_path, dry_run=False)
    wrong_config = preflight(bundle, exe, probe)
    assert wrong_config.returncode == 3
    assert "phase=dry_run" in wrong_config.stdout


def test_argomenti_assenti_falliscono_senza_prompt(tmp_path):
    missing = preflight(None, None, tmp_path / "seen.txt")
    assert missing.returncode == 3, missing.stdout + missing.stderr
    assert missing.stdout.strip() == "status=error phase=arguments"


def test_tls_verificato_in_entrambi_gli_output(tmp_path, params_text):
    bundle, _ = bundle_for(tmp_path, params_text)
    exe = fake_fluent_bit(tmp_path)
    probe = tmp_path / "seen.txt"
    config = bundle / "fluent-bit.conf"
    original = config.read_text(encoding="utf-8")
    key = "    tls.verify_hostname       on"
    assert original.count(key) == 2
    first = original.replace(key, "", 1)
    broken = first.replace(key, key + "\n" + key, 1)
    assert broken.count(key) == 2
    config.write_text(broken, encoding="utf-8")

    result = preflight(bundle, exe, probe)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "phase=configuration" in result.stdout
    assert not probe.exists()


def test_bookmark_fuori_runtime_viene_rifiutato(tmp_path, params_text):
    bundle, _ = bundle_for(tmp_path, params_text)
    exe = fake_fluent_bit(tmp_path)
    probe = tmp_path / "seen.txt"
    config = bundle / "fluent-bit.conf"
    original = config.read_text(encoding="utf-8")
    original_db = f"{(tmp_path / 'runtime').as_posix()}/winevtlog.sqlite"
    for new_db in (
        f"{(tmp_path / 'unprotected').as_posix()}/winevtlog.sqlite",
        f"{(tmp_path / 'runtime').as_posix()}/../runtime/winevtlog.sqlite",
    ):
        broken = original.replace(original_db, new_db)
        assert broken != original
        config.write_text(broken, encoding="utf-8")

        result = preflight(bundle, exe, probe)
        assert result.returncode == 3, result.stdout + result.stderr
        assert "phase=configuration" in result.stdout
        assert not probe.exists()
