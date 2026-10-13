"""La pubblicazione va osservata su un login nuovo, con tempi e controlli reali."""

import copy
import importlib.util
import io
import json
from datetime import UTC, datetime

import pytest

from conftest import FIXTURES, ROOT

spec = importlib.util.spec_from_file_location(
    "nebula_publication", ROOT / "tools/watch-nebula-publication.py"
)
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)
EVENTS = json.loads((FIXTURES / "nebula-switch-events.json").read_text(encoding="utf-8"))
LOGIN = next(e for e in EVENTS if publication.windows.poller.outcome(e) == "login")
LOGOUT = next(e for e in EVENTS if publication.windows.poller.outcome(e) == "logout")
TARGET = {"site_id": "<SITE_ID>", "device_id": "<SWITCH_ID>"}
START_MS = LOGIN["timestamp"] - 2000


class Clock:
    def __init__(self):
        self.seconds = 0

    def now(self):
        return datetime.fromtimestamp(START_MS / 1000 + self.seconds, UTC)

    def sleep(self, seconds):
        self.seconds += seconds


class Client:
    def __init__(self, clock, pages):
        self.clock, self.pages = clock, pages
        self.calls = []

    def fetch(self, target, left, right):
        self.calls.append((left, right))
        self.clock.seconds += 1
        return self.pages[min(len(self.calls) - 1, len(self.pages) - 1)]


def measure(tmp_path, pages, **settings):
    clock = Clock()
    client = Client(clock, pages)
    report = publication.measure(
        client, TARGET, tmp_path, clock.now, lambda: clock.seconds, clock.sleep, **settings
    )
    return report, client


def test_negative_then_positive_records_delay_and_exact_candidate(tmp_path):
    report, client = measure(tmp_path, [[], [], [LOGIN]])
    assert report["ok"] and report["status"] == "observed"
    assert report["requests"] == len(client.calls) == 3
    assert report["apparent_delay_upper_ms"] == 31000
    assert report["last_negative_request_start_delay_ms"] == 14000
    assert report["candidate_timestamp_ms"] == LOGIN["timestamp"]
    assert (
        json.loads((tmp_path / "ready.json").read_text())["observation_started_at"]
        == report["started_at"]
    )
    assert json.loads((tmp_path / "private-candidates.json").read_text()) == [LOGIN]
    assert all(
        value not in json.dumps(report) for value in ("<ACCOUNT>", "<CLIENT_IP>", "<SWITCH_ID>")
    )


def test_empty_responses_are_inconclusive_and_bounded(tmp_path):
    report, client = measure(tmp_path, [[]])
    assert not report["ok"] and report["status"] == "no_new_login"
    assert 1 < len(client.calls) <= publication.MAX_REQUESTS
    assert report["apparent_delay_upper_ms"] is None
    assert report["last_negative_request_start_delay_ms"] is None


def test_old_login_and_technical_event_do_not_complete_observation(tmp_path):
    old = copy.deepcopy(LOGIN)
    old["timestamp"] = START_MS - 1000
    technical = copy.deepcopy(EVENTS[-1])
    technical["timestamp"] = START_MS
    report, _ = measure(tmp_path, [[old, technical]])
    assert not report["ok"] and report["candidate_logins"] == 0


def test_multiple_new_logins_are_ambiguous(tmp_path):
    other = copy.deepcopy(LOGIN)
    other["message"] = other["message"].replace("<ACCOUNT>", "<OTHER_ACCOUNT>")
    report, _ = measure(tmp_path, [[], [LOGIN, other]])
    assert not report["ok"] and report["status"] == "ambiguous"
    assert report["candidate_logins"] == 2 and report["candidate_timestamp_ms"] is None


def test_exact_duplicate_is_one_candidate(tmp_path):
    report, _ = measure(tmp_path, [[], [LOGIN, LOGIN]])
    assert report["ok"] and report["candidate_logins"] == 1


def test_saturated_response_does_not_measure_delay(tmp_path):
    with pytest.raises(
        publication.windows.poller.PollError, match="observation_response_saturated"
    ):
        measure(tmp_path, [[], [LOGIN] * publication.RESPONSE_GUARD])


