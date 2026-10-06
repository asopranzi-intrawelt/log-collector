---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
  - tests/**
last-verified-commit: 8d834dd
---

# Stack applicativo

> Documento di recupero più importante: tracciato, perché un collega che clona deve vederlo. Popolare leggendo il codice attuale, non inventare. Affinare `covers-paths` man mano.

## Stack e runtime

Al commit `8d834dd` il codice copre il componente 1, il ricevente rsyslog del componente 2 e l'host Proxmox come sorgente del punto 3; i runbook registrano l'installazione e i collaudi già eseguiti sulla VM Debian 13 e sulle sorgenti. Le configurazioni del collettore stanno in `config/collettore/`, quelle dell'host in `config/proxmox-host/`. Gli script Bash usano `set -euo pipefail` e si provano con Bats e nei container Debian; gli strumenti Python usano la libreria standard, mentre il bootstrap installa `python3-requests` per i componenti API previsti. `ruff` e `pytest` controllano il Python. Le impostazioni di firewall e NAS si eseguono dalle rispettive interfacce e sono descritte nei runbook, non implementate da script di questo repository.

## Alternative deliberatamente escluse

PyYAML per leggere `parametri.yaml`: escluso dal vincolo di una sola dipendenza esterna, e al suo posto `bin/adsparams.py` legge il sottoinsieme che il file usa davvero, rifiutando con il numero di riga ogni struttura che non riconosce. Un motore di template come Jinja: escluso per la stessa ragione; i segnaposto sono `{{ sezione.chiave }}` e `{{ a.b + c.d }}`, dove la seconda forma unisce più valori saltando i vuoti. Il tag VLAN e la seconda subnet obbligatori, come li scrive l'handoff: esclusi perché nella rete attuale nessun bridge è VLAN-aware e la LAN è un'unica rete (scheda `design-and-security.md` di `D:/network-design`), quindi entrambi sono facoltativi e il tag si aggiunge solo se compilato. Chiavi ECDSA per la PKI: esclusa a favore di RSA 3072 per compatibilità con GnuTLS di rsyslog sulle sorgenti e con OpenSSL di Fluent Bit.

## Flussi di codice e ruolo architetturale dei file

Il flusso parte dalla postazione dell'amministratore. `config/parametri.yaml`, ignorato da git, fornisce i valori dell'ambiente; `bin/ads-render.py` genera da `config/collettore/` e `config/proxmox-host/` alberi distinti in `build/`, senza scrivere se mancano parametri o la destinazione esiste. `bin/ads-vm-command.py` stampa il comando `qm create`, con lettore CD opzionale per la ISO (`--iso`), senza eseguirlo; `bin/ads-pki.sh` crea CA e certificato del collettore tenendo la chiave della CA sulla postazione. Sul collettore `bin/ads-bootstrap.sh` installa pacchetti, account personali e chiavi SSH, gruppo `ads-admin`, configurazioni e materiale TLS; verifica il montaggio di `/srv/ads` con `nodev,nosuid,noexec`, `nft -c`, `sshd -t`, `visudo -c` e `rsyslogd -N1` prima di attivare i servizi. Con `--prova` stampa i comandi senza eseguirli.

Il ricevente `config/collettore/etc/rsyslog.d/10-ads.conf` ascolta su 514/udp e 6514/tcp con TLS, instrada anche `sshd*`, `sudo`, `su`, `login`, `systemd-logind` e `gdm-password` locali e scrive `AdsLine` in `/srv/ads/<IP mittente>/<giorno>.log`, con permessi `root:ads` 0640 e cartelle 0750. Per i messaggi RFC 3164 e 5424 ricompone tag e testo in modo distinto; il parser RFC 3164 gestisce anche l'anno dopo l'ora delle righe Zyxel. `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` inoltra via TLS con verifica del nome del certificato i login SSH, `sudo`, `su`, `login`, le autenticazioni di `pvedaemon` e le richieste `/access/ticket` di `pveproxy`; usa code su disco e parte dalla fine dell'access log al primo avvio.

## Riferimenti a snippet

`bin/adsparams.py:parse` e `bin/adsparams.py:require` per la lettura dei parametri; `bin/ads-render.py:render_text` e `render_tree` per i segnaposto e l'albero generato; `bin/ads-vm-command.py:build_command` per il comando della VM; `bin/ads-bootstrap.sh:check_inputs` e `check_data_mount` per i controlli iniziali; `config/collettore/etc/nftables.conf.template` per il firewall locale; `config/collettore/etc/rsyslog.d/10-ads.conf` per ricezione e `AdsLine`; `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` per i filtri e l'invio dell'host.
