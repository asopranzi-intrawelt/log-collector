"""The offline receiver must persist one validated QA event before acknowledging it."""

import importlib.util
import json
import os
import subprocess
import sys
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


def receive(receiver, source, archive):
    return receiver.receive(
        source, archive, "qa-test-source", "staging", max_archive_bytes=4096,
    )


def test_persists_original_and_minimised_view_before_receipt(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event(job_ref="private-ref"))
    receipt = receive(receiver, source, archive)
    assert receipt["status"] == "stored"
    stored = json.loads((archive / ("a" * 32 + ".json")).read_text(encoding="utf-8"))
    assert stored["original"]["job_ref"] == "private-ref"
    assert "job_ref" not in stored["technical"]["record"]
    assert stored["technical"]["labels"]["archive"] == "technical"
    assert stored["received_at"].endswith("+00:00")
    assert stored["sha256"] == receipt["sha256"]
    assert receive(receiver, source, archive)["status"] == "duplicate"
    assert len(list(archive.glob("*.json"))) == 1


def test_same_event_id_with_different_bytes_is_not_acknowledged(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    receive(receiver, source, archive)
    source.write_text(json.dumps(event(trigger="T3")) + "\n", encoding="utf-8")
    with pytest.raises(receiver.Rejected, match="event_id_collision"):
        receive(receiver, source, archive)
    stored = json.loads((archive / ("a" * 32 + ".json")).read_text(encoding="utf-8"))
    assert stored["original"]["trigger"] == "T1_T2"


def test_existing_entry_with_matching_hash_but_altered_view_is_rejected(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event(job_ref="private-ref"))
    receive(receiver, source, archive)
    destination = archive / ("a" * 32 + ".json")
    stored = json.loads(destination.read_text(encoding="utf-8"))
    stored["technical"]["record"]["job_ref"] = "private-ref"
    destination.write_text(json.dumps(stored) + "\n", encoding="utf-8")
    with pytest.raises(receiver.Rejected, match="archive_entry"):
        receive(receiver, source, archive)


def test_symlink_archive_entry_is_never_acknowledged(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    destination = archive / ("a" * 32 + ".json")
    try:
        destination.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("Creating a file symlink is not available")
    with pytest.raises(receiver.Rejected, match="archive_entry"):
        receive(receiver, source, archive)


def test_rejects_authorisation_without_publishing_a_file(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event(
        component="authorisation", event="authorisation_granted", who="private-person",
    ))
    with pytest.raises(receiver.Rejected, match="restricted_route"):
        receive(receiver, source, archive)
    assert list(archive.iterdir()) == []


def test_rejects_untrusted_archive_directory_before_writing(tmp_path, receiver):
    archive = tmp_path / "archive"
    archive.mkdir(mode=0o777)
    if os.name == "posix":
        archive.chmod(0o777)
    source = source_file(tmp_path, event())
    if os.name == "posix":
        with pytest.raises(receiver.Rejected, match="archive_permissions"):
            receive(receiver, source, archive)
    else:
        archive.rmdir()
        with pytest.raises(receiver.Rejected, match="archive_directory"):
            receive(receiver, source, archive)


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
        receive(receiver, source, archive)
    assert (archive / ("a" * 32 + ".json")).exists()
    monkeypatch.setattr(receiver, "_sync_directory", sync)
    assert receive(receiver, source, archive)["status"] == "duplicate"


def test_failed_pending_cleanup_sync_gives_no_receipt_and_retry_is_duplicate(
    tmp_path, receiver, monkeypatch,
):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    sync = receiver._sync_directory
    calls = 0

    def fail_second_sync(directory):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("cleanup sync failed")
        sync(directory)

    monkeypatch.setattr(receiver, "_sync_directory", fail_second_sync)
    with pytest.raises(OSError, match="cleanup sync failed"):
        receive(receiver, source, archive)
    assert (archive / ("a" * 32 + ".json")).exists()
    monkeypatch.setattr(receiver, "_sync_directory", sync)
    assert receive(receiver, source, archive)["status"] == "duplicate"


def test_file_name_must_match_validated_event_id(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    renamed = source.with_name("b" * 32 + ".json")
    source.rename(renamed)
    with pytest.raises(receiver.Rejected, match="source_name"):
        receive(receiver, renamed, archive)
    assert list(archive.iterdir()) == []


def test_archive_cannot_live_inside_repository(tmp_path, receiver):
    archive = tmp_path / "repository" / "private"
    archive.mkdir(parents=True, mode=0o700)
    source = source_file(tmp_path, event())
    with pytest.raises(receiver.Rejected, match="archive_inside_repository"):
        receive(receiver, source, archive)
    assert list(archive.iterdir()) == []


def test_archive_budget_blocks_new_event_but_allows_exact_retry(tmp_path, receiver):
    archive = private_directory(tmp_path)
    first = source_file(tmp_path, event())
    receiver.receive(first, archive, "qa-test-source", "staging", max_archive_bytes=4096)
    first_size = (archive / first.name).stat().st_size
    second = source_file(tmp_path, event(event_id="b" * 32))
    with pytest.raises(receiver.Rejected, match="archive_capacity"):
        receiver.receive(second, archive, "qa-test-source", "staging", max_archive_bytes=first_size)
    assert not (archive / second.name).exists()
    assert receiver.receive(
        first, archive, "qa-test-source", "staging", max_archive_bytes=first_size,
    )["status"] == "duplicate"


def test_archive_budget_rejects_first_event_without_pending_file(tmp_path, receiver):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    with pytest.raises(receiver.Rejected, match="archive_capacity"):
        receiver.receive(source, archive, "qa-test-source", "staging", max_archive_bytes=1)
    assert list(archive.iterdir()) == []


def test_unexpected_archive_entry_blocks_receipt(tmp_path, receiver):
    archive = private_directory(tmp_path)
    (archive / "unexpected.txt").write_text("unclassified", encoding="utf-8")
    source = source_file(tmp_path, event())
    with pytest.raises(receiver.Rejected, match="archive_entry"):
        receiver.receive(source, archive, "qa-test-source", "staging", max_archive_bytes=4096)
    assert not (archive / source.name).exists()


@pytest.mark.skipif(os.name == "posix", reason="Windows-only CLI safety gate")
def test_cli_rejects_windows_before_archive_write(tmp_path):
    archive = private_directory(tmp_path)
    source = source_file(tmp_path, event())
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--event-file", str(source),
         "--archive-dir", str(archive), "--source-id", "qa-test-source",
         "--environment", "staging", "--max-archive-bytes", "4096"],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.strip() == "rejected:posix_required"
    assert list(archive.iterdir()) == []
