"""Prove del controllo delle fonti fra repository locali."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "verifica-progetti-collegati.py"
spec = importlib.util.spec_from_file_location("verifica_progetti_collegati", SCRIPT)
assert spec is not None and spec.loader is not None
linked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linked)


class LinkedContextTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.base = Path(scratch.name)
        self.project = self.base / "project"
        self.source = self.base / "source"
        self.project.mkdir()
        self.source.mkdir()
        (self.project / "data").mkdir()
        (self.source / "docs").mkdir()
        (self.source / "docs" / "current.md").write_text(
            "riservato\n", encoding="utf-8"
        )
        self.manifest = {
            "schema": 1,
            "sources": [
                {
                    "name": "rete",
                    "root": str(self.source),
                    "branch": "main",
                    "paths": ["docs/*.md"],
                }
            ],
        }
        self._write_manifest()

    def _write_manifest(self) -> None:
        (self.project / linked.MANIFEST).write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def _git(self, root: Path, *args: str) -> str:
        if args[-1] == "--show-toplevel":
            return str(root)
        if args[-1] == "HEAD" and "--abbrev-ref" in args:
            return "main"
        return "0123456789ab"

    def test_content_change_with_same_size_and_mtime_is_reported(self) -> None:
        with mock.patch.object(linked, "_git", side_effect=self._git):
            baseline = linked.snapshot(self.project)
            target = self.source / "docs" / "current.md"
            before = target.stat()
            target.write_text("segreto!!\n", encoding="utf-8")
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            current = linked.snapshot(self.project)

        changes = linked.compare(current, baseline)
        self.assertEqual(changes, ["rete: docs/current.md cambiato/aggiunto/rimosso"])
        self.assertNotIn("segreto", "\n".join(changes))

    def test_windows_fd_ctime_difference_does_not_raise_false_alarm(self) -> None:
        target = self.source / "docs" / "current.md"
        actual_fstat = os.fstat

        def different_ctime(fd: int) -> types.SimpleNamespace:
            result = actual_fstat(fd)
            return types.SimpleNamespace(
                st_dev=result.st_dev,
                st_ino=result.st_ino,
                st_size=result.st_size,
                st_mtime_ns=result.st_mtime_ns,
                st_ctime_ns=result.st_ctime_ns + 1_000_000_000,
            )

        with mock.patch.object(linked.os, "fstat", side_effect=different_ctime):
            observed = linked._digest(target)
        expected = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assertEqual(observed, expected)

    def test_glob_detects_new_file(self) -> None:
        with mock.patch.object(linked, "_git", side_effect=self._git):
            baseline = linked.snapshot(self.project)
            (self.source / "docs" / "new.md").write_text("new\n", encoding="utf-8")
            current = linked.snapshot(self.project)

        self.assertIn(
            "rete: docs/new.md cambiato/aggiunto/rimosso",
            linked.compare(current, baseline),
        )

    def test_missing_source_cannot_be_acknowledged(self) -> None:
        self.manifest["sources"][0]["paths"] = ["docs/missing.md"]
        self._write_manifest()
        with mock.patch.object(linked, "_git", side_effect=self._git):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = linked.main(["--project", str(self.project), "--ack"])

        self.assertEqual(code, 2)
        self.assertIn("fonte non trovata", output.getvalue())
        self.assertFalse((self.project / linked.STATE).exists())

    def test_hook_reports_first_review_without_blocking_session(self) -> None:
        with mock.patch.object(linked, "_git", side_effect=self._git):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = linked.main(["--project", str(self.project), "--hook"])

        self.assertEqual(code, 0)
        self.assertIn("baseline assente", output.getvalue())
        self.assertNotIn("riservato", output.getvalue())


if __name__ == "__main__":
    unittest.main()
