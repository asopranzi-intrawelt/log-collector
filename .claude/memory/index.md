# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario. Vale per la branch dichiarata qui sotto e non per il progetto: se il progetto usa più alberi di lavoro e questa non è la branch più avanti, la memoria valida è quella dell'albero autorevole indicato (norma `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`).

## Stato

```
Branch attivo:        main
Commit di riferimento: PENDING-FIRST-COMMIT
Data snapshot:        2026-09-30
Albero autorevole:    unico
Remoto:               git@github-corp:asopranzi-intrawelt/log-collector.git (vuoto al 2026-09-30)
Template:             E:\template-claude-developing @ d732a25
```

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | PENDING-FIRST-COMMIT | stack dichiarato, nessun codice ancora |
| design-and-security.md | PENDING-FIRST-COMMIT | solo struttura |
| deployment.md | PENDING-FIRST-COMMIT | solo struttura; gate separazione-ambienti da fare |
| dev-testing.md | PENDING-FIRST-COMMIT | solo struttura |
| current-work.md | PENDING-FIRST-COMMIT | nessuna feature attiva |
| roadmap.md | PENDING-FIRST-COMMIT | solo struttura |

## Punto di ripresa

Dopo il primo commit: eseguire `sync-context` per ancorare le schede a HEAD; poi completare i gate rimasti aperti dell'inizializzazione (pacchetti, separazione fra test e produzione, MCP, README pubblico) e iniziare lo sviluppo dalla sezione 7 dell'handoff, verificando prima i valori bloccanti della sezione 0 in `config/parametri.yaml`.
