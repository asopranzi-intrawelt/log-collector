---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - tests/**
last-verified-commit: 8d834dd
---

# Test di sviluppo

> Popolare leggendo la configurazione reale dei test. La checklist operativa locale dei test manuali vive invece in `_notes/TEST-CHECKLIST.md`, ignorata da git.

## Test runner e comandi

Quattro livelli, dal più rapido al più vicino agli apparati. Il primo è `python -m pytest -q tests`, che copre lettura dei parametri, rendering dei due alberi e comando della VM: 44 casi passati il 2026-10-06, senza rete. Il secondo è `bats tests/*.bats`, 22 prove su PKI e bootstrap in modalità di prova, già eseguite in Git Bash su Windows e Ubuntu 24.04 in WSL; su NTFS da Git Bash il permesso 0600 non si conserva e quel controllo si salta. Il terzo comprende due script con Docker: `bash tests/debian13/verifica-config.sh` controlla in `debian:trixie` nftables, SSH, sudo, guest agent, aggiornamenti di sicurezza, chrony e il ricevente rsyslog; `bash tests/debian12/verifica-sorgente-proxmox.sh` controlla in `debian:bookworm` l'invio TLS dell'host con la PKI del progetto. Entrambi richiedono rete per immagine e pacchetti. Il quarto è il collaudo manuale sulla VM e sulle sorgenti reali, documentato nei runbook; i container non sostituiscono la verifica delle righe realmente prodotte dagli apparati.

La verifica Debian 13 usa nomi `sshd-session` e `sshd-auth` osservati sul collettore e una riga Zyxel con l'anno dopo l'ora: controlla che `AdsLine` conservi i cinque campi e il messaggio del firewall, che il TCP in chiaro sulla 6514 e i messaggi locali estranei non siano registrati, e che file e directory abbiano i permessi previsti. La verifica Debian 12 controlla login SSH, autenticazioni di `pvedaemon` e richieste di login web; prova anche che non arrivino task, richieste periodiche, storico dell'access log o messaggi inviati con un nome di certificato non permesso. I messaggi delle prove sono derivati dai log reali con identificativi sostituiti: la prima prova di rsyslog usava `logger -t sshd` ed era verde mentre sul collettore i login, scritti da `sshd-session`, non arrivavano.

Due prove di non vacuità fatte il 2026-09-30. Togliendo da `ads-render.py` il filtro dei valori vuoti cadono 4 prove di rendering, togliendo la condizione sul tag VLAN ne cade 1; togliendo la riga `#clear` dalla configurazione di unattended-upgrades la verifica in container fallisce sull'origine non di sicurezza che Debian 13 abilita di default.

## Rotte e dati mockati

`tests/fixtures/parametri-completi.yaml` è un `parametri.yaml` compilato solo con indirizzi di documentazione (RFC 5737) e domini `example.com`, mai valori reali: lo richiede il controllo di anonimizzazione, che blocca il commit se un prefisso reale compare in un file pubblicabile. Il bootstrap non si prova contro un sistema vero ma nella sua modalità `--prova`, che stampa i comandi; il terzo livello verifica i file contro Debian 13 in container, e la prova sul collettore vero resta il collaudo della sezione 6 dell'handoff.

## Hook e controlli di qualità

Lint manuale: `ruff check bin tests`, `ruff format --check bin tests` e `shellcheck bin/*.sh tests/*.bats tests/debian12/*.sh tests/debian13/*.sh .githooks/pre-commit.d/*`. La disponibilità corrente di ruff, shellcheck e Bats sulla postazione va verificata prima di eseguirli: il 2026-09-30 erano stati usati da un ambiente temporaneo poi rimosso. In WSL Bats era stato clonato ed eseguito nella stessa chiamata; da Git Bash si usa `MSYS_NO_PATHCONV=1` con Docker per evitare la conversione del percorso montato. Il pre-commit esegue misura degli instruction file, anti-slop (avviso) e anonymization (bloccante); non esegue automaticamente pytest, Bats o i container. `.gitattributes` impone LF su `bin/`, `tests/`, `config/` e `.githooks/`, perché un CR in uno script Bash lo rompe su Linux.
