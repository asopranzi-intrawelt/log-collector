"""Verify an unfinished JSONL line across an external Alloy restart."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from uuid import uuid4

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader


ROOT = Path(__file__).resolve().parent
STATE = ROOT / "fixtures" / "partial-state.json"


def load_script(name: str):
    loader = SourceFileLoader(name.replace("-", "_"), str(ROOT / name))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


logs = load_script("check-logs.py")
fixture = load_script("emit-fixture.py")


def unique_segment() -> Path:
    path = ROOT / "fixtures" / f"technical-{uuid4().hex}.jsonl"
    path.touch(exist_ok=False)
    return path


def raw_lines(event_id: str) -> list[str]:
    payload = logs.request_json(logs.query_url(logs.LOKI, event_id))
    if payload.get("status") != "success":
        raise RuntimeError("Query Loki non riuscita")
    return [
        line
        for stream in payload.get("data", {}).get("result", [])
        for _, line in stream.get("values", [])
    ]


def assert_stream_json() -> int:
    expression = '{archive="technical",source_family="pilot",service="fixture"}'
    url = logs.LOKI + "/loki/api/v1/query_range?" + urlencode(
        {"query": expression, "since": "10m", "limit": "500"}
    )
    payload = logs.request_json(url)
    if payload.get("status") != "success":
        raise RuntimeError("Query della serie Loki non riuscita")
    lines = [
        line
        for stream in payload.get("data", {}).get("result", [])
        for _, line in stream.get("values", [])
    ]
    if not lines or len(lines) >= 500:
        raise RuntimeError("La scansione delle righe Loki è vuota o troncata")
    for line in lines:
        json.loads(line)
    return len(lines)


def assert_absent(event_id: str, seconds: int) -> int:
    deadline = time.monotonic() + seconds
    checks = 0
    while time.monotonic() < deadline:
        if raw_lines(event_id):
            raise RuntimeError("Una riga incompleta è stata pubblicata in Loki")
        checks += 1
        time.sleep(2)
    return checks


def wait_for_full_record(expected: dict) -> None:
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            lines = raw_lines(expected["event_id"])
            if lines:
                records = [json.loads(line) for line in lines]
                if records != [expected]:
                    raise RuntimeError("Loki non contiene esattamente il record completo")
                return
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(2)
    raise RuntimeError("Il record completo non è arrivato in Loki dopo 75 secondi")


def prepare() -> None:
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))
        if "complete_sha256" not in previous:
            raise RuntimeError("Stato parziale già presente: completare o esaminare la prova precedente")
        history = ROOT / "fixtures" / "state-history"
        history.mkdir(exist_ok=True)
        STATE.replace(history / f"partial-{uuid4().hex}.json")
    control_id, control = fixture.emit()
    wait_for_full_record(control)
    event_id, record = fixture.create_record()
    line = fixture.serialized_line(record)
    split = len(line) // 2
    if event_id not in line[:split] or "\n" in line[:split]:
        raise RuntimeError("La prima metà non rende osservabile un'eventuale pubblicazione prematura")
    segment = unique_segment()
    with segment.open("a", encoding="utf-8", newline="\n") as output:
        output.write(line[:split])
    checks = assert_absent(event_id, 14)
    state = {
        "control_id": control_id,
        "event_id": event_id,
        "record": record,
        "segment": segment.name,
        "prefix_sha256": sha256(line[:split].encode("utf-8")).hexdigest(),
        "remainder": line[split:],
        "checks_before_restart": checks,
    }
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prima del riavvio: {checks} query senza riga parziale; riavviare solo Alloy")


def finish() -> None:
    if not STATE.exists():
        raise RuntimeError("Eseguire prima prepare e riavviare Alloy")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    event_id = state["event_id"]
    segment = ROOT / "fixtures" / state["segment"]
    prefix = segment.read_bytes()
    if sha256(prefix).hexdigest() != state["prefix_sha256"] or b"\n" in prefix:
        raise RuntimeError("Il prefisso è stato modificato prima del completamento")
    control_id, control = fixture.create_record()
    control_segment = unique_segment()
    control_segment.write_text(fixture.serialized_line(control), encoding="utf-8", newline="\n")
    wait_for_full_record(control)
    checks = assert_absent(event_id, 4)
    with segment.open("a", encoding="utf-8", newline="\n") as output:
        output.write(state["remainder"])
    wait_for_full_record(state["record"])
    checked_lines = assert_stream_json()
    original = ROOT / state["record"]["original_ref"]
    if sha256(original.read_bytes()).hexdigest() != state["record"]["original_sha256"]:
        raise RuntimeError("Impronta dell'originale sintetico non coincide")
    state["control_after_restart_id"] = control_id
    state["control_after_restart_segment"] = control_segment.name
    state["checks_after_restart"] = checks
    state["valid_json_lines_checked"] = checked_lines
    state["complete_sha256"] = sha256(segment.read_bytes()).hexdigest()
    state.pop("remainder")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Dopo il riavvio: {checks} query senza riga parziale; record completo presente una volta")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "finish"))
    phase = parser.parse_args().phase
    {"prepare": prepare, "finish": finish}[phase]()


if __name__ == "__main__":
    main()
