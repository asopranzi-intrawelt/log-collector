#!/usr/bin/env python3
"""Conta i mittenti nell'archivio AdS senza leggere i file dei log.

L'inventario osservato è un preflight per riconciliare i parametri privati prima
di rendere esplicito l'instradamento rsyslog. Non prova identità, consegna,
completezza dei log o prontezza del filtro futuro sulla VM.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adsparams  # noqa: E402

CONFIGURED_KEYS = (
    "firewall_usg_flex",
    "nebula_switch_ap",
    "qnap",
    "ilo",
    "proxmox_host",
    "windows_pilota",
)
LOCAL = ipaddress.IPv4Address("127.0.0.1")


class QuietParser(argparse.ArgumentParser):
    """Rifiuta argomenti invalidi senza ripeterli su stderr."""

    def error(self, _message: str) -> None:
        raise ValueError("argomenti invalidi")


def _addresses(
    params: adsparams.Params,
) -> tuple[set[ipaddress.IPv4Address], set[ipaddress.IPv4Address]]:
    configured: set[ipaddress.IPv4Address] = set()
    seen: set[ipaddress.IPv4Address] = {LOCAL}
    for key in (*CONFIGURED_KEYS, "seeweb_opnsense"):
        value = adsparams.lookup(params, f"sorgenti.{key}")
        values = value if isinstance(value, list) else [value]
        for raw in values:
            if raw == "" and not isinstance(value, list):
                continue
            address = ipaddress.IPv4Address(raw)
            if address in seen:
                raise ValueError("indirizzo duplicato")
            seen.add(address)
            if key != "seeweb_opnsense":
                configured.add(address)
    return configured, seen - configured - {LOCAL}


def _empty(status: str) -> dict[str, str | int]:
    return {
        "status": status,
        "local": 0,
        "configured": 0,
        "unknown": 0,
        "seeweb_in_ads": 0,
        "unexpected_entries": 0,
    }


def _classify(
    entries: os.ScandirIterator[str],
    configured: set[ipaddress.IPv4Address],
    seeweb: set[ipaddress.IPv4Address],
) -> dict[str, str | int]:
    report = _empty("needs_reconciliation")
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
            report["unexpected_entries"] += 1
            continue
        try:
            address = ipaddress.IPv4Address(entry.name)
        except ValueError:
            report["unexpected_entries"] += 1
            continue
        if address == LOCAL:
            report["local"] += 1
        elif address in seeweb:
            report["seeweb_in_ads"] += 1
        elif address in configured:
            report["configured"] += 1
        else:
            report["unknown"] += 1
    if (report["local"] or report["configured"]) and not any(
        report[key] for key in ("unknown", "seeweb_in_ads", "unexpected_entries")
    ):
        report["status"] = "ok"
    return report


def scan(
    root: Path,
    configured: set[ipaddress.IPv4Address],
    seeweb: set[ipaddress.IPv4Address],
) -> dict[str, str | int]:
    """Classifica solo i figli immediati; su Linux apre la radice senza seguire link."""
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("archivio non regolare")
    if os.name == "posix":
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with os.scandir(fd) as entries:
                return _classify(entries, configured, seeweb)
        finally:
            os.close(fd)
    with os.scandir(root) as entries:
        return _classify(entries, configured, seeweb)


def main(argv: list[str] | None = None) -> int:
    parser = QuietParser(description=__doc__)
    parser.add_argument("--parametri", required=True, type=Path)
    parser.add_argument("--ads-root", required=True, type=Path)
    try:
        options = parser.parse_args(argv)
        configured, seeweb = _addresses(adsparams.load(options.parametri))
        report = scan(options.ads_root, configured, seeweb)
    except (OSError, UnicodeError, adsparams.ParamsError, ValueError):
        report = _empty("measurement_failed")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return {"ok": 0, "needs_reconciliation": 2, "measurement_failed": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
