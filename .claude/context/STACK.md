---
generated-from-commit: PENDING-FIRST-COMMIT
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
  - tests/**
last-verified-commit: PENDING-FIRST-COMMIT
---

# Stack applicativo

> Documento di recupero più importante: tracciato, perché un collega che clona deve vederlo. Popolare leggendo il codice attuale, non inventare. Affinare `covers-paths` man mano.

## Stack e runtime

Al 2026-09-30 il repository non contiene ancora codice: `bin/` e `tests/` sono vuoti, `config/` contiene solo `parametri.example.yaml`. Lo stack che segue è quello dichiarato in `CLAUDE.md` e nei due documenti di `docs/`, non ancora osservato nel codice: si conferma o si corregge quando il primo componente viene scritto.

- Destinazione: VM Debian 13 su Proxmox (parametri della VM nella sezione 1 dell'handoff).
- Script: Bash con `set -euo pipefail`, verificati con `shellcheck`, provati con `bats`.
- Python 3 della distribuzione Debian 13, con `requests` come sola dipendenza esterna; lint con `ruff`, test con `pytest` e risposte API registrate in `tests/fixtures/`.
- Componenti di sistema configurati da template in `config/`: rsyslog, nftables, chrony, fluent-bit, unità systemd.

## Alternative deliberatamente escluse

<da popolare leggendo la sezione dello studio che motiva le scelte, quando si implementa il primo componente>

## Flussi di codice e ruolo architetturale dei file

<da popolare quando esiste codice>

## Riferimenti a snippet

<puntatori a file e funzioni chiave, nella forma percorso:simbolo>
