---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
  - tests/**
last-verified-commit: 9710d4d
---

# Stack applicativo

> Documento di recupero più importante: tracciato, perché un collega che clona deve vederlo. Popolare leggendo il codice attuale, non inventare. Affinare `covers-paths` man mano.

## Stack e runtime

Il target `--switch-model XGS2220-54HP` è eseguito realmente il 13/10 dalla postazione: due risposte, una vuota e una con login. Report ricalcolato identico dai payload e dagli orari, candidato esatto e mapping del secondo apparato confermati; ritardo apparente 14,769 secondi. Il riferimento tecnico non è stato interrogato nella diagnosi, perché l'osservazione è positiva. La prova dimostra quel login, non logout, fallimenti, clock offset o servizio installato sulla VM.

`tools/watch-nebula-publication.py` aggiunge `--switch-model` per scegliere un modello univoco nello snapshot privato, senza dedurlo dal login storico del 30HP. `select_target` conserva il percorso precedente quando il parametro manca; con modello esplicito usa il riferimento più recente dello stesso apparato, anche tecnico. `--observation` verifica il target conservato accanto al report prima del client. Wrapper privato 54HP e piano preparati, nessuna nuova API; il controllo tecnico del 54HP non è una misura di copertura AdS.

La prova reale `--final-attempt` del 12/10 termina dopo cinque richieste: quattro array vuoti e un login 30HP. Report ricalcolato identico dai campioni; conferma umana successiva di 4,827975 secondi al timestamp del record. Prima risposta positiva a +38,030 secondi sul timestamp dichiarato, senza misura dello scarto dell'orologio. La diagnostica di timeout non è stata invocata. Misura e limiti nel runbook, nessun cambio al poller; il target del 54HP deve essere predisposto separatamente perché il wrapper seleziona dal riferimento storico 30HP.

La nuova modalità `--final-attempt` di `tools/watch-nebula-publication.py` osserva fino a dieci minuti con budget 41 POST; dopo un esito vuoto aggiunge soltanto le due letture diagnostiche già disponibili. La diagnosi non promuove il timeout a misura riuscita. Il wrapper privato `_notes/watch-nebula-publication-final.ps1` conserva il trasporto via stdin e attende ready prima del login; un Invio umano dopo il pannello registra `operator-confirmation.json`. Preparazione recuperata e provata il 12/10, misura reale ancora attesa.

La verifica dello storico è versionata in `8dba118`, finestre ed estremi in `48be07b`: cinque accessi concordanti e un riferimento su entrambi gli estremi dopo 93,356911 ore. Il 54HP resta senza accessi noti. `tools/watch-nebula-publication.py` osserva un login locale nuovo; il primo giro reale produce venti array vuoti con login confermato dall'operatore, quindi nessun ritardo misurato. La modalità `--observation` rilegge due ore precedenti l'avvio fino a ora corrente e un vecchio riferimento di controllo, con due POST. La rilettura reale delle 16:15:38 del 12/10 ritrova il controllo e 22 eventi unici, con un candidato login alle 15:12:23, fuori dalla prima finestra. Report ricalcolato identico; associazione all'ora umana ancora pendente. Candidati e grezzi privati, nessun identificativo nel riepilogo; nessuna installazione sulla VM.

Al commit `2456511` il codice copre il componente 1, il ricevente rsyslog del componente 2, l'host Proxmox come sorgente del punto 3 e il lettore Redfish iLO 5 alternativo. Remote Syslog, filtro iLO e ritenzione tecnica sono installati sul collettore, mentre Redfish e catena locale D-1 restano non installati. Il lavoro locale del 12/10 aggiunge il poller HTTPS Nebula, preparato e provato senza attivazione. Le configurazioni del collettore stanno in `config/collettore/`, quelle dell'host in `config/proxmox-host/`. Gli script Bash usano `set -euo pipefail` e si provano con test locali e container Debian; gli strumenti Python usano la libreria standard e `requests`, installato dal bootstrap come `python3-requests`. `ruff` e `pytest` controllano il Python. Le impostazioni di firewall e NAS si eseguono dalle rispettive interfacce e sono descritte nei runbook.

Il componente 4 ha un lettore Redfish versionato dal 2026-10-06: `bin/ads-ilo.py` usa `requests` per l'IEL di iLO 5, con test in `tests/test_ilo.py` e unità `ads-ilo@.service` e `ads-ilo@.timer`. Il codice non è installato sul collettore. Il dispositivo reale è un DL380 Gen10 con iLO Advanced: Remote Syslog sulla porta UDP 514 ha già consegnato login riusciti e fallito; Redfish resta alternativo. Dal 08/10 gli eventi tecnici iLO nuovi sono separati dagli accessi Browser, con ritenzione locale di 90 giorni; i file storici misti restano da trattare.

## Alternative deliberatamente escluse

PyYAML per leggere `parametri.yaml`: escluso dal vincolo di una sola dipendenza esterna, e al suo posto `bin/adsparams.py` legge il sottoinsieme che il file usa davvero, rifiutando con il numero di riga ogni struttura che non riconosce. Un motore di template come Jinja: escluso per la stessa ragione; i segnaposto sono `{{ sezione.chiave }}` e `{{ a.b + c.d }}`, dove la seconda forma unisce più valori saltando i vuoti. Il tag VLAN e la seconda subnet obbligatori, come li scrive l'handoff: esclusi perché nella rete attuale nessun bridge è VLAN-aware e la LAN è un'unica rete (scheda `design-and-security.md` di `D:/network-design`), quindi entrambi sono facoltativi e il tag si aggiunge solo se compilato. Chiavi ECDSA per la PKI: esclusa a favore di RSA 3072 per compatibilità con GnuTLS di rsyslog sulle sorgenti e con OpenSSL di Fluent Bit.

## Flussi di codice e ruolo architetturale dei file

Il flusso parte dalla postazione dell'amministratore. `config/parametri.yaml`, ignorato da git, fornisce i valori dell'ambiente; `bin/ads-render.py` genera da `config/collettore/` e `config/proxmox-host/` alberi distinti in `build/`, senza scrivere se mancano parametri o la destinazione esiste. `bin/ads-vm-command.py` stampa il comando `qm create`, con lettore CD opzionale per la ISO (`--iso`), senza eseguirlo; `bin/ads-pki.sh` crea CA e certificato del collettore tenendo la chiave della CA sulla postazione. Sul collettore `bin/ads-bootstrap.sh` installa pacchetti, account personali e chiavi SSH, gruppo `ads-admin`, configurazioni e materiale TLS; verifica il montaggio di `/srv/ads` con `nodev,nosuid,noexec`, `nft -c`, `sshd -t`, `visudo -c` e `rsyslogd -N1` prima di attivare i servizi. Con `--prova` stampa i comandi senza eseguirli.

Il ricevente `config/collettore/etc/rsyslog.d/10-ads.conf.template` ascolta su 514/udp e 6514/tcp con TLS, instrada anche `sshd*`, `sudo`, `su`, `login`, `systemd-logind` e `gdm-password` locali e scrive `AdsLine` in `/srv/ads/<IP mittente>/<giorno>.log`, con permessi `root:ads` 0640 e cartelle 0750. Per i messaggi RFC 3164 e 5424 ricompone tag e testo in modo distinto; il parser RFC 3164 gestisce anche l'anno dopo l'ora delle righe Zyxel. Il template installato dal 08/10 separa per IP iLO gli accessi espliciti dagli altri eventi e conserva questi ultimi in `/var/log/ads-ilo-other/`; la prova integrata Debian 13 e il collaudo Browser/test tecnico reale passano. `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` inoltra via TLS con verifica del nome del certificato i login SSH, `sudo`, `su`, `login`, le autenticazioni di `pvedaemon` e le richieste `/access/ticket` di `pveproxy`; usa code su disco e parte dalla fine dell'access log al primo avvio.

Il nuovo `ads-ilo.py` crea una sessione Redfish, percorre tutte le pagine dell'IEL, converte `Id`, `Created`, `Count`, `Updated`, `Code` e `Message` in righe `AdsLine` sotto `/srv/ads/<IP_ILO>/` e salva lo stato dopo aver sincronizzato il log. Il timer orario è soltanto preparato: non è installato né abilitato. Il runbook del componente 4 descrive prerequisiti e prove sul dispositivo.

`bin/ads-ilo-other-retain.sh` è il job separato del flusso tecnico iLO. La rotazione avviene già nel nome giornaliero prodotto da rsyslog; il job confronta la data nel nome con la finestra di 90 giorni inclusivi e scade solo i file più vecchi. `--dry-run` e `--apply` distinguono simulazione e cancellazione; `ads-ilo-other-retain.service` e `.timer` sono installati e il timer è attivo dal 08/10, con un giro manuale riuscito e zero scadenze. Questo albero usa `root:root`, separato da `/srv/ads/` e dalla sua catena D-1.

`bin/ads-nebula.py` legge gli eventi di un solo switch dalla OpenAPI con TLS verificato e credenziale separata. Configurazione privata JSON, intervalli temporali sovrapposti e deduplicazione SHA-256 alimentano un diario SQLite prima dell'append delle righe `AdsLine`. `collect` gestisce suddivisione temporale e selezione degli accessi; `recover` completa i byte pendenti e conferma il checkpoint. Servizio e timer per istanza sono preparati, con `LoadCredential`; nessuna installazione o notifica esterna. Limiti API e gate in `docs/runbook-componente-3-nebula.md` e ADR-018.

Il poller è versionato in `98c5dbd`; `tools/compare-nebula-history.py`, in `8dba118`, legge localmente i JSON diagnostici. Confronta tutti i sette campi degli accessi già noti e produce solo tempi, conteggi ed esiti, distinguendo età del campione ritrovato da retention massima e completezza non dimostrate. Storico e coerenza delle finestre sono misurati sul campione reale; i wrapper di acquisizione rimangono privati e manuali dalla postazione. Esercizio del poller sulla VM ancora atteso.

Sul dispositivo reale iLO Advanced è stata abilitata via Remote Syslog UDP 514: due login web riusciti, un fallimento ed eventi SNTP sono arrivati sul collettore, superando i collaudi punti 3 e 7. Il lettore Redfish resta non installato. Il successivo stadio locale è in `bin/ads-nightly.sh` e `bin/ads-verify.sh`: comprime D-1, scrive manifest SHA-256 concatenati e verifica che log originari e archivi coincidano. `ads-nightly.service` e `.timer` sono preparati ma non installati. La prova in `tests/test-nightly.sh` usa dati temporanei; restano la separazione dei log non AdS e l'ancoraggio esterno TSA/WORM prima della catena definitiva.

## Riferimenti a snippet

`bin/adsparams.py:parse` e `bin/adsparams.py:require` per la lettura dei parametri; `bin/ads-render.py:render_text` e `render_tree` per i segnaposto e l'albero generato; `bin/ads-vm-command.py:build_command` per il comando della VM; `bin/ads-bootstrap.sh:check_inputs` e `check_data_mount` per i controlli iniziali; `config/collettore/etc/nftables.conf.template` per il firewall locale; `config/collettore/etc/rsyslog.d/10-ads.conf.template` per ricezione, `AdsLine` e filtro iLO; `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` per i filtri e l'invio dell'host.

`bin/ads-ilo.py:read_entries` per la paginazione IEL, `plan_entries` per il confronto dei contatori, `poll` per l'ordine fra scrittura e checkpoint; `config/collettore/etc/systemd/system/ads-ilo@.service` per il processo orario non ancora attivato.
