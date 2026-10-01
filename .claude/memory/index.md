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

Al 2026-10-01 il componente 1 è completo e collaudato sul collettore vero (VM 210 `ads-collector` su Proxmox, Debian 13.7, procedura e esiti in `docs/runbook-componente-1.md`), da committare come milestone. Decisioni aperte: memoria della VM con il desktop mantenuto (ADR-012), custode della prova e analisi (ADR-010, `docs/modello-di-custodia.md`), Wazuh come livello di analisi dopo il pilota (ADR-009). Prossimo nell'ordine di sviluppo: componente 2, rsyslog ricevente e accessi al collettore stesso, con la prova completa del collaudo punto 2. Da portare in network-design (ADR-004): VM 210, indirizzo e nome DNS da registrare sul firewall, due postazioni ammesse in SSH, i due gateway diversi fra serie server e DHCP delle postazioni. Gate ancora aperti: separazione-ambienti, README pubblico.
