"""Receive one QA outbox file into a restricted offline archive.

This command has no network listener. The expected source identity must come
from a future authenticated transport, not from the event's own claim.
"""

import argparse
import json
import os
import stat
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import qa_technical_boundary as boundary

PROJECT = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = boundary.MAX_BATCH_BYTES


class Rejected(ValueError):
    """A stable error code that never contains input bytes."""


def _archive_directory(path: Path) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink() or path.is_junction():
        raise Rejected("archive_directory")
    resolved = path.resolve(strict=True)
    if resolved.is_relative_to(PROJECT):
        raise Rejected("archive_inside_repository")
    if os.name == "posix":
        info = path.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise Rejected("archive_permissions")
    return path


def _source_bytes(path: Path) -> bytes:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise Rejected("source_file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise Rejected("source_file")
        raw = source.read(MAX_FILE_BYTES + 1)
    if not raw or len(raw) > MAX_FILE_BYTES:
        raise Rejected("source_file")
    return raw


def _sync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _existing(path: Path, digest: str, original: dict, technical: dict) -> dict:
    if path.is_symlink() or path.is_junction():
        raise Rejected("archive_entry")
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as entry:
            info = os.fstat(entry.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 2 * MAX_FILE_BYTES:
                raise Rejected("archive_entry")
            if os.name == "posix" and (
                info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise Rejected("archive_entry")
            data = entry.read(2 * MAX_FILE_BYTES + 1)
        if len(data) > 2 * MAX_FILE_BYTES:
            raise Rejected("archive_entry")
        stored = json.loads(data)
    except (OSError, ValueError) as exc:
        raise Rejected("archive_entry") from exc
    if type(stored) is not dict or stored.get("sha256") != digest:
        raise Rejected("event_id_collision")
    if stored.get("original") != original or stored.get("technical") != technical:
        raise Rejected("archive_entry")
    _sync_directory(path.parent)
    return {"status": "duplicate", "event_id": path.stem, "sha256": digest}


def receive(source: Path, archive: Path, source_id: str, environment: str) -> dict:
    """Validate, publish atomically, then acknowledge the exact source bytes."""
    archive = _archive_directory(archive)
    raw = _source_bytes(source)
    try:
        checked = boundary.check_jsonl(raw, source_id, environment)
    except boundary.Rejected as exc:
        raise Rejected(str(exc)) from exc
    if len(checked) != 1:
        raise Rejected("single_event_required")
    event_id = checked[0]["record"]["event_id"]
    if source.name != f"{event_id}.json":
        raise Rejected("source_name")
    destination = archive / f"{event_id}.json"
    digest = sha256(raw).hexdigest()
    original = json.loads(raw)
    technical = checked[0]
    if destination.exists() or destination.is_symlink():
        return _existing(destination, digest, original, technical)
    envelope = {
        "received_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": digest,
        "original": original,
        "technical": technical,
    }
    payload = (
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    pending = archive / f".pending-{uuid4().hex}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        with os.fdopen(os.open(pending, flags, 0o600), "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(pending, destination)
        except FileExistsError:
            return _existing(destination, digest, original, technical)
        _sync_directory(archive)
        return {"status": "stored", "event_id": event_id, "sha256": digest}
    finally:
        pending.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True, type=Path)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--environment", required=True, choices=("staging", "production"))
    args = parser.parse_args()
    try:
        receipt = receive(args.event_file, args.archive_dir, args.source_id, args.environment)
    except (Rejected, OSError) as exc:
        code = str(exc) if isinstance(exc, Rejected) else "io_error"
        print(f"rejected:{code}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
