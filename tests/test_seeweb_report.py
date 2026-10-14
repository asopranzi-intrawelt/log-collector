"""Prove del formato osservato: per unità, senza inventare tempi dei job."""

import base64
import json
import re
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = spec_from_file_location("seeweb_reader", ROOT / "tools/read-seeweb-report.py")
reader = module_from_spec(spec)
spec.loader.exec_module(reader)
FIXTURES = ROOT / "tests/fixtures"


def raw(status="error"):
    return (FIXTURES / f"seeweb-report-{status}.eml").read_bytes()


def change_html(transform, source=None):
    message = BytesParser(policy=policy.default).parsebytes(source or raw())
    changed = transform(message.get_content())
    message.set_content(changed, subtype="html", charset="utf-8", cte="base64")
    return message.as_bytes(policy=policy.SMTP)


def change_header(name, value, source=None):
    message = BytesParser(policy=policy.default).parsebytes(source or raw())
    message.replace_header(name, value)
    return message.as_bytes(policy=policy.SMTP)


@pytest.mark.parametrize(
    "status,expected", [("ok", ["OK", "OK", "OK"]), ("error", ["Error", "Error", "OK"])]
)
def test_real_shape_preserves_every_unit_status(status, expected):
    report = reader.parse_report(raw(status), datetime(2026, 10, 14, tzinfo=UTC))
    assert [u["consumption_unit"] for u in report["units"]] == [
        "<UNITA_1>",
        "<UNITA_2>",
        "<UNITA_3>",
    ]
    assert [u["data_source"] for u in report["units"]] == [
        "<DATA_SOURCE_1>",
        "<DATA_SOURCE_2>",
        "<DATA_SOURCE_3>",
    ]
    assert [u["status"] for u in report["units"]] == expected
    assert report["total_consumption_units"] == 3
    assert report["counts"]["Error"] == (2 if status == "error" else 0)
    assert report["archive"] == "backup_outcomes"
    assert report["job_execution_time"] is None
    assert all(u["job_execution_time"] is None for u in report["units"])
    assert report["declared_message_at"].endswith("+02:00")
    assert report["acquired_at"] == "2026-10-14T00:00:00+00:00"
    assert report["header_claims_revalidated"] is False
    assert report["attachment_count"] == 0


def test_issue_text_and_displayed_storage_difference_are_kept():
    report = reader.parse_report(raw())
    assert (
        report["units"][0]["issues"] == "Event status: Failed (1)\nOne or more failed schedules (1)"
    )
    assert report["units"][1]["issues"] == report["units"][0]["issues"]
    assert report["units"][2]["issues"] == ""
    assert report["units"][0]["total_storage_gb"] == "54.76"
    assert report["overview_gb"]["Total storage"] == "221.51"
    assert report["displayed_storage_delta_gb"] == "-0.01"


def test_missing_unit_is_not_a_successful_partial_import():
    def remove(html):
        rows = [r for r in re.findall(r"<tr\b[^>]*>.*?</tr>", html, re.S) if "&lt;UNITA_2&gt;" in r]
        assert len(rows) == 1
        return html.replace(rows[0], "", 1)

    with pytest.raises(reader.ReportError, match="unit_count_mismatch"):
        reader.parse_report(change_html(remove))


def test_inconsistent_status_summary_is_rejected():
    def change(html):
        for label, old, new in (("OK", "1", "2"), ("Error", "2", "1")):
            pattern = rf"(<td[^>]*>\s*{label}\s*</td>\s*<td[^>]*>\s*){old}(\s*</td>)"
            html, count = re.subn(
                pattern, lambda m, replacement=new: m[1] + replacement + m[2], html
            )
            assert count == 1
        return html

    with pytest.raises(reader.ReportError, match="status_count_mismatch"):
        reader.parse_report(change_html(change))


