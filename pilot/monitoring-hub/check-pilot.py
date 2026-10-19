"""Check the live local metrics path, not just Compose syntax."""

import base64
from http.client import RemoteDisconnected
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PROMETHEUS = "http://127.0.0.1:19090"
GRAFANA = "http://127.0.0.1:13000"


def request_json(url: str, authorization: str | None = None) -> dict:
    headers = {"Authorization": authorization} if authorization else {}
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return json.load(response)


def query(expression: str) -> list:
    url = PROMETHEUS + "/api/v1/query?" + urlencode({"query": expression})
    payload = request_json(url)
    if payload.get("status") != "success":
        raise RuntimeError("Query Prometheus non riuscita")
    return payload["data"]["result"]


def wait_for_self_scrape() -> None:
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            results = query('up{job="prometheus"}')
            if len(results) == 1 and results[0]["value"][1] == "1":
                return
        except (ConnectionError, HTTPError, URLError, TimeoutError, RemoteDisconnected):
            pass
        time.sleep(2)
    raise RuntimeError("Scrape interno Prometheus assente dopo 75 secondi")


def wait_for_grafana() -> None:
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            if request_json(GRAFANA + "/api/health").get("database") == "ok":
                return
        except (ConnectionError, HTTPError, URLError, TimeoutError, RemoteDisconnected):
            pass
        time.sleep(2)
    raise RuntimeError("Grafana non pronta dopo 75 secondi")


def grafana_authorization() -> str:
    line = next(
        (line for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
         if line.startswith("GRAFANA_ADMIN_PASSWORD=")),
        None,
    )
    if line is None:
        raise RuntimeError("Password Grafana mancante nel file privato .env")
    password = line.split("=", 1)[1]
    token = base64.b64encode(f"admin:{password}".encode()).decode()
    return "Basic " + token


def check_grafana(authorization: str) -> None:
    endpoint = GRAFANA + "/api/datasources/uid/pilot-prometheus"
    try:
        request_json(endpoint)
    except HTTPError as error:
        if error.code != 401:
            raise RuntimeError(f"Accesso anonimo Grafana: HTTP {error.code}") from error
    else:
        raise RuntimeError("Grafana ha esposto il datasource senza login")

    datasource = request_json(endpoint, authorization)
    if datasource.get("url") != "http://prometheus:9090":
        raise RuntimeError("Datasource Grafana diverso dal Prometheus del pilota")
    dashboard = request_json(
        GRAFANA + "/api/dashboards/uid/linux-metrics-pilot", authorization
    )
    if dashboard.get("dashboard", {}).get("uid") != "linux-metrics-pilot":
        raise RuntimeError("Dashboard del pilota non caricata")
    proxy_url = (
        GRAFANA
        + "/api/datasources/proxy/uid/pilot-prometheus/api/v1/query?"
        + urlencode({"query": 'up{job="prometheus"}'})
    )
    proxied = request_json(proxy_url, authorization)
    values = proxied.get("data", {}).get("result", [])
    if proxied.get("status") != "success" or len(values) != 1 or values[0]["value"][1] != "1":
        raise RuntimeError("Grafana non riesce a leggere lo scrape tramite il datasource")


def check_netdata_targets() -> str:
    targets = json.loads((ROOT / "targets" / "netdata.json").read_text(encoding="utf-8"))
    if not targets:
        return "Netdata: nessun target reale configurato (atteso nel pilota isolato)"
    expected = sum(len(group.get("targets", [])) for group in targets)
    results = query('up{job="netdata"}')
    if expected == 0 or len(results) != expected:
        raise RuntimeError("Numero di target Netdata scoperti diverso dal file privato")
    if any(result["value"][1] != "1" for result in results):
        raise RuntimeError("Almeno uno scrape Netdata non riesce")
    samples = query('count({job="netdata",__name__!="up"})')
    if not samples or float(samples[0]["value"][1]) <= 0:
        raise RuntimeError("Scrape Netdata riuscito ma nessuna metrica acquisita")
    return f"Netdata: {expected} target con scrape e campioni presenti"


def main() -> None:
    wait_for_self_scrape()
    print("Prometheus: scrape interno riuscito")
    wait_for_grafana()
    check_grafana(grafana_authorization())
    print("Grafana: accesso anonimo negato, dashboard e query al datasource riuscite")
    print(check_netdata_targets())


if __name__ == "__main__":
    main()
