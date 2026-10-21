# Pilota locale di metriche e log tecnici

Il profilo usa Prometheus 3.13.4 LTS, Grafana OSS 13.2.4, Loki 3.7.0 e Alloy 1.20.1, tutti fissati ai digest verificati sul PC. È un pilota isolato: Prometheus legge la propria metrica interna; Alloy legge soltanto un JSON tecnico **fittizio** creato qui. Non legge file del collettore, non riceve log QA e non definisce il futuro hub di produzione. La prova del 19/10 ha mostrato un evento non recuperato quando Loki era fermo e Alloy è stato riavviato: questa configurazione non va distribuita come trasporto affidabile. Nessun indirizzo o credenziale reale è nel repository.

## Avvio e verifica sul PC

Da questa directory:

```powershell
python init-pilot.py
docker compose config --quiet
docker compose run --rm --no-deps --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose run --rm --no-deps alloy validate /etc/alloy/config.alloy
docker compose up -d
python check-pilot.py
python check-logs.py
```

`init-pilot.py` crea una password casuale in `.env`, una lista target vuota in `targets/netdata.json` e i file fittizi sotto `fixtures/`, tutti ignorati da Git. Inizializza anche `fixtures/current-log.txt` con un segmento vuoto di partenza; dopo ogni emissione il file indica l'ultimo segmento pubblicato e serve ai controlli. Non sovrascrive la credenziale o i target esistenti. Le porte sono pubblicate solo su `127.0.0.1`: Grafana `13000`, Prometheus `19090`, Loki `13100`. La credenziale `admin` è nel file `.env` privato; l'autenticazione anonima è disattivata. Le API di Prometheus e Loki restano accessibili localmente senza autenticazione: questa configurazione non è per la LAN.

Il controllo verifica il target interno Prometheus, il datasource e la dashboard in Grafana, oltre al rifiuto di una chiamata Grafana anonima. Questo dimostra l'avvio e la consultazione locale delle metriche interne. Non dimostra la raggiungibilità dell'Agent Netdata fisico, ancora in loopback, né CPU/RAM/GPU nel backend centrale.

`check-logs.py` crea un originale tecnico sintetico con nome unico, scrive una riga JSON v0 di consultazione e controlla l'impronta SHA-256 dell'originale. Il generatore scrive ogni record in un file `.pending-*.tmp` fuori dal glob di Alloy, forza i byte su disco con `flush` e `fsync`, poi rinomina il file completo a `technical-<identificativo>.jsonl` nello stesso filesystem. Il segmento pubblicato è immutabile; il puntatore `current-log.txt` è aggiornato dopo la rinomina. Il controllo aspetta che Alloy invii la riga a Loki, verifica che Loki restituisca esattamente il record atteso e ripete la query tramite il datasource Grafana autenticato. Il generatore costruisce direttamente i campi: **non è un parser delle sorgenti reali**. Le label dichiarate nel file Alloy sono `archive`, `source_family` e `service`; nel collaudo risultano anche `service_name` e `detected_level` derivate da Loki. Alloy rimuove `filename` prima dell'invio per non creare una serie per ogni segmento. Il controllo rifiuta altre label e l'identificativo dell'evento nelle label. Le posizioni Alloy stanno in un volume persistente.

La prova di continuità locale separa il riavvio di Alloy dalla pubblicazione di segmenti con nomi unici. La versione precedente riutilizzava sempre `technical.jsonl`: un primo `rename/create` è riuscito, ma un secondo con file nuovo della stessa lunghezza non è arrivato a Loki entro 75 secondi. Il percorso fisso e l'offset preesistente non sono quindi una base sufficiente per dichiarare sicura la rotazione. La configurazione corrente scopre `technical-*.jsonl`; il produttore scrive fuori dal glob e pubblica solo il file completo. Con tutti i servizi avviati, eseguire in ordine:

```powershell
python check-recovery.py prepare
docker compose restart alloy
python check-recovery.py after-restart
python check-recovery.py rotate
```

