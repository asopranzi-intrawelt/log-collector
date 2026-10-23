"""Receive one QA event into a restricted archive from a file or forced SSH command.

This command has no network listener. For SSH, the server fixes the source
identity in its forced command; the event's own claim never selects it.
"""

import argparse
import json
import os
import re
import shutil
import stat
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import qa_technical_boundary as boundary

PROJECT = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = boundary.MAX_BATCH_BYTES
MAX_ARCHIVE_ENTRY_BYTES = 2 * MAX_FILE_BYTES
PENDING_NAME = re.compile(r"\.pending-[0-9a-f]{32}\.json\Z")
MOUNTINFO = Path("/proc/self/mountinfo")


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


@contextmanager
def _archive_lock(path: Path):
    if os.name != "posix":
        yield
        return
    import fcntl

    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked = os.fstat(descriptor)
        current = path.stat()
        if (locked.st_dev, locked.st_ino) != (current.st_dev, current.st_ino):
            raise Rejected("archive_directory")
        if locked.st_uid != os.geteuid() or stat.S_IMODE(locked.st_mode) & 0o077:
            raise Rejected("archive_permissions")
        yield
    finally:
        os.close(descriptor)


def _archive_usage(path: Path) -> int:
    """Count published and abandoned pending bytes; reject unknown entries."""
    total = 0
    with os.scandir(path) as entries:
        for entry in entries:
            name = entry.name
            if not (
                name.endswith(".json") and boundary.EVENT_ID.fullmatch(name[:-5])
                or PENDING_NAME.fullmatch(name)
            ):
                raise Rejected("archive_entry")
            info = entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE_ENTRY_BYTES:
                raise Rejected("archive_entry")
            if os.name == "posix" and (
                info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise Rejected("archive_entry")
            total += info.st_size
    return total


def _require_archive_mount(path: Path) -> None:
    """Reject an SSH archive that fell back to its parent filesystem."""
    if not sys.platform.startswith("linux"):
        raise Rejected("linux_mount_required")
    try:
        mounts = MOUNTINFO.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise Rejected("mount_info") from exc
    target = str(path.resolve(strict=True))
    for line in mounts:
        fields = line.split(" - ", 1)[0].split()
        if len(fields) < 5:
            raise Rejected("mount_info")
        mounted = re.sub(
            r"\\([0-7]{3})", lambda match: chr(int(match.group(1), 8)), fields[4],
        )
        if mounted == target:
            return
    raise Rejected("archive_mount_missing")


def _existing(path: Path, digest: str, original: dict, technical: dict) -> dict:
    if path.is_symlink() or path.is_junction():
        raise Rejected("archive_entry")
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as entry:
            info = os.fstat(entry.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE_ENTRY_BYTES:
                raise Rejected("archive_entry")
            if os.name == "posix" and (
                info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise Rejected("archive_entry")
            data = entry.read(MAX_ARCHIVE_ENTRY_BYTES + 1)
        if len(data) > MAX_ARCHIVE_ENTRY_BYTES:
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


def receive(
    source: Path, archive: Path, source_id: str, environment: str, *,
    max_archive_bytes: int, min_free_bytes: int,
) -> dict:
    """Receive an offline file whose name matches the validated event ID."""
    archive = _archive_directory(archive)
    raw = _source_bytes(source)
    return receive_bytes(
        raw, archive, source_id, environment,
        max_archive_bytes=max_archive_bytes, min_free_bytes=min_free_bytes,
        source_name=source.name,
    )


def receive_bytes(
    raw: bytes, archive: Path, source_id: str, environment: str, *,
    max_archive_bytes: int, min_free_bytes: int, source_name: str | None = None,
    require_mount: bool = False,
) -> dict:
    """Validate, publish atomically, then acknowledge the exact source bytes."""
    if type(max_archive_bytes) is not int or max_archive_bytes <= 0:
        raise Rejected("archive_limit")
    if type(min_free_bytes) is not int or min_free_bytes <= 0:
        raise Rejected("free_space_limit")
    if type(raw) is not bytes or not raw or len(raw) > MAX_FILE_BYTES:
        raise Rejected("source_file")
    archive = _archive_directory(archive)
    try:
        checked = boundary.check_jsonl(raw, source_id, environment)
    except boundary.Rejected as exc:
        raise Rejected(str(exc)) from exc
    if len(checked) != 1:
        raise Rejected("single_event_required")
    event_id = checked[0]["record"]["event_id"]
    if source_name is not None and source_name != f"{event_id}.json":
        raise Rejected("source_name")
    destination = archive / f"{event_id}.json"
    digest = sha256(raw).hexdigest()
    original = json.loads(raw)
    technical = checked[0]
    with _archive_lock(archive):
        if require_mount:
            _require_archive_mount(archive)
        used = _archive_usage(archive)
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
        if used + len(payload) > max_archive_bytes:
            raise Rejected("archive_capacity")
        if shutil.disk_usage(archive).free < len(payload) + min_free_bytes:
            raise Rejected("free_space_reserve")
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
            _sync_directory(archive)


def _read_ssh_stdin(stream) -> bytes:
    if (os.environ.get("SSH_ORIGINAL_COMMAND") != "qa-tech-v1"
            or not os.environ.get("SSH_CONNECTION")):
        raise Rejected("ssh_command")
    raw = stream.read(MAX_FILE_BYTES + 1)
    if not raw or len(raw) > MAX_FILE_BYTES:
        raise Rejected("source_file")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event-file", type=Path)
    source.add_argument("--ssh-stdin", action="store_true")
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--environment", required=True, choices=("staging", "production"))
    parser.add_argument(
        "--max-archive-bytes", required=True, type=int,
        help="Logical byte limit for private archive entries",
    )
    parser.add_argument(
        "--min-free-bytes", required=True, type=int,
        help="Minimum available filesystem bytes after admitting one entry",
    )
    args = parser.parse_args()
    try:
        if os.name != "posix":
            raise Rejected("posix_required")
        if args.ssh_stdin:
            raw = _read_ssh_stdin(sys.stdin.buffer)
            receipt = receive_bytes(
                raw, args.archive_dir, args.source_id, args.environment,
                max_archive_bytes=args.max_archive_bytes, min_free_bytes=args.min_free_bytes,
                require_mount=True,
            )
        else:
            receipt = receive(
                args.event_file, args.archive_dir, args.source_id, args.environment,
                max_archive_bytes=args.max_archive_bytes, min_free_bytes=args.min_free_bytes,
            )
    except (Rejected, OSError) as exc:
        code = str(exc) if isinstance(exc, Rejected) else "io_error"
        print(f"rejected:{code}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
