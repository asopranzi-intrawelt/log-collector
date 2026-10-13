"""Prove del poller su risposta registrata e guasti prima del checkpoint."""

import copy
import json
import os
import sqlite3
from datetime import UTC, datetime

import pytest
import requests
from requests.adapters import BaseAdapter

from conftest import FIXTURES, load_script

nebula = load_script("ads-nebula.py")
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text(encoding="utf-8"))
INITIAL = min(e["timestamp"] for e in EVENTS) - 1
END = max(e["timestamp"] for e in EVENTS) + 1
NOW = END + 60_000
RECEIVED = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "site_id": "<SITE_ID>",
                "device_id": "<SWITCH_ID>",
                "source": "nebula-test",
                "system": "switch-test",
                "initial_start_ms": INITIAL,
                "recovery_horizon_ms": 86_400_000,
                "chunk_ms": 3_600_000,
            }
        ),
        encoding="utf-8",
    )
    return nebula.load_config(path)


class RecordedClient:
    def __init__(self, events=None):
        self.events = copy.deepcopy(EVENTS if events is None else events)
        self.calls = []

    def fetch(self, config, start, end):
        self.calls.append((start, end))
        return [e for e in self.events if start <= e["timestamp"] <= end]


def run(tmp_path, config, client=None, now=NOW):
    return nebula.poll(
        client or RecordedClient(),
        config,
        tmp_path / "state",
        tmp_path / "logs",
        now,
        clock=lambda: RECEIVED,
    )


def rows(tmp_path, table):
    with sqlite3.connect(tmp_path / "state/state.sqlite") as connection:
        return connection.execute(f"SELECT * FROM {table}").fetchall()


def lines(tmp_path):
    return (tmp_path / "logs/2026-10-09.log").read_text(encoding="utf-8").splitlines()


def test_recorded_events_arrive_as_ads_lines_and_second_run_is_identical(tmp_path, config):
    assert run(tmp_path, config) == 5
    first = lines(tmp_path)
    assert len(first) == 5
    assert [line.split("outcome=")[1].split()[0] for line in first] == [
        "failure",
        "failure",
        "failure",
        "login",
        "logout",
    ]
    for line in first:
        received, source, declared, system, message = line.split(" ", 4)
        assert datetime.fromisoformat(received) == RECEIVED
        assert source == "nebula-test"
        assert system == "switch-test"
        assert datetime.fromisoformat(declared).utcoffset().total_seconds() == 0
        assert "<ACCOUNT>" in message and "<CLIENT_IP>" in message
        assert "<TECHNICAL_MESSAGE>" not in message
    assert rows(tmp_path, "meta")[0][2] == END
    assert run(tmp_path, config) == 0
    assert lines(tmp_path) == first


def test_recorded_manual_logout_arrives_as_ads_line_without_duplicate(tmp_path, config):
    logout = json.loads((FIXTURES / "nebula-switch-manual-logout.json").read_text())
    config["initial_start_ms"] = logout["timestamp"] - 1
    received = datetime(2026, 10, 13, 9, 47, 48, tzinfo=UTC)
    client = RecordedClient([logout])
    args = (client, config, tmp_path / "state", tmp_path / "logs", logout["timestamp"] + 60_001)
    assert nebula.poll(*args, clock=lambda: received) == 1
    path = tmp_path / "logs/2026-10-13.log"
    original = path.read_bytes()
    record = original.decode().strip()
    stamp, source, declared, system, message = record.split(" ", 4)
    assert datetime.fromisoformat(stamp) == received
    assert source == "nebula-test" and system == "switch-test"
    assert declared == "2026-10-13T09:46:19.000+00:00"
    assert message == (
        "nebula-auth outcome=logout "
        "event_id=fee8618984b4b1fa4db4e8e2d9d424e7810c6f2d88585cf00c794105f0f59c36 "
        "HTTP(s) user <ACCOUNT> logout [IP address = <CLIENT_IP>]"
    )
    assert nebula.poll(*args, clock=lambda: received) == 0
    assert path.read_bytes() == original and len(rows(tmp_path, "seen")) == 1


