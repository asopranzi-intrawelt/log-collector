#!/usr/bin/env python3
"""Ricognisce lo storico cloud, senza attribuire agli intervalli una prova AdS.

Una lettura event-logs di controllo e una connectivity per switch, massimo quattro.
Gli stati restano nel campione privato e richiedono una lettura contestuale.
La ricognizione non verifica il recupero dei log prodotti durante un'interruzione.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from functools import partial
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
spec = spec_from_file_location("connectivity_windows", ROOT / "tools/check-nebula-windows.py")
windows = module_from_spec(spec)
spec.loader.exec_module(windows)


class ConnectivityClient(windows.poller.NebulaClient):
    def connectivity(self, target, period):
        site, device = (quote(target[key], safe="") for key in ("site_id", "device_id"))
        try:
            response = self.session.post(
                f"{windows.poller.API_BASE}/{site}/{device}/connectivity",
                json={"period": period},
                timeout=(10, 30),
                verify=self.verify,
                allow_redirects=False,
            )
            if response.status_code != 200:
                raise windows.poller.PollError(f"http_{response.status_code}")
            return response.json()
        except (windows.poller.requests.RequestException, ValueError) as exc:
            raise windows.poller.PollError("transport_or_json") from exc


def validate_connectivity(response):
    if not isinstance(response, list):
        raise windows.history.EvidenceError("connectivity_schema")
    for row in response:
        if not isinstance(row, dict) or any(
            field not in row for field in ("begin_time", "end_time", "status")
        ):
            raise windows.history.EvidenceError("connectivity_schema")
        begin, end = row["begin_time"], row["end_time"]
        if type(begin) is not int or type(end) is not int or not 0 <= begin <= end:
            raise windows.history.EvidenceError("connectivity_time")
        status = row["status"]
        if (
            not isinstance(status, str)
            or not status
            or any(ord(char) < 32 or ord(char) == 127 for char in status)
        ):
            raise windows.history.EvidenceError("connectivity_status")
    return response


def plan(snapshot, cached):
    targets = windows.resolve_targets(snapshot, cached)
    if any(not cached[device] for device, _ in targets):
        raise windows.history.EvidenceError("cached_events_missing")
    return targets


def measure(client, snapshot, cached, output, period="30d", now=None):
    if period != "30d":
        raise windows.history.EvidenceError("connectivity_period")
    now = now or (lambda: datetime.now(UTC))
    targets = plan(snapshot, cached)
    windows.write_private(output / "private-targets.json", [target for _, target in targets])
    observations, sources = [], []

    def acquire(alias, label, query, call, validate):
        requested = now()
        response = call()
        received = now()
        windows.write_private(output / f"{alias}-{label}.json", response)
        meta = {
            "ordinal": len(observations) + 1,
            "source_alias": alias,
            "label": label,
            "query": query,
            "requested_at": requested.isoformat(),
            "received_at": received.isoformat(),
        }
        try:
            if received < requested:
                raise windows.history.EvidenceError("connectivity_clock_backwards")
            rows = validate(response)
            meta["rows"] = len(rows)
        except (windows.history.EvidenceError, windows.poller.PollError) as exc:
            meta.update(rows=None, validation_error=str(exc))
            windows.write_private(output / f"{alias}-{label}-meta.json", meta)
            raise
        windows.write_private(output / f"{alias}-{label}-meta.json", meta)
        observations.append(meta)
        return rows

    for index, (device, target) in enumerate(targets, 1):
        alias = f"switch-{index}"
        reference = max(cached[device], key=lambda row: row["timestamp"])
        left, right = reference["timestamp"] - 1000, reference["timestamp"] + 1000
        control = acquire(
            alias,
            "control",
            {"startTimestamp": left, "endTimestamp": right},
            partial(client.fetch, target, left, right),
            partial(windows.poller.validate_events, config=target, start=left, end=right),
        )
        rows = acquire(
            alias,
            "connectivity",
            {"period": period},
            partial(client.connectivity, target, period),
            validate_connectivity,
        )
        present = windows.history.digest(reference) in windows.signatures(control)
        sources.append(
            {
                "source_alias": alias,
                "control_present": present,
                "intervals": len(rows),
                "online_intervals": sum(row["status"] == "online" for row in rows),
                "other_status_intervals": sum(row["status"] != "online" for row in rows),
                "earliest_begin_time": min((row["begin_time"] for row in rows), default=None),
                "latest_end_time": max((row["end_time"] for row in rows), default=None),
                "inspection_ok": present and bool(rows),
                "offline_recovery_verified": False,
            }
        )
    return {
        "acquired_at": now().isoformat(),
        "requested_period": period,
        "requests": len(observations),
        "request_budget": len(targets) * 2,
        "sources": sources,
        "observations": observations,
        "inspection_ok": all(source["inspection_ok"] for source in sources),
        "scope": "returned_connectivity_intervals_only; offline_recovery_unverified",
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
        plan(snapshot, cached)
        args.output.mkdir(parents=False, exist_ok=False)
        key = sys.stdin.readline(4097).rstrip("\r\n")
        if not key or len(key) > 4096 or any(char.isspace() for char in key):
            raise windows.history.EvidenceError("key_input")
        client = ConnectivityClient(key)
        key = None
        report = measure(client, snapshot, cached, args.output)
        windows.write_private(args.output / "inspection.json", report)
        status = 0 if report["inspection_ok"] else 1
        detail = (
            f"status={'inspected' if not status else 'inconclusive'} "
            f"sources={len(report['sources'])} requests={report['requests']} "
            "other_status_intervals="
            f"{sum(source['other_status_intervals'] for source in report['sources'])} "
            "offline_recovery=unverified"
        )
    except (windows.history.EvidenceError, windows.poller.PollError) as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError):
        detail, status = "status=error code=local_input_or_schema", 1
    finally:
        if client is not None:
            client.close()
    stamp = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{stamp} nebula-check {stamp} nebula-connectivity {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
