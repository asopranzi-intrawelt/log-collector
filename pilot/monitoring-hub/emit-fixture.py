"""Write one synthetic original and one synthetic v0 consultation record."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
CURRENT_LOG = FIXTURES / "current-log.txt"


def active_log() -> Path:
    name = CURRENT_LOG.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"technical-[a-z0-9-]+\.jsonl", name):
        raise RuntimeError("Nome del segmento sintetico non valido")
    return FIXTURES / name


def build_record() -> tuple[str, bytes, dict]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    event_id = "pilot-" + uuid4().hex
    raw = f"{now} servizio=fixture esito=ok id={event_id}\n".encode("utf-8")
    record = {
        "schema_version": "0",
        "event_id": event_id,
        "archive": "technical",
        "observed_at": now,
        "event_at": now,
        "event_time_original": now,
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
        "original_ref": f"fixtures/original/{event_id}.log",
        "original_sha256": sha256(raw).hexdigest(),
        "record_locator": "line:1",
    }
    return event_id, raw, record


def write_original(event_id: str, raw: bytes) -> None:
    original = FIXTURES / "original" / f"{event_id}.log"
    original.parent.mkdir(parents=True, exist_ok=True)
    with original.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def create_record() -> tuple[str, dict]:
    event_id, raw, record = build_record()
    write_original(event_id, raw)
    return event_id, record


def serialized_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"


def emit() -> tuple[str, dict]:
    event_id, record = create_record()
    marker = uuid4().hex
    staged = FIXTURES / f".pending-{marker}.tmp"
    segment = FIXTURES / f"technical-{marker}.jsonl"
    with staged.open("xb") as output:
        output.write(serialized_line(record).encode("utf-8"))
        output.flush()
        os.fsync(output.fileno())
    if segment.exists():
        raise RuntimeError("Il segmento sintetico di destinazione esiste già")
    staged.replace(segment)
    pointer = FIXTURES / f".current-log-{marker}.tmp"
    with pointer.open("x", encoding="utf-8", newline="\n") as output:
        output.write(segment.name + "\n")
        output.flush()
        os.fsync(output.fileno())
    pointer.replace(CURRENT_LOG)
    return event_id, record


if __name__ == "__main__":
    event_id, _ = emit()
    print(event_id)
