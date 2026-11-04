#!/usr/bin/env python3
"""Segnala le fonti locali cambiate dall'ultima lettura approvata.

Il controllo non legge il contenuto nel report e non aggiorna la baseline da solo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
MANIFEST = Path("data/contesto-collegato.json")
STATE = Path("_notes/.contesto-collegato-state.json")
MAX_FILES = 128
MAX_BYTES = 16 * 1024 * 1024


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=5,
        check=False,
    )
    if result.returncode:
        raise ValueError("repository Git non leggibile")
    return result.stdout.strip()


def _digest(path: Path) -> str:
    before = path.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError("file oltre il limite di lettura")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        after = os.fstat(stream.fileno())
    after_path = path.stat()

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
        )
    if identity(before) != identity(after) or identity(before) != identity(after_path):
        raise ValueError(f"fonte cambiata durante la lettura: {path}")
    return digest.hexdigest()


def _files(root: Path, patterns: list[str]) -> dict[str, str]:
    root_real = root.resolve(strict=True)
    found: dict[str, str] = {}
    for pattern in patterns:
        parts = Path(pattern).parts
        if not pattern or Path(pattern).is_absolute() or ".." in parts or "\\" in pattern:
            raise ValueError("percorso sorvegliato non relativo")
        matches = sorted(root.glob(pattern))
        if not matches:
            raise ValueError(f"fonte non trovata: {pattern}")
        for path in matches:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"fonte non regolare: {pattern}")
            if not path.resolve(strict=True).is_relative_to(root_real):
                raise ValueError(f"fonte fuori dal repository: {pattern}")
            found[path.relative_to(root).as_posix()] = _digest(path)
            if len(found) > MAX_FILES:
                raise ValueError("troppe fonti sorvegliate")
    return found


def snapshot(project: Path) -> dict[str, object]:
    manifest_path = project / MANIFEST
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != 1 or not isinstance(manifest.get("sources"), list):
        raise ValueError("manifest non valido")
    sources: dict[str, object] = {}
    for source in manifest["sources"]:
        name = source["name"]
        if name in sources:
            raise ValueError("nome sorgente duplicato")
        root = Path(os.environ.get(source.get("env", ""), source["root"]))
        if not root.is_dir():
            raise ValueError(f"{name}: repository non raggiungibile")
        if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
            raise ValueError(f"{name}: radice Git diversa")
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
        if branch != source["branch"]:
            raise ValueError(f"{name}: ramo {branch}, atteso {source['branch']}")
        sources[name] = {
            "root": str(root.resolve()),
            "branch": branch,
            "head": _git(root, "rev-parse", "--short=12", "HEAD"),
            "files": _files(root, source["paths"]),
        }
    return {"schema": 1, "manifest": hashlib.sha256(manifest_bytes).hexdigest(), "sources": sources}


def compare(current: dict[str, object], previous: dict[str, object] | None) -> list[str]:
    if previous is None:
        result = ["baseline assente: leggere data/contesto-collegato.json, poi registrarla"]
        result.extend(
            f"{name}: {len(source['files'])} file sorvegliati"
            for name, source in current["sources"].items()
        )
        return result
    changes: list[str] = []
    if current["manifest"] != previous.get("manifest"):
        changes.append("manifest delle dipendenze modificato")
    old_sources = previous.get("sources", {})
    for name, source in current["sources"].items():
        old = old_sources.get(name)
        if (
            old is None
            or source["root"] != old.get("root")
            or source["branch"] != old.get("branch")
        ):
            changes.append(f"{name}: sorgente o ramo diverso")
            continue
        old_files = old.get("files", {})
        for path in sorted(set(source["files"]) | set(old_files)):
            if source["files"].get(path) != old_files.get(path):
                changes.append(f"{name}: {path} cambiato/aggiunto/rimosso")
        if source["head"] != old.get("head") and source["files"] == old_files:
            changes.append(f"{name}: HEAD cambiato, file sorvegliati invariati")
    for name in sorted(set(old_sources) - set(current["sources"])):
        changes.append(f"{name}: sorgente rimossa dal manifest")
    return changes


def _save(path: Path, current: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = stream.name
            json.dump(current, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--ack", action="store_true", help="registra dopo aver letto e riconciliato le fonti"
    )
    mode.add_argument("--hook", action="store_true", help="report non bloccante per SessionStart")
    options = parser.parse_args(argv)
    try:
        current = snapshot(options.project)
        state_path = options.project / STATE
        previous = (
            json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
        )
        changes = compare(current, previous)
        if options.ack:
            _save(state_path, current)
            print("CONTESTO_COLLEGATO: baseline registrata dopo la lettura delle fonti")
            return 0
        if changes:
            print("CONTESTO_COLLEGATO: fonti da verificare")
            for change in changes:
                print(f"  {change}")
            print("Leggere le fonti cambiate, aggiornare contesto e memoria, poi usare --ack.")
            return 0 if options.hook else 1
        print("CONTESTO_COLLEGATO: fonti sorvegliate invariate")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"CONTESTO_COLLEGATO: verifica non disponibile ({exc})")
        return 0 if options.hook else 2


if __name__ == "__main__":
    sys.exit(main())
