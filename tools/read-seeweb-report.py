#!/usr/bin/env python3
"""Legge originali Seeweb in locale; produce stati per unità, non esiti di job.

Output soltanto nel livello privato _notes; nessuna rete o installazione VM.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from email import policy
from email.errors import MessageError
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 5_000_000  # Guardia interna, non limite del provider.
STATUSES = ("OK", "Warning", "Error", "Ignored issue", "Pending")
COLUMNS = (
    "Business unit",
    "Consumption unit",
    "Data-source",
    "Client version",
    "Server",
    "Status",
    "Issues",
    "Total storage (GB)",
    "Transferred (GB)",
)
UNIT_FIELDS = (
    "business_unit",
    "consumption_unit",
    "data_source",
    "client_version",
    "server",
    "status",
    "issues",
    "total_storage_gb",
    "transferred_gb",
)


class ReportError(ValueError):
    """Codice privo di contenuto o identificativi del messaggio."""


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = self.row = self.cell = None
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.suppressed += 1
        if self.suppressed:
            return
        if tag == "table":
            if self.table is not None:
                raise ReportError("nested_table")
            self.table = []
        elif self.table is not None:
            if tag == "tr":
                if self.row is not None:
                    raise ReportError("unclosed_row")
                self.row = []
            elif tag in ("td", "th"):
                if self.row is None or self.cell is not None:
                    raise ReportError("cell_structure")
                self.cell = []
            elif tag in ("li", "br", "p", "div") and self.cell is not None:
                self.cell.append("\n")

    def handle_data(self, value):
        if self.cell is not None and not self.suppressed:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.suppressed:
            self.suppressed -= 1
            return
        if self.suppressed:
            return
        if tag in ("td", "th"):
            if self.row is None or self.cell is None:
                raise ReportError("cell_structure")
            text = "\n".join(
                " ".join(line.split()) for line in "".join(self.cell).splitlines() if line.strip()
            )
            self.row.append(text)
            self.cell = None
        elif tag == "tr":
            if self.table is None or self.row is None or self.cell is not None:
                raise ReportError("row_structure")
            self.table.append(self.row)
            self.row = None
        elif tag == "table":
            if self.table is None or self.row is not None:
                raise ReportError("table_structure")
            self.tables.append(self.table)
            self.table = None


def decimal_gb(value):
    if not re.fullmatch(r"\d+,\d{2}", value):
        raise ReportError("decimal_format")
    return str(Decimal(value.replace(",", ".")))


def timestamp(value, code):
    try:
        point = parsedate_to_datetime(value)
        if point.utcoffset() is None:
            raise ValueError
        return point.isoformat()
    except (ValueError, TypeError, OverflowError) as exc:
        raise ReportError(code) from exc


def parse_report(raw, acquired_at=None, expected_sender=None):
    """Interpreta il formato osservato e conserva tutte le unità del report."""
    if len(raw) > MAX_BYTES:
        raise ReportError("input_size")
    acquired_at = acquired_at or datetime.now(UTC)
    if acquired_at.utcoffset() is None:
        raise ReportError("acquisition_timezone")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    for name in ("From", "Date", "Subject", "Message-ID"):
        if len(message.get_all(name, [])) != 1:
            raise ReportError("header_cardinality")
    try:
        senders = message["From"].addresses
        if len(senders) != 1 or not senders[0].username or not senders[0].domain:
            raise ValueError
        sender = senders[0].addr_spec
        if expected_sender is not None and sender.casefold() != expected_sender.casefold():
            raise ReportError("sender_mismatch")
        html_parts = [
            part
            for part in message.walk()
            if part.get_content_type() == "text/html"
            and part.get_content_disposition() != "attachment"
        ]
        if len(html_parts) != 1:
            raise ReportError("html_body_count")
        body = html_parts[0]
        html = body.get_content(errors="strict")
    except (ValueError, LookupError, AttributeError, MessageError) as exc:
        if isinstance(exc, ReportError):
            raise
        raise ReportError("mime_or_sender") from exc
    if any(part.defects for part in message.walk()):
        raise ReportError("mime_defects")
    mid = str(message["Message-ID"])
    if not re.fullmatch(r"<[^<>\s]+>", mid):
        raise ReportError("message_id")
    subject = str(message["Subject"])
    matched = re.fullmatch(
        r"Backup status report \(([^()]+)\): (.+) \((\d{4}-\d{2}-\d{2})\)", subject
    )
    if matched is None:
        raise ReportError("subject_format")
    declared_at = timestamp(str(message["Date"]), "message_date")
    if datetime.fromisoformat(declared_at).date().isoformat() != matched[3]:
        raise ReportError("report_date_mismatch")
    parser = Tables()
    parser.feed(html)
    parser.close()
    if parser.table is not None or parser.cell is not None or len(parser.tables) != 2:
        raise ReportError("tables_schema")
    overview, detail = parser.tables
    summary = {}
    volumes = {}
    for row in overview:
        if not any(row):
            continue
        if len(row) != 2:
            raise ReportError("overview_columns")
        label, value = row
        if (label, value) in (
            ("Storage type", "Total (GB)"),
            ("Transferred", "Total (GB)"),
            ("Status", "Total"),
        ):
            continue
        if label in (*STATUSES, "Total consumption units"):
            if label in summary or not re.fullmatch(r"\d+", value):
                raise ReportError("overview_counts")
            summary[label] = int(value)
        elif label in ("Primary data", "Archive data", "Total storage", "Transferred"):
            if label in volumes:
                raise ReportError("overview_volumes")
            volumes[label] = decimal_gb(value)
        else:
            raise ReportError("overview_label")
    if set(summary) != {*STATUSES, "Total consumption units"} or len(volumes) != 4:
        raise ReportError("overview_missing")
    if not detail or tuple(detail[0]) != COLUMNS:
        raise ReportError("unit_columns")
    units = []
    for row in detail[1:]:
        if not any(row):
            continue
        if len(row) != len(COLUMNS):
            raise ReportError("unit_columns")
        if not any(row[:7]):  # Riga totale distinta dalle unità reali.
            for value in row[7:]:
                decimal_gb(value)
            continue
        unit = dict(zip(UNIT_FIELDS, row, strict=True))
        if any(not unit[field] for field in UNIT_FIELDS[:6]) or unit["status"] not in STATUSES:
            raise ReportError("unit_field")
        unit["total_storage_gb"] = decimal_gb(unit["total_storage_gb"])
        unit["transferred_gb"] = decimal_gb(unit["transferred_gb"])
        unit["job_execution_time"] = None
        units.append(unit)
    identities = [
        (u["business_unit"], u["server"], u["data_source"], u["consumption_unit"]) for u in units
    ]
    if len(identities) != len(set(identities)):
        raise ReportError("duplicate_unit")
    counts = {key: summary[key] for key in STATUSES}
    total = summary["Total consumption units"]
    if total == 0 or total != len(units) or total != sum(counts.values()):
        raise ReportError("unit_count_mismatch")
    measured = Counter(unit["status"] for unit in units)
    if any(measured[key] != count for key, count in counts.items()):
        raise ReportError("status_count_mismatch")
    if (
        matched[1] not in STATUSES
        or (matched[1] == "OK" and counts["OK"] != total)
        or (matched[1] == "Error" and not counts["Error"])
    ):
        raise ReportError("subject_status_mismatch")
    received_headers = []
    for value in message.get_all("Received", []):
        if ";" not in value:
            raise ReportError("received_date")
        received_headers.append(timestamp(value.rsplit(";", 1)[1].strip(), "received_date"))
    return {
        "schema_version": 1,
        "source": "seeweb_cloud_backup_email",
        "archive": "backup_outcomes",
        "scope": "latest_status_per_consumption_unit_report_snapshot",
        "acquired_at": acquired_at.isoformat(),
        "declared_message_at": declared_at,
        "received_header_times": received_headers,
        "job_execution_time": None,
        "report_date": matched[3],
        "declared_report_status": matched[1],
        "sender": sender,
        "message_id": mid,
        "subject": subject,
        "source_eml_sha256": hashlib.sha256(raw).hexdigest(),
        "decoded_html_sha256": hashlib.sha256(body.get_payload(decode=True)).hexdigest(),
        "authentication_results_declared": message.get_all("Authentication-Results", []),
        "header_claims_revalidated": False,
        "attachment_count": sum(
            part.get_content_disposition() == "attachment" for part in message.walk()
        ),
        "counts": counts,
        "total_consumption_units": total,
        "overview_gb": volumes,
        "displayed_storage_delta_gb": str(
            Decimal(volumes["Total storage"]) - sum(Decimal(u["total_storage_gb"]) for u in units)
        ),
        "units": units,
    }


def write_private(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-config", type=Path, required=True)
    args = parser.parse_args(argv)
    output, observations, reports = args.output.resolve(), [], []
    try:
        if not output.is_relative_to(ROOT / "_notes") or output == ROOT / "_notes":
            raise ReportError("output_not_private")
        expected = json.loads(args.source_config.read_text(encoding="utf-8-sig"))["sender"]
        if not isinstance(expected, str) or not expected:
            raise ReportError("source_config")
        output.mkdir(parents=False, exist_ok=False)
        exact_sources = set()
        report_ids = {}
        exact_duplicates = 0
        for index, path in enumerate(args.input, 1):
            acquired = datetime.now(UTC)
            with path.open("rb") as handle:
                raw = handle.read(MAX_BYTES + 1)
            complete = len(raw) <= MAX_BYTES
            suffix = "eml" if complete else "prefix.bin"
            (output / f"input-{index:03}.{suffix}").write_bytes(raw)
            meta = {
                "index": index,
                "source_filename": path.name,
                "acquired_at": acquired.isoformat(),
                "bytes": len(raw),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_copy_complete": complete,
            }
            observations.append(meta)
            try:
                report = parse_report(raw, acquired, expected)
                identity = (report["sender"].casefold(), report["message_id"])
                content = (report["declared_message_at"], report["decoded_html_sha256"])
                if identity in report_ids and report_ids[identity] != content:
                    raise ReportError("message_id_conflict")
                if identity in report_ids:
                    meta["same_message_content_candidate"] = True
                report_ids[identity] = content
            except ReportError as exc:
                meta["error"] = str(exc)
                raise
            if report["source_eml_sha256"] in exact_sources:
                meta["byte_identical_duplicate"] = True
                exact_duplicates += 1
            else:
                exact_sources.add(report["source_eml_sha256"])
                reports.append(report)
        write_private(output / "reports.json", reports)
        records = [
            {
                "record_type": "backup_report_unit_status",
                "archive": report["archive"],
                "source": report["source"],
                "acquired_at": report["acquired_at"],
                "declared_at": report["declared_message_at"],
                "declared_at_kind": "email_date_header",
                "message_id": report["message_id"],
                "source_eml_sha256": report["source_eml_sha256"],
                **unit,
            }
            for report in reports
            for unit in report["units"]
        ]
        (output / "unit-statuses.jsonl").write_bytes(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records).encode("utf-8")
        )
        detail = (
            f"status=parsed reports={len(reports)} unit_statuses={len(records)} "
            f"byte_duplicates={exact_duplicates} "
            f"unit_errors={sum(r['counts']['Error'] for r in reports)} job_times=unavailable"
        )
        code = 0
    except ReportError as exc:
        detail, code = f"status=error code={exc}", 1
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        detail, code = "status=error code=local_input_or_schema", 1
    if observations:
        try:
            write_private(output / "manifest.json", {"ok": code == 0, "inputs": observations})
        except OSError:
            detail, code = "status=error code=manifest_write", 1
    stamp = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{stamp} email-check {stamp} seeweb-report {detail}")
    return code


if __name__ == "__main__":
    sys.exit(main())