def test_duplicate_unit_identity_is_rejected():
    changed = change_html(
        lambda html: html.replace("&lt;UNITA_2&gt;", "&lt;UNITA_1&gt;").replace(
            "&lt;DATA_SOURCE_2&gt;", "&lt;DATA_SOURCE_1&gt;"
        )
    )
    with pytest.raises(reader.ReportError, match="duplicate_unit"):
        reader.parse_report(changed)


@pytest.mark.parametrize(
    "old,new,code",
    [
        ("Data-source", "Data source renamed", "unit_columns"),
        ("54,76", "54.76", "decimal_format"),
        ("<table ", "<table><table ", "nested_table"),
    ],
)
def test_format_changes_are_errors(old, new, code):
    with pytest.raises(reader.ReportError, match=code):
        reader.parse_report(change_html(lambda html: html.replace(old, new, 1)))


def test_subject_ok_cannot_hide_error_units():
    changed = change_header("Subject", "Backup status report (OK): <ORGANIZZAZIONE> (2026-10-13)")
    with pytest.raises(reader.ReportError, match="subject_status_mismatch"):
        reader.parse_report(changed)


def test_sender_is_a_filter_and_does_not_prove_authenticity():
    with pytest.raises(reader.ReportError, match="sender_mismatch"):
        reader.parse_report(raw(), expected_sender="other@example.com")
    report = reader.parse_report(raw(), expected_sender="reports@example.com")
    assert "spf=pass" in report["authentication_results_declared"][0]
    assert report["header_claims_revalidated"] is False


@pytest.mark.parametrize(
    "kind,code",
    [
        ("missing_date", "header_cardinality"),
        ("duplicate_date", "header_cardinality"),
        ("naive_date", "message_date"),
        ("wrong_report_date", "report_date_mismatch"),
    ],
)
def test_ambiguous_or_inconsistent_dates_are_rejected(kind, code):
    message = BytesParser(policy=policy.default).parsebytes(raw())
    if kind == "missing_date":
        del message["Date"]
        changed = message.as_bytes(policy=policy.SMTP)
    elif kind == "duplicate_date":
        changed = raw().replace(b"Date: ", b"Date: Tue, 13 Oct 2026 08:08:43 +0200\r\nDate: ", 1)
    elif kind == "naive_date":
        changed = change_header("Date", "Tue, 13 Oct 2026 08:08:43 -0000")
    else:
        changed = change_header(
            "Subject", "Backup status report (Error): <ORGANIZZAZIONE> (2026-10-12)"
        )
    with pytest.raises(reader.ReportError, match=code):
        reader.parse_report(changed)


def test_naive_acquisition_time_is_rejected():
    with pytest.raises(reader.ReportError, match="acquisition_timezone"):
        reader.parse_report(raw(), datetime(2026, 10, 14))


def test_invalid_utf8_cannot_silently_change_a_unit_identity():
    message = BytesParser(policy=policy.default).parsebytes(raw())
    body = message.get_payload(decode=True)
    assert b"UNITA_1" in body
    message.set_payload(base64.b64encode(body.replace(b"UNITA_1", b"UNITA_\xff", 1)).decode())
    with pytest.raises(reader.ReportError, match="mime_or_sender"):
        reader.parse_report(message.as_bytes(policy=policy.SMTP))


def cli_args(tmp_path, monkeypatch, payloads):
    monkeypatch.setattr(reader, "ROOT", tmp_path)
    private = tmp_path / "_notes"
    private.mkdir()
    config = private / "source.json"
    config.write_text(json.dumps({"sender": "reports@example.com"}))
    paths = []
    for index, payload in enumerate(payloads):
        path = private / f"sample-{index}.eml"
        path.write_bytes(payload)
        paths.append(str(path))
    output = private / "read"
    args = ["--input", *paths, "--output", str(output), "--source-config", str(config)]
    return args, output