Il controllo confronta gli eventi precedenti e successivi a ogni transizione tramite query Loki, con identificativi unici e uguaglianza del record JSON. Scrive lo stato in `fixtures/recovery-state.json` e verifica due segmenti pubblicati della stessa dimensione, senza cambiare i precedenti. I file restano sotto `fixtures/`, ignorata da Git; la loro pulizia non è automatica. La prova conferma la continuità osservata con segmenti unici; non dimostra assenza di perdita o duplicazione sotto arresto durante una scrittura, né consegna *exactly once*. Il file `technical.jsonl` del vecchio test locale non è più letto dalla configurazione corrente.

Una prova distinta forza una riga incompleta in un file già visibile ad Alloy, riavvia il lettore prima del newline e completa la stessa riga. Serve a misurare come il lettore tratta il prefisso; il publisher normale non espone file incompleti in quel glob:

```powershell
python check-partial.py prepare
docker compose restart alloy
python check-partial.py finish
```

Il controllo esige un evento completo di riferimento prima del prefisso e un nuovo evento completo acquisito dopo il riavvio. Cerca il prefisso in Loki prima e dopo il riavvio, poi verifica il record integrale e che le righe consultate siano JSON valido. Una prova del produttore simula invece il crash prima della rinomina: il file `.pending-*.tmp` incompleto deve restare invisibile ad Alloy e non deve contaminare l'emissione successiva. La prima esecuzione del controllo offline sulla vecchia implementazione è fallita perché accodava al prefisso; la versione corrente lascia il prefisso invariato e pubblica il successivo evento in un segmento nuovo:

```powershell
python check-publisher.py self-test
python check-publisher.py prepare
docker compose restart alloy
python check-publisher.py finish
```

I controlli di continuità conservano stato ed evidenza in `fixtures/`; quando si ripetono, archiviano lo stato già completato sotto `fixtures/state-history/`. Se una fase resta incompleta, si fermano invece di cancellarla. Un arresto prima della rinomina può lasciare un originale e un `.pending-*.tmp` privato senza record pubblicato: la riconciliazione di quell'originale non è automatizzata nel pilota. Il test non copre perdita di alimentazione, sincronizzazione della directory, scritture concorrenti o ritentativi reali.

La fase `check-publisher.py prepare` è stata eseguita il 17/10, poi la sessione si è interrotta lasciando i container accesi. Le sette query negative prima della pausa e le due query negative dopo il riavvio di Alloy del 19/10 non sorvegliano le circa 38 ore intermedie. Poiché Loki ha una retention configurata di 24 ore, la seconda coppia di query non prova che il prefisso sia rimasto assente per tutto l'intervallo. Il 19/10 il prefisso staged era ancora immutato, un nuovo record completo è arrivato dopo il riavvio e il self-test offline è riuscito. La prova di continuità è stata ripetuta con il publisher aggiornato e ha acquisito i due segmenti consecutivi da 818 byte. `check-pilot.py`, `check-logs.py` e le 12 prove del guard offline sono passati; i quattro container sono stati poi fermati con i volumi preservati. Il dossier privato è `_notes/lavoro-corrente/linux-observability-20261015/hub/publisher-20261019.json` (SHA-256 `dfa424aa281cbd3e6649b7647c446d5b13e920716660fa6a90d14361542a1559`).

## Fermo Loki con riavvio Alloy: perdita osservata nel pilota

Il 19/10 è stata aggiunta una prova che crea un evento di controllo indicizzato, ferma Loki, pubblica un segmento completo, riavvia Alloy con Loki ancora fermo, pubblica un secondo segmento e riavvia Loki. Il log di Alloy conferma l'avvio del tailer sul primo segmento durante il fermo. `check-outage.py` interroga ogni record per identificativo entro 90 secondi e confronta l'intero JSON e le label; conserva lo stato anche se fallisce. Per riprodurre il caso con il profilo locale avviato:

```powershell
python check-outage.py prepare
docker compose stop loki
python check-outage.py before-restart
docker compose restart alloy
python check-outage.py after-restart
docker compose start loki
python check-outage.py finish
python check-outage.py probe
```

