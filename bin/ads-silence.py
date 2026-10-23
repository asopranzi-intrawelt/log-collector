#!/usr/bin/env python3
"""Report daily source evidence without mistaking silence for an outage."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SIGNALS = {"daily_event", "daily_heartbeat"}
DEFAULT_POLICY = Path("/etc/ads/silence-policy.json")
DEFAULT_LOG_ROOT = Path("/srv/ads")
DEFAULT_HEARTBEAT_ROOT = Path("/var/lib/ads/heartbeats")


class PolicyError(ValueError):
    """Invalid or unsafe source policy."""


def _directory(path: Path) -> None:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise PolicyError("directory_invalid")


def load_policy(path: Path) -> list[dict[str, str]]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise PolicyError("policy_missing")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyError("policy_unreadable") from exc
    if (
        not isinstance(policy, dict)
        or type(policy.get("version")) is not int
        or policy["version"] != 1
    ):
        raise PolicyError("policy_version")
    sources = policy.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PolicyError("sources_empty")
    seen: set[str] = set()
    checked: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"id", "signal"}:
            raise PolicyError("source_invalid")
        source_id = source["id"]
        signal = source["signal"]
        if (
            not isinstance(source_id, str)
            or not SOURCE_ID.fullmatch(source_id)
            or ".." in source_id
            or source_id in seen
            or not isinstance(signal, str)
            or signal not in SIGNALS
        ):
            raise PolicyError("source_invalid")
        seen.add(source_id)
        checked.append({"id": source_id, "signal": signal})
    return checked


def _signal_file(path: Path) -> str:
    try:
        directory = path.parent
        if directory.is_symlink():
            return "unsafe_path"
        info = path.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "read_error"
    if not stat.S_ISREG(info.st_mode):
        return "unsafe_path"
    return "observed" if info.st_size > 0 else "empty"


def check_day(
    sources: list[dict[str, str]], day: str, log_root: Path, heartbeat_root: Path,
) -> dict[str, object]:
    _directory(log_root)
    # The heartbeat path may not exist until the first heartbeat arrives.
    if heartbeat_root.exists():
        _directory(heartbeat_root)
    results: list[dict[str, str]] = []
    for source in sources:
        signal = source["signal"]
        root = log_root if signal == "daily_event" else heartbeat_root
        extension = ".log" if signal == "daily_event" else ".heartbeat"
        raw = _signal_file(root / source["id"] / f"{day}{extension}")
        status = (
            "no_events" if raw in {"missing", "empty"} and signal == "daily_event"
            else "heartbeat_missing" if raw in {"missing", "empty"}
            else raw
        )
        results.append({"id": source["id"], "signal": signal, "status": status})
    return {
        "day": day,
        "checked": len(results),
        "status": "ok" if all(item["status"] == "observed" for item in results) else "alert",
        "sources": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--heartbeat-root", type=Path, default=DEFAULT_HEARTBEAT_ROOT)
    parser.add_argument("--day", help="Day to check, YYYY-MM-DD; default is yesterday in Rome")
    args = parser.parse_args(argv)
    if args.day is None:
        day = (datetime.now(ZoneInfo("Europe/Rome")) - timedelta(days=1)).date()
    else:
        try:
            day = datetime.strptime(args.day, "%Y-%m-%d").date()
        except ValueError:
            print("ads-silence: invalid_day", file=sys.stderr)
            return 3
        if day.isoformat() != args.day:
            print("ads-silence: invalid_day", file=sys.stderr)
            return 3
    try:
        report = check_day(
            load_policy(args.policy), day.isoformat(), args.log_root, args.heartbeat_root,
        )
    except PolicyError as exc:
        print(f"ads-silence: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
