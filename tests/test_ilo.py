"""Prove del lettore IEL con risposte nel formato documentato da HPE per iLO 5."""

from contextlib import nullcontext

import pytest

from conftest import load_script

ilo = load_script("ads-ilo.py")


def entry(*, count=1, updated="2026-10-06T14:05:09Z", user="Operator", created=None):
    return {
        "Id": "1",
        "Created": created or "2026-10-06T14:05:01Z",
        "Message": f"Host REST login: {user}",
        "Oem": {
            "Hpe": {
                "Categories": ["Security", "Administration"],
                "Code": 1131,
                "Count": count,
                "Updated": updated,
            }
        },
    }


def test_nuova_voce_incremento_e_rilettura_senza_duplicati():
    received = "2026-10-06T16:00:00+02:00"
    first, state = ilo.plan_entries([entry(count=2)], {}, "ads-reader", received)
    assert len(first) == 1
    assert first[0][0] == "2026-10-06T14:05:01+00:00"
    assert "Id=1 Code=1131 Count=2" in first[0][1]
    assert "Updated=2026-10-06T14:05:09+00:00" in first[0][1]
    repeated, state = ilo.plan_entries([entry(count=5)], state, "ads-reader", received)
    assert len(repeated) == 1
    assert repeated[0][0] == "2026-10-06T14:05:09+00:00"
    assert "repeat_delta=3" in repeated[0][1]
    unchanged, _ = ilo.plan_entries([entry(count=5)], state, "ads-reader", received)
    assert unchanged == []


def test_ripetizione_senza_updated_non_inventa_l_ora():
    old = {"1": {"created": "2026-10-06T14:05:01+00:00", "count": 1}}
    current = entry(count=3, updated=None)
    received = "2026-10-06T16:00:00+02:00"
    lines, _ = ilo.plan_entries([current], old, "ads-reader", received)
    assert lines == [
        (
            received,
            "Id=1 Code=1131 Count=3 repeat_delta=2 repeat_time=unknown Host REST login: Operator",
        )
    ]


def test_updated_nullo_hpe_non_blocca_la_raccolta():
    old = {"1": {"created": "2026-10-06T14:05:01+00:00", "count": 1}}
    received = "2026-10-06T16:00:00+02:00"
    lines, _ = ilo.plan_entries(
        [entry(count=2, updated="0000-00-00T00:00:00Z")], old, "ads-reader", received
    )
    assert lines[0][0] == received
    assert "repeat_time=unknown" in lines[0][1]


def test_stesso_id_con_created_diverso_e_un_evento_nuovo():
    old = {"1": {"created": "2026-10-05T10:00:00+00:00", "count": 12}}
    lines, state = ilo.plan_entries(
        [entry(count=1)], old, "ads-reader", "2026-10-06T16:00:00+02:00"
    )
    assert len(lines) == 1
    assert "repeat_delta" not in lines[0][1]
    assert state["1"]["count"] == 1


def test_login_del_lettore_non_produce_evento_ma_avanza_lo_stato():
    lines, state = ilo.plan_entries(
        [entry(user="ads-reader")], {}, "ads-reader", "2026-10-06T16:00:00+02:00"
    )
    assert lines == []
    assert state["1"]["count"] == 1


@pytest.mark.parametrize("bad", [0, -1, "2", None, True])
def test_count_non_valido_ferma_l_intero_giro(bad):
    with pytest.raises(ilo.PollError, match="Count IEL"):
        ilo.plan_entries([entry(count=bad)], {}, "ads-reader", "2026-10-06T16:00:00+02:00")


@pytest.mark.parametrize(
    "next_link", [ilo.ENTRIES + "?$skip=1", ilo.ENTRIES.rstrip("/") + "?$skip=1"]
)
def test_paginazione_legge_anche_i_membri_non_espansi(next_link):
    class Client:
        def __init__(self):
            self.calls = []

        def url(self, reference, base=None):
            return "https://192.0.2.15" + reference if reference.startswith("/") else reference

        def get_json(self, reference, *, base=None):
            self.calls.append(reference)
            if reference.endswith("Entries/"):
                return {
                    "Members": [{"@odata.id": ilo.ENTRIES + "1"}],
                    "Members@odata.nextLink": next_link,
                }
            if reference.endswith("Entries/1"):
                return entry()
            if reference.endswith("?$skip=1"):
                return {"Members": [{**entry(), "Id": "2"}]}
            raise AssertionError(reference)

    client = Client()
    entries = ilo.read_entries(client)
    assert [e["Id"] for e in entries] == ["1", "2"]
    assert len(client.calls) == 3


def test_url_e_token_restano_sullo_stesso_ilo(tmp_path):
    client = ilo.RedfishClient("192.0.2.15", tmp_path / "ca.pem", "a" * 64)
    try:
        assert client.http.trust_env is False
        assert client.http.verify == str(tmp_path / "ca.pem")
        adapter = client.http.get_adapter("https://192.0.2.15/redfish/v1/")
        assert adapter.poolmanager.connection_pool_kw["assert_fingerprint"] == "a" * 64
        with pytest.raises(ilo.PollError, match="esterno"):
            client.url("https://192.0.2.16/redfish/v1/Managers/1/")
    finally:
        client.http.close()


