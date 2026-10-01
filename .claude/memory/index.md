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

Al 2026-10-01 i componenti 1 e 2 sono installati e verificati sul collettore vero (VM 210 `ads-collector`): VM, Debian 13.7, rete fissa, nftables, chrony su INRIM, TLS, account personali, swap, rsyslog che riceve in UDP e TLS e registra gli accessi al collettore stesso. Procedure ed esiti in `docs/runbook-componente-1.md` e `docs/runbook-componente-2.md`. Rinviati: filtro D7 del QNAP (elenco AdS bloccante), prova negativa del collaudo punto 2 (serve un mittente fuori dalla LAN). Decisioni aperte: memoria della VM con il desktop (ADR-012), custode della prova e analisi (ADR-010), Wazuh come livello di analisi (ADR-009). Prossimo nell'ordine di sviluppo: punto 3, sorgenti firewall, NAS e host Proxmox; la configurazione dell'host (handoff, sezione 5) tocca un sistema dell'MSP e va concordata. Da portare in network-design (ADR-004): VM 210, nome DNS da registrare sul firewall, postazioni ammesse in SSH, i due gateway.
