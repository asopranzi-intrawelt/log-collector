# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario. Vale per la branch dichiarata qui sotto e non per il progetto: se il progetto usa più alberi di lavoro e questa non è la branch più avanti, la memoria valida è quella dell'albero autorevole indicato (norma `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`).

## Stato

```
Branch attivo:        main
Commit di riferimento: e3e6e69
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

Componente 1 dell'ordine di sviluppo (VM, Debian, nftables, chrony, TLS) scritto, provato in locale e committato in `e3e6e69` il 2026-09-30; dettaglio e voci [Non verificato] in `context/current-work.md`, scelta su VLAN e subnet in ADR-006. Per eseguirlo manca in `config/parametri.yaml` solo l'indirizzo del collettore; restano aperte le domande di ADR-006 e ADR-007. Senza quei valori si prosegue con il componente 2, rsyslog ricevente e accessi al collettore stesso, che si scrive e si prova allo stesso modo. Restano aperti i gate separazione-ambienti, README pubblico e procedura concreta del legame con network-design (ADR-004).
