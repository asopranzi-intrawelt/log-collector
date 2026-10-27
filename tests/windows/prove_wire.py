"""Cattura ripetibile di Syslog sintetico dal binario Fluent Bit Windows."""

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
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--fluent-bit", type=Path, required=True,
    help="binario Windows 5.1.3 verificato per SHA-256",
)
args = parser.parse_args()
if os.name != "nt":
    parser.error("questa prova esegue il binario Fluent Bit Windows")
exe = args.fluent_bit.resolve(strict=True)
root = Path(__file__).resolve().parents[2]
source = root / "config/windows-pilota"
work = root / "_notes/tmp" / f"windows-wire-{uuid.uuid4().hex}"
work.mkdir(parents=True)


def certs() -> tuple[Path, Path]:
    now = dt.datetime.now(dt.UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic Test CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    ca = work / "ca.pem"
    cert = work / "server.pem"
    key = work / "server.key"
    ca.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    cert.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    key.write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return ca, cert


ca, cert = certs()
key = work / "server.key"
shutil.copyfile(source / "ads.lua", work / "ads.lua")


def config(host: str, port: int, suffix: str, *, verify_hostname: bool = True) -> Path:
    text = (source / "fluent-bit.conf.template").read_text(encoding="utf-8")
    start = text.index("[INPUT]")
    end = text.index("[INPUT]", start + 1)
    synthetic = (
        '[INPUT]\n    Name dummy\n    Tag ads.win\n'
        '    Dummy {"EventID":4624,"Computer":"PILOT-01","EventRecordID":42,'
        '"TimeCreated":"2026-10-27T08:00:00Z","EventData":'
        '{"TargetUserName":"ads_test","LogonType":"10","IpAddress":"192.0.2.10"}}\n'
        '    Interval_Sec 1\n    storage.type filesystem\n\n'
    )
    text = text[:start] + synthetic + text[end:]
    text = text.replace("Interval_Sec              3600", "Interval_Sec              1")
    text = text.replace("@@EVENT_QUERY@@", "*")
    text = text.replace("@@COLLECTOR_HOST@@", host)
    text = text.replace("@@COMPUTER_NAME@@", "PILOT-01")
    runtime = work / f"state-{suffix}"
    runtime.mkdir()
    text = text.replace("@@RUNTIME_DIR@@", runtime.as_posix())
    text = text.replace("@@CA_FILE@@", ca.as_posix())
    text = text.replace("Port                      6514", f"Port                      {port}")
    if not verify_hostname:
        text = text.replace("tls.verify_hostname       on", "tls.verify_hostname       off")
    text = text.replace("Log_Level                 info", "Log_Level                 warning")
    text = text.replace("Flush                     5", "Flush                     1")
    path = work / f"{suffix}.conf"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def run(host: str, suffix: str, *, verify_hostname: bool = True) -> tuple[list[bytes], str]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(10)
    listener.settimeout(0.3)
    port = listener.getsockname()[1]
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    received: list[bytes] = []
    stop = threading.Event()

    def serve() -> None:
        workers: list[threading.Thread] = []

        def collect(conn: socket.socket) -> None:
            try:
                with context.wrap_socket(conn, server_side=True) as secure:
                    secure.settimeout(0.3)
                    buffer = bytearray()
                    while not stop.is_set():
                        try:
                            data = secure.recv(16384)
                        except TimeoutError:
                            continue
                        if not data:
                            break
                        buffer.extend(data)
                        while b"\n" in buffer:
                            end = buffer.index(b"\n") + 1
                            received.append(bytes(buffer[:end]))
                            del buffer[:end]
            except (ssl.SSLError, ConnectionResetError, OSError):
                pass

        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            worker = threading.Thread(target=collect, args=(conn,), daemon=True)
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join(timeout=1)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    path = config(host, port, suffix, verify_hostname=verify_hostname)
    proc = subprocess.Popen(
        [str(exe), "-c", str(path)],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    time.sleep(8)
    proc.terminate()
    try:
        _, stderr = proc.communicate(timeout=4)
    except subprocess.TimeoutExpired:
        proc.kill()
        _, stderr = proc.communicate(timeout=4)
    stop.set()
    thread.join(timeout=2)
    listener.close()
    return received, stderr.decode("utf-8", errors="replace")


positive, positive_log = run("127.0.0.1", "positive")
lines = [line for stream in positive for line in stream.splitlines(keepends=True)]
access = next((line for line in lines if b" ads-win " in line and b"ads_test" in line), None)
heartbeat = next(
    (line for line in lines if b" ads-heartbeat " in line and b"heartbeat" in line),
    None,
)
if access is None or heartbeat is None:
    raise SystemExit(
        f"mancano i due messaggi: streams={len(positive)}, lines={len(lines)}; "
        f"{positive_log[-500:]}"
    )

negative, negative_log = run("localhost", "wrong-san")
if any(negative):
    raise SystemExit("TLS con SAN errato ha consegnato dati")
if "certificate verify failed" not in negative_log:
    raise SystemExit(f"rifiuto SAN non dimostrato: {negative_log[-500:]}")

control, control_log = run("localhost", "hostname-check-off", verify_hostname=False)
if not any(b" ads-win " in part and b"ads_test" in part for part in control):
    raise SystemExit(f"controllo con verifica nome spenta non consegna: {control_log[-500:]}")

wire = work / "fluent-bit-windows-wire.bin"
wire.write_bytes(access + heartbeat)
print(f"ACCESS_LEN={len(access)} HEARTBEAT_LEN={len(heartbeat)}")
print(f"WRONG_SAN_PAYLOAD={sum(map(len, negative))} TLS_MISMATCH=True")
print(f"NAME_CHECK_OFF_PAYLOAD={sum(map(len, control))}")
print(f"FIXTURE_PRIVATE={wire}")
