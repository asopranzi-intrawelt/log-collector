"""Controlla offline i record v0 prodotti dalla sola fixture sintetica del pilota.

Questo modulo non interpreta syslog, QA o eventi AdS reali. Il rifiuto di tutto
ciò che non è la fixture attesa evita di promuovere dati non classificati.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


EVENT_ID = re.compile(r"pilot-[0-9a-f]{32}\Z")
ORIGINAL = re.compile(
    rb"(?P<time>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00) "
    rb"servizio=fixture esito=ok id=(?P<id>pilot-[0-9a-f]{32})\n\Z"
)
LABELS = {"archive": "technical", "source_family": "pilot", "service": "fixture"}
MAX_JSONL_BYTES = 1_048_576
MAX_ORIGINAL_BYTES = 4_096


class Rejected(ValueError):
    """Input non appartenente al contratto sintetico ammesso."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("duplicate_key")
        result[key] = value
    return result


def validate(record: object, root: Path, allow_replay_original: bool = False) -> dict[str, str]:
    """Verifica record, byte conservati e provenienza; restituisce label fisse."""
    if not isinstance(record, dict):
        raise Rejected("record_type")
    event_id = record.get("event_id")
    if not isinstance(event_id, str) or not EVENT_ID.fullmatch(event_id):
        raise Rejected("event_id")

    allowed_refs = {f"fixtures/original/{event_id}.log"}
    if allow_replay_original:
        allowed_refs.add(f"fixtures/replay-original/{event_id}.log")
    original_ref = record.get("original_ref")
    if not isinstance(original_ref, str) or original_ref not in allowed_refs:
        raise Rejected("original_ref")
    resolved_root = root.resolve(strict=True)
    expected_original = resolved_root / original_ref
    if any(
        path.is_symlink() or path.is_junction()
        for path in (expected_original.parent.parent, expected_original.parent, expected_original)
    ):
        raise Rejected("original_location")
    original = expected_original.resolve(strict=True)
    if not original.is_relative_to(resolved_root) or not original.is_file():
        raise Rejected("original_location")
    if original.stat().st_size > MAX_ORIGINAL_BYTES:
        raise Rejected("original_size")
    raw = original.read_bytes()
    parsed = ORIGINAL.fullmatch(raw)
    if parsed is None or parsed.group("id").decode("ascii") != event_id:
        raise Rejected("original_format")
    observed_at = parsed.group("time").decode("ascii")
    try:
        instant = datetime.fromisoformat(observed_at)
    except ValueError as exc:
        raise Rejected("timestamp") from exc
    if instant.utcoffset() != timezone.utc.utcoffset(instant):
        raise Rejected("timestamp_zone")

    expected = {
        "schema_version": "0",
        "event_id": event_id,
        "archive": "technical",
        "observed_at": observed_at,
        "event_at": observed_at,
        "event_time_original": observed_at,
        "source_id": "pilot-synthetic",
        "host": "pilot-synthetic",
        "service": "fixture",
        "transport_peer": None,
        "category": "service",
        "action": "health_test",
        "outcome": "success",
        "severity_original": "info",
        "severity_normalized": "info",
        "actor": None,
        "target": None,
        "message": "Evento tecnico sintetico del pilota",
        "attributes": {},
        "parser_name": "pilot_fixture_generator",
        "parser_version": "0",
        "parse_status": "ok",
        "errors": [],
        "original_ref": original_ref,
        "original_sha256": sha256(raw).hexdigest(),
        "record_locator": "line:1",
    }
    if record.keys() != expected.keys() or any(
        type(record[key]) is not type(value) or record[key] != value
        for key, value in expected.items()
    ):
        raise Rejected("record_contract")
    return LABELS.copy()


def check_jsonl(payload: bytes, root: Path, allow_replay_original: bool = False) -> list[dict]:
    """Rifiuta l'intero lotto prima di produrre un singolo risultato."""
    if not payload or len(payload) > MAX_JSONL_BYTES:
        raise Rejected("jsonl_size")
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise Rejected("jsonl_encoding") from exc
    if not lines or len(lines) > 1000:
        raise Rejected("jsonl_count")
    results = []
    for line in lines:
        if not line:
            raise Rejected("empty_line")
        try:
            record = json.loads(line, object_pairs_hook=_unique_object)
        except (ValueError, json.JSONDecodeError) as exc:
            raise Rejected("jsonl_format") from exc
        labels = validate(record, root, allow_replay_original=allow_replay_original)
        results.append({"labels": labels, "record": record})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Radice del pilota")
    parser.add_argument("--jsonl", type=Path, required=True, help="Record JSONL offline")
    args = parser.parse_args()
    try:
        if args.jsonl.stat().st_size > MAX_JSONL_BYTES:
            raise Rejected("jsonl_size")
        results = check_jsonl(args.jsonl.read_bytes(), args.root)
    except (Rejected, OSError) as exc:
        code = str(exc) if isinstance(exc, Rejected) else "io_error"
        print(f"rejected:{code}", file=sys.stderr)
        return 1
    for result in results:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