def test_cli_real_shapes_write_six_private_records_without_identifiers_on_stdout(
    tmp_path, monkeypatch, capsys
):
    args, output = cli_args(tmp_path, monkeypatch, [raw(), raw("ok")])
    assert reader.main(args) == 0
    reports = json.loads((output / "reports.json").read_text())
    records = [
        json.loads(line) for line in (output / "unit-statuses.jsonl").read_text().splitlines()
    ]
    assert len(reports) == 2 and len(records) == 6
    assert [record["status"] for record in records] == ["Error", "Error", "OK", "OK", "OK", "OK"]
    assert all(record["job_execution_time"] is None for record in records)
    assert (output / "input-001.eml").read_bytes() == raw()
    log = capsys.readouterr().out
    assert "unit_statuses=6" in log and "unit_errors=2" in log
    assert all(
        token not in log
        for token in ("<UNITA_1>", "<ORGANIZZAZIONE>", "reports@example.com", "sample-0.eml")
    )


def test_only_byte_identical_messages_are_deduplicated(tmp_path, monkeypatch):
    args, output = cli_args(tmp_path, monkeypatch, [raw("ok"), raw("ok")])
    assert reader.main(args) == 0
    assert len(json.loads((output / "reports.json").read_text())) == 1
    assert len((output / "unit-statuses.jsonl").read_text().splitlines()) == 3
    assert len(list(output.glob("input-*.eml"))) == 2
    assert json.loads((output / "manifest.json").read_text())["inputs"][1][
        "byte_identical_duplicate"
    ]


def test_transport_copy_is_marked_without_discarding_it(tmp_path, monkeypatch):
    copied = change_header(
        "Received",
        "from provider.example.com by receiver.example.com; Mon, 12 Oct 2026 06:12:59 +0000",
        raw("ok"),
    )
    args, output = cli_args(tmp_path, monkeypatch, [raw("ok"), copied])
    assert reader.main(args) == 0
    assert len(json.loads((output / "reports.json").read_text())) == 2
    assert json.loads((output / "manifest.json").read_text())["inputs"][1][
        "same_message_content_candidate"
    ]


def test_reused_message_id_with_other_content_fails_without_normalized_output(
    tmp_path, monkeypatch
):
    changed = change_header("Message-ID", "<report-ok@example.com>")
    args, output = cli_args(tmp_path, monkeypatch, [raw("ok"), changed])
    assert reader.main(args) == 1
    manifest = json.loads((output / "manifest.json").read_text())
    assert not manifest["ok"] and manifest["inputs"][1]["error"] == "message_id_conflict"
    assert not (output / "reports.json").exists()
    assert len(list(output.glob("input-*.eml"))) == 2


def test_cli_invalid_report_keeps_raw_and_fails(tmp_path, monkeypatch):
    changed = change_html(lambda html: html.replace("Data-source", "Changed-column", 1))
    args, output = cli_args(tmp_path, monkeypatch, [changed])
    assert reader.main(args) == 1
    assert (output / "input-001.eml").read_bytes() == changed
    manifest = json.loads((output / "manifest.json").read_text())
    assert not manifest["ok"] and manifest["inputs"][0]["error"] == "unit_columns"
    assert not (output / "unit-statuses.jsonl").exists()


def test_cli_rejects_public_output_before_creating_files(tmp_path, monkeypatch):
    args, output = cli_args(tmp_path, monkeypatch, [raw()])
    public = tmp_path / "public-output"
    args[args.index(str(output))] = str(public)
    assert reader.main(args) == 1
    assert not public.exists()


def test_size_limit_labels_incomplete_raw_copy(tmp_path, monkeypatch):
    args, output = cli_args(tmp_path, monkeypatch, [raw()])
    monkeypatch.setattr(reader, "MAX_BYTES", 100)
    assert reader.main(args) == 1
    manifest = json.loads((output / "manifest.json").read_text())
    assert not manifest["inputs"][0]["raw_copy_complete"]
    assert manifest["inputs"][0]["error"] == "input_size"
    assert (output / "input-001.prefix.bin").stat().st_size == 101
    assert not list(output.glob("input-*.eml"))
