#!/usr/bin/env python3
"""Misura la coerenza delle risposte Nebula per uno stesso periodo.

Il token arriva solo da stdin. Identificativi e risposte restano nell'output
privato; il riepilogo contiene soltanto intervalli, conteggi ed esiti.
"""

import argparse
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHUNK_MS = 300_000


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


history = load_module("nebula_history_windows", ROOT / "tools/compare-nebula-history.py")
poller = load_module("nebula_poller_windows", ROOT / "bin/ads-nebula.py")


def known_window(baseline):
    timestamps = [
        e["timestamp"]
        for events in baseline.values()
        for e in events
        if e["category"] == "AAA" and e["tag"] == "authentication"
    ]
    if not timestamps:
        raise history.EvidenceError("reference_authentication_missing")
    start = min(timestamps) // CHUNK_MS * CHUNK_MS
    end = (max(timestamps) // CHUNK_MS + 1) * CHUNK_MS
    if end - start > 3_600_000:
        raise history.EvidenceError("reference_window_too_large")
    return start, end


def resolve_targets(snapshot, devices):
    targets = {}
    for organization in snapshot["organizations"]:
        for site in organization["sites"]:
            for device in site["devices"]:
                key = device.get("devId")
                if key not in devices or device.get("type") != "SW":
                    continue
                if key in targets or not isinstance(site.get("siteId"), str) or not site["siteId"]:
                    raise history.EvidenceError("snapshot_device_ambiguous")
                targets[key] = {"site_id": site["siteId"], "device_id": key}
    if set(targets) != set(devices):
        raise history.EvidenceError("snapshot_device_missing")
    if not 1 <= len(targets) <= 2:
        raise history.EvidenceError("target_count")
    return [(key, targets[key]) for key in devices]


def signatures(events):
    return {history.digest(e) for e in events}


def compare_period(cached, wide, pages, expected, start, end):
    cached_in_period = [e for e in cached if start <= e["timestamp"] <= end]
    split = [event for page in pages for event in page]
    old_ids, wide_ids, split_ids = map(signatures, (cached_in_period, wide, split))
    expected_ids = signatures(
        [e for e in expected if e["category"] == "AAA" and e["tag"] == "authentication"]
    )
    # L'uguaglianza deve includere tutti gli eventi, anche quelli tecnici.
    equal = old_ids == wide_ids == split_ids
    missing_known = len(expected_ids - wide_ids) + len(expected_ids - split_ids)
    return {
        "cached_rows": len(cached_in_period),
        "cached_unique": len(old_ids),
        "wide_rows": len(wide),
        "wide_unique": len(wide_ids),
        "split_rows_before_dedup": len(split),
        "split_unique": len(split_ids),
        "split_duplicates": len(split) - len(split_ids),
        "cached_missing_from_wide": len(old_ids - wide_ids),
        "cached_missing_from_split": len(old_ids - split_ids),
        "wide_missing_from_split": len(wide_ids - split_ids),
        "split_missing_from_wide": len(split_ids - wide_ids),
        "known_accesses": len(expected_ids),
        "missing_known_accesses": missing_known,
        "response_sets_equal": equal,
        "ok": equal and missing_known == 0,
    }


def write_private(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def measure(client, targets, baseline, broad, start, end, output):
    if any(device not in broad for device, _ in targets):
        raise history.EvidenceError("broad_device_missing")
    results = []
    request_count = 0
    for ordinal, (device, config) in enumerate(targets, start=1):
        alias = f"switch-{ordinal}"

        def fetch(left, right, suffix, target=config, label=alias):
            nonlocal request_count
            request_count += 1
            if request_count > 26:
                raise history.EvidenceError("request_budget")
            response = client.fetch(target, left, right)
            write_private(output / f"{label}-{suffix}.json", response)
            return poller.validate_events(response, target, left, right)

        wide = fetch(start, end, "wide")
        pages = []
        left = start
        while left < end:
            right = min(left + CHUNK_MS, end)
            pages.append(fetch(left, right, f"segment-{len(pages) + 1}"))
            left = right
        result = compare_period(broad[device], wide, pages, baseline[device], start, end)
        result["source_alias"] = alias
        results.append(result)
    return {
        "acquired_at": datetime.now(UTC).isoformat(),
        "start_ms": start,
        "end_ms": end,
        "chunk_ms": CHUNK_MS,
        "requests": request_count,
        "sources": results,
        "ok": all(result["ok"] for result in results),
        "scope": "fixed_window_response_consistency; physical_completeness_unverified",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--broad", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-stdin", action="store_true", required=True)
    args = parser.parse_args(argv)
    client = None
    try:
        baseline = history.read_switches(args.baseline)
        broad = history.read_switches(args.broad)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        start, end = known_window(baseline)
        targets = resolve_targets(snapshot, baseline)
        if any(device not in broad for device, _ in targets):
            raise history.EvidenceError("broad_device_missing")
        args.output.mkdir(parents=False, exist_ok=False)
        write_private(args.output / "private-targets.json", [target for _, target in targets])
        key = sys.stdin.readline(4097).rstrip("\r\n")
        if not key or len(key) > 4096 or any(c.isspace() for c in key):
            raise history.EvidenceError("key_input")
        client = poller.NebulaClient(key)
        key = None
        report = measure(client, targets, baseline, broad, start, end, args.output)
        write_private(args.output / "comparison.json", report)
        status = 0 if report["ok"] else 1
        detail = (
            f"status={'ok' if status == 0 else 'inconsistent'} "
            f"sources={len(report['sources'])} requests={report['requests']}"
        )
    except (history.EvidenceError, poller.PollError) as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError):
        detail, status = "status=error code=local_input_or_schema", 1
    finally:
        if client is not None:
            client.close()
    now = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{now} nebula-check {now} nebula-windows {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
