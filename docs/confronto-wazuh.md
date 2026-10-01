# Confronto con l'architettura Wazuh proposta dall'MSP

> Studio richiesto dall'utente il 2026-10-01: perché il collettore non usa Wazuh, se convenga fondere le due proposte, e che cosa si prende da quella dell'MSP. Fonti: lo schema dell'architettura proposta dall'MSP, ricevuto come immagine il 2026-10-01 (lo studio completo da cui viene non è stato visto); la documentazione ufficiale di Wazuh 4.14, pagine *Quickstart* e *Event logging*, lette lo stesso giorno; `docs/studio-collettore-ads.md` per i requisiti del provvedimento e le scelte del collettore. Ciò che non viene da queste fonti è marcato come inferenza.

## Le due proposte in una riga

Lo schema dell'MSP mette al centro un *Wazuh manager* che riceve i syslog di Zyxel Nebula sulla porta 514, gli eventi di GravityZone e i webhook di NinjaOne attraverso un *gateway HTTPS in DMZ* con reverse proxy, e i log di Windows da un *agent Wazuh*; il manager applica decoder, regole e alert, invia gli eventi al *Wazuh indexer* con ricerca e retention di 90 giorni, mostrati dal *Wazuh dashboard* per ricerca, report e compliance, e scrive i log grezzi in un *archivio immutabile* per almeno sei mesi.

Il collettore di questo progetto è una VM Debian che riceve le stesse sorgenti in syslog e TLS, legge NinjaOne, Microsoft 365 e iLO con chiamate API in uscita, scrive un file per sorgente e per giorno, e ogni notte comprime i file di D-1, li lega in una catena di impronte, appone una marca temporale RFC 3161 di una TSA qualificata, copia su una cartella WORM del NAS e manda l'impronta alla Direzione (studio, sezione 5). Non ha regole né alert: ha un solo scopo, che è conservare le registrazioni degli accessi in una forma di cui si possa dimostrare l'integrità.

## La differenza che decide: che cosa si deve dimostrare

Il provvedimento del Garante del 27/11/2008 non chiede di rilevare attacchi né di produrre allarmi. Chiede che gli accessi degli amministratori di sistema siano registrati, che le registrazioni siano complete, inalterabili e verificabili nella loro integrità, e che siano conservate per almeno sei mesi (studio, sezioni 1 e 5). Wazuh è un SIEM: il suo mestiere è il secondo genere di cosa, cioè correlare eventi e avvisare, ed è molto bravo a farlo. La domanda giusta non è quale dei due strumenti sia migliore, ma quale dei due regga la richiesta specifica del provvedimento, e su quattro punti la risposta va nella stessa direzione.

| Requisito | Collettore del progetto | Architettura Wazuh dello schema |
|---|---|---|
| Completezza | ogni riga ricevuta finisce su file, filtrata solo per l'elenco nominativo degli AdS (D2) | di default il manager archivia solo gli eventi che fanno scattare una regola; la registrazione di tutti i messaggi richiede `logall` o `logall_json` in `ossec.conf` (documentazione *Event logging*) |
| Inalterabilità e verifica | catena di impronte più marca temporale qualificata, cioè un'ancora fuori dal collettore che chi lo amministra non può rifare (D3); copia WORM; impronta alla Direzione | la documentazione dice che i file compressi ogni giorno sono «digitally signed using MD5, SHA1, and SHA256»; il file `.sum` sta però accanto all'archivio sulla stessa macchina, quindi chi controlla il manager può riscrivere il log e ricalcolare le impronte. È lo stesso difetto per cui lo studio ha scartato l'HMAC del foglio (D3). L'*archivio immutabile* dello schema non dice come lo sia né chi lo controlli |
| Conservazione | 213 giorni sul collettore, poi la copia WORM (handoff, sezione 4) | l'indexer conserva 90 giorni; l'archivio grezzo dello schema almeno sei mesi; la documentazione avverte che Wazuh di suo conserva gli archivi per sempre, quindi la retention va costruita a parte |
| Indipendenza da chi è registrato | lo amministrano i due amministratori non MSP (ADR-007), con account personali (ADR-008) | lo schema non dice chi amministra il manager; se è l'MSP, chi è registrato controlla il sistema che lo registra |

L'ultima riga è la più pesante, e conviene leggerla come un fatto di architettura e non di fiducia. L'MSP amministra l'hypervisor e accede da remoto con NinjaOne (studio, sezione 6): i suoi tecnici sono amministratori di sistema, i cui accessi il collettore deve registrare. Un sistema di registrazione amministrato dalla stessa parte di cui registra gli accessi non soddisfa l'inalterabilità nemmeno se nessuno lo altera, perché non lo può dimostrare. La separazione dall'MSP è il presupposto da cui nasce la figura dell'amministratore non MSP nello studio, e vale qualunque prodotto si scelga.