Senza WAL il controllo e l'evento successivo al riavvio sono presenti, mentre quello letto prima del riavvio non arriva entro 90 secondi né al probe successivo. Una variante temporanea con `loki.write.wal` e `--stability.level=experimental` è stata validata dall'Alloy fissato e ha superato la query normale, ma ha dato lo stesso esito nel test di fermo su un volume già esistente. Durante lo shutdown Alloy ha registrato `error tailing WAL` per il segmento `00000001` mancante. La variante WAL è stata rimossa dal profilo corrente: l'errore non ne dimostra la causa, e la prova non separa la migrazione di un volume preesistente dal comportamento del WAL su volume nuovo. Le due prove private e i loro hash sono nel dossier `_notes/lavoro-corrente/linux-observability-20261015/hub/outage-investigation-20261019.json` (SHA-256 `D867439A4203CFA2550624268C7F7E91D3FB65B3E7C863C380992C60E0D25D69`).

La [documentazione ufficiale di `loki.write`](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.write/) descrive il WAL come funzione experimental e il valore predefinito di dieci retry; la [lettura file di Alloy](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/) conserva offset di lettura, non conferme di indicizzazione. Il gate del trasporto reale richiede una coda durevole con limiti di spazio, replay e deduplicazione misurati, oppure un altro percorso che dimostri la stessa proprietà. Questo test usa due eventi sintetici durante ciascun fermo e una query entro dieci minuti: non quantifica la perdita sotto carico o dopo guasti più lunghi.

### Riparazione circoscritta della fixture