@pytest.mark.parametrize("suffix", [" extra", " due to unknown reason", "\n"])
def test_manual_logout_pattern_does_not_accept_other_formats(suffix):
    logout = json.loads((FIXTURES / "nebula-switch-manual-logout.json").read_text())
    if suffix.startswith(" due"):
        logout["message"] = logout["message"].replace("logout [", "logout" + suffix + " [")
    else:
        logout["message"] += suffix
    with pytest.raises(nebula.PollError, match="authentication_unknown"):
        nebula.outcome(logout)


def test_overlap_collects_late_event_without_duplicating_previous_rows(tmp_path, config):
    run(tmp_path, config)
    late = copy.deepcopy(EVENTS[3])
    late["message"] = late["message"].replace("<ACCOUNT>", "<OTHER_ACCOUNT>")
    late["timestamp"] = END - 1000
    assert run(tmp_path, config, RecordedClient(EVENTS + [late]), now=NOW + 1000) == 1
    assert len(lines(tmp_path)) == 6
    assert "<OTHER_ACCOUNT>" in lines(tmp_path)[-1]


def test_same_timestamp_different_message_remains_distinct(tmp_path, config):
    second = copy.deepcopy(EVENTS[3])
    second["message"] = second["message"].replace("<ACCOUNT>", "<OTHER_ACCOUNT>")
    assert run(tmp_path, config, RecordedClient(EVENTS + [second, EVENTS[3]])) == 6
    assert len(lines(tmp_path)) == 6


def test_empty_response_advances_poll_checkpoint_without_fabricating_access(tmp_path, config):
    assert run(tmp_path, config, RecordedClient([])) == 0
    assert rows(tmp_path, "meta")[0][2] == END
    assert not list((tmp_path / "logs").glob("*.log"))


@pytest.mark.parametrize("code", ["http_403", "http_429", "http_523", "transport_or_json"])
def test_api_error_after_success_preserves_checkpoint(tmp_path, config, code):
    run(tmp_path, config)
    baseline = rows(tmp_path, "meta")
    original = lines(tmp_path)

    class FailingClient:
        def fetch(self, *args):
            raise nebula.PollError(code)

    with pytest.raises(nebula.PollError, match=code):
        run(tmp_path, config, FailingClient(), now=NOW + 1000)
    assert rows(tmp_path, "meta") == baseline
    assert lines(tmp_path) == original


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("devId", "<OTHER_SWITCH>", "event_device"),
        ("timestamp", True, "event_time"),
        ("timestamp", INITIAL - 1, "event_time"),
        ("message", "injected\nline", "event_control_character"),
        ("message", "HTTP(s) unexpected authentication format", "authentication_unknown"),
        ("tag", None, "event_schema"),
    ],
)
def test_invalid_record_or_unknown_authentication_stops_entire_batch(
    tmp_path, config, field, value, code
):
    events = copy.deepcopy(EVENTS)
    events[0][field] = value

    class MalformedClient:
        def fetch(self, *args):
            return events

    config["chunk_ms"] = END - INITIAL + 1
    with pytest.raises(nebula.PollError, match=code):
        run(tmp_path, config, MalformedClient())
    assert not rows(tmp_path, "meta")
    assert not list((tmp_path / "logs").glob("*.log"))


def test_dict_response_is_not_guessed_as_an_api_page(tmp_path, config):
    class WrappedClient:
        def fetch(self, *args):
            return {"Count": 5, "value": EVENTS}

    with pytest.raises(nebula.PollError, match="response_schema"):
        run(tmp_path, config, WrappedClient())
    assert not rows(tmp_path, "meta")


def test_saturated_interval_splits_with_overlapping_boundary(tmp_path, config):
    config["chunk_ms"] = END - INITIAL + 1
    config["response_guard"] = 3
    client = RecordedClient()
    assert run(tmp_path, config, client) == 5
    assert len(client.calls) > 1
    assert len(lines(tmp_path)) == 5
    assert client.calls[1][0] == INITIAL


