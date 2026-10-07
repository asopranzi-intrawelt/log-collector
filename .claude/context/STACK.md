---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
  - tests/**
last-verified-commit: a031a4c
---

# Stack applicativo

> Documento di recupero più importante: tracciato, perché un collega che clona deve vederlo. Popolare leggendo il codice attuale, non inventare. Affinare `covers-paths` man mano.

## Stack e runtime

Al commit `30b4c1c` il codice copre il componente 1, il ricevente rsyslog del componente 2, l'host Proxmox come sorgente del punto 3 e il lettore Redfish iLO 5 alternativo. L'iLO fisica è stata poi collaudata via Remote Syslog sul collettore reale, mentre il lettore Redfish non è stato installato. Lo stadio locale del componente 5 è preparato nell'albero di lavoro e provato solo in WSL. Le configurazioni del collettore stanno in `config/collettore/`, quelle dell'host in `config/proxmox-host/`. Gli script Bash usano `set -euo pipefail` e si provano con test locali e container Debian; gli strumenti Python usano la libreria standard e `requests`, installato dal bootstrap come `python3-requests`. `ruff` e `pytest` controllano il Python. Le impostazioni di firewall e NAS si eseguono dalle rispettive interfacce e sono descritte nei runbook.

Il componente 4 ha un lettore Redfish versionato dal 2026-10-06: `bin/ads-ilo.py` usa `requests` per l'IEL di iLO 5, con test in `tests/test_ilo.py` e unità `ads-ilo@.service` e `ads-ilo@.timer`. Il codice non è installato sul collettore. Il dispositivo reale è un DL380 Gen10 con iLO Advanced: Remote Syslog sulla porta UDP 514 ha già consegnato login riusciti e fallito; Redfish resta alternativo. Gli eventi tecnici iLO arrivano nello stesso file e richiedono uno smistamento prima della catena finale.

## Alternative deliberatamente escluse

PyYAML per leggere `parametri.yaml`: escluso dal vincolo di una sola dipendenza esterna, e al suo posto `bin/adsparams.py` legge il sottoinsieme che il file usa davvero, rifiutando con il numero di riga ogni struttura che non riconosce. Un motore di template come Jinja: escluso per la stessa ragione; i segnaposto sono `{{ sezione.chiave }}` e `{{ a.b + c.d }}`, dove la seconda forma unisce più valori saltando i vuoti. Il tag VLAN e la seconda subnet obbligatori, come li scrive l'handoff: esclusi perché nella rete attuale nessun bridge è VLAN-aware e la LAN è un'unica rete (scheda `design-and-security.md` di `D:/network-design`), quindi entrambi sono facoltativi e il tag si aggiunge solo se compilato. Chiavi ECDSA per la PKI: esclusa a favore di RSA 3072 per compatibilità con GnuTLS di rsyslog sulle sorgenti e con OpenSSL di Fluent Bit.

## Flussi di codice e ruolo architetturale dei file

Il flusso parte dalla postazione dell'amministratore. `config/parametri.yaml`, ignorato da git, fornisce i valori dell'ambiente; `bin/ads-render.py` genera da `config/collettore/` e `config/proxmox-host/` alberi distinti in `build/`, senza scrivere se mancano parametri o la destinazione esiste. `bin/ads-vm-command.py` stampa il comando `qm create`, con lettore CD opzionale per la ISO (`--iso`), senza eseguirlo; `bin/ads-pki.sh` crea CA e certificato del collettore tenendo la chiave della CA sulla postazione. Sul collettore `bin/ads-bootstrap.sh` installa pacchetti, account personali e chiavi SSH, gruppo `ads-admin`, configurazioni e materiale TLS; verifica il montaggio di `/srv/ads` con `nodev,nosuid,noexec`, `nft -c`, `sshd -t`, `visudo -c` e `rsyslogd -N1` prima di attivare i servizi. Con `--prova` stampa i comandi senza eseguirli.

Il ricevente `config/collettore/etc/rsyslog.d/10-ads.conf.template` ascolta su 514/udp e 6514/tcp con TLS, instrada anche `sshd*`, `sudo`, `su`, `login`, `systemd-logind` e `gdm-password` locali e scrive `AdsLine` in `/srv/ads/<IP mittente>/<giorno>.log`, con permessi `root:ads` 0640 e cartelle 0750. Per i messaggi RFC 3164 e 5424 ricompone tag e testo in modo distinto; il parser RFC 3164 gestisce anche l'anno dopo l'ora delle righe Zyxel. Il nuovo template, non installato, separa per IP iLO gli accessi espliciti dagli altri eventi e conserva questi ultimi in `/var/log/ads-ilo-other/`; la prova integrata Debian 13 passa. `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` inoltra via TLS con verifica del nome del certificato i login SSH, `sudo`, `su`, `login`, le autenticazioni di `pvedaemon` e le richieste `/access/ticket` di `pveproxy`; usa code su disco e parte dalla fine dell'access log al primo avvio.

Il nuovo `ads-ilo.py` crea una sessione Redfish, percorre tutte le pagine dell'IEL, converte `Id`, `Created`, `Count`, `Updated`, `Code` e `Message` in righe `AdsLine` sotto `/srv/ads/<IP_ILO>/` e salva lo stato dopo aver sincronizzato il log. Il timer orario è soltanto preparato: non è installato né abilitato. Il runbook del componente 4 descrive prerequisiti e prove sul dispositivo.

Sul dispositivo reale iLO Advanced è stata abilitata via Remote Syslog UDP 514: due login web riusciti, un fallimento ed eventi SNTP sono arrivati sul collettore, superando i collaudi punti 3 e 7. Il lettore Redfish resta non installato. Il successivo stadio locale è in `bin/ads-nightly.sh` e `bin/ads-verify.sh`: comprime D-1, scrive manifest SHA-256 concatenati e verifica che log originari e archivi coincidano. `ads-nightly.service` e `.timer` sono preparati ma non installati. La prova in `tests/test-nightly.sh` usa dati temporanei; restano la separazione dei log non AdS e l'ancoraggio esterno TSA/WORM prima della catena definitiva.

## Riferimenti a snippet

`bin/adsparams.py:parse` e `bin/adsparams.py:require` per la lettura dei parametri; `bin/ads-render.py:render_text` e `render_tree` per i segnaposto e l'albero generato; `bin/ads-vm-command.py:build_command` per il comando della VM; `bin/ads-bootstrap.sh:check_inputs` e `check_data_mount` per i controlli iniziali; `config/collettore/etc/nftables.conf.template` per il firewall locale; `config/collettore/etc/rsyslog.d/10-ads.conf.template` per ricezione, `AdsLine` e filtro iLO; `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` per i filtri e l'invio dell'host.

`bin/ads-ilo.py:read_entries` per la paginazione IEL, `plan_entries` per il confronto dei contatori, `poll` per l'ordine fra scrittura e checkpoint; `config/collettore/etc/systemd/system/ads-ilo@.service` per il processo orario non ancora attivato.
