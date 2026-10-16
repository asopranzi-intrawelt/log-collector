# Normalizzazione, retention e capienza del collettore

Stato al 15/10/2026: requisiti confermati dall’operatore e progetto tecnico, non configurazione in esercizio. Il primo Agent Netdata risponde localmente sul fisico pilota; il Debian non riceve ancora questi eventi o metriche. Sviluppo richiesto sulla VM del collettore, con risorse Proxmox adeguabili dopo misure. [Studio Linux](osservabilita-linux-netdata.md), [runbook del pilota](runbook-monitoraggio-linux.md), [tre archivi logici](progetto-log-operativi-email.md) e [fonti e passi](fonti-osservabilita-linux.md) formano lo stesso percorso anche nel progetto rete.

## Lettura uniforme, provenienza conservata

Decisione: una vista di consultazione comune per tutte le sorgenti, costruita da adattatori specifici per formato/versione. Gli originali raccolti e i loro riferimenti restano disponibili secondo la politica del rispettivo archivio. Il modello proposto si ispira alle distinzioni fra tempi, risorsa, severità e corpo del [Logs Data Model OpenTelemetry](https://opentelemetry.io/docs/specs/otel/logs/data-model/); il JSON del progetto sarà un contratto locale versionato, non dichiarato automaticamente un payload OTLP conforme. Grafana presenterà i campi comuni e permetterà di aprire quelli specifici della sorgente.

| Campo della vista proposta v0 | Significato e regola |
|---|---|
| schema_version, event_id | Versione del contratto e identità dell’occorrenza acquisita; eventi distinti possono avere testo identico |
| archive | ads, technical, backup_outcomes oppure unclassified; la categoria incerta non diventa automaticamente AdS |
| observed_at, event_at, event_time_original | Ricezione osservata distinta dal tempo dichiarato; originale e offset conservati, UTC solo se determinabile; tempo evento ignoto resta null |
| source_id, host, service, transport_peer | Identità censita, host dichiarato e peer del trasporto distinti; un relay non diventa l’autore dell’evento |
| category, action, outcome | Valori controllati e documentati; esito unknown quando il messaggio non consente di determinarlo |
| severity_original, severity_normalized | Livello originale e mappatura dichiarata per sorgente; assenza del livello non equivale a normalità |
| actor, target | Account, eventuale identità personale verificata e oggetto; account condiviso non attribuito a una persona per deduzione |
| message, attributes | Messaggio leggibile e campi specifici preservati, con tipi e unità espliciti |
| parser_name, parser_version, parse_status, errors | Regola applicata, versione e stato ok/partial/unknown/error; campi estratti sempre riconducibili all’input |
| original_ref, original_sha256, record_locator | Riferimento all’oggetto originale effettivamente conservato, impronta e posizione della riga/unità; il digest non prova da solo autenticità o custodia indipendente |

Il formato AdsLine attuale conserva ricezione, IP di provenienza, tempo e hostname dichiarati e messaggio ricostruito dal template. Non si attribuisce retroattivamente ai file storici una cattura byte per byte del datagramma. La nuova vista deve riferire il record conservato senza riscrivere gli archivi giornalieri o i manifest esistenti. I [template rsyslog](https://docs.rsyslog.com/doc/configuration/templates.html) consentono mapping ed escaping JSON; prima dell’uso va verificata la disponibilità nella versione effettiva del Debian. Non basta concatenare stringhe per produrre JSON valido.

| Famiglia | Adattamento da verificare su campioni reali |
|---|---|
| Syslog/AdsLine, Linux e apparati | Separare peer, hostname dichiarato, tempo sorgente e ricezione; riconoscere formato e multilinea senza perdere il testo |
| Nebula | Conservare risposta originale, identità dell’apparato e chiave del record; classificazione degli accessi solo per formati collaudati |
| Report backup email | Conservare EML/MIME; un evento per unità/job quando presente; Date e Received non sono l’ora di esecuzione del job |
| API, journal e notifiche tecniche | Cursore/identità/tempi e severità propri della fonte; accesso via UI Netdata non prova inoltro al collettore |
| Metriche Netdata/Prometheus | Serie temporali con nome, etichette, unità e tempo; restano metriche, eventuale allarme diventa un evento tecnico separato |
| Output di collaudo | Evidenza della procedura con origine e limiti, non ingresso indiscriminato nell’archivio AdS |

Pipeline proposta: acquisizione dell’originale, identificazione del formato, parsing, normalizzazione, classificazione, scrittura della vista e indicizzazione della copia consultabile. I fallimenti producono stato esplicito, contatore e flusso di quarantena con capienza controllata; non scompaiono silenziosamente. La politica di deduplicazione deve distinguere una ritrasmissione dello stesso record da due eventi uguali; il solo hash del testo non basta. Un report con più unità mantiene i legami all’EML comune. D7, elenco AdS approvato e gate già aperti restano necessari.

## Politiche distinte di conservazione

| Oggetto | Politica da rispettare o definire | Controllo prima dell’esercizio |
|---|---|---|
| Originali AdS e manifest | 213 giorni previsti dallo studio esistente; custodia e gate del progetto invariati | Volume e riserva commisurati al periodo; nessuna cancellazione anticipata per fare spazio |
| Tecnici iLO | 90 giorni attivi dal 08/10; timer enabled/active e primo service riuscito | Giorno corrente più 89 precedenti; prova reale con deleted=0, permessi e limiti nel runbook iLO |
| Altri tecnici e quarantena | Durata e budget da approvare per sorgente e criticità | Origine, scadenza, quota, diritti, errori del parser e controllo della perdita |
| Esiti backup e originali EML | Durata da definire; storico dei job distinto dalla durata delle copie di backup | Più job per mail, copie inoltrate, mancata ricezione e prova di ripristino distinti |
| Copia normalizzata e indice Loki | Durata esplicita per archivio, coerente con autorizzazioni e politica degli originali | Retention realmente abilitata e cancellazione osservata, non solo parametro nel file |
| Metriche locali e centrali | Risoluzione, periodo e quota da scegliere misurando serie e crescita | Budget Netdata locale e TSDB centrale distinti; downsampling solo dove effettivamente configurato |
| Journal del sistema, log dei componenti, WAL, code e temporanei | Budget autonomi con spazio di emergenza | Contare rotazione, riavvio, compattazione, spool e stato persistente del lettore |

Le politiche AdS e iLO provengono dal documento canonico `docs/studio-collettore-ads.md` del progetto collettore, non da una nuova valutazione normativa in questo documento. Dove il periodo non è deciso non si assegna un valore implicito né si mantiene un default senza revisione. Ridurre una copia analitica non autorizza a eliminare il suo originale. I tempi di conservazione e le quote di byte hanno scopi diversi: se la quota fa espirare campioni prima del tempo desiderato, si deve rilevare e dichiarare il periodo realmente coperto.

La [retention Loki](https://grafana.com/docs/loki/latest/operations/storage/retention/) richiede la corretta configurazione del Compactor e dello storage scelto. Le [etichette Loki](https://grafana.com/docs/loki/latest/get-started/labels/) devono restare a cardinalità controllata: archive, famiglia di sorgente e servizio sono candidati; utente, IP, UID, hash e testo vanno di norma nel corpo o nei metadati, non in una label diversa per ogni evento. La verifica va ripetuta sulla release fissata, con un campione isolato a scadenza breve e originali di prova.

La [TSDB Prometheus](https://prometheus.io/docs/prometheus/latest/storage/) richiede margine per WAL, Head e compattazioni oltre ai blocchi conservati. La documentazione consultata suggerisce retention.size al massimo all’80-85% dello spazio dedicato a Prometheus: è un’indicazione del prodotto, non una soglia già applicata alla VM o agli originali. Anche i [limiti Netdata](https://learn.netdata.cloud/docs/netdata-agent/configuration/database) sono obiettivi per tier e possono essere superati temporaneamente. Il campo API multidb-disk-quota=1024 del pilota non prova un tetto complessivo di 1 GiB per installazione, journal e tutti i tier; configurazione effettiva e occupazione restano da leggere.

## Misure e budget prima di allocare risorse

La prima baseline guest del 16/10 è ricevuta: nproc=2, RAM totale 2030473216 byte e disponibile 923115520 byte; swap usata 482140160 byte. Sono misure puntuali, non un dimensionamento accettato; dettagli e disco AdS nella sezione finale. I circa 372 MiB letti nel servizio Netdata riguardano il fisico pilota: non sono il costo di Grafana, Loki e Prometheus né una raccomandazione di RAM per l’hub. La configurazione finale richiede baseline del Debian e del nodo Proxmox, conteggi delle sorgenti attive e misura sotto carico rappresentativo, includendo il ciclo di manutenzione notturna.

| Misura | Uso nel dimensionamento |
|---|---|
| Byte/eventi giornalieri per archivio, distribuzione delle dimensioni e picchi | Originali da conservare, throughput di parsing e ritardo accettabile |
| Crescita reale di originali, normalizzati, indice, WAL e cache | Evitare fattori di compressione/indicizzazione inventati e contare le copie multiple |
| Serie attive, scrape interval, campioni/giorno e variazione delle label | TSDB e carico di scraping; campioni/giorno circa serie medie per 86400 diviso intervallo in secondi |
| Byte liberi, inode liberi, volumi e mount reali | Riserva OS, quota per area e individuazione di un volume dati non montato |
| CPU, memoria disponibile/cgroup, swap, PSI, latenza disco e code | Margine sotto ingestione, query concorrenti, rotazioni e compressione D-1 |
| Ritardo e riempimento code, tasso d’ingresso e drenaggio | Finestra di disservizio assorbibile e tempo di recupero dopo il ripristino |
| RAM/CPU/storage del nodo Proxmox, thin pool, snapshot e backup | Capacità fisica prima di aumentare risorse nominali della VM |

Calcolo da compilare con le misure: spazio dati richiesto = somma dei byte/giorno osservati per il periodo di ciascuna copia, più code, WAL, indici, stato, temporanei di picco e riserva operativa. Per le code il riferimento è il picco di byte/secondo per la finestra di disservizio accettata, aggiungendo l’overhead misurato. Il tempo stimato a esaurimento è byte ancora utilizzabili sopra la riserva diviso crescita netta positiva in byte/secondo; senza crescita positiva il risultato è non applicabile, non una divisione per zero o garanzia di spazio infinito. Registrarvi finestra e qualità della stima.

I volumi o quote separati servono a impedire che indice e metriche consumino la riserva degli originali e del sistema. Una directory diversa sullo stesso filesystem non isola la capienza. Il progetto deve prevedere directory di mount dedicate e verifica del mount prima di scrivere, così un disco assente non riversa i dati sulla root. Backup, snapshot, ricostruzione degli indici e compressione possono tenere contemporaneamente due copie: includerle nel picco, non solo nella media giornaliera.

## Guardie proposte, non applicate

Le seguenti soglie sono valori iniziali di progetto da ricalibrare con la baseline e la finestra di intervento concordata. Sono condizioni alternative: un filesystem grande può avere percentuale buona e autonomia insufficiente; gli inode possono terminare prima dei byte.

| Segnale | Soglia iniziale proposta | Reazione da realizzare e verificare |
|---|---|---|
| Dati o root in crescita | Avviso dall’80%, critico dal 90%; oppure autonomia stimata sotto 7 giorni/48 ore | Notifica al sysadmin, analisi dell’area in crescita; riserva minima in GiB da fissare per volume |
| Inode | Avviso sotto il 10% libero, critico sotto il 5% | Individuare moltiplicazione di file/serie senza cancellare gli originali protetti |
| Code e ritardo | Avviso al 70% del budget, critico al 90%, più massima età e tempo previsto al pieno | Controllare il ricevitore e rallentare le copie analitiche dove supportato; perdita o blocco espliciti, mai promesse di assenza di perdita UDP |
| Memoria/CPU/I/O | Disponibilità, pressione e ritardi confrontati con la baseline su intervallo sostenuto | Budget per servizio; prima ridurre frequenza/query/concorrenza analitica e verificare ingestione |
| Mount, parser e raccolta | Mount atteso assente, errori/unknown in crescita, sorgente silente o heartbeat mancante | Allarme indipendente dal solo hub e stato degradato visibile |
| Manutenzione e retention | Job fallito, spazio non recuperato, retention reale inferiore alla richiesta | Errore esplicito, verifica conteggi e allarme; nessuna pulizia indiscriminata |

I [controlli systemd](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.resource-control.xml) possono attribuire priorità CPU/I/O e limiti di memoria sui sistemi compatibili. MemoryHigh provoca pressione/rallentamento; MemoryMax può portare all’OOM nel servizio. Perciò un limite rigido scelto senza misura può interrompere la raccolta: non si copia lo stesso budget su tutti i componenti. Definire margine per OS e ingestione, limitare separatamente le query/copie analitiche e verificare cgroup, versione e comportamento effettivi del Debian. Le priorità relative non sono prenotazioni assolute.

Le [code rsyslog](https://docs.rsyslog.com/doc/concepts/queues.html) richiedono sia limite di elementi sia spazio disco e comportamento al pieno; la sola queue.size non limita i byte della parte disk-assisted. La persistenza allo shutdown non è garanzia contro ogni crash. Anche [journald](https://raw.githubusercontent.com/systemd/systemd/main/man/journald.conf.xml) richiede budget di uso e spazio da lasciare libero: il vacuum rimuove file archiviati, non garantisce che i file attivi spariscano. Il namespace Netdata aggiunto dall’installer e il journal di sistema vanno entrambi censiti.

In emergenza la procedura deve proteggere gli originali: sospendere o contenere attività analitiche onerose secondo un piano provato, segnalare code/perdite e ripristinare capienza. Le cancellazioni seguono esclusivamente la politica della specifica area e il suo dry-run; nessun comando globale per liberare il disco. Un osservatore esterno deve rilevare hub indisponibile e mancata consegna delle notifiche: un allarme ospitato soltanto sulla VM satura non basta. Destinatario, canale e cadenza saranno concordati prima della messa in esercizio.

## Adeguamento tramite Proxmox e prove di accettazione

Prima di cambiare la VM si confrontano risorse guest e margine del nodo, storage reale e configurazione di memoria/ballooning. Il [manuale qm](https://pve.proxmox.com/pve-docs/qm.1.html), la [guida della memoria](https://raw.githubusercontent.com/proxmox/pve-docs/master/qm.adoc) e il [modello storage](https://raw.githubusercontent.com/proxmox/pve-docs/master/pvesm.adoc) sono riferimenti ufficiali; M29 resta il punto di coordinamento della standardizzazione. Aumentare il disco virtuale non dimostra che partizione, LVM e filesystem del guest siano già ampliati: rilevare la catena reale prima di preparare i comandi. Headroom fisico, pool thin, snapshot e backup si verificano separatamente. Nessuna nuova allocazione è eseguita o prescritta con numeri non misurati.

L’accettazione richiede un caso reale per ciascuna famiglia di log, con confronto input/campi/UI e errore su formato sconosciuto; orari senza fuso, account condivisi, multilinea, ritrasmissioni e più job per EML sono casi distinti. Riavvio, rotazione e breve interruzione del solo ricevitore di prova devono dimostrare continuità o rendere misurabile la perdita. Scadenza, compattazione, coda piena, mount assente e soglie di capienza si provano in ambiente isolato con dati fittizi, senza saturare il collettore reale o interrompere Ollama. Dopo il carico rappresentativo si misurano ingestione, query, pressione e riserva; solo allora si fissano taglie, retention dei nuovi archivi ed estensione agli altri host.

## Rettifica iLO e prossimo rilievo Debian, 16/10/2026

La tabella precedente riportava erroneamente il timer iLO come non installato. Il runbook iLO del collettore registra installazione verificata, attivazione del timer e service eseguito sotto systemd alle 15:29:04 del 08/10: status=ok mode=apply, deleted=0, filesystem_used_pct=44. Quella fotografia dimostra attivazione e un giro senza scaduti; non misura crescita odierna o conservazione su novanta giorni. Nessuna nuova azione sulla VM è stata eseguita in questa rettifica. Rimangono da realizzare budget e guardie generali qui proposti.

La raccolta locale della GPU del pilota è ora verificata; il budget dello stack sul Debian resta aperto. Il runbook del pilota prepara letture di RAM in byte, spazio/inode e dispositivi/mount, stato rsyslog, timer iLO e occupazione journal. Sono il primo rilievo del guest, non una misura di crescita o un’autorizzazione a cancellare/ridimensionare. Output del Debian ancora atteso; occorreranno poi volumi per archivio e headroom Proxmox prima di fissare risorse.

## Baseline Debian ricevuta; spazio AdS e attività swap da misurare, 16/10/2026

Prima baseline riferita dalla VM il 16/10 alle 10:29:01+02:00: 2 CPU disponibili al processo, RAM totale 2030473216 byte e disponibile 923115520 (880,35 MiB); swap occupata 482140160 (459,80 MiB), attività non misurata. Root /dev/sda2 ext4 al 44%, 8785534976 byte disponibili, inode al 16%. Secondo disco da 60 GiB con partizione ext4 /dev/sdb1 montata su /srv/ads e opzioni rw,nosuid,nodev,noexec,relatime; spazio e inode liberi di quel filesystem non misurati. df / /var /srv osserva il filesystem padre e non il sottomount AdS: le tre righe root sono coerenti e non vanno sommate. La prima lettura in chat che suggeriva un conflitto è corretta qui e nel work-log.

rsyslog active/running con MemoryCurrent 10113024 byte e CPUUsageNSec 24227915000: istantanea del cgroup e contatore cumulativo. Timer iLO con ultimo giro questa notte e prossimo domani, risultato del service non letto; journal 24M. Questi dati sostituiscono l’assenza di baseline guest, non attestano ancora spazio utilizzabile per lo stack, volumi/giorno, successo della retention o margine Proxmox. Le nuove letture preparate nel runbook misurano direttamente i due archivi, un du circoscritto con timeout e sei righe vmstat; output atteso. Nessuna guardia generale, quota o nuova retention applicata.

## Archivi misurati e processo snapshot della postazione tracciato, 16/10/2026

L’operatore esegue le letture mirate del Debian. Date riporta 16/10 alle 10:45:30+02:00; la scansione du termina con du_exit=0. Il successivo vmstat mostra sei rapporti, con cinque intervalli correnti alle 10:45:48-52. Il tempo tra Date e il primo rapporto non è il tempo di esecuzione di du: include anche l’autenticazione e gli altri comandi.

| Area | Misura | Limite |
|---|---|---|
| Volume AdS /dev/sdb1 ext4 | Totale 63088406528, usati 45211648, disponibili 59805298688 byte; uso 1% | Disponibili 55,70 GiB; distingue capacità del filesystem dalla partizione e dal disco di 60 GiB |
| Inode AdS | 3932160 totali, 111 usati, 3932049 liberi, 1% riportato | Non misura crescita futura o numero di eventi |
| Archivio AdS | du 43110400 byte, 41,11 MiB | Spazio allocato del percorso, distinto dal totale di df; non byte/giorno |
| Tecnici iLO | du 45056 byte, 44 KiB; filesystem /dev/sda2 root | Restano sulla root, disponibile 8785526784 byte e uso 44%; non sono isolati sul volume AdS |
| Swap occupata | vmstat swpd=470840 KiB | Coerente con la prima baseline, non è un tasso di trasferimento |
| Cinque intervalli correnti | si=0, so=0, wa=0, idle=100 come riportato; r=b=0 | Cinque secondi osservati; percentuali arrotondate, non copertura dei picchi |

La prima riga vmstat dà i tassi dal boot e non si conta come sesto intervallo corrente. Un esito du riuscito chiude la scansione circoscritta, non dimostra salute storage, assenza di perdite o conservazione per l’intero periodo. Trascrizione integrale del testo ricevuto e campi strutturati nei file privati operator-capacity-followup-transcript-20261016.txt e operator-capacity-followup-selected-20261016.json, con SHA nel manifest. Restano fonti già lette: [df](https://manpages.debian.org/trixie/coreutils/df.1.en.html), [du](https://manpages.debian.org/trixie/coreutils/du.1.en.html), [vmstat](https://manpages.debian.org/trixie/procps/vmstat.8.en.html).

Il dimensionamento deve inoltre considerare il nodo: 25,41 GiB free e quasi 8 GiB di swap occupata nella fotografia mattutina, massimi delle VM running superiori alla RAM fisica. Occorrono attività corrente, picchi e metadati thin. La retention degli snapshot sulla postazione è un processo distinto, tracciato nella rete con ISO-41/38; nessuna politica di pulizia degli originali AdS è cambiata.

## Sorgenti QA catalogate e ripresa con altro account preparata, 16/10/2026

Ricevuta chiusura manuale rete bff861b con push e verifica remoto riusciti; policy snapshot abilitata dall’operatore a 90 giorni, zero candidati/eliminati su 127 copie, primo giro pianificato ancora da osservare. Ripreso il focus Linux e poi richiesta la chiusura della sessione. Solo scaricate sul PC le immagini ufficiali Prometheus 3.13.4 LTS e Grafana OSS 13.2.4, digest registrati; nessuno stack/configurazione o container del pilota avviato, nessun nuovo flusso al Debian. Letta la segnalazione del produttore QA e il suo codice in lavorazione: due LXC Debian previsti (produzione/staging), istanza Ollama dedicata sul fisico GPU, non ancora censiti come in esercizio. Catalogo in docs/integrazione-log-qa-verifier.md: tecnici applicativi e tentativi, job, autenticazione, proxy, uso/costi riservati, runtime, OS e backup separati; coda cifrata e documenti esclusi dalla raccolta. Requisiti: messaggi italiani con tempi/codice/errore/batch/segmenti/tentativo; senza consenso, recupero locale transitorio almeno dieci minuti. Codice letto con default 600 s e intervallo 60 s, distinto dai retry della chiamata; nessuna prova runtime o finale del produttore svolta qui. Timestamp applicativo senza offset, intervallo segmenti non promosso a elenco completo; troncamento del messaggio non è sanitizzazione. Memoria, fonti, timeline, ISO e integrazione rete aggiornati nello stesso giro; specifica template e procedura di passaggio account aggiornate. Punto di ripresa: margine live Proxmox e pilota centrale metriche/log con guardie, normalizzazione e retention; GPU locale resta verificata 1/3/1, impatto aperto. Offline Nebula rimandato, Seeweb atteso, D7 e gate AdS invariati. Pulizia Codex in due tempi, sessioni vive protette e chiusura Git solo manuale. Nessun add/commit/push/deploy dell’assistente; modifiche parallele preservate.
