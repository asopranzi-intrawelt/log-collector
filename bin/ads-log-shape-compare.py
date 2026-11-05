#!/usr/bin/env python3
"""Confronta due misure private di ads-log-shape per un cambio NAS.

Il confronto misura variazioni di forma e volume; non certifica identità del
dispositivo, completezza della ricezione o appartenenza degli account agli AdS.
L'output contiene indirizzi sorgente e resta nel livello privato del progetto.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
from pathlib import Path

MAX_REPORT_BYTES = 1024 * 1024
METRICS = (
    ("lines", None),
    ("bytes", None),
    ("unmatched_lines", None),
    ("qnap_connection_log", "markers"),
    ("qnap_event_log", "markers"),
    ("qnap_login_success", "markers"),
    ("qnap_login_failure", "markers"),
    ("qnap_admin_login_success", "correlations"),
    ("qnap_admin_login_failure", "correlations"),
    ("qnap_smb_login_success", "correlations"),
    ("qnap_smb_login_failure", "correlations"),
    ("qnap_admin_smb_overlap", "correlations"),
    ("qnap_login_without_context", "correlations"),
)


class IncompleteReport(ValueError):
    """Una fonte misurata non contiene un file utile per il confronto."""


def _day(value: object) -> dt.date:
    if not isinstance(value, str):
        raise ValueError("data assente")
    parsed = dt.date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("data non canonica")
    return parsed


def _count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("conteggio non valido")
    return value


def _read(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("report troppo grande")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or data.get("status") != "measured":
        raise ValueError("report non misurato")
    return data


def _source(report: dict, address: str) -> tuple[dt.date, dict]:
    day = _day(report.get("date"))
    wanted = str(ipaddress.IPv4Address(address))
    if wanted != address:
        raise ValueError("indirizzo sorgente non canonico")
    sources = report.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("fonti assenti")
    seen: set[str] = set()
    totals = {"files": 0, "lines": 0, "bytes": 0}
    selected = None
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("source"), str):
            raise ValueError("fonte non valida")
        name = str(ipaddress.IPv4Address(item["source"]))
        if name != item["source"] or name in seen:
            raise ValueError("fonte duplicata o non canonica")
        seen.add(name)
        present = item.get("file_present")
        if type(present) is not bool:
            raise ValueError("presenza file non valida")
        lines, size = _count(item.get("lines")), _count(item.get("bytes"))
        if not present and (lines or size):
            raise ValueError("file assente con contenuto")
        totals["files"] += present
        totals["lines"] += lines
        totals["bytes"] += size
        if name == wanted:
            selected = item
    if any(_count(report.get(key)) != value for key, value in totals.items()):
        raise ValueError("totali del report incoerenti")
    if selected is None or not selected["file_present"] or not selected["lines"]:
        raise IncompleteReport("fonte senza file giornaliero utile")
    for key, group in METRICS:
        bucket = selected if group is None else selected.get(group)
        if not isinstance(bucket, dict):
            raise ValueError("sezione dei marcatori assente")
        if _count(bucket.get(key)) > selected["lines"] and key != "bytes":
            raise ValueError("marcatore oltre il numero di righe")
    return day, selected


def compare(before: dict, after: dict, before_ip: str, after_ip: str,
            cutover: dt.date, today: dt.date | None = None) -> dict:
    before_day, old = _source(before, before_ip)
    after_day, new = _source(after, after_ip)
    if not before_day < cutover < after_day:
        raise ValueError("il confronto richiede un giorno intero prima e dopo il cambio")
    if after_day >= (today or dt.date.today()):
        raise ValueError("il giorno dopo il cambio non e ancora chiuso")
    metrics = {}
    for key, group in METRICS:
        previous = old[key] if group is None else old[group][key]
        current = new[key] if group is None else new[group][key]
        metrics[key] = {"before": previous, "after": current, "delta": current - previous}
    warnings = []
    if new["unmatched_lines"]:
        warnings.append("righe_senza_marcatori")
    if new["markers"]["qnap_connection_log"] + new["markers"]["qnap_event_log"] != new["lines"]:
        warnings.append("prefissi_qnap_non_coprono_le_righe")
    if new["correlations"]["qnap_login_without_context"]:
        warnings.append("login_senza_contesto")
    if new["correlations"]["qnap_admin_smb_overlap"]:
        warnings.append("contesti_sovrapposti")
    if not new["correlations"]["qnap_admin_login_success"]:
        warnings.append("nessun_login_amministrativo_riuscito_nel_giorno")
    return {
        "status": "compared_requires_review",
        "before_date": before_day.isoformat(),
        "after_date": after_day.isoformat(),
        "cutover_date": cutover.isoformat(),
        "before_source": before_ip,
        "after_source": after_ip,
        "metrics": metrics,
        "warnings": warnings,
        "manual_gates": [
            "identita_e_ora_di_sostituzione_verificate_sull_apparato",
            "prova_controllata_login_admin_riuscito_e_fallito",
            "prova_controllata_modifica_configurazione",
            "cinque_campi_AdsLine_e_orari_verificati_su_campioni_minimizzati",
            "trasporto_e_completezza_del_flusso_verificati_separatamente",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--source-before", required=True)
    parser.add_argument("--source-after", required=True)
    parser.add_argument("--cutover-date", required=True)
    options = parser.parse_args(argv)
    try:
        result = compare(
            _read(options.before), _read(options.after), options.source_before,
            options.source_after, _day(options.cutover_date),
        )
        code = 0
    except IncompleteReport:
        result, code = {"status": "incomplete"}, 2
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        result, code = {"status": "measurement_failed"}, 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
