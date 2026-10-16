# Progetto del pacchetto opzionale linux-observability

Richiesta dell’operatore del 15/10/2026, nata nel progetto del collettore e da completare dopo il collaudo del pilota reale: trasformare procedura, strumenti e stack locale in un pacchetto riproducibile e parametrizzato del template. Questo documento registra il mandato; il pacchetto non è ancora implementato, catalogato o disponibile per l’istanza automatica. La preparazione di un Agent non equivale al collaudo della console centrale.

## Obiettivo e collocazione

Pacchetto opzionale proposto: `.claude/templates/linux-observability/`, nel settore «Macchine e continuità operativa». Copre macchine Linux e hardware effettivamente esposto: Agent Netdata per le metriche, Prometheus per la raccolta, Grafana OSS per la consultazione, Loki e Alloy per i log tecnici. Il servizio deve funzionare in locale senza sottoscrizione Cloud. Un Parent Netdata rimane un’opzione motivata dalla topologia, non una dipendenza del primo profilo.

Il pacchetto si propone soltanto ai progetti che amministrano una macchina, una flotta o uno stack eseguibile. La sua presenza nel catalogo non autorizza installazioni su host reali: destinazione, impatto e comandi di rilascio restano espliciti. Nessun agente di rete, host reale o credenziale del progetto di origine entra nei file tracciati del template. La documentazione del template deve descrivere lo stato di verifica del pacchetto, senza presentare la prova su una macchina come copertura di ogni distribuzione o architettura.

## Profili da realizzare

| Profilo | Risultato atteso | Dipendenze e limiti |
|---|---|---|
| Agent Linux | Metriche locali, versione fissata, ascolto limitato, nessun claim e telemetria disattivata | Metodo nativo o statico scelto secondo il sistema reale; il pilota iniziale usa statico x86_64 |
| Hub locale | Console Grafana OSS con Prometheus, Loki e stato Alloy persistenti | Dimensionamento preventivo, autenticazione locale, TLS e porte esplicite; servizio su host o stack in container da collaudare |
| Inoltro eventi | Sorgenti OS/servizi verso un ricevitore parametrizzato, con coda e controllo del silenzio | Log originali distinti dalla copia Loki; permessi minimi sui file e classificazione prima dell’invio |
| GPU e sensori | Collector hardware attivati soltanto quando esistono strumenti e permessi compatibili | Nessuna installazione o sostituzione automatica del driver; NVIDIA richiede utility compatibile con il modulo caricato |

Le metriche non sono righe di log amministrativo e Loki non fornisce da solo una catena della prova. Il pacchetto generico deve consentire l’integrazione con un collettore esistente senza imporne schema, nomi di archivi o obblighi normativi specifici. Nel progetto di origine gli accessi AdS, i tecnici e i backup mantengono tre archivi logici distinti; questo è un requisito di quell’istanza, non un nome di directory da copiare in ogni progetto.

## Parametri ed elementi riproducibili

| Area | Parametri da esplicitare |
|---|---|
| Identità e inventario | Identificativo stabile della sorgente, distribuzione/init, architettura, ruolo fisico/VM e gruppi di raccolta |
| Artefatti | Release, URL ufficiali, SHA-256 dei singoli file, eventuali digest delle immagini, licenze e data della verifica |
| Rete | Bind iniziale locale, porte, sorgenti ammesse, percorso del ricevitore/scraper, TLS e nomi verificati |
| Stato e risorse | Directory dati, memoria/CPU, retention, quote, crescita disco, backup, posizioni Alloy e recupero |
| Accesso | Autenticazione della console, ruoli e file privati delle credenziali, senza password predefinite nel repository |
| Eventi | File o journal autorizzati, etichette non sensibili, coda, classificazione, silenzio e destinazioni |
| Modalità | Preflight e rendering senza modifiche; installazione, configurazione, verifica e ripristino come passi distinti |

Nessuna tag `latest` o release implicita nei file destinati al rilascio: le versioni e le impronte appartengono a un manifest verificabile. Un nome contenente `latest` nel bundle offline ufficiale è accettabile solo se il manifest lo lega all’impronta di una release fissata; non si tratta come selezione dinamica dell’ultima versione. I valori reali dell’istanza si compilano in un file privato ignorato da Git, partendo da un esempio senza identificativi. I valori dell’ambiente non vengono dedotti da IP o hostname presenti nei campioni.

