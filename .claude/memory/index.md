# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario. Vale per la branch dichiarata qui sotto e non per il progetto: se il progetto usa più alberi di lavoro e questa non è la branch più avanti, la memoria valida è quella dell'albero autorevole indicato (norma `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`).

## Stato

```
Branch attivo:        main
Commit di riferimento: c913760
Data snapshot:        2026-09-30
Albero autorevole:    unico
Remoto:               git@github-corp:asopranzi-intrawelt/log-collector.git (primo push di 9ee87b4 il 2026-09-30)
Template:             E:\template-claude-developing @ d732a25
```

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | 039e562 | componente 1 descritto dal codice |
| design-and-security.md | 9ee87b4 | solo struttura |
| deployment.md | 9ee87b4 | solo struttura; gate separazione-ambienti da fare |
| dev-testing.md | 039e562 | tre livelli di prova descritti |
| current-work.md | 039e562 | feature attiva: componente 1 |
| roadmap.md | 9ee87b4 | solo struttura |

## Punto di ripresa

Al 2026-10-02 i componenti 1 e 2 sono installati e verificati sul collettore vero, e l'host Proxmox invia al collettore i propri accessi: collaudo punto 3 superato per l'host (login web e SSH, riusciti e falliti, con i cinque campi). Procedure ed esiti nei tre runbook di `docs/`. Il 2026-10-02 il firewall USG FLEX è completo come sorgente (collaudi punti 3 e 7 superati, runbook `docs/runbook-componente-3-firewall.md`); del punto 3 restano i NAS QNAP, di cui va letto il firmware sul dispositivo, e la decisione su INTRA3, dismesso di fatto. Rinviati: filtro D7 del QNAP (elenco AdS bloccante), prova negativa del collaudo punto 2. Decisioni aperte: memoria della VM (ADR-012), custode della prova e analisi (ADR-010), Wazuh (ADR-009). Portato in network-design il 2026-10-02 (ADR-004) tutto quanto fatto fino ad allora: VM 210, regole del collettore, host Proxmox e firewall come sorgenti, modifiche agli apparati, fatti emersi. Da portare ancora: NAS quando configurati, nome DNS quando registrato, alias SSH Windows quando aggiunto, decisione sul backup della VM 210.
