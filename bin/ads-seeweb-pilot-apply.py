#!/usr/bin/env python3
"""Installa il solo pilota Seeweb da un bundle privato ancorato al live."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import signal
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime

FILES = {
    "candidate-10-ads.conf": pathlib.Path("/etc/rsyslog.d/10-ads.conf"),
    "candidate-nftables.conf": pathlib.Path("/etc/nftables.conf"),
}
BACKUP_ROOT = pathlib.Path("/var/backups/ads-seeweb-pilot")
LOCK = pathlib.Path("/run/lock/ads-seeweb-pilot.lock")


class PilotError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(*command: str) -> None:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        raise PilotError(f"comando fallito: {command[0]} ({result.returncode})")


def check_local_destination(address: str) -> None:
    result = subprocess.run(("ip", "-j", "-4", "addr", "show"), capture_output=True)
    if result.returncode:
        raise PilotError("indirizzi locali non leggibili")
    interfaces = json.loads(result.stdout)
    addresses = {
        item["local"]
        for interface in interfaces
        for item in interface.get("addr_info", [])
        if item.get("family") == "inet"
    }
    if address not in addresses:
        raise PilotError("destinazione del manifesto diversa da questa VM")


def check_nft_tables() -> None:
    result = subprocess.run(("nft", "-j", "list", "tables"), capture_output=True)
    if result.returncode:
        raise PilotError("tabelle nftables attive non leggibili")
    listing = json.loads(result.stdout)
    tables = {
        (entry["table"]["family"], entry["table"]["name"])
        for entry in listing.get("nftables", [])
        if "table" in entry
    }
    if tables != {("inet", "filter")}:
        raise PilotError("tabelle nftables diverse dal baseline del pilota")


def regular_file(path: pathlib.Path) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise PilotError(f"file non regolare: {path.name}")
    return info


def load_bundle(bundle: pathlib.Path, targets: dict[str, pathlib.Path]) -> dict:
    regular_file(bundle / "manifest.json")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if set(manifest.get("files", {})) != set(targets):
        raise PilotError("manifesto: insieme dei file inatteso")
    ipaddress.IPv4Address(manifest["source"])
    ipaddress.IPv4Address(manifest["destination"])
    for name, target in targets.items():
        entry = manifest["files"][name]
        if set(entry) != {"sha256", "live_sha256"}:
            raise PilotError(f"manifesto incompleto: {name}")
        regular_file(bundle / name)
        regular_file(target)
        if digest((bundle / name).read_bytes()) != entry["sha256"]:
            raise PilotError(f"impronta candidata diversa: {name}")
        if (bundle / name).read_text(encoding="utf-8").count(manifest["source"]) != 1:
            raise PilotError(f"mittente assente o duplicato: {name}")
        if digest(target.read_bytes()) != entry["live_sha256"]:
            raise PilotError(f"impronta live diversa: {target.name}")
    return manifest


def check(bundle: pathlib.Path, targets: dict[str, pathlib.Path]) -> dict:
    manifest = load_bundle(bundle, targets)
    check_local_destination(manifest["destination"])
    check_nft_tables()
    run("nft", "-c", "-f", str(bundle / "candidate-nftables.conf"))
    run("rsyslogd", "-N1", "-f", str(bundle / "candidate-10-ads.conf"))
    run("systemctl", "is-active", "--quiet", "rsyslog")
    run("systemctl", "is-active", "--quiet", "nftables")
    return manifest


def replace_file(path: pathlib.Path, data: bytes, info: os.stat_result) -> None:
    regular_file(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), stat.S_IMODE(info.st_mode))
            os.fchown(stream.fileno(), info.st_uid, info.st_gid)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup_current(
    targets: dict[str, pathlib.Path], root: pathlib.Path, manifest: dict
) -> tuple[pathlib.Path, dict]:
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise PilotError("directory backup non valida")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_uid != 0:
        raise PilotError("directory backup non di root")
    os.chmod(root, 0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root / stamp
    backup.mkdir(mode=0o700)
    originals = {}
    for name, target in targets.items():
        info = regular_file(target)
        data = target.read_bytes()
        copy = backup / name
        with copy.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(copy, 0o600)
        originals[name] = {"data": data, "stat": info}
    metadata = {
        name: {
            "sha256": digest(originals[name]["data"]),
            "mode": stat.S_IMODE(originals[name]["stat"].st_mode),
            "uid": originals[name]["stat"].st_uid,
            "gid": originals[name]["stat"].st_gid,
        }
        for name in targets
    }
    for name, content in (
        ("metadata.json", metadata),
        ("manifest.json", manifest),
    ):
        with (backup / name).open("w", encoding="utf-8") as stream:
            json.dump(content, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(backup / name, 0o600)
    directory_fd = os.open(backup, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return backup, originals


def apply(
    bundle: pathlib.Path, targets: dict[str, pathlib.Path], backup_root: pathlib.Path
) -> pathlib.Path:
    manifest = check(bundle, targets)
    backup, originals = backup_current(targets, backup_root, manifest)
    changed: list[str] = []
    try:
        for name, service in (
            ("candidate-10-ads.conf", "rsyslog"),
            ("candidate-nftables.conf", "nftables"),
        ):
            target = targets[name]
            if digest(target.read_bytes()) != manifest["files"][name]["live_sha256"]:
                raise PilotError(f"live cambiato durante il pilot: {target.name}")
            regular_file(bundle / name)
            candidate = (bundle / name).read_bytes()
            if digest(candidate) != manifest["files"][name]["sha256"]:
                raise PilotError(f"candidato cambiato durante il pilot: {name}")
            changed.append(name)
            replace_file(target, candidate, originals[name]["stat"])
            if service == "rsyslog":
                run("rsyslogd", "-N1")
                run("systemctl", "restart", "rsyslog")
            else:
                run("nft", "-f", str(target))
            run("systemctl", "is-active", "--quiet", service)
        for name, target in targets.items():
            if digest(target.read_bytes()) != manifest["files"][name]["sha256"]:
                raise PilotError(f"candidato alterato dopo installazione: {target.name}")
    except BaseException as error:
        failures = []
        for name in reversed(changed):
            target = targets[name]
            try:
                replace_file(target, originals[name]["data"], originals[name]["stat"])
                if name == "candidate-nftables.conf":
                    run("nft", "-f", str(target))
                else:
                    run("systemctl", "restart", "rsyslog")
            except (OSError, PilotError) as rollback_error:
                failures.append(f"{target.name}: {rollback_error}")
        if failures:
            raise PilotError(f"ripristino incompleto ({backup}): {'; '.join(failures)}") from error
        raise PilotError(
            f"installazione fallita; ripristino eseguito ({backup}): {error}"
        ) from error
    return backup


def rollback(
    backup_root: pathlib.Path, backup_id: str, targets: dict[str, pathlib.Path]
) -> pathlib.Path:
    if not re.fullmatch(r"\d{8}T\d{12}Z", backup_id):
        raise PilotError("identificativo backup non valido")
    backup = backup_root / backup_id
    if backup.is_symlink() or not backup.is_dir() or backup.stat().st_uid != 0:
        raise PilotError("backup assente o non protetto")
    regular_file(backup / "manifest.json")
    regular_file(backup / "metadata.json")
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    metadata = json.loads((backup / "metadata.json").read_text(encoding="utf-8"))
    if set(manifest.get("files", {})) != set(targets) or set(metadata) != set(targets):
        raise PilotError("backup incompleto")
    check_local_destination(manifest["destination"])
    check_nft_tables()
    before = {}
    for name, target in targets.items():
        info = regular_file(target)
        current = target.read_bytes()
        regular_file(backup / name)
        baseline = (backup / name).read_bytes()
        expected = manifest["files"][name]
        fields = metadata[name]
        if digest(current) != expected["sha256"]:
            raise PilotError(f"live diverso dal pilota: {target.name}")
        if digest(baseline) != expected["live_sha256"] or digest(baseline) != fields["sha256"]:
            raise PilotError(f"backup alterato: {name}")
        if not all(isinstance(fields[key], int) for key in ("mode", "uid", "gid")):
            raise PilotError(f"metadata backup non validi: {name}")
        if not 0 <= fields["mode"] <= 0o777 or fields["uid"] < 0 or fields["gid"] < 0:
            raise PilotError(f"metadata backup non validi: {name}")
        old_info = os.stat_result(
            (fields["mode"], 0, 0, 0, fields["uid"], fields["gid"], 0, 0, 0, 0)
        )
        before[name] = {
            "current": current, "info": info, "baseline": baseline, "old_info": old_info
        }
    changed: list[str] = []
    try:
        for name, service in (
            ("candidate-10-ads.conf", "rsyslog"),
            ("candidate-nftables.conf", "nftables"),
        ):
            target = targets[name]
            if digest(target.read_bytes()) != manifest["files"][name]["sha256"]:
                raise PilotError(f"live cambiato durante il ripristino: {target.name}")
            changed.append(name)
            replace_file(target, before[name]["baseline"], before[name]["old_info"])
            if service == "rsyslog":
                run("rsyslogd", "-N1")
                run("systemctl", "restart", "rsyslog")
            else:
                run("nft", "-f", str(target))
            run("systemctl", "is-active", "--quiet", service)
    except BaseException as error:
        failures = []
        for name in reversed(changed):
            target = targets[name]
            try:
                replace_file(target, before[name]["current"], before[name]["info"])
                if name == "candidate-nftables.conf":
                    run("nft", "-f", str(target))
                else:
                    run("systemctl", "restart", "rsyslog")
            except (OSError, PilotError) as recovery_error:
                failures.append(f"{target.name}: {recovery_error}")
        if failures:
            raise PilotError(
                f"ripristino incompleto ({backup}): {'; '.join(failures)}"
            ) from error
        raise PilotError(f"ripristino fallito; pilota reintegrato ({backup}): {error}") from error
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=pathlib.Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    action.add_argument("--rollback", metavar="BACKUP_ID")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise PilotError("eseguire come root sulla VM")

    def stop(_signum: int, _frame: object) -> None:
        raise PilotError("interruzione ricevuta")

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with LOCK.open("a+") as lock:
        os.chmod(LOCK, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.rollback:
            backup = rollback(BACKUP_ROOT, args.rollback, FILES)
            print(f"Baseline ripristinato dal backup: {backup}")
        elif args.check:
            if args.bundle is None:
                raise PilotError("--bundle obbligatorio per il controllo")
            check(args.bundle, FILES)
            print("Pilota Seeweb pronto; nessuna modifica")
        else:
            if args.bundle is None:
                raise PilotError("--bundle obbligatorio per l'applicazione")
            backup = apply(args.bundle, FILES, BACKUP_ROOT)
            print(f"Pilota Seeweb applicato; backup: {backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, PilotError) as exc:
        print(f"Pilota Seeweb fermato: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
