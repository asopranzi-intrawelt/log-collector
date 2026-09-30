"""Lettura del sottoinsieme YAML di parametri.yaml."""

import pytest

import adsparams
from conftest import ROOT


def test_legge_scalari_liste_in_linea_e_a_blocco(params_text):
    p = adsparams.parse(params_text)
    assert p["proxmox"]["pve_version"] == "9.2.1"
    assert p["proxmox"]["bridge"] == "vmbr0"
    assert p["sorgenti"]["nebula_switch_ap"] == ["192.0.2.2", "192.0.2.3"]
    assert p["sorgenti"]["qnap"] == ["192.0.2.4", "192.0.2.5"]
    assert p["sorgenti"]["ilo"] == []
    assert p["rete"]["subnet_server"] == ""


def test_il_cancelletto_dentro_gli_apici_non_e_un_commento(params_text):
    p = adsparams.parse(params_text)
    assert p["api"]["ninjaone_base_url"] == "https://api.example.com/#frammento"


def test_legge_il_file_di_esempio_versionato():
    # Il file di esempio è il contratto: se diventa illeggibile, lo è anche la copia locale.
    p = adsparams.load(ROOT / "config" / "parametri.example.yaml")
    assert p["proxmox"]["bridge"] == "vmbr0"
    assert p["ads"]["elenco_approvato"] == []
    assert set(p) == {"proxmox", "rete", "collettore", "sorgenti", "ads", "integrita", "api"}


def test_require_rifiuta_il_valore_vuoto(params_text):
    p = adsparams.parse(params_text)
    with pytest.raises(adsparams.ParamsError, match="integrita.tsa_url: valore vuoto"):
        adsparams.require(p, "integrita.tsa_url")
    with pytest.raises(adsparams.ParamsError, match="sorgenti.ilo: valore vuoto"):
        adsparams.require(p, "sorgenti.ilo")


def test_lookup_rifiuta_la_chiave_inesistente(params_text):
    p = adsparams.parse(params_text)
    with pytest.raises(adsparams.ParamsError, match="proxmox.inesistente: chiave inesistente"):
        adsparams.lookup(p, "proxmox.inesistente")


def test_file_assente_rimanda_all_esempio(tmp_path):
    with pytest.raises(adsparams.ParamsError, match="parametri.example.yaml"):
        adsparams.load(tmp_path / "parametri.yaml")


@pytest.mark.parametrize(
    ("testo", "messaggio"),
    [
        ("a:\n  b: 1\n  b: 2\n", "riga 3: chiave a.b ripetuta"),
        ("a:\n  b: 1\na:\n", "riga 3: sezione 'a' ripetuta"),
        ("  b: 1\n", "riga 1: chiave fuori da una sezione"),
        ("a:\n  b: [1, 2\n", "riga 2: lista in linea non chiusa"),
        ("a:\n  b: 'x'\n", "riga 2: sintassi YAML non gestita"),
        ("a:\n  b: 1\n    - x\n", "riga 3: voce di lista sotto un valore scalare"),
        ("a:\n\tb: 1\n", "riga 2: tabulazione"),
        ("a:\n   b: 1\n", "riga 2: struttura non riconosciuta"),
    ],
)
def test_rifiuta_con_numero_di_riga_cio_che_non_riconosce(testo, messaggio):
    with pytest.raises(adsparams.ParamsError, match=messaggio):
        adsparams.parse(testo)
