"""Il confronto deve rilevare perdite anche sotto la soglia del poller."""

import copy
import importlib.util
import io
import json
from datetime import UTC, datetime

import pytest

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "nebula_volume", ROOT / "tools/check-nebula-volume.py"
)
volume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(volume)
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text())
DEVICE = "<SWITCH_ID>"
START = min(event["timestamp"] for event in EVENTS) // volume.DAY_MS * volume.DAY_MS - volume.DAY_MS
END = START + 6 * volume.DAY_MS
NOW = datetime.fromtimestamp((END + volume.DAY_MS) / 1000, UTC)
SNAPSHOT = {
    "organizations": [
        {"sites": [{"siteId": "<SITE_ID>", "devices": [{"type": "SW", "devId": DEVICE}]}]}
    ]
}


def many_events(count=600):
    events = []
    for index in range(count):
        event = copy.deepcopy(EVENTS[-1])
        event.update(
            timestamp=START + (index + 1) * (END - START) // (count + 1),
            message=f"<TECHNICAL_MESSAGE_{index}>",
        )
        events.append(event)
    return events


class Client:
    def __init__(self, events, cap=None):
        self.events, self.cap, self.calls = events, cap, []

    def fetch(self, target, left, right):
        self.calls.append((left, right))
        found = [event for event in self.events if left <= event["timestamp"] <= right]
        return found[: self.cap] if self.cap is not None else found


def measure(tmp_path, events=None, client=None):
    events = many_events() if events is None else events
    client = client or Client(events)
    return volume.measure(client, SNAPSHOT, {DEVICE: events}, tmp_path, lambda: NOW), client


def test_plan_uses_same_six_days_with_a_control_and_two_wide_queries():
    targets, start, end, intervals, budget = volume.make_plan(
        SNAPSHOT, {DEVICE: many_events()}, NOW
    )
    assert len(targets) == 1 and (start, end) == (START, END)
    assert len(intervals) == 6 and budget == 9
    assert intervals[0] == (START, START + volume.DAY_MS) and intervals[-1][1] == END


def test_complete_measure_checks_600_events_and_preserves_raw_responses(tmp_path):
    report, client = measure(tmp_path)
    source = report["sources"][0]
    assert report["ok"] and source["status"] == "consistent"
    assert report["requests"] == len(client.calls) == 9
    assert (
        source["wide_before_unique"] == source["wide_after_unique"] == source["split_unique"] == 600
    )
    assert source["largest_response_rows"] == 600 and not source["response_threshold_reached"]
    assert client.calls[1] == client.calls[-1] == (START, END)
    assert len(json.loads((tmp_path / "switch-1-wide-before.json").read_text())) == 600
    assert all(
        value not in json.dumps(report) for value in (DEVICE, "<SITE_ID>", "<TECHNICAL_MESSAGE")
    )
    assert "maximum_limit_and_physical_completeness_unverified" in report["scope"]


def test_response_cap_at_500_is_detected_below_the_1000_guard(tmp_path):
    events = many_events()
    report, _ = measure(tmp_path, events, Client(events, cap=500))
    source = report["sources"][0]
    assert not report["ok"] and source["status"] == "coverage_mismatch"
    assert source["control_present"] and source["wide_responses_stable"]
    assert source["split_missing_from_wide"] == 100 and source["split_unique"] == 600
    assert not source["response_threshold_reached"]


def test_missing_technical_record_is_detected_even_if_authentication_is_complete(tmp_path):
    events = many_events(10) + copy.deepcopy(EVENTS)
    technical = events[0]

    class MissingTechnical(Client):
        def fetch(self, target, left, right):
            found = super().fetch(target, left, right)
            return (
                [event for event in found if event != technical]
                if (left, right) == (START, END)
                else found
            )

    report, _ = measure(tmp_path, events, MissingTechnical(events))
    source = report["sources"][0]
    assert source["status"] == "coverage_mismatch" and source["split_missing_from_wide"] == 1


def test_wide_query_changing_during_acquisition_is_not_reported_as_truncation(tmp_path):
    events = many_events()

    class Changing(Client):
        def fetch(self, target, left, right):
            found = super().fetch(target, left, right)
            return found[1:] if len(self.calls) == 2 else found

    report, _ = measure(tmp_path, events, Changing(events))
    assert not report["ok"] and report["sources"][0]["status"] == "wide_responses_changed"


def test_old_records_missing_from_every_current_query_are_not_assumed_truncated(tmp_path):
    events = many_events()
    report, _ = measure(tmp_path, events, Client(events[1:]))
    source = report["sources"][0]
    assert source["wide_and_split_sets_equal"] and source["control_present"]
    assert source["cached_missing_from_split"] == 1 and not source["ok"]
    assert source["status"] == "historical_records_unavailable"


