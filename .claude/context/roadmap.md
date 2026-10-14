---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths: []
last-verified-commit: 9ee87b4
---

# Roadmap

## Pannelli Seeweb censiti, raccolta ancora locale, 14/10/2026

Dopo il lettore email locale, il perimetro Seeweb comprende sette punti di accesso confermati, con appliance pubblica/privata probabilmente della stessa sorgente in base al Word storico. Verificare dashboard, identità/versione e registri esistenti prima di scegliere canali o configurare raccolta. Non assumere API di audit, protezione di tutte le VM o disponibilità di log dai soli URL. Il test AdS offline resta rimandato. La timeline della rete riporta ogni avanzamento e lacuna del collettore nello stesso giro.

## Report Seeweb letti e stati per unità verificati, 14/10/2026

Primo lettore Seeweb locale verificato su due report della casella IT condivisa: sei stati per unità, due Error il 13/10, 24 prove passate. Chiudere la milestone e confrontare poi una copia già ricevuta in una casella IT personale. Prima della produzione servono dedup reale, conferma dei job e della cadenza, canale con permessi minimi, silenzio e politiche dell'archivio backup. Tre archivi sulla stessa VM, frontend sysadmin e correlazione successivi; test AdS offline rimandato per scelta dell'utente.

## Milestone Nebula chiusa, offline rimandato e censimento email avviato, 13/10/2026

L'utente rimanda esplicitamente il collaudo degli accessi AdS offline dopo la spiegazione dell'impatto. Il gate rimane aperto prima dell'installazione Nebula. La priorità passa al censimento delle notifiche automatiche IT e dei backup Seeweb, partendo da un originale .eml recente e poi dai formati/esiti reali e dalle copie. Outlook Email ancora disponibile e non installato al controllo delle 17:32:59, suggerimento già presente. Tre archivi nella stessa VM, frontend sysadmin e correlazione successivi conservati.

## Login fallito 54HP verificato, tre casi API completati, 13/10/2026

I tre casi di accesso locale del 54HP sono verificati nei campioni API del 13/10, con ultimo fallimento osservato e report ricalcolato identico. Dopo la milestone, misurare limiti/troncamenti e offline prima del collaudo VM; la raccolta dei sei apparati e dei login NCC rimane aperta. Censimento email IT/Seeweb e tre archivi stessa VM conservati.

## Log operativi, email e correlazione futura

ADR-019 amplia il censimento ai servizi e ai backup, iniziando da Seeweb. L’utente conferma la VM esistente per archivi logici AdS, tecnici e backup; frontend LAN riservato al sysadmin e successiva correlazione/allarmi. Prima: censire le notifiche IT, verificare sorgenti attive, campioni, canali, deduplicazione e politiche. Outlook Email ancora da installare/collegare; nessun nuovo flusso in esercizio. Il collaudo Nebula continua. Dettaglio in docs/ricognizione-servizi-e-backup.md e docs/progetto-log-operativi-email.md.

> Direzione e priorità del progetto. Tracciata. Non è il work-log: qui sta dove si va, non cosa è già stato fatto.

## Direzione

Raccogliere e verificare gli accessi amministrativi di tutte le sorgenti applicabili dell'inventario, con prova per dispositivo, separazione dai log tecnici e tracciamento delle lacune. Dopo la raccolta, irrobustire la VM Debian che custodisce i log e aggiungere una piccola interfaccia web di consultazione limitata alla LAN e al sysadmin autorizzato.

## Priorità

1. Completare le sorgenti del componente 3 secondo `docs/matrice-sorgenti-rete.md`: il poller HTTPS Nebula è preparato e provato localmente su cinque accessi reali anonimizzati; misurare retention, limiti e offline cloud, collegare notifica esterna e coordinamento D-1, quindi collaudare con credenziale dedicata sulla VM; proseguire con 54HP, AP e gli altri nodi applicabili. La matrice include 57 nodi, ma la maggior parte non è ancora una sorgente collaudata.
2. Chiudere la separazione NAS D7 quando esisteranno nomina ed elenco AdS approvato, poi collaudare il componente 5 sul collettore e completare custodia e ancoraggio della prova.
3. Eseguire un intervento di hardening della VM con baseline, controlli negativi e verifica di accessi, aggiornamenti, backup e monitoraggio; requisiti precisi da definire sullo stato reale prima dei cambi.
4. Progettare e collaudare una GUI web minima, raggiungibile solo dalla LAN e autenticata per l'unico sysadmin autorizzato, con tracciamento della consultazione e permessi di sola lettura sui log. Il nome dell'account e la forma di autenticazione sono ancora da decidere.

## Idee e ipotesi da verificare

- [Verificato sul campione del 08/10] L'endpoint `event-logs` della OpenAPI Nebula restituisce i cinque eventi `AAA/authentication` del 30HP visti nella GUI NCC, con ora, account e IP. Restano da verificare durata dello storico, limiti e paginazione, dispositivo offline e gestione dei buchi.
- [Da verificare] Il canale scelto per Nebula consente di distinguere gli accessi AdS dai log tecnici senza perdita o duplicazione della prova.
- [Da definire] Identità autorizzata alla GUI web e nomina AdS formale; il ruolo operativo corrente non sostituisce l'atto scritto.
