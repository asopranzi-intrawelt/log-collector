"""Rendering dei template di configurazione del collettore."""

import adsparams
from conftest import FIXTURES, ROOT, load_script

render = load_script("ads-render.py")
SOURCE = ROOT / "config" / "collettore"
ADMINS = 'ip_admin_non_msp:\n    - "203.0.113.10"\n    - "203.0.113.11"'


def run(tmp_path, params_file, source=SOURCE, *, strict=False):
    dest = tmp_path / "out"
    args = ["--parametri", str(params_file), "--sorgente", str(source), "--destinazione", str(dest)]
    if strict:
        args.append("--strict-syslog-sources")
    code = render.main(args)
    return code, dest


def test_nftables_ammette_le_sole_reti_dichiarate(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    nft = (dest / "etc" / "nftables.conf").read_text(encoding="utf-8")
    assert "{{" not in nft
    # subnet_server è vuoto: l'insieme contiene la sola LAN, senza virgole pendenti.
    assert "ip saddr { 192.0.2.0/24 } udp dport 514 accept" in nft
    assert "ip saddr { 192.0.2.0/24 } tcp dport 6514 accept" in nft
    assert "ip saddr { 203.0.113.10, 203.0.113.11 } tcp dport 22 accept" in nft
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
        "etc/sudoers.d/ads-admin",
    ]:
        assert (dest / rel).read_bytes() == (SOURCE / rel).read_bytes()
    assert not list(dest.rglob("*.template"))


