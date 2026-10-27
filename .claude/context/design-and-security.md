---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
  - pilot/monitoring-hub/**
last-verified-commit: 8773aa6dfa3708a34b0cd7b3b530aabaeaef2fb3
---

# Design e sicurezza applicativa

## Limite della catena locale dopo un fermo, 26/10/2026

La ripresa dei manifest scorre i giorni mancanti fino a D-1 sotto un lock, ma non inventa evidenze oltre 213 giorni o prima del primo `GENESIS`. Il servizio richiede `/srv/ads` montato e il job verifica il mount prima di creare directory o manifest: un mount perso non diventa una giornata vuota da chiudere. Un manifest vuoto mantiene la continuità della catena, senza attestare che una sorgente fosse completa; D6 deve valutare i segnali attesi e un destinatario esterno deve ricevere l'allarme. Manifest, archivi e log restano nella stessa VM: TSA, WORM e impronta consegnata alla Direzione sono ancora necessari per una prova indipendente.

Un preflight integrale rifiuta la nuova chiusura se la catena storica locale non è verificabile. Questa verifica dipende dagli originali ancora presenti; la futura eliminazione a 213 giorni richiede una politica esplicita di troncamento e un ancoraggio esterno, altrimenti il job si fermerà.

Le radici e directory di archivio simboliche sono rifiutate prima della scrittura o della certificazione locale. La guardia esercitata in WSL non è una difesa contro la sostituzione concorrente da parte di un writer che abbia accesso alle stesse directory: proprietà, ACL e mount restano parte del collaudo operativo.

## Limiti del segnale D6 e del mount QA, 26/10/2026

Un evento giornaliero assente indica `no_events`, non una sorgente guasta; un heartbeat mancante è `heartbeat_missing` solo se il produttore è stato collaudato. Il servizio D6 rifiuta una politica mancante, chiavi JSON duplicate e un `/srv/ads` non montato, opera come `ads` senza rete e non può leggere `/etc/ads/secrets`. `active_from` impedisce di dichiarare controllati giorni anteriori all'ingresso di una sorgente; la finestra massima di 213 giorni e il totale delle anomalie restano espliciti nel report, mentre il dettaglio è limitato a 100. Il ricevente candidato distingue trasporto TLS, RFC 5424 e IP autorizzato prima di creare il file di heartbeat; i marker rifiutati vanno fuori da `/srv/ads/`. Il TLS esistente autentica il server, ma i client rsyslog sono anonimi: l'IP non prova l'identità crittografica della postazione. Ritenzione e capienza del flusso rifiutato restano da definire. Il giornale locale e il codice di uscita non sostituiscono un allarme esterno né una prova di custodia oltre la finestra. Il controllo mount del ricevitore QA è passato su tmpfs WSL, ma la custodia e la quota del volume di destinazione restano da provare.

La documentazione Fluent Bit 4.1 precisa che `tls.verify` non controlla il nome per default: il template propone `tls.verify_hostname on`. Il test negativo su un IP assente dal SAN, ma con certificato attendibile, ha prodotto `hostname mismatch (X509 code: 62)` e nessun payload. Questo rafforza l'autenticazione del server; il client resta anonimo verso rsyslog.

La ritenzione dei marker rifiutati riusa il motore tecnico Seeweb senza accesso a `/srv/ads/`. Il motore richiede `--days N` per cancellare, valida nomi, date, link e hard link, e riporta un avviso se l'archivio è vuoto o il filesystem raggiunge l'80%. Non c'è durata predefinita o timer installato; la soglia locale non è una quota né un allarme consegnato.

## Identità e ricevuta del flusso QA, 23/10/2026

La riga SSH forzata proposta associa una chiave per ambiente a `source_id` e archivio privato fissati sul server; il payload non può cambiare l'origine attesa. `--ssh-stdin` rifiuta un comando originale diverso e legge un solo evento entro 1 MiB. Il mittente riconosce solo una ricevuta con ID e SHA-256 identici ai byte inviati e conserva il file pronto quando la risposta manca o non coincide. Il retry riceve `duplicate` se l'archivio centrale ha già pubblicato gli stessi byte. Il protocollo è candidato locale: autenticazione fra host, host key, ACL, limite fisico, allarme e durabilità sul volume destinato richiedono prova operativa.

## Errore fisico dello spool e prova di autorizzazione QA, 21/10/2026

Nel tmpfs Linux a zero blocchi, `lock.open('x')` poteva creare `.lock` e fallire durante la scrittura: prima della correzione quel file restava e impediva anche il triage con `status`. Ora si elimina solo il lock creato dal processo dopo un errore sincrono di scrittura/fsync; i lock preesistenti continuano a bloccare. La prova non simula un kill o un taglio di corrente. Nel produttore QA l'autorizzazione è ancora solo in RAM e la CLI raggiunge il client esterno senza il gate web: nessun backup esterno è da abilitare finché il registro riservato non è durevole e tutte le vie d'uscita sono governate.

## Confine QA: autorizzazione fuori dalla vista tecnica, 21/10/2026

Il nuovo controllo offline rifiuta `authorisation_granted` prima di produrre una vista tecnica. Chiavi esatte, enum, origine attesa, timestamp con offset, chiavi JSON duplicate e intero lotto sono verificati; l'output è costruito esplicitamente senza `job_ref`. La prova del builder è su dati costruiti secondo il codice sorgente, non su un job reale o su Loki. Il registro riservato dell'autorizzazione e la sua conservazione devono essere progettati separatamente prima di collegare il produttore.

## Risposta ambigua dopo la POST, 21/10/2026

Un marker di tentativo scritto e sincronizzato prima dell'invio separa un record ancora mai tentato da uno che potrebbe essere stato accettato senza risposta. Il riavvio può verificare l'indice, ma non ripete la POST di un record assente con marker; un marker senza segmento o con digest diverso blocca il lotto. Il digest del segmento viene ricontrollato anche dopo la seconda query e prima del marker. La directory è sincronizzata solo su POSIX; su Windows il pilot prova il flusso logico, non la durabilità dopo perdita di alimentazione. Il lock riguarda i writer che usano questa coda; writer esterni e Loki non condividono una transazione, quindi nessuna garanzia *exactly once*.

## Confine fisico proposto per il replay sintetico, 21/10/2026

Prima di creare la coda o contattare Loki, la modalità vincolata richiede due mount Linux esatti sullo stesso filesystem di massimo 64 MiB. La directory degli originali deve corrispondere esattamente ai riferimenti dei segmenti: un file parziale/orfano blocca emissione e replay, evitando di scambiare un ENOSPC per un invio riuscito. I riferimenti storici a `fixtures/original/` sono consentiti soltanto nel pilot PC. Questa guardia non sostituisce la prova su mount reale né impedisce modifiche di writer esterni ai file pubblicati; nessun flusso reale autorizzato.

## Confine degli originali nel replay, 21/10/2026

Il guard ammette `fixtures/replay-original/<id>.log` solo su richiesta esplicita della coda; la CLI normale accetta soltanto il percorso precedente. I record storici non vengono riscritti e i loro originali condivisi restano soggetti a verifica dei byte. Le nuove emissioni evitano la contesa di quota con gli altri generatori, ma la separazione è logica: non impone limite al filesystem, non impedisce modifiche da processi esterni e non abilita dati reali. I due segmenti storici sono oltre la finestra di replay automatico.

## Confine del ricevitore Seeweb, 20/10/2026

La regola nftables ammette UDP 514 solo dall'IPv4 Seeweb configurato, ma l'indirizzo non autentica il mittente. Rsyslog isola tutti i messaggi di quella sorgente nell'archivio tecnico `root:root 0640/0750`, senza promuoverli ad accessi AdS prima di campioni nativi con attore. Il controllo di ritenzione richiede giorni espliciti prima di cancellare, registra i percorsi rimossi e segnala localmente archivio vuoto o uso disco almeno all'80%. Non è installato; percorso VPN, volume reale, durata, silenzio e allarme esterno restano da verificare.

## Nuovo builder QA e confine degli archivi, 20/10/2026

Su `staging` a `71a3892` il produttore QA ha versionato `app/events.py`: crea due famiglie di eventi `qa-tech-v1`, ma non le invia né è collegato ai chiamanti applicativi. `authorisation_event()` include identità e nome file; il contratto del collettore riserva questi dati a un registro dell'autorizzazione con accessi distinti dalla vista tecnica generale. `validate()` da sola controlla le chiavi ma non tutti i valori e le combinazioni. Prima di costruire il ricevente servono separazione dei due archivi, schema con allowlist completo e prove negative sui dati prodotti dall'applicazione. I due LXC QA non esistono ancora e nessuna sorgente è collegata.

## Pubblicazione del pilot e limiti residui, 20/10/2026

Nel pilot `os.link` crea il nome definitivo dallo staged nella stessa directory dopo `fsync` del file; se il nome è stato occupato nel frattempo, l'emissione fallisce e non sovrascrive il segmento esterno. Su questo PC la prova della collisione tardiva conferma i byte invariati e lo staged residuo. La specifica POSIX di [`link()`](https://pubs.opengroup.org/onlinepubs/9699919799/functions/link.html) descrive creazione atomica ed errore `EEXIST`; [Python `os.link`](https://docs.python.org/3/library/os.html#os.link) espone l'operazione anche su Windows, dove l'esito qui è una prova locale e non una garanzia generale dedotta dalla specifica POSIX. La directory non è sincronizzata dopo la pubblicazione; un altro writer può modificare il file in seguito e gli originali restano condivisi. Quota fisica, isolamento, concorrenza di replay, carico e guasti prolungati restano gate prima di sorgenti reali.

## Confine della coda sintetica, 19/10/2026

Il pilot rifiuta figli inattesi della directory della coda e un nome di segmento già presente prima di scrivere l'originale. Il lock resta locale al comando cooperante; `os.link` rifiuta la collisione tardiva, ma non impedisce modifiche successive da altri writer, e gli originali sono in una cartella condivisa. La quota di 8 MiB è logica, non imposta dal filesystem. Nessun evento reale QA o AdS deve entrare in questo percorso finché isolamento degli originali, quota fisica e prove di guasto non siano verificati.

## Confine QA riconfermato dal produttore, 19/10/2026

L'ADR-023 versionata del produttore QA su `staging` a `7472de5` adotta `qa-tech-v1` e corregge l'ipotesi che `AdsLine` fosse il formato in ingresso. Il codice letto non emette ancora il contratto: il lavoro del passo 5 è non committato, con CSV uso che conserva `filename` e `user` e fallback che nomina `T1/T2`. Il futuro evento tecnico generale resta a vocabolari chiusi, senza testo libero o identificativi in label; l'eventuale registro identificante dell'autorizzazione al backup richiede perimetro e accessi separati. Nessun adapter QA o flusso reale è abilitato dal pilot.

## Perimetro del contratto sintetico e dei futuri eventi QA, 17/10/2026

ADR-022 e `docs/integrazione-log-qa-verifier.md` richiedono eventi QA strutturati e minimizzati prima del Loki generale; i diagnostici originali eventualmente autorizzati restano in archivio protetto. Anche un testo di formato noto richiede whitelist e rifiuto dei campi non classificati. `bin/pilot_consultation_v0.py` è fail closed soltanto per la fixture sintetica, con originale confinato e hash controllato: non autentica la fonte, non prova assenza di dati sensibili nei log QA e non è collegato alla pipeline reale. La verifica del produttore con errori sensibili fittizi e UI/job sul consenso e sull'attesa di 600 s resta un gate aperto.

## Verifica dei volumi API preparata, milestone precedente versionata, 13/10/2026

Verificatore dei volumi separato dal poller: chiave solo stdin, client TLS e mapping dallo snapshot, budget massimo interno di 20 POST e piano corrente di 18. Prima di creare il client si rifiutano cache vuote, periodo oltre sette giorni o terminato meno di un'ora prima. Questo margine e la guardia di 1.000 righe sono scelte prudenziali interne, senza garanzia Zyxel. Controllo positivo e confronto ampie prima/dopo impediscono di promuovere il vuoto a prova o attribuire automaticamente a troncamento un cloud cambiato. Vecchi record assenti sono indisponibili, senza causa dedotta. Limite e retention massimi, completezza fisica e raccolta VM restano non dimostrati. Fonte API e distinzione fra documento e misura nei passi 70-71 del runbook; parser manuale riconciliato a 928da73.

## Formato manuale Nebula osservato

Il campione reale 54HP del 13/10 aggiunge il formato esatto del logout manuale alla lista del poller. La guardia sui formati AAA sconosciuti conserva il comportamento di errore senza cursore avanzato; il verificatore conserva tempi e conteggio non disponibile in caso di classificazione fallita. Non è un ampliamento generico basato su keyword. Campione, regressione, mutazioni e limiti nei passi 59-63 del runbook; nessun canale in esercizio o ritardo massimo nuovo dimostrato.

> Stato riconciliato al commit `2456511`, con poller Nebula nel lavoro locale del 12/10. Le scelte di custodia della prova restano in `docs/modello-di-custodia.md` e ADR-010.

## Paradigmi di software design

`bin/adsparams.py` interpreta solo il sottoinsieme di YAML usato da `parametri.yaml` e segnala gli errori con la riga; `bin/ads-render.py` sostituisce i segnaposto nei due alberi di configurazione senza scrivere un albero parziale o sovrascrivere una destinazione esistente. `bin/ads-vm-command.py` genera un comando da eseguire manualmente, non opera sull'host. `bin/ads-pki.sh` emette CA e certificato sulla postazione amministrativa, mentre `bin/ads-bootstrap.sh` valida gli ingressi e installa la configurazione sulla VM. Questa separazione permette di provare generazione e configurazione in container prima dell'installazione reale.

Sul collettore rsyslog riceve da sorgenti UDP e TLS nello stesso ruleset, aggiunge ora di ricezione e IP osservato e salva i cinque campi di `AdsLine`. L'host Proxmox filtra in origine i soli messaggi di autenticazione e li inoltra con due code su disco, una per il journal e una per l'access log di `pveproxy`. I NAS e il firewall sono configurati nelle loro interfacce; i runbook documentano l'esito di ogni sorgente.

Il template rsyslog del collettore ora riceve da `ads-render.py` un confronto di IP validati per `sorgenti.ilo`; con lista vuota genera una condizione impossibile accettata da rsyslog 8.2504. Per gli IP iLO, i prefissi espliciti Browser, SSH e Remote console entrano nel flusso AdS; i restanti messaggi vanno in `/var/log/ads-ilo-other/` per revisione, senza perdita. Solo i tre prefissi Browser sono stati osservati sulla iLO fisica. L'IT Manager ha scelto 90 giorni locali per il secondo flusso: file giornalieri `root:root 0640`, directory `0750` e job di scadenza separato, provato in WSL. Il controllo dei permessi e dei due flussi passa in Debian 13; regola e timer sono installati dal 08/10 con collaudo Browser/test tecnico reale e un giro del service riuscito. La presa in carico degli avvisi di capienza resta aperta.

Il poller Nebula locale usa una sola origine HTTPS, TLS verificato, nessun proxy ereditato o redirect e chiave passata come file con `LoadCredential`. Il diario SQLite conserva il lavoro pendente prima dell'append e completa soltanto i byte mancanti dopo un arresto; un conflitto blocca la ripresa senza riscrivere il log. Formati AAA ignoti, saturazione e recupero oltre la finestra concordata falliscono senza avanzare il cursore. La deduplicazione non distingue eventi identici nello stesso millisecondo; la soglia locale non rileva un troncamento remoto inferiore e la sovrapposizione copre solo ritardi contenuti nella finestra. Stato, permessi e crash sono provati localmente; retention, offline remoto, notifica esterna e coordinamento D-1 restano aperti prima dell'esercizio (ADR-018).

Nel componente iLO versionato il client Redfish separa recupero delle pagine, trasformazione delle voci e scrittura del checkpoint. L'intero giro è esclusivo per sorgente tramite lock sul collettore Linux. Il log viene sincronizzato prima del checkpoint atomico: un arresto fra i due può duplicare una riga, identificabile da `Id` e `Count`, ma non far avanzare lo stato oltre eventi mai scritti. Un giro fallito scrive `status=error` e termina con codice non zero; il controllo di silenzio futuro dovrà leggere l'esito, non soltanto vedere se esiste un file.

## Sicurezza applicativa

Il login riuscito 54HP del 13/10 è ricevuto nella seconda risposta API: record unico, modello e target confermati, MAC del riferimento coerente e account/IP coincidenti con il login 30HP. Report ricalcolato identico; grezzi e identificativi restano privati. Risposta positiva a +14,769 secondi dichiarati, prima query antecedente al record: non si costruisce un limite inferiore da quel vuoto o una garanzia di ritardo massimo. Il campione non estende la verifica a fallimenti/logout 54HP o alla custodia sul collettore.

Il modello esplicito del nuovo collaudo 54HP deve essere univoco nello snapshot, con riferimento del medesimo apparato; una rilettura con target diverso dal report conservato fallisce prima di leggere la chiave o creare il client. URL e mapping reali sono privati. Il riferimento storico del 54HP è tecnico e non autorizza a dichiarare copertura AdS. Token sempre via stdin e nessuna credenziale consultata dall'agente per preparare il comando; nuovo login reale e relativa misura ancora attesi.

Il nuovo login 30HP del 12/10 è osservato nella quinta risposta API con ritardo apparente di 38,030 secondi rispetto all'ora dichiarata. Conferma umana successiva all'accesso e candidato unico coerente con account/IP noti, senza pubblicarne i valori. Screenshot, candidati e payload sono nel livello privato; il report ricalcolato coincide. Il campione non stabilisce scarto degli orologi, ritardo massimo, completezza generale o copertura 54HP: non si ridimensionano settle e overlap sulla sola misura.

La prima misura reale Nebula ha ritrovato cinque accessi AAA identici dopo oltre 90 ore; una prova successiva include entrambi gli estremi per un riferimento ancora presente dopo 93,356911 ore, senza stabilire retention massima. Le finestre concordano sul campione 30HP, mentre il 54HP resta senza accessi noti. I verificatori di finestre, estremi e pubblicazione conservano grezzi e mapping privati e riusano TLS e origine del poller. Token via stdin UTF-8, stdout inoltrato e stderr privato; il trasporto non isola i processi dello stesso account. Il tempo di pubblicazione preparato è apparente: offset degli orologi e associazione del candidato all'azione dell'operatore richiedono verifica. Completezza, offline e ritardi cloud ancora aperti; nessuna chiave sulla VM.

Venti risposte reali vuote con login confermato non autorizzano a dichiarare assenza dell'accesso o ritardo massimo. La rilettura diagnostica richiede il riferimento storico esatto, mantiene i candidati privati e distingue timestamp interrogato e idoneità al filtro originale. La causa resta aperta finché non si associa il record all'azione umana; nessun parametro del poller cambia per la sola FAQ sul tempo di sincronizzazione generale dei dispositivi.

L'accesso SSH al collettore richiede una chiave personale, un indirizzo amministrativo ammesso da nftables e l'appartenenza a `ads-admin`; il login di root e l'autenticazione SSH con password sono disabilitati. `sudo` richiede la password locale dell'account personale. Il bootstrap controlla nomi e chiavi pubbliche prima di installare gli account e ricaricare SSH; ne verifica la sintassi e quella di sudoers e nftables. L'utente di servizio `ads` non ha shell di login né privilegi sudo. Il guest agent permette le sole RPC elencate in `allow-rpcs`, escludendo l'esecuzione di comandi e la gestione di file o credenziali dalla console dell'hypervisor.

`config/parametri.yaml` e gli alberi generati sotto `build/` sono privati e ignorati da git. La chiave della CA rimane sulla postazione amministrativa; sul collettore arrivano solo certificato della CA, certificato server e relativa chiave, installata 0600. I segreti applicativi appartengono a `/etc/ads/secrets/` sulla VM. Il bootstrap si ferma se nella cartella TLS trova `ca.key`. Lo script PKI rifiuta di sovrascrivere file esistenti e verifica il certificato emesso contro la CA.

La porta 6514/tcp accetta TLS ma il ricevente non autentica il certificato del mittente: `StreamDriver.AuthMode="anon"`; nftables limita gli IP alle reti configurate. L'host Proxmox verifica invece il nome del certificato del collettore con `x509/name` e conserva i messaggi in coda durante un'interruzione. La porta 514/udp serve gli apparati che non offrono TLS e trasporta i log in chiaro, senza conferma di consegna. Finché la LAN è un'unica subnet, nftables ammette i messaggi syslog da tutta quella rete: l'indirizzo del mittente non è da solo una prova di autenticità. I log sono scritti `root:ads`, file 0640 e directory 0750; la protezione contro alterazioni da parte degli amministratori del collettore è ancora una decisione aperta sulla custodia esterna della prova (ADR-010).

L'iLO reale ha licenza Advanced e Remote Syslog sulla porta 514/udp ha superato il collaudo degli accessi e degli orologi: eredita i limiti del trasporto in chiaro senza conferma di consegna descritti sopra, con file prodotti da rsyslog come `root:ads`. Il login fallito non riporta l'account tentato; i successi riportano l'account generico `administrator`. Il flusso nuovo separa accessi Browser ed eventi tecnici, ma i file storici misti restano da trattare prima della catena. La pagina Security Dashboard del 2026-10-07 segnala certificato SSL predefinito, SNMPv1 attivo, Secure Boot e complessità password disabilitati e login iLO RBSU non richiesto; la correzione di questi rilievi appartiene al progetto di rete. Il client Redfish alternativo richiede sia una CA attendibile sia l'impronta SHA-256 del certificato presentato durante ogni handshake HTTPS. Non eredita proxy né segue redirect; rifiuta URI Redfish di origine diversa. La password è letta da un file privato con permessi 0600 sul collettore, il token della sessione non entra nei log e la sessione è cancellata a fine giro. Il sistema `ilo5` scriverebbe file propri come utente `ads`, in una directory della sorgente posseduta da `ads:ads`; la sicurezza e la compatibilità del certificato andrebbero provate prima dell'attivazione.

La catena locale preparata in `ads-nightly.sh` e `ads-verify.sh` rileva modifiche ai log dopo la chiusura D-1 confrontando origine, gzip e manifest concatenati. I manifest e i log restano però sulla stessa VM e un amministratore che possa riscriverli entrambi può creare una nuova catena coerente: l'indipendenza della prova dipende da TSA, WORM e impronta comunicata alla Direzione, che non sono ancora implementati. Il servizio systemd previsto scrive solo in `/var/lib/ads` e legge `/srv/ads` in sola lettura; il test dei permessi reali e l'installazione restano aperti.

## Diagrammi

Nessun diagramma di questi componenti è presente nel repository al commit verificato. Una tabella dei diagrammi sarà aggiunta quando esisteranno sorgente e derivato corrispondenti al codice.

## Publisher sintetico e ripresa del pilota, 19/10/2026

Nel pilot il glob di Alloy include solo `technical-*.jsonl`: il publisher prepara `.pending-*.tmp` fuori glob e rinomina il file completo. Questa guardia locale non prova durabilità dopo power loss, consegna esattamente una volta o sanitizzazione delle sorgenti QA reali; ADR-022 e il gate del produttore restano validi.

## Fermo Loki e riavvio Alloy, 19/10/2026

Il punto di perdita osservato è fra offset del lettore file e conferma di indicizzazione Loki. Segmenti completi e posizioni persistenti non sostituiscono una coda durevole con replay e limiti; nessuna sorgente reale entra nel percorso del pilot secondo ADR-023.

## Riparazione di una fixture dopo il fermo, 19/10/2026

Il backfill del pilot usa soltanto il contratto sintetico validato e le label fisse; rifiuta record alterati e query ambigue. Query e push separati non sono atomici, quindi il secondo giro senza invio non prova assenza di duplicati sotto concorrenza o crash.
