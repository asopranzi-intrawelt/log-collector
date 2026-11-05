#!/usr/bin/env python3
"""Misura i file giornalieri del deposito AdS senza leggerne il contenuto."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import stat
import sys
from datetime import date, timedelta
from pathlib import Path

DAY_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.log$")


def measure(root: Path, through: date, days: int, *, require_mount: bool = False) -> dict:
    if days < 1 or days > 366:
        raise ValueError("days fuori intervallo")
    if through >= date.today():
        raise ValueError("through deve essere un giorno chiuso")
    if root.is_symlink() or not root.is_dir():
        raise ValueError("radice assente o simbolica")
    if require_mount and not root.is_mount():
        raise ValueError("archivio non montato")
    window = [through - timedelta(days=n) for n in range(days - 1, -1, -1)]
    sources = []
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name == "lost+found":
                if not entry.is_dir(follow_symlinks=False):
                    raise ValueError("lost+found non è una directory")
                with os.scandir(entry.path) as children:
                    if next(children, None) is not None:
                        raise ValueError("lost+found non è vuota")
                continue
            try:
                ipaddress.IPv4Address(entry.name)
            except ValueError as exc:
                raise ValueError("voce sorgente inattesa") from exc
            if not entry.is_dir(follow_symlinks=False):
                raise ValueError("sorgente non è una directory reale")
            files: dict[date, int] = {}
            with os.scandir(entry.path) as children:
                for child in children:
                    match = DAY_FILE.fullmatch(child.name)
                    if match is None:
                        raise ValueError("nome file giornaliero inatteso")
                    if not child.is_file(follow_symlinks=False):
                        raise ValueError("file giornaliero non regolare")
                    day = date.fromisoformat(match.group(1))
                    if day > through:
                        continue  # Il giorno in corso non entra nella profondità misurata.
                    info = child.stat(follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode) or info.st_size < 0:
                        raise ValueError("file giornaliero invalido")
                    files[day] = info.st_size
            dates = sorted(files)
            daily = [
                {"date": day.isoformat(), "present": day in files, "bytes": files.get(day, 0)}
                for day in window
            ]
            sources.append(
                {
                    "source": entry.name,
                    "first_file": dates[0].isoformat() if dates else None,
                    "last_file": dates[-1].isoformat() if dates else None,
                    "files_through": len(dates),
                    "calendar_span_days": (dates[-1] - dates[0]).days + 1 if dates else 0,
                    "window_bytes": sum(files.get(day, 0) for day in window),
                    "days_without_file_window": [
                        day.isoformat() for day in window if day not in files
                    ],
                    "daily": daily,
                }
            )
    sources.sort(key=lambda row: ipaddress.IPv4Address(row["source"]))
    return {
        "status": "metadata_measured_requires_review",
        "through": through.isoformat(),
        "window_days": days,
        "window_bytes": sum(row["window_bytes"] for row in sources),
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ads-root", type=Path, default=Path("/srv/ads"))
    parser.add_argument("--through", required=True, type=date.fromisoformat)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    try:
        result = measure(
            args.ads_root,
            args.through,
            args.days,
            require_mount=args.ads_root == Path("/srv/ads"),
        )
    except (OSError, ValueError) as exc:
        print(f"Misura non valida: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
