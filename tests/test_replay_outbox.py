"""Prove della coda sintetica con arresto e risposta persa del backend."""

import importlib.util
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "pilot" / "monitoring-hub" / "replay-outbox.py"


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("replay_outbox_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path
    (root / "fixtures").mkdir()
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "OUTBOX", root / "fixtures" / "replay-outbox")
    monkeypatch.setattr(module, "REPLAY_ORIGINALS", root / "fixtures" / "replay-original")
    monkeypatch.setattr(module, "LOCAL_PILOT", True)
    monkeypatch.setattr(module.fixture, "FIXTURES", root / "fixtures")
    return module


def test_outage_then_replay_and_restart_are_idempotent(outbox, monkeypatch):
    event_id = outbox.emit()
    assert len(outbox.segments()) == 1
    assert outbox.load_pending()[0]["record"]["event_id"] == event_id
    assert not (outbox.OUTBOX / ".lock").exists()

    def offline(_record):
        raise ConnectionError("Loki fermo")

    monkeypatch.setattr(outbox, "query", offline)
    with pytest.raises(ConnectionError):
        outbox.reconcile(True)
    assert len(outbox.segments()) == 1
    assert not (outbox.OUTBOX / ".lock").exists()

    indexed = {}
    sent = []

    def query(record):
        return indexed.get(record["event_id"], []).copy()

    def push(item):
        record = item["record"]
        sent.append(record["event_id"])
        indexed[record["event_id"]] = [record]

    monkeypatch.setattr(outbox, "query", query)
    monkeypatch.setattr(outbox, "push", push)
    assert outbox.reconcile(False)["missing_before"] == 1
    assert not sent
    assert outbox.reconcile(True)["pushed"] == 1
    assert sent == [event_id]
    assert outbox.reconcile(True)["pushed"] == 0
    assert sent == [event_id]


def test_lost_push_reply_and_invalid_lot_block_writes(outbox, monkeypatch):
    first_id = outbox.emit()
    indexed = {}
    sent = []

    def query(record):
        return indexed.get(record["event_id"], []).copy()

    def push_then_lose_reply(item):
        record = item["record"]
        sent.append(record["event_id"])
        indexed[record["event_id"]] = [record]
        raise TimeoutError("risposta persa dopo l'indicizzazione")

    monkeypatch.setattr(outbox, "query", query)
    monkeypatch.setattr(outbox, "push", push_then_lose_reply)
    with pytest.raises(TimeoutError):
        outbox.reconcile(True)
    assert sent == [first_id]
    assert outbox.reconcile(True)["pushed"] == 0
    assert sent == [first_id]

    outbox.emit()
    newest = outbox.segments()[-1]
    newest.write_bytes(newest.read_bytes() + b'{"message":"non classificato"}\n')
    with pytest.raises((RuntimeError, outbox.guard.Rejected)):
        outbox.reconcile(True)
    assert sent == [first_id]


def test_staged_segment_left_by_crash_blocks_new_emission(outbox):
    outbox.emit()
    staged = outbox.OUTBOX / (".pending-" + "0" * 32 + ".tmp")
    staged.write_bytes(b"incompleto")
    before = len(list(outbox.REPLAY_ORIGINALS.glob("*.log")))
    with pytest.raises(RuntimeError, match="temporaneo residuo"):
        outbox.emit()
    after = len(list(outbox.REPLAY_ORIGINALS.glob("*.log")))
    assert after == before


def test_unexpected_file_blocks_emission_and_replay(outbox, monkeypatch):
    outbox.emit()
    rogue = outbox.OUTBOX / "non-classificato.bin"
    rogue.write_bytes(b"x" * 64)
    originals = outbox.REPLAY_ORIGINALS
    before = sorted(path.name for path in originals.iterdir())
    network_calls = []
    monkeypatch.setattr(outbox, "query", lambda _record: network_calls.append("query"))
    monkeypatch.setattr(outbox, "push", lambda _item: network_calls.append("push"))
    with pytest.raises(RuntimeError, match="inatteso"):
        outbox.emit()
    with pytest.raises(RuntimeError, match="inatteso"):
        outbox.reconcile(True)
    assert sorted(path.name for path in originals.iterdir()) == before
    assert network_calls == []


