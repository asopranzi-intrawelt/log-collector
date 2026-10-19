"""Misura il recupero di due segmenti durante un fermo Loki con riavvio Alloy."""

import argparse
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
STATE = ROOT / "fixtures" / "outage-state.json"


def load_script(name: str):
    loader = SourceFileLoader(name.replace("-", "_"), str(ROOT / name))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


logs = load_script("check-logs.py")
fixture = load_script("emit-fixture.py")


def read_state() -> dict:
    if not STATE.exists():
        raise RuntimeError("Prima eseguire prepare")
    return json.loads(STATE.read_text(encoding="utf-8"))


def write_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_loki_down() -> None:
    try:
        with urlopen(logs.LOKI + "/ready", timeout=3) as response:
            if response.status == 200:
                raise RuntimeError("Loki risponde ancora: il fermo non è iniziato")
    except (HTTPError, URLError, TimeoutError):
        return


def found_records(record: dict) -> list[dict]:
    payload = logs.request_json(logs.query_url(logs.LOKI, record["event_id"]))
    return logs.check_labels(logs.entries(payload), record)


def wait_for_record(record: dict, seconds: int = 90) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            found = found_records(record)
            if found:
                if found != [record]:
                    raise RuntimeError("Loki restituisce un record diverso o duplicato")
                return True
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(2)
    return False


def emit_checked() -> dict:
    _, record = fixture.emit()
    segment = fixture.active_log()
    if segment.read_text(encoding="utf-8") != fixture.serialized_line(record):
        raise RuntimeError("Il segmento non contiene il record emesso")
    original = ROOT / record["original_ref"]
    if sha256(original.read_bytes()).hexdigest() != record["original_sha256"]:
        raise RuntimeError("L'originale sintetico non corrisponde")
    return {"record": record, "segment": segment.name, "segment_sha256": sha256(segment.read_bytes()).hexdigest()}


def prepare() -> None:
    if STATE.exists():
        previous = read_state()
        if "result" not in previous:
            raise RuntimeError("Prova outage incompleta: completare o esaminare lo stato")
        history = ROOT / "fixtures" / "state-history"
        history.mkdir(exist_ok=True)
        STATE.replace(history / f"outage-{uuid4().hex}.json")
    control = emit_checked()
    if not wait_for_record(control["record"], 75):
        raise RuntimeError("Evento di controllo non acquisito prima del fermo")
    write_state({"control": control})
    print("Controllo acquisito; fermare solo Loki")


def before_restart() -> None:
    state = read_state()
    if "before_restart" in state:
        raise RuntimeError("Evento durante fermo già emesso")
    assert_loki_down()
    state["before_restart"] = emit_checked()
    write_state(state)
    time.sleep(10)
    print("Primo segmento pubblicato con Loki fermo; riavviare solo Alloy")


def after_restart() -> None:
    state = read_state()
    if "before_restart" not in state or "after_restart" in state:
        raise RuntimeError("Fasi del fermo fuori ordine")
    assert_loki_down()
    state["after_restart"] = emit_checked()
    write_state(state)
    time.sleep(10)
    print("Secondo segmento pubblicato con Loki ancora fermo; avviare Loki")


def finish() -> None:
    state = read_state()
    if "after_restart" not in state or "result" in state:
        raise RuntimeError("Fasi del fermo fuori ordine")
    result = {}
    for key in ("control", "before_restart", "after_restart"):
        item = state[key]
        segment = ROOT / "fixtures" / item["segment"]
        if sha256(segment.read_bytes()).hexdigest() != item["segment_sha256"]:
            raise RuntimeError("Un segmento è stato modificato durante il fermo")
        result[key] = wait_for_record(item["record"])
    state["result"] = result
    write_state(state)
    print("Esito dei tre eventi: " + json.dumps(result, sort_keys=True))
    if not all(result.values()):
        raise RuntimeError("Uno o più eventi non sono arrivati entro 90 secondi")


def probe() -> None:
    state = read_state()
    result = {
        key: found_records(state[key]["record"]) == [state[key]["record"]]
        for key in ("control", "before_restart", "after_restart")
    }
    print("Presenza corrente dei tre eventi: " + json.dumps(result, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "before-restart", "after-restart", "finish", "probe"))
    phase = parser.parse_args().phase
    {"prepare": prepare, "before-restart": before_restart, "after-restart": after_restart, "finish": finish, "probe": probe}[phase]()


if __name__ == "__main__":
    main()
