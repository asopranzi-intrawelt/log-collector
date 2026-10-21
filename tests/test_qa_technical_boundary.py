"""The QA general view must never receive authorisation evidence or text."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "qa_technical_boundary.py"
SPEC = importlib.util.spec_from_file_location("qa_technical_boundary", SCRIPT)
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)


def event(**changes):
    row = {
        "schema_version": "qa-tech-v1",
        "event_id": "a" * 32,
        "event_time_original": "2026-10-21T15:30:00+02:00",
        "source_id": "qa-verifier-prod-01",
        "environment": "production",
        "service": "qa-verifier",
        "component": "backend",
        "event": "backup_selected",
        "role": "backup",
        "trigger": "T1_T2",
        "job_ref": "abc123",
    }
    row.update(changes)
    return row


def payload(*events):
    return ("\n".join(json.dumps(row) for row in events) + "\n").encode()


def check(raw):
    return BOUNDARY.check_jsonl(raw, "qa-verifier-prod-01", "production")


def test_producer_shape_keeps_only_reviewed_fields_and_static_labels():
    result = check(payload(event()))[0]
    assert result["record"]["event_at"] == "2026-10-21T13:30:00+00:00"
    assert result["record"]["trigger"] == "T1_T2"
    assert "job_ref" not in result["record"]
    assert result["labels"] == {
        "archive": "technical", "source_family": "qa",
        "environment": "production", "service": "qa-verifier",
    }


def test_authorisation_evidence_cannot_enter_general_view():
    sensitive = event(
        component="authorisation", event="authorisation_granted",
        who="<EMAIL_UTENTE>", file="client-document.xlsx",
        model="sonnet", text_version="v1-aabbccddeeff", retention_months=12,
    )
    del sensitive["role"]
    del sensitive["trigger"]
    with pytest.raises(BOUNDARY.Rejected, match="restricted_route"):
        check(payload(sensitive))


@pytest.mark.parametrize("change", [
    {"message": "token=example-secret"},
    {"who": "<EMAIL_UTENTE>"},
    {"file": "client-document.xlsx"},
    {"event": "authorisation_granted"},
    {"component": "authorisation"},
    {"role": "local"},
    {"trigger": "T6"},
    {"event_time_original": "2026-10-21T15:30:00"},
    {"event_time_original": "2026-02-30T15:30:00+02:00"},
    {"environment": "staging"},
    {"source_id": "other-source"},
    {"job_ref": "<EMAIL_UTENTE>"},
    {"job_ref": 123},
    {"event_id": "invalid"},
    {"schema_version": "qa-tech-v2"},
])
def test_refuses_unreviewed_fields_values_and_source_claims(change):
    with pytest.raises(BOUNDARY.Rejected):
        check(payload(event(**change)))


def test_duplicate_json_key_and_event_id_are_rejected():
    raw = payload(event()).replace(b'"role": "backup"', b'"role": "backup", "role": "local"')
    with pytest.raises(BOUNDARY.Rejected, match="duplicate_key"):
        check(raw)
    with pytest.raises(BOUNDARY.Rejected, match="duplicate_event_id"):
        check(payload(event(), event()))


def test_cli_validates_full_batch_before_any_stdout(tmp_path):
    first = event()
    second = event(event_id="b" * 32, message="client secret")
    path = tmp_path / "qa.jsonl"
    path.write_bytes(payload(first, second))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--jsonl", str(path),
         "--source-id", "qa-verifier-prod-01", "--environment", "production"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "rejected:record_keys"
    assert "client secret" not in result.stderr


def test_cli_emits_minimised_batch_without_job_reference(tmp_path):
    path = tmp_path / "qa.jsonl"
    path.write_bytes(payload(event()))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--jsonl", str(path),
         "--source-id", "qa-verifier-prod-01", "--environment", "production"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["record"]["event"] == "backup_selected"
    assert "abc123" not in result.stdout
