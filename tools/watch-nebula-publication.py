#!/usr/bin/env python3
"""Osserva un nuovo login, logout o fallimento di autenticazione in Nebula.

Osservazione ordinaria di cinque minuti, pausa 15 secondi, budget 21 POST.
Ultima prova opzionale: dieci minuti, massimo 41 POST e due letture diagnostiche.
Tempi e conteggi nel riepilogo; record, mapping e chiave restano privati.
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = spec_from_file_location(
    "nebula_publication_boundary", ROOT / "tools/check-nebula-boundaries.py"
)
boundaries = module_from_spec(spec)
spec.loader.exec_module(boundaries)
windows = boundaries.windows
MAX_REQUESTS = 21
DURATION_SECONDS = 300
INTERVAL_SECONDS = 15
RESPONSE_GUARD = 1000
FINAL_DURATION_SECONDS = 600
FINAL_MAX_REQUESTS = 41
EVENT_KINDS = ("login", "logout", "failure")


def select_target(snapshot, baseline, switch_model=None):
    """Sceglie il riferimento storico o un modello univoco nello snapshot."""
    if switch_model is None:
        device, reference = boundaries.select_reference(baseline)
    else:
        matches = [
            device
            for organization in snapshot["organizations"]
            for site in organization["sites"]
            for device in site["devices"]
            if device.get("type") == "SW" and device.get("model") == switch_model
        ]
        if len(matches) != 1:
            raise windows.history.EvidenceError("snapshot_model_missing_or_ambiguous")
        device = matches[0].get("devId")
        if not isinstance(device, str) or not device or not baseline.get(device):
            raise windows.history.EvidenceError("target_reference_missing")
        # Il controllo del nuovo apparato può essere tecnico: non prova un accesso.
        reference = max(baseline[device], key=lambda event: event["timestamp"])
    _, target = windows.resolve_targets(snapshot, {device: []})[0]
    return target, reference


def measure(
    client,
    target,
    output,
    now=None,
    monotonic=None,
    sleep=None,
    duration_seconds=DURATION_SECONDS,
    max_requests=MAX_REQUESTS,
    expected_event="login",
):
    if expected_event not in EVENT_KINDS:
        raise windows.history.EvidenceError("expected_event_invalid")
    count_key = "candidate_logins" if expected_event == "login" else "candidate_events"
    now = now or (lambda: datetime.now(UTC))
    monotonic = monotonic or time.monotonic
    sleep = sleep or time.sleep
    started = now()
    started_ms = int(started.timestamp() * 1000)
    eligible_start = started_ms // 1000 * 1000
    query_start = eligible_start - 30_000
    timer_start = monotonic()
    windows.write_private(output / "ready.json", {"observation_started_at": started.isoformat()})
    observations, scans, candidates = [], [], []
    outcome = f"no_new_{expected_event}"
    previous_received = started_ms
    for ordinal in range(1, max_requests + 1):
        if monotonic() - timer_start > duration_seconds:
            break
        requested = now()
        end = int(requested.timestamp() * 1000)
        if end < previous_received:
            raise windows.poller.PollError("observation_clock_backwards")
        response = client.fetch(target, query_start, end)
        received = now()
        received_ms = int(received.timestamp() * 1000)
        windows.write_private(output / f"sample-{ordinal:03}.json", response)
        if received_ms < end:
            raise windows.poller.PollError("observation_clock_backwards")
        events = windows.poller.validate_events(response, target, query_start, end)
        if len(events) >= RESPONSE_GUARD:
            raise windows.poller.PollError("observation_response_saturated")
        observation = {
            "ordinal": ordinal,
            "query_start_ms": query_start,
            "query_end_ms": end,
            "requested_at": requested.isoformat(),
            "received_at": received.isoformat(),
            "rows": len(events),
            count_key: None,
        }
        found = {}
        try:
            for event in events:
                if (
                    windows.poller.outcome(event) == expected_event
                    and event["timestamp"] >= eligible_start
                ):
                    found[windows.history.digest(event)] = event
        except windows.poller.PollError as exc:
            # Conservare il tempo anche quando un nuovo formato impedisce il conteggio.
            observation["classification_error"] = str(exc)
            windows.write_private(output / f"sample-{ordinal:03}-meta.json", observation)
            raise
        observation[count_key] = len(found)
        windows.write_private(output / f"sample-{ordinal:03}-meta.json", observation)
        observations.append(observation)
        scans.append((end, set(found)))
        previous_received = received_ms
        if found:
            candidates = list(found.values())
            windows.write_private(output / "private-candidates.json", candidates)
            outcome = "observed" if len(candidates) == 1 else "ambiguous"
            break
        remaining = duration_seconds - (monotonic() - timer_start)
        if remaining <= 0 or ordinal == max_requests:
            break
        sleep(min(INTERVAL_SECONDS, remaining))
    reference_ms = candidates[0]["timestamp"] if len(candidates) == 1 else None
    upper, negative_start = None, None
    if reference_ms is not None:
        signature = windows.history.digest(candidates[0])
        upper = previous_received - reference_ms
        negative = [
            end
            for end, signatures in scans[:-1]
            if end >= reference_ms and signature not in signatures
        ]
        if negative:
            negative_start = negative[-1] - reference_ms
    report = {
        "started_at": started.isoformat(),
        "eligible_start_ms": eligible_start,
        "acquired_at": now().isoformat(),
        "requests": len(observations),
        "duration_seconds": duration_seconds,
        "max_requests": max_requests,
        "status": outcome,
        "ok": outcome == "observed",
        count_key: len(candidates),
        "candidate_timestamp_ms": reference_ms,
        "apparent_delay_upper_ms": upper,
        "last_negative_request_start_delay_ms": negative_start,
        "observations": observations,
        "scope": f"first_api_visibility_of_one_candidate_{expected_event}; clock_offset_unverified",
    }
    if expected_event != "login":
        report["expected_event"] = expected_event
    return report


def recheck(client, target, reference, observation, output, now=None):
    """Rilegge il tentativo con controllo storico e due ore precedenti all'avvio."""
    now = now or (lambda: datetime.now(UTC))
    eligible = observation.get("eligible_start_ms")
    samples = observation.get("observations")
    expected_event = observation.get("expected_event", "login")
    if (
        expected_event not in EVENT_KINDS
        or observation.get("status") != f"no_new_{expected_event}"
        or observation.get("ok") is not False
        or type(eligible) is not int
        or not isinstance(samples, list)
        or not samples
        or type(samples[-1].get("query_end_ms")) is not int
        or samples[-1]["query_end_ms"] < eligible
    ):
        raise windows.history.EvidenceError("observation_schema")
    end = int(now().timestamp() * 1000)
    if end < samples[-1]["query_end_ms"]:
        raise windows.history.EvidenceError("recheck_clock_before_observation")
    point = reference["timestamp"]
    control = client.fetch(target, point - 1000, point + 1000)
    windows.write_private(output / "control.json", control)
    control = windows.poller.validate_events(control, target, point - 1000, point + 1000)
    start = eligible - 7_200_000
    wide = client.fetch(target, start, end)
    received = now()
    windows.write_private(output / "wide.json", wide)
    wide = windows.poller.validate_events(wide, target, start, end)
    if len(control) >= RESPONSE_GUARD or len(wide) >= RESPONSE_GUARD:
        raise windows.poller.PollError("recheck_response_saturated")
    control_present = windows.history.digest(reference) in windows.signatures(control)
    found = {}
    for event in wide:
        if windows.poller.outcome(event) == expected_event:
            found[windows.history.digest(event)] = event
    candidates = sorted(found.values(), key=lambda event: event["timestamp"])
    windows.write_private(output / "private-candidates.json", candidates)
    status = "candidates_found" if candidates else f"no_recent_{expected_event}"
    if not control_present:
        status = "control_missing"
    report = {
        "acquired_at": received.isoformat(),
        "requests": 2,
        "query_start_ms": start,
        "query_end_ms": end,
        "control_present": control_present,
        "wide_rows": len(wide),
        ("login_candidates" if expected_event == "login" else "event_candidates"): len(candidates),
        "candidates": [
            {
                "timestamp_ms": event["timestamp"],
                "within_original_query_window": (
                    eligible - 30_000 <= event["timestamp"] <= samples[-1]["query_end_ms"]
                ),
                "eligible_for_original_watch": (
                    eligible <= event["timestamp"] <= samples[-1]["query_end_ms"]
                ),
            }
            for event in candidates
        ],
        "status": status,
        "ok": control_present and bool(candidates),
        "scope": "diagnostic_recheck; candidate_identity_and_publication_time_unverified",
    }
    if expected_event != "login":
        report["expected_event"] = expected_event
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-stdin", action="store_true", required=True)
    parser.add_argument("--switch-model", choices=("XGS2220-30HP", "XGS2220-54HP"))
    parser.add_argument("--event", choices=EVENT_KINDS, default="login")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--observation", type=Path)
    mode.add_argument("--final-attempt", action="store_true")
    args = parser.parse_args(argv)
    client = None
    try:
        baseline = windows.history.read_switches(args.baseline)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        target, reference = select_target(snapshot, baseline, args.switch_model)
        observation = None
        if args.observation is not None:
            recorded_target = json.loads(
                args.observation.with_name("private-target.json").read_text(encoding="utf-8-sig")
            )
            if recorded_target != target:
                raise windows.history.EvidenceError("observation_target_mismatch")
            observation = json.loads(args.observation.read_text(encoding="utf-8-sig"))
            if observation.get("expected_event", "login") != args.event:
                raise windows.history.EvidenceError("observation_event_mismatch")
        args.output.mkdir(parents=False, exist_ok=False)
        windows.write_private(args.output / "private-target.json", target)
        key = sys.stdin.readline(4097).rstrip("\r\n")
        if not key or len(key) > 4096 or any(c.isspace() for c in key):
            raise windows.history.EvidenceError("key_input")
        client = windows.poller.NebulaClient(key)
        key = None
        if args.observation is None:
            settings = {}
            if args.final_attempt:
                settings = {
                    "duration_seconds": FINAL_DURATION_SECONDS,
                    "max_requests": FINAL_MAX_REQUESTS,
                }
            if args.event != "login":
                settings["expected_event"] = args.event
            report = measure(client, target, args.output, **settings)
            count_key = "candidate_logins" if args.event == "login" else "candidate_events"
            detail = (
                f"status={report['status']} requests={report['requests']} "
                f"{count_key}={report[count_key]} "
                f"apparent_delay_upper_ms={report['apparent_delay_upper_ms']}"
            )
        else:
            report = recheck(client, target, reference, observation, args.output)
            count_key = "login_candidates" if args.event == "login" else "event_candidates"
            detail = (
                f"status={report['status']} requests={report['requests']} "
                f"control_present={report['control_present']} "
                f"{count_key}={report[count_key]}"
            )
        windows.write_private(args.output / "comparison.json", report)
        if args.final_attempt and report["status"] == f"no_new_{args.event}":
            followup = args.output / "followup"
            followup.mkdir()
            diagnostic = recheck(client, target, reference, report, followup)
            count_key = "login_candidates" if args.event == "login" else "event_candidates"
            windows.write_private(followup / "comparison.json", diagnostic)
            detail += (
                f" recheck_status={diagnostic['status']} recheck_requests={diagnostic['requests']}"
                f" recheck_{count_key}={diagnostic[count_key]}"
            )
        if args.event != "login":
            detail += f" expected_event={args.event}"
        status = 0 if report["ok"] else 1
    except (windows.history.EvidenceError, windows.poller.PollError) as exc:
        detail, status = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError):
        detail, status = "status=error code=local_input_or_schema", 1
    finally:
        if client is not None:
            client.close()
    stamp = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{stamp} nebula-check {stamp} nebula-publication {detail}")
    return status


if __name__ == "__main__":
    sys.exit(main())
