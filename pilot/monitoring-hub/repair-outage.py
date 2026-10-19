"""Ripara un solo evento sintetico mancante della prova di fermo Loki."""

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
STATE = ROOT / "fixtures" / "outage-state.json"
RESULT = ROOT / "fixtures" / "repair-state.json"
LOKI = "http://127.0.0.1:13100"


def load_script(path: Path, name: str):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


guard = load_script(PROJECT / "bin" / "pilot_consultation_v0.py", "pilot_guard")
logs = load_script(ROOT / "check-logs.py", "pilot_logs")


def load_missing() -> tuple[dict, dict, str]:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("result", {}).get("before_restart") is not False:
        raise RuntimeError("La prova non identifica un evento mancante")
    item = state["before_restart"]
    segment = ROOT / "fixtures" / item["segment"]
    raw = segment.read_bytes()
    digest = sha256(raw).hexdigest()
    if digest != item["segment_sha256"]:
        raise RuntimeError("Il segmento è cambiato rispetto alla prova")
    checked = guard.check_jsonl(raw, ROOT)
    if len(checked) != 1 or checked[0]["record"] != item["record"]:
        raise RuntimeError("Il guard non conferma il record della prova")
    record = checked[0]["record"]
    instant = datetime.fromisoformat(record["event_at"])
    if instant.utcoffset() != timedelta(0) or datetime.now(timezone.utc) - instant > timedelta(minutes=55):
        raise RuntimeError("Evento fuori dalla finestra di query sicura del pilot")
    return checked[0]["labels"], record, digest


def query(record: dict) -> list[dict]:
    expression = '{archive="technical",source_family="pilot",service="fixture"} |= "' + record["event_id"] + '"'
    url = LOKI + "/loki/api/v1/query_range?" + urlencode({"query": expression, "since": "1h", "limit": "20"})
    payload = logs.request_json(url)
    return logs.check_labels(logs.entries(payload), record)


def save_result(data: dict) -> None:
    RESULT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def archive_previous_result() -> None:
    if RESULT.exists():
        history = ROOT / "fixtures" / "state-history"
        history.mkdir(exist_ok=True)
        RESULT.replace(history / f"repair-{uuid4().hex}.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Invia il record validato solo se assente")
    args = parser.parse_args()
    archive_previous_result()
    labels, record, digest = load_missing()
    found = query(record)
    if found not in ([], [record]):
        raise RuntimeError("Query precedente ambigua: nessun invio")
    result = {
        "event_id": record["event_id"],
        "segment_sha256": digest,
        "labels": labels,
        "before_count": len(found),
        "apply": args.apply,
        "push_status": None,
        "after_count": None,
    }
    save_result(result)
    if found:
        print("Record già indicizzato: nessun invio")
        return
    if not args.apply:
        print("Guard e query riusciti: un record sintetico mancante, invio non richiesto")
        return
    instant = datetime.fromisoformat(record["event_at"])
    timestamp_ns = str(int(instant.timestamp()) * 1_000_000_000)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    body = json.dumps({"streams": [{"stream": labels, "values": [[timestamp_ns, line]]}]}, ensure_ascii=False).encode("utf-8")
    request = Request(LOKI + "/loki/api/v1/push", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=10) as response:
        result["push_status"] = response.status
    save_result(result)
    if result["push_status"] != 204:
        raise RuntimeError("Loki non ha confermato il push con 204")
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        found = query(record)
        if found:
            if found != [record]:
                raise RuntimeError("Record di riparazione diverso o duplicato")
            result["after_count"] = len(found)
            save_result(result)
            print("Record sintetico validato, inviato e letto una volta dall'indice Loki")
            return
        time.sleep(2)
    raise RuntimeError("Push confermato ma record non indicizzato entro 75 secondi")


if __name__ == "__main__":
    main()
