#!/usr/bin/env python3
"""Raccoglie l'iLO Event Log via Redfish senza perdere gli incrementi di Count.

Un'istanza gestisce un solo indirizzo iLO. Il file di stato viene aggiornato solo dopo
aver scritto e sincronizzato le righe: un'interruzione può ripetere una riga, ma non
far avanzare lo stato oltre una riga mai scritta. Id, Created e Count nella riga
permettono di riconoscere un'eventuale ripetizione.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import stat
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter

ENTRIES = "/redfish/v1/Managers/1/LogServices/IEL/Entries/"
SESSIONS = "/redfish/v1/SessionService/Sessions/"
TIMEOUT = (5, 20)


class PollError(Exception):
    """Risposta Redfish, stato o configurazione non utilizzabile."""


class FingerprintAdapter(HTTPAdapter):
    """Verifica l'impronta SHA-256 durante ogni handshake TLS del pool HTTP."""

    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["assert_fingerprint"] = self.fingerprint
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def read_fingerprint(path: Path) -> str:
    value = path.read_text(encoding="ascii").strip().replace(":", "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise PollError("impronta SHA-256 iLO non valida")
    return value


def read_password(path: Path) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    if os.name == "posix" and mode & 0o077:
        raise PollError("il file della password iLO deve avere permessi 0600")
    value = path.read_text(encoding="utf-8").rstrip("\r\n")
    if not value or "\n" in value or "\r" in value:
        raise PollError("il file della password iLO deve contenere una sola riga non vuota")
    return value


def safe_text(value: object) -> str:
    """Una voce non può aggiungere righe o campi al formato AdsLine."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(value)).strip()


def event_time(value: object) -> str:
    if not isinstance(value, str):
        raise PollError("timestamp IEL assente")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PollError("timestamp IEL non valido") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PollError("timestamp IEL senza fuso")
    return parsed.isoformat(timespec="seconds")


def updated_time(value: object) -> str | None:
    # HPE usa anche l'ora nulla 0000-00-00T00:00:00Z per un evento non ripetuto.
    if value is None or (isinstance(value, str) and value.startswith("0000-")):
        return None
    return event_time(value)


class RedfishClient:
    """Accetta solo URI Redfish dello stesso iLO e non segue redirect."""

    def __init__(self, host: str, ca_file: Path, fingerprint: str):
        self.origin = f"https://{host}"
        self.http = requests.Session()
        self.http.trust_env = False
        self.http.verify = str(ca_file)
        self.http.headers.update({"Accept": "application/json", "OData-Version": "4.0"})
        self.http.mount(self.origin + "/", FingerprintAdapter(fingerprint))
        self.token: str | None = None
        self.location: str | None = None

    def url(self, reference: str, base: str | None = None) -> str:
        if not isinstance(reference, str) or not reference:
            raise PollError("URI Redfish assente")
        result = urljoin(base or self.origin + "/", reference)
        parts = urlsplit(result)
        if (
            parts.scheme != "https"
            or parts.netloc != urlsplit(self.origin).netloc
            or not parts.path.startswith("/redfish/v1/")
            or ".." in parts.path.split("/")
            or parts.fragment
        ):
            raise PollError("URI Redfish esterno o non valido")
        return result

    def request(self, method: str, reference: str, *, base: str | None = None, **kwargs):
        url = self.url(reference, base)
        response = self.http.request(method, url, timeout=TIMEOUT, allow_redirects=False, **kwargs)
        if not 200 <= response.status_code < 300:
            raise PollError(f"Redfish {method} HTTP {response.status_code}")
        return response

    def login(self, username: str, password: str) -> None:
        response = self.request("POST", SESSIONS, json={"UserName": username, "Password": password})
        if response.status_code != 201:
            raise PollError(f"creazione sessione Redfish: HTTP {response.status_code}")
        token = response.headers.get("X-Auth-Token")
        location = response.headers.get("Location")
        if not token or not location:
            raise PollError("sessione Redfish senza token o Location")
        self.location = self.url(location)
        if not urlsplit(self.location).path.startswith(SESSIONS):
            raise PollError("Location della sessione Redfish inattesa")
        self.token = token
        self.http.headers["X-Auth-Token"] = token

    def get_json(self, reference: str, *, base: str | None = None) -> dict:
        response = self.request("GET", reference, base=base)
        try:
            data = response.json()
        except ValueError as exc:
            raise PollError("risposta Redfish non JSON") from exc
        if not isinstance(data, dict):
            raise PollError("risposta Redfish non oggetto")
        return data

    def logout(self) -> None:
        try:
            if self.location:
                self.request("DELETE", self.location)
        finally:
            self.http.close()
            self.token = None
            self.location = None


def read_entries(client: RedfishClient) -> list[dict]:
    """Legge tutte le pagine; membri incompleti sono recuperati per URI."""
    current = client.url(ENTRIES)
    visited: set[str] = set()
    entries: list[dict] = []
    while current:
        if current in visited:
            raise PollError("ciclo nella paginazione IEL")
        visited.add(current)
        page = client.get_json(current)
        members = page.get("Members")
        if not isinstance(members, list):
            raise PollError("pagina IEL senza Members")
        for member in members:
            if not isinstance(member, dict):
                raise PollError("membro IEL non valido")
            if {"Id", "Created", "Message", "Oem"}.issubset(member):
                entry = member
            else:
                link = member.get("@odata.id")
                member_url = client.url(link, current)
                if not urlsplit(member_url).path.startswith(ENTRIES):
                    raise PollError("membro IEL fuori dalla raccolta")
                entry = client.get_json(member_url)
            entries.append(entry)
        next_link = page.get("Members@odata.nextLink") or page.get("@odata.nextLink")
        current = client.url(next_link, current) if next_link else ""
        if current and not (
            urlsplit(current).path == ENTRIES.rstrip("/")
            or urlsplit(current).path.startswith(ENTRIES)
        ):
            raise PollError("paginazione IEL fuori dalla raccolta")
    return entries


def is_own_login(message: str, username: str) -> bool:
    return bool(
        re.search(r"\b(?:REST|Redfish)\b.*\b(?:login|logout)\b", message, re.I)
        and re.search(rf"(?<![\w-]){re.escape(username)}(?![\w-])", message, re.I)
    )


def plan_entries(entries: list[dict], previous: dict, username: str, received: str):
    """Restituisce righe nuove e stato futuro senza scrivere nulla."""
    state = dict(previous)
    lines: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise PollError("voce IEL non valida")
        key = str(entry.get("Id", ""))
        if not key or key in seen or any(ch in key for ch in "\r\n"):
            raise PollError("Id IEL assente o duplicato")
        seen.add(key)
        created = event_time(entry.get("Created"))
        extensions = entry.get("Oem")
        if not isinstance(extensions, dict):
            raise PollError("estensione OEM della voce IEL non valida")
        oem = extensions.get("Hpe")
        if not isinstance(oem, dict):
            raise PollError("estensione HPE della voce IEL non valida")
        count = oem.get("Count")
        if type(count) is not int or count < 1:
            raise PollError("Count IEL assente o non valido")
        message = safe_text(entry.get("Message", ""))
        code = safe_text(oem.get("Code", "unknown"))
        if not message:
            raise PollError("Message IEL assente")
        old = previous.get(key)
        is_new = not old or old.get("created") != created or count < old.get("count", 0)
        delta = count if is_new else count - old["count"]
        state[key] = {"created": created, "count": count}
        if delta == 0 or is_own_login(message, username):
            continue
        if is_new:
            declared = created
            updated = updated_time(oem.get("Updated"))
            updated_note = f" Updated={updated}" if updated else ""
            if count > 1 and not updated:
                updated_note = " Updated=unknown"
            detail = f"Id={safe_text(key)} Code={code} Count={count}{updated_note} {message}"
        else:
            updated = updated_time(oem.get("Updated"))
            declared = updated or received
            time_note = "" if updated else " repeat_time=unknown"
            detail = (
                f"Id={safe_text(key)} Code={code} Count={count} "
                f"repeat_delta={delta}{time_note} {message}"
            )
        lines.append((declared, detail))
    return lines, state


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PollError("stato iLO illeggibile") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise PollError("versione dello stato iLO non valida")
    entries = data.get("entries")
    if not isinstance(entries, dict):
        raise PollError("voci dello stato iLO non valide")
    for item in entries.values():
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("created"), str)
            or type(item.get("count")) is not int
            or item["count"] < 1
        ):
            raise PollError("voce dello stato iLO non valida")
    return entries


def save_state(path: Path, entries: dict) -> None:
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".ilo-", delete=False
        ) as temporary:
            name = temporary.name
            os.chmod(name, 0o640)
            json.dump({"version": 1, "entries": entries}, temporary, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(name, path)
        name = None
        if os.name == "posix":
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if name is not None:
            Path(name).unlink(missing_ok=True)


def ads_line(host: str, received: datetime, declared: str, message: str) -> str:
    return (
        f"{received.isoformat(timespec='microseconds')} {host} {declared} "
        f"ilo5 {safe_text(message)}\n"
    )


def append_lines(directory: Path, host: str, lines: list[tuple[str, str]]) -> None:
    if not directory.is_dir():
        raise PollError("cartella della sorgente iLO assente")
    now = datetime.now().astimezone()
    path = directory / f"{now.date().isoformat()}.log"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    with os.fdopen(fd, "a", encoding="utf-8", newline="") as output:
        for declared, message in lines:
            output.write(ads_line(host, now, declared, message))
        output.flush()
        os.fsync(output.fileno())


@contextmanager
def source_lock(path: Path):
    if os.name != "posix":
        raise PollError("il job iLO richiede il collettore Linux")
    import fcntl

    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def poll(
    host: str,
    username: str,
    password: str,
    ca_file: Path,
    fingerprint: str,
    state_dir: Path,
    output_dir: Path,
) -> int:
    state_path = state_dir / f"{host}.json"
    log_dir = output_dir / host
    with source_lock(state_dir / f"{host}.lock"):
        previous = load_state(state_path)
        client = RedfishClient(host, ca_file, fingerprint)
        try:
            client.login(username, password)
            try:
                entries = read_entries(client)
            finally:
                client.logout()
        except BaseException:
            client.http.close()
            raise
        now = datetime.now().astimezone()
        planned, state = plan_entries(
            entries, previous, username, now.isoformat(timespec="seconds")
        )
        planned.append(
            (now.isoformat(timespec="seconds"), f"ads-ilo status=ok entries={len(entries)}")
        )
        append_lines(log_dir, host, planned)
        save_state(state_path, state)
        return len(planned) - 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="indirizzo IPv4 dell'iLO")
    parser.add_argument("--username", default="ads-reader")
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--fingerprint-file", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/ads/ilo"))
    parser.add_argument("--output-dir", type=Path, default=Path("/srv/ads"))
    args = parser.parse_args()
    valid_host = False
    try:
        ipaddress.IPv4Address(args.host)
        valid_host = True
        password = read_password(args.password_file)
        fingerprint = read_fingerprint(args.fingerprint_file)
        if not args.ca_file.is_file():
            raise PollError("certificato CA iLO assente")
        count = poll(
            args.host,
            args.username,
            password,
            args.ca_file,
            fingerprint,
            args.state_dir,
            args.output_dir,
        )
        print(f"iLO {args.host}: {count} nuove righe IEL")
        return 0
    except (OSError, requests.RequestException, PollError, ValueError) as exc:
        # Mai stampare il messaggio d'errore HTTP, che potrebbe includere URI o token.
        now = datetime.now().astimezone()
        if valid_host:
            try:
                append_lines(
                    args.output_dir / args.host,
                    args.host,
                    [
                        (
                            now.isoformat(timespec="seconds"),
                            f"ads-ilo status=error type={type(exc).__name__}",
                        )
                    ],
                )
            except (OSError, PollError):
                pass  # systemd registra comunque il codice di uscita non zero.
        print(f"iLO {args.host}: lettura fallita ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