def test_empty_responses_cannot_prove_consistency(tmp_path):
    report, _ = measure(tmp_path, client=Client([]))
    assert not report["ok"] and report["sources"][0]["status"] == "control_missing"


def test_duplicate_on_shared_boundary_is_counted_once(tmp_path):
    events = many_events(20)
    for event in events:
        event["timestamp"] += 1
    boundary = copy.deepcopy(events[0])
    boundary["timestamp"] = START + volume.DAY_MS
    events.append(boundary)
    report, _ = measure(tmp_path, events)
    source = report["sources"][0]
    assert source["ok"] and source["split_duplicates"] == 1 and source["split_unique"] == 21


def test_equal_responses_at_guard_threshold_do_not_prove_completeness(tmp_path):
    report, _ = measure(tmp_path, many_events(volume.RESPONSE_GUARD))
    source = report["sources"][0]
    assert source["wide_and_split_sets_equal"] and source["response_threshold_reached"]
    assert not source["ok"] and source["status"] == "response_threshold_reached"


@pytest.mark.parametrize("problem", ["empty", "large", "recent"])
def test_bad_plan_is_rejected_before_any_api_client(tmp_path, monkeypatch, problem):
    events = many_events()
    if problem == "empty":
        events = []
    elif problem == "large":
        events[-1]["timestamp"] = START + 8 * volume.DAY_MS
    else:
        events = [copy.deepcopy(EVENTS[0])]
        events[0]["timestamp"] = int(datetime.now(UTC).timestamp() * 1000)
    cache, snapshot = tmp_path / "cache.json", tmp_path / "snapshot.json"
    cache.write_text(json.dumps([{"DevId": DEVICE, "EventLogs": events}]))
    snapshot.write_text(json.dumps(SNAPSHOT))

    def no_client(key):
        raise AssertionError("Client creato prima di validare il piano")

    monkeypatch.setattr(volume.windows.poller, "NebulaClient", no_client)
    monkeypatch.setattr(volume.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    assert (
        volume.main(
            [
                "--key-stdin",
                "--cache",
                str(cache),
                "--snapshot",
                str(snapshot),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert not output.exists()


def test_two_switches_have_18_requests_and_distinct_control_records(tmp_path):
    first = many_events(20)
    second = copy.deepcopy(first)
    other = "<OTHER_SWITCH>"
    for event in second:
        event["devId"] = other
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["organizations"][0]["sites"][0]["devices"].append({"type": "SW", "devId": other})

    class TwoSwitchClient(Client):
        def fetch(self, target, left, right):
            self.calls.append((target["device_id"], left, right))
            source = first if target["device_id"] == DEVICE else second
            return [event for event in source if left <= event["timestamp"] <= right]

    client = TwoSwitchClient(first)
    report = volume.measure(client, snapshot, {DEVICE: first, other: second}, tmp_path, lambda: NOW)
    assert (
        report["ok"] and report["requests"] == report["request_budget"] == len(client.calls) == 18
    )
    assert all(source["control_present"] for source in report["sources"])


def test_http_error_keeps_only_payloads_received_before_failure(tmp_path):
    class Failing(Client):
        def fetch(self, target, left, right):
            if self.calls:
                raise volume.windows.poller.PollError("http_429")
            return super().fetch(target, left, right)

    with pytest.raises(volume.windows.poller.PollError, match="http_429"):
        measure(tmp_path, client=Failing(many_events()))
    assert (tmp_path / "switch-1-control.json").exists()
    assert not (tmp_path / "switch-1-wide-before.json").exists()


def test_cli_keeps_key_and_identifiers_private_and_closes_client(tmp_path, monkeypatch, capsys):
    events = many_events()
    cache, snapshot = tmp_path / "cache.json", tmp_path / "snapshot.json"
    cache.write_text(json.dumps([{"DevId": DEVICE, "EventLogs": events}]))
    snapshot.write_text(json.dumps(SNAPSHOT))
    clients = []

    class StdinClient(Client):
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"
            super().__init__(events)
            self.closed = False
            clients.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(volume.windows.poller, "NebulaClient", StdinClient)
    monkeypatch.setattr(volume.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    assert (
        volume.main(
            [
                "--key-stdin",
                "--cache",
                str(cache),
                "--snapshot",
                str(snapshot),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert clients[0].closed and json.loads((output / "comparison.json").read_text())["ok"]
    public = capsys.readouterr().out
    assert "status=consistent" in public
    assert all(value not in public for value in ("FAKE_STDIN_KEY", DEVICE, "<SITE_ID>"))
