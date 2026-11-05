#!/usr/bin/env python3
"""Conta marcatori noti nei log AdS di un giorno senza emettere messaggi.

L'output contiene indirizzi delle sorgenti e va conservato nel livello privato.
I marcatori sono indizi di formato, non una classificazione AdS approvata.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import stat
from pathlib import Path

ROOT = Path("/srv/ads")
MAX_SOURCES = 64
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 64 * 1024
DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)

# Stringhe osservate nei runbook dei quattro NAS, del firewall e di Proxmox.
# I conteggi possono sovrapporsi; la quota senza marcatori va sempre letta.
MARKERS: dict[str, tuple[bytes, ...]] = {
    "qnap_connection_log": (b"conn log:",),
    "qnap_event_log": (b"event log:",),
    "qnap_admin_resource": (b"Accessed resources: Administration",),
    "qnap_smb_connection": (b"Connection type: SMB",),
    "qnap_samba_connection": (b"Connection type: SAMBA",),
    "qnap_http_connection": (b"Connection type: HTTP",),
    "qnap_ssh_connection": (b"Connection type: SSH",),
    "qnap_login_success": (b"Action: Login Success", b"Action: Login OK"),
    "qnap_login_failure": (b"Action: Login Fail", b"Failed to log in via user account"),
    "qnap_logout": (b"Action: Logout",),
    "qnap_read": (b"Action: Read",),
    "firewall_user_category": (b'cat="User"',),
    "firewall_system_category": (b'cat="System"',),
    "host_auth_hint": (b"pvedaemon", b"sshd", b"/access/ticket"),
}

CORRELATIONS = (
    "qnap_admin_login_success",
    "qnap_admin_login_failure",
    "qnap_smb_login_success",
    "qnap_smb_login_failure",
    "qnap_admin_smb_overlap",
    "qnap_login_without_context",
)


def _empty_source(source: str) -> dict[str, object]:
    return {
        "source": source,
        "file_present": False,
        "bytes": 0,
        "lines": 0,
        "unmatched_lines": 0,
        "markers": {name: 0 for name in MARKERS},
        "correlations": {name: 0 for name in CORRELATIONS},
    }


def _scan_file(source_fd: int, filename: str, report: dict[str, object]) -> None:
    try:
        descriptor = os.open(filename, FILE_FLAGS, dir_fd=source_fd)
    except FileNotFoundError:
        return
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("file non regolare o con link multipli")
        if before.st_size > MAX_FILE_BYTES:
            raise ValueError("file oltre il limite di misura")
        report["file_present"] = True
        markers = report["markers"]
        correlations = report["correlations"]
        assert isinstance(markers, dict)
        assert isinstance(correlations, dict)
        for line in stream:
            report["bytes"] += len(line)
            report["lines"] += 1
            if len(line) > MAX_LINE_BYTES or report["bytes"] > MAX_FILE_BYTES:
                raise ValueError("riga o file oltre il limite di misura")
            found: set[str] = set()
            for name, forms in MARKERS.items():
                if any(form in line for form in forms):
                    markers[name] += 1
                    found.add(name)
            if not found:
                report["unmatched_lines"] += 1
            if "qnap_connection_log" in found:
                admin = "qnap_admin_resource" in found
                smb = bool({"qnap_smb_connection", "qnap_samba_connection"} & found)
                success = "qnap_login_success" in found
                failure = "qnap_login_failure" in found
                if admin and success:
                    correlations["qnap_admin_login_success"] += 1
                if admin and failure:
                    correlations["qnap_admin_login_failure"] += 1
                if smb and success:
                    correlations["qnap_smb_login_success"] += 1
                if smb and failure:
                    correlations["qnap_smb_login_failure"] += 1
                if admin and smb:
                    correlations["qnap_admin_smb_overlap"] += 1
                if (success or failure) and not (admin or smb):
                    correlations["qnap_login_without_context"] += 1
        after = os.fstat(stream.fileno())
        def snapshot(value: os.stat_result) -> tuple[int, int, int, int, int]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )
        if snapshot(before) != snapshot(after) or report["bytes"] != after.st_size:
            raise ValueError("file cambiato durante la misura")


def scan(root: Path, day: dt.date) -> dict[str, object]:
    """Scansiona solo i file del giorno nelle directory IPv4 immediate."""
    root_fd = os.open(root, DIR_FLAGS)
    try:
        entries: list[tuple[ipaddress.IPv4Address, str]] = []
        with os.scandir(root_fd) as children:
            for entry in children:
                if entry.name == "lost+found":
                    if not entry.is_dir(follow_symlinks=False):
                        raise ValueError("voce di filesystem inattesa")
                    lost_fd = os.open(entry.name, DIR_FLAGS, dir_fd=root_fd)
                    try:
                        with os.scandir(lost_fd) as recovered:
                            if next(recovered, None) is not None:
                                raise ValueError("voce di filesystem non vuota")
                    finally:
                        os.close(lost_fd)
                    continue
                if not entry.is_dir(follow_symlinks=False):
                    raise ValueError("voce sorgente non regolare")
                address = ipaddress.IPv4Address(entry.name)
                entries.append((address, entry.name))
        if len(entries) > MAX_SOURCES:
            raise ValueError("troppe sorgenti")
        reports = []
        for _, source in sorted(entries):
            source_fd = os.open(source, DIR_FLAGS, dir_fd=root_fd)
            try:
                report = _empty_source(source)
                _scan_file(source_fd, f"{day.isoformat()}.log", report)
                reports.append(report)
            finally:
                os.close(source_fd)
        total_lines = sum(item["lines"] for item in reports)
        return {
            "status": "measured" if total_lines else "no_data",
            "date": day.isoformat(),
            "sources": reports,
            "files": sum(bool(item["file_present"]) for item in reports),
            "lines": total_lines,
            "bytes": sum(item["bytes"] for item in reports),
        }
    finally:
        os.close(root_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ads-root", type=Path, default=ROOT)
    parser.add_argument("--date", required=True)
    options = parser.parse_args(argv)
    try:
        day = dt.date.fromisoformat(options.date)
        if (
            day.isoformat() != options.date
            or day >= dt.date.today()
            or not options.ads_root.is_mount()
        ):
            raise ValueError("data aperta o mount non valido")
        result = scan(options.ads_root, day)
    except (OSError, ValueError):
        result = {"status": "measurement_failed"}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return {"measured": 0, "no_data": 2, "measurement_failed": 3}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
