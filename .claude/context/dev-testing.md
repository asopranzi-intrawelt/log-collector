---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - tests/**
last-verified-commit: 039e562
---

# Test di sviluppo

> Popolare leggendo la configurazione reale dei test. La checklist operativa locale dei test manuali vive invece in `_notes/TEST-CHECKLIST.md`, ignorata da git.

## Test runner e comandi

Tre livelli, dal più rapido al più vicino al collettore. Il primo è `python -m pytest -q tests`, che copre lettura dei parametri, rendering e comando della VM: 43 prove al 2026-09-30, senza rete. Il secondo è `bats tests/*.bats`, 22 prove su PKI e bootstrap in modalità di prova, verdi sia in Git Bash su Windows sia su Ubuntu 24.04 in WSL, dove il controllo dei permessi 0600 della chiave vale davvero; su NTFS da Git Bash il permesso non si conserva e quel controllo si salta. Il terzo è `bash tests/debian13/verifica-config.sh`, che con Docker attivo genera l'albero dalla fixture e lo controlla dentro `debian:trixie` con `nft -c`, `sshd -T` per ciascun amministratore, `visudo -c` e `sudo -l`, `qemu-ga --dump-conf`, `apt-config`, `unattended-upgrade --dry-run` e `chronyd -p`, e avvia rsyslog per una prova di ricezione (UDP RFC 5424 e 3164, TLS, TCP in chiaro da scartare, accessi locali da instradare, formato dei cinque campi, permessi); richiede rete per immagine e pacchetti e circa un minuto.

Regola appresa il 2026-10-01: i messaggi usati dalle prove si copiano da un log reale della sorgente, non si scrivono a partire da ciò che il codice si aspetta; la prima prova di rsyslog usava `logger -t sshd` ed era verde mentre sul collettore i login, scritti da `sshd-session`, non arrivavano.

Due prove di non vacuità fatte il 2026-09-30. Togliendo da `ads-render.py` il filtro dei valori vuoti cadono 4 prove di rendering, togliendo la condizione sul tag VLAN ne cade 1; togliendo la riga `#clear` dalla configurazione di unattended-upgrades la verifica in container fallisce sull'origine non di sicurezza che Debian 13 abilita di default.

## Rotte e dati mockati

`tests/fixtures/parametri-completi.yaml` è un `parametri.yaml` compilato solo con indirizzi di documentazione (RFC 5737) e domini `example.com`, mai valori reali: lo richiede il controllo di anonimizzazione, che blocca il commit se un prefisso reale compare in un file pubblicabile. Il bootstrap non si prova contro un sistema vero ma nella sua modalità `--prova`, che stampa i comandi; il terzo livello verifica i file contro Debian 13 in container, e la prova sul collettore vero resta il collaudo della sezione 6 dell'handoff.

## Hook e controlli di qualità

Lint: `ruff check bin tests` e `ruff format --check bin tests`, `shellcheck bin/*.sh tests/*.bats tests/debian13/*.sh .githooks/pre-commit.d/*`. Sulla macchina di sviluppo Windows ruff, shellcheck e bats non sono installati: il 2026-09-30 sono stati usati da un ambiente virtuale e da un clone di `bats-core` nello scratchpad di sessione, e la pulizia di fine sessione li rimuove, quindi vanno reinstallati finché non si decide dove tenerli. In WSL bats si clona ed esegue nella stessa chiamata, perché `/tmp` non sopravvive fra due invocazioni di `wsl`, e da Git Bash si passa `MSYS_NO_PATHCONV=1`, altrimenti il percorso dello script viene convertito. Il pre-commit esegue misura degli instruction file, anti-slop (avviso) e anonymization (blocca). `.gitattributes` impone LF su `bin/`, `tests/`, `config/` e `.githooks/`, perché un CR in uno script Bash lo rompe su Linux.