`repair-outage.py` legge soltanto `fixtures/outage-state.json` e il segmento indicato come mancante. Prima di qualsiasi invio verifica SHA del segmento, schema e byte dell'originale tramite `bin/pilot_consultation_v0.py`, poi cerca l'identificativo in Loki in una finestra di un'ora. Rifiuta un evento oltre 55 minuti, una query ambigua o un record diverso. Senza `--apply` esegue solo la verifica; con `--apply` invia il singolo JSON validato all'API locale di Loki e controlla la risposta HTTP 204 e la successiva query dell'intero record. L'API ufficiale richiede [timestamp in nanosecondi come stringa e corpo JSON `streams`](https://grafana.com/docs/loki/latest/reference/loki-http-api/). Il risultato privato è scritto in `fixtures/repair-state.json`; ogni nuova esecuzione archivia il risultato precedente.

Nel test del 19/10 il dry-run ha trovato il record assente, l'invio ha ricevuto 204 e la query lo ha trovato una volta. Una seconda esecuzione con `--apply` ha rilevato il record presente e non ha inviato nulla. Le prove private hanno SHA-256 `4190910FD2ED6D6E51238D2D9ECECEA2E45E86BAE10421D776A415D8FC27982B` per l'invio e `EDDC122E8C9AF3C3BE002333AB0DA34A797F96B3B24256C43C5F83B94E0B9E53` per il secondo giro. Per ripetere, con lo stack avviato e uno stato di outage recente:

```powershell
python repair-outage.py
python repair-outage.py --apply
python repair-outage.py --apply
```

Questa è una riparazione manuale di un solo evento fittizio noto. Query e push non sono una transazione: un invio concorrente può produrre duplicati, e un crash dopo il 204 può precedere la scrittura del risultato locale. Non sono presenti scheduler, scansione completa, coda con quota, replay autonomo, autenticazione LAN o supporto di dati reali. ADR-023 continua a bloccare il trasporto di produzione.

Al primo avvio locale Grafana 13.2.4 ha scaricato plugin suggeriti. La configurazione ora imposta `GF_PLUGINS_PREINSTALL_DISABLED=true`. Una seconda partenza con volumi nuovi e rete Docker interna ha avviato entrambe le applicazioni e permesso una query da Grafana a Prometheus; nei log non compaiono download di plugin. Questa prova riguarda le funzioni del pilota e non tutte le integrazioni future.

Per ripetere la prova da volumi nuovi senza uscita Internet, fermare il profilo principale e usare un nome progetto distinto:

```powershell
docker compose -f compose.yaml -f compose.offline.yaml -p intrawelt-monitoring-offline up -d prometheus grafana
docker compose -f compose.yaml -f compose.offline.yaml -p intrawelt-monitoring-offline exec -T prometheus promtool query instant http://localhost:9090 up
docker compose -f compose.yaml -f compose.offline.yaml -p intrawelt-monitoring-offline exec -T grafana sh -c 'curl -fsS -u "admin:$GF_SECURITY_ADMIN_PASSWORD" "http://localhost:3000/api/datasources/proxy/uid/pilot-prometheus/api/v1/query?query=up"'
docker compose -f compose.yaml -f compose.offline.yaml -p intrawelt-monitoring-offline down
```

L'override rende interna la rete Docker fra Prometheus e Grafana: Docker Desktop non pubblica le porte verso il PC in questa modalità, perciò `check-pilot.py` eseguito sull'host non può verificare la prova offline. Le due query sopra sono eseguite dentro i container; la seconda usa la password già presente nell'ambiente privato del container senza stamparla. Controllare anche che i log Grafana non riportino download di plugin. Questa prova offline riguarda la catena delle metriche; Loki e Alloy sono stati collaudati nel profilo locale normale. I volumi del progetto di prova restano conservati dopo `down`, finché non si decide di rimuoverli manualmente.

## Originali della coda sintetica isolati, 21/10/2026

I nuovi eventi di `replay-outbox.py` scrivono gli originali in `fixtures/replay-original/`; gli altri generatori del pilot continuano a usare `fixtures/original/`. Il limite logico di 8 MiB conta i segmenti, tutti gli originali della nuova cartella e solo gli originali della cartella condivisa ancora citati dai segmenti storici. Il guard ammette il nuovo percorso soltanto quando il chiamante attiva esplicitamente la modalità replay; la CLI ordinaria continua a rifiutarlo. I due segmenti locali del 19/10 sono stati validati con i loro originali e lasciati intatti: i loro record e il contenuto già indicizzato non vengono riscritti. Sono ormai fuori dalla finestra automatica di 55 minuti; una riconciliazione del lotto locale si fermerà finché non saranno gestiti manualmente. Le prove isolate verificano che un file grande scritto da un altro generatore nella cartella condivisa non consumi la quota della nuova coda e che un file inatteso nella cartella isolata blocchi l'emissione. La separazione delle directory non è una quota del filesystem, non impedisce a un processo esterno di alterare i file della coda e non prova la tenuta sotto carico o dopo un guasto di alimentazione. Nessun flusso reale è abilitato.

## Gate dello spool e stato di saturazione, 21/10/2026

La CLI richiede per impostazione predefinita due mount Linux esatti, uno su `fixtures/replay-outbox/` e uno su `fixtures/replay-original/`, sullo stesso filesystem con dimensione totale positiva e non superiore a 64 MiB. Il controllo avviene prima di creare la coda o interrogare Loki; un mount assente blocca l'operazione invece di scrivere nel filesystem padre. Due bind mount dello stesso filesystem dedicato sono un possibile allestimento, ancora da collaudare su Linux. Il limite logico resta 8 MiB e 256 segmenti. Segmenti storici che puntano a `fixtures/original/` sono ammessi solo nel pilot locale: la modalità vincolata li rifiuta, perché quell'originale non sarebbe contenuto nel filesystem limitato. I due segmenti privati esistenti hanno superato 55 minuti e richiedono comunque esame manuale; non sono stati migrati o eliminati.

Sul PC, dove non è predisposto un mount dedicato, indicare esplicitamente `--local-pilot`. Questa modalità mostra soltanto la quota logica e non dichiara verificata una quota fisica:

```powershell
python replay-outbox.py emit --local-pilot
python replay-outbox.py reconcile --local-pilot
python replay-outbox.py reconcile --apply --local-pilot
python replay-outbox.py status --local-pilot
```

`status` restituisce JSON con byte, segmenti e motivi di avviso; esce con codice 2 quando raggiunge almeno l'80% del limite logico. Nella modalità vincolata misura anche byte e inode disponibili sul filesystem e avvisa al 20% o meno. Il comando non spedisce una notifica. Mancano monitoraggio periodico, destinatario e prova di ricezione/silenzio dell'allarme: una stampa locale non chiude quel gate. Mancano inoltre una prova Linux con mount reale ed esaurimento fisico, carico e guasti lunghi. Prima di un uso operativo, il filesystem dedicato va creato e montato con procedura approvata, con dipendenze del servizio dal mount e monitoraggio esterno collaudato. Nessun dato reale usa questa coda.

## Coda e replay sintetici separati da Alloy, 19/10/2026

`replay-outbox.py` crea un evento fittizio in `fixtures/replay-outbox/`, fuori dal glob di Alloy. Conserva il segmento dopo ogni invio e, a ogni riconciliazione, valida tutti i segmenti e gli originali con il guard v0 prima di interrogare Loki. Il limite logico è 256 segmenti e 8 MiB complessivi per segmenti, originali dedicati e originali storici referenziati. Il produttore calcola i byte del nuovo originale e del segmento prima di creare file; un `.pending-*.tmp` residuo o un file inatteso blocca emissione e replay. Una collisione del nome del segmento viene rifiutata prima di scrivere l'originale. Dopo il flush dello staged, la pubblicazione crea un hard link con nome definitivo: un writer che occupa quel nome non viene sovrascritto e lo staged resta per esame. La [specifica POSIX di `link()`](https://pubs.opengroup.org/onlinepubs/9699919799/functions/link.html) descrive `EEXIST` e atomicità su POSIX; [Python documenta `os.link`](https://docs.python.org/3/library/os.html#os.link) anche su Windows. Il filesystem deve supportare hard link nella stessa directory. La coda usa un lock esclusivo: dopo un crash che lasci `.lock`, esaminare processo e file prima di sbloccare. Il controllo logico non impedisce a un writer esterno di modificare file già pubblicati; la directory non viene sincronizzata su disco dopo la pubblicazione. Il mount limitato è ancora da provare su Linux sotto carico e con guasto fisico.

```powershell
python replay-outbox.py emit --local-pilot
python replay-outbox.py reconcile --local-pilot
python replay-outbox.py reconcile --apply --local-pilot
```

Il replay confronta il record completo e le tre label fisse nell'indice e rifiuta label non previste; le due label opzionali derivate da Loki non sono confrontate con un valore atteso. La query usa una finestra assoluta attorno all'ora dell'evento e l'età è ricontrollata prima di query e push. Invia solo un evento assente e ricontrolla dopo la risposta HTTP 204. Una query ambigua, un evento più vecchio di 55 minuti, un file incompleto o il backend non raggiungibile fermano il lotto. La finestra di query/push resta una gara: l'esito osservato non dimostra consegna *exactly once*, né copre crash di alimentazione o guasti oltre 55 minuti. `status` misura la saturazione quando viene chiamato; non esistono scheduler, pulizia automatica degli originali, recapito degli allarmi o prova di carico. Un crash prima della pubblicazione del collegamento definitivo può lasciare un originale senza record pubblicato, che blocca ulteriori emissioni e richiede esame manuale. Nessun flusso reale può usare questa coda.

Nel test locale sono stati emessi due eventi sintetici, uno per volta con Loki fermo. Le riconciliazioni durante il fermo hanno fallito senza togliere i segmenti; dopo il ripristino l'indice conteneva entrambi, e la seconda esecuzione con `--apply` ha inviato zero record. Le prime query durante ciascun avvio di Loki hanno avuto timeout, poi il replay è riuscito. Dopo la correzione della finestra temporale, una nuova query sul Loki reale ha trovato i due record e non ha inviato copie. Le prove isolate coprono anche la risposta persa dopo l'indicizzazione, il blocco per lotto invalido o file temporaneo residuo, la quota complessiva prima di creare un originale e il rifiuto dell'identificativo duplicato prima di contattare Loki. La prova sulla quota è stata controllata reintroducendo il difetto: omettere gli originali dal conteggio fa fallire la prova, poi il ripristino verificato riporta la suite a 18/18. Il controllo aggiunto per i file inattesi fallisce se si ripristina la scansione dei soli `*.jsonl`; dopo il ripristino verificato della sorgente, guard e coda passano 19/19 prove. La prova sulla collisione sequenziale fa fallire il test quando viene tolta la guardia; quella che inserisce un segmento esterno tra controllo e pubblicazione fa fallire il test quando si ripristina `replace()`. Guard e coda passano ora 21/21 prove isolate, senza nuova prova live di Loki. Evidenze private `_notes/lavoro-corrente/linux-observability-20261015/hub/replay-outbox-20261019.json` (SHA-256 `3ED8E8A8EF1F05C3E98502328CEAA090F0383363A4BFC206C65B50BB3891CDBA`) e `replay-review-20261019.json` (SHA-256 `6890E74BD6C80110D738A50632B4A7465F42918B172AB2505E2C7EBF262FC60B`). La sorgente ufficiale per il push e la query è la [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/).

## Collegare un Agent dopo aver definito il trasporto

Prometheus legge `targets/netdata.json` tramite file discovery. Il file privato parte come `[]`; solo dopo che un endpoint sia raggiungibile **dal container** e ristretto al solo hub, aggiungere un gruppo come questo, sostituendo segnaposto e identità con valori censiti:

```json
[{"targets":["<ENDPOINT_AGENT>:19999"],"labels":{"source_id":"<SOURCE_ID>","environment":"<AMBIENTE>"}}]
```

Il job usa `/api/v1/allmetrics?format=prometheus`, che esporta le metriche locali del singolo Agent. Per un Parent con più host serve una configurazione diversa (`prometheus_all_hosts` e valutazione di `honor_labels`). Non aprire la porta 19999 dell'Agent alla LAN per provare questo file: prima definire accesso ristretto, verifica TLS o un trasporto protetto, identità e firewall. I due LXC QA sono solo pianificati e non vanno aggiunti come target attivi.

## Dati, arresto e limiti

Prometheus conserva nel volume Docker locale al massimo 24 ore o 1 GB di blocchi, a seconda di quale limite scatta per primo. Il limite dimensionale non è una quota rigida del filesystem: WAL e compattazione richiedono spazio addizionale. Loki configura 24 ore per i soli dati fittizi, con Compactor e archivio filesystem; la cancellazione effettiva a scadenza non è stata osservata e non c'è una quota di byte. Questi valori non fissano la retention della flotta. Grafana mantiene dashboard e impostazioni nel suo volume; Alloy conserva le posizioni nel proprio volume. I log stdout/stderr di ciascun container usano il driver Docker `local` con tre file da 10 MB, un limite distinto dai volumi dati e dai file sintetici. I container usano `no-new-privileges`; Prometheus, Grafana e Loki hanno tutte le capability Linux rimosse. Alloy conserva quelle predefinite: con il volume delle posizioni già creato, `cap_drop: ALL` ha impedito l'accesso a `/var/lib/alloy/data`, e il semplice cambio all'UID 473 non ha potuto leggere `positions.yml`. Queste due varianti sono state scartate dopo il test live. Per fermare il pilota: `docker compose down`; non usare `-v` se si vogliono conservare i dati di prova. La rimozione dei volumi resta una decisione manuale.

Parser reali, tre archivi logici, quote del Debian, allarmi e accesso LAN con TLS sono passi separati ancora da realizzare. Il posizionamento dello stack va deciso dopo misure live del nodo Proxmox, includendo entrambi i LXC QA richiesti. Riferimenti e criteri: [studio di osservabilità](../../docs/osservabilita-linux-netdata.md), [normalizzazione e capienza](../../docs/normalizzazione-retention-capienza.md), [integrazione QA](../../docs/integrazione-log-qa-verifier.md), [lettura file Alloy](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/), [retention Loki](https://grafana.com/docs/loki/latest/operations/storage/retention/), [driver Docker local](https://docs.docker.com/engine/logging/drivers/local/).