def test_saturated_single_millisecond_is_an_error_without_checkpoint(tmp_path, config):
    config["response_guard"] = 2
    duplicate = copy.deepcopy(EVENTS[3])
    duplicate["message"] = duplicate["message"].replace("<ACCOUNT>", "<OTHER_ACCOUNT>")
    with pytest.raises(nebula.PollError, match="response_saturated"):
        run(tmp_path, config, RecordedClient([EVENTS[3], duplicate]))
    assert not rows(tmp_path, "meta")


def test_request_budget_is_not_a_partial_success(tmp_path, config):
    config["max_requests"] = 1
    with pytest.raises(nebula.PollError, match="request_budget"):
        run(tmp_path, config)
    assert not rows(tmp_path, "meta")


def test_offline_period_within_horizon_recovers_full_window(tmp_path, config):
    client = RecordedClient()
    assert run(tmp_path, config, client, now=NOW + 3_600_000) == 5
    assert client.calls[0][0] == INITIAL
    assert rows(tmp_path, "meta")[0][2] == END + 3_600_000


def test_gap_beyond_horizon_does_not_silently_reset_start(tmp_path, config):
    run(tmp_path, config)
    baseline = rows(tmp_path, "meta")
    client = RecordedClient()
    with pytest.raises(nebula.PollError, match="gap_exceeds_horizon"):
        run(tmp_path, config, client, now=NOW + config["recovery_horizon_ms"])
    assert not client.calls
    assert rows(tmp_path, "meta") == baseline


def test_clock_rollback_does_not_regress_checkpoint(tmp_path, config):
    run(tmp_path, config)
    with pytest.raises(nebula.PollError, match="clock_before_checkpoint"):
        run(tmp_path, config, now=NOW - 1)
    assert rows(tmp_path, "meta")[0][2] == END


def test_crash_after_synced_log_replays_journal_without_duplicate(tmp_path, config, monkeypatch):
    original = nebula.sync_directory

    def crash(path):
        original(path)
        if path == tmp_path / "logs":
            raise OSError("simulated interruption after fsync")

    monkeypatch.setattr(nebula, "sync_directory", crash)
    with pytest.raises(OSError):
        run(tmp_path, config)
    assert len(lines(tmp_path)) == 5
    assert not rows(tmp_path, "meta")
    assert len(rows(tmp_path, "pending")) == 1
    monkeypatch.setattr(nebula, "sync_directory", original)
    assert run(tmp_path, config) == 0
    assert len(lines(tmp_path)) == 5
    assert not rows(tmp_path, "pending")
    assert rows(tmp_path, "meta")[0][2] == END


def test_partial_append_is_completed_byte_for_byte(tmp_path, config, monkeypatch):
    original = nebula.Path.open

    class PartialWriter:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def __getattr__(self, key):
            return getattr(self.handle, key)

        def write(self, payload):
            self.handle.write(payload[:19])
            self.handle.flush()
            raise OSError("simulated partial append")

    def partial(path, *args, **kwargs):
        handle = original(path, *args, **kwargs)
        return PartialWriter(handle) if path.suffix == ".log" else handle

    monkeypatch.setattr(nebula.Path, "open", partial)
    with pytest.raises(OSError):
        run(tmp_path, config)
    assert (tmp_path / "logs/2026-10-09.log").stat().st_size == 19
    assert not rows(tmp_path, "meta")
    monkeypatch.setattr(nebula.Path, "open", original)
    assert run(tmp_path, config) == 0
    assert len(lines(tmp_path)) == 5
    assert datetime.fromisoformat(lines(tmp_path)[0].split()[0]) == RECEIVED


