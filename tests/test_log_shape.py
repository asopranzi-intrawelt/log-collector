"""Prove della ricognizione privata dei marcatori nei log AdS."""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "ads-log-shape.py"
DAY = dt.date(2026, 11, 3)
spec = importlib.util.spec_from_file_location("ads_log_shape", SCRIPT)
assert spec is not None and spec.loader is not None
shape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shape)


def _line(message: str) -> str:
    return (
        "2026-11-03T10:00:00+01:00 127.0.0.2 "
        f"2026-11-03T10:00:00+01:00 NAS-TEST {message}\n"
    )


@unittest.skipUnless(os.name == "posix", "apertura sicura POSIX")
class LogShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def test_admin_and_smb_markers_remain_distinct_without_raw_output(self) -> None:
        source = self.root / "127.0.0.2"
        source.mkdir()
        (self.root / "lost+found").mkdir()
        contents = "".join(
            (
                _line(
                    "conn log: Users: <account>, Accessed resources: Administration, "
                    "Action: Login Success"
                ),
                _line(
                    "conn log: Users: <account>, Connection type: SMB, "
                    "Accessed resources: SharedFolder"
                ),
                _line(
                    "event log: Category: Login and Security, "
                    "Failed to log in via user account <account>"
                ),
                _line("event log: Category: General, Content: service started"),
            )
        )
        (source / "2026-11-03.log").write_text(contents, encoding="utf-8")

        result = shape.scan(self.root, DAY)

        self.assertEqual(result["status"], "measured")
        self.assertEqual(result["files"], 1)
        self.assertEqual(result["lines"], 4)
        self.assertEqual(result["bytes"], len(contents.encode("utf-8")))
        report = result["sources"][0]
        self.assertEqual(report["markers"]["qnap_admin_resource"], 1)
        self.assertEqual(report["markers"]["qnap_smb_connection"], 1)
        self.assertEqual(report["markers"]["qnap_login_success"], 1)
        self.assertEqual(report["markers"]["qnap_login_failure"], 1)
        self.assertEqual(report["unmatched_lines"], 1)
        self.assertNotIn("<account>", json.dumps(result))
        self.assertNotIn("SharedFolder", json.dumps(result))

    def test_no_daily_file_is_reported_as_no_data(self) -> None:
        (self.root / "127.0.0.2").mkdir()

        result = shape.scan(self.root, DAY)

        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["files"], 0)
        self.assertFalse(result["sources"][0]["file_present"])

    def test_refuses_daily_symlink(self) -> None:
        source = self.root / "127.0.0.2"
        source.mkdir()
        target = source / "other.log"
        target.write_text(_line("secret-marker"), encoding="utf-8")
        (source / "2026-11-03.log").symlink_to(target)

        with self.assertRaises(OSError):
            shape.scan(self.root, DAY)

    def test_refuses_nonempty_lost_found(self) -> None:
        recovered = self.root / "lost+found"
        recovered.mkdir()
        (recovered / "entry").write_text("data", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "non vuota"):
            shape.scan(self.root, DAY)

    def test_file_changed_during_scan_fails(self) -> None:
        source = self.root / "127.0.0.2"
        source.mkdir()
        target = source / "2026-11-03.log"
        target.write_text(_line("event log: service started"), encoding="utf-8")
        original_fstat = os.fstat
        calls = 0

        def change_before_second_stat(descriptor: int) -> os.stat_result:
            nonlocal calls
            calls += 1
            if calls == 2:
                with target.open("ab") as stream:
                    stream.write(b"another line\n")
            return original_fstat(descriptor)

        with mock.patch.object(shape.os, "fstat", side_effect=change_before_second_stat):
            with self.assertRaisesRegex(ValueError, "file cambiato"):
                shape.scan(self.root, DAY)

    def test_cli_refuses_unmounted_root_without_path_or_content(self) -> None:
        (self.root / "127.0.0.2").mkdir()
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            code = shape.main(["--ads-root", str(self.root), "--date", DAY.isoformat()])

        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output.getvalue()), {"status": "measurement_failed"})
        self.assertNotIn(str(self.root), output.getvalue())


if __name__ == "__main__":
    unittest.main()
