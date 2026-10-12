#!/usr/bin/env python3
"""Raccoglie gli accessi locali degli switch Nebula con ripresa durevole.

Endpoint e schema: https://zyxelnetworks.github.io/NebulaOpenAPI/doc/openapi.html
Il diario SQLite precede l'append: una ripresa completa anche una riga parziale,
senza riscrivere i byte già presenti o anticipare il checkpoint.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import requests

API_BASE = "https://api.nebula.zyxel.com/v1/nebula"
FIELDS = ("timestamp", "category", "devId", "mac", "message", "priority", "tag")
PATTERNS = (
    ("failure", r"HTTP\(s\) authentication failure \[username: (.+), IP address = (.+)\]"),
    ("login", r"HTTP\(s\) user (.+) login \[IP address = (.+)\]"),
    (
        "logout",
        r"HTTP\(s\) user (.+) logout due to session timeout \[IP address = (.+)\]",
    ),
)


class PollError(Exception):
    """Codice diagnostico pubblico, senza messaggi remoti o credenziali."""


def load_config(path):
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PollError("config_invalid") from exc
    if not isinstance(config, dict):
        raise PollError("config_invalid")
    for key in ("site_id", "device_id", "source", "system"):
        value = config.get(key)
        if not isinstance(value, str) or not value or any(c.isspace() for c in value):
            raise PollError("config_invalid")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", config["source"]):
        raise PollError("source_invalid")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", config["system"]):
        raise PollError("system_invalid")
    if any(ord(c) < 32 or ord(c) == 127 for k in ("site_id", "device_id") for c in config[k]):
        raise PollError("config_invalid")
    defaults = {
        "chunk_ms": 300_000,
        "overlap_ms": 600_000,
        "settle_ms": 60_000,
        "response_guard": 1_000,
        "max_requests": 200,
    }
    for key, value in defaults.items():
        config.setdefault(key, value)
    for key in ("initial_start_ms", "recovery_horizon_ms", *defaults):
        if type(config.get(key)) is not int or config[key] <= 0:
            raise PollError("config_invalid")
    if config["overlap_ms"] >= config["recovery_horizon_ms"]:
        raise PollError("config_invalid")
    return config


def read_key(path):
    if path.is_symlink():
        raise PollError("key_permissions")
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise PollError("key_permissions")
    value = path.read_text(encoding="utf-8").strip()
    if not value or any(c.isspace() for c in value):
        raise PollError("key_invalid")
    return value


class NebulaClient:
    def __init__(self, key, ca_file=None):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["X-ZyxelNebula-API-Key"] = key
        self.verify = str(ca_file) if ca_file else True

    def fetch(self, config, start, end):
        site = quote(config["site_id"], safe="")
        device = quote(config["device_id"], safe="")
        try:
            response = self.session.post(
                f"{API_BASE}/{site}/sw/{device}/event-logs",
                json={"startTimestamp": start, "endTimestamp": end},
                timeout=(10, 30),
                verify=self.verify,
                allow_redirects=False,
            )
            if response.status_code != 200:
                raise PollError(f"http_{response.status_code}")
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PollError("transport_or_json") from exc

    def close(self):
        self.session.close()


def event_id(event):
    # L'API non fornisce un ID: due eventi identici nello stesso millisecondo
    # sono indistinguibili. La limitazione è esplicita nel runbook.
    data = json.dumps([event[k] for k in FIELDS], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def validate_events(events, config, start, end):
    if not isinstance(events, list):
        raise PollError("response_schema")
    for event in events:
        if not isinstance(event, dict) or any(key not in event for key in FIELDS):
            raise PollError("event_schema")
        timestamp = event["timestamp"]
        if type(timestamp) is not int or not start <= timestamp <= end:
            raise PollError("event_time")
        for key in FIELDS[1:]:
            if not isinstance(event[key], str) or not event[key]:
                raise PollError("event_schema")
            if any(ord(c) < 32 or ord(c) == 127 for c in event[key]):
                raise PollError("event_control_character")
        if event["devId"] != config["device_id"]:
            raise PollError("event_device")
    return events


def outcome(event):
    if event["category"] != "AAA" or event["tag"] != "authentication":
        return None
    for label, pattern in PATTERNS:
        if re.fullmatch(pattern, event["message"]):
            return label
    # Un nuovo formato AAA richiede ricognizione: non diventa un accesso AdS
    # per il solo nome della categoria e non viene scartato avanzando il cursore.
    raise PollError("authentication_unknown")


def collect(client, config, start, end, clock):
    collected = {}
    calls = 0

    def interval(left, right):
        nonlocal calls
        calls += 1
        if calls > config["max_requests"]:
            raise PollError("request_budget")
        events = validate_events(client.fetch(config, left, right), config, left, right)
        received = clock().astimezone()
        if len(events) >= config["response_guard"]:
            if right - left <= 1:
                raise PollError("response_saturated")
            middle = (left + right) // 2
            interval(left, middle)
            interval(middle, right)
            return
        for event in events:
            label = outcome(event)
            if label:
                collected.setdefault(event_id(event), (event, label, received))

    left = start
    while left < end:
        right = min(left + config["chunk_ms"], end)
        interval(left, right)
        # Il confine è richiesto due volte: l'inclusività non è documentata.
        left = right
    return collected


def sync_directory(path):
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


@contextmanager
def source_lock(path):
    if path.is_symlink():
        raise PollError("lock_symlink")
    with path.open("a+b") as handle:
        os.chmod(path, 0o600)
        if path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "posix":
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise PollError("poll_already_running") from exc
        try:
            yield
        finally:
            if os.name == "posix":
                fcntl.flock(handle, fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def open_state(path, identity):
    if path.is_symlink():
        raise PollError("state_symlink")
    connection = sqlite3.connect(path)
    os.chmod(path, 0o600)
    connection.execute("PRAGMA synchronous=FULL")
    connection.executescript(
        "CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY CHECK(id=1), "
        "identity TEXT NOT NULL, cursor INTEGER NOT NULL);"
        "CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, timestamp INTEGER NOT NULL);"
        "CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY CHECK(id=1), "
        "payload TEXT NOT NULL);"
    )
    saved = connection.execute("SELECT identity FROM meta WHERE id=1").fetchone()
    pending = connection.execute("SELECT payload FROM pending WHERE id=1").fetchone()
    if (saved and saved[0] != identity) or (
        pending and json.loads(pending[0])["identity"] != identity
    ):
        connection.close()
        raise PollError("state_identity")
    sync_directory(path.parent)
    return connection


def recover(connection, log_dir):
    row = connection.execute("SELECT payload FROM pending WHERE id=1").fetchone()
    if row is None:
        return
    batch = json.loads(row[0])
    for item in batch["writes"]:
        filename = item["file"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.log", filename):
            raise PollError("journal_invalid")
        path = log_dir / filename
        if path.is_symlink():
            raise PollError("log_symlink")
        if not path.exists() and item["offset"] != 0:
            raise PollError("log_journal_conflict")
        payload = base64.b64decode(item["bytes"], validate=True)
        with path.open("r+b" if path.exists() else "w+b") as handle:
            os.chmod(path, 0o640)
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            offset = item["offset"]
            if not offset <= size <= offset + len(payload):
                raise PollError("log_journal_conflict")
            handle.seek(offset)
            existing = handle.read()
            if existing != payload[: len(existing)]:
                raise PollError("log_journal_conflict")
            handle.seek(0, os.SEEK_END)
            handle.write(payload[len(existing) :])
            handle.flush()
            os.fsync(handle.fileno())
        sync_directory(log_dir)
    with connection:
        connection.executemany("INSERT OR IGNORE INTO seen VALUES (?, ?)", batch["seen"])
        connection.execute(
            "INSERT OR REPLACE INTO meta VALUES (1, ?, ?)",
            (batch["identity"], batch["cursor"]),
        )
        connection.execute("DELETE FROM seen WHERE timestamp < ?", (batch["prune_before"],))
        connection.execute("DELETE FROM pending WHERE id=1")


def poll(client, config, state_dir, log_dir, now_ms, clock=None):
    clock = clock or (lambda: datetime.now().astimezone())
    for directory in (state_dir, log_dir):
        if directory.is_symlink():
            raise PollError("directory_symlink")
        directory.mkdir(mode=0o750, parents=True, exist_ok=True)
        sync_directory(directory.parent)
    identity = json.dumps(
        [
            config[k]
            for k in ("site_id", "device_id", "source", "system", "initial_start_ms", "overlap_ms")
        ]
        + [str(log_dir.resolve())]
    )
    with source_lock(state_dir / "poll.lock"):
        connection = open_state(state_dir / "state.sqlite", identity)
        try:
            recover(connection, log_dir)
            row = connection.execute("SELECT cursor FROM meta WHERE id=1").fetchone()
            cursor = row[0] if row else config["initial_start_ms"]
            end = now_ms - config["settle_ms"]
            if end < cursor:
                raise PollError("clock_before_checkpoint")
            if (
                now_ms - max(config["initial_start_ms"], cursor - config["overlap_ms"])
                > config["recovery_horizon_ms"]
            ):
                raise PollError("gap_exceeds_horizon")
            start = max(config["initial_start_ms"], cursor - config["overlap_ms"])
            events = collect(client, config, start, end, clock)
            writes = {}
            seen = []
            for key, (event, label, received) in sorted(
                events.items(), key=lambda item: (item[1][0]["timestamp"], item[0])
            ):
                if connection.execute("SELECT 1 FROM seen WHERE id=?", (key,)).fetchone():
                    continue
                declared = datetime.fromtimestamp(event["timestamp"] / 1000, UTC)
                line = (
                    f"{received.isoformat(timespec='microseconds')} {config['source']} "
                    f"{declared.isoformat(timespec='milliseconds')} {config['system']} "
                    f"nebula-auth outcome={label} event_id={key} {event['message']}\n"
                )
                filename = f"{received.date().isoformat()}.log"
                writes[filename] = writes.get(filename, b"") + line.encode("utf-8")
                seen.append([key, event["timestamp"]])
            planned = []
            for filename, payload in writes.items():
                path = log_dir / filename
                if path.is_symlink():
                    raise PollError("log_symlink")
                planned.append(
                    {
                        "file": filename,
                        "offset": path.stat().st_size if path.exists() else 0,
                        "bytes": base64.b64encode(payload).decode("ascii"),
                    }
                )
            batch = {
                "identity": identity,
                "cursor": end,
                "prune_before": max(config["initial_start_ms"], end - config["overlap_ms"]),
                "seen": seen,
                "writes": planned,
            }
            # Commit del diario PRIMA dei log: il checkpoint resta quello precedente.
            with connection:
                connection.execute("INSERT INTO pending VALUES (1, ?)", (json.dumps(batch),))
            recover(connection, log_dir)
            return len(seen)
        finally:
            connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--state-root", type=Path, default=Path("/var/lib/ads/nebula"))
    parser.add_argument("--output-root", type=Path, default=Path("/srv/ads"))
    args = parser.parse_args(argv)
    os.umask(0o027)
    client = None
    source = "nebula"
    try:
        config = load_config(args.config)
        source = config["source"]
        client = NebulaClient(read_key(args.api_key_file), args.ca_file)
        count = poll(
            client,
            config,
            args.state_root / source,
            args.output_root / source,
            int(datetime.now().timestamp() * 1000),
        )
        detail = f"status=ok written={count}"
        status = 0
    except PollError as exc:
        detail = f"status=error code={exc}"
        status = 1
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        detail = "status=error code=local_io_or_state"
        status = 1
    finally:
        if client is not None:
            client.close()
    received = datetime.now().astimezone().isoformat(timespec="microseconds")
    print(f"{received} {source} {received} nebula-poller {detail}", file=sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main())
