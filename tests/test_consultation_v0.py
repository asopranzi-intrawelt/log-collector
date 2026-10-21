"""Prove del guard offline contro il produttore sintetico effettivo."""

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "pilot_consultation_v0.py"
EMITTER = ROOT / "pilot" / "monitoring-hub" / "emit-fixture.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sample(tmp_path):
    emitter = load(EMITTER, "synthetic_emitter")
    emitter.FIXTURES = tmp_path / "fixtures"
    emitter.FIXTURES.mkdir()
    emitter.CURRENT_LOG = emitter.FIXTURES / "current-log.txt"
    emitter.CURRENT_LOG.write_text("technical-test.jsonl\n", encoding="utf-8")
    event_id, record = emitter.emit()
    return tmp_path, event_id, record


def run_cli(root: Path, jsonl: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--jsonl", str(jsonl)],
        capture_output=True,
        text=True,
        check=False,
    )


def write_jsonl(root: Path, *records: dict) -> Path:
    path = root / "input.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return path


def test_real_synthetic_producer_yields_only_fixed_labels(sample):
    root, event_id, record = sample
    name = (root / "fixtures" / "current-log.txt").read_text(encoding="utf-8").strip()
    assert name.startswith("technical-") and name.endswith(".jsonl")
    result = run_cli(root, root / "fixtures" / name)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["record"] == record
    assert output["labels"] == {
        "archive": "technical",
        "source_family": "pilot",
        "service": "fixture",
    }
    assert event_id not in json.dumps(output["labels"])
    assert record["original_sha256"] == sha256(
        (root / record["original_ref"]).read_bytes()
    ).hexdigest()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", "unreviewed-qa"),
        ("parser_name", "unknown-parser"),
        ("archive", "ads"),
        ("service", "per-user-service"),
        ("original_sha256", "0" * 64),
        ("original_ref", "../outside.log"),
        ("message", "Evento tecnico sintetico del pilota token=SEGRETO_SENTINELLA"),
        ("attributes", {"password": "SEGRETO_SENTINELLA"}),
    ],
)
def test_unknown_provenance_and_extra_content_are_rejected(sample, field, value):
    root, _, record = sample
    modified = {**record, field: value}
    result = run_cli(root, write_jsonl(root, modified))
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("rejected:")
    assert "SEGRETO_SENTINELLA" not in result.stderr


def test_modified_original_is_rejected_even_with_matching_digest(sample):
    root, _, record = sample
    original = root / record["original_ref"]
    original.write_bytes(original.read_bytes().rstrip(b"\n") + b" token=SEGRETO_SENTINELLA\n")
    modified = {**record, "original_sha256": sha256(original.read_bytes()).hexdigest()}
    result = run_cli(root, write_jsonl(root, modified))
    assert result.returncode == 1
    assert result.stdout == ""
    assert "SEGRETO_SENTINELLA" not in result.stderr


def test_duplicate_key_is_rejected(sample):
    root, _, record = sample
    line = json.dumps(record).removesuffix("}") + ',"source_id":"pilot-synthetic"}\n'
    path = root / "duplicate.jsonl"
    path.write_text(line, encoding="utf-8")
    result = run_cli(root, path)
    assert result.returncode == 1
    assert result.stdout == ""


def test_replay_original_needs_explicit_guard_mode(sample):
    root, event_id, record = sample
    guard = load(SCRIPT, "replay_guard_test")
    raw = (root / record["original_ref"]).read_bytes()
    replay = root / "fixtures" / "replay-original"
    replay.mkdir()
    (replay / f"{event_id}.log").write_bytes(raw)
    new_record = {**record, "original_ref": f"fixtures/replay-original/{event_id}.log"}
    payload = (json.dumps(new_record, ensure_ascii=False) + "\n").encode("utf-8")

    with pytest.raises(guard.Rejected, match="original_ref"):
        guard.check_jsonl(payload, root)
    assert guard.check_jsonl(payload, root, allow_replay_original=True)[0]["record"] == new_record
    assert run_cli(root, write_jsonl(root, new_record)).returncode == 1


def test_late_bad_record_does_not_release_earlier_good_record(sample):
    root, _, record = sample
    result = run_cli(root, write_jsonl(root, record, {**record, "source_id": "unknown"}))
    assert result.returncode == 1
    assert result.stdout == ""