def test_http_failure_is_not_a_negative_sample(tmp_path):
    clock = Clock()

    class Failure(Client):
        def fetch(self, target, left, right):
            raise publication.windows.poller.PollError("http_403")

    with pytest.raises(publication.windows.poller.PollError, match="http_403"):
        publication.measure(
            Failure(clock, []), TARGET, tmp_path, clock.now, lambda: clock.seconds, clock.sleep
        )
    assert not list(tmp_path.glob("sample-*-meta.json"))


def test_clock_regression_invalidates_observation(tmp_path):
    clock = Clock()

    class Backwards(Client):
        def fetch(self, target, left, right):
            clock.seconds -= 1
            return []

    with pytest.raises(publication.windows.poller.PollError, match="observation_clock_backwards"):
        publication.measure(
            Backwards(clock, []), TARGET, tmp_path, clock.now, lambda: clock.seconds, clock.sleep
        )


def recheck(tmp_path, pages, observation=None):
    clock = Clock()
    clock.seconds = 60
    client = Client(clock, pages)
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    original = {
        "status": "no_new_login",
        "ok": False,
        "eligible_start_ms": START_MS,
        "observations": [{"query_end_ms": START_MS + 30_000}],
    }
    report = publication.recheck(
        client,
        TARGET,
        reference,
        original if observation is None else observation,
        tmp_path,
        clock.now,
    )
    return report, client


def test_recheck_preserves_control_and_diagnostic_scope(tmp_path):
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    report, client = recheck(tmp_path, [[reference], [LOGIN]])
    assert report["ok"] and report["status"] == "candidates_found"
    assert report["requests"] == len(client.calls) == 2
    assert report["control_present"] and report["login_candidates"] == 1
    assert report["candidates"][0]["within_original_query_window"]
    assert report["query_start_ms"] == START_MS - 7_200_000
    assert "publication_time_unverified" in report["scope"]


def test_recheck_empty_with_valid_control_is_still_inconclusive(tmp_path):
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    report, _ = recheck(tmp_path, [[reference], []])
    assert report["control_present"] and not report["ok"]
    assert report["status"] == "no_recent_login" and report["login_candidates"] == 0


def test_recheck_without_historical_reference_cannot_validate_candidates(tmp_path):
    report, _ = recheck(tmp_path, [[], [LOGIN]])
    assert not report["ok"] and report["status"] == "control_missing"
    assert report["login_candidates"] == 1


def test_recheck_candidate_with_earlier_timestamp_is_identified_without_claiming_cause(tmp_path):
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    early = copy.deepcopy(LOGIN)
    early["timestamp"] = START_MS - 60_000
    report, _ = recheck(tmp_path, [[reference], [early]])
    assert report["control_present"] and report["login_candidates"] == 1
    assert not report["candidates"][0]["within_original_query_window"]


def test_recheck_rejects_unusable_observation_before_http(tmp_path):
    class NoHttp:
        def fetch(self, target, left, right):
            raise AssertionError("Richiesta prima della verifica del report")

    with pytest.raises(publication.windows.history.EvidenceError, match="observation_schema"):
        publication.recheck(NoHttp(), TARGET, LOGIN, {"status": "observed"}, tmp_path)


def test_recheck_distinguishes_query_window_from_login_eligibility(tmp_path):
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    early = copy.deepcopy(LOGIN)
    early["timestamp"] = START_MS - 10_000
    report, _ = recheck(tmp_path, [[reference], [early]])
    assert report["candidates"][0]["within_original_query_window"]
    assert not report["candidates"][0]["eligible_for_original_watch"]


def test_recheck_saturated_wide_response_does_not_claim_result(tmp_path):
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    with pytest.raises(publication.windows.poller.PollError, match="recheck_response_saturated"):
        recheck(tmp_path, [[reference], [LOGIN] * publication.RESPONSE_GUARD])


