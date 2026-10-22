"""The offline receiver must persist one validated QA event before acknowledging it."""

import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "qa_technical_archive.py"


@pytest.fixture
def receiver(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("qa_technical_archive_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PROJECT", tmp_path / "repository")
    return module


def event(**changes):
    data = {
        "schema_version": "qa-tech-v1",
        "event_id": "a" * 32,
        "event_time_original": "2026-10-21T15:30:00+02:00",
        "source_id": "qa-test-source",
        "environment": "staging",
        "service": "qa-verifier",
        "component": "backend",
        "event": "backup_selected",
        "role": "backup",
        "trigger": "T1_T2",
    }
    data.update(changes)
    return data


def private_directory(tmp_path):
    directory = tmp_path / "archive"
    directory.mkdir(mode=0o700)
    if os.name == "posix":
        directory.chmod(0o700)
    return directory


def source_file(tmp_path, data):
    path = tmp_path / f"{data['event_id']}.json"
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return path


def test_persists_original_and_minimised_view_before_receipt(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event(job_ref="private-ref"))
    receipt = receiver.receive(source, archive, "qa-test-source", "staging")
    assert receipt["status"] == "stored"
    stored = json.loads((archive / ("a" * 32 + ".json")).read_text(encoding="utf-8"))
    assert stored["original"]["job_ref"] == "private-ref"
    assert "job_ref" not in stored["technical"]["record"]
    assert stored["technical"]["labels"]["archive"] == "technical"
    assert stored["received_at"].endswith("+00:00")
    assert stored["sha256"] == receipt["sha256"]
    assert receiver.receive(source, archive, "qa-test-source", "staging")["status"] == "duplicate"
    assert len(list(archive.glob("*.json"))) == 1


def test_same_event_id_with_different_bytes_is_not_acknowledged(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    receiver.receive(source, archive, "qa-test-source", "staging")
    source.write_text(json.dumps(event(trigger="T3")) + "\n", encoding="utf-8")
    with pytest.raises(receiver.Rejected, match="event_id_collision"):
        receiver.receive(source, archive, "qa-test-source", "staging")
    stored = json.loads((archive / ("a" * 32 + ".json")).read_text(encoding="utf-8"))
    assert stored["original"]["trigger"] == "T1_T2"


def test_existing_entry_with_matching_hash_but_altered_view_is_rejected(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event(job_ref="private-ref"))
    receiver.receive(source, archive, "qa-test-source", "staging")
    destination = archive / ("a" * 32 + ".json")
    stored = json.loads(destination.read_text(encoding="utf-8"))
    stored["technical"]["record"]["job_ref"] = "private-ref"
    destination.write_text(json.dumps(stored) + "\n", encoding="utf-8")
    with pytest.raises(receiver.Rejected, match="archive_entry"):
        receiver.receive(source, archive, "qa-test-source", "staging")


def test_symlink_archive_entry_is_never_acknowledged(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    destination = archive / ("a" * 32 + ".json")
    try:
        destination.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("Creating a file symlink is not available")
    with pytest.raises(receiver.Rejected, match="archive_entry"):
        receiver.receive(source, archive, "qa-test-source", "staging")


def test_rejects_authorisation_without_publishing_a_file(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event(
        component="authorisation", event="authorisation_granted", who="private-person",
    ))
    with pytest.raises(receiver.Rejected, match="restricted_route"):
        receiver.receive(source, archive, "qa-test-source", "staging")
    assert list(archive.iterdir()) == []


def test_rejects_untrusted_archive_directory_before_writing(tmp_path, receiver):
    archive = tmp_path / "archive"
    archive.mkdir(mode=0o777)
    if os.name == "posix":
        archive.chmod(0o777)
    source = source_file(tmp_path, event())
    if os.name == "posix":
        with pytest.raises(receiver.Rejected, match="archive_permissions"):
            receiver.receive(source, archive, "qa-test-source", "staging")
    else:
        archive.rmdir()
        with pytest.raises(receiver.Rejected, match="archive_directory"):
            receiver.receive(source, archive, "qa-test-source", "staging")


def test_failed_directory_sync_gives_no_receipt_and_retry_is_duplicate(
    tmp_path, receiver, monkeypatch,
):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    sync = receiver._sync_directory

    def fail_sync(_directory):
        raise OSError("directory sync failed")

    monkeypatch.setattr(receiver, "_sync_directory", fail_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        receiver.receive(source, archive, "qa-test-source", "staging")
    assert (archive / ("a" * 32 + ".json")).exists()
    monkeypatch.setattr(receiver, "_sync_directory", sync)
    assert receiver.receive(source, archive, "qa-test-source", "staging")["status"] == "duplicate"


def test_file_name_must_match_validated_event_id(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    renamed = source.with_name("b" * 32 + ".json")
    source.rename(renamed)
    with pytest.raises(receiver.Rejected, match="source_name"):
        receiver.receive(renamed, archive, "qa-test-source", "staging")
    assert list(archive.iterdir()) == []


def test_archive_cannot_live_inside_repository(tmp_path, receiver):
    archive = tmp_path / "repository" / "private"
    archive.mkdir(parents=True, mode=0o700)
    source = source_file(tmp_path, event())
    with pytest.raises(receiver.Rejected, match="archive_inside_repository"):
        receiver.receive(source, archive, "qa-test-source", "staging")
    assert list(archive.iterdir()) == []
