#!/usr/bin/env python3
"""Prepara il bundle privato Fluent Bit per un singolo pilota Windows."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adsparams  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "windows-pilota"
IDENTITY = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]{0,254})/([A-Za-z0-9._@-]{1,128})\Z")
HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}\Z")
COMPUTER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,62}\Z")
WINDOWS_PATH = re.compile(r"[A-Za-z]:/[A-Za-z0-9_./-]+\Z")


def event_query(accounts: list[tuple[str, str]]) -> str:
    """Seleziona l'account coinvolto come destinatario o come attore dell'evento."""
    target_ids = " or ".join(f"EventID={n}" for n in (4624, 4625, 4634, 4647, 4648))
    subject_ids = "EventID=4648 or EventID=4672"
    selects = [
        f'<Select Path="Security">*[(System[({target_ids})] and '
        f"EventData[Data[@Name='TargetUserName']='{user}' and "
        f"Data[@Name='TargetDomainName']='{domain}']) or "
        f"(System[({subject_ids})] and "
        f"EventData[Data[@Name='SubjectUserName']='{user}' and "
        f"Data[@Name='SubjectDomainName']='{domain}'])]</Select>"
        for domain, user in accounts
    ]
    global_ids = " or ".join(f"EventID={n}" for n in (1102, 4719, 4720, 4732, 4733))
    selects.append(f'<Select Path="Security">*[System[({global_ids})]]</Select>')
    return '<QueryList><Query Id="0" Path="Security">' + "".join(selects) + "</Query></QueryList>"


def _read_values(path: Path) -> tuple[str, list[tuple[str, str]]]:
    params = adsparams.load(path)
    host = adsparams.lookup(params, "collettore.fqdn")
    accounts = adsparams.lookup(params, "ads.elenco_approvato")
    if not isinstance(host, str) or not HOST.fullmatch(host) or ".." in host:
        raise ValueError("collettore.fqdn assente o non valido")
    if not isinstance(accounts, list) or not accounts:
        raise ValueError("ads.elenco_approvato vuoto: serve l'elenco approvato")
    identities = [IDENTITY.fullmatch(item) if isinstance(item, str) else None for item in accounts]
    if any(match is None for match in identities):
        raise ValueError("ads.elenco_approvato: usare DOMINIO/utente dai campi Security")
    pairs = [match.groups() for match in identities if match is not None]
    if len({(domain.casefold(), user.casefold()) for domain, user in pairs}) != len(pairs):
        raise ValueError("ads.elenco_approvato contiene duplicati")
    return host, pairs


def _safe_windows_path(value: str) -> bool:
    return (
        bool(WINDOWS_PATH.fullmatch(value))
        and ".." not in value.split("/")
        and not value.endswith("/")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parametri", required=True, type=Path)
    parser.add_argument("--computer-name", required=True)
    parser.add_argument("--destinazione", required=True, type=Path)
    parser.add_argument("--runtime-dir", default="C:/ProgramData/fluent-bit")
    parser.add_argument("--ca-file", default="C:/ProgramData/fluent-bit/conf/ca.pem")
    args = parser.parse_args(argv)
    destination = args.destinazione.resolve()
    if destination.is_relative_to(ROOT) and not destination.is_relative_to(ROOT / "_notes"):
        print("errore: il bundle con account reali va nel livello privato _notes", file=sys.stderr)
        return 1
    if destination.exists():
        print("errore: destinazione già esistente", file=sys.stderr)
        return 1
    if not COMPUTER.fullmatch(args.computer_name):
        print("errore: nome computer non valido", file=sys.stderr)
        return 1
    if not _safe_windows_path(args.runtime_dir) or not _safe_windows_path(args.ca_file):
        print("errore: percorso Windows non valido o contenente spazi", file=sys.stderr)
        return 1
    try:
        host, accounts = _read_values(args.parametri)
    except (adsparams.ParamsError, ValueError) as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1

    template = (SOURCE / "fluent-bit.conf.template").read_text(encoding="utf-8")
    values = {
        "@@EVENT_QUERY@@": event_query(accounts),
        "@@COLLECTOR_HOST@@": host,
        "@@COMPUTER_NAME@@": args.computer_name,
        "@@RUNTIME_DIR@@": args.runtime_dir,
        "@@CA_FILE@@": args.ca_file,
    }
    for token, value in values.items():
        template = template.replace(token, value)
    if "@@" in template:
        print("errore: segnaposto sconosciuto nel template", file=sys.stderr)
        return 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".windows-pilota-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        (staging / "fluent-bit.conf").write_text(template, encoding="utf-8", newline="\n")
        shutil.copyfile(SOURCE / "ads.lua", staging / "ads.lua")
        staging.rename(destination)
    except BaseException:
        if staging.resolve().is_relative_to(destination.parent.resolve()):
            shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"bundle candidato: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