def test_final_observation_is_longer_bounded_and_empty_is_not_success(tmp_path):
    clock = Clock()
    client = Client(clock, [[]])
    report = publication.measure(
        client,
        TARGET,
        tmp_path,
        clock.now,
        lambda: clock.seconds,
        clock.sleep,
        duration_seconds=publication.FINAL_DURATION_SECONDS,
        max_requests=publication.FINAL_MAX_REQUESTS,
    )
    assert not report["ok"] and report["status"] == "no_new_login"
    assert report["duration_seconds"] == 600 and report["max_requests"] == 41
    assert publication.MAX_REQUESTS < report["requests"] <= 41


@pytest.mark.parametrize("observed", [False, True])
def test_final_cli_rechecks_only_timeout_and_keeps_it_inconclusive(
    tmp_path, monkeypatch, capsys, observed
):
    baseline = tmp_path / "baseline.json"
    snapshot = tmp_path / "snapshot.json"
    baseline.write_text(json.dumps([{"DevId": TARGET["device_id"], "EventLogs": EVENTS}]))
    snapshot.write_text(
        json.dumps(
            {
                "organizations": [
                    {
                        "sites": [
                            {
                                "siteId": TARGET["site_id"],
                                "devices": [{"devId": TARGET["device_id"], "type": "SW"}],
                            }
                        ]
                    }
                ]
            }
        )
    )
    output = tmp_path / "output"
    calls = []

    class FinalClient:
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"

        def fetch(self, target, left, right):
            calls.append((left, right))
            assert not observed, "Diagnosi dopo una misura già positiva"
            _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
            return [reference] if len(calls) == 1 else [LOGIN]

        def close(self):
            pass

    def observation(client, target, path, **settings):
        assert settings == {"duration_seconds": 600, "max_requests": 41}
        return {
            "status": "observed" if observed else "no_new_login",
            "ok": observed,
            "eligible_start_ms": START_MS,
            "observations": [{"query_end_ms": START_MS + 30_000}],
            "requests": 1,
            "candidate_logins": int(observed),
            "apparent_delay_upper_ms": 15000 if observed else None,
        }

    monkeypatch.setattr(publication, "measure", observation)
    monkeypatch.setattr(publication.windows.poller, "NebulaClient", FinalClient)
    monkeypatch.setattr(publication.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    result = publication.main(
        [
            "--key-stdin",
            "--final-attempt",
            "--baseline",
            str(baseline),
            "--snapshot",
            str(snapshot),
            "--output",
            str(output),
        ]
    )
    assert result == (0 if observed else 1)
    assert len(calls) == (0 if observed else 2)
    primary = json.loads((output / "comparison.json").read_text())
    assert primary["ok"] is observed
    if not observed:
        diagnostic = json.loads((output / "followup/comparison.json").read_text())
        assert diagnostic["status"] == "candidates_found"
    else:
        assert not (output / "followup").exists()
    assert "FAKE_STDIN_KEY" not in capsys.readouterr().out


def two_switches():
    device54 = "<SWITCH54_ID>"
    technical = copy.deepcopy(EVENTS[-1])
    technical["devId"] = device54
    technical["timestamp"] = START_MS - 100_000
    baseline = {TARGET["device_id"]: EVENTS, device54: [technical]}
    snapshot = {
        "organizations": [
            {
                "sites": [
                    {
                        "siteId": TARGET["site_id"],
                        "devices": [
                            {
                                "devId": TARGET["device_id"],
                                "type": "SW",
                                "model": "XGS2220-30HP",
                            },
                            {"devId": device54, "type": "SW", "model": "XGS2220-54HP"},
                        ],
                    }
                ]
            }
        ]
    }
    return baseline, snapshot, {**TARGET, "device_id": device54}, technical


def test_explicit_model_selects_54hp_with_technical_control_instead_of_30hp():
    baseline, snapshot, target54, technical = two_switches()
    target, reference = publication.select_target(snapshot, baseline, "XGS2220-54HP")
    assert target == target54 and reference == technical
    assert publication.windows.poller.outcome(reference) is None
    legacy, legacy_reference = publication.select_target(snapshot, baseline)
    assert legacy == TARGET
    assert legacy_reference in EVENTS


@pytest.mark.parametrize("matches", [0, 2])
def test_explicit_model_rejects_missing_or_ambiguous_snapshot(matches):
    baseline, snapshot, _, _ = two_switches()
    devices = snapshot["organizations"][0]["sites"][0]["devices"]
    other = devices.pop()
    devices.extend(copy.deepcopy(other) for _ in range(matches))
    with pytest.raises(
        publication.windows.history.EvidenceError, match="snapshot_model_missing_or_ambiguous"
    ):
        publication.select_target(snapshot, baseline, "XGS2220-54HP")


def test_explicit_model_requires_a_reference_from_the_selected_device():
    baseline, snapshot, target54, _ = two_switches()
    baseline[target54["device_id"]] = []
    with pytest.raises(publication.windows.history.EvidenceError, match="target_reference_missing"):
        publication.select_target(snapshot, baseline, "XGS2220-54HP")


@pytest.mark.parametrize("observed", [False, True])
def test_54hp_cli_observes_correct_target_and_rechecks_its_technical_control(
    tmp_path, monkeypatch, observed
):
    baseline_data, snapshot_data, target54, technical = two_switches()
    baseline = tmp_path / "baseline.json"
    snapshot = tmp_path / "snapshot.json"
    baseline.write_text(
        json.dumps(
            [{"DevId": device, "EventLogs": events} for device, events in baseline_data.items()]
        )
    )
    snapshot.write_text(json.dumps(snapshot_data))
    login54 = copy.deepcopy(LOGIN)
    login54["devId"] = target54["device_id"]
    calls = []

    class SelectedClient:
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"

        def fetch(self, target, left, right):
            assert target == target54
            calls.append((left, right))
            return [technical] if len(calls) == 1 else [login54]

        def close(self):
            pass

    def observation(client, target, path, **settings):
        assert target == target54 and settings == {"duration_seconds": 600, "max_requests": 41}
        return {
            "status": "observed" if observed else "no_new_login",
            "ok": observed,
            "eligible_start_ms": START_MS,
            "observations": [{"query_end_ms": START_MS + 30_000}],
            "requests": 1,
            "candidate_logins": int(observed),
            "apparent_delay_upper_ms": 15000 if observed else None,
        }

    monkeypatch.setattr(publication, "measure", observation)
    monkeypatch.setattr(publication.windows.poller, "NebulaClient", SelectedClient)
    monkeypatch.setattr(publication.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    status = publication.main(
        [
            "--key-stdin",
            "--final-attempt",
            "--switch-model",
            "XGS2220-54HP",
            "--baseline",
            str(baseline),
            "--snapshot",
            str(snapshot),
            "--output",
            str(output),
        ]
    )
    assert status == (0 if observed else 1)
    assert json.loads((output / "private-target.json").read_text()) == target54
    assert len(calls) == (0 if observed else 2)
    if not observed:
        assert calls[0] == (technical["timestamp"] - 1000, technical["timestamp"] + 1000)
        diagnostic = json.loads((output / "followup/comparison.json").read_text())
        assert diagnostic["control_present"] and diagnostic["status"] == "candidates_found"


def test_recheck_rejects_a_report_from_the_other_device_before_client_creation(
    tmp_path, monkeypatch
):
    baseline_data, snapshot_data, _, _ = two_switches()
    baseline = tmp_path / "baseline.json"
    snapshot = tmp_path / "snapshot.json"
    baseline.write_text(
        json.dumps(
            [{"DevId": device, "EventLogs": events} for device, events in baseline_data.items()]
        )
    )
    snapshot.write_text(json.dumps(snapshot_data))
    observation = tmp_path / "comparison.json"
    observation.write_text("{}")
    (tmp_path / "private-target.json").write_text(json.dumps(TARGET))

    def no_client(key):
        raise AssertionError("Client creato prima di verificare il target del report")

    monkeypatch.setattr(publication.windows.poller, "NebulaClient", no_client)
    monkeypatch.setattr(publication.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    status = publication.main(
        [
            "--key-stdin",
            "--switch-model",
            "XGS2220-54HP",
            "--observation",
            str(observation),
            "--baseline",
            str(baseline),
            "--snapshot",
            str(snapshot),
            "--output",
            str(output),
        ]
    )
    assert status == 1 and not output.exists()


def test_logout_ignores_login_and_old_logout_then_saves_exact_new_event(tmp_path):
    old = copy.deepcopy(LOGOUT)
    old["timestamp"] = START_MS - 1000
    logout = copy.deepcopy(LOGOUT)
    logout["timestamp"] = START_MS + 20_000
    report, client = measure(tmp_path, [[old], [LOGIN], [logout]], expected_event="logout")
    assert report["ok"] and report["status"] == "observed"
    assert report["expected_event"] == "logout" and report["candidate_events"] == 1
    assert len(client.calls) == 3 and report["candidate_timestamp_ms"] == logout["timestamp"]
    assert report["apparent_delay_upper_ms"] == 13_000
    assert json.loads((tmp_path / "private-candidates.json").read_text()) == [logout]
    assert "candidate_logins" not in report


def test_logout_watch_does_not_succeed_on_logins_alone(tmp_path):
    report, _ = measure(tmp_path, [[], [LOGIN]], expected_event="logout")
    assert not report["ok"] and report["status"] == "no_new_logout"
    assert report["candidate_events"] == 0 and report["apparent_delay_upper_ms"] is None


def test_unknown_logout_preserves_error_and_positive_response_timing(tmp_path):
    logout = copy.deepcopy(LOGOUT)
    logout["timestamp"] = START_MS
    logout["message"] = logout["message"].replace("due to session timeout", "due to unknown reason")
    with pytest.raises(publication.windows.poller.PollError, match="authentication_unknown"):
        measure(tmp_path, [[logout]], expected_event="logout")
    assert json.loads((tmp_path / "sample-001.json").read_text()) == [logout]
    meta = json.loads((tmp_path / "sample-001-meta.json").read_text())
    assert meta["classification_error"] == "authentication_unknown"
    assert meta["requested_at"] == datetime.fromtimestamp(START_MS / 1000, UTC).isoformat()
    assert meta["received_at"] == datetime.fromtimestamp(START_MS / 1000 + 1, UTC).isoformat()
    assert meta["rows"] == 1 and meta["candidate_events"] is None
    assert not (tmp_path / "comparison.json").exists()


def test_recorded_manual_logout_is_observed_with_exact_payload(tmp_path):
    logout = json.loads((FIXTURES / "nebula-switch-manual-logout.json").read_text())
    clock = Clock()
    clock.now = lambda: datetime.fromtimestamp(logout["timestamp"] / 1000 - 2 + clock.seconds, UTC)
    client = Client(clock, [[], [logout]])
    report = publication.measure(
        client,
        TARGET,
        tmp_path,
        clock.now,
        lambda: clock.seconds,
        clock.sleep,
        expected_event="logout",
    )
    assert report["ok"] and report["status"] == "observed" and client.calls
    assert report["candidate_timestamp_ms"] == logout["timestamp"]
    assert report["candidate_events"] == 1 and report["apparent_delay_upper_ms"] == 15_000
    assert json.loads((tmp_path / "private-candidates.json").read_text()) == [logout]


@pytest.mark.parametrize("with_logout", [False, True])
def test_logout_recheck_counts_only_logout_and_keeps_diagnostic_scope(tmp_path, with_logout):
    _, reference = publication.boundaries.select_reference({TARGET["device_id"]: EVENTS})
    logout = copy.deepcopy(LOGOUT)
    logout["timestamp"] = START_MS + 20_000
    original = {
        "status": "no_new_logout",
        "expected_event": "logout",
        "ok": False,
        "eligible_start_ms": START_MS,
        "observations": [{"query_end_ms": START_MS + 30_000}],
    }
    report, _ = recheck(
        tmp_path, [[reference], [LOGIN] + ([logout] if with_logout else [])], original
    )
    assert report["event_candidates"] == int(with_logout)
    assert report["ok"] is with_logout
    assert report["status"] == ("candidates_found" if with_logout else "no_recent_logout")
    assert "publication_time_unverified" in report["scope"]


@pytest.mark.parametrize("observed", [False, True])
@pytest.mark.parametrize("expected_event", ["logout", "failure"])
def test_event_cli_uses_requested_event_and_keeps_timeout_inconclusive(
    tmp_path, monkeypatch, capsys, observed, expected_event
):
    baseline_data, snapshot_data, target54, technical = two_switches()
    baseline, snapshot = tmp_path / "baseline.json", tmp_path / "snapshot.json"
    baseline.write_text(
        json.dumps([{"DevId": d, "EventLogs": e} for d, e in baseline_data.items()])
    )
    snapshot.write_text(json.dumps(snapshot_data))
    logout = copy.deepcopy(LOGOUT if expected_event == "logout" else EVENTS[0])
    logout.update(devId=target54["device_id"], timestamp=START_MS + 20_000)
    calls = []

    class SelectedClient:
        def __init__(self, key):
            assert key == "FAKE_STDIN_KEY"

        def fetch(self, target, left, right):
            assert target == target54
            calls.append((left, right))
            return [technical] if len(calls) == 1 else [logout]

        def close(self):
            pass

    def observation(client, target, path, **settings):
        assert target == target54
        assert settings == {
            "duration_seconds": 600,
            "max_requests": 41,
            "expected_event": expected_event,
        }
        return {
            "status": "observed" if observed else f"no_new_{expected_event}",
            "ok": observed,
            "expected_event": expected_event,
            "candidate_events": int(observed),
            "eligible_start_ms": START_MS,
            "observations": [{"query_end_ms": START_MS + 30_000}],
            "requests": 1,
            "apparent_delay_upper_ms": 15000 if observed else None,
        }

    monkeypatch.setattr(publication, "measure", observation)
    monkeypatch.setattr(publication.windows.poller, "NebulaClient", SelectedClient)
    monkeypatch.setattr(publication.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    status = publication.main(
        [
            "--key-stdin",
            "--final-attempt",
            "--event",
            expected_event,
            "--switch-model",
            "XGS2220-54HP",
            "--baseline",
            str(baseline),
            "--snapshot",
            str(snapshot),
            "--output",
            str(output),
        ]
    )
    assert status == (0 if observed else 1)
    assert len(calls) == (0 if observed else 2)
    assert json.loads((output / "comparison.json").read_text())["ok"] is observed
    if not observed:
        assert (
            json.loads((output / "followup/comparison.json").read_text())["status"]
            == "candidates_found"
        )
    assert f"expected_event={expected_event}" in capsys.readouterr().out


def test_failure_watch_ignores_successes_and_logout(tmp_path):
    failure = copy.deepcopy(EVENTS[0])
    failure["timestamp"] = START_MS + 20_000
    logout = copy.deepcopy(LOGOUT)
    logout["timestamp"] = START_MS + 1000
    report, client = measure(tmp_path, [[], [LOGIN, logout], [failure]], expected_event="failure")
    assert report["ok"] and report["expected_event"] == "failure"
    assert report["requests"] == len(client.calls) == 3 and report["candidate_events"] == 1
    assert json.loads((tmp_path / "private-candidates.json").read_text()) == [failure]


def test_cli_rejects_wrong_event_report_before_client_creation(tmp_path, monkeypatch):
    baseline_data, snapshot_data, target54, _ = two_switches()
    baseline, snapshot = tmp_path / "baseline.json", tmp_path / "snapshot.json"
    baseline.write_text(
        json.dumps([{"DevId": d, "EventLogs": e} for d, e in baseline_data.items()])
    )
    snapshot.write_text(json.dumps(snapshot_data))
    observation = tmp_path / "comparison.json"
    observation.write_text(json.dumps({"expected_event": "login"}))
    (tmp_path / "private-target.json").write_text(json.dumps(target54))

    def no_client(key):
        raise AssertionError("Client creato prima di verificare il tipo di evento")

    monkeypatch.setattr(publication.windows.poller, "NebulaClient", no_client)
    monkeypatch.setattr(publication.sys, "stdin", io.StringIO("FAKE_STDIN_KEY\n"))
    output = tmp_path / "output"
    assert (
        publication.main(
            [
                "--key-stdin",
                "--event",
                "logout",
                "--switch-model",
                "XGS2220-54HP",
                "--observation",
                str(observation),
                "--baseline",
                str(baseline),
                "--snapshot",
                str(snapshot),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert not output.exists()
