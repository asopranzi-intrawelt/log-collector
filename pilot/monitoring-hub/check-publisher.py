"""Check that an abandoned partial staging file cannot poison the next event."""

import argparse
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
STATE = ROOT / "fixtures" / "publisher-state.json"


def load_script(name: str):
    loader = SourceFileLoader(name.replace("-", "_"), str(ROOT / name))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


logs = load_script("check-logs.py")
fixture = load_script("emit-fixture.py")


def wait_for_record(expected: dict) -> None:
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            found = logs.entries(logs.request_json(logs.query_url(logs.LOKI, expected["event_id"])))
            records = logs.check_labels(found, expected)
            if records == [expected]:
                return
            if records:
                raise RuntimeError("Record Loki inattesi")
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(2)
    raise RuntimeError("Il record completo non è arrivato in Loki")


def assert_absent(event_id: str, seconds: int) -> int:
    checks = 0
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        payload = logs.request_json(logs.query_url(logs.LOKI, event_id))
        if payload.get("status") != "success":
            raise RuntimeError("Query Loki non riuscita")
        lines = [line for stream in payload.get("data", {}).get("result", [])
                 for _, line in stream.get("values", [])]
        if lines:
            raise RuntimeError("Il prefisso abbandonato è stato pubblicato in Loki")
        checks += 1
        time.sleep(2)
    return checks


def self_test() -> None:
    saved_fixtures, saved_current = fixture.FIXTURES, fixture.CURRENT_LOG
    temp = ROOT / "fixtures" / "publisher-tests"
    temp.mkdir(exist_ok=True)
    marker = uuid4().hex
    try:
        fixture.FIXTURES = temp
        fixture.CURRENT_LOG = temp / f"current-log-{marker}.txt"
        fixture.CURRENT_LOG.write_text(f"technical-{marker}.jsonl\n", encoding="utf-8")
        abandoned = temp / f"technical-{marker}.jsonl"
        prefix = b'{"event_id":"pilot-abandoned"'
        abandoned.write_bytes(prefix)
        event_id, expected = fixture.emit()
        if abandoned.read_bytes() != prefix:
            raise RuntimeError("Il publisher ha accodato al prefisso interrotto")
        published = fixture.active_log()
        if published == abandoned or not published.name.startswith("technical-"):
            raise RuntimeError("Il publisher non ha creato un segmento distinto")
        if published.read_text(encoding="utf-8") != fixture.serialized_line(expected):
            raise RuntimeError("Il segmento pubblicato non contiene esattamente un record")
        original = temp / "original" / f"{event_id}.log"
        if sha256(original.read_bytes()).hexdigest() != expected["original_sha256"]:
            raise RuntimeError("Impronta dell'originale sintetico non coincide")
    finally:
        fixture.FIXTURES, fixture.CURRENT_LOG = saved_fixtures, saved_current
    print("Crash simulato offline: prefisso invariato, nuovo segmento completo e originale verificato")


def prepare() -> None:
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))
        if not previous.get("completed"):
            raise RuntimeError("Stato publisher presente: esaminare o completare la prova precedente")
        history = ROOT / "fixtures" / "state-history"
        history.mkdir(exist_ok=True)
        STATE.replace(history / f"publisher-{uuid4().hex}.json")
    _, control = fixture.emit()
    wait_for_record(control)
    event_id, record = fixture.create_record()
    line = fixture.serialized_line(record)
    prefix = line[:len(line) // 2]
    if event_id not in prefix or "\n" in prefix:
        raise RuntimeError("Prefisso di prova non osservabile")
    staged = fixture.FIXTURES / f".pending-{uuid4().hex}.tmp"
    with staged.open("xb") as output:
        output.write(prefix.encode("utf-8"))
        output.flush()
        os.fsync(output.fileno())
    checks = assert_absent(event_id, 14)
    state = {
        "event_id": event_id,
        "record": record,
        "staged": staged.name,
        "prefix_sha256": sha256(staged.read_bytes()).hexdigest(),
        "checks_before_restart": checks,
    }
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prima del riavvio: {checks} query senza prefisso staged; riavviare solo Alloy")


def finish() -> None:
    if not STATE.exists():
        raise RuntimeError("Eseguire prima prepare e riavviare Alloy")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    staged = fixture.FIXTURES / state["staged"]
    if sha256(staged.read_bytes()).hexdigest() != state["prefix_sha256"]:
        raise RuntimeError("Il prefisso staged è stato modificato")
    _, next_record = fixture.emit()
    wait_for_record(next_record)
    checks = assert_absent(state["event_id"], 4)
    if sha256(staged.read_bytes()).hexdigest() != state["prefix_sha256"]:
        raise RuntimeError("Il nuovo evento ha modificato il prefisso abbandonato")
    state["next_event_id"] = next_record["event_id"]
    state["next_segment"] = fixture.active_log().name
    state["checks_after_restart"] = checks
    state["completed"] = True
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Dopo il riavvio: nuovo evento acquisito, {checks} query senza prefisso abbandonato")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("self-test", "prepare", "finish"))
    phase = parser.parse_args().phase
    {"self-test": self_test, "prepare": prepare, "finish": finish}[phase]()


if __name__ == "__main__":
    main()
