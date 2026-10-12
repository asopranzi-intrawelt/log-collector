#!/usr/bin/env python3
"""Misura gli estremi di una richiesta Nebula usando un accesso già osservato.

Tre richieste di sola lettura: controllo attorno al record, record sull'estremo
finale e record sull'estremo iniziale. Token solo da stdin, grezzi privati.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = spec_from_file_location("nebula_windows_boundaries", ROOT / "tools/check-nebula-windows.py")
windows = module_from_spec(spec)
spec.loader.exec_module(windows)


def select_reference(baseline):
    candidates = [
        (event["timestamp"], windows.history.digest(event), device, event)
        for device, events in baseline.items()
        for event in events
        if event["category"] == "AAA" and event["tag"] == "authentication"
    ]
    if not candidates:
        raise windows.history.EvidenceError("reference_authentication_missing")
    _, _, device, event = min(candidates, key=lambda item: item[:2])
    return device, event


def measure(client, target, reference, output):
    timestamp = reference["timestamp"]
    signature = windows.history.digest(reference)
    presence = {}
    counts = {}
    intervals = {
        "control": (timestamp - 1000, timestamp + 1000),
        "at_end": (timestamp - 1, timestamp),
        "at_start": (timestamp, timestamp + 1),
    }
    for label, (start, end) in intervals.items():
        response = client.fetch(target, start, end)
        windows.write_private(output / f"{label}.json", response)
        events = windows.poller.validate_events(response, target, start, end)
        presence[label] = signature in windows.signatures(events)
        counts[label] = len(events)
    control = presence["control"]
    return {
        "acquired_at": datetime.now(UTC).isoformat(),
        "reference_timestamp_ms": timestamp,
        "requests": 3,
        "rows": counts,
        "reference_present_in_control": control,
        "included_at_start": presence["at_start"] if control else None,
        "included_at_end": presence["at_end"] if control else None,
        "ok": control and presence["at_start"] and presence["at_end"],
        "scope": "boundary_membership_of_one_known_event; physical_completeness_unverified",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-stdin", action="store_true", required=True)
    args = parser.parse_args(argv)
    client = None
    try:
        baseline = windows.history.read_switches(args.baseline)
        device, reference = select_reference(baseline)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        _, target = windows.resolve_targets(snapshot, {device: []})[0]
        args.output.mkdir(parents=False, exist_ok=False)
        windows.write_private(args.output / "private-target.json", target)
        key = sys.stdin.readline(4097).rstrip("\r\n")
        if not key or len(key) > 4096 or any(c.isspace() for c in key):
            raise windows.history.EvidenceError("key_input")
        client = windows.poller.NebulaClient(key)
        key = None
        report = measure(client, target, reference, args.output)
        windows.write_private(args.output / "comparison.json", report)
        status = 0 if report["ok"] else 1
        outcome = "ok" if status == 0 else "boundary_difference"
        if not report["reference_present_in_control"]:
            outcome = "inconclusive"
        detail = (
            f"status={outcome} "
            f"requests={report['requests']} "
            f"included_at_start={report['included_at_start']} "
            f"included_at_end={report['included_at_end']}"
        )
    except (windows.history.EvidenceError, windows.poller.PollError) as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError):
        detail, status = "status=error code=local_input_or_schema", 1
    finally:
        if client is not None:
            client.close()
    now = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{now} nebula-check {now} nebula-boundaries {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