## Materiali del pacchetto

Servono README con mappa di istanziazione e recap d’uso, guida tecnica con motivazioni e fonti, esempio di parametri, manifest delle versioni, strumenti di preflight/rendering, installazione e verifica dell’Agent, configurazioni dello stack locale e procedura di ripristino. Le fonti e gli esiti devono distinguere ciò che è documentato dal produttore, ciò che è provato in ambiente isolato e ciò che è misurato su una macchina reale.

Gli script devono fermarsi se mancano parametri, compare un’installazione precedente non riconciliata, fallisce un download o non coincide un checksum. Una riesecuzione non deve sovrascrivere dati, utenze o configurazioni esistenti senza un confronto e una copia verificabile. Il primo avvio non deve precedere la configurazione del bind. Disabilitare aggiornamenti automatici comporta una procedura documentata di aggiornamento controllato, non l’abbandono degli aggiornamenti.

## Criteri di completamento

| Prova | Che cosa deve dimostrare |
|---|---|
| Artefatto alterato | Un hash errato ferma il flusso prima di qualsiasi esecuzione con privilegi |
| Parametri e rendering | Assenza di segnaposto nei file eseguibili prodotti, valori quotati, errori prima delle modifiche |
| Installazione e primo avvio | Versione effettiva, servizio, listener, telemetria e mancato claim verificati sulla macchina scelta |
| Raccolta metrica | Campioni dell’Agent presenti in Prometheus con identità stabile e consultabili da Grafana |
| Percorso log | Un evento reale entra nel percorso autorizzato e si ritrova in Loki; duplicazione, rotazione e riavvio misurati |
| Persistenza e recupero | Riavvio dello stack con dati e posizioni conservati; ripristino dei volumi/configurazioni provato |
| Impatto | Confronto prima/dopo di risorse e del servizio ospitato, nello stesso contesto e con carico concordato |
| Uso in altro progetto | Render o istanziazione isolata con valori differenti, senza riferimenti al progetto d’origine |

Prima della pubblicazione nel catalogo si aggiorneranno `PACKAGES.md`, il README del template tramite `sync-readme`, gli eventuali contatori e il controllo d’istanza. L’utente eseguirà commit, push e propagazione: il mandato di creare il pacchetto non autorizza l’agente a compierli automaticamente. Le modifiche estranee già presenti nel template restano fuori dal lavoro.

## Stato iniziale e fonti

Il pilota del 15/10 ha completato preflight, dry-run e preparazione del bundle ufficiale 2.12.1 con checksum OK; il controllo del percorso successivo ha fermato l’installazione. Dopo il recupero l’operatore ha installato Netdata 2.12.1: servizio presente, fermo e abilitato al boot, configurazione loopback scritta, opt-out e backup presenti, updater disattivato con conferma nell’output. Primo avvio ora ricevuto: active/running, listener loopback, ACLK non online e campioni CPU/RAM locali; GPU e impatto ancora da misurare, utility di interrogazione da sistemare. Lo stack centrale e il percorso degli eventi non sono ancora installati. Dettaglio della prova e dei limiti: runbook del progetto di origine, con valori e output reali esclusivamente nel suo livello privato. Questo documento non distribuisce tali output.

