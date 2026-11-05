"""Prove del confronto fra misure NAS prima e dopo una sostituzione."""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "ads-log-shape-compare.py"
spec = importlib.util.spec_from_file_location("ads_log_shape_compare", SCRIPT)
assert spec is not None and spec.loader is not None
shape_compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shape_compare)
PRODUCER = SCRIPT.with_name("ads-log-shape.py")
producer_spec = importlib.util.spec_from_file_location("ads_log_shape", PRODUCER)
assert producer_spec is not None and producer_spec.loader is not None
producer = importlib.util.module_from_spec(producer_spec)
producer_spec.loader.exec_module(producer)

SOURCE = "192.0.2.10"
CUTOVER = dt.date(2026, 11, 6)
TODAY = dt.date(2026, 11, 8)


def report(day: str, *, present: bool = True, lines: int = 10) -> dict:
    count = lines if present else 0
    source = producer._empty_source(SOURCE)
    source.update({"file_present": present, "lines": count, "bytes": count * 50})
    source["markers"].update({
        "qnap_connection_log": count - 1 if present else 0,
        "qnap_event_log": 1 if present else 0,
        "qnap_login_success": 2 if present else 0,
        "qnap_login_failure": 1 if present else 0,
    })
    source["correlations"].update({
        "qnap_admin_login_success": 1 if present else 0,
        "qnap_smb_login_success": 1 if present else 0,
        "qnap_smb_login_failure": 1 if present else 0,
    })
    return {
        "status": "measured",
        "date": day,
        "sources": [source],
        "files": int(present),
        "lines": count,
        "bytes": count * 50,
    }


class CompareTests(unittest.TestCase):
    def test_real_day_gate_and_delta_do_not_claim_admissibility(self) -> None:
        before = report("2026-11-03")
        after = report("2026-11-07", lines=12)

        result = shape_compare.compare(before, after, SOURCE, SOURCE, CUTOVER, TODAY)

        self.assertEqual(result["status"], "compared_requires_review")
        self.assertEqual(result["metrics"]["lines"], {"before": 10, "after": 12, "delta": 2})
        self.assertEqual(result["metrics"]["qnap_admin_login_success"]["after"], 1)
        self.assertIn(
            "identita_e_ora_di_sostituzione_verificate_sull_apparato", result["manual_gates"]
        )

    def test_absent_new_day_cannot_look_like_zero_activity(self) -> None:
        after = report("2026-11-07", present=False)
        with self.assertRaises(shape_compare.IncompleteReport):
            shape_compare.compare(report("2026-11-03"), after, SOURCE, SOURCE, CUTOVER, TODAY)

    def test_partial_or_same_day_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "giorno intero"):
            shape_compare.compare(
                report("2026-11-03"), report("2026-11-06"), SOURCE, SOURCE, CUTOVER, TODAY
            )

    def test_open_day_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non e ancora chiuso"):
            shape_compare.compare(
                report("2026-11-03"), report("2026-11-07"), SOURCE, SOURCE,
                CUTOVER, dt.date(2026, 11, 7),
            )

    def test_drift_is_visible_even_when_report_is_measured(self) -> None:
        after = report("2026-11-07")
        source = after["sources"][0]
        source["unmatched_lines"] = 1
        source["markers"]["qnap_event_log"] = 0
        source["correlations"]["qnap_admin_login_success"] = 0

        result = shape_compare.compare(
            report("2026-11-03"), after, SOURCE, SOURCE, CUTOVER, TODAY
        )

        self.assertIn("righe_senza_marcatori", result["warnings"])
        self.assertIn("prefissi_qnap_non_coprono_le_righe", result["warnings"])
        self.assertIn("nessun_login_amministrativo_riuscito_nel_giorno", result["warnings"])

    def test_cli_rejects_incoherent_totals_without_echoing_private_data(self) -> None:
        after = report("2026-11-07")
        after["lines"] = 9
        after["private_account"] = "secret-account"
        output = io.StringIO()

        with mock.patch.object(shape_compare, "_read", side_effect=[report("2026-11-03"), after]):
            with contextlib.redirect_stdout(output):
                code = shape_compare.main([
                    "--before", "before.json", "--after", "after.json",
                    "--source-before", SOURCE, "--source-after", SOURCE,
                    "--cutover-date", CUTOVER.isoformat(),
                ])

        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output.getvalue()), {"status": "measurement_failed"})
        self.assertNotIn("secret-account", output.getvalue())


if __name__ == "__main__":
    unittest.main()
