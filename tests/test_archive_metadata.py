import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "ads_archive_metadata", Path(__file__).resolve().parents[1] / "bin" / "ads-archive-metadata.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
TMP = Path(__file__).resolve().parents[1] / "_notes" / "tmp"


class ArchiveMetadataTests(unittest.TestCase):
    def test_reports_bytes_and_observed_span_without_claiming_continuity(self):
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            source = Path(tmp) / "192.0.2.10"
            source.mkdir()
            (source / "2026-11-01.log").write_bytes(b"a" * 5)
            (source / "2026-11-03.log").write_bytes(b"b" * 7)
            row = MODULE.measure(Path(tmp), date(2026, 11, 4), 4)["sources"][0]
            self.assertEqual(row["files_through"], 2)
            self.assertEqual(row["calendar_span_days"], 3)
            self.assertEqual(row["window_bytes"], 12)
            self.assertEqual(row["days_without_file_window"], ["2026-11-02", "2026-11-04"])

    def test_refuses_symlinked_daily_file(self):
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            source = Path(tmp) / "192.0.2.10"
            source.mkdir()
            outside = Path(tmp) / "secret"
            outside.write_text("do not read")
            try:
                (source / "2026-11-03.log").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "non regolare"):
                MODULE.measure(Path(tmp), date(2026, 11, 4), 2)

    def test_refuses_unmounted_root_when_required(self):
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            with self.assertRaisesRegex(ValueError, "non montato"):
                MODULE.measure(Path(tmp), date(2026, 11, 4), 2, require_mount=True)

    def test_refuses_current_day(self):
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            with self.assertRaisesRegex(ValueError, "giorno chiuso"):
                MODULE.measure(Path(tmp), date.today(), 2)


if __name__ == "__main__":
    unittest.main()
