"""Check Alloy continuity across restart and two unique fixture segments."""

import argparse
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
from pathlib import Path
import time
from uuid import uuid4
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parent
STATE = ROOT / "fixtures" / "recovery-state.json"


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
            result = logs.entries(logs.request_json(logs.query_url(logs.LOKI, expected["event_id"])))
            records = logs.check_labels(result, expected)
            if records == [expected]:
                return
            if records:
                raise RuntimeError("Loki ha restituito record inattesi per l'identificativo")
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(2)
    raise RuntimeError("L'evento non è arrivato esattamente una volta alla query Loki")


def emit_and_wait() -> dict:
    _, expected = fixture.emit()
    wait_for_record(expected)
    return expected


def read_state() -> dict:
    if not STATE.exists():
        raise RuntimeError("Prima eseguire la fase prepare")
    return json.loads(STATE.read_text(encoding="utf-8"))


def write_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare() -> None:
    if STATE.exists():
        previous = read_state()
        if "after_rotation_2" not in previous:
            raise RuntimeError("Stato di continuità incompleto: completare o esaminare la prova precedente")
        history = ROOT / "fixtures" / "state-history"
        history.mkdir(exist_ok=True)
        STATE.replace(history / f"recovery-{uuid4().hex}.json")
    state = {"before_restart": emit_and_wait()}
    write_state(state)
    print("Evento di riferimento acquisito; riavviare solo Alloy prima di after-restart")


def after_restart() -> None:
    state = read_state()
    wait_for_record(state["before_restart"])
    state["after_restart"] = emit_and_wait()
    write_state(state)
    print("Dopo il riavvio: evento precedente leggibile e nuovo evento acquisito")


def rotate() -> None:
    state = read_state()
    if "after_restart" not in state:
        raise RuntimeError("Prima eseguire la fase after-restart")
    wait_for_record(state["after_restart"])
    previous = fixture.active_log()
    previous_digest = sha256(previous.read_bytes()).hexdigest()
    lengths = []
    for number in (1, 2):
        state[f"after_rotation_{number}"] = emit_and_wait()
        segment = fixture.active_log()
        if segment == previous:
            raise RuntimeError("Il publisher ha riutilizzato il segmento precedente")
        if segment.read_text(encoding="utf-8") != fixture.serialized_line(
            state[f"after_rotation_{number}"]
        ):
            raise RuntimeError("Il segmento nuovo non contiene esattamente il record atteso")
        wait_for_record(state["after_restart"])
        if sha256(previous.read_bytes()).hexdigest() != previous_digest:
            raise RuntimeError("Un segmento precedente è stato modificato durante la rotazione")
        lengths.append(segment.stat().st_size)
        previous = segment
        previous_digest = sha256(segment.read_bytes()).hexdigest()
    if lengths[0] != lengths[1]:
        raise RuntimeError("I due segmenti non hanno la stessa dimensione del caso regressivo")
    state["active_file"] = fixture.active_log().name
    state["segment_lengths"] = lengths
    write_state(state)
    print("Dopo due nuovi segmenti: evento precedente leggibile e nuovi file acquisiti")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "after-restart", "rotate"))
    phase = parser.parse_args().phase
    {"prepare": prepare, "after-restart": after_restart, "rotate": rotate}[phase]()


if __name__ == "__main__":
    main()