def test_old_record_can_be_queried_but_cannot_be_pushed(outbox, monkeypatch):
    outbox.emit()
    record = outbox.load_pending()[0]["record"]
    urls = []

    def response(request, timeout):
        urls.append(request.full_url)
        assert timeout == 15
        return BytesIO(b'{"status":"success","data":{"result":[]}}')

    monkeypatch.setattr(outbox, "urlopen", response)
    assert outbox.query(record) == []
    params = parse_qs(urlsplit(urls[0]).query)
    assert "since" not in params
    assert (int(params["end"][0]) - int(params["start"][0])) == 4_000_000_000

    monkeypatch.setattr(outbox, "MAX_AGE", -timedelta(seconds=1))
    assert outbox.query(record) == []
    assert len(urls) == 2
    item = outbox.load_pending()[0]
    with pytest.raises(RuntimeError, match="fuori dalla finestra"):
        outbox.push(item)
    assert len(urls) == 2


def test_delayed_index_after_lost_reply_never_retries_push(outbox, monkeypatch):
    event_id = outbox.emit()
    item = outbox.load_pending()[0]
    indexed = {}
    sent = []
    monkeypatch.setattr(outbox, "query", lambda record: indexed.get(record["event_id"], []))

    def accepted_but_unconfirmed(payload):
        marker = outbox.OUTBOX / (
            ".attempt-" + payload["segment"].stem.removeprefix("technical-") + ".sha256"
        )
        assert marker.read_bytes() == payload["sha256"].encode("ascii") + b"\n"
        sent.append(payload["record"]["event_id"])
        raise TimeoutError("Risposta persa prima dell'indicizzazione")

    monkeypatch.setattr(outbox, "push", accepted_but_unconfirmed)
    with pytest.raises(TimeoutError, match="Risposta persa"):
        outbox.reconcile(True)
    assert sent == [event_id]
    assert outbox.spool_status()["attempt_markers"] == 1
    assert outbox.reconcile(False)["uncertain_missing"] == 1
    with pytest.raises(RuntimeError, match="invio incerto"):
        outbox.reconcile(True)
    assert sent == [event_id]
    indexed[event_id] = [item["record"]]
    assert outbox.reconcile(True)["pushed"] == 0
    assert sent == [event_id]


