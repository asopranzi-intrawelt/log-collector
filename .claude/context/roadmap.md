---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths: []
last-verified-commit: 9ee87b4
---

# Roadmap

> Direzione e priorità del progetto. Tracciata. Non è il work-log: qui sta dove si va, non cosa è già stato fatto.

## Direzione

Raccogliere e verificare gli accessi amministrativi di tutte le sorgenti applicabili dell'inventario, con prova per dispositivo, separazione dai log tecnici e tracciamento delle lacune. Dopo la raccolta, irrobustire la VM Debian che custodisce i log e aggiungere una piccola interfaccia web di consultazione limitata alla LAN e al sysadmin autorizzato.

## Priorità

1. Completare le sorgenti del componente 3 secondo `docs/matrice-sorgenti-rete.md`: la OpenAPI ha restituito i cinque accessi reali del 30HP, perciò progettare e collaudare il poller HTTPS con credenziale dedicata e controllo dei buchi; proseguire con 54HP, AP e gli altri nodi applicabili. La matrice include 57 nodi, ma la maggior parte non è ancora una sorgente collaudata.
2. Chiudere la separazione NAS D7 quando esisteranno nomina ed elenco AdS approvato, poi collaudare il componente 5 sul collettore e completare custodia e ancoraggio della prova.
3. Eseguire un intervento di hardening della VM con baseline, controlli negativi e verifica di accessi, aggiornamenti, backup e monitoraggio; requisiti precisi da definire sullo stato reale prima dei cambi.
4. Progettare e collaudare una GUI web minima, raggiungibile solo dalla LAN e autenticata per l'unico sysadmin autorizzato, con tracciamento della consultazione e permessi di sola lettura sui log. Il nome dell'account e la forma di autenticazione sono ancora da decidere.

## Idee e ipotesi da verificare

- [Verificato sul campione del 08/10] L'endpoint `event-logs` della OpenAPI Nebula restituisce i cinque eventi `AAA/authentication` del 30HP visti nella GUI NCC, con ora, account e IP. Restano da verificare durata dello storico, limiti e paginazione, dispositivo offline e gestione dei buchi.
- [Da verificare] Il canale scelto per Nebula consente di distinguere gli accessi AdS dai log tecnici senza perdita o duplicazione della prova.
- [Da definire] Identità autorizzata alla GUI web e nomina AdS formale; il ruolo operativo corrente non sostituisce l'atto scritto.
