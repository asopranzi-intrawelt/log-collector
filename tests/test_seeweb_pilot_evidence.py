"""La prova Seeweb distingue ricezione tecnica, assenza e contaminazione AdS."""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "bin/ads-seeweb-pilot-evidence.py"
SPEC = importlib.util.spec_from_file_location("ads_seeweb_pilot_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SOURCE = "192.0.2.55"
START = "2026-10-30T19:00:00+01:00"
END = "2026-10-30T19:10:00+01:00"


@unittest.skipUnless(os.name == "posix", "la misura usa dir_fd e O_NOFOLLOW Linux")
class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.technical = self.root / "technical"
        self.ads = self.root / "ads"
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"source": SOURCE}), encoding="utf-8")

    def write_log(self, root: pathlib.Path, lines: list[str], day: str = "2026-10-30") -> None:
        directory = root / SOURCE
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{day}.log").write_text("".join(lines), encoding="utf-8")

    def report(self, start: str = START, end: str = END) -> dict[str, object]:
        return MODULE.measure(self.manifest, start, end, self.technical, self.ads)

    def test_eventi_tecnici_nella_finestra_senza_esporre_contenuto(self) -> None:
        self.write_log(self.technical, [
            f"2026-10-30T18:59:59+01:00 {SOURCE} ora host fuori-finestra\n",
            f"2026-10-30T19:01:00+01:00 {SOURCE} ora host GUI login utente\n",
            f"2026-10-30T19:03:00+01:00 {SOURCE} ora host SSH failed\n",
        ])
        report = self.report()
        self.assertEqual(report["status"], "observed")
        self.assertEqual(report["technical_events"], 2)
        self.assertEqual(report["ads_events"], 0)
        self.assertEqual(report["first_received"], "2026-10-30T19:01:00+01:00")
        self.assertNotIn(SOURCE, json.dumps(report))
        self.assertNotIn("utente", json.dumps(report))

    def test_assenza_non_diventa_prova_di_consegna(self) -> None:
        self.assertEqual(self.report()["status"], "not_observed")

    def test_riga_nell_archivio_ads_ferma_l_accettazione(self) -> None:
        line = f"2026-10-30T19:02:00+01:00 {SOURCE} ora host GUI login\n"
        self.write_log(self.technical, [line])
        self.write_log(self.ads, [line])
        report = self.report()
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["ads_events"], 1)

    def test_sorgente_incoerente_non_viene_contata(self) -> None:
        self.write_log(self.technical, [
            "2026-10-30T19:02:00+01:00 192.0.2.99 ora host evento\n",
        ])
        report = self.report()
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["technical_events"], 0)
        self.assertEqual(report["malformed_lines"], 1)

    def test_file_simbolico_non_viene_seguito(self) -> None:
        outside = self.root / "outside.log"
        outside.write_text(f"2026-10-30T19:02:00+01:00 {SOURCE} ora host evento\n")
        directory = self.technical / SOURCE
        directory.mkdir(parents=True)
        (directory / "2026-10-30.log").symlink_to(outside)
        with self.assertRaises(OSError):
            self.report()

    def test_fifo_non_blocca_la_misura(self) -> None:
        directory = self.technical / SOURCE
        directory.mkdir(parents=True)
        os.mkfifo(directory / "2026-10-30.log")
        with self.assertRaises(MODULE.MeasurementError):
            self.report()

    def test_file_oltre_limite_fallisce_la_misura(self) -> None:
        self.write_log(self.technical, [])
        file = self.technical / SOURCE / "2026-10-30.log"
        with file.open("wb") as stream:
            stream.truncate(MODULE.MAX_FILE_BYTES + 1)
        with self.assertRaises(MODULE.MeasurementError):
            self.report()

    def test_file_cresciuto_dopo_lo_stat_fallisce_la_misura(self) -> None:
        self.write_log(self.technical, [
            f"2026-10-30T19:02:00+01:00 {SOURCE} ora host evento\n",
        ])
        directory = self.technical / SOURCE
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fake_stat = SimpleNamespace(st_mode=0o100600, st_nlink=1, st_size=1)
            with patch.object(MODULE, "MAX_FILE_BYTES", 32):
                with patch.object(MODULE.os, "fstat", return_value=fake_stat):
                    with self.assertRaises(MODULE.MeasurementError):
                        MODULE.count_day(
                            descriptor, "2026-10-30", SOURCE,
                            MODULE.datetime.fromisoformat(START),
                            MODULE.datetime.fromisoformat(END),
                        )
        finally:
            os.close(descriptor)

    def test_due_giorni_alla_mezzanotte(self) -> None:
        import time

        self.write_log(self.technical, [
            f"2026-10-30T23:59:00+01:00 {SOURCE} ora host evento\n",
        ])
        self.write_log(self.technical, [
            f"2026-10-31T00:01:00+01:00 {SOURCE} ora host evento\n",
        ], day="2026-10-31")
        try:
            with patch.dict(os.environ, {"TZ": "UTC-1"}):
                time.tzset()
                report = self.report(
                    "2026-10-30T23:58:00+01:00", "2026-10-31T00:02:00+01:00"
                )
        finally:
            time.tzset()
        self.assertEqual(report["technical_events"], 2)

    def test_intervallo_naive_non_e_ammesso(self) -> None:
        with self.assertRaises(MODULE.MeasurementError):
            self.report("2026-10-30T19:00:00", "2026-10-30T19:10:00")

    def test_date_dei_file_seguono_il_fuso_del_collettore(self) -> None:
        import time

        try:
            with patch.dict(os.environ, {"TZ": "UTC"}):
                time.tzset()
                _, _, dates = MODULE.interval(
                    "2026-10-31T00:30:00+02:00", "2026-10-31T00:40:00+02:00"
                )
        finally:
            time.tzset()
        self.assertEqual(dates, ("2026-10-30",))

    def test_errori_di_lettura_non_diventano_assenza(self) -> None:
        with patch.object(MODULE, "measure", side_effect=PermissionError("privato")):
            with patch.object(MODULE, "print") as output:
                code = MODULE.main([
                    "--manifest", str(self.manifest), "--start", START, "--end", END,
                ])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output.call_args.args[0]), {"status": "measurement_failed"})


if __name__ == "__main__":
    unittest.main()
