"""Il preflight conta i mittenti senza leggere o divulgare i loro log."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "ads-source-inventory.py"


def parameters(
    tmp_path: Path, *, firewall: str = "192.0.2.10", seeweb: str = "198.51.100.44"
) -> Path:
    path = tmp_path / "params.yaml"
    path.write_text(
        "sorgenti:\n"
        f'  firewall_usg_flex: "{firewall}"\n'
        '  nebula_switch_ap: []\n'
        '  qnap: ["192.0.2.20"]\n'
        '  ilo: []\n'
        '  proxmox_host: []\n'
        '  windows_pilota: []\n'
        f'  seeweb_opnsense: ["{seeweb}"]\n',
        encoding="utf-8",
    )
    return path


def run(params: Path, ads_root: Path) -> tuple[int, dict[str, int | str], str, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--parametri", str(params), "--ads-root", str(ads_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    return result.returncode, json.loads(lines[0]), result.stdout, result.stderr


def test_known_sources_and_local_are_only_clean_state(tmp_path: Path) -> None:
    params = parameters(tmp_path)
    archive = tmp_path / "ads"
    archive.mkdir()
    for name in ("127.0.0.1", "192.0.2.10", "192.0.2.20"):
        (archive / name).mkdir()
        (archive / name / "event.log").write_text("PRIVATE_PAYLOAD", encoding="utf-8")

    code, report, output, stderr = run(params, archive)

    assert code == 0
    assert report == {
        "status": "ok",
        "local": 1,
        "configured": 2,
        "unknown": 0,
        "seeweb_in_ads": 0,
        "unexpected_entries": 0,
    }
    assert "PRIVATE_PAYLOAD" not in output
    assert "192.0.2" not in output
    assert str(archive) not in output
    assert stderr == ""


def test_unknown_and_seeweb_are_anomalies_even_if_seeweb_is_configured(tmp_path: Path) -> None:
    params = parameters(tmp_path)
    archive = tmp_path / "ads"
    archive.mkdir()
    for name in ("192.0.2.10", "192.0.2.99", "198.51.100.44", "not-an-ip"):
        (archive / name).mkdir()
    (archive / "stray.txt").write_text("PRIVATE_PAYLOAD", encoding="utf-8")

    code, report, output, stderr = run(params, archive)

    assert code == 2
    assert report == {
        "status": "needs_reconciliation",
        "local": 0,
        "configured": 1,
        "unknown": 1,
        "seeweb_in_ads": 1,
        "unexpected_entries": 2,
    }
    for sensitive in ("192.0.2", "198.51", "not-an-ip", "stray.txt", "PRIVATE_PAYLOAD"):
        assert sensitive not in output
    assert stderr == ""


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("192.0.2.99", "unknown"),
        ("198.51.100.44", "seeweb_in_ads"),
        ("not-an-ip", "unexpected_entries"),
    ],
)
def test_each_anomaly_alone_fails_closed(tmp_path: Path, name: str, field: str) -> None:
    archive = tmp_path / "ads"
    archive.mkdir()
    (archive / "192.0.2.10").mkdir()
    (archive / name).mkdir()
    code, report, output, stderr = run(parameters(tmp_path), archive)
    assert code == 2
    assert report["status"] == "needs_reconciliation"
    assert report["configured"] == 1
    assert report[field] == 1
    assert name not in output
    assert stderr == ""


def test_empty_archive_is_not_a_success(tmp_path: Path) -> None:
    archive = tmp_path / "ads"
    archive.mkdir()
    code, report, _, stderr = run(parameters(tmp_path), archive)
    assert code == 2
    assert report["status"] == "needs_reconciliation"
    assert sum(value for value in report.values() if isinstance(value, int)) == 0
    assert stderr == ""


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_root_missing_or_not_a_directory_fails_measurement(tmp_path: Path, kind: str) -> None:
    archive = tmp_path / "ads"
    if kind == "file":
        archive.write_text("PRIVATE_PAYLOAD", encoding="utf-8")
    code, report, output, stderr = run(parameters(tmp_path), archive)
    assert code == 3
    assert report["status"] == "measurement_failed"
    assert "PRIVATE_PAYLOAD" not in output
    assert str(archive) not in output
    assert stderr == ""


@pytest.mark.parametrize("firewall", ["192.0.2.10;PRIVATE", "192.0.2.20", "127.0.0.1"])
def test_invalid_or_duplicate_config_fails_without_leak(tmp_path: Path, firewall: str) -> None:
    archive = tmp_path / "ads"
    archive.mkdir()
    (archive / "192.0.2.10").mkdir()
    code, report, output, stderr = run(parameters(tmp_path, firewall=firewall), archive)
    assert code == 3
    assert report["status"] == "measurement_failed"
    assert firewall not in output
    assert str(archive) not in output
    assert stderr == ""


def test_symlink_child_is_unexpected_without_following_it(tmp_path: Path) -> None:
    archive = tmp_path / "ads"
    archive.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "PRIVATE_PAYLOAD").write_text("payload", encoding="utf-8")
    try:
        (archive / "192.0.2.10").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink non disponibile: {type(exc).__name__}")
    code, report, output, stderr = run(parameters(tmp_path), archive)
    assert code == 2
    assert report["unexpected_entries"] == 1
    assert report["configured"] == 0
    assert "PRIVATE_PAYLOAD" not in output
    assert stderr == ""


def test_symlink_root_is_not_followed(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "192.0.2.10").mkdir()
    root_link = tmp_path / "ads"
    try:
        root_link.symlink_to(actual, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink non disponibile: {type(exc).__name__}")
    code, report, output, stderr = run(parameters(tmp_path), root_link)
    assert code == 3
    assert report["status"] == "measurement_failed"
    assert "192.0.2" not in output
    assert stderr == ""


def test_unreadable_archive_fails_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    spec = importlib.util.spec_from_file_location("ads_source_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = tmp_path / "ads"
    archive.mkdir()
    params = parameters(tmp_path)

    def denied(_path: object) -> object:
        raise PermissionError("PRIVATE_PATH")

    monkeypatch.setattr(module.os, "scandir", denied)
    code = module.main(["--parametri", str(params), "--ads-root", str(archive)])
    out = capsys.readouterr()
    assert code == 3
    assert json.loads(out.out)["status"] == "measurement_failed"
    assert "PRIVATE_PATH" not in out.out + out.err
