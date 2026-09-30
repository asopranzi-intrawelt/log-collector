#!/usr/bin/env python3
"""Stampa il comando ``qm create`` della VM del collettore (handoff, sezione 1).

Non esegue nulla: il comando va rivisto e lanciato a mano sull'host Proxmox da chi lo
amministra. I valori dell'ambiente vengono da parametri.yaml e non hanno default: VMID,
storage, tipo di storage e versione di Proxmox sono obbligatori. Il tag VLAN si aggiunge solo
se ``proxmox.vlan_server`` è compilato, perché nella rete attuale nessun bridge è VLAN-aware
e un tag su un bridge che non lo è mette la VM su una VLAN che lo switch non trasporta.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adsparams  # noqa: E402

SYSTEM_GB = 16
DATA_GB_DEFAULT = 60  # WORM da 50 GB + margine; si ridimensiona dopo la misura dei volumi
STORAGE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
BRIDGE_NAME = re.compile(r"^vmbr[0-9]+$")


def _flag(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in ("true", "sì", "si", "yes", "1"):
        return True
    if normalized in ("false", "no", "0"):
        return False
    raise adsparams.ParamsError(f"{name}: atteso true o false, trovato {value!r}")


def build_command(params: adsparams.Params, data_gb: int) -> tuple[list[str], list[str]]:
    """Restituisce le parti del comando e gli avvisi da mostrare prima di eseguirlo."""
    warnings: list[str] = []
    pve = str(adsparams.require(params, "proxmox.pve_version"))
    vmid = str(adsparams.require(params, "proxmox.vmid"))
    storage = str(adsparams.require(params, "proxmox.storage"))
    ssd = _flag(str(adsparams.require(params, "proxmox.storage_is_ssd")), "proxmox.storage_is_ssd")
    bridge = str(adsparams.require(params, "proxmox.bridge"))
    vlan = str(adsparams.lookup(params, "proxmox.vlan_server"))

    if not vmid.isdigit() or not 100 <= int(vmid) <= 999_999_999:
        raise adsparams.ParamsError(f"proxmox.vmid: atteso un intero da 100, trovato {vmid!r}")
    if not STORAGE_NAME.match(storage):
        raise adsparams.ParamsError(f"proxmox.storage: nome non valido {storage!r}")
    if not BRIDGE_NAME.match(bridge):
        raise adsparams.ParamsError(f"proxmox.bridge: nome non valido {bridge!r}")
    if vlan and (not vlan.isdigit() or not 1 <= int(vlan) <= 4094):
        raise adsparams.ParamsError(f"proxmox.vlan_server: atteso 1-4094, trovato {vlan!r}")
    if not 1 <= data_gb <= 4096:
        raise adsparams.ParamsError(f"--dati-gb: valore fuori intervallo {data_gb}")

    major = pve.split(".", 1)[0].strip()
    if major == "8":
        warnings.append(
            "PVE 8.x: il modello CPU x86-64-v2-AES su 8.x è [Non verificato] (handoff, sez. 1)"
        )
    elif major != "9":
        warnings.append(f"PVE {pve}: parametri scritti per 8.x e 9.x, rivederli prima di eseguire")
    if vlan:
        warnings.append(
            f"tag VLAN {vlan} su {bridge}: verificare che il bridge sia VLAN-aware "
            "(scheda design-and-security di network-design)"
        )

    disk_opts = "iothread=1,discard=on" + (",ssd=1" if ssd else "")
    net = f"virtio,bridge={bridge}" + (f",tag={vlan}" if vlan else "")
    parts = [
        "qm",
        "create",
        vmid,
        "--name",
        "ads-collector",
        "--ostype",
        "l26",
        "--machine",
        "q35",
        "--bios",
        "ovmf",
        "--efidisk0",
        f"{storage}:1,efitype=4m,pre-enrolled-keys=1",
        "--cpu",
        "x86-64-v2-AES",
        "--sockets",
        "1",
        "--cores",
        "2",
        "--memory",
        "2048",
        "--balloon",
        "0",
        "--scsihw",
        "virtio-scsi-single",
        "--scsi0",
        f"{storage}:{SYSTEM_GB},{disk_opts}",
        "--scsi1",
        f"{storage}:{data_gb},{disk_opts},backup=0",
        "--net0",
        net,
        "--agent",
        "enabled=1,fstrim_cloned_disks=1",
        "--onboot",
        "1",
        "--startup",
        "order=1,up=30",
        "--protection",
        "1",
        "--tablet",
        "0",
    ]
    return parts, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parametri", required=True, type=Path, help="percorso di parametri.yaml")
    parser.add_argument(
        "--dati-gb",
        type=int,
        default=DATA_GB_DEFAULT,
        help=f"dimensione di scsi1 in GB (default {DATA_GB_DEFAULT})",
    )
    args = parser.parse_args(argv)
    try:
        params = adsparams.load(args.parametri)
        parts, warnings = build_command(params, args.dati_gb)
    except adsparams.ParamsError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1
    for line in warnings:
        print(f"avviso: {line}", file=sys.stderr)
    print(" ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
