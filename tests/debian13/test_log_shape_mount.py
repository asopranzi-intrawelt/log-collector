"""Prova CLI sul mount POSIX reale, con dati costruiti e senza rete."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/srv/ads")
SCRIPT = Path("/work/bin/ads-log-shape.py")
assert ROOT.is_mount(), "Il test richiede /srv/ads montato come tmpfs"
source = ROOT / "127.0.0.2"
source.mkdir()
(ROOT / "lost+found").mkdir()
(source / "2026-11-03.log").write_text(
    "2026-11-03T10:00:00+01:00 127.0.0.2 "
    "2026-11-03T10:00:00+01:00 NAS-TEST "
    "conn log: Users: <account>, Connection type: SMB\n",
    encoding="utf-8",
)
result = subprocess.run(
    [sys.executable, str(SCRIPT), "--ads-root", str(ROOT), "--date", "2026-11-03"],
    capture_output=True,
    text=True,
    check=False,
)
assert result.returncode == 0, result.stderr
report = json.loads(result.stdout)
assert report["status"] == "measured"
assert report["files"] == 1
assert report["lines"] == 1
assert report["sources"][0]["markers"]["qnap_smb_connection"] == 1
assert "<account>" not in result.stdout
print("MOUNT_CLI_OK")