Fonti primarie iniziali: [Netdata Agent](https://github.com/netdata/netdata), [bundle offline ufficiale](https://learn.netdata.cloud/docs/netdata-agent/installation/linux/offline-systems), [protezione degli Agent](https://learn.netdata.cloud/docs/netdata-agent/configuration/securing-agents), [comunicazioni in uscita](https://learn.netdata.cloud/docs/security-and-privacy-design/netdata-agent#outbound-network-communication), [export Prometheus](https://learn.netdata.cloud/docs/exporting-metrics/prometheus), [Grafana OSS](https://grafana.com/oss/grafana/), [Loki](https://grafana.com/docs/loki/latest/) e [stato di lettura Alloy](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/). Consultazione e compatibilità delle release dello stack centrale andranno registrate quando si realizzerà quel profilo.

## Difetto osservato da coprire nel pacchetto

Nel kickstart 2.12.1, `--prepare-offline-install-source` usa `sanitize_string` e rimuove gli slash dal percorso. La prima procedura consegnata al pilota usava un assoluto, produceva un bundle in una directory diversa e falliva il controllo del file successivo. L’installazione non è stata invocata; righe di configurazione indipendenti hanno poi prodotto altri errori. Per la preparazione si usa un nome semplice, per l’installazione la sorgente è assoluta. Le modifiche devono essere condizionate al successo dei controlli e del passo precedente.

La prova isolata sulle funzioni originali distingue entrambi gli errori: preparazione assoluta trasformata e sorgente relativa invalidata dal cambio directory. Comando corretto ripristinato e sorgente del produttore invariata. La prova riguarda parser, validazione e URL, non il payload o il servizio. Va incorporata nei controlli del pacchetto insieme ai test dell’installazione completa; non basta il dry-run o il controllo sintattico dei comandi. Staging con nome semplice senza spazi, da validare anche nei progetti con directory che contengono spazi. Fonte del comportamento: [sorgente del kickstart 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/packaging/installer/kickstart.sh).

## Installazione del primo Agent ricevuta

Il recupero dal bundle effettivo ha superato il controllo degli hash e installato il binario 2.12.1 sul pilota. Il risultato verificato dall’operatore è servizio loaded/inactive/enabled, file con bind loopback scritto, backup e opt-out presenti, comando updater che conferma la disattivazione. Non è ancora un collaudo di listener, dati, ACLK, prestazioni o riavvio. La verifica del primo avvio è preparata nel runbook di origine; la console e il percorso log rimangono da realizzare.

La procedura generica deve distinguere avvio immediato, abilitazione al boot e pianificazione degli aggiornamenti: sono stati differenti. Deve inoltre censire le modifiche dell’installer fuori dal suo prefisso e i privilegi aggiunti, inclusi gruppi Docker/video e capability dei plugin, così il ripristino e la scelta dei collector non si riducono a eliminare una directory. Il pilota non ha modificato queste concessioni dopo l’installazione; la loro necessità va verificata per profilo prima dell’estensione. Fonti: [controllo del servizio](https://learn.netdata.cloud/docs/netdata-agent/maintenance/service-control), [CLI Agent](https://learn.netdata.cloud/docs/netdata-agent/agent-cli) e output del pilota conservato privatamente.

## Primo avvio ricevuto e requisiti da rendere parametrizzabili

L’operatore ha avviato il primo Agent: servizio active/running, listener soltanto loopback, nodo non claimed/non online, export locale CPU/RAM presente. Memoria del cgroup circa 372 MiB in una singola lettura, non costo a regime del futuro hub. GPU, query remote, pipeline dei log e stack centrale restano da realizzare/collaudare. Il pacchetto resta una specifica e non un rilascio completo.

Requisiti aggiunti: documentare ogni passo con fonte/link e data, ragione, comando e destinazione, criterio, risultato, limiti e riferimento alle evidenze con hash. Il profilo eventi deve offrire un contratto versionato per la vista uniforme, parser identificabili, stato degli errori e riferimento all’originale; non deve imporre a tutti i progetti una classificazione AdS. Il profilo hub deve esporre retention per area, risoluzione delle metriche, budget di volumi/code/WAL, riserva, soglie byte/inode/crescita, limiti CPU/RAM/I/O e osservazione esterna. Nessuna cancellazione globale o installazione con taglie arbitrarie prima delle misure.

La verifica isolata deve esercitare formato sconosciuto, ripartenza/rotazione, coda piena, mount assente e scadenza con dati fittizi. Una directory sullo stesso filesystem non garantisce isolamento della capienza. L’eventuale adeguamento tramite hypervisor deve includere margine fisico e filesystem guest; non sostituisce la politica di conservazione. Sono parametri e prove da implementare, non risultati del primo Agent. Fonti: [modello log](https://opentelemetry.io/docs/specs/otel/logs/data-model/), [TSDB Prometheus](https://prometheus.io/docs/prometheus/latest/storage/), [retention Loki](https://grafana.com/docs/loki/latest/operations/storage/retention/), [database Netdata](https://learn.netdata.cloud/docs/netdata-agent/configuration/database) e [controlli systemd](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.resource-control.xml).

## Preflight GPU e revisione delle dipendenze

Il profilo GPU deve distinguere modulo caricato, utility nel PATH e pacchetti installati dai soli candidati. Un pacchetto rimosso con configurazione residua non è un secondo driver attivo. Sul pilota i candidati standard delle utility e della libreria sono alla stessa versione del modulo, quelli server differiscono: questo motiva una simulazione alle versioni esatte, senza promuoverla a query GPU riuscita. Inventario e piano del resolver restano evidenze distinte.

Per una nuova istanza si parametrizzano nomi/versioni dopo la lettura reale, si conserva il piano di apt-get --simulate e si rifiutano rimozioni o cambiamenti inattesi prima del rilascio. Non si mescolano varianti standard/server scegliendo soltanto il numero del ramo. Il controllo delle rimozioni non vieta ogni aggiornamento: il resolver va revisionato interamente e ricontrollato prima dell’installazione. Riferimenti: [APT](https://manpages.debian.org/trixie/apt/apt-get.8.en.html), [dpkg-query](https://manpages.debian.org/trixie/dpkg/dpkg-query.1.en.html), [guida NVIDIA Ubuntu](https://documentation.ubuntu.com/server/how-to/graphics/install-nvidia-drivers/). Comandi effettivi, motivazione e risultato restano nel runbook dell’istanza; il pacchetto completo non è ancora realizzato.

## Ripresa dopo un intervento parallelo

La simulazione sul pilota ha trovato le utility già presenti: un ripristino autorizzato era stato documentato nel frattempo. La procedura deve rileggere stato e handoff correnti prima di ripetere un’installazione, conservando entrambi gli inventari con la loro provenienza. Una simulazione senza operazioni non è un’installazione e un binario funzionante non prova che il collector abbia ripreso la raccolta. Il passo seguente è verificare permessi dell’utente di servizio, configurazione effettiva e campioni hardware; i soli stati di unità NVIDIA non chiudono la prova GPU. Riferimenti: [APT](https://manpages.debian.org/trixie/apt/apt-get.8.en.html) e [collector del tag](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/collector/nvidia_smi/collector.go). Pacchetto e stack centrale rimangono da completare.

## Dal permesso della query ai campioni del collector

Sul pilota la query GPU riesce come utente Netdata e il job risulta nel file distribuito; il journal mostra accettazione del comando di abilitazione. La procedura deve tenere distinti accesso al dispositivo, configurazione, comando accettato e campioni recenti: ognuno ha la propria evidenza. Per la prova dei campioni si selezionano contesti hardware precisi della release, si controllano valori finiti e tempi e si escludono i soli stati delle unità. Per una flotta con più GPU il criterio deve associare i contesti allo stesso identificativo di dispositivo. Fonti: [contesti del tag](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/collector/nvidia_smi/charts.go) ed [export Prometheus](https://learn.netdata.cloud/docs/exporting-metrics/prometheus).

Il filtro preparato ha superato prove isolate di gruppi mancanti e campioni non validi o vecchi, con mutazioni delle guardie rilevate e download fallito che impedisce il filtro. Questi esiti validano la procedura; le metriche GPU reali sono ancora da ricevere. Soglia di età e tolleranza del clock devono essere parametri dichiarati, non valori coperti da un presunto standard del produttore. Stack, impatto e istanziazione del pacchetto restano da completare.

## Esito reale negativo dopo prove locali verdi

Il controllo reale del pilota non ha trovato campioni che soddisfacessero il criterio; il corpo dell’export non è ancora stato osservato. La procedura deve conservare l’esito negativo, mantenere le guardie e raccogliere formato grezzo e diagnostica prima di correggere filtro o collector. Un processo diagnostico separato, con limite di tempo e codice di uscita espliciti, non prova da solo il funzionamento del job nel daemon e non sostituisce l’export reale. Riferimenti: [debug del collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/nvidia-gpu) e [GNU timeout](https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html). Pacchetto e stack completo restano da collaudare.

## Modulo funzionante in debug e abilitazione persistente

Il processo diagnostico del pilota raccoglie dati mentre l’export del daemon non contiene metriche hardware. Prima di ripetere installazioni, il profilo deve verificare abilitazione del modulo e configurazione effettiva del servizio. La proposta deriva la configurazione locale dal file stock della release fissata, conserva gli altri valori, cambia solo il modulo richiesto e impedisce sovrascritture di override esistenti. Hash della sorgente, diff del rendering, esito delle guardie e impatto del riavvio appartengono alla procedura. Fonti: [stock del tag](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/config/go.d.conf) e [configurazione dei collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors-configuration).

I test isolati usano lo stock reale e sostituiscono il controllo del servizio; non attestano un riavvio già avvenuto o campioni acquisiti dal daemon. Il ripristino mantiene la copia e non rimuove altri file. L’accettazione rimane sull’export con dati recenti, non sul solo codice di uscita del debug. Modifica del pilota ancora da eseguire e pacchetto/stack completo non rilasciati.

## Riscontro del daemon e requisito di baseline centrale, 16/10/2026

L’operatore ha applicato l’abilitazione esplicita: il servizio esporta campioni hardware recenti GPU/VRAM/temperatura con contatori 1/3/1. Il profilo riproducibile deve conservare la sequenza stock verificato, override locale senza sovrascritture, riavvio circoscritto, accettazione su dati finiti e recenti e ripristino conservativo. Non deve confondere il numero di dimensioni VRAM con GPU o intervalli di prova. Il collaudo ha risolto la raccolta locale osservata; impatto, reboot e ingestione centrale restano requisiti aperti.

Il pacchetto dovrà separare le letture del guest hub da quelle dei nodi: capacità e mount realmente visibili, RAM disponibile, inode, archivi/code e stato dei servizi. Snapshot e specifiche nominali non sostituiscono la baseline. La procedura del Debian è preparata nel runbook, non ancora eseguita. Restano richiesti normalizzazione uniforme, quote/retention, guardie e margine Proxmox, con accettazione misurabile. La specifica in questo file è aggiornata anche nel template; pacchetto opzionale e stack completo ancora non rilasciati.

## Baseline Debian ricevuta; spazio AdS e attività swap da misurare, 16/10/2026

La baseline del guest hub è ora ricevuta; il profilo riproducibile deve interrogare i percorsi reali degli archivi, perché df sul padre non misura un sottomount. Distinguere device/partizione da filesystem e byte disponibili, senza sommare righe dello stesso filesystem. Memoria disponibile, swap occupata e trasferimenti swap devono essere campi distinti; un contatore CPU cumulativo non è una percentuale. La scansione du deve esplicitare spazio allocato o apparente, perimetro, timeout e completezza. Un timer con LAST non certifica l’esito del servizio. Questi sono criteri del futuro preflight parametrizzato, ancora da implementare come pacchetto; riferimento e comandi nel runbook condiviso.

Nessuna assegnazione di risorse Proxmox o installazione dello stack consegue automaticamente da questa prima fotografia; occorrono dati dell’archivio, crescita e margine del nodo. Il pilota GPU locale è verificato; impatto sostenuto e flusso centrale restano aperti. La specifica è aggiornata nei tre repository, non è un rilascio del pacchetto o dello stack.

## Archivi misurati e processo snapshot della postazione tracciato, 16/10/2026

La raccolta delle misure del progetto e i loro snapshot hanno un ciclo di vita distinto dai log degli host. Il futuro pacchetto deve esplicitare macchina/account esecutore, scheduler, dipendenza dalla sessione, provenienza, pin delle evidenze, conservazione e recupero. Nel progetto rete è stato realizzato un processo locale di retention parametrica con test di cancellazione isolati e attivazione manuale; non è una retention già applicata agli archivi del collettore né un rilascio del pacchetto Linux. Nel dimensionamento distinguere snapshot configurati e misure guest correnti, spazio allocato e byte liberi, scambio corrente e swap occupata.

## Sorgenti QA catalogate e ripresa con altro account preparata, 16/10/2026

Il profilo di integrazione deve registrare ambiente, versione e stato effettivo del produttore: un servizio previsto non diventa sorgente attiva dalla sola presenza del codice. Separare tentativi LLM, recupero del job, consenso al backup, accessi, registro di uso/costi e contenuti della coda. Le durate monotone non sostituiscono i tempi degli eventi; un timestamp senza offset resta di fuso ignoto. Troncamento di errori e intervalli di ID non equivalgono a sanitizzazione o elenco completo dei segmenti. Per rendere riutilizzabile il caso, servono campioni autorizzati e parametrizzazione, non copie dei dati del produttore. Il catalogo specifico vive nel progetto d’origine. Pacchetto completo non rilasciato.
