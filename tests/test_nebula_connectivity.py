"""La lettura della connettività non deve diventare una prova del recupero."""

import copy
import importlib.util
import io
import json
from datetime import UTC, datetime

import pytest
import requests

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "connectivity", ROOT / "tools/check-nebula-connectivity.py"
)
connectivity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(connectivity)
ONLINE = json.loads((FIXTURES / "nebula-connectivity-online.json").read_text())
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text())
DEVICE = EVENTS[0]["devId"]
SNAPSHOT = {
    "organizations": [
        {"sites": [{"siteId": "<SITE_ID>", "devices": [{"devId": DEVICE, "type": "SW"}]}]}
    ]
}
NOW = datetime(2026, 10, 13, 13, tzinfo=UTC)


class RecordedClient:
    def __init__(self, rows=None, missing_control=False):
        self.rows = copy.deepcopy(ONLINE if rows is None else rows)
        self.missing_control = missing_control
        self.calls = []

    def fetch(self, target, left, right):
        self.calls.append(("event-logs", target, left, right))
        return [] if self.missing_control else [max(EVENTS, key=lambda row: row["timestamp"])]

    def connectivity(self, target, period):
        self.calls.append(("connectivity", target, period))
        return self.rows


def measure(tmp_path, client):
    return connectivity.measure(client, SNAPSHOT, {DEVICE: EVENTS}, tmp_path, now=lambda: NOW)


def test_real_online_fixture_only_inspects_and_preserves_raw_and_query(tmp_path):
    client = RecordedClient()
    report = measure(tmp_path, client)
    assert report["inspection_ok"] and report["requests"] == len(client.calls) == 2
    assert report["sources"][0]["online_intervals"] == 1
    assert not report["sources"][0]["offline_recovery_verified"]
    assert json.loads((tmp_path / "switch-1-connectivity.json").read_text()) == ONLINE
    assert report["observations"][1]["query"] == {"period": "30d"}
    assert "offline_recovery_unverified" in report["scope"]
    assert DEVICE not in json.dumps(report)


def test_other_status_is_private_unclassified_and_never_proves_recovery(tmp_path):
    rows = copy.deepcopy(ONLINE)
    rows[0]["status"] = "<UNCLASSIFIED_SYNTHETIC_STATUS>"
    report = measure(tmp_path, RecordedClient(rows))
    source = report["sources"][0]
    assert source["other_status_intervals"] == 1 and source["online_intervals"] == 0
    assert not source["offline_recovery_verified"]
    assert rows[0]["status"] not in json.dumps(report)


@pytest.mark.parametrize("problem", ["empty", "control"])
def test_empty_connectivity_or_missing_control_is_inconclusive(tmp_path, problem):
    client = RecordedClient([]) if problem == "empty" else RecordedClient(missing_control=True)
    report = measure(tmp_path, client)
    assert not report["inspection_ok"]


@pytest.mark.parametrize("problem", ["schema", "bool_time", "inverted", "newline"])
def test_bad_schema_keeps_payload_and_error_metadata(tmp_path, problem):
    rows = copy.deepcopy(ONLINE)
    if problem == "schema":
        rows = {"items": rows}
    elif problem == "bool_time":
        rows[0]["begin_time"] = True
    elif problem == "inverted":
        rows[0]["begin_time"] = rows[0]["end_time"] + 1
    else:
        rows[0]["status"] = "online\n"
    with pytest.raises(connectivity.windows.history.EvidenceError):
        measure(tmp_path, RecordedClient(rows))
    assert json.loads((tmp_path / "switch-1-connectivity.json").read_text()) == rows
    meta = json.loads((tmp_path / "switch-1-connectivity-meta.json").read_text())
    assert meta["rows"] is None and meta["validation_error"]
    assert meta["requested_at"] == meta["received_at"] == NOW.isoformat()


