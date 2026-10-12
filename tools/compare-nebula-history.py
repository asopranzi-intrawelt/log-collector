#!/usr/bin/env python3
"""Confronta accessi Nebula registrati senza stampare messaggi o identificativi."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

FIELDS = ("timestamp", "category", "devId", "mac", "message", "priority", "tag")


class EvidenceError(Exception):
    """Codice pubblico dell'errore di confronto."""


def read_switches(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not data:
        raise EvidenceError("switches_missing")
    switches = {}
    for switch in data:
        if not isinstance(switch, dict) or not isinstance(switch.get("DevId"), str):
            raise EvidenceError("switch_schema")
        device = switch["DevId"]
        if not device or device in switches:
            raise EvidenceError("switch_duplicate_or_empty")
        raw = switch.get("EventLogs")
        # Count/value è un contenitore del consumer PowerShell, non dell'API.
        if isinstance(raw, dict):
            events = raw.get("value")
            if type(raw.get("Count")) is not int or not isinstance(events, list):
                raise EvidenceError("events_wrapper")
            if raw["Count"] != len(events):
                raise EvidenceError("events_count")
        else:
            events = raw
        if not isinstance(events, list):
            raise EvidenceError("events_missing")
        for event in events:
            if not isinstance(event, dict) or any(k not in event for k in FIELDS):
                raise EvidenceError("event_schema")
            if type(event["timestamp"]) is not int or event["timestamp"] <= 0:
                raise EvidenceError("event_time")
            if any(not isinstance(event[k], str) or not event[k] for k in FIELDS[1:]):
                raise EvidenceError("event_schema")
            if event["devId"] != device:
                raise EvidenceError("event_device")
        switches[device] = events
    return switches


def digest(event):
    raw = json.dumps([event[k] for k in FIELDS], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compare(reference, candidate, acquired_at):
    if acquired_at.tzinfo is None:
        raise EvidenceError("acquisition_timezone")
    expected = [
        event
        for events in reference.values()
        for event in events
        if event["category"] == "AAA" and event["tag"] == "authentication"
    ]
    if not expected:
        raise EvidenceError("reference_authentication_missing")
    if any(device not in candidate for device in reference):
        raise EvidenceError("candidate_switch_missing")
    available = {digest(event) for events in candidate.values() for event in events}
    results = []
    for event in sorted(expected, key=lambda e: e["timestamp"]):
        declared = datetime.fromtimestamp(event["timestamp"] / 1000, UTC)
        if declared > acquired_at:
            raise EvidenceError("acquisition_before_event")
        results.append(
            {
                "declared_at": declared.isoformat(timespec="milliseconds"),
                "age_hours": round((acquired_at - declared).total_seconds() / 3600, 6),
                "exact_match": digest(event) in available,
            }
        )
    matches = [r for r in results if r["exact_match"]]
    return {
        "acquired_at": acquired_at.astimezone(UTC).isoformat(),
        "reference_accesses": len(results),
        "exact_matches": len(matches),
        "missing_or_changed": len(results) - len(matches),
        "oldest_matched_age_hours": max((r["age_hours"] for r in matches), default=None),
        "all_reference_accesses_found": len(matches) == len(results),
        "events": results,
        "scope": "sample_age_lower_bound; maximum_retention_and_completeness_unverified",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--acquired-at", required=True)
    args = parser.parse_args(argv)
    try:
        report = compare(
            read_switches(args.reference),
            read_switches(args.candidate),
            datetime.fromisoformat(args.acquired_at.replace("Z", "+00:00")),
        )
        # Il report contiene solo tempi, conteggi ed esiti: nessun messaggio API.
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        status = 0 if report["all_reference_accesses_found"] else 1
        detail = (
            f"status={'ok' if status == 0 else 'incomplete'} "
            f"reference={report['reference_accesses']} matched={report['exact_matches']} "
            f"missing_or_changed={report['missing_or_changed']} "
            f"oldest_matched_age_hours={report['oldest_matched_age_hours']}"
        )
    except EvidenceError as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, TypeError):
        detail, status = "status=error code=local_input_or_output", 1
    now = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{now} nebula-check {now} nebula-history {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
