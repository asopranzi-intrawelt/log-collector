#!/usr/bin/env python3
"""Misura la verifica integrale AdS senza riportare nomi o contenuti dei log."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

VERIFIER = Path(__file__).with_name("ads-verify.sh")
MANIFEST_NAME = re.compile(r"manifest-[0-9]{4}-[0-9]{2}-[0-9]{2}\.txt\Z")
ARCHIVE_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\.log\.gz\Z")
ORIGINAL_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\.log\Z")


def _entries(path: Path) -> list[os.DirEntry[str]]:
    if not stat.S_ISDIR(path.stat(follow_symlinks=False).st_mode):
        raise ValueError("directory assente o collegata")
    with os.scandir(path) as iterator:
        return sorted(iterator, key=lambda entry: entry.name)


def _snapshot(log_root: Path, state_root: Path) -> tuple[dict[str, int], str]:
    digest = hashlib.sha256()
    counts = {
        "manifests": 0,
        "archives": 0,
        "archive_bytes": 0,
        "originals": 0,
        "original_bytes": 0,
    }

    def record(entry: os.DirEntry[str], kind: str, relative: str) -> None:
        info = entry.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("file non regolare")
        counts[kind] += 1
        if kind == "archives":
            counts["archive_bytes"] += info.st_size
        elif kind == "originals":
            counts["original_bytes"] += info.st_size
        digest.update(f"{relative}\0{info.st_ino}\0{info.st_size}\0{info.st_mtime_ns}\n".encode())

    for item in _entries(state_root / "manifests"):
        if MANIFEST_NAME.fullmatch(item.name):
            record(item, "manifests", f"manifests/{item.name}")

    for root, kind, name_pattern in (
        (state_root / "archives", "archives", ARCHIVE_NAME),
        (log_root, "originals", ORIGINAL_NAME),
    ):
        for source in _entries(root):
            if not source.is_dir(follow_symlinks=False):
                raise ValueError("sorgente non regolare")
            for item in _entries(Path(source.path)):
                if name_pattern.fullmatch(item.name):
                    record(item, kind, f"{kind}/{source.name}/{item.name}")
    return counts, digest.hexdigest()


def measure(log_root: Path, state_root: Path) -> tuple[dict[str, object], int]:
    import resource

    before, fingerprint = _snapshot(log_root, state_root)
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic_ns()
    result = subprocess.run(
        ["bash", str(VERIFIER)],
        env={**os.environ, "ADS_LOG_ROOT": str(log_root), "ADS_STATE_ROOT": str(state_root)},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    elapsed = (time.monotonic_ns() - started) / 1_000_000_000
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    after, fingerprint_after = _snapshot(log_root, state_root)
    stable = fingerprint == fingerprint_after and before == after
    if result.returncode != 0:
        status = "verification_failed_and_dataset_changed" if not stable else "verification_failed"
    else:
        status = "ok" if stable else "dataset_changed"
    report: dict[str, object] = {
        "status": status,
        "elapsed_seconds": round(elapsed, 3),
        "cpu_user_seconds": round(usage_after.ru_utime - usage_before.ru_utime, 3),
        "cpu_system_seconds": round(usage_after.ru_stime - usage_before.ru_stime, 3),
        "max_single_child_rss_kib": usage_after.ru_maxrss,
        "input_block_operations": usage_after.ru_inblock - usage_before.ru_inblock,
        "output_block_operations": usage_after.ru_oublock - usage_before.ru_oublock,
        **before,
    }
    return report, 0 if status == "ok" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-root", type=Path, default=Path("/srv/ads"))
    parser.add_argument("--state-root", type=Path, default=Path("/var/lib/ads"))
    args = parser.parse_args(argv)
    if sys.platform != "linux":
        print('{"status":"unsupported_platform"}')
        return 3
    try:
        report, code = measure(args.log_root, args.state_root)
    except (OSError, ValueError):
        print('{"status":"measurement_error"}')
        return 3
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
