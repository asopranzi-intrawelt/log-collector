"""Create ignored local inputs for the isolated metrics pilot."""

from pathlib import Path
import re
import secrets


ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
TARGETS = ROOT / "targets" / "netdata.json"
FIXTURES = ROOT / "fixtures"
CURRENT_LOG = FIXTURES / "current-log.txt"


def main() -> None:
    if not ENV.exists():
        ENV.write_text(
            "GRAFANA_ADMIN_PASSWORD=" + secrets.token_urlsafe(32) + "\n",
            encoding="utf-8",
        )
        print("Credenziale Grafana locale creata nel file ignorato .env")
    else:
        print("Credenziale Grafana locale esistente preservata")
    TARGETS.parent.mkdir(exist_ok=True)
    if not TARGETS.exists():
        TARGETS.write_text("[]\n", encoding="utf-8")
        print("Lista target Netdata privata inizializzata vuota")
    else:
        print("Lista target Netdata privata esistente preservata")
    FIXTURES.mkdir(exist_ok=True)
    (FIXTURES / "original").mkdir(exist_ok=True)
    if not CURRENT_LOG.exists():
        CURRENT_LOG.write_text("technical-0000.jsonl\n", encoding="utf-8")
    name = CURRENT_LOG.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"technical-[a-z0-9-]+\.jsonl", name):
        raise RuntimeError("Nome del segmento sintetico non valido")
    (FIXTURES / name).touch(exist_ok=True)


if __name__ == "__main__":
    main()
