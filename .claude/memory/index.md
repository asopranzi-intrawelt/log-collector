# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario. Vale per la branch dichiarata qui sotto e non per il progetto: se il progetto usa più alberi di lavoro e questa non è la branch più avanti, la memoria valida è quella dell'albero autorevole indicato (norma `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`).

## Stato

```
Branch attivo:        main
Commit di riferimento: 9ee87b4
Data snapshot:        2026-09-30
Albero autorevole:    unico
Remoto:               git@github-corp:asopranzi-intrawelt/log-collector.git (primo push di 9ee87b4 il 2026-09-30)
Template:             E:\template-claude-developing @ d732a25
```

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | 9ee87b4 | stack dichiarato, nessun codice ancora |
| design-and-security.md | 9ee87b4 | solo struttura |
| deployment.md | 9ee87b4 | solo struttura; gate separazione-ambienti da fare |
| dev-testing.md | 9ee87b4 | solo struttura |
| current-work.md | 9ee87b4 | nessuna feature attiva |
| roadmap.md | 9ee87b4 | solo struttura |

## Punto di ripresa

Schede ancorate a `9ee87b4` e gate dei pacchetti chiuso il 2026-09-30 (fix-typography, anti-slop, anonymization; esiti in `progress.md`). Prossimo: completare i gate rimasti aperti dell'inizializzazione (separazione fra test e produzione, README pubblico, procedura concreta del legame con network-design secondo ADR-004; MCP rifiutato per ora) e iniziare lo sviluppo dalla sezione 7 dell'handoff, verificando prima i valori bloccanti della sezione 0 in `config/parametri.yaml`.
