# Segnalazione dal produttore QA: macchine e servizi da censire

> Scritta il 2026-10-16 dal progetto produttore QA (tool di quality check delle traduzioni, repository di origine privato), su richiesta dell'utente: le macchine e i servizi che crea entrano nel parco macchine da censire nel collettore e nel progetto rete. La segnalazione è stata riconciliata nei due cataloghi e resta come fonte del passaggio di consegne. I percorsi e i valori reali stanno nel livello privato del progetto di origine.

## Che cosa entra nel parco macchine

| Elemento | Dove | Stato al 2026-10-16 | Decisione di origine |
|---|---|---|---|
| LXC di produzione del tool QC: webapp FastAPI, nginx, systemd, Debian | nodo Proxmox | previsto, non creato | ADR-007, ADR-011 |
| LXC di staging del tool QC, gemello della produzione, spento quando non serve | nodo Proxmox | previsto, non creato | ADR-011 |
| Istanza Ollama dedicata al tool, servizio systemd separato con porta, utente e cartella dei modelli propri | macchina fisica con la GPU, la stessa di IntraLino | previsto, non installato | ADR-009 |

Dimensione prevista di ciascun LXC: 2 vCPU, 4 GiB di RAM, circa 16 GiB di disco sullo storage `<STORAGE_PROXMOX>`. La verifica di capacità del nodo è stata fatta con `scripts/Get-ProxmoxSnapshot.ps1` del progetto rete, in sola lettura.

## Che cosa interessa alla raccolta dei log

- L'istanza Ollama del tool è un secondo servizio sulla macchina GPU accanto a quello dell'assistente interno: va distinta nelle sorgenti, e la sua porta deve essere raggiungibile solo dagli LXC del tool (la porta dell'assistente interno rispondeva senza autenticazione alla LAN nel rilievo del produttore).
- Gli LXC del tool scrivono un registro dei costi con contatori e l'e-mail del PM che lancia la verifica, mai il contenuto dei documenti. La coda dei job su disco contiene bozze riservate dei clienti, è cifrata ed esclusa dai backup e dagli snapshot (ADR-010): non va raccolta né copiata.
- Il servizio autentica i PM con Microsoft 365 (Entra ID), con una registrazione dell'applicazione per ambiente.

## Che cosa manca e chi lo aggiorna

Il progetto del tool segnala qui ogni cambiamento nello stesso giro in cui avviene (ADR-014 del progetto di origine): creazione degli LXC, installazione dell'istanza Ollama, regole di firewall. Lo stato "previsto" di questa tabella diventa "in esercizio" solo con una nuova segnalazione, non per deduzione.