def test_filtro_ilo_vuoto_disattiva_lo_smistamento(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    conf = (dest / "etc" / "rsyslog.d" / "10-ads.conf").read_text(encoding="utf-8")
    assert 'if ($fromhost-ip == "0.0.0.0" and $fromhost-ip == "::") then {' in conf
    assert "{{" not in conf


def test_filtro_ilo_usa_solo_indirizzi_validati(tmp_path, params_text):
    f = tmp_path / "p.yaml"
    f.write_text(
        params_text.replace("ilo: []", 'ilo: ["192.0.2.8", "192.0.2.9"]'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, f)
    assert code == 0
    conf = (dest / "etc" / "rsyslog.d" / "10-ads.conf").read_text(encoding="utf-8")
    assert 'if ($fromhost-ip == "192.0.2.8" or $fromhost-ip == "192.0.2.9") then {' in conf


def test_filtro_ilo_rifiuta_valori_che_iniettano_configurazione(tmp_path, params_text, capsys):
    f = tmp_path / "p.yaml"
    f.write_text(params_text.replace("ilo: []", 'ilo: ["192.0.2.8; stop"]'), encoding="utf-8")
    code, dest = run(tmp_path, f)
    assert code == 1
    assert not dest.exists()
    assert "sorgenti.ilo: indirizzo IP non valido" in capsys.readouterr().err


def test_seeweb_disattivato_senza_ip_sorgente(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    nft = (dest / "etc" / "nftables.conf").read_text(encoding="utf-8")
    conf = (dest / "etc" / "rsyslog.d" / "10-ads.conf").read_text(encoding="utf-8")
    assert "# Sorgente Seeweb non ancora autorizzata" in nft
    assert "ip saddr { 127.0.0.2 } udp dport 514 accept" not in nft
    assert 'if ($fromhost-ip == "0.0.0.0" and $fromhost-ip == "::") then {' in conf


def test_seeweb_apre_solo_udp_per_l_ip_validato_e_separa_i_log(tmp_path, params_text):
    f = tmp_path / "p.yaml"
    f.write_text(
        params_text.replace("seeweb_opnsense: []", 'seeweb_opnsense: ["127.0.0.2"]'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, f)
    assert code == 0
    nft = (dest / "etc" / "nftables.conf").read_text(encoding="utf-8")
    conf = (dest / "etc" / "rsyslog.d" / "10-ads.conf").read_text(encoding="utf-8")
    assert "ip saddr { 127.0.0.2 } udp dport 514 accept" in nft
    assert "ip saddr { 127.0.0.2 } tcp dport 6514 accept" not in nft
    assert 'if ($fromhost-ip == "127.0.0.2") then {' in conf
    assert 'dynaFile="AdsSeewebTechnicalFile"' in conf
    assert 'fileGroup="root" fileCreateMode="0640"' in conf


def test_seeweb_rifiuta_ip_non_valido_senza_scrivere_output(tmp_path, params_text, capsys):
    f = tmp_path / "p.yaml"
    f.write_text(
        params_text.replace("seeweb_opnsense: []", 'seeweb_opnsense: ["127.0.0.2; accept"]'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, f)
    assert code == 1
    assert not dest.exists()
    assert "sorgenti.seeweb_opnsense: indirizzo IPv4 non valido" in capsys.readouterr().err


def test_default_conserva_il_fallback_attuale(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    conf = (dest / "etc" / "rsyslog.d" / "10-ads.conf").read_text(encoding="utf-8")
    assert "AdsUnclassifiedFile" not in conf
    assert "ads-local" not in conf
    assert '    call ads\n}' in conf
    assert '''    } else {
        action(type="omfile" dynaFile="AdsFile" template="AdsLine"
               fileOwner="root" fileGroup="ads" fileCreateMode="0640"
               dirOwner="root" dirGroup="ads" dirCreateMode="0750")
    }
}

input(type="imudp"''' in conf


def test_strict_separa_sorgenti_note_ignote_e_accessi_locali(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml", strict=True)
    assert code == 0
    conf = (dest / "etc" / "rsyslog.d" / "10-ads.conf").read_text(encoding="utf-8")
    for ip in ("192.0.2.1", "192.0.2.2", "192.0.2.3", "192.0.2.4", "192.0.2.5"):
        assert f'$fromhost-ip == "{ip}"' in conf
    assert 'dynaFile="AdsUnclassifiedFile"' in conf
    assert '/var/log/ads-unclassified/%fromhost-ip%' in conf
    assert 'fileOwner="root" fileGroup="root" fileCreateMode="0640"' in conf
    assert 'dirOwner="root" dirGroup="root" dirCreateMode="0750"' in conf
    assert 'ruleset(name="ads-local")' in conf
    assert '    call ads-local\n}' in conf
    assert '    call ads\n}' not in conf


def test_strict_rifiuta_duplicato_anche_tra_classi(tmp_path, params_text, capsys):
    path = tmp_path / "params.yaml"
    path.write_text(
        params_text.replace('ilo: []', 'ilo: ["192.0.2.1"]'), encoding="utf-8"
    )
    code, dest = run(tmp_path, path, strict=True)
    assert code == 1 and not dest.exists()
    assert "duplicato in sorgenti.firewall_usg_flex" in capsys.readouterr().err


def test_strict_non_stampa_il_valore_ip_errato(tmp_path, params_text, capsys):
    path = tmp_path / "params.yaml"
    marker = "SENTINELLA-PRIVATA-DA-NON-STAMPARE"
    path.write_text(
        params_text.replace('firewall_usg_flex: "192.0.2.1"', f'firewall_usg_flex: "{marker}"'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, path, strict=True)
    err = capsys.readouterr().err
    assert code == 1 and not dest.exists()
    assert "sorgenti.firewall_usg_flex: indirizzo IPv4 non valido" in err
    assert marker not in err


def test_strict_rifiuta_ipv6_e_lista_ads_vuota(tmp_path, params_text, capsys):
    path = tmp_path / "params.yaml"
    path.write_text(
        params_text.replace('firewall_usg_flex: "192.0.2.1"', 'firewall_usg_flex: "::1"'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, path, strict=True)
    assert code == 1 and not dest.exists()
    assert "sorgenti.firewall_usg_flex: indirizzo IPv4 non valido" in capsys.readouterr().err

    path.write_text(
        params_text.replace('firewall_usg_flex: "192.0.2.1"', 'firewall_usg_flex: ""')
        .replace('nebula_switch_ap: ["192.0.2.2", "192.0.2.3"]', 'nebula_switch_ap: []')
        .replace('  qnap:\n    - "192.0.2.4"\n    - "192.0.2.5"', '  qnap: []'),
        encoding="utf-8",
    )
    code, dest = run(tmp_path, path, strict=True)
    assert code == 1 and not dest.exists()
    assert "elenco delle sorgenti AdS vuoto" in capsys.readouterr().err


def test_un_solo_amministratore_scritto_come_scalare(tmp_path, params_text):
    f = tmp_path / "p.yaml"
    f.write_text(params_text.replace(ADMINS, 'ip_admin_non_msp: "203.0.113.10"'), encoding="utf-8")
    code, dest = run(tmp_path, f)
    assert code == 0
    nft = (dest / "etc" / "nftables.conf").read_text(encoding="utf-8")
    assert "ip saddr { 203.0.113.10 } tcp dport 22 accept" in nft


def test_valore_mancante_non_scrive_niente(tmp_path, params_text, capsys):
    f = tmp_path / "p.yaml"
    f.write_text(params_text.replace(ADMINS, "ip_admin_non_msp: []"), encoding="utf-8")
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
    # Con i soli valori di esempio, tutti vuoti, il rendering deve rifiutarsi: è la prova che
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


def test_elenco_amministratori_generato(tmp_path):
    code, dest = run(tmp_path, FIXTURES / "parametri-completi.yaml")
    assert code == 0
    text = (dest / "etc" / "ads" / "amministratori").read_text(encoding="utf-8")
    assert text.splitlines()[-1] == "admuno, admdue"


def test_configurazione_host_proxmox(tmp_path):
    code, dest = run(
        tmp_path, FIXTURES / "parametri-completi.yaml", ROOT / "config" / "proxmox-host"
    )
    assert code == 0
    conf = (dest / "etc" / "rsyslog.d" / "90-ads.conf").read_text(encoding="utf-8")
    assert "{{" not in conf
    assert 'target="192.0.2.50" port="6514"' in conf
    assert 'StreamDriverPermittedPeers="ads-collector.example.com"' in conf
    assert 'freshStartTail="on"' in conf
    # L'access log va su un ruleset proprio e si inoltra solo il login (runbook del punto 3).
    assert 'ruleset="ads_pveproxy"' in conf
    assert 'if $msg contains "/access/ticket" then' in conf
    assert '$programname == "pvedaemon" and $msg contains "auth"' in conf
