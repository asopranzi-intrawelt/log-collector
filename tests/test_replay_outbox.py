"""Prove della coda sintetica con arresto e risposta persa del backend."""

from datetime import timedelta
import importlib.util
from io import BytesIO
from pathlib import Path
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
    before = len(list((outbox.ROOT / "fixtures" / "original").glob("*.log")))
    with pytest.raises(RuntimeError, match="temporaneo residuo"):
        outbox.emit()
    after = len(list((outbox.ROOT / "fixtures" / "original").glob("*.log")))
    assert after == before


def test_unexpected_file_blocks_emission_and_replay(outbox, monkeypatch):
    outbox.emit()
    rogue = outbox.OUTBOX / "non-classificato.bin"
    rogue.write_bytes(b"x" * 64)
    originals = outbox.ROOT / "fixtures" / "original"
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


def test_query_uses_event_window_and_rechecks_age(outbox, monkeypatch):
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
    with pytest.raises(RuntimeError, match="fuori dalla finestra"):
        outbox.query(record)
    assert len(urls) == 1


def test_total_quota_counts_originals_before_creating_another(outbox, monkeypatch):
    outbox.emit()
    originals = outbox.ROOT / "fixtures" / "original"
    before = sorted(path.name for path in originals.glob("*.log"))
    candidate = outbox.fixture.build_record()
    next_payload = outbox.fixture.serialized_line(candidate[2]).encode("utf-8")
    used = sum(path.stat().st_size for path in outbox.segments())
    used += sum(path.stat().st_size for path in originals.iterdir())
    monkeypatch.setattr(outbox.fixture, "build_record", lambda: candidate)
    monkeypatch.setattr(outbox, "MAX_BYTES", used + len(next_payload))
    with pytest.raises(RuntimeError, match="Coda piena"):
        outbox.emit()
    assert sorted(path.name for path in originals.glob("*.log")) == before
    assert len(outbox.segments()) == 1


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