def test_two_targets_have_exactly_four_reads_and_independent_controls(tmp_path):
    second = copy.deepcopy(EVENTS)
    other = "<OTHER_SWITCH>"
    for row in second:
        row["devId"] = other
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["organizations"][0]["sites"][0]["devices"].append({"devId": other, "type": "SW"})

    class TwoTargets(RecordedClient):
        def fetch(self, target, left, right):
            self.calls.append(("event-logs", target, left, right))
            rows = EVENTS if target["device_id"] == DEVICE else second
            return [max(rows, key=lambda row: row["timestamp"])]

    client = TwoTargets()
    report = connectivity.measure(
        client, snapshot, {DEVICE: EVENTS, other: second}, tmp_path, now=lambda: NOW
    )
    assert (
        report["inspection_ok"]
        and report["requests"] == report["request_budget"] == len(client.calls) == 4
    )


@pytest.mark.parametrize("http_status", [200, 302, 429])
def test_real_requests_contract_tls_body_path_and_errors(http_status):
    seen = []

    class Adapter(requests.adapters.BaseAdapter):
        def send(self, request, **kwargs):
            seen.append(request)
            assert kwargs["verify"] is True and kwargs["timeout"] == (10, 30)
            assert request.method == "POST" and request.url.endswith(
                "/%3CSITE_ID%3E/%3CSWITCH_ID%3E/connectivity"
            )
            assert json.loads(request.body) == {"period": "30d"}
            assert request.headers["X-ZyxelNebula-API-Key"] == "FAKE_KEY"
            response = requests.Response()
            response.status_code = http_status
            response._content = json.dumps(ONLINE).encode()
            response.request = request
            response.headers["Location"] = "https://example.invalid/redirect"
            return response

        def close(self):
            pass

    client = connectivity.ConnectivityClient("FAKE_KEY")
    client.session.mount("https://", Adapter())
    assert not client.session.trust_env
    target = {"site_id": "<SITE_ID>", "device_id": "<SWITCH_ID>"}
    try:
        if http_status == 200:
            assert client.connectivity(target, "30d") == ONLINE
        else:
            with pytest.raises(connectivity.windows.poller.PollError, match=f"http_{http_status}"):
                client.connectivity(target, "30d")
        assert len(seen) == 1
    finally:
        client.close()


def test_cli_inspection_keeps_key_and_unknown_status_private(tmp_path, monkeypatch, capsys):
    clients = []

    class StdinClient(RecordedClient):
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"
            rows = copy.deepcopy(ONLINE)
            rows[0]["status"] = "<UNCLASSIFIED_SYNTHETIC_STATUS>"
            super().__init__(rows)
            self.closed = False
            clients.append(self)

        def close(self):
            self.closed = True

    cache, snapshot = tmp_path / "cache.json", tmp_path / "snapshot.json"
    cache.write_text(json.dumps([{"DevId": DEVICE, "EventLogs": EVENTS}]))
    snapshot.write_text(json.dumps(SNAPSHOT))
    monkeypatch.setattr(connectivity, "ConnectivityClient", StdinClient)
    monkeypatch.setattr(connectivity.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    assert (
        connectivity.main(
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
    assert clients[0].closed
    public = capsys.readouterr().out
    assert "status=inspected" in public and "offline_recovery=unverified" in public
    assert all(value not in public for value in ("FAKE_STDIN_KEY", DEVICE, "<UNCLASSIFIED"))
    report = json.loads((output / "inspection.json").read_text())
    assert report["sources"][0]["other_status_intervals"] == 1


def test_bad_cache_stops_cli_before_client_and_output(tmp_path, monkeypatch):
    cache, snapshot = tmp_path / "cache.json", tmp_path / "snapshot.json"
    cache.write_text(json.dumps([{"DevId": DEVICE, "EventLogs": []}]))
    snapshot.write_text(json.dumps(SNAPSHOT))

    def no_client(key):
        raise AssertionError("API prima della verifica del riferimento")

    monkeypatch.setattr(connectivity, "ConnectivityClient", no_client)
    output = tmp_path / "output"
    assert (
        connectivity.main(
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
