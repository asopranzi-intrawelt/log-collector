"""Il monitor Windows distingue coda, spazio e misura indisponibile."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/ads-windows-queue-health.ps1"

pytestmark = pytest.mark.skipif(os.name != "nt", reason="richiede Windows PowerShell")


def config_for(directory: Path, storage: Path) -> Path:
    config = directory / "fluent-bit.conf"
    config.write_text(f"[SERVICE]\n    storage.path {storage.as_posix()}\n", encoding="utf-8")
    return config


def check(config: Path, *, queue: int = 1000, free: int = 1, oldest: int = 60):
    return subprocess.run(
        [
            shutil.which("powershell") or "powershell",
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
            "-ConfigFile", str(config),
            "-MaxQueueBytes", str(queue),
            "-MinFreeBytes", str(free),
            "-MaxOldestChunkMinutes", str(oldest),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_misura_della_coda_e_soglie(tmp_path):
    runtime = tmp_path / "runtime"
    storage = runtime / "storage"
    storage.mkdir(parents=True)
    config = config_for(tmp_path, storage)
    chunk = storage / "record.flb"
    chunk.write_bytes(b"0123456789")

    normal = check(config)
    assert normal.returncode == 0, normal.stdout + normal.stderr
    assert "status=ok" in normal.stdout
    assert "queue_bytes=10" in normal.stdout
    assert "chunks=1" in normal.stdout
    assert chunk.read_bytes() == b"0123456789"

    full = check(config, queue=10)
    assert full.returncode == 2, full.stdout + full.stderr
    assert "reason=queue_bytes" in full.stdout

    old_time = time.time() - 2 * 3600
    os.utime(chunk, (old_time, old_time))
    stale = check(config, oldest=60)
    assert stale.returncode == 2, stale.stdout + stale.stderr
    assert "reason=oldest_chunk" in stale.stdout

    metadata = storage / "metadata"
    metadata.write_bytes(b"x")
    chunk.unlink()
    os.utime(metadata, (old_time, old_time))
    no_chunk = check(config)
    assert no_chunk.returncode == 0, no_chunk.stdout + no_chunk.stderr
    assert "oldest_chunk_minutes=-1" in no_chunk.stdout


def test_spazio_e_misura_assente_non_danno_verde(tmp_path):
    runtime = tmp_path / "runtime"
    storage = runtime / "storage"
    storage.mkdir(parents=True)
    config = config_for(tmp_path, storage)
    low_space = check(config, free=2**63 - 1)
    assert low_space.returncode == 2, low_space.stdout + low_space.stderr
    assert "reason=free_bytes" in low_space.stdout

    missing = check(config_for(tmp_path, tmp_path / "missing" / "storage"))
    assert missing.returncode == 3, missing.stdout + missing.stderr
    assert "status=error reason=measurement_failed" in missing.stdout


def test_legge_la_coda_indicata_dalla_configurazione_attiva(tmp_path):
    default_storage = tmp_path / "runtime" / "storage"
    default_storage.mkdir(parents=True)
    active_storage = tmp_path / "other-runtime" / "storage"
    active_storage.mkdir(parents=True)
    (active_storage / "pending.flb").write_bytes(b"0123456789")
    config = config_for(tmp_path, active_storage)

    active = check(config, queue=10)
    assert active.returncode == 2, active.stdout + active.stderr
    assert "queue_bytes=10" in active.stdout
    assert "reason=queue_bytes" in active.stdout

    config.write_text("[SERVICE]\n    Flush 5\n", encoding="utf-8")
    no_storage = check(config)
    assert no_storage.returncode == 3, no_storage.stdout + no_storage.stderr


def test_parametri_assenti_falliscono_senza_prompt():
    missing = subprocess.run(
        [
            shutil.which("powershell") or "powershell",
            "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(SCRIPT),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert missing.returncode == 3, missing.stdout + missing.stderr
    assert missing.stdout.strip() == "status=error reason=measurement_failed"
