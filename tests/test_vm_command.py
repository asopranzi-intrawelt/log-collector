"""Comando qm create della VM del collettore."""

import pytest

import adsparams
from conftest import load_script

vm = load_script("ads-vm-command.py")


def build(params_text, data_gb=60, **overrides):
    text = params_text
    for key, value in overrides.items():
        section, name = key.split("__")
        old = next(line for line in text.splitlines() if line.startswith(f"  {name}:"))
        text = text.replace(old, f'  {name}: "{value}"')
    return vm.build_command(adsparams.parse(text), data_gb)


def opt(parts, name):
    return parts[parts.index(name) + 1]


def test_comando_con_i_parametri_dell_handoff(params_text):
    parts, warnings = build(params_text)
    assert parts[:3] == ["qm", "create", "140"]
    assert opt(parts, "--scsi0") == "local-lvm:16,iothread=1,discard=on,ssd=1"
    assert opt(parts, "--scsi1") == "local-lvm:60,iothread=1,discard=on,ssd=1,backup=0"
    assert opt(parts, "--efidisk0") == "local-lvm:1,efitype=4m,pre-enrolled-keys=1"
    assert opt(parts, "--memory") == "2048" and opt(parts, "--balloon") == "0"
    assert opt(parts, "--protection") == "1"
    assert warnings == ["nessuna --iso: la VM nasce senza supporto di installazione"]


def test_senza_vlan_nessun_tag(params_text):
    parts, _ = build(params_text)
    assert opt(parts, "--net0") == "virtio,bridge=vmbr0"


def test_con_vlan_tag_e_avviso(params_text):
    parts, warnings = build(params_text, proxmox__vlan_server="30")
    assert opt(parts, "--net0") == "virtio,bridge=vmbr0,tag=30"
    assert any("VLAN-aware" in w for w in warnings)


def test_storage_non_ssd_toglie_ssd(params_text):
    parts, _ = build(params_text, proxmox__storage_is_ssd="false")
    assert "ssd=1" not in opt(parts, "--scsi0")
    assert "ssd=1" not in opt(parts, "--scsi1")


def test_pve_8_avvisa_del_modello_cpu_non_verificato(params_text):
    _, warnings = build(params_text, proxmox__pve_version="8.4.1")
    assert any("Non verificato" in w for w in warnings)


def test_disco_dati_ridimensionabile(params_text):
    parts, _ = build(params_text, data_gb=120)
    assert opt(parts, "--scsi1").startswith("local-lvm:120,")


@pytest.mark.parametrize(
    ("override", "messaggio"),
    [
        ({"proxmox__vmid": ""}, "proxmox.vmid: valore vuoto"),
        ({"proxmox__vmid": "12"}, "proxmox.vmid: atteso un intero"),
        ({"proxmox__storage_is_ssd": ""}, "proxmox.storage_is_ssd: valore vuoto"),
        ({"proxmox__storage_is_ssd": "forse"}, "atteso true o false"),
        ({"proxmox__pve_version": ""}, "proxmox.pve_version: valore vuoto"),
        ({"proxmox__storage": "local lvm"}, "proxmox.storage: nome non valido"),
        ({"proxmox__bridge": "eth0"}, "proxmox.bridge: nome non valido"),
        ({"proxmox__vlan_server": "5000"}, "proxmox.vlan_server: atteso 1-4094"),
    ],
)
def test_valori_mancanti_o_invalidi_rifiutati(params_text, override, messaggio):
    with pytest.raises(adsparams.ParamsError, match=messaggio):
        build(params_text, **override)


def test_main_stampa_una_riga_sola(tmp_path, params_text, capsys):
    f = tmp_path / "p.yaml"
    f.write_text(params_text, encoding="utf-8")
    assert vm.main(["--parametri", str(f)]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1 and out.startswith("qm create 140 ")


ISO = "local:iso/debian-13.1.0-amd64-netinst.iso"


def test_con_iso_lettore_cd_e_ordine_di_avvio(params_text):
    parts, warnings = vm.build_command(adsparams.parse(params_text), 60, ISO)
    assert opt(parts, "--ide2") == f"{ISO},media=cdrom"
    assert opt(parts, "--boot") == "order=scsi0;ide2"
    assert not any("--iso" in w for w in warnings)


def test_iso_malformata_rifiutata(params_text):
    with pytest.raises(adsparams.ParamsError, match="--iso: atteso"):
        vm.build_command(adsparams.parse(params_text), 60, "debian.iso")


def test_il_punto_e_virgola_arriva_tra_apici(tmp_path, params_text, capsys):
    # Senza apici, sulla shell dell'host "order=scsi0;ide2" diventerebbe due comandi.
    f = tmp_path / "p.yaml"
    f.write_text(params_text, encoding="utf-8")
    assert vm.main(["--parametri", str(f), "--iso", ISO]) == 0
    out = capsys.readouterr().out
    assert "--boot 'order=scsi0;ide2'" in out
