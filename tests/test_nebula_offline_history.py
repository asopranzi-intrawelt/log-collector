"""Lettura storica confrontata con record locali indipendenti dall'API."""

import copy
import importlib.util
import io
import json
from datetime import UTC, datetime

import pytest

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "offline", ROOT / "tools/check-nebula-offline-history.py"
)
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text())
DEVICE = EVENTS[0]["devId"]
BASE = 1791280090000
SNAPSHOT = {
    "organizations": [
        {
            "sites": [
                {
                    "siteId": "<SITE_ID>",
                    "devices": [{"devId": DEVICE, "type": "SW", "model": "XGS2220-30HP"}],
                }
            ]
        }
    ]
}
NOW = datetime(2026, 10, 13, tzinfo=UTC)


def sample():
    records, intervals = [], []
    for index in range(2):
        left = BASE + index * 3_600_000
        intervals.append({"begin_ms": left, "end_ms": left + 60_000})
        record = copy.deepcopy(EVENTS[-1])
        record.update(timestamp=left + 1000, message=f"<LOCAL_TECHNICAL_MESSAGE_{index}>")
        records.append(record)
    reference = {
        "source_model": "XGS2220-30HP",
        "intervals": intervals,
        "references": [{field: row[field] for field in offline.LOCAL_FIELDS} for row in records],
    }
    return reference, records


class Client:
    def __init__(self, records, missing_control=False):
        self.records, self.calls, self.missing_control = records, [], missing_control

    def fetch(self, target, left, right):
        self.calls.append((left, right))
        if len(self.calls) == 1:
            return [] if self.missing_control else [max(EVENTS, key=lambda row: row["timestamp"])]
        return [row for row in self.records if left <= row["timestamp"] <= right]


def measure(tmp_path, reference=None, client=None):
    normal, records = sample()
    return offline.measure(
        client or Client(records),
        SNAPSHOT,
        {DEVICE: EVENTS},
        reference or normal,
        tmp_path,
        lambda: NOW,
    )


def test_independent_local_records_match_without_proving_ads_continuity(tmp_path):
    reference, records = sample()
    client = Client(records)
    report = measure(tmp_path, reference, client)
    assert report["ok"] and report["matched_local_unique"] == 2
    assert report["requests"] == report["request_budget"] == len(client.calls) == 3
    assert report["windows"][0]["known_authentication_rows"] == 0
    assert "ads_continuity_unverified" in report["scope"]
    assert DEVICE not in json.dumps(report)


@pytest.mark.parametrize("field", ["timestamp", "priority", "tag", "message"])
def test_each_changed_projection_field_prevents_a_match(tmp_path, field):
    reference, records = sample()
    if field == "timestamp":
        records[0][field] += 1
    else:
        records[0][field] = "<CHANGED>"
    report = measure(tmp_path, reference, Client(records))
    assert not report["ok"] and report["missing_local_unique"] == 1
    assert report["status"] == "reference_not_fully_available_now"


def test_empty_historical_response_does_not_identify_retention_or_loss(tmp_path):
    report = measure(tmp_path, client=Client([]))
    assert not report["ok"] and report["missing_local_unique"] == 2
    assert report["control_present"]


def test_matching_windows_with_missing_control_remain_inconclusive(tmp_path):
    reference, records = sample()
    report = measure(tmp_path, reference, Client(records, missing_control=True))
    assert report["matched_local_unique"] == 2 and not report["ok"]
    assert report["status"] == "control_missing"


def test_duplicate_local_lines_do_not_double_expected_cloud_records(tmp_path):
    reference, records = sample()
    reference["references"].append(copy.deepcopy(reference["references"][0]))
    report = measure(tmp_path, reference, Client(records))
    assert report["ok"] and report["matched_local_unique"] == 2
    assert report["windows"][0]["local_rows"] == 2 and report["windows"][0]["local_duplicates"] == 1


@pytest.mark.parametrize("problem", ["outside", "too_many", "empty"])
def test_invalid_reference_stops_before_any_fetch(tmp_path, problem):
    reference, records = sample()
    if problem == "outside":
        reference["references"][0]["timestamp"] = 0
    elif problem == "too_many":
        reference["intervals"].append({"begin_ms": BASE + 10_000_000, "end_ms": BASE + 10_001_000})
    else:
        reference["references"] = []
    client = Client(records)
    with pytest.raises(offline.windows.history.EvidenceError):
        measure(tmp_path, reference, client)
    assert client.calls == []


def test_equal_known_records_at_response_guard_remain_inconclusive(tmp_path):
    reference, records = sample()
    client = Client([records[0]] * 1000 + [records[1]])
    report = measure(tmp_path, reference, client)
    assert report["matched_local_unique"] == 2 and not report["ok"]
    assert report["status"] == "response_threshold_reached"


def test_cli_keeps_reference_messages_and_key_private(tmp_path, monkeypatch, capsys):
    reference, records = sample()
    clients = []

    class StdinClient(Client):
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"
            super().__init__(records)
            self.closed = False
            clients.append(self)

        def close(self):
            self.closed = True

    paths = {name: tmp_path / f"{name}.json" for name in ("reference", "cache", "snapshot")}
    paths["reference"].write_text(json.dumps(reference))
    paths["cache"].write_text(json.dumps([{"DevId": DEVICE, "EventLogs": EVENTS}]))
    paths["snapshot"].write_text(json.dumps(SNAPSHOT))
    monkeypatch.setattr(offline.windows.poller, "NebulaClient", StdinClient)
    monkeypatch.setattr(offline.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    argv = ["--key-stdin", "--output", str(output)]
    for name, path in paths.items():
        argv.extend(["--" + name, str(path)])
    assert offline.main(argv) == 0 and clients[0].closed
    public = capsys.readouterr().out
    assert "status=matched_local_reference" in public and "ads_continuity=unverified" in public
    assert all(value not in public for value in ("FAKE_STDIN_KEY", DEVICE, "<LOCAL_TECHNICAL"))
    assert json.loads((output / "comparison.json").read_text())["matched_local_unique"] == 2
