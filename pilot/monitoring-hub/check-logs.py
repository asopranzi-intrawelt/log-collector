"""Verify synthetic original -> Alloy -> Loki -> Grafana query locally."""

import base64
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader


ROOT = Path(__file__).resolve().parent
LOKI = "http://127.0.0.1:13100"
GRAFANA = "http://127.0.0.1:13000"


def fixture_module():
    loader = SourceFileLoader("emit_fixture", str(ROOT / "emit-fixture.py"))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


def request_json(url: str, authorization: str | None = None) -> dict:
    headers = {"Authorization": authorization} if authorization else {}
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return json.load(response)


def authorization() -> str:
    line = next(
        line for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
        if line.startswith("GRAFANA_ADMIN_PASSWORD=")
    )
    token = base64.b64encode(("admin:" + line.split("=", 1)[1]).encode()).decode()
    return "Basic " + token


def query_url(base: str, event_id: str) -> str:
    expression = '{archive="technical",source_family="pilot",service="fixture"} |= "' + event_id + '"'
    return base + "/loki/api/v1/query_range?" + urlencode(
        {"query": expression, "since": "10m", "limit": "20"}
    )


def entries(payload: dict) -> list[tuple[dict, dict]]:
    if payload.get("status") != "success":
        raise RuntimeError("Query Loki non riuscita")
    return [
        (stream["stream"], json.loads(line))
        for stream in payload.get("data", {}).get("result", [])
        for _, line in stream.get("values", [])
    ]


def check_labels(found: list[tuple[dict, dict]], expected: dict) -> list[dict]:
    allowed = {
        "archive", "source_family", "service", "service_name", "detected_level"
    }
    for labels, _ in found:
        if not {"archive", "source_family", "service"}.issubset(labels):
            raise RuntimeError("Label stabili richieste assenti")
        if any(
            labels[key] != value
            for key, value in {
                "archive": "technical",
                "source_family": "pilot",
                "service": "fixture",
            }.items()
        ):
            raise RuntimeError("Valore delle label stabili inatteso")
        unexpected = set(labels) - allowed
        if unexpected:
            raise RuntimeError(f"Label non previste nel pilota: {sorted(unexpected)}")
        label_text = json.dumps(labels)
        if any(
            dynamic in label_text
            for dynamic in (
                expected["event_id"],
                expected["original_ref"],
                expected["original_sha256"],
            )
        ):
            raise RuntimeError("Identificativo, riferimento o digest finito nelle label")
    return [record for _, record in found]


def main() -> None:
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            with urlopen(LOKI + "/ready", timeout=5) as response:
                if response.status == 200:
                    break
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(2)
    else:
        raise RuntimeError("Loki non pronto dopo 75 secondi")

    event_id, expected = fixture_module().emit()
    original = ROOT / expected["original_ref"]
    if sha256(original.read_bytes()).hexdigest() != expected["original_sha256"]:
        raise RuntimeError("Impronta dell'originale sintetico non coincide")

    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            found = entries(request_json(query_url(LOKI, event_id)))
            records = check_labels(found, expected)
            if records:
                break
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(2)
    else:
        raise RuntimeError("L'evento sintetico non è arrivato in Loki")
    if records != [expected]:
        raise RuntimeError("Loki non contiene esattamente il record sintetico atteso")
    print("Alloy/Loki: un record sintetico, originale SHA-256 e label controllate")
    print("Label osservate: " + ", ".join(sorted(found[0][0])))

    proxy = GRAFANA + "/api/datasources/proxy/uid/pilot-loki"
    records_from_grafana = check_labels(
        entries(request_json(query_url(proxy, event_id), authorization())), expected
    )
    if records_from_grafana != [expected]:
        raise RuntimeError("Grafana non restituisce il record Loki atteso")
    print("Grafana: query Loki autenticata riuscita")


if __name__ == "__main__":
    main()
