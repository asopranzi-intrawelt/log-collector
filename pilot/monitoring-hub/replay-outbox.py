"""Coda locale e replay dei soli eventi sintetici del pilota.

Il processo e il lettore Alloy non condividono i segmenti di questa coda.
L'indice Loki e la fonte di conferma; un risultato ambiguo blocca il replay.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
OUTBOX = ROOT / "fixtures" / "replay-outbox"
REPLAY_ORIGINALS = ROOT / "fixtures" / "replay-original"
PROJECT = ROOT.parents[1]
LOKI = "http://127.0.0.1:13100"
SEGMENT_NAME = re.compile(r"technical-[0-9a-f]{32}\.jsonl\Z")
MAX_BYTES = 8 * 1024 * 1024
MAX_SEGMENTS = 256
MAX_AGE = timedelta(minutes=55)


def load_script(path: Path, name: str):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


guard = load_script(PROJECT / "bin" / "pilot_consultation_v0.py", "outbox_guard")
fixture = load_script(ROOT / "emit-fixture.py", "outbox_fixture")
logs = load_script(ROOT / "check-logs.py", "outbox_logs")


@contextmanager
def exclusive():
    fixtures = ROOT / "fixtures"
    if fixtures.is_symlink() or fixtures.is_junction():
        raise RuntimeError("Radice delle fixture collegata altrove")
    OUTBOX.mkdir(parents=True, exist_ok=True)
    if OUTBOX.is_symlink() or OUTBOX.is_junction():
        raise RuntimeError("Cartella della coda collegata altrove")
    lock = OUTBOX / ".lock"
    try:
        with lock.open("x", encoding="ascii") as handle:
            handle.write(f"pid={os.getpid()}\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise RuntimeError("Coda occupata o lock residuo: verificare prima di sbloccare") from exc
    try:
        yield
    finally:
        lock.unlink()


def segments() -> list[Path]:
    paths = []
    for path in OUTBOX.iterdir():
        if path.name == ".lock":
            continue
        if path.name.startswith(".pending-"):
            raise RuntimeError("Segmento temporaneo residuo: verificare prima di proseguire")
        if not SEGMENT_NAME.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            raise RuntimeError("File o collegamento inatteso nella coda")
        paths.append(path)
    return sorted(paths)


def capacity(paths: list[Path]) -> int:
    if len(paths) > MAX_SEGMENTS:
        raise RuntimeError("Quota del numero di segmenti superata")
    if REPLAY_ORIGINALS.is_symlink() or REPLAY_ORIGINALS.is_junction():
        raise RuntimeError("Cartella degli originali collegata altrove")
    original_paths = list(REPLAY_ORIGINALS.iterdir()) if REPLAY_ORIGINALS.exists() else []
    if any(not guard.EVENT_ID.fullmatch(path.stem) or path.suffix != ".log" or
           not path.is_file() or path.is_symlink() for path in original_paths):
        raise RuntimeError("Originale non regolare nella coda isolata")
    # I due segmenti storici conservano il riferimento alla cartella condivisa.
    # Contiamo solo gli originali cui fanno riferimento, non i file di altri produttori.
    legacy = set()
    for path in paths:
        checked = guard.check_jsonl(path.read_bytes(), ROOT, allow_replay_original=True)
        if len(checked) != 1:
            raise RuntimeError("Il segmento della coda deve contenere un solo record")
        original_ref = checked[0]["record"]["original_ref"]
        if original_ref.startswith("fixtures/original/"):
            legacy.add(ROOT / original_ref)
    total = sum(path.stat().st_size for path in paths + original_paths + sorted(legacy))
    if total > MAX_BYTES:
        raise RuntimeError("Quota byte di segmenti e originali superata")
    return total


def emit() -> str:
    with exclusive():
        paths = segments()
        used = capacity(paths)
        if len(paths) >= MAX_SEGMENTS:
            raise RuntimeError("Coda piena: nessun nuovo originale creato")
        event_id, raw, record = fixture.build_record(original_dir="replay-original")
        payload = fixture.serialized_line(record).encode("utf-8")
        if (len(raw) > guard.MAX_ORIGINAL_BYTES or
                len(payload) > guard.MAX_JSONL_BYTES or
                used + len(raw) + len(payload) > MAX_BYTES):
            raise RuntimeError("Coda piena: nessun nuovo originale creato")
        marker = uuid4().hex
        staged = OUTBOX / f".pending-{marker}.tmp"
        segment = OUTBOX / f"technical-{marker}.jsonl"
        if segment.exists() or segment.is_symlink():
            raise RuntimeError("Segmento di destinazione già presente nella coda")
        fixture.write_original(event_id, raw, original_dir="replay-original")
        guard.check_jsonl(payload, ROOT, allow_replay_original=True)
        with staged.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(staged, segment)
        except FileExistsError as exc:
            raise RuntimeError("Segmento di destinazione comparso durante la pubblicazione") from exc
        staged.unlink()
        return event_id


def recent_instant(record: dict) -> datetime:
    instant = datetime.fromisoformat(record["event_at"])
    age = datetime.now(timezone.utc) - instant
    if age > MAX_AGE or age < -timedelta(seconds=5):
        raise RuntimeError("Evento fuori dalla finestra di replay: intervento manuale richiesto")
    return instant


def load_pending() -> list[dict]:
    paths = segments()
    capacity(paths)
    result = []
    ids = set()
    for path in paths:
        raw = path.read_bytes()
        checked = guard.check_jsonl(raw, ROOT, allow_replay_original=True)
        if len(checked) != 1:
            raise RuntimeError("Il segmento della coda deve contenere un solo record")
        item = checked[0]
        record = item["record"]
        event_id = record["event_id"]
        if event_id in ids:
            raise RuntimeError("Identificativo evento ripetuto nella coda")
        ids.add(event_id)
        recent_instant(record)
        result.append({"record": record, "labels": item["labels"], "sha256": sha256(raw).hexdigest()})
    return result


def query(record: dict) -> list[dict]:
    instant = recent_instant(record)
    expression = '{archive="technical",source_family="pilot",service="fixture"} |= "' + record["event_id"] + '"'
    start_ns = int((instant - timedelta(seconds=2)).timestamp() * 1_000_000_000)
    end_ns = int((instant + timedelta(seconds=2)).timestamp() * 1_000_000_000)
    url = LOKI + "/loki/api/v1/query_range?" + urlencode({"query": expression, "start": str(start_ns), "end": str(end_ns), "limit": "20"})
    with urlopen(Request(url), timeout=15) as response:
        payload = json.load(response)
    return logs.check_labels(logs.entries(payload), record)


def push(item: dict) -> None:
    record = item["record"]
    instant = recent_instant(record)
    seconds = int(instant.timestamp())
    timestamp_ns = str(seconds * 1_000_000_000 + instant.microsecond * 1_000)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    body = json.dumps({"streams": [{"stream": item["labels"], "values": [[timestamp_ns, line]]}]}, ensure_ascii=False).encode("utf-8")
    request = Request(LOKI + "/loki/api/v1/push", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=10) as response:
        if response.status != 204:
            raise RuntimeError("Loki non ha confermato il push")


def reconcile(apply: bool) -> dict:
    with exclusive():
        items = load_pending()  # Valida l'intero lotto prima della prima query o scrittura.
        before = [query(item["record"]) for item in items]
        if any(found not in ([], [item["record"]]) for item, found in zip(items, before)):
            raise RuntimeError("Indice ambiguo o record diverso: nessun invio")
        missing = [item for item, found in zip(items, before) if not found]
        pushed = 0
        if apply:
            for item in missing:
                # La seconda query restringe la finestra di concorrenza con altri writer.
                found = query(item["record"])
                if found == [item["record"]]:
                    continue
                if found:
                    raise RuntimeError("Indice ambiguo prima del push")
                push(item)
                pushed += 1
                deadline = time.monotonic() + 75
                while time.monotonic() < deadline:
                    found = query(item["record"])
                    if found == [item["record"]]:
                        break
                    if found:
                        raise RuntimeError("Record diverso o duplicato dopo il push")
                    time.sleep(2)
                else:
                    raise RuntimeError("Push confermato ma record assente dall'indice entro 75 secondi")
        return {"segments": len(items), "present_before": len(items) - len(missing), "missing_before": len(missing), "pushed": pushed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("emit", help="Crea un solo evento fittizio nella coda locale")
    replay = commands.add_parser("reconcile", help="Confronta la coda con l'indice Loki")
    replay.add_argument("--apply", action="store_true", help="Invia solo gli eventi assenti")
    args = parser.parse_args()
    if args.command == "emit":
        print(emit())
    else:
        print(json.dumps(reconcile(args.apply), sort_keys=True))


if __name__ == "__main__":
    main()
