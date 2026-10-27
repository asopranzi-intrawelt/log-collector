"""Prova il replay del buffer Windows dopo arresto con ricevitore indisponibile."""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import os
import shutil
import socket
import ssl
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--fluent-bit", type=Path, required=True)
parser.add_argument("--online-seconds", type=int, default=60)
args = parser.parse_args()
if os.name != "nt":
    parser.error("questa prova esegue il binario Fluent Bit Windows")

exe = args.fluent_bit.resolve(strict=True)
root = Path(__file__).resolve().parents[2]
work = root / "_notes/tmp" / f"windows-backlog-{uuid.uuid4().hex}"
work.mkdir(parents=True)
runtime = work / "runtime"
runtime.mkdir()
template = (root / "config/windows-pilota/fluent-bit.conf.template").read_text(encoding="utf-8")


def certificates() -> tuple[Path, Path, Path]:
    now = dt.datetime.now(dt.UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Backlog Test CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
        .issuer_name(ca_name).public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    ca, cert, key = work / "ca.pem", work / "server.pem", work / "server.key"
    ca.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    cert.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    key.write_bytes(server_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    return ca, cert, key


ca, cert, key = certificates()
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]


def configuration(marker: str) -> Path:
    service = template.split("[INPUT]", 1)[0]
    output = "[OUTPUT]" + template.split("[OUTPUT]", 2)[1]
    service = service.replace("@@RUNTIME_DIR@@", runtime.as_posix())
    service = service.replace("Flush                     5", "Flush                     1")
    output = output.replace("@@COLLECTOR_HOST@@", "127.0.0.1")
    output = output.replace("@@COMPUTER_NAME@@", "PILOT-01")
    output = output.replace("@@CA_FILE@@", ca.as_posix())
    output = output.replace("Port                      6514", f"Port                      {port}")
    source = (
        "[INPUT]\n    Name dummy\n    Tag ads.win\n"
        f'    Dummy {{"message":"{marker}","Computer":"PILOT-01"}}\n'
        "    Interval_Sec 1\n    Samples 1\n    storage.type filesystem\n\n"
    )
    path = work / f"{marker}.conf"
    path.write_text(service + source + output, encoding="utf-8", newline="\n")
    return path


def run(
    path: Path, *, seconds: int, complete: Callable[[], bool] | None = None
) -> tuple[str, float]:
    proc = subprocess.Popen(
        [str(exe), "-c", str(path)],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    start = time.monotonic()
    while time.monotonic() - start < seconds and proc.poll() is None:
        if complete is not None and complete():
            break
        time.sleep(0.1)
    elapsed = time.monotonic() - start
    if proc.poll() is None:
        proc.kill()
    _, stderr = proc.communicate(timeout=5)
    return stderr.decode("utf-8", errors="replace"), elapsed


offline_log, _ = run(configuration("backlog-old"), seconds=4)
(work / "offline.log").write_text(offline_log, encoding="utf-8")
chunks = list((runtime / "storage").rglob("*.flb"))
if not chunks:
    raise SystemExit(f"nessun chunk persistente prima del riavvio: {offline_log[-800:]}")
health = subprocess.run(
    [
        shutil.which("powershell") or "powershell",
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(root / "bin/ads-windows-queue-health.ps1"),
        "-RuntimeDir", str(runtime),
        "-MaxQueueBytes", "1",
        "-MinFreeBytes", "1",
        "-MaxOldestChunkMinutes", "60",
    ],
    cwd=root,
    capture_output=True,
    text=True,
    check=False,
)
if health.returncode != 2 or "reason=queue_bytes" not in health.stdout:
    raise SystemExit(f"monitor non rileva il chunk offline: {health.stdout} {health.stderr}")

receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
receiver.bind(("127.0.0.1", port))
receiver.listen(5)
receiver.settimeout(0.2)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(cert, key)
stop = threading.Event()
payloads: list[bytes] = []


def receive() -> None:
    while not stop.is_set():
        try:
            conn, _ = receiver.accept()
        except TimeoutError:
            continue
        except OSError:
            break
        try:
            with context.wrap_socket(conn, server_side=True) as secure:
                secure.settimeout(0.2)
                while not stop.is_set():
                    try:
                        part = secure.recv(16384)
                    except TimeoutError:
                        continue
                    if not part:
                        break
                    payloads.append(part)
        except (OSError, ssl.SSLError):
            pass


thread = threading.Thread(target=receive, daemon=True)
thread.start()
try:
    online_log, replay_seconds = run(
        configuration("backlog-new"),
        seconds=args.online_seconds,
        complete=lambda: (
            b"backlog-old" in b"".join(payloads)
            and b"backlog-new" in b"".join(payloads)
        ),
    )
finally:
    stop.set()
    receiver.close()
    thread.join(timeout=2)

payload = b"".join(payloads)
(work / "online.log").write_text(online_log, encoding="utf-8")
(work / "received.bin").write_bytes(payload)
old_count = payload.count(b"backlog-old")
new_count = payload.count(b"backlog-new")
print(
    f"PERSISTED_CHUNKS={len(chunks)} OLD_RECEIVED={old_count} "
    f"NEW_RECEIVED={new_count} REPLAY_SECONDS={replay_seconds:.1f}"
)
print("HEALTH_OFFLINE=alert")
print(f"PROBE_PRIVATE={work}")
if old_count < 1 or new_count < 1:
    raise SystemExit(f"replay o evento nuovo assente: {online_log[-800:]}")
