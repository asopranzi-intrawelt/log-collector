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
- [x] PKI emessa il 2026-09-30 in `%USERPROFILE%\ads-pki\` sulla postazione di Alessio Sopranzi; pacchetto per il collettore in `build/pacchetto/`, provato con `--prova`
- [x] netinst `debian-13.7.0-amd64-netinst.iso` scaricata in `local` e verificata con SHA-512 (2026-10-01)
- [x] VM 210 creata sull'host con il comando stampato da `ads-vm-command.py --iso`, configurazione verificata con `qm config` (2026-10-01)
- [x] `ads-bootstrap.sh` imposta il fuso `Europe/Rome` (l'installazione del 2026-10-01 ha il fuso centrale degli Stati Uniti), provato in bats
- [x] Debian 13.7 installata, `scsi1` su `/srv/ads` con `nodev,nosuid,noexec`, chiavi raccolte, `ads-bootstrap.sh` eseguito il 2026-10-01 (via SSH dalla postazione, ADR-012 per il desktop rimasto)
- [x] password locali (`tvezeni` temporanea, da cambiare al suo primo accesso; `asopranzi` quella dell'installer per decisione dell'utente), nome completo di `tvezeni`, ISO staccata, swap file da 1 GB: tutto il 2026-10-01
- [x] collaudo punto 1 superato; punto 2 superato nella parte di rete (SSH scartato dall'host non ammesso, 6514 ammessa), da completare con rsyslog attivo; punto 7 soddisfatto lato collettore, da completare sulle sorgenti

Stato delle voci [Non verificato] del componente, dall'handoff sezioni 1-3:

| Voce | Stato | Come si chiude |
|---|---|---|
| Sintassi di `allow-rpcs` in `/etc/qemu/qemu-ga.conf` | Verificata in container e sull'host il 2026-10-01: `qm agent 210 ping` risponde e `qm guest exec 210 -- id` è rifiutato con «Command guest-exec has been disabled» | Chiusa; collaudo punto 1 superato |
| rsyslog non installato di default su Debian 13 | Aperta: il container non è un'installazione netinst | Irrilevante per il risultato, perché `ads-bootstrap.sh` lo installa comunque; si annota dopo l'installazione con `dpkg -l rsyslog` |
| Modello CPU `x86-64-v2-AES` su PVE 8.x | Verificata il 2026-09-30 sullo snapshot Proxmox di network-design delle 07:30: il nodo è a pve-manager 8.3.4 e sette VM su dieci usano già `x86-64-v2-AES`; la VM100 usa già q35, OVMF ed efidisk con chiavi pre-caricate sullo storage SERVIZI | Chiusa per questo nodo; l'avviso di `ads-vm-command.py` resta perché vale per qualunque host 8.x |
| Origini di sicurezza di unattended-upgrades su Debian 13 | Verificata in container: Debian 13 abilita di default anche l'origine `label=Debian`, e senza `#clear` resterebbe attiva | Chiusa |
| Forma delle righe `pool` in `chrony.conf` di Debian 13 | Verificata in container: una riga `pool`, `sourcedir /etc/chrony/sources.d` presente, `chronyd -p` accetta il risultato | Chiusa |
| Fluent Bit confronta `Host` con il SAN del certificato (Inferenza, sezione 3) | Aperta | Si verifica nel pilota Windows (punto 7): il certificato porta FQDN e IP nel SAN, quindi regge entrambe le scelte |

Domande aperte:

La rete attuale smentisce due presupposti dell'handoff: nessun bridge di Proxmox è VLAN-aware e la LAN è un'unica rete, non una LAN più una VLAN server (scheda `design-and-security.md` di `D:/network-design`). Il codice ne tiene conto rendendo facoltativi `proxmox.vlan_server` e `rete.subnet_server`, ma resta da decidere con chi amministra la rete se il collettore debba nascere su `vmbr0` senza tag, come oggi è possibile, o aspettare la segmentazione del piano firewall di network-design; la regola nftables ammette 514 e 6514 dall'intera LAN finché non ci sono reti più strette. Una volta decisa, la scelta va riportata anche in network-design come nuova VM e nuova sorgente di traffico, secondo ADR-004.

