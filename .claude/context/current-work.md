---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/collettore/**
  - tests/**
last-verified-commit: 039e562
stato: componente 1 scritto e provato in locale, da eseguire sugli host
---

# Lavoro in corso

> La fonte di verità su cosa è fatto resta `memory/index.md` e il work-log, non le spunte di questo file. Ogni feature si descrive con lo schema fisso sotto, così il lavoro pendente è leggibile senza ricostruire il contesto da capo.

## Feature: componente 1, VM + Debian + nftables + chrony + TLS

Cosa fa: prepara tutto ciò che serve a creare la VM del collettore e a portarla a una Debian 13 configurata e raggiungibile in TLS, cioè il punto 1 della sezione 7 dell'handoff, che la sezione 0 non blocca. Scadenza dello studio per i punti 1-4: 23/10/2026.

File creati:

```
bin/adsparams.py                  lettura di parametri.yaml senza PyYAML
bin/ads-render.py                 albero di configurazione da config/collettore/ e parametri
bin/ads-vm-command.py             stampa il comando qm create, non lo esegue
bin/ads-pki.sh                    CA e certificato del collettore, sulla postazione admin
bin/ads-bootstrap.sh              installazione sul collettore, con --prova
config/collettore/etc/...         nftables (template), chrony, sshd, unattended-upgrades, qemu-ga
tests/                            pytest, bats, fixture, verifica Debian 13 in container
ruff.toml, .gitattributes         lint Python, LF su script e configurazioni
```

Definition of done:

- [x] codice e configurazioni scritti, lint e test verdi (38 pytest, 14 bats su Windows e Linux, verifica in container `debian:trixie`)
- [x] `config/parametri.yaml` compilato il 2026-09-30: valori Proxmox dallo snapshot di network-design, VMID 210, FQDN, indirizzo del collettore nella serie dei server confermato dall'utente, due amministratori (ADR-007, ADR-008); indirizzo verificato libero il 2026-09-30 dalla postazione di Alessio Sopranzi (ping senza risposta, vicino `Unreachable` con indirizzo fisico nullo)
- [x] PKI emessa il 2026-09-30 in `%USERPROFILE%ds-pki\` sulla postazione di Alessio Sopranzi; pacchetto per il collettore in `build/pacchetto/`, provato con `--prova`
- [ ] netinst `debian-13.7.0-amd64-netinst.iso` scaricata in `local` e verificata con SHA-512
- [ ] VM creata sull'host con il comando stampato da `ads-vm-command.py --iso`, dopo conferma esplicita
- [ ] Debian installata, `scsi1` montato su `/srv/ads` con `nodev,nosuid,noexec`, chiavi pubbliche dei due amministratori raccolte, `ads-bootstrap.sh` eseguito dalla console di Proxmox, password locali impostate
- [ ] collaudo punti 1, 2 e 7 della sezione 6 dell'handoff sul collettore vero

Stato delle voci [Non verificato] del componente, dall'handoff sezioni 1-3:

| Voce | Stato | Come si chiude |
|---|---|---|
| Sintassi di `allow-rpcs` in `/etc/qemu/qemu-ga.conf` | Verificata in container il 2026-09-30: `qemu-ga --dump-conf` di Debian 13 legge il file di default e riporta l'elenco | Resta la prova dall'host: `qm guest exec <VMID> -- id` deve fallire (collaudo punto 1) |
| rsyslog non installato di default su Debian 13 | Aperta: il container non è un'installazione netinst | Irrilevante per il risultato, perché `ads-bootstrap.sh` lo installa comunque; si annota dopo l'installazione con `dpkg -l rsyslog` |
| Modello CPU `x86-64-v2-AES` su PVE 8.x | Verificata il 2026-09-30 sullo snapshot Proxmox di network-design delle 07:30: il nodo è a pve-manager 8.3.4 e sette VM su dieci usano già `x86-64-v2-AES`; la VM100 usa già q35, OVMF ed efidisk con chiavi pre-caricate sullo storage SERVIZI | Chiusa per questo nodo; l'avviso di `ads-vm-command.py` resta perché vale per qualunque host 8.x |
| Origini di sicurezza di unattended-upgrades su Debian 13 | Verificata in container: Debian 13 abilita di default anche l'origine `label=Debian`, e senza `#clear` resterebbe attiva | Chiusa |
| Forma delle righe `pool` in `chrony.conf` di Debian 13 | Verificata in container: una riga `pool`, `sourcedir /etc/chrony/sources.d` presente, `chronyd -p` accetta il risultato | Chiusa |
| Fluent Bit confronta `Host` con il SAN del certificato (Inferenza, sezione 3) | Aperta | Si verifica nel pilota Windows (punto 7): il certificato porta FQDN e IP nel SAN, quindi regge entrambe le scelte |

Domande aperte:

La rete attuale smentisce due presupposti dell'handoff: nessun bridge di Proxmox è VLAN-aware e la LAN è un'unica rete, non una LAN più una VLAN server (scheda `design-and-security.md` di `D:/network-design`). Il codice ne tiene conto rendendo facoltativi `proxmox.vlan_server` e `rete.subnet_server`, ma resta da decidere con chi amministra la rete se il collettore debba nascere su `vmbr0` senza tag, come oggi è possibile, o aspettare la segmentazione del piano firewall di network-design; la regola nftables ammette 514 e 6514 dall'intera LAN finché non ci sono reti più strette. Una volta decisa, la scelta va riportata anche in network-design come nuova VM e nuova sorgente di traffico, secondo ADR-004.

Le due domande di ADR-007 sono chiuse: le postazioni hanno indirizzo fisso, e gli account sono personali (ADR-008). Prima del bootstrap ciascun amministratore genera sulla propria postazione una chiave SSH e consegna il solo file `.pub`, nominato `asopranzi.pub` e `tvezeni.pub` e raccolto nella cartella privata `_notes/chiavi/` della postazione di Alessio Sopranzi, ignorata da git, da cui arriva al collettore insieme al materiale TLS; la chiave è generata come `ads-collector_ed25519` in `.ssh` del profilo utente, senza passphrase per scelta dell'utente; al 2026-09-30 ci sono entrambe; dopo il bootstrap, dalla console, si imposta a ciascuno una password temporanea con scadenza immediata. Il nome `ads-collector.int.intrawelt.com` va registrato nel DNS del firewall, come prevede M25 di network-design, prima di configurare le sorgenti TLS.

## Riconciliazione

Ultima verifica: 2026-09-30 al commit e3e6e69, con le modifiche di ADR-008 non ancora committate.
