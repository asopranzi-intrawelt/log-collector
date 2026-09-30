"""Rendering dei template di configurazione del collettore."""

import adsparams
from conftest import FIXTURES, ROOT, load_script

render = load_script("ads-render.py")
SOURCE = ROOT / "config" / "collettore"


def run(tmp_path, params_file, source=SOURCE):
    dest = tmp_path / "out"
    code = render.main(
        ["--parametri", str(params_file), "--sorgente", str(source), "--destinazione", str(dest)]
    )
    return code, dest


def test_nftables_ammette_le_sole_reti_dichiarate(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    nft = (dest / "etc" / "nftables.conf").read_text(encoding="utf-8")
    assert "{{" not in nft
    # subnet_server e' vuoto: l'insieme contiene la sola LAN, senza virgole pendenti.
    assert "ip saddr { 192.0.2.0/24 } udp dport 514 accept" in nft
    assert "ip saddr { 192.0.2.0/24 } tcp dport 6514 accept" in nft
    assert "ip saddr 203.0.113.10 tcp dport 22 accept" in nft
    assert "policy drop;" in nft


def test_seconda_rete_entra_nell_insieme(tmp_path, params_text):
    f = tmp_path / "p.yaml"
    f.write_text(
        params_text.replace('subnet_server: ""', 'subnet_server: "198.51.100.0/24"'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, f)
    assert code == 0
    nft = (dest / "etc" / "nftables.conf").read_text(encoding="utf-8")
    assert "ip saddr { 192.0.2.0/24, 198.51.100.0/24 } udp dport 514 accept" in nft


def test_file_statici_copiati_identici(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    for rel in [
        "etc/qemu/qemu-ga.conf",
        "etc/chrony/sources.d/inrim.sources",
        "etc/ssh/sshd_config.d/10-ads.conf",
        "etc/apt/apt.conf.d/52ads-unattended-upgrades",
    ]:
        assert (dest / rel).read_bytes() == (SOURCE / rel).read_bytes()
    assert not list(dest.rglob("*.template"))


def test_valore_mancante_non_scrive_niente(tmp_path, params_text, capsys):
    f = tmp_path / "p.yaml"
    f.write_text(
        params_text.replace('ip_admin_non_msp: "203.0.113.10"', 'ip_admin_non_msp: ""'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, f)
    assert code == 1
    assert not dest.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".ads-render-")]
    assert "rete.ip_admin_non_msp vuoto" in capsys.readouterr().err


def test_entrambe_le_reti_vuote_e_un_errore(tmp_path, params_text, capsys):
    f = tmp_path / "p.yaml"
    f.write_text(
        params_text.replace('subnet_lan: "192.0.2.0/24"', 'subnet_lan: ""'), encoding="utf-8"
    )
    code, _ = run(tmp_path, f)
    assert code == 1
    assert "rete.subnet_lan + rete.subnet_server vuoto" in capsys.readouterr().err


def test_il_file_di_esempio_non_basta_a_generare(tmp_path, capsys):
    # Con i soli valori di esempio, tutti vuoti, il rendering deve rifiutarsi: e' la prova che
    # nessun valore dell'ambiente viene inventato.
    code, dest = run(tmp_path, ROOT / "config" / "parametri.example.yaml")
    assert code == 1
    assert not dest.exists()


def test_destinazione_esistente_rifiutata(tmp_path, capsys):
    (tmp_path / "out").mkdir()
    code, _ = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 1
    assert "esiste già" in capsys.readouterr().err


def test_segnaposto_malformato_e_chiave_inesistente(tmp_path):
    p = adsparams.parse((FIXTURES / "parametri-completi.yaml").read_text(encoding="utf-8"))
    errors: list[str] = []
    out = render.render_text("{{ rete }} {{ rete.nessuna }} {{ rete.subnet_lan }}", p, "t", errors)
    assert out.endswith("192.0.2.0/24")
    assert any("segnaposto non valido" in e for e in errors)
    assert any("rete.nessuna: chiave inesistente" in e for e in errors)


def test_lista_resa_con_virgole(tmp_path):
    p = adsparams.parse((FIXTURES / "parametri-completi.yaml").read_text(encoding="utf-8"))
    errors: list[str] = []
    assert render.render_text("{{ sorgenti.qnap }}", p, "t", errors) == "192.0.2.4, 192.0.2.5"
    assert errors == []
