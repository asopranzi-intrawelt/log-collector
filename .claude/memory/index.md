# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario. Vale per la branch dichiarata qui sotto e non per il progetto: se il progetto usa più alberi di lavoro e questa non è la branch più avanti, la memoria valida è quella dell'albero autorevole indicato (norma `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`).

## Stato

```
Branch attivo:        main
Commit di riferimento: d69b587
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

Al 2026-10-02 i componenti 1 e 2 sono installati e verificati sul collettore vero, e l'host Proxmox invia al collettore i propri accessi: collaudo punto 3 superato per l'host (login web e SSH, riusciti e falliti, con i cinque campi). Procedure ed esiti nei tre runbook di `docs/`. Il 2026-10-02 il firewall USG FLEX è completo come sorgente (collaudi punti 3 e 7 superati, runbook `docs/runbook-componente-3-firewall.md`); dei NAS QNAP sono completi come sorgenti HERO e INTRA2 (TLS sulla 6514) e INTRA (TS-410U, solo UDP sulla 514, rischio residuo fino alla sostituzione del 2027), tutti con NTP su INRIM e collaudi punti 3 e 7 superati, runbook `docs/runbook-componente-3-nas.md`; aperta la decisione sulle righe SMB periodiche dell'account `backup` di Proxmox su INTRA; resta INTRA3 (TS-210, nel perimetro), da leggere sul dispositivo. Rinviati: filtro D7 del QNAP (elenco AdS bloccante), prova negativa del collaudo punto 2. Decisioni aperte: memoria della VM (ADR-012), custode della prova e analisi (ADR-010), Wazuh (ADR-009). Portato in network-design il 2026-10-02 (ADR-004) tutto quanto fatto fino ad allora: VM 210, regole del collettore, host Proxmox e firewall come sorgenti, modifiche agli apparati, fatti emersi. Da portare ancora: NAS quando configurati, con la correzione dell'inventario (INTRA2 è un TS-435XeU con QTS 5.2.9, non un TS-451U), la lentezza dell'interfaccia di INTRA2 con le misure del 02/10 per NAS-003 (diagnosi fermata qui per restare sullo scopo), l'accesso HTTP in chiaro e il firmware non aggiornato di INTRA2, nome DNS quando registrato, alias SSH Windows quando aggiunto, decisione sul backup della VM 210.

Il 2026-10-05, da una sessione dedicata alla VM 204 (bloccata dal 12/09 senza che nessuno se ne accorgesse), l'utente ha deciso ADR-013: le macchine virtuali di Proxmox entrano fra le sorgenti, a partire dalla VM 204, con accessi e heartbeat; il controllo di silenzio diventa anche il controllo di disponibilità delle VM e va anticipato; gli allarmi tecnici restano fuori dal collettore e condividono solo il relay SMTP, che diventa più urgente. Feature aperta in `current-work.md`; la parte tecnica è registrata in `D:/network-design` (#205-#207). Da valutare anche per la VM 210 watchdog e memoria, con lo stesso criterio.
