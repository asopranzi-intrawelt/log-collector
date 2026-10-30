#!/usr/bin/env python3
"""Misura la ricezione del pilot Seeweb senza esporre IP o messaggi."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path

TECHNICAL_ROOT = Path("/var/log/ads-seeweb-technical")
ADS_ROOT = Path("/srv/ads")
MAX_FILE_BYTES = 64 * 1024 * 1024
DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)


class MeasurementError(Exception):
    pass


def interval(start_raw: str, end_raw: str) -> tuple[datetime, datetime, tuple[str, ...]]:
    start = datetime.fromisoformat(start_raw)
    end = datetime.fromisoformat(end_raw)
    if (
        start.utcoffset() is None
        or end.utcoffset() is None
        or not start < end <= start + timedelta(hours=2)
    ):
        raise MeasurementError("intervallo invalido")
    dates = []
    day = start.astimezone().date()
    last_day = end.astimezone().date()
    while day <= last_day:
        dates.append(day.isoformat())
        day += timedelta(days=1)
    if len(dates) > 2:
        raise MeasurementError("intervallo di giorni inatteso")
    return start, end, tuple(dates)


def open_directory(name: str | Path, parent: int | None = None) -> int | None:
    try:
        descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=parent)
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise MeasurementError("directory non regolare")
    return descriptor


def count_day(
    source_dir: int, day: str, source: str, start: datetime, end: datetime
) -> tuple[int, int, datetime | None, datetime | None, bool]:
    try:
        descriptor = os.open(f"{day}.log", FILE_FLAGS, dir_fd=source_dir)
    except FileNotFoundError:
        return 0, 0, None, None, False
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise MeasurementError("file non regolare")
        if info.st_size > MAX_FILE_BYTES:
            raise MeasurementError("file oltre il limite di misura")
        events = malformed = 0
        first = last = None
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            consumed = 0
            while True:
                raw = stream.readline(MAX_FILE_BYTES - consumed + 1)
                if not raw:
                    break
                consumed += len(raw)
                if consumed > MAX_FILE_BYTES:
                    raise MeasurementError("file cresciuto oltre il limite di misura")
                try:
                    parts = raw.decode("utf-8").split(" ", 2)
                    if len(parts) != 3 or parts[1] != source:
                        raise ValueError("forma o sorgente")
                    received = datetime.fromisoformat(parts[0])
                    if received.utcoffset() is None:
                        raise ValueError("ora senza fuso")
                except (UnicodeError, ValueError):
                    malformed += 1
                    continue
                if start <= received <= end:
                    events += 1
                    first = received if first is None else min(first, received)
                    last = received if last is None else max(last, received)
        return events, malformed, first, last, True
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def measure_root(
    root: Path, source: str, dates: tuple[str, ...], start: datetime, end: datetime
) -> tuple[int, int, datetime | None, datetime | None, bool]:
    base = open_directory(root)
    if base is None:
        return 0, 0, None, None, False
    try:
        source_dir = open_directory(source, base)
        if source_dir is None:
            return 0, 0, None, None, False
        try:
            events = malformed = 0
            first = last = None
            present = False
            for day in dates:
                count, invalid, early, late, exists = count_day(
                    source_dir, day, source, start, end
                )
                events += count
                malformed += invalid
                present = present or exists
                if early is not None:
                    first = early if first is None else min(first, early)
                    last = late if last is None else max(last, late)
            return events, malformed, first, last, present
        finally:
            os.close(source_dir)
    finally:
        os.close(base)


def measure(
    manifest: Path, start_raw: str, end_raw: str,
    technical_root: Path = TECHNICAL_ROOT, ads_root: Path = ADS_ROOT,
) -> dict[str, object]:
    if os.name != "posix":
        raise MeasurementError("richiede Linux")
    info = manifest.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise MeasurementError("manifesto non regolare")
    source = str(ipaddress.IPv4Address(json.loads(manifest.read_text(encoding="utf-8"))["source"]))
    start, end, dates = interval(start_raw, end_raw)
    technical = measure_root(technical_root, source, dates, start, end)
    ads = measure_root(ads_root, source, dates, start, end)
    status = (
        "needs_review" if technical[1] or ads[1] or ads[0]
        else "observed" if technical[0]
        else "not_observed"
    )
    return {
        "status": status,
        "technical_events": technical[0],
        "ads_events": ads[0],
        "malformed_lines": technical[1] + ads[1],
        "technical_file_present": technical[4],
        "ads_file_present": ads[4],
        "first_received": technical[2].isoformat() if technical[2] else None,
        "last_received": technical[3].isoformat() if technical[3] else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    options = parser.parse_args(argv)
    try:
        report = measure(options.manifest, options.start, options.end)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, MeasurementError):
        report = {"status": "measurement_failed"}
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return {"observed": 0, "not_observed": 2, "needs_review": 2, "measurement_failed": 3}[
        report["status"]
    ]


if __name__ == "__main__":
    raise SystemExit(main())
