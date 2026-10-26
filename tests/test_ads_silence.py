"""A quiet event source and a missing heartbeat have distinct evidence."""

import importlib.util
import json
from datetime import date, timedelta
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
    prepared = [
        {**source, "active_from": source.get("active_from", "2026-10-22")}
        for source in sources
    ]
    path.write_text(json.dumps({"version": 2, "sources": prepared}), encoding="utf-8")
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
        [{"id": "source-a", "signal": "daily_event", "active_from": "2026-02-30"}],
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


def test_cli_rejects_unmounted_log_root(tmp_path, silence, capsys):
    logs = tmp_path / "logs"
    logs.mkdir()
    policy = policy_file(tmp_path, [{"id": "source-a", "signal": "daily_event"}])
    code = silence.main([
        "--policy", str(policy), "--log-root", str(logs),
        "--heartbeat-root", str(tmp_path / "beats"), "--day", "2026-10-22",
        "--require-log-mount",
    ])
    assert code == 3
    captured = capsys.readouterr()
    assert "log_mount_missing" in captured.err
    assert not captured.out


def test_window_recovers_a_day_missed_before_yesterday(tmp_path, silence, capsys):
    logs = tmp_path / "logs"
    source_dir = logs / "source-a"
    source_dir.mkdir(parents=True)
    (source_dir / "2026-10-22.log").write_text("access\n", encoding="utf-8")
    policy = policy_file(tmp_path, [{
        "id": "source-a", "signal": "daily_event", "active_from": "2026-10-20",
    }])
    args = [
        "--policy", str(policy), "--log-root", str(logs),
        "--heartbeat-root", str(tmp_path / "beats"),
        "--day", "2026-10-22", "--lookback-days", "3",
    ]
    assert silence.main(args) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["window_start"] == "2026-10-20"
    assert report["checked_days"] == 3
    assert report["checked"] == 3
    assert [issue["day"] for issue in report["issues"]] == [
        "2026-10-20", "2026-10-21",
    ]
    for day in ["2026-10-20", "2026-10-21"]:
        (source_dir / f"{day}.log").write_text("access\n", encoding="utf-8")
    assert silence.main(args) == 0
    assert json.loads(capsys.readouterr().out)["issue_count"] == 0


def test_window_starts_at_each_sources_activation(tmp_path, silence):
    logs = tmp_path / "logs"
    (logs / "old-source").mkdir(parents=True)
    (logs / "new-source").mkdir()
    for day in ["2026-10-20", "2026-10-21", "2026-10-22"]:
        (logs / "old-source" / f"{day}.log").write_text("access\n", encoding="utf-8")
    (logs / "new-source" / "2026-10-22.log").write_text("access\n", encoding="utf-8")
    sources = silence.load_policy(policy_file(tmp_path, [
        {"id": "old-source", "signal": "daily_event", "active_from": "2026-10-20"},
        {"id": "new-source", "signal": "daily_event", "active_from": "2026-10-22"},
    ]))
    report = silence.check_window(sources, "2026-10-22", 213, logs, tmp_path / "beats")
    assert report["window_start"] == "2026-10-20"
    assert report["checked_days"] == 3
    assert report["checked"] == 4
    assert report["issue_count"] == 0


def test_window_bounds_journal_details_but_keeps_issue_count(tmp_path, silence):
    logs = tmp_path / "logs"
    logs.mkdir()
    first = date(2026, 1, 1)
    sources = silence.load_policy(policy_file(tmp_path, [{
        "id": "source-a", "signal": "daily_event", "active_from": first.isoformat(),
    }]))
    target = (first + timedelta(days=100)).isoformat()
    report = silence.check_window(sources, target, 213, logs, tmp_path / "beats")
    assert report["checked_days"] == 101
    assert report["issue_count"] == 101
    assert len(report["issues"]) == 100
    assert report["omitted_issues"] == 1


def test_window_accepts_maximum_calendar_day(tmp_path, silence):
    logs = tmp_path / "logs"
    source_dir = logs / "source-a"
    source_dir.mkdir(parents=True)
    for day in ["9999-12-30", "9999-12-31"]:
        (source_dir / f"{day}.log").write_text("access\n", encoding="utf-8")
    sources = silence.load_policy(policy_file(tmp_path, [{
        "id": "source-a", "signal": "daily_event", "active_from": "9999-12-30",
    }]))
    report = silence.check_window(sources, "9999-12-31", 2, logs, tmp_path / "beats")
    assert report["checked_days"] == 2
    assert report["checked"] == 2
    assert report["status"] == "ok"


def test_old_policy_and_invalid_window_cannot_report_green(tmp_path, silence, capsys):
    policy = policy_file(tmp_path, [{"id": "source-a", "signal": "daily_event"}])
    policy.write_text('{"version": 1, "sources": []}', encoding="utf-8")
    with pytest.raises(silence.PolicyError, match="policy_version"):
        silence.load_policy(policy)
    policy = policy_file(tmp_path, [{"id": "source-a", "signal": "daily_event"}])
    logs = tmp_path / "logs"
    logs.mkdir()
    code = silence.main([
        "--policy", str(policy), "--log-root", str(logs),
        "--day", "2026-10-22", "--lookback-days", "214",
    ])
    assert code == 3
    assert "lookback_invalid" in capsys.readouterr().err


def test_policy_rejects_duplicate_json_keys(tmp_path, silence):
    path = tmp_path / "policy.json"
    path.write_text(
        '{"version":2,"sources":[{"id":"source-a","id":"source-b",'
        '"signal":"daily_event","active_from":"2026-10-22"}]}',
        encoding="utf-8",
    )
    with pytest.raises(silence.PolicyError, match="policy_duplicate_key"):
        silence.load_policy(path)
