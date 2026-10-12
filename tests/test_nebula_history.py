"""Il confronto richiede eventi esatti e un riferimento non vuoto."""

import copy
import importlib.util
import json
from datetime import UTC, datetime

import pytest

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "nebula_history", ROOT / "tools/compare-nebula-history.py"
)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text(encoding="utf-8"))
ACQUIRED = datetime(2026, 10, 12, 9, tzinfo=UTC)


def write_history(path, events):
    path.write_text(
        json.dumps(
            [{"DevId": "<SWITCH_ID>", "EventLogs": {"Count": len(events), "value": events}}]
        ),
        encoding="utf-8",
    )
    return history.read_switches(path)


def test_exact_match_uses_all_seven_fields_without_disclosing_values(tmp_path):
    reference = write_history(tmp_path / "reference.json", EVENTS)
    candidate = write_history(tmp_path / "candidate.json", EVENTS)
    report = history.compare(reference, candidate, ACQUIRED)
    assert report["reference_accesses"] == 5
    assert report["exact_matches"] == 5
    assert report["all_reference_accesses_found"]
    assert report["oldest_matched_age_hours"] > 90
    serialized = json.dumps(report)
    assert all(value not in serialized for value in ("<SWITCH_ID>", "<ACCOUNT>", "<CLIENT_IP>"))


@pytest.mark.parametrize("field", ["timestamp", "message", "category", "tag", "mac", "priority"])
def test_changed_reference_event_is_not_claimed_as_retained(tmp_path, field):
    reference = write_history(tmp_path / "reference.json", EVENTS)
    changed = copy.deepcopy(EVENTS)
    changed[0][field] = changed[0][field] + 1 if field == "timestamp" else "<CHANGED>"
    candidate = write_history(tmp_path / "candidate.json", changed)
    report = history.compare(reference, candidate, ACQUIRED)
    assert report["exact_matches"] == 4
    assert report["missing_or_changed"] == 1
    assert not report["all_reference_accesses_found"]


def test_empty_reference_cannot_produce_success(tmp_path):
    reference = write_history(tmp_path / "reference.json", [])
    with pytest.raises(history.EvidenceError, match="reference_authentication_missing"):
        history.compare(reference, reference, ACQUIRED)


def test_empty_candidate_is_valid_input_but_incomplete_measure(tmp_path):
    reference = write_history(tmp_path / "reference.json", EVENTS)
    candidate = write_history(tmp_path / "candidate.json", [])
    report = history.compare(reference, candidate, ACQUIRED)
    assert report["exact_matches"] == 0
    assert not report["all_reference_accesses_found"]
    assert report["oldest_matched_age_hours"] is None


def test_missing_response_is_a_failed_acquisition(tmp_path):
    path = tmp_path / "failed.json"
    path.write_text(json.dumps([{"DevId": "<SWITCH_ID>", "EventLogs": None}]), encoding="utf-8")
    with pytest.raises(history.EvidenceError, match="events_missing"):
        history.read_switches(path)


def test_wrapper_count_must_match_received_rows(tmp_path):
    path = tmp_path / "failed.json"
    path.write_text(
        json.dumps([{"DevId": "<SWITCH_ID>", "EventLogs": {"Count": 1, "value": []}}]),
        encoding="utf-8",
    )
    with pytest.raises(history.EvidenceError, match="events_count"):
        history.read_switches(path)


def test_other_device_does_not_satisfy_reference(tmp_path):
    reference = write_history(tmp_path / "reference.json", EVENTS)
    with pytest.raises(history.EvidenceError, match="candidate_switch_missing"):
        history.compare(reference, {"<OTHER_SWITCH>": EVENTS}, ACQUIRED)


def test_cli_writes_masked_report_and_marks_missing_event_incomplete(tmp_path, capsys):
    reference = tmp_path / "reference.json"
    candidate = tmp_path / "candidate.json"
    report = tmp_path / "report.json"
    write_history(reference, EVENTS)
    write_history(candidate, EVENTS[1:])
    assert (
        history.main(
            [
                "--reference",
                str(reference),
                "--candidate",
                str(candidate),
                "--report",
                str(report),
                "--acquired-at",
                ACQUIRED.isoformat(),
            ]
        )
        == 1
    )
    assert json.loads(report.read_text(encoding="utf-8"))["missing_or_changed"] == 1
    output = capsys.readouterr().out
    assert "status=incomplete" in output
    assert "<ACCOUNT>" not in output