def test_changed_attempt_marker_blocks_before_query(outbox, monkeypatch):
    outbox.emit()
    monkeypatch.setattr(outbox, "query", lambda _record: [])
    monkeypatch.setattr(outbox, "push", lambda _item: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(TimeoutError):
        outbox.reconcile(True)
    marker = next(outbox.OUTBOX.glob(".attempt-*.sha256"))
    marker.write_bytes(b"0" * 64 + b"\n")
    calls = []
    monkeypatch.setattr(outbox, "query", lambda _record: calls.append("query"))
    with pytest.raises(RuntimeError, match="diverso dal segmento"):
        outbox.reconcile(True)
    assert calls == []


def test_segment_changed_between_queries_blocks_before_marker_or_push(outbox, monkeypatch):
    outbox.emit()
    segment = outbox.segments()[0]
    queries = []

    def query_and_change(_record):
        queries.append("query")
        if len(queries) == 2:
            segment.write_bytes(segment.read_bytes().removesuffix(b"\n") + b" \n")
        return []

    monkeypatch.setattr(outbox, "query", query_and_change)
    monkeypatch.setattr(
        outbox, "push", lambda _item: (_ for _ in ()).throw(AssertionError("POST inattesa"))
    )
    with pytest.raises(RuntimeError, match="Segmento cambiato prima dell'invio"):
        outbox.reconcile(True)
    assert queries == ["query", "query"]
    assert list(outbox.OUTBOX.glob(".attempt-*.sha256")) == []


def test_failed_directory_sync_keeps_marker_and_prevents_push(outbox, monkeypatch):
    outbox.emit()
    monkeypatch.setattr(outbox, "query", lambda _record: [])
    sent = []
    monkeypatch.setattr(outbox, "push", lambda item: sent.append(item))

    def failed_sync():
        raise OSError(5, "Errore fsync della directory")

    monkeypatch.setattr(outbox, "sync_outbox_directory", failed_sync)
    with pytest.raises(OSError, match="fsync"):
        outbox.reconcile(True)
    assert sent == []
    assert outbox.spool_status()["attempt_markers"] == 1
    with pytest.raises(RuntimeError, match="invio incerto"):
        outbox.reconcile(True)
    assert sent == []


def test_stale_segment_blocks_lot_before_fresh_push(outbox, monkeypatch):
    old_now = datetime.now(UTC) - timedelta(hours=1)
    original_datetime = outbox.fixture.datetime

    class OldClock:
        @staticmethod
        def now(_timezone):
            return old_now

    monkeypatch.setattr(outbox.fixture, "datetime", OldClock)
    old_event = outbox.emit()
    monkeypatch.setattr(outbox.fixture, "datetime", original_datetime)
    fresh_event = outbox.emit()
    assert old_event != fresh_event
    queried = []
    pushed = []
    monkeypatch.setattr(outbox, "query", lambda record: queried.append(record["event_id"]) or [])
    monkeypatch.setattr(outbox, "push", lambda item: pushed.append(item["record"]["event_id"]))
    report = outbox.reconcile(False)
    assert report["stale_missing"] == 1
    assert report["requires_review"] == 1
    assert set(queried) == {old_event, fresh_event}
    assert outbox.spool_status()["stale_segments"] == 1
    with pytest.raises(RuntimeError, match="segmento vecchio"):
        outbox.reconcile(True)
    assert pushed == []

    old_record = next(
        item["record"] for item in outbox.load_pending()
        if item["record"]["event_id"] == old_event
    )
    indexed = {old_event: [old_record]}

    def indexed_query(record):
        return indexed.get(record["event_id"], [])

    def indexed_push(item):
        record = item["record"]
        pushed.append(record["event_id"])
        indexed[record["event_id"]] = [record]

    monkeypatch.setattr(outbox, "query", indexed_query)
    monkeypatch.setattr(outbox, "push", indexed_push)
    assert outbox.reconcile(True)["pushed"] == 1
    assert pushed == [fresh_event]


def test_second_process_cannot_reconcile_while_first_holds_lock(outbox, tmp_path, monkeypatch):
    ready = tmp_path / "child-ready"
    child_code = """
import importlib.util
from pathlib import Path
import sys

script, root, ready = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("replay_lock_child", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = root
module.OUTBOX = root / "fixtures" / "replay-outbox"
module.REPLAY_ORIGINALS = root / "fixtures" / "replay-original"
module.LOCAL_PILOT = True
with module.exclusive():
    ready.write_text("locked", encoding="ascii")
    sys.stdin.readline()
"""
    child = subprocess.Popen(
        [sys.executable, "-c", child_code, str(SCRIPT), str(outbox.ROOT), str(ready)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.read_text(encoding="ascii") == "locked"
        calls = []
        monkeypatch.setattr(outbox, "query", lambda _record: calls.append("query"))
        with pytest.raises(RuntimeError, match="Coda occupata"):
            outbox.reconcile(True)
        assert calls == []
    finally:
        try:
            _stdout, stderr = child.communicate(input="\n", timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            _stdout, stderr = child.communicate(timeout=10)
        assert child.returncode == 0, stderr


def test_total_quota_counts_originals_before_creating_another(outbox, monkeypatch):
    outbox.emit()
    originals = outbox.REPLAY_ORIGINALS
    before = sorted(path.name for path in originals.glob("*.log"))
    candidate = outbox.fixture.build_record(original_dir="replay-original")
    next_payload = outbox.fixture.serialized_line(candidate[2]).encode("utf-8")
    used = sum(path.stat().st_size for path in outbox.segments())
    used += sum(path.stat().st_size for path in originals.iterdir())
    monkeypatch.setattr(outbox.fixture, "build_record", lambda **_kwargs: candidate)
    monkeypatch.setattr(outbox, "MAX_BYTES", used + len(next_payload))
    with pytest.raises(RuntimeError, match="Coda piena"):
        outbox.emit()
    assert sorted(path.name for path in originals.glob("*.log")) == before
    assert len(outbox.segments()) == 1


def test_emission_reserves_attempt_marker_for_every_unattempted_segment(outbox, monkeypatch):
    outbox.emit()
    used = outbox.capacity(outbox.segments())
    candidate = outbox.fixture.build_record(original_dir="replay-original")
    raw = candidate[1]
    payload = outbox.fixture.serialized_line(candidate[2]).encode("utf-8")
    monkeypatch.setattr(outbox.fixture, "build_record", lambda **_kwargs: candidate)
    outbox.MAX_BYTES = used + len(raw) + len(payload) + outbox.ATTEMPT_BYTES
    with pytest.raises(RuntimeError, match="Coda piena"):
        outbox.emit()
    assert len(outbox.segments()) == 1


def test_new_originals_are_isolated_from_other_fixture_writers(outbox):
    first = outbox.emit()
    record = outbox.load_pending()[0]["record"]
    assert record["event_id"] == first
    assert record["original_ref"] == f"fixtures/replay-original/{first}.log"
    assert (outbox.REPLAY_ORIGINALS / f"{first}.log").is_file()

    shared = outbox.ROOT / "fixtures" / "original"
    shared.mkdir()
    (shared / "unrelated.log").write_bytes(b"x" * (outbox.MAX_BYTES + 1))
    used = outbox.capacity(outbox.segments())
    assert used < outbox.MAX_BYTES
    assert outbox.emit() != first
    assert outbox.capacity(outbox.segments()) < outbox.MAX_BYTES


def test_historical_segment_keeps_its_original_and_counts_only_that_file(outbox):
    event_id, raw, record = outbox.fixture.build_record()
    outbox.fixture.write_original(event_id, raw)
    outbox.OUTBOX.mkdir()
    old = outbox.OUTBOX / ("technical-" + "a" * 32 + ".jsonl")
    old.write_text(outbox.fixture.serialized_line(record), encoding="utf-8")
    shared = outbox.ROOT / "fixtures" / "original"
    (shared / "unrelated.log").write_bytes(b"x" * (outbox.MAX_BYTES + 1))

    assert outbox.capacity(outbox.segments()) == len(raw) + old.stat().st_size
    assert outbox.load_pending()[0]["record"] == record
    assert outbox.emit() != event_id
    assert (shared / f"{event_id}.log").read_bytes() == raw
    assert (outbox.REPLAY_ORIGINALS / f"{event_id}.log").exists() is False


def test_bounded_mode_rejects_historical_original_outside_spool(outbox):
    event_id, raw, record = outbox.fixture.build_record()
    outbox.fixture.write_original(event_id, raw)
    outbox.OUTBOX.mkdir()
    old = outbox.OUTBOX / ("technical-" + "a" * 32 + ".jsonl")
    old.write_text(outbox.fixture.serialized_line(record), encoding="utf-8")
    outbox.LOCAL_PILOT = False
    with pytest.raises(RuntimeError, match="Segmento storico fuori dal filesystem limitato"):
        outbox.capacity(outbox.segments())


def test_unexpected_replay_original_blocks_emission(outbox):
    outbox.emit()
    before = sorted(path.name for path in outbox.REPLAY_ORIGINALS.iterdir())
    (outbox.REPLAY_ORIGINALS / "unclassified.bin").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="Originale non regolare"):
        outbox.emit()
    after = sorted(path.name for path in outbox.REPLAY_ORIGINALS.iterdir())
    assert after == sorted(before + ["unclassified.bin"])


def test_bounded_mode_rejects_missing_mount_before_any_write_or_query(outbox, monkeypatch):
    outbox.LOCAL_PILOT = False
    calls = []
    monkeypatch.setattr(outbox, "query", lambda _record: calls.append("query"))
    with pytest.raises(RuntimeError, match="mount Linux|Mount dedicato"):
        outbox.emit()
    with pytest.raises(RuntimeError, match="mount Linux|Mount dedicato"):
        outbox.reconcile(True)
    assert not outbox.OUTBOX.exists()
    assert not outbox.REPLAY_ORIGINALS.exists()
    assert calls == []


def test_full_disk_during_lock_write_does_not_leave_false_lock(outbox, monkeypatch):
    def no_space(_fd):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(outbox.os, "fsync", no_space)
    with pytest.raises(OSError, match="No space left on device"):
        outbox.emit()
    assert not (outbox.OUTBOX / ".lock").exists()
    assert not outbox.REPLAY_ORIGINALS.exists()


def test_original_directory_sync_failure_stops_before_segment_publication(outbox, monkeypatch):
    def failed_sync(path):
        assert path == outbox.REPLAY_ORIGINALS
        raise OSError(5, "directory sync failed")

    monkeypatch.setattr(outbox, "sync_directory", failed_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        outbox.emit()
    assert outbox.segments() == []
    assert len(list(outbox.REPLAY_ORIGINALS.iterdir())) == 1
    assert not (outbox.OUTBOX / ".lock").exists()


def test_segment_directory_sync_failure_keeps_segment_for_triage(outbox, monkeypatch):
    def failed_sync():
        raise OSError(5, "directory sync failed")

    monkeypatch.setattr(outbox, "sync_outbox_directory", failed_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        outbox.emit()
    assert len(outbox.segments()) == 1
    assert outbox.capacity(outbox.segments()) > 0
    assert not (outbox.OUTBOX / ".lock").exists()


def test_mount_validation_requires_both_paths_and_small_filesystem(outbox, monkeypatch):
    outbox.OUTBOX.mkdir()
    outbox.REPLAY_ORIGINALS.mkdir()
    both = {str(outbox.OUTBOX), str(outbox.REPLAY_ORIGINALS)}
    with pytest.raises(RuntimeError, match="Mount dedicato"):
        outbox.validate_spool_mounts({str(outbox.OUTBOX)})

    blocks = [128]
    monkeypatch.setattr(
        outbox.os, "statvfs",
        lambda _path: SimpleNamespace(f_blocks=blocks[0], f_frsize=1024 * 1024),
        raising=False,
    )
    with pytest.raises(RuntimeError, match="Filesystem della coda non limitato"):
        outbox.validate_spool_mounts(both)
    blocks[0] = 32
    outbox.validate_spool_mounts(both)


def test_partial_original_after_full_disk_blocks_further_emission(outbox, monkeypatch):
    write_original = outbox.fixture.write_original

    def full_disk(event_id, raw, original_dir):
        write_original(event_id, raw[:16], original_dir=original_dir)
        raise OSError(28, "Spazio esaurito")

    monkeypatch.setattr(outbox.fixture, "write_original", full_disk)
    with pytest.raises(OSError, match="Spazio esaurito"):
        outbox.emit()
    assert outbox.segments() == []
    assert len(list(outbox.REPLAY_ORIGINALS.iterdir())) == 1
    monkeypatch.setattr(outbox.fixture, "write_original", write_original)
    with pytest.raises(RuntimeError, match="Originale senza segmento"):
        outbox.emit()
    assert outbox.segments() == []


def test_local_status_reports_logical_warning_without_claiming_mount(outbox):
    outbox.emit()
    normal = outbox.spool_status()
    assert normal["bounded_mount_verified"] is False
    assert normal["filesystem_bytes_available"] is None
    assert normal["filesystem_inodes_available"] is None
    assert normal["warning_reasons"] == []
    outbox.MAX_BYTES = normal["logical_bytes"]
    warning = outbox.spool_status()
    assert warning["warning_reasons"] == ["logical_bytes_80_percent"]
    assert not (outbox.OUTBOX / ".lock").exists()


def test_status_cli_exits_two_at_warning_threshold(outbox, monkeypatch, capsys):
    outbox.emit()
    outbox.MAX_BYTES = outbox.capacity(outbox.segments())
    monkeypatch.setattr(sys, "argv", ["replay-outbox.py", "status", "--local-pilot"])
    with pytest.raises(SystemExit) as stopped:
        outbox.main()
    assert stopped.value.code == 2
    report = outbox.json.loads(capsys.readouterr().out)
    assert report["warning_reasons"] == ["logical_bytes_80_percent"]
    assert report["bounded_mount_verified"] is False


def test_duplicate_event_id_blocks_whole_replay(outbox, monkeypatch):
    outbox.emit()
    first = outbox.segments()[0]
    duplicate = outbox.OUTBOX / ("technical-" + "f" * 32 + ".jsonl")
    duplicate.write_bytes(first.read_bytes())
    network_calls = []
    monkeypatch.setattr(outbox, "query", lambda _record: network_calls.append("query"))
    monkeypatch.setattr(outbox, "push", lambda _item: network_calls.append("push"))
    with pytest.raises(RuntimeError, match="ripetuto"):
        outbox.reconcile(True)
    assert network_calls == []


def test_segment_name_collision_preserves_existing_record_and_originals(outbox, monkeypatch):
    outbox.emit()
    existing = outbox.segments()[0]
    saved = existing.read_bytes()
    originals = outbox.REPLAY_ORIGINALS
    before = sorted(path.name for path in originals.iterdir())
    marker = existing.stem.removeprefix("technical-")
    monkeypatch.setattr(outbox, "uuid4", lambda: type("Id", (), {"hex": marker})())

    with pytest.raises(RuntimeError, match="destinazione già presente"):
        outbox.emit()

    assert existing.read_bytes() == saved
    assert sorted(path.name for path in originals.iterdir()) == before
    assert not (outbox.OUTBOX / ".lock").exists()


def test_external_writer_between_guard_and_publish_cannot_be_overwritten(outbox, monkeypatch):
    marker = "f" * 32
    segment = outbox.OUTBOX / f"technical-{marker}.jsonl"
    staged = outbox.OUTBOX / f".pending-{marker}.tmp"
    monkeypatch.setattr(outbox, "uuid4", lambda: type("Id", (), {"hex": marker})())
    write_original = outbox.fixture.write_original

    def external_writer(event_id, raw, original_dir):
        write_original(event_id, raw, original_dir=original_dir)
        segment.write_bytes(b"segmento scritto da un altro processo\n")

    monkeypatch.setattr(outbox.fixture, "write_original", external_writer)
    with pytest.raises(RuntimeError, match="comparso durante la pubblicazione"):
        outbox.emit()

    assert segment.read_bytes() == b"segmento scritto da un altro processo\n"
    assert staged.exists()
    assert not (outbox.OUTBOX / ".lock").exists()