Le due domande di ADR-007 sono chiuse: le postazioni hanno indirizzo fisso, e gli account sono personali (ADR-008). Prima del bootstrap ciascun amministratore genera sulla propria postazione una chiave SSH e consegna il solo file `.pub`, nominato `asopranzi.pub` e `tvezeni.pub` e raccolto nella cartella privata `_notes/chiavi/` della postazione di Alessio Sopranzi, ignorata da git, da cui arriva al collettore insieme al materiale TLS; la chiave è generata come `ads-collector_ed25519` in `.ssh` del profilo utente, senza passphrase per scelta dell'utente; al 2026-09-30 ci sono entrambe; dopo il bootstrap, dalla console, si imposta a ciascuno una password temporanea con scadenza immediata. Aperta dal 2026-10-01, misurata: con il desktop (ADR-012) la VM ha 546 MiB disponibili su 1.9 GiB; chiudere la sessione grafica quando non serve, o portare la RAM a 4 GB a VM spenta. Aperte dal 2026-10-01 per ADR-010 (`docs/modello-di-custodia.md`): chi custodisce la prova, cioè quale TSA e chi amministra il supporto immutabile, che non può essere Intrawelt né l'MSP; se la finestra del giorno in corso vada stretta; se serva un'analisi continua; la verifica annuale del punto 4.4 è decisa (ADR-011: IT Manager e IT Assistant, MSP in loro assenza, con la cautela della verifica incrociata). Candidati per la prova: TSA qualificata via RFC 3161 (InfoCert verificata sul manuale) e, come terzo custode da interrogare, Intrusa. Il componente 5 dipende dalla prima risposta. Aperta dal 2026-10-01: Wazuh. Lo studio `docs/confronto-wazuh.md` propone di tenere il collettore come sistema di registrazione, di aggiungere GravityZone come sorgente e di valutare Wazuh come livello di analisi dopo il pilota Windows; serve la decisione dell'utente e, se possibile, lo studio completo dell'MSP. Il nome `ads-collector.int.intrawelt.com` va registrato nel DNS del firewall, come prevede M25 di network-design, prima di configurare le sorgenti TLS.

## Feature: componente 2, rsyslog ricevente e accessi al collettore

Cosa fa: riceve i log delle sorgenti su 514/udp e 6514/tcp in TLS e li scrive in `/srv/ads/<ip>/<giorno>.log` nel formato `AdsLine`; instrada nello stesso ruleset gli accessi al collettore stesso (`sshd`, `sudo`, `su`, `login`, `systemd-logind`, `gdm-password`), in `/srv/ads/127.0.0.1/`. Punto 2 della sezione 7 dell'handoff.

Definition of done:

- [x] configurazione `config/collettore/etc/rsyslog.d/10-ads.conf`, installata e controllata dal bootstrap
- [x] verifica in container `debian:trixie`: ricezione UDP e TLS, TCP in chiaro scartato, accessi locali instradati, cinque campi, permessi
- [x] bootstrap rieseguito sul collettore con il pacchetto nuovo il 2026-10-01, senza errori e senza pacchetti nuovi (rieseguibile)
- [x] sul collettore vero: un accesso SSH di un amministratore compare in `/srv/ads/127.0.0.1/` come `sshd-session ... Accepted publickey`, con impronta della chiave (2026-10-01, dopo la correzione del filtro)
- [x] una riga inviata da una sorgente ammessa (l'host Proxmox) compare nella sua cartella, `root:ads` 0750, nel formato a cinque campi (2026-10-01)
- [ ] collaudo punto 2 completo: da una sorgente non ammessa nessuna scrittura; con la LAN unica /19 serve un mittente fuori da quella rete

Rinviato: filtro D7 del QNAP, che dipende dall'elenco AdS approvato (sezione 0, bloccante).

## Riconciliazione

Ultima verifica: 2026-09-30 al commit e3e6e69, con le modifiche di ADR-008 non ancora committate.
