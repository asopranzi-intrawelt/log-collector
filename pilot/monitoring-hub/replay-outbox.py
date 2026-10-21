"""Coda locale e replay dei soli eventi sintetici del pilota.

Il processo e il lettore Alloy non condividono i segmenti di questa coda.
L'indice Loki e la fonte di conferma; un risultato ambiguo blocca il replay.
"""

import argparse
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
OUTBOX = ROOT / "fixtures" / "replay-outbox"
REPLAY_ORIGINALS = ROOT / "fixtures" / "replay-original"
PROJECT = ROOT.parents[1]
LOKI = "http://127.0.0.1:13100"
SEGMENT_NAME = re.compile(r"technical-[0-9a-f]{32}\.jsonl\Z")
ATTEMPT_NAME = re.compile(r"\.attempt-[0-9a-f]{32}\.sha256\Z")
MAX_BYTES = 8 * 1024 * 1024
MAX_SEGMENTS = 256
MAX_AGE = timedelta(minutes=55)
MAX_BOUNDED_FILESYSTEM_BYTES = 64 * 1024 * 1024
ATTEMPT_BYTES = 65
LOCAL_PILOT = False


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
    check_spool_mount()
    OUTBOX.mkdir(parents=True, exist_ok=True)
    if OUTBOX.is_symlink() or OUTBOX.is_junction():
        raise RuntimeError("Cartella della coda collegata altrove")
    lock = OUTBOX / ".lock"
    try:
        handle = lock.open("x", encoding="ascii")
    except FileExistsError as exc:
        raise RuntimeError("Coda occupata o lock residuo: verificare prima di sbloccare") from exc
    try:
        with handle:
            handle.write(f"pid={os.getpid()}\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # L'apertura esclusiva riuscita ha creato questo lock.
        # Un errore sincrono di scrittura non deve lasciarlo come falso residuo.
        lock.unlink()
        raise
    try:
        yield
    finally:
        lock.unlink()


def check_spool_mount() -> None:
    """In modalità vincolata rifiuta il fallback sul filesystem padre."""
    if LOCAL_PILOT:
        return
    if os.name != "posix":
        raise RuntimeError(
            "La coda vincolata richiede un mount Linux; usare --local-pilot solo per le fixture"
        )
    mounts = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    mounted_paths = {line.split(" - ", 1)[0].split()[4] for line in mounts}
    validate_spool_mounts(mounted_paths)


def validate_spool_mounts(mounted_paths: set[str]) -> None:
    """Controlla i due percorsi e il loro filesystem, senza creare directory."""
    for path in (OUTBOX, REPLAY_ORIGINALS):
        if not path.is_dir() or path.is_symlink() or str(path) not in mounted_paths:
            raise RuntimeError(
                "Mount dedicato della coda assente o non valido"
            )
    if OUTBOX.stat().st_dev != REPLAY_ORIGINALS.stat().st_dev:
        raise RuntimeError("Segmenti e originali non condividono il filesystem limitato")
    filesystems = [os.statvfs(path) for path in (OUTBOX, REPLAY_ORIGINALS)]
    sizes = [fs.f_blocks * fs.f_frsize for fs in filesystems]
    if sizes[0] != sizes[1] or not 0 < sizes[0] <= MAX_BOUNDED_FILESYSTEM_BYTES:
        raise RuntimeError("Filesystem della coda non limitato alla dimensione del pilot")


def segments() -> list[Path]:
    paths = []
    for path in OUTBOX.iterdir():
        if path.name == ".lock":
            continue
        if path.name.startswith(".pending-"):
            raise RuntimeError("Segmento temporaneo residuo: verificare prima di proseguire")
        if ATTEMPT_NAME.fullmatch(path.name):
            if path.is_symlink() or path.is_junction() or not path.is_file():
                raise RuntimeError("Tentativo di invio non regolare nella coda")
            continue
        if not SEGMENT_NAME.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            raise RuntimeError("File o collegamento inatteso nella coda")
        paths.append(path)
    return sorted(paths)


def attempts(paths: list[Path]) -> dict[Path, Path]:
    """Associa ogni intento durevole al segmento esatto e al suo digest."""
    known = {path.stem.removeprefix("technical-"): path for path in paths}
    result = {}
    for marker in OUTBOX.iterdir():
        if not ATTEMPT_NAME.fullmatch(marker.name):
            continue
        if marker.is_symlink() or marker.is_junction() or not marker.is_file():
            raise RuntimeError("Tentativo di invio non regolare nella coda")
        key = marker.name.removeprefix(".attempt-").removesuffix(".sha256")
        segment = known.get(key)
        if segment is None:
            raise RuntimeError("Tentativo di invio senza segmento nella coda")
        expected = sha256(segment.read_bytes()).hexdigest().encode("ascii") + b"\n"
        if marker.read_bytes() != expected:
            raise RuntimeError("Tentativo di invio diverso dal segmento conservato")
        result[segment] = marker
    return result


def sync_directory(path: Path) -> None:
    """Sincronizza la directory su Linux prima di confermare la scrittura."""
    if os.name != "posix":
        return  # Il pilot PC non prova la persistenza dopo perdita di alimentazione.
    directory_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def sync_outbox_directory() -> None:
    """Sincronizza i marker prima di una POST potenzialmente irreversibile."""
    sync_directory(OUTBOX)


def record_attempt(item: dict) -> None:
    marker = OUTBOX / (".attempt-" + item["segment"].stem.removeprefix("technical-") + ".sha256")
    with marker.open("xb") as output:
        output.write(item["sha256"].encode("ascii") + b"\n")
        output.flush()
        os.fsync(output.fileno())
    sync_outbox_directory()


def capacity(paths: list[Path]) -> int:
    if len(paths) > MAX_SEGMENTS:
        raise RuntimeError("Quota del numero di segmenti superata")
    if REPLAY_ORIGINALS.is_symlink() or REPLAY_ORIGINALS.is_junction():
        raise RuntimeError("Cartella degli originali collegata altrove")
    original_paths = list(REPLAY_ORIGINALS.iterdir()) if REPLAY_ORIGINALS.exists() else []
    if any(
        not guard.EVENT_ID.fullmatch(path.stem)
        or path.suffix != ".log"
        or not path.is_file()
        or path.is_symlink()
        or path.is_junction()
        for path in original_paths
    ):
        raise RuntimeError("Originale non regolare nella coda isolata")
    # I due segmenti storici conservano il riferimento alla cartella condivisa.
    # Contiamo solo gli originali cui fanno riferimento, non i file di altri produttori.
    legacy = set()
    referenced_new = set()
    for path in paths:
        checked = guard.check_jsonl(path.read_bytes(), ROOT, allow_replay_original=True)
        if len(checked) != 1:
            raise RuntimeError("Il segmento della coda deve contenere un solo record")
        original_ref = checked[0]["record"]["original_ref"]
        if original_ref.startswith("fixtures/original/"):
            legacy.add(ROOT / original_ref)
        else:
            referenced_new.add(ROOT / original_ref)
    if legacy and not LOCAL_PILOT:
        raise RuntimeError("Segmento storico fuori dal filesystem limitato: trattare manualmente")
    if set(original_paths) != referenced_new:
        raise RuntimeError("Originale senza segmento o segmento senza originale nella coda")
    marker_paths = list(attempts(paths).values())
    counted_paths = paths + original_paths + sorted(legacy) + marker_paths
    total = sum(path.stat().st_size for path in counted_paths)
    if total > MAX_BYTES:
        raise RuntimeError("Quota byte di segmenti e originali superata")
    return total


def emit() -> str:
    with exclusive():
        paths = segments()
        used = capacity(paths)
        unattempted = len(paths) - len(attempts(paths))
        if len(paths) >= MAX_SEGMENTS:
            raise RuntimeError("Coda piena: nessun nuovo originale creato")
        event_id, raw, record = fixture.build_record(original_dir="replay-original")
        payload = fixture.serialized_line(record).encode("utf-8")
        if (len(raw) > guard.MAX_ORIGINAL_BYTES or
                len(payload) > guard.MAX_JSONL_BYTES or
                used + len(raw) + len(payload) + ATTEMPT_BYTES * (unattempted + 1)
                > MAX_BYTES):
            raise RuntimeError("Coda piena: nessun nuovo originale creato")
        marker = uuid4().hex
        staged = OUTBOX / f".pending-{marker}.tmp"
        segment = OUTBOX / f"technical-{marker}.jsonl"
        if segment.exists() or segment.is_symlink():
            raise RuntimeError("Segmento di destinazione già presente nella coda")
        fixture.write_original(event_id, raw, original_dir="replay-original")
        sync_directory(REPLAY_ORIGINALS)
        guard.check_jsonl(payload, ROOT, allow_replay_original=True)
        with staged.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(staged, segment)
        except FileExistsError as exc:
            raise RuntimeError(
                "Segmento di destinazione comparso durante la pubblicazione"
            ) from exc
        staged.unlink()
        sync_outbox_directory()
        return event_id


def recent_instant(record: dict) -> datetime:
    instant = datetime.fromisoformat(record["event_at"])
    age = datetime.now(UTC) - instant
    if age > MAX_AGE or age < -timedelta(seconds=5):
        raise RuntimeError("Evento fuori dalla finestra di replay: intervento manuale richiesto")
    return instant


def replay_age(record: dict) -> str:
    age = datetime.now(UTC) - datetime.fromisoformat(record["event_at"])
    if age < -timedelta(seconds=5):
        return "future"
    if age > MAX_AGE:
        return "stale"
    return "fresh"


def load_pending() -> list[dict]:
    paths = segments()
    capacity(paths)
    markers = attempts(paths)
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
        result.append({
            "record": record, "labels": item["labels"],
            "sha256": sha256(raw).hexdigest(), "segment": path,
            "attempted": path in markers,
        })
    return result


def spool_status() -> dict:
    """Espone saturazione e modalità senza attribuire al pilot una quota fisica locale."""
    with exclusive():
        paths = segments()
        used = capacity(paths)
        items = load_pending()
        age_states = [replay_age(item["record"]) for item in items]
        reasons = []
        if used * 100 >= MAX_BYTES * 80:
            reasons.append("logical_bytes_80_percent")
        if len(paths) * 100 >= MAX_SEGMENTS * 80:
            reasons.append("segments_80_percent")
        if "stale" in age_states:
            reasons.append("stale_segments")
        if "future" in age_states:
            reasons.append("future_segments")
        result = {
            "bounded_mount_verified": not LOCAL_PILOT,
            "segments": len(paths),
            "logical_bytes": used,
            "logical_limit_bytes": MAX_BYTES,
            "attempt_markers": sum(item["attempted"] for item in items),
            "stale_segments": age_states.count("stale"),
            "future_segments": age_states.count("future"),
            "filesystem_bytes_available": None,
            "filesystem_inodes_available": None,
            "warning_reasons": reasons,
        }
        if not LOCAL_PILOT:
            fs = os.statvfs(OUTBOX)
            total = fs.f_blocks * fs.f_frsize
            available = fs.f_bavail * fs.f_frsize
            result["filesystem_bytes_available"] = available
            result["filesystem_inodes_available"] = fs.f_favail
            if available * 100 <= total * 20:
                reasons.append("filesystem_bytes_available_20_percent")
            if fs.f_files and fs.f_favail * 100 <= fs.f_files * 20:
                reasons.append("filesystem_inodes_available_20_percent")
        return result


def query(record: dict) -> list[dict]:
    instant = datetime.fromisoformat(record["event_at"])
    expression = (
        '{archive="technical",source_family="pilot",service="fixture"} |= "'
        + record["event_id"] + '"'
    )
    start_ns = int((instant - timedelta(seconds=2)).timestamp() * 1_000_000_000)
    end_ns = int((instant + timedelta(seconds=2)).timestamp() * 1_000_000_000)
    url = LOKI + "/loki/api/v1/query_range?" + urlencode({
        "query": expression, "start": str(start_ns), "end": str(end_ns), "limit": "20",
    })
    with urlopen(Request(url), timeout=15) as response:
        payload = json.load(response)
    return logs.check_labels(logs.entries(payload), record)


def push(item: dict) -> None:
    record = item["record"]
    instant = recent_instant(record)
    seconds = int(instant.timestamp())
    timestamp_ns = str(seconds * 1_000_000_000 + instant.microsecond * 1_000)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    body = json.dumps(
        {"streams": [{"stream": item["labels"], "values": [[timestamp_ns, line]]}]},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        LOKI + "/loki/api/v1/push", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 204:
            raise RuntimeError("Loki non ha confermato il push")


def reconcile(apply: bool) -> dict:
    with exclusive():
        items = load_pending()  # Valida l'intero lotto prima della prima query o scrittura.
        before = [query(item["record"]) for item in items]
        if any(
            found not in ([], [item["record"]])
            for item, found in zip(items, before, strict=True)
        ):
            raise RuntimeError("Indice ambiguo o record diverso: nessun invio")
        missing = [item for item, found in zip(items, before, strict=True) if not found]
        stale = [item for item in missing if replay_age(item["record"]) == "stale"]
        future = [item for item in missing if replay_age(item["record"]) == "future"]
        uncertain = [item for item in missing if item["attempted"]]
        needs_review = {item["segment"] for item in stale + future + uncertain}
        if apply and needs_review:
            raise RuntimeError(
                "Replay sospeso: segmento vecchio, futuro o con invio incerto; "
                "esame manuale richiesto"
            )
        pushed = 0
        if apply:
            for item in missing:
                # La seconda query restringe la finestra di concorrenza con altri writer.
                found = query(item["record"])
                if found == [item["record"]]:
                    continue
                if found:
                    raise RuntimeError("Indice ambiguo prima del push")
                recent_instant(item["record"])
                if capacity(segments()) + ATTEMPT_BYTES > MAX_BYTES:
                    raise RuntimeError("Quota insufficiente per registrare il tentativo di invio")
                if sha256(item["segment"].read_bytes()).hexdigest() != item["sha256"]:
                    raise RuntimeError("Segmento cambiato prima dell'invio")
                record_attempt(item)
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
                    raise RuntimeError(
                        "Push confermato ma record assente dall'indice entro 75 secondi"
                    )
        return {
            "segments": len(items), "present_before": len(items) - len(missing),
            "missing_before": len(missing), "stale_missing": len(stale),
            "future_missing": len(future), "uncertain_missing": len(uncertain),
            "requires_review": len(needs_review), "pushed": pushed,
        }


def main() -> None:
    global LOCAL_PILOT
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    emission = commands.add_parser("emit", help="Crea un solo evento fittizio nella coda locale")
    emission.add_argument(
        "--local-pilot", action="store_true", help="Usa directory locali senza mount limitato"
    )
    replay = commands.add_parser("reconcile", help="Confronta la coda con l'indice Loki")
    replay.add_argument("--apply", action="store_true", help="Invia solo gli eventi assenti")
    replay.add_argument(
        "--local-pilot", action="store_true", help="Usa directory locali senza mount limitato"
    )
    status = commands.add_parser(
        "status", help="Misura la saturazione della coda senza contattare Loki"
    )
    status.add_argument(
        "--local-pilot", action="store_true", help="Usa directory locali senza mount limitato"
    )
    args = parser.parse_args()
    LOCAL_PILOT = args.local_pilot
    if args.command == "emit":
        print(emit())
    elif args.command == "reconcile":
        print(json.dumps(reconcile(args.apply), sort_keys=True))
    else:
        report = spool_status()
        print(json.dumps(report, sort_keys=True))
        if report["warning_reasons"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