def test_external_append_conflicts_with_pending_journal(tmp_path, config, monkeypatch):
    original = nebula.sync_directory

    def crash(path):
        if path == tmp_path / "logs":
            raise OSError("simulated interruption")
        original(path)

    monkeypatch.setattr(nebula, "sync_directory", crash)
    with pytest.raises(OSError):
        run(tmp_path, config)
    with (tmp_path / "logs/2026-10-09.log").open("ab") as handle:
        handle.write(b"external modification\n")
    monkeypatch.setattr(nebula, "sync_directory", original)
    with pytest.raises(nebula.PollError, match="log_journal_conflict"):
        run(tmp_path, config)
    assert not rows(tmp_path, "meta")
    assert rows(tmp_path, "pending")


def test_state_cannot_be_reused_for_other_switch(tmp_path, config):
    run(tmp_path, config)
    config["device_id"] = "<OTHER_SWITCH>"
    with pytest.raises(nebula.PollError, match="state_identity"):
        run(tmp_path, config)


def test_concurrent_execution_is_refused(tmp_path, config):
    (tmp_path / "state").mkdir()
    with nebula.source_lock(tmp_path / "state/poll.lock"):
        with pytest.raises(nebula.PollError, match="poll_already_running"):
            run(tmp_path, config)


class ResponseAdapter(BaseAdapter):
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload
        self.calls = []

    def send(self, request, **kwargs):
        self.calls.append((request, kwargs))
        response = requests.Response()
        response.status_code = self.status
        response._content = self.payload
        response.request = request
        response.url = request.url
        return response

    def close(self):
        pass


@pytest.mark.parametrize("status", [200, 302, 403, 429, 523])
def test_http_request_has_verified_tls_fixed_origin_no_redirect_or_proxy(config, status):
    client = nebula.NebulaClient("test-key")
    adapter = ResponseAdapter(status, b"[]")
    client.session.mount("https://", adapter)
    try:
        if status == 200:
            assert client.fetch(config, INITIAL, END) == []
        else:
            with pytest.raises(nebula.PollError, match=f"http_{status}"):
                client.fetch(config, INITIAL, END)
        assert len(adapter.calls) == 1
        request, kwargs = adapter.calls[0]
        assert request.method == "POST"
        assert request.url.startswith(nebula.API_BASE + "/")
        assert request.headers["X-ZyxelNebula-API-Key"] == "test-key"
        assert json.loads(request.body) == {"startTimestamp": INITIAL, "endTimestamp": END}
        assert kwargs["verify"] is True
        assert not kwargs["proxies"]
        assert kwargs["timeout"] == (10, 30)
        assert client.session.trust_env is False
    finally:
        client.close()


def test_invalid_json_response_is_an_error(config):
    client = nebula.NebulaClient("test-key")
    client.session.mount("https://", ResponseAdapter(200, b"not-json"))
    try:
        with pytest.raises(nebula.PollError, match="transport_or_json"):
            client.fetch(config, INITIAL, END)
    finally:
        client.close()


def test_public_example_requires_environment_values():
    with pytest.raises(nebula.PollError):
        nebula.load_config(FIXTURES.parent.parent / "config/nebula-switch.example.json")


def test_cli_failure_emits_adsline_without_exception_or_secret(tmp_path, capsys):
    config = tmp_path / "config.json"
    config.write_text("not json", encoding="utf-8")
    assert nebula.main(["--config", str(config), "--api-key-file", str(tmp_path / "key")]) == 1
    output = capsys.readouterr().err.strip().split(" ", 4)
    assert len(output) == 5
    assert output[1] == "nebula"
    assert output[3] == "nebula-poller"
    assert output[4] == "status=error code=config_invalid"


@pytest.mark.skipif(os.name != "posix", reason="permessi POSIX verificati solo su Linux")
def test_secret_and_log_permissions(tmp_path, config):
    key = tmp_path / "key"
    key.write_text("test-key", encoding="utf-8")
    key.chmod(0o644)
    with pytest.raises(nebula.PollError, match="key_permissions"):
        nebula.read_key(key)
    key.chmod(0o600)
    assert nebula.read_key(key) == "test-key"
    run(tmp_path, config)
    assert (tmp_path / "logs/2026-10-09.log").stat().st_mode & 0o777 == 0o640
    assert (tmp_path / "state/state.sqlite").stat().st_mode & 0o777 == 0o600
