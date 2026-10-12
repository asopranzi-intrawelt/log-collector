"""Coerenza delle finestre su fixture registrata, inclusi confini e tecnici."""

import copy
import importlib.util
import io
import json

import pytest

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "nebula_windows", ROOT / "tools/check-nebula-windows.py"
)
windows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(windows)
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text(encoding="utf-8"))
DEVICE = "<SWITCH_ID>"
BASELINE = {DEVICE: EVENTS}
START, END = windows.known_window(BASELINE)
TARGETS = [(DEVICE, {"site_id": "<SITE_ID>", "device_id": DEVICE})]


class Client:
    def __init__(self, events=None):
        self.events = EVENTS if events is None else events
        self.calls = []

    def fetch(self, config, left, right):
        self.calls.append((left, right))
        return [e for e in self.events if left <= e["timestamp"] <= right]


def test_window_is_fixed_around_known_authentication():
    assert END - START == 20 * 60 * 1000
    assert START % windows.CHUNK_MS == END % windows.CHUNK_MS == 0
    with pytest.raises(windows.history.EvidenceError, match="reference_authentication_missing"):
        windows.known_window({DEVICE: []})


def test_complete_measure_saves_real_response_shape_without_printing_identifiers(tmp_path):
    client = Client()
    report = windows.measure(client, TARGETS, BASELINE, BASELINE, START, END, tmp_path)
    assert report["ok"]
    assert report["requests"] == 5
    assert len(client.calls) == 5
    assert report["sources"][0]["wide_unique"] == 5
    assert report["sources"][0]["split_unique"] == 5
    assert report["sources"][0]["known_accesses"] == 5
    assert all(v not in json.dumps(report) for v in (DEVICE, "<ACCOUNT>", "<CLIENT_IP>"))
    assert isinstance(json.loads((tmp_path / "switch-1-wide.json").read_text()), list)


def test_boundary_record_is_deduplicated_in_split_windows(tmp_path):
    boundary = copy.deepcopy(EVENTS[-1])
    boundary["timestamp"] = START + windows.CHUNK_MS
    events = EVENTS + [boundary]
    report = windows.measure(
        Client(events), TARGETS, BASELINE, {DEVICE: events}, START, END, tmp_path
    )
    source = report["sources"][0]
    assert source["ok"]
    assert source["wide_unique"] == 6
    assert source["split_unique"] == 6
    assert source["split_duplicates"] == 1


def test_missing_technical_event_in_wide_response_is_detected(tmp_path):
    technical = copy.deepcopy(EVENTS[-1])
    technical["timestamp"] = START + 1
    events = EVENTS + [technical]

    class Truncated(Client):
        def fetch(self, config, left, right):
            rows = super().fetch(config, left, right)
            return [e for e in rows if e != technical] if (left, right) == (START, END) else rows

    report = windows.measure(
        Truncated(events), TARGETS, BASELINE, {DEVICE: events}, START, END, tmp_path
    )
    assert not report["ok"]
    source = report["sources"][0]
    assert source["cached_missing_from_wide"] == 1
    assert source["split_missing_from_wide"] == 1
    assert source["missing_known_accesses"] == 0


def test_missing_known_event_in_all_new_responses_is_detected(tmp_path):
    report = windows.measure(Client(EVENTS[1:]), TARGETS, BASELINE, BASELINE, START, END, tmp_path)
    assert not report["ok"]
    assert report["sources"][0]["missing_known_accesses"] == 2


def test_empty_current_and_cached_cannot_hide_missing_known_accesses(tmp_path):
    report = windows.measure(Client([]), TARGETS, BASELINE, {DEVICE: []}, START, END, tmp_path)
    assert not report["ok"]
    assert report["sources"][0]["response_sets_equal"]
    assert report["sources"][0]["missing_known_accesses"] == 10


def test_no_previous_broad_response_fails_before_http(tmp_path):
    client = Client()
    with pytest.raises(windows.history.EvidenceError, match="broad_device_missing"):
        windows.measure(client, TARGETS, BASELINE, {}, START, END, tmp_path)
    assert not client.calls


def test_http_failure_preserves_only_received_private_responses(tmp_path):
    class Failure(Client):
        def fetch(self, config, left, right):
            if self.calls:
                raise windows.poller.PollError("http_403")
            return super().fetch(config, left, right)

    with pytest.raises(windows.poller.PollError, match="http_403"):
        windows.measure(Failure(), TARGETS, BASELINE, BASELINE, START, END, tmp_path)
    assert (tmp_path / "switch-1-wide.json").exists()
    assert not (tmp_path / "switch-1-segment-1.json").exists()


def test_site_mapping_requires_same_device_and_rejects_ambiguity():
    site = {"siteId": "<SITE_ID>", "devices": [{"devId": DEVICE, "type": "SW"}]}
    snapshot = {"organizations": [{"sites": [site]}]}
    assert windows.resolve_targets(snapshot, BASELINE) == TARGETS
    with pytest.raises(windows.history.EvidenceError, match="snapshot_device_missing"):
        windows.resolve_targets(snapshot, {"<OTHER_SWITCH>": []})
    snapshot["organizations"][0]["sites"].append(site)
    with pytest.raises(windows.history.EvidenceError, match="snapshot_device_ambiguous"):
        windows.resolve_targets(snapshot, BASELINE)


def test_cli_reads_key_from_stdin_and_only_emits_masked_result(tmp_path, monkeypatch, capsys):
    baseline = tmp_path / "baseline.json"
    broad = tmp_path / "broad.json"
    snapshot = tmp_path / "snapshot.json"
    rows = [{"DevId": DEVICE, "EventLogs": EVENTS}]
    baseline.write_text(json.dumps(rows), encoding="utf-8")
    broad.write_text(json.dumps(rows), encoding="utf-8")
    snapshot.write_text(
        json.dumps(
            {
                "organizations": [
                    {
                        "sites": [
                            {"siteId": "<SITE_ID>", "devices": [{"devId": DEVICE, "type": "SW"}]}
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    clients = []

    class StdinClient(Client):
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"
            super().__init__()
            self.closed = False
            clients.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(windows.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    monkeypatch.setattr(windows.poller, "NebulaClient", StdinClient)
    output = tmp_path / "private-output"
    assert (
        windows.main(
            [
                "--key-stdin",
                "--baseline",
                str(baseline),
                "--broad",
                str(broad),
                "--snapshot",
                str(snapshot),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    assert report["ok"] and report["requests"] == 5
    assert clients[0].closed
    public_output = capsys.readouterr().out
    assert "status=ok" in public_output
    assert all(v not in public_output for v in ("FAKE_STDIN_KEY", DEVICE, "<ACCOUNT>"))
