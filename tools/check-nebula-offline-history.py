#!/usr/bin/env python3
"""Cerca nel cloud record locali datati dentro intervalli dichiarati offline.

Un controllo noto e al massimo due finestre storiche, tre POST complessivi.
Concordanza su timestamp, priorità, tag e testo; non prova continuità AdS.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = spec_from_file_location("offline_windows", ROOT / "tools/check-nebula-windows.py")
windows = module_from_spec(spec)
spec.loader.exec_module(windows)
LOCAL_FIELDS = ("timestamp", "priority", "tag", "message")
PADDING_MS = 600_000


def signature(row):
    return tuple(row[field] for field in LOCAL_FIELDS)


def plan(snapshot, cached, reference):
    if reference["source_model"] != "XGS2220-30HP":
        raise windows.history.EvidenceError("reference_model")
    candidates = [
        device["devId"]
        for organization in snapshot["organizations"]
        for site in organization["sites"]
        for device in site["devices"]
        if device.get("type") == "SW" and device.get("model") == reference["source_model"]
    ]
    if len(candidates) != 1 or not cached.get(candidates[0]):
        raise windows.history.EvidenceError("reference_target")
    device = candidates[0]
    _, target = windows.resolve_targets(snapshot, {device: cached[device]})[0]
    intervals, rows = reference["intervals"], reference["references"]
    if not isinstance(intervals, list) or not 1 <= len(intervals) <= 2 or not rows:
        raise windows.history.EvidenceError("reference_intervals")
    bounds = []
    for interval in intervals:
        left, right = interval["begin_ms"], interval["end_ms"]
        if type(left) is not int or type(right) is not int or not 0 < left < right:
            raise windows.history.EvidenceError("reference_time")
        if right - left > 3_600_000:
            raise windows.history.EvidenceError("reference_window_too_large")
        bounds.append((left, right))
    if len(set(bounds)) != len(bounds):
        raise windows.history.EvidenceError("reference_duplicate_interval")
    for row in rows:
        point = row["timestamp"]
        if type(point) is not int or not any(left <= point <= right for left, right in bounds):
            raise windows.history.EvidenceError("reference_outside_offline")
        for field in LOCAL_FIELDS[1:]:
            value = row[field]
            if (
                not isinstance(value, str)
                or not value
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                raise windows.history.EvidenceError("reference_field")
    if any(not any(left <= row["timestamp"] <= right for row in rows) for left, right in bounds):
        raise windows.history.EvidenceError("reference_empty_interval")
    return device, target, bounds, rows


def measure(client, snapshot, cached, reference, output, now=None):
    now = now or (lambda: datetime.now(UTC))
    device, target, bounds, expected = plan(snapshot, cached, reference)
    windows.write_private(output / "private-target.json", target)
    observations = []

    def fetch(label, left, right):
        requested = now()
        response = client.fetch(target, left, right)
        received = now()
        windows.write_private(output / f"{label}.json", response)
        meta = {
            "ordinal": len(observations) + 1,
            "label": label,
            "query_start_ms": left,
            "query_end_ms": right,
            "requested_at": requested.isoformat(),
            "received_at": received.isoformat(),
        }
        try:
            if received < requested:
                raise windows.history.EvidenceError("offline_history_clock_backwards")
            rows = windows.poller.validate_events(response, target, left, right)
            meta["rows"] = len(rows)
        except (windows.history.EvidenceError, windows.poller.PollError) as exc:
            meta.update(rows=None, validation_error=str(exc))
            windows.write_private(output / f"{label}-meta.json", meta)
            raise
        windows.write_private(output / f"{label}-meta.json", meta)
        observations.append(meta)
        return rows

    control_reference = max(cached[device], key=lambda row: row["timestamp"])
    point = control_reference["timestamp"]
    control = fetch("control", point - 1000, point + 1000)
    present = windows.history.digest(control_reference) in windows.signatures(control)
    results = []
    threshold = len(control) >= 1000
    for index, (left, right) in enumerate(bounds, 1):
        rows = fetch(f"window-{index}", left - PADDING_MS, right + PADDING_MS)
        known = [row for row in expected if left <= row["timestamp"] <= right]
        wanted, returned = {signature(row) for row in known}, {signature(row) for row in rows}
        matched = wanted & returned
        threshold = threshold or len(rows) >= 1000
        results.append(
            {
                "begin_ms": left,
                "end_ms": right,
                "local_rows": len(known),
                "local_unique": len(wanted),
                "local_duplicates": len(known) - len(wanted),
                "cloud_rows": len(rows),
                "matched_local_unique": len(matched),
                "missing_local_unique": len(wanted - returned),
                "known_authentication_rows": sum(row["tag"] == "authentication" for row in known),
            }
        )
    missing = sum(row["missing_local_unique"] for row in results)
    if not present:
        status = "control_missing"
    elif threshold:
        status = "response_threshold_reached"
    elif missing:
        status = "reference_not_fully_available_now"
    else:
        status = "matched_local_reference"
    return {
        "acquired_at": now().isoformat(),
        "control_present": present,
        "requests": len(observations),
        "request_budget": 1 + len(bounds),
        "windows": results,
        "observations": observations,
        "status": status,
        "matched_local_unique": sum(row["matched_local_unique"] for row in results),
        "missing_local_unique": missing,
        "ok": status == "matched_local_reference",
        "scope": (
            "local_records_timestamped_in_reported_cloud_offline_intervals_visible_now; "
            "ads_continuity_unverified"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cache", "snapshot", "reference", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--key-stdin", action="store_true", required=True)
    args = parser.parse_args(argv)
    client = None
    try:
        cached = windows.history.read_switches(args.cache)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        reference = json.loads(args.reference.read_text(encoding="utf-8-sig"))
        plan(snapshot, cached, reference)
        args.output.mkdir(parents=False, exist_ok=False)
        key = sys.stdin.readline(4097).rstrip("\r\n")
        if not key or len(key) > 4096 or any(char.isspace() for char in key):
            raise windows.history.EvidenceError("key_input")
        client = windows.poller.NebulaClient(key)
        key = None
        report = measure(client, snapshot, cached, reference, args.output)
        windows.write_private(args.output / "comparison.json", report)
        status = 0 if report["ok"] else 1
        detail = (
            f"status={report['status']} requests={report['requests']} "
            f"matched_local_unique={report['matched_local_unique']} "
            f"missing_local_unique={report['missing_local_unique']} ads_continuity=unverified"
        )
    except (windows.history.EvidenceError, windows.poller.PollError) as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError):
        detail, status = "status=error code=local_input_or_schema", 1
    finally:
        if client is not None:
            client.close()
    stamp = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{stamp} nebula-check {stamp} nebula-offline-history {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