def test_sessione_redfish_usa_token_e_logout_esplicito(tmp_path, monkeypatch):
    client = ilo.RedfishClient("192.0.2.15", tmp_path / "ca.pem", "a" * 64)
    calls = []

    class Response:
        def __init__(self, status, headers=None):
            self.status_code = status
            self.headers = headers or {}

    def request(method, url, **kwargs):
        calls.append((method, url, dict(client.http.headers), kwargs))
        if method == "POST":
            return Response(
                201,
                {
                    "X-Auth-Token": "token-di-prova",
                    "Location": "/redfish/v1/SessionService/Sessions/7/",
                },
            )
        return Response(204)

    monkeypatch.setattr(client.http, "request", request)
    client.login("ads-reader", "password-di-prova")
    client.logout()
    assert [call[0] for call in calls] == ["POST", "DELETE"]
    assert calls[1][1].endswith("/SessionService/Sessions/7/")
    assert calls[1][2]["X-Auth-Token"] == "token-di-prova"
    assert all(call[3]["allow_redirects"] is False for call in calls)


def test_poll_scrive_prima_del_checkpoint_e_non_duplica(tmp_path, monkeypatch):
    host = "192.0.2.15"
    output = tmp_path / "ads"
    (output / host).mkdir(parents=True)
    state_dir = tmp_path / "state"

    class Client:
        def __init__(self, *_args):
            self.http = self

        def login(self, *_args):
            pass

        def logout(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(ilo, "RedfishClient", Client)
    monkeypatch.setattr(ilo, "read_entries", lambda _client: [entry()])
    monkeypatch.setattr(ilo, "source_lock", lambda _path: nullcontext())
    assert ilo.poll(host, "ads-reader", "secret", tmp_path / "ca", "a" * 64, state_dir, output) == 1
    assert ilo.poll(host, "ads-reader", "secret", tmp_path / "ca", "a" * 64, state_dir, output) == 0
    data = "".join(p.read_text(encoding="utf-8") for p in (output / host).glob("*.log"))
    assert data.count("Code=1131") == 1
    assert data.count("ads-ilo status=ok") == 2
    assert ilo.load_state(state_dir / f"{host}.json")["1"]["count"] == 1


def test_scrittura_fallita_non_avanza_il_checkpoint(tmp_path, monkeypatch):
    host = "192.0.2.15"
    output = tmp_path / "ads"
    (output / host).mkdir(parents=True)
    state_dir = tmp_path / "state"

    class Client:
        def __init__(self, *_args):
            self.http = self

        def login(self, *_args):
            pass

        def logout(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(ilo, "RedfishClient", Client)
    monkeypatch.setattr(ilo, "read_entries", lambda _client: [entry()])
    monkeypatch.setattr(ilo, "source_lock", lambda _path: nullcontext())

    def disk_full(*_args):
        raise OSError("disco pieno")

    monkeypatch.setattr(ilo, "append_lines", disk_full)
    with pytest.raises(OSError, match="disco pieno"):
        ilo.poll(host, "ads-reader", "secret", tmp_path / "ca", "a" * 64, state_dir, output)
    assert not (state_dir / f"{host}.json").exists()


def test_errore_di_lettura_chiude_la_sessione_redfish(tmp_path, monkeypatch):
    closed = []

    class Client:
        def __init__(self, *_args):
            self.http = self

        def login(self, *_args):
            pass

        def logout(self):
            closed.append("logout")

        def close(self):
            pass

    def failed_read(_client):
        raise ilo.PollError("risposta incompleta")

    monkeypatch.setattr(ilo, "RedfishClient", Client)
    monkeypatch.setattr(ilo, "read_entries", failed_read)
    monkeypatch.setattr(ilo, "source_lock", lambda _path: nullcontext())
    with pytest.raises(ilo.PollError, match="risposta incompleta"):
        ilo.poll(
            "192.0.2.15",
            "ads-reader",
            "secret",
            tmp_path / "ca",
            "a" * 64,
            tmp_path / "state",
            tmp_path / "ads",
        )
    assert closed == ["logout"]


def test_errore_del_poll_segnala_il_fallimento_senza_segreti(tmp_path, monkeypatch):
    host = "192.0.2.15"
    output = tmp_path / "ads"
    (output / host).mkdir(parents=True)
    password = tmp_path / "password"
    password.write_text("password-di-prova\n", encoding="utf-8")
    fingerprint = tmp_path / "pin"
    fingerprint.write_text("a" * 64, encoding="ascii")
    ca = tmp_path / "ca.pem"
    ca.write_text("certificato-di-prova", encoding="ascii")

    def failed_poll(*_args):
        raise ilo.PollError("token-segreto-di-prova")

    monkeypatch.setattr(ilo, "poll", failed_poll)
    monkeypatch.setattr(
        ilo.sys,
        "argv",
        [
            "ads-ilo.py",
            "--host",
            host,
            "--password-file",
            str(password),
            "--ca-file",
            str(ca),
            "--fingerprint-file",
            str(fingerprint),
            "--output-dir",
            str(output),
        ],
    )
    assert ilo.main() == 1
    data = "".join(p.read_text(encoding="utf-8") for p in (output / host).glob("*.log"))
    assert "ads-ilo status=error type=PollError" in data
    assert "token-segreto-di-prova" not in data
