---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths: []
last-verified-commit: 9ee87b4
---

# Roadmap

## WAN Seeweb completata: 29 regole manuali,14/10/2026

Lette screenshot 196 e 197 a risoluzione originale; 83 schermate totali (100-180 e 196-197), originali/SHA e note privati nei due progetti. La tabella WAN manuale è completa: 29 regole, 19 abilitate e 10 disabilitate; dieci automatiche ancora ripiegate. Nuove righe 20-29: POP3/IMAP/IMAPS/POP3S disabilitati, HTTPS 443 a GroupShare e TCP 902 a LAN net abilitati da any, UDP 500/4500 verso WAN ed ESP abilitati. Ultima regola 29 pass/in/quick IPv4 qualsiasi, sorgente qualsiasi, destinazione indirizzo WAN, porte any, logging abilitato: un permesso generale al firewall oltre alle regole VPN. Regole dedicate GUI80/443 disabilitate non bastano a dichiararne l'isolamento, perché la29 può ammettere quel traffico se non intercettato prima. Logging blu su 6 e 29, grigio sulle altre righe; log dei pacchetti non diventano autenticazioni. HTTPS GroupShare già consentito in 22: verificarlo, non presumere assenza di TLS; raggiungibilità e servizi effettivi443/8080/902 non provati dall'agente. Dossier e gap212/M31c-d aggiornati nella rete; nessuna regola, host o raccolta VM modificati. Solo log PF/charon locali osservati, audit GUI/SSH/config e target remoti ancora da verificare. Offline AdS Nebula rimandato; task Proxmox pianificato, PowerShell 7, dieci guest-agent 403 e audit fonti ADR aperti. Chiusure manuali chiarite con comandi PowerShell e conferma: salvataggio/pubblicazione dei documenti, non configurazione del firewall.

Stato finale riconciliato: network-design pulito e già pubblicato manualmente in 9e0e12c, confermato da ls-remote. Il commit include tutte le 83 prove censite, il dossier WAN completo, M31/gap 212 e timeline 202; nessuna nuova chiusura della rete da chiedere. Rimangono soltanto 11 file Seeweb del collettore da chiudere, con nove file del template esclusi. L'utente apre PowerShell su questo PC, esegue il comando con cd al collettore e conferma s per versionare/pubblicare i documenti. Nessuna configurazione firewall o raccolta VM modificata.

Dossier e 83 prove byte-identiche conservati nei due progetti; WAN manuale completa 29=19 abilitate+10 disabilitate, dieci automatiche da leggere. Controlli completi verdi nei due progetti dopo il supplemento, schede rigorose senza difetti. Timeline 202 eventi e tre HTML ISO allineati. La chiusura manuale parallela della rete ha incluso il primo dossier 81 e M31 nel commit e9745dd (integrità-docs); verificata la sua lista di 20 file, non ripetere quella milestone. Rimangono 11 file del collettore e 16 della rete da chiudere, manifesti da aggiornare ai rispettivi HEAD. Nessun add/commit/push/deploy o comando firewall dell'agente; nove template e lavoro di altra sessione preservati. Prossimo riscontro: menu Sistema espanso per logging/ruoli.

## Firewall Seeweb letto integralmente nelle schermate, 14/10/2026

Esaminati tutti gli 81 screenshot 100-180 del firewall, originali/SHA e note per pagina conservati privatamente nei due progetti. OPNsense 21.1.5 con FreeBSD 12.1 e OpenSSL 1.1.1k; hostname pubblico e LAN confermano SWB-02/SWB-07 sulla stessa sorgente. Tre NAT uno-a-uno; WAN superiore con 19 righe, regole provider da conservare e GroupShare 80/8080 abilitati da qualunque origine; sessioni HTTP stabilite su 80 osservate. LAN IPv4/IPv6 e IPsec ampi. IKEv1 aggressive/PSK/AES-128/SHA-1/DH2, PFS2 e selettori cloud /24 ↔ sede /16; due SA ESP e DPD/ACK correnti. Vicino NetApp con due sessioni TCP 445 dalla sede, proprietà/share/backup ignoti. Firmware della serie upstream fuori supporto e certificato GUI indicato in uso scaduto nel 2020: priorità di progettazione con Seeweb, senza modifiche. Log locali filterlog e charon visibili, accessi GUI/SSH e cambi ancora da verificare. Target audit 21.1.6, Syslog TLS 21.1.7 e formato filterlog21.1.9 non retroattribuiti alla21.1.5. WAN inferiore, automatiche, quattro rotte e opzioni logging/ruoli non letti:81 schermate non equivalgono a export integrale. Dettaglio docs/firewall-seeweb-opnsense.md; nessun comando sul firewall o raccolta Seeweb automatica attivata. Aggiornamento del progetto rete nello stesso giro con dossier, prove, roadmap e ISO; test offline AdS Nebula rimandato. Task Proxmox pianificato, PowerShell 7, dieci guest-agent403 e audit fonti ADR restano aperti.

Sincronizzazione completata: dossier autonomo e 81 originali identici anche nella rete, M31a-f e cinque gap 210-214 aperti, M14 integrato. ISO-25/27/30 in_corso, glossario aggiornato, timeline a 201 eventi e tre viste HTML allineate. Il generatore aveva rifiutato M31 senza glossario: aggiunte le spiegazioni, ripresa senza duplicare eventi. Collettore a f95354e e rete a f112e 6c, precedenti milestone manuali; nuovi file ancora non committati. Nessun cambiamento firewall/VM, nessuna raccolta Seeweb automatica. Controlli completi verdi nei due progetti, diff puliti e schede rigorose senza difetti; corretti i 42 trattini tipografici dei nuovi testi. Venti casi delle due chiusure manuali passati con git/python/conferma/attese sostituiti: stage occupato, file cambiato, perimetro diverso, HEAD cambiato, timeout/remoto diverso e ripresa senza secondo commit. Parser PowerShell verde; nessuna operazione git o impronta reali nel collaudo. Chiusura limitata a 11 file del collettore e 19 della rete; i nove file del template restano fuori. Le 24 prove pregresse del lettore restano riferite al codice invariato, non alle schermate. Skill intrawelt-design letta per i riferimenti degli artefatti futuri; nessuno stile del prodotto modificato.

Il censimento dei sette ingressi è chiuso manualmente in f95354e; il lettore resta in a5fe489. Le vecchie sezioni sottostanti conservano gli stati alla loro data. In questo giro si documentano le configurazioni e si progetta la raccolta; codice del lettore, test, servizi della VM e firewall non modificati.

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
