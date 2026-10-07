---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - config/**
  - docs/handoff-sviluppo-collettore.md
last-verified-commit: 30b4c1c
---

# Deployment

> Stato osservato nel repository e nei runbook al commit `30b4c1c`. Commit, push e interventi sugli host restano operazioni manuali dell'utente.

## Modello di separazione fra test e produzione

Il gate di scelta del modello del catalogo `.claude/skills/separazione-ambienti/RIFERIMENTO.md` non risulta concluso né registrato in un ADR: non si assegnano sigle ai suoi assi per deduzione. Stato di fatto: i test locali e nei container usano fixture con indirizzi di documentazione; la produzione è la VM 210 Debian 13 su Proxmox, installata e verificata nei runbook. Il repository ha la sola branch `main`, un solo albero di lavoro e nessuna pipeline CI presente. Generazione, trasferimento e installazione della configurazione sono azioni manuali. Restano da decidere e documentare con l'utente il modello di separazione e una procedura di ritorno alla configurazione precedente; nessun ambiente staging del collettore risulta predisposto.

## Livelli

Il primo livello esegue `pytest`, Bats e controlli statici senza accedere alla rete di produzione. Il secondo verifica la configurazione generata in container `debian:trixie` per il collettore e `debian:bookworm` per l'host Proxmox, usando dati fittizi. Il terzo è il collaudo manuale sulla VM e sulle sorgenti reali, registrato in `docs/runbook-componente-1.md`, `docs/runbook-componente-2.md` e nei runbook del componente 3. I domini, gli indirizzi e gli account dell'ambiente reale sono nel file privato `config/parametri.yaml`, non in questa scheda.

Il componente iLO è al primo livello: script, unità systemd e prove locali sono nel repository, mentre installazione sulla VM e collaudo su iLO reale sono ancora aperti e documentati in `docs/runbook-componente-4-ilo.md`. Le unità non sono attivate dal bootstrap; servono prima licenza verificata, account di lettura, certificato e cartelle con permessi corretti.

## Alberi di lavoro

Un solo albero di lavoro, `D:/log-collector` su `main`; non è un ambiente di produzione. La VM di esercizio non è un albero git di questo repository.

## Comandi

Sulla postazione di sviluppo, `python bin/ads-render.py --parametri config/parametri.yaml --sorgente config/collettore --destinazione <cartella-privata>` genera la configurazione del collettore; la stessa utility con `--sorgente config/proxmox-host` genera quella dell'host. `bin/ads-vm-command.py` stampa il comando per creare la VM e `bin/ads-pki.sh` emette i certificati sulla postazione amministrativa. `bin/ads-bootstrap.sh --prova <albero-generato> <cartella-tls> <cartella-chiavi>` mostra le azioni previste; l'esecuzione reale e ogni intervento sugli host richiedono un passo esplicito dell'utente e sono registrati nei runbook. I controlli prima dell'attivazione sono `nft -c`, `sshd -t`, `visudo -c` e `rsyslogd -N1`. Non c'è uno script di rilascio o rollback verificato nel repository; gli aggiornamenti eseguiti finora sono descritti nel runbook corrispondente.

Il nuovo script `bin/ads-ilo.py` usa un'istanza per IP iLO e le unità `config/collettore/etc/systemd/system/ads-ilo@.service` e `.timer`. I file di password, CA e impronta hanno percorsi privati sulla VM; prima dell'attivazione si esegue un giro manuale e si controllano formato delle righe, checkpoint e logout. L'installazione non è automatizzata dal bootstrap attuale.

## Variabili d'ambiente e segreti

I valori di rete, sorgenti, amministratori e API sono raccolti in `config/parametri.yaml`, ignorato da git e compilato a partire da `config/parametri.example.yaml`. Gli alberi prodotti in `build/` possono contenerli e restano ignorati da git. Le credenziali dei componenti futuri appartengono a `/etc/ads/secrets/` sul collettore; i certificati TLS e le chiavi private seguono la procedura descritta nella scheda di sicurezza. `ADS_ROOT` è usata da `ads-bootstrap.sh` per indirizzare l'installazione in un albero di prova, non contiene un segreto.
