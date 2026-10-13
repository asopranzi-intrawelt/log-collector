#!/usr/bin/env python3
"""Confronta risposte ampie e giornaliere Nebula su eventi già registrati.

Una lettura di controllo, due ampie e una per giorno/switch; massimo 20 POST.
La concordanza sul campione non prova retention o limite massimo del servizio.
Chiave da stdin, identificativi e grezzi soltanto nel livello privato.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = spec_from_file_location("nebula_volume_windows", ROOT / "tools/check-nebula-windows.py")
windows = module_from_spec(spec)
spec.loader.exec_module(windows)
DAY_MS = 86_400_000
MAX_DAYS = 7
MAX_REQUESTS = 20
RESPONSE_GUARD = 1000


def make_plan(snapshot, cached, now=None):
    """Ricava il periodo e il budget dai dati, prima di creare il client."""
    targets = windows.resolve_targets(snapshot, cached)
    if any(not cached[device] for device, _ in targets):
        raise windows.history.EvidenceError("cached_events_missing")
    points = [event["timestamp"] for events in cached.values() for event in events]
    start = min(points) // DAY_MS * DAY_MS
    end = (max(points) // DAY_MS + 1) * DAY_MS
    if end - start > MAX_DAYS * DAY_MS:
        raise windows.history.EvidenceError("volume_window_too_large")
    now = now or datetime.now(UTC)
    if end > int(now.timestamp() * 1000) - 3_600_000:
        raise windows.history.EvidenceError("volume_window_recent_or_future")
    intervals = [(left, min(left + DAY_MS, end)) for left in range(start, end, DAY_MS)]
    requests = len(targets) * (len(intervals) + 3)
    if requests > MAX_REQUESTS:
        raise windows.history.EvidenceError("volume_request_budget")
    return targets, start, end, intervals, requests


def compare(cached, reference, control, before, pages, after):
    """Confronta tutti i sette campi, inclusi gli eventi tecnici e le differenze."""
    split = [event for page in pages for event in page]
    old, first, parts, last = map(windows.signatures, (cached, before, split, after))
    control_present = windows.history.digest(reference) in windows.signatures(control)
    stable = first == last
    equal = first == parts == last
    missing = old - parts
    threshold = any(len(rows) >= RESPONSE_GUARD for rows in [control, before, *pages, after])
    if not control_present:
        status = "control_missing"
    elif not stable:
        status = "wide_responses_changed"
    elif threshold:
        status = "response_threshold_reached"
    elif not equal:
        status = "coverage_mismatch"
    elif missing:
        status = "historical_records_unavailable"
    else:
        status = "consistent"
    return {
        "control_present": control_present,
        "cached_rows": len(cached),
        "cached_unique": len(old),
        "wide_before_rows": len(before),
        "wide_before_unique": len(first),
        "segment_rows": [len(page) for page in pages],
        "split_rows_before_dedup": len(split),
        "split_unique": len(parts),
        "split_duplicates": len(split) - len(parts),
        "wide_after_rows": len(after),
        "wide_after_unique": len(last),
        "cached_missing_from_wide": len(old - first),
        "cached_missing_from_split": len(missing),
        "split_missing_from_wide": len(parts - first),
        "wide_missing_from_split": len(first - parts),
        "wide_responses_stable": stable,
        "wide_and_split_sets_equal": equal,
        "response_threshold_reached": threshold,
        "largest_response_rows": max(map(len, [control, before, *pages, after])),
        "status": status,
        "ok": status == "consistent",
    }


def measure(client, snapshot, cached, output, now=None):
    now = now or (lambda: datetime.now(UTC))
    targets, start, end, intervals, budget = make_plan(snapshot, cached, now())
    windows.write_private(output / "private-targets.json", [target for _, target in targets])
    sources, observations = [], []

    def fetch(target, alias, label, left, right):
        if len(observations) >= budget:
            raise windows.history.EvidenceError("volume_request_budget")
        requested = now()
        response = client.fetch(target, left, right)
        received = now()
        if received < requested:
            raise windows.history.EvidenceError("volume_clock_backwards")
        windows.write_private(output / f"{alias}-{label}.json", response)
        events = windows.poller.validate_events(response, target, left, right)
        meta = {
            "ordinal": len(observations) + 1,
            "source_alias": alias,
            "label": label,
            "query_start_ms": left,
            "query_end_ms": right,
            "requested_at": requested.isoformat(),
            "received_at": received.isoformat(),
            "rows": len(events),
        }
        windows.write_private(output / f"{alias}-{label}-meta.json", meta)
        observations.append(meta)
        return events

    for ordinal, (device, target) in enumerate(targets, 1):
        alias = f"switch-{ordinal}"
        reference = max(cached[device], key=lambda event: event["timestamp"])
        point = reference["timestamp"]
        control = fetch(target, alias, "control", point - 1000, point + 1000)
        before = fetch(target, alias, "wide-before", start, end)
        pages = [
            fetch(target, alias, f"day-{index}", left, right)
            for index, (left, right) in enumerate(intervals, 1)
        ]
        after = fetch(target, alias, "wide-after", start, end)
        result = compare(cached[device], reference, control, before, pages, after)
        result["source_alias"] = alias
        sources.append(result)
    return {
        "acquired_at": now().isoformat(),
        "start_ms": start,
        "end_ms": end,
        "chunk_ms": DAY_MS,
        "days": len(intervals),
        "requests": len(observations),
        "request_budget": budget,
        "sources": sources,
        "observations": observations,
        "ok": all(source["ok"] for source in sources),
        "scope": (
            "fixed_period_response_coverage; maximum_limit_and_physical_completeness_unverified"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-stdin", action="store_true", required=True)
    args = parser.parse_args(argv)
    client = None
    try:
        cached = windows.history.read_switches(args.cache)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        make_plan(snapshot, cached)
        args.output.mkdir(parents=False, exist_ok=False)
        key = sys.stdin.readline(4097).rstrip("\r\n")
        if not key or len(key) > 4096 or any(char.isspace() for char in key):
            raise windows.history.EvidenceError("key_input")
        client = windows.poller.NebulaClient(key)
        key = None
        report = measure(client, snapshot, cached, args.output)
        windows.write_private(args.output / "comparison.json", report)
        status = 0 if report["ok"] else 1
        detail = (
            f"status={'consistent' if report['ok'] else 'inconclusive'} "
            f"sources={len(report['sources'])} requests={report['requests']} "
            f"source_statuses={','.join(source['status'] for source in report['sources'])}"
        )
    except (windows.history.EvidenceError, windows.poller.PollError) as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError):
        detail, status = "status=error code=local_input_or_schema", 1
    finally:
        if client is not None:
            client.close()
    stamp = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{stamp} nebula-check {stamp} nebula-volume {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
