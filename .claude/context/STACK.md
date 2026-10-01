---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
  - tests/**
last-verified-commit: 039e562
---

# Stack applicativo

> Documento di recupero più importante: tracciato, perché un collega che clona deve vederlo. Popolare leggendo il codice attuale, non inventare. Affinare `covers-paths` man mano.

## Stack e runtime

Dal 2026-09-30 il repository contiene il componente 1 dell'ordine di sviluppo (VM, Debian, nftables, chrony, TLS), scritto e provato in locale ma non ancora eseguito su un host reale. Lo stack osservato nel codice conferma quello dichiarato in `CLAUDE.md`: la destinazione è una VM Debian 13 su Proxmox; gli script Bash usano `set -euo pipefail`, passano `shellcheck` e si provano con `bats`; il Python è quello della distribuzione (3.13 su Debian 13), con la sola libreria standard nel componente 1, lint `ruff` con la configurazione di `ruff.toml` e test `pytest`. Le configurazioni di sistema stanno come albero in `config/collettore/`, che riproduce `/` del collettore.

## Alternative deliberatamente escluse

PyYAML per leggere `parametri.yaml`: escluso dal vincolo di una sola dipendenza esterna, e al suo posto `bin/adsparams.py` legge il sottoinsieme che il file usa davvero, rifiutando con il numero di riga ogni struttura che non riconosce. Un motore di template come Jinja: escluso per la stessa ragione; i segnaposto sono `{{ sezione.chiave }}` e `{{ a.b + c.d }}`, dove la seconda forma unisce più valori saltando i vuoti. Il tag VLAN e la seconda subnet obbligatori, come li scrive l'handoff: esclusi perché nella rete attuale nessun bridge è VLAN-aware e la LAN è un'unica rete (scheda `design-and-security.md` di `D:/network-design`), quindi entrambi sono facoltativi e il tag si aggiunge solo se compilato. Chiavi ECDSA per la PKI: esclusa a favore di RSA 3072 per compatibilità con GnuTLS di rsyslog sulle sorgenti e con OpenSSL di Fluent Bit.

## Flussi di codice e ruolo architetturale dei file

Il flusso va dalla postazione dell'amministratore al collettore. Sulla postazione `config/parametri.yaml`, copia locale ignorata da git, fornisce i valori dell'ambiente; `bin/ads-render.py` produce da `config/collettore/` un albero in `build/`, anch'esso ignorato perché contiene valori reali, e lo fa tutto o niente: con un segnaposto vuoto elenca i mancanti e non scrive nulla. `bin/ads-vm-command.py` stampa il comando `qm create` della sezione 1 dell'handoff, con in più il lettore CD della ISO di installazione che l'handoff non prevede (`--iso`), senza eseguirlo, e `bin/ads-pki.sh` crea CA e certificato del collettore tenendo la chiave della CA sulla postazione. Sul collettore `bin/ads-bootstrap.sh`, come root dalla console di Proxmox, installa pacchetti, utente di servizio `ads`, un account personale per ogni amministratore di `etc/ads/amministratori` con la sua chiave e il gruppo `ads-admin` che `sshd` e `sudo` ammettono (ADR-008), cartelle della sezione 4 dell'handoff, file di configurazione e materiale TLS, controlla il ruleset con `nft -c` prima di caricarlo e si ferma se `/srv/ads` non è montato con `nodev,nosuid,noexec`; con `--prova` stampa i comandi senza eseguirli.

## Riferimenti a snippet

`bin/adsparams.py:parse` e `bin/adsparams.py:require` per la lettura dei parametri; `bin/ads-render.py:render_text` per i segnaposto; `bin/ads-vm-command.py:build_command` per il comando della VM; `bin/ads-bootstrap.sh:check_inputs` per i controlli che precedono qualunque scrittura; `config/collettore/etc/nftables.conf.template` per il firewall locale; `config/collettore/etc/rsyslog.d/10-ads.conf` per la ricezione, il formato `AdsLine` e gli accessi al collettore stesso.
