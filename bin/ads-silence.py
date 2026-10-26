#!/usr/bin/env python3
"""Report daily source evidence without mistaking silence for an outage."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SIGNALS = {"daily_event", "daily_heartbeat"}
DEFAULT_POLICY = Path("/etc/ads/silence-policy.json")
DEFAULT_LOG_ROOT = Path("/srv/ads")
DEFAULT_HEARTBEAT_ROOT = Path("/var/lib/ads/heartbeats")
MAX_LOOKBACK_DAYS = 213
MAX_REPORTED_ISSUES = 100


class PolicyError(ValueError):
    """Invalid or unsafe source policy."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("policy_duplicate_key")
        result[key] = value
    return result


def _directory(path: Path) -> None:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise PolicyError("directory_invalid")


def _day(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError("invalid_day") from exc
    if parsed.isoformat() != value:
        raise PolicyError("invalid_day")
    return parsed


def load_policy(path: Path) -> list[dict[str, str]]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise PolicyError("policy_missing")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyError("policy_unreadable") from exc
    if (
        not isinstance(policy, dict)
        or type(policy.get("version")) is not int
        or policy["version"] != 2
    ):
        raise PolicyError("policy_version")
    sources = policy.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PolicyError("sources_empty")
    seen: set[str] = set()
    checked: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"id", "signal", "active_from"}:
            raise PolicyError("source_invalid")
        source_id = source["id"]
        signal = source["signal"]
        active_from = source["active_from"]
        if (
            not isinstance(source_id, str)
            or not SOURCE_ID.fullmatch(source_id)
            or ".." in source_id
            or source_id in seen
            or not isinstance(signal, str)
            or signal not in SIGNALS
        ):
            raise PolicyError("source_invalid")
        try:
            _day(active_from)
        except PolicyError as exc:
            raise PolicyError("source_active_from_invalid") from exc
        seen.add(source_id)
        checked.append({"id": source_id, "signal": signal, "active_from": active_from})
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
    require_log_mount: bool = False,
) -> dict[str, object]:
    _day(day)
    _directory(log_root)
    if require_log_mount and not log_root.is_mount():
        raise PolicyError("log_mount_missing")
    # The heartbeat path may not exist until the first heartbeat arrives.
    if heartbeat_root.exists():
        _directory(heartbeat_root)
    results: list[dict[str, str]] = []
    for source in sources:
        if source["active_from"] > day:
            continue
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
    if not results:
        raise PolicyError("no_active_sources")
    return {
        "day": day,
        "checked": len(results),
        "status": "ok" if all(item["status"] == "observed" for item in results) else "alert",
        "sources": results,
    }


def check_window(
    sources: list[dict[str, str]], target: str, lookback_days: int,
    log_root: Path, heartbeat_root: Path, require_log_mount: bool = False,
) -> dict[str, object]:
    last_day = _day(target)
    if not 1 <= lookback_days <= MAX_LOOKBACK_DAYS:
        raise PolicyError("lookback_invalid")
    if not sources:
        raise PolicyError("sources_empty")
    first_active = min(_day(source["active_from"]) for source in sources)
    if first_active > last_day:
        raise PolicyError("no_active_sources")
    try:
        horizon_start = last_day - timedelta(days=lookback_days - 1)
    except OverflowError:
        horizon_start = date.min
    start = max(first_active, horizon_start)
    current = start
    checked = 0
    issue_count = 0
    issues: list[dict[str, str]] = []
    while current <= last_day:
        report = check_day(
            sources, current.isoformat(), log_root, heartbeat_root,
            require_log_mount=require_log_mount,
        )
        checked += report["checked"]
        for item in report["sources"]:
            if item["status"] == "observed":
                continue
            issue_count += 1
            if len(issues) < MAX_REPORTED_ISSUES:
                issues.append({"day": current.isoformat(), **item})
        if current == last_day:
            break
        current += timedelta(days=1)
    return {
        "day": target,
        "window_start": start.isoformat(),
        "checked_days": (last_day - start).days + 1,
        "checked": checked,
        "status": "alert" if issue_count else "ok",
        "issue_count": issue_count,
        "omitted_issues": issue_count - len(issues),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--heartbeat-root", type=Path, default=DEFAULT_HEARTBEAT_ROOT)
    parser.add_argument("--require-log-mount", action="store_true")
    parser.add_argument("--lookback-days", type=int, default=1)
    parser.add_argument("--day", help="Day to check, YYYY-MM-DD; default is yesterday in Rome")
    args = parser.parse_args(argv)
    try:
        day = (
            (datetime.now(ZoneInfo("Europe/Rome")) - timedelta(days=1)).date()
            if args.day is None else _day(args.day)
        )
        sources = load_policy(args.policy)
        if args.lookback_days == 1:
            report = check_day(
                sources, day.isoformat(), args.log_root, args.heartbeat_root,
                require_log_mount=args.require_log_mount,
            )
        else:
            report = check_window(
                sources, day.isoformat(), args.lookback_days,
                args.log_root, args.heartbeat_root,
                require_log_mount=args.require_log_mount,
            )
    except PolicyError as exc:
        print(f"ads-silence: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
