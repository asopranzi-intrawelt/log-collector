#!/usr/bin/env python3
"""Genera l'albero di configurazione del collettore dai template e da parametri.yaml.

Percorre la cartella sorgente (per esempio ``config/collettore``) e riproduce l'albero nella
destinazione: i file ``*.template`` perdono il suffisso e hanno i segnaposto sostituiti, gli
altri si copiano come sono. Un segnaposto ha la forma ``{{ sezione.chiave }}``; la forma
``{{ a.b + c.d }}`` unisce più valori saltando quelli vuoti, e serve dove un valore è
facoltativo (la seconda subnet, oggi assente perché la LAN è unica). Una lista si scrive con
gli elementi separati da ``, ``, che è la sintassi degli insiemi di nftables.

Il rendering è tutto o niente: se anche un solo segnaposto resta senza valore, lo script elenca
tutti quelli mancanti, esce con 1 e non scrive nulla. La destinazione non deve esistere, così
un rendering non si mescola mai con uno precedente.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adsparams  # noqa: E402

PLACEHOLDER = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")
DOTTED = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
RSYSLOG_IP_MATCH = re.compile(r"^rsyslog_ip_match\(([^()]*)\)$")
NFT_UDP_SOURCE_RULE = re.compile(r"^nft_udp_source_rule\(([^()]*)\)$")
SUFFIX = ".template"
STRICT_RSYSLOG_PATH = Path("etc/rsyslog.d/10-ads.conf")
SYSLOG_SOURCE_KEYS = (
    "firewall_usg_flex",
    "nebula_switch_ap",
    "qnap",
    "ilo",
    "seeweb_opnsense",
    "proxmox_host",
    "windows_pilota",
)
ADS_SOURCE_KEYS = (
    "firewall_usg_flex",
    "nebula_switch_ap",
    "qnap",
    "proxmox_host",
    "windows_pilota",
)


def _values(value: adsparams.Value) -> list[str]:
    return value if isinstance(value, list) else [value]


def render_text(text: str, params: adsparams.Params, where: str, errors: list[str]) -> str:
    """Sostituisce i segnaposto di un testo; gli errori si accumulano in ``errors``."""

    def substitute(match: re.Match[str]) -> str:
        expr = match.group(1)
        if nft_rule := NFT_UDP_SOURCE_RULE.fullmatch(expr):
            key = nft_rule.group(1).strip()
            if not DOTTED.fullmatch(key):
                errors.append(f"{where}: chiave IP non valida {{{{ {expr} }}}}")
                return match.group(0)
            try:
                value = adsparams.lookup(params, key)
                addresses = [str(ipaddress.IPv4Address(item)) for item in _values(value) if item]
            except (adsparams.ParamsError, ValueError):
                errors.append(f"{where}: {key}: indirizzo IPv4 non valido")
                return match.group(0)
            return (
                "ip saddr { " + ", ".join(addresses) + " } udp dport 514 accept"
                if addresses
                else "# Sorgente Seeweb non ancora autorizzata"
            )
        if ip_match := RSYSLOG_IP_MATCH.fullmatch(expr):
            key = ip_match.group(1).strip()
            if not DOTTED.fullmatch(key):
                errors.append(f"{where}: chiave IP non valida {{{{ {expr} }}}}")
                return match.group(0)
            try:
                value = adsparams.lookup(params, key)
                addresses = [str(ipaddress.ip_address(item)) for item in _values(value) if item]
            except (adsparams.ParamsError, ValueError):
                errors.append(f"{where}: {key}: indirizzo IP non valido")
                return match.group(0)
            return (
                "(" + " or ".join(f"$fromhost-ip == {json.dumps(ip)}" for ip in addresses) + ")"
                if addresses
                else '($fromhost-ip == "0.0.0.0" and $fromhost-ip == "::")'
            )
        keys = [part.strip() for part in expr.split("+")]
        collected: list[str] = []
        for key in keys:
            if not DOTTED.match(key):
                errors.append(f"{where}: segnaposto non valido {{{{ {expr} }}}}")
                return match.group(0)
            try:
                value = adsparams.lookup(params, key)
            except adsparams.ParamsError as exc:
                errors.append(f"{where}: {exc}")
                return match.group(0)
            collected.extend(v for v in _values(value) if v != "")
        if not collected:
            errors.append(f"{where}: {' + '.join(keys)} vuoto in parametri.yaml, va compilato")
            return match.group(0)
        return ", ".join(collected)

    return PLACEHOLDER.sub(substitute, text)


def render_tree(source: Path, params: adsparams.Params) -> tuple[dict[Path, bytes], list[str]]:
    """Calcola in memoria i file di uscita, indicizzati per percorso relativo."""
    files: dict[Path, bytes] = {}
    errors: list[str] = []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source)
        if path.name.endswith(SUFFIX):
            text = path.read_text(encoding="utf-8")
            out = render_text(text, params, rel.as_posix(), errors)
            files[rel.with_name(path.name[: -len(SUFFIX)])] = out.encode("utf-8")
        else:
            files[rel] = path.read_bytes()
    return files, errors


def strict_syslog_addresses(params: adsparams.Params) -> list[str]:
    """Valida tutte le classi Syslog; restituisce gli IP ammessi nel flusso AdS."""
    seen: dict[str, str] = {}
    by_key: dict[str, list[str]] = {}
    for key in SYSLOG_SOURCE_KEYS:
        value = adsparams.lookup(params, f"sorgenti.{key}")
        addresses = [] if value == "" else _values(value)
        by_key[key] = []
        for item in addresses:
            try:
                address = str(ipaddress.IPv4Address(item))
            except ValueError:
                raise adsparams.ParamsError(
                    f"sorgenti.{key}: indirizzo IPv4 non valido"
                ) from None
            if address in seen:
                raise adsparams.ParamsError(
                    f"sorgenti.{key}: indirizzo duplicato in sorgenti.{seen[address]}"
                )
            seen[address] = key
            by_key[key].append(address)
    allowed = [address for key in ADS_SOURCE_KEYS for address in by_key[key]]
    if not allowed:
        raise adsparams.ParamsError(
            "--strict-syslog-sources: elenco delle sorgenti AdS vuoto"
        )
    return allowed


def strict_rsyslog_conf(conf: str, addresses: list[str]) -> str:
    """Sostituisce solo il fallback di rete e isola gli accessi locali.

    Le ancore esatte fanno fallire il rendering se il template cambia: la modalita'
    strict non deve mai ricadere inavvertitamente nel catch-all originale.
    """
    old_fallback = '''    } else {
        action(type="omfile" dynaFile="AdsFile" template="AdsLine"
               fileOwner="root" fileGroup="ads" fileCreateMode="0640"
               dirOwner="root" dirGroup="ads" dirCreateMode="0750")
    }
}

input(type="imudp"'''
    match = " or ".join(f"$fromhost-ip == {json.dumps(ip)}" for ip in addresses)
    new_fallback = f'''    }} else if ({match}) then {{
        action(type="omfile" dynaFile="AdsFile" template="AdsLine"
               fileOwner="root" fileGroup="ads" fileCreateMode="0640"
               dirOwner="root" dirGroup="ads" dirCreateMode="0750")
    }} else {{
        action(type="omfile" dynaFile="AdsUnclassifiedFile" template="AdsLine"
               fileOwner="root" fileGroup="root" fileCreateMode="0640"
               dirOwner="root" dirGroup="root" dirCreateMode="0750")
    }}
}}

# Gli accessi al collettore restano AdS anche quando l'IP locale non e' una sorgente di rete.
ruleset(name="ads-local") {{
    if $protocol-version == "1" then {{
        set $!ads_msg = $syslogtag & " " & $msg;
    }} else {{
        set $!ads_msg = $syslogtag & $msg;
    }}
    action(type="omfile" dynaFile="AdsFile" template="AdsLine"
           fileOwner="root" fileGroup="ads" fileCreateMode="0640"
           dirOwner="root" dirGroup="ads" dirCreateMode="0750")
}}

input(type="imudp"'''
    local_call = "    call ads\n}"
    if conf.count(old_fallback) != 1 or conf.count(local_call) != 1:
        raise adsparams.ParamsError(
            "10-ads.conf: struttura del fallback cambiata; strict non generato"
        )
    conf = conf.replace(old_fallback, new_fallback, 1)
    conf = conf.replace(local_call, "    call ads-local\n}", 1)
    declaration = (
        'template(name="AdsSeewebTechnicalFile" type="string" '
        'string="/var/log/ads-seeweb-technical/%fromhost-ip%/'
        '%$year%-%$month%-%$day%.log")'
    )
    if conf.count(declaration) != 1:
        raise adsparams.ParamsError(
            "10-ads.conf: template tecnico Seeweb cambiato; strict non generato"
        )
    conf = conf.replace(
        declaration,
        declaration + '\n# Quarantena tecnica per le sorgenti di rete non censite.\n'
        'template(name="AdsUnclassifiedFile" type="string" '
        'string="/var/log/ads-unclassified/%fromhost-ip%/'
        '%$year%-%$month%-%$day%.log")',
        1,
    )
    return conf


def write_tree(files: dict[Path, bytes], destination: Path) -> None:
    """Scrive in una cartella temporanea accanto alla destinazione e la rinomina alla fine."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".ads-render-", dir=destination.parent))
    try:
        for rel, data in files.items():
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parametri", required=True, type=Path, help="percorso di parametri.yaml")
    parser.add_argument("--sorgente", required=True, type=Path, help="cartella dei template")
    parser.add_argument("--destinazione", required=True, type=Path, help="cartella da creare")
    parser.add_argument(
        "--strict-syslog-sources",
        action="store_true",
        help="isola in un archivio tecnico le sorgenti Syslog di rete non censite",
    )
    args = parser.parse_args(argv)

    if not args.sorgente.is_dir():
        print(f"errore: {args.sorgente} non è una cartella", file=sys.stderr)
        return 1
    if args.destinazione.exists():
        print(
            f"errore: {args.destinazione} esiste già, rimuoverla o sceglierne un'altra",
            file=sys.stderr,
        )
        return 1
    try:
        params = adsparams.load(args.parametri)
    except adsparams.ParamsError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1

    addresses: list[str] = []
    if args.strict_syslog_sources:
        try:
            addresses = strict_syslog_addresses(params)
        except adsparams.ParamsError as exc:
            print(f"errore: {exc}", file=sys.stderr)
            return 1

    files, errors = render_tree(args.sorgente, params)
    if args.strict_syslog_sources and not errors:
        try:
            if STRICT_RSYSLOG_PATH not in files:
                raise adsparams.ParamsError(
                    "10-ads.conf assente: strict richiede l'albero collettore"
                )
            strict = strict_rsyslog_conf(
                files[STRICT_RSYSLOG_PATH].decode("utf-8"), addresses
            )
            files[STRICT_RSYSLOG_PATH] = strict.encode("utf-8")
        except adsparams.ParamsError as exc:
            errors.append(str(exc))
    if errors:
        for line in errors:
            print(f"errore: {line}", file=sys.stderr)
        print(f"{len(errors)} segnaposto senza valore, nessun file scritto", file=sys.stderr)
        return 1
    write_tree(files, args.destinazione)
    print(f"{len(files)} file scritti in {args.destinazione}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
