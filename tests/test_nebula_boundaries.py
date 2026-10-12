"""Verifica il record esatto agli estremi e distingue un controllo vuoto."""

import copy
import importlib.util
import json

import pytest

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "nebula_boundaries", ROOT / "tools/check-nebula-boundaries.py"
)
boundaries = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundaries)
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text(encoding="utf-8"))
DEVICE = "<SWITCH_ID>"
TARGET = {"site_id": "<SITE_ID>", "device_id": DEVICE}
_, REFERENCE = boundaries.select_reference({DEVICE: EVENTS})


class Client:
    def __init__(self, events=None):
        self.events = [REFERENCE] if events is None else events
        self.calls = []

    def fetch(self, target, left, right):
        self.calls.append((left, right))
        return [e for e in self.events if left <= e["timestamp"] <= right]


def test_reference_is_earliest_known_authentication_and_required():
    device, reference = boundaries.select_reference({DEVICE: EVENTS[::-1]})
    assert device == DEVICE
    assert reference["timestamp"] == min(e["timestamp"] for e in EVENTS if e["category"] == "AAA")
    with pytest.raises(
        boundaries.windows.history.EvidenceError, match="reference_authentication_missing"
    ):
        boundaries.select_reference({DEVICE: []})


def test_three_intervals_measure_exact_record_on_both_ends(tmp_path):
    client = Client()
    report = boundaries.measure(client, TARGET, REFERENCE, tmp_path)
    point = REFERENCE["timestamp"]
    assert client.calls == [(point - 1000, point + 1000), (point - 1, point), (point, point + 1)]
    assert report["requests"] == 3
    assert report["reference_present_in_control"]
    assert report["included_at_start"] and report["included_at_end"] and report["ok"]
    assert len(list(tmp_path.glob("*.json"))) == 3
    assert all(value not in json.dumps(report) for value in (DEVICE, "<ACCOUNT>", "<CLIENT_IP>"))


@pytest.mark.parametrize("excluded", ["start", "end"])
def test_exclusive_endpoint_is_detected(tmp_path, excluded):
    class Exclusive(Client):
        def fetch(self, target, left, right):
            rows = super().fetch(target, left, right)
            return [e for e in rows if e["timestamp"] != (left if excluded == "start" else right)]

    report = boundaries.measure(Exclusive(), TARGET, REFERENCE, tmp_path)
    assert report["reference_present_in_control"]
    assert report[f"included_at_{excluded}"] is False
    assert report[f"included_at_{'end' if excluded == 'start' else 'start'}"] is True
    assert not report["ok"]


def test_missing_control_is_inconclusive_even_if_edge_responses_have_record(tmp_path):
    class MissingControl(Client):
        def fetch(self, target, left, right):
            rows = super().fetch(target, left, right)
            return [] if right - left == 2000 else rows

    report = boundaries.measure(MissingControl(), TARGET, REFERENCE, tmp_path)
    assert not report["reference_present_in_control"] and not report["ok"]
    assert report["included_at_start"] is report["included_at_end"] is None


def test_same_timestamp_with_changed_message_cannot_replace_reference(tmp_path):
    changed = copy.deepcopy(REFERENCE)
    changed["message"] += " diverso"
    report = boundaries.measure(Client([changed]), TARGET, REFERENCE, tmp_path)
    assert not report["reference_present_in_control"] and not report["ok"]


def test_http_failure_does_not_invent_boundary_result(tmp_path):
    class Failure(Client):
        def fetch(self, target, left, right):
            if self.calls:
                raise boundaries.windows.poller.PollError("http_403")
            return super().fetch(target, left, right)

    with pytest.raises(boundaries.windows.poller.PollError, match="http_403"):
        boundaries.measure(Failure(), TARGET, REFERENCE, tmp_path)
    assert (tmp_path / "control.json").exists()
    assert not (tmp_path / "at_end.json").exists()
