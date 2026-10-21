"""Validate QA technical events offline before any general index can see them.

This boundary accepts the current producer's backup_selected event only.
Authorisation evidence needs a separate restricted archive and is rejected here.
No socket, archive writer or automatic transport is opened by this program.
"""

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

MAX_BATCH_BYTES = 1_048_576
MAX_EVENTS = 1000
EVENT_ID = re.compile(r"[0-9a-f]{32}\Z")
SOURCE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
JOB_REF = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\Z"
)
BASE_KEYS = {
    "schema_version", "event_id", "event_time_original", "source_id",
    "environment", "service", "component", "event",
}
TECHNICAL_KEYS = BASE_KEYS | {"role", "trigger"}
TRIGGERS = {"T1_T2", "T3", "T4", "T5"}


class Rejected(ValueError):
    """A stable code; input bytes are never included in the error."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("duplicate_key")
        result[key] = value
    return result


def _string(event: dict, key: str) -> str:
    value = event.get(key)
    if type(value) is not str:
        raise Rejected(f"{key}_type")
    return value


def validate(event: object, source_id: str, environment: str) -> dict:
    """Return a minimal general-view record, without unreviewed correlators."""
    if type(event) is not dict:
        raise Rejected("record_type")
    # This test precedes any optional-field handling: authorisation evidence
    # must never be converted into a technical record or printed by the CLI.
    if event.get("component") == "authorisation" or event.get("event") == "authorisation_granted":
        raise Rejected("restricted_route")
    if set(event) not in (TECHNICAL_KEYS, TECHNICAL_KEYS | {"job_ref"}):
        raise Rejected("record_keys")
    if _string(event, "schema_version") != "qa-tech-v1":
        raise Rejected("schema_version")
    event_id = _string(event, "event_id")
    if not EVENT_ID.fullmatch(event_id):
        raise Rejected("event_id")
    if _string(event, "source_id") != source_id:
        raise Rejected("source_id")
    if _string(event, "environment") != environment:
        raise Rejected("environment")
    if _string(event, "service") != "qa-verifier":
        raise Rejected("service")
    if _string(event, "component") != "backend":
        raise Rejected("component")
    if _string(event, "event") != "backup_selected":
        raise Rejected("event")
    if _string(event, "role") != "backup":
        raise Rejected("role")
    if _string(event, "trigger") not in TRIGGERS:
        raise Rejected("trigger")
    if "job_ref" in event and not JOB_REF.fullmatch(_string(event, "job_ref")):
        raise Rejected("job_ref")
    declared_time = _string(event, "event_time_original")
    if not TIMESTAMP.fullmatch(declared_time):
        raise Rejected("event_time_original")
    try:
        instant = datetime.fromisoformat(declared_time)
        if instant.utcoffset() is None or abs(instant.utcoffset().total_seconds()) > 14 * 3600:
            raise ValueError("offset")
    except ValueError as exc:
        raise Rejected("event_time_original") from exc
    # Explicit construction prevents a future optional producer field from
    # reaching the general view through an accidental dict copy.
    return {
        "schema_version": "qa-tech-v1",
        "event_id": event_id,
        "event_at": instant.astimezone(UTC).isoformat(timespec="seconds"),
        "event_time_original": declared_time,
        "source_id": source_id,
        "environment": environment,
        "service": "qa-verifier",
        "component": "backend",
        "event": "backup_selected",
        "role": "backup",
        "trigger": event["trigger"],
    }


def check_jsonl(payload: bytes, source_id: str, environment: str) -> list[dict]:
    """Validate the whole batch before returning a single visible event."""
    if not SOURCE_ID.fullmatch(source_id):
        raise Rejected("expected_source_id")
    if environment not in ("staging", "production"):
        raise Rejected("expected_environment")
    if not payload or len(payload) > MAX_BATCH_BYTES:
        raise Rejected("batch_size")
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise Rejected("batch_encoding") from exc
    if not lines or len(lines) > MAX_EVENTS:
        raise Rejected("batch_count")
    records = []
    seen = set()
    for line in lines:
        if not line:
            raise Rejected("empty_line")
        try:
            event = json.loads(line, object_pairs_hook=_unique_object)
        except Rejected:
            raise
        except ValueError as exc:
            raise Rejected("json_format") from exc
        record = validate(event, source_id, environment)
        if record["event_id"] in seen:
            raise Rejected("duplicate_event_id")
        seen.add(record["event_id"])
        records.append({
            "labels": {
                "archive": "technical", "source_family": "qa",
                "environment": environment, "service": "qa-verifier",
            },
            "record": record,
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--source-id", required=True, help="Registered source identity")
    parser.add_argument("--environment", required=True, choices=("staging", "production"))
    args = parser.parse_args()
    try:
        if args.jsonl.stat().st_size > MAX_BATCH_BYTES:
            raise Rejected("batch_size")
        records = check_jsonl(args.jsonl.read_bytes(), args.source_id, args.environment)
    except (Rejected, OSError) as exc:
        code = str(exc) if isinstance(exc, Rejected) else "io_error"
        print(f"rejected:{code}", file=sys.stderr)
        return 1
    for record in records:
        print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