## Gli altri punti tecnici

Le risorse. La documentazione di Wazuh 4.14 indica per un'installazione completa, da 1 a 25 agent, almeno 4 vCPU, 8 GiB di RAM e 50 GB per 90 giorni; la VM del collettore ha 2 vCPU e 2 GB. Sull'host lo snapshot di network-design del 2026-09-30 mostra circa 106 GB di RAM in uso su 134, quindi lo spazio ci sarebbe, ma è un ordine di grandezza diverso per una funzione che il provvedimento non chiede.

Il sistema operativo. Fra i sistemi raccomandati per i componenti centrali la pagina *Quickstart* elenca Amazon Linux, CentOS Stream, Red Hat Enterprise Linux e Ubuntu, non Debian; la VM appena creata è Debian 13 [Non verificato] se l'installazione su Debian sia comunque supportata dai pacchetti.

La superficie esposta. Lo schema riceve gli eventi di GravityZone e di NinjaOne con un *gateway HTTPS in DMZ*, cioè con un servizio raggiungibile da Internet che accetta richieste in ingresso. Il collettore legge NinjaOne con chiamate API in uscita (`ads-ninja.py`, handoff sezione 4) e non espone nulla verso l'esterno. [Inferenza] GravityZone si può leggere allo stesso modo con la sua API pubblica, invece che riceverne gli eventi in push; da verificare sulla documentazione Bitdefender prima di scriverlo.

L'agent su Windows. Lo schema usa l'agent Wazuh, lo studio Fluent Bit (D1). L'agent Wazuh parla solo con il manager Wazuh: adottarlo farebbe arrivare i log di Windows al collettore solo passando per Wazuh, cioè per un sistema esterno alla catena di integrità. Per questo, se Wazuh si aggiunge, Fluent Bit resta.

## Che cosa si prende dalla proposta dell'MSP

GravityZone. È l'unico contenuto dello schema assente dallo studio, e non è marginale: gli accessi alla console di GravityZone sono accessi di amministratori a un sistema che gestisce la sicurezza di tutte le postazioni, e vanno nella matrice delle sorgenti (studio, sezione 2) con i suoi cinque campi. Va aggiunta come sorgente del collettore, letta via API come NinjaOne, e la verifica dei campi disponibili si fa come per le altre sorgenti [Non verificato].

La rilevazione. Wazuh porta ciò che il collettore deliberatamente non fa: regole, alert, controllo dell'integrità dei file, vulnerabilità, cruscotti di conformità. Sono utili ai controlli ISO 27001 sul monitoraggio (A.8.15, A.8.16), su cui lavora il portale ISO 27001 di network-design, e non sono richiesti dal provvedimento.

## La fusione possibile, e in quale verso

Le due cose stanno insieme se il verso è questo: il collettore resta il sistema di registrazione, quello da cui si dimostra l'integrità, amministrato dagli amministratori non MSP; Wazuh, se lo si vuole, diventa un livello di analisi che riceve una copia degli stessi eventi, per esempio inoltrata dal collettore con rsyslog, e può anche essere amministrato dall'MSP, perché nessuna prova poggia su di lui. Un'alterazione su Wazuh non tocca nulla della catena, e un'alterazione sulla catena non passa inosservata. Il verso opposto, Wazuh al posto del collettore con un archivio da rendere immutabile in un secondo momento, sposta la parte difficile del problema dentro il riquadro dello schema che non la descrive.

Sul calendario la fusione non costa niente adesso: i componenti 1-6 dell'ordine di sviluppo restano identici, e il livello Wazuh si può decidere dopo il pilota Windows, quando i volumi misurati diranno anche quanto peserebbe.

## Decisione presa

Il 2026-10-01 l'utente ha confermato che lo studio dell'MSP consiste nel solo schema, e ha deciso di aggiungere GravityZone come sorgente (studio, D9; ADR-009). Lo schema non descrive l'archivio immutabile né chi amministri il manager, quindi il terzo esito qui sotto resta escluso; il secondo, Wazuh come livello di analisi alimentato dal collettore, si valuta dopo il pilota Windows.

## Decisione da prendere

Tre esiti, da registrare come ADR quando l'utente sceglie. Primo, solo collettore, con GravityZone aggiunta come sorgente: è la proposta di questo studio. Secondo, collettore più Wazuh come livello di analisi alimentato dal collettore, da decidere dopo il pilota. Terzo, Wazuh al posto del collettore: sconsigliato, per le ragioni della tabella, a meno che lo studio completo dell'MSP descriva un archivio immutabile con un'ancora esterna e un'amministrazione separata dall'MSP; prima di scartarlo del tutto conviene leggerlo.
