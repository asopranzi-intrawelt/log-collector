"""A quiet event source and a missing heartbeat have distinct evidence."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "ads-silence.py"


@pytest.fixture
def silence():
    spec = importlib.util.spec_from_file_location("ads_silence_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy_file(tmp_path, sources):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"version": 1, "sources": sources}), encoding="utf-8")
    return path


def test_event_and_heartbeat_need_their_own_positive_signal(tmp_path, silence):
    day = "2026-10-22"
    logs = tmp_path / "logs"
    beats = tmp_path / "beats"
    logs.mkdir()
    beats.mkdir()
    (logs / "source-a").mkdir()
    (beats / "win-pilot").mkdir()
    (logs / "source-a" / f"{day}.log").write_text("access\n", encoding="utf-8")
    (beats / "win-pilot" / f"{day}.heartbeat").write_text("alive\n", encoding="utf-8")
    policy = policy_file(
        tmp_path,
        [
            {"id": "source-a", "signal": "daily_event"},
            {"id": "win-pilot", "signal": "daily_heartbeat"},
        ],
    )
    sources = silence.load_policy(policy)
    assert silence.check_day(sources, day, logs, beats)["status"] == "ok"

    (beats / "win-pilot" / f"{day}.heartbeat").unlink()
    report = silence.check_day(sources, day, logs, beats)
    assert [item["status"] for item in report["sources"]] == [
        "observed", "heartbeat_missing",
    ]
    assert report["status"] == "alert"

    (logs / "source-a" / f"{day}.log").write_text("", encoding="utf-8")
    report = silence.check_day(sources, day, logs, beats)
    assert [item["status"] for item in report["sources"]] == [
        "no_events", "heartbeat_missing",
    ]


@pytest.mark.parametrize(
    "sources",
    [
        [],
        [{"id": "../escape", "signal": "daily_event"}],
        [{"id": "source-a", "signal": "not_a_signal"}],
        [{"id": "source-a", "signal": ["daily_event"]}],
        [
            {"id": "source-a", "signal": "daily_event"},
            {"id": "source-a", "signal": "daily_heartbeat"},
        ],
    ],
)
def test_bad_or_empty_policy_cannot_report_green(tmp_path, silence, sources):
    with pytest.raises(silence.PolicyError):
        silence.load_policy(policy_file(tmp_path, sources))


def test_cli_reports_silence_without_claiming_source_failure(tmp_path, silence, capsys):
    logs = tmp_path / "logs"
    logs.mkdir()
    policy = policy_file(tmp_path, [{"id": "source-a", "signal": "daily_event"}])
    code = silence.main([
        "--policy", str(policy), "--log-root", str(logs),
        "--heartbeat-root", str(tmp_path / "beats"), "--day", "2026-10-22",
    ])
    report = json.loads(capsys.readouterr().out)
    assert code == 2
    assert report["status"] == "alert"
    assert report["sources"] == [
        {"id": "source-a", "signal": "daily_event", "status": "no_events"},
    ]


def test_cli_rejects_invalid_day_before_reading_policy(tmp_path, silence, capsys):
    assert silence.main(["--policy", str(tmp_path / "missing"), "--day", "2026-02-30"]) == 3
    assert "invalid_day" in capsys.readouterr().err
