---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/collettore/**
  - tests/**
last-verified-commit: 9710d4d
stato: componenti 1 e 2 in esercizio; INTRA3 e iLO Remote Syslog collaudati ai punti 3 e 7; eventi iLO tecnici separati con ritenzione 90 giorni attiva; catena locale provata in WSL, non installata; D7 bloccato da nomina ed elenco AdS
---

# Lavoro in corso

## Login riuscito 54HP osservato realmente, 13/10/2026

Wrapper dedicato eseguito dall'operatore: due richieste, zero eventi nella prima e un login nella seconda. Evento alle 09:08:27 locali, conferma alle 09:08:30,765602 e risposta positiva alle 09:08:41,769102. Ritardo apparente 14,769 secondi sul timestamp dichiarato, circa 11,0035 secondi dalla conferma. Report e candidato ricalcolati identici senza rete; modello e target sono del 54HP, MAC coincide con il riferimento, account/IP con il login 30HP. La prima query non include l'ora dell'evento, quindi non misura un limite inferiore del ritardo. Ispezione privata e SHA, passi 47-48 nel runbook.

Login riusciti dimostrati via API per entrambi gli switch. Sul 54HP logout e tentativo fallito restano non collaudati; ritardo massimo, clock offset e completezza generale non dimostrati. Nessun cambio a settle/overlap o installazione VM. Misura propagata in network-design, preservando il lavoro codeSigning degli altri progetti: sei documenti, indirizzo della GUI nel livello privato, timeline a 186 eventi e ISO-30 in_corso con tre viste HTML verificate allineate. Prossimo gesto: chiusura manuale della milestone dopo i controlli completi; poi adattare il criterio e collaudare il logout del 54HP. Quattro pendenze e altri gate conservano il loro stato.

## Indirizzo 54HP ricevuto, osservatore dedicato pronto, 12/10/2026

Il proprietario fornisce direttamente l'URL della pagina di login locale del XGS2220-54HP: registrato in `_notes/nebula-54hp-env.json`, non nei file pubblicabili. Superata la richiesta di screenshot per conoscere l'indirizzo; l'agente non lo contatta. Il nuovo `--switch-model` sceglie un solo apparato di quel modello nello snapshot e verifica un riferimento storico dello stesso dispositivo; sul 54HP è un evento tecnico, senza prova AdS implicita. Le riletture rifiutano un report con target diverso prima di creare il client.

Pronto `_notes/watch-nebula-publication-54hp.ps1`, con trasporto del wrapper già provato, modello esplicito, ready e conferma Invio dopo il pannello. Sette casi nuovi e 55/55 locali senza rete; mutazioni della scelta del dispositivo e della guardia sul report rilevate, ripristino SHA-256 verificato. Prova nativa del parametro 54HP, conferma dopo ready e fallimento con codice 7; Ruff e parser verdi. Prossimo passo: un solo login dopo l'avviso, Invio e attesa del riepilogo. Nuova prova reale ancora attesa; nessun parametro del poller sulla VM modificato. Passi 43-46 nel runbook, quattro pendenze e altri gate invariati.

## Milestone chiusa, prossimo apparato 54HP, 12/10/2026

Il proprietario ha eseguito `chiudi`: `main` e riferimento locale `origin/main` a `9710d4d`, albero pulito e impronta delle 17:48 coerente prima di questo giro. Osservatore, test e misura del 30HP sono versionati. STACK, dev-testing e questa scheda sono riconciliate per contenuto e ancorate al commit; nessun nuovo test funzionale necessario per questa annotazione. Nel progetto rete il secondo switch è XGS2220-54HP, «Switch piano 2 (rack)», nodo `sw54`; topologia e snapshot letti non contengono un indirizzo di gestione utilizzabile. Prossimo gesto: scheda del dispositivo in NCC e schermata per individuarne la GUI locale. Non chiedere ancora il login e non riusare il wrapper 30HP per il secondo apparato. Quattro pendenze e altri gate invariati; nessuna chiamata reale o credenziale del 54HP consultata dall'agente.

## Nuovo login 30HP osservato realmente, 12/10/2026

L'utente ha eseguito il wrapper e inviato screenshot 423 e riepilogo `observed`: cinque richieste, quattro array vuoti e poi un solo login. Evento alle 17:24:38 locali, conferma umana alle 17:24:42,827975, prima risposta positiva alle 17:25:16,030664. Ritardo apparente sul timestamp del record: ultima richiesta negativa a +22,549 secondi, risposta positiva a +38,030; quest'ultima è 33,202689 secondi dopo la conferma. Target/site, candidato esatto, account/IP rispetto al login noto e report ricalcolato identico verificati senza rete. Screenshot e SHA privati; passi 38-39 nel runbook. Il nuovo campione prova la comparsa del login, senza stabilire clock offset, ritardo massimo o copertura 54HP. Il vecchio candidato resta non associato e non blocca il lavoro. Nessun cambio a settle/overlap o installazione VM.

Misura propagata in network-design: integrazione, memoria, current-work, timeline e resume aggiornati; timeline SVG a 185 eventi, ISO-30 in_corso e tre viste HTML verificate allineate. Le modifiche precedenti di integrità-docs sono conservate; il loro messaggio di commit non è sovrascritto, proposta Nebula separata nel livello privato del progetto rete. Prossimo gesto dell'utente: `chiudi` nella radice del collettore dopo i controlli completi, messaggio pronto. Il lavoro successivo è la scheda del 54HP in Nebula per individuarne la GUI locale e predisporre il target del suo login. Le quattro pendenze elencate sotto e gli altri gate conservano il loro stato.

## Nuovo login controllato richiesto dall'utente, 12/10/2026

Il proprietario preferisce rifare un login per procedere prima. Il chiarimento dell'ora precedente resta irrisolto e non blocca il nuovo tentativo. Pronto `_notes/watch-nebula-publication-final.ps1`: pagina locale di login preparata prima dell'avvio, accesso soltanto dopo «Osservazione avviata», Invio nel terminale appena compare il pannello nel browser. `operator-confirmation.json` registra un'ora successiva all'accesso, senza inventare il secondo esatto del login. Osservazione di dieci minuti, massimo 41 POST più due diagnostici soltanto se vuota; nessun cambiamento ai parametri del poller sulla VM. Se la diagnosi trova un candidato dopo il timeout, il comando resta inconcludente per il ritardo.

La preparazione lunga era già su disco prima del riavvio ma non nella memoria. Ritrovata una mutazione ancora applicata che promuoveva la diagnosi positiva a misura riuscita: prova discriminante rossa, ripristino dal backup verificato byte per byte e con SHA-256, poi 48/48 casi verdi dei quattro verificatori senza rete. Prova nativa del wrapper con chiave finta: conferma dopo ready, figlio fallito senza richiesta di login e codice 7 conservato; parser PowerShell verde. Passi 35-37 nel runbook. Nuova misura reale ancora attesa; quattro pendenze invariate.

## Ripresa dopo riavvio, 12/10/2026

Ricostruito il punto dai passi 32-33 già presenti nel runbook e dal diario. L'impronta delle 13:05 precede otto file modificati e due nuovi; nessun commit successivo, unico albero `main` a `48be07b`. Il report diagnostico è presente e la sua impronta SHA-256 coincide con quella registrata. Il vecchio resume e i rimandi che chiedevano ancora la rilettura sono stati aggiornati. Resta da chiarire l'ora umana del login, senza ripetere API o generare accessi per questa sola ripresa. Le quattro pendenze elencate sotto mantengono il loro stato.

## Candidato ritrovato dopo la finestra originaria, 12/10/2026

Rilettura reale alle 16:15:38 locali: due POST, vecchio riferimento presente, 22 eventi unici con un login e un logout. Report ricalcolato identico. Il candidato dichiara 15:12:23 locali, fuori dalle prime query terminate a 15:08:18.655 e dopo il comando finito a 15:08:25; account/IP coincidono con il login prima verificato. Nessuna misura del ritardo cloud da questi dati. L'utente aveva confermato il login durante l'osservazione: il chiarimento sull'ora reale resta irrisolto. La successiva richiesta esplicita di un nuovo login supera il precedente arresto operativo, mantenendo non associato questo candidato. Passi 32-33 e SHA nel runbook; quattro pendenze invariate.

## Pubblicazione: venti risposte vuote con login confermato, 12/10/2026

L'osservatore è stato eseguito dalle 15:03:25 alle 15:08:25 locali: venti array vuoti, zero candidati, nessuna misura del ritardo. Ultimo estremo interrogato 15:08:18.655. Target/site coincidono con riferimento e snapshot, modello XGS2220-30HP; report e metadati verificati localmente. Dopo chiarimento l'utente conferma anche il login locale nel browser durante il comando, non soltanto l'avvio PowerShell; ora precisa non fornita. La causa resta irrisolta. Pronto `_notes/check-nebula-publication-followup.ps1`: due POST, vecchio riferimento di controllo e finestra da due ore prima dell'avvio a ora corrente, senza nuovo login. Modalità diagnostica locale, sette nuovi casi e 45/45 complessivi senza rete; mutazione del controllo rilevata e SHA ripristinato. Non cambiare il minuto di attesa del poller da questo esito. Passi 24-29 nel runbook, rilettura reale ancora attesa.

## Tracciabilità richiesta dall'operatore, 12/10/2026

Per preparare il login locale, leggere la password nel sito NCC del 30HP: `Site-wide > Configure > Site settings > Device configuration > Local credentials > Password`. Percorso riconfermato sulla guida ufficiale leggibile; fonte e passo 23 nel runbook. Nessun valore consultato dall'agente e nessun login nuovo attestato. Avviare l'osservatore prima del login di prova.

Ogni singolo passo di implementazione deve essere documentabile. Registrare nel runbook del componente data, motivo, modifica, file coinvolti, metodo di verifica ed esito; includere difetti osservati e correzioni, distinguendo prove locali, misure sull'ambiente e lavoro preparato. Memoria e schede rinviano al runbook, che alimenta il progetto compilatore-documenti. Payload e identificativi restano privati. Vincolo da conservare nelle riprese successive.

## Confronto delle finestre misurato, 12/10/2026

Milestone committata e pushata dall'utente in `48be07b`; HEAD e `origin/main` coincidenti. Il primo tentativo degli estremi era fermo prima dell'avvio per il percorso relativo; con percorso assoluto l'utente ha eseguito i tre POST alle 12:15:07.880462 UTC. Un record ciascuno, primo fallimento noto del 30HP identico nei sette campi, presente nel controllo e su entrambi gli estremi. Report ricalcolato identico e payload identici nei byte; quel record è ancora presente dopo 93,356911 ore, senza stabilire retention massima. Prossimo gate: comparsa cloud di un nuovo login locale 30HP. Usare percorsi assoluti per i comandi consegnati alla postazione.

Pronto `_notes/watch-nebula-publication.ps1`: avvio prima del login locale, avviso in console soltanto dopo `ready.json` scritto da Python e osservazione per cinque minuti più richiesta in corso, massimo 21 POST con pausa 15 secondi. Un solo candidato nuovo è osservato; vuoto o più candidati sono inconcludenti. Tempi apparenti, associazione al login da confermare sul grezzo. Otto nuovi casi, 38/38 totali senza rete; mutazioni delle risposte vuote e dell'avviso prematuro rilevate con SHA ripristinati, Ruff e parser verdi. Nessuna API eseguita per prepararlo. Passi 13-21 in runbook; poller sulla VM e tutte le altre pendenze ancora aperti. Nuova misura propagata in network-design, timeline a 182 eventi e tre HTML ISO allineati, ISO-30 in_corso.

Il confronto delle finestre alle 10:40:39.310815 UTC ha concluso dieci POST: cinque accessi 30HP identici in risposta precedente filtrata, finestra unica e quattro segmenti; 54HP vuoto, senza collaudo AdS. Report ricalcolato e coincidente, inoltro del wrapper corretto e provato senza altre API. Le tre richieste degli estremi sono poi riuscite come descritto sopra. Retention massima, completezza fisica, ritardo cloud, offline e copertura 54HP restano aperti. Misure delle finestre e degli estremi propagate in network-design, ISO-30 in_corso.

## Prima misura reale dello storico superata, 12/10/2026

L'utente ha committato la verifica in `8dba118` e lanciato il wrapper reale. I cinque accessi dell'08/10 sono ancora disponibili e identici il 12/10 alle 09:24:33.688147 UTC; età del più vecchio 90,51408 ore. Report ricalcolato dal grezzo, con 370 eventi 30HP e 586 54HP, nessun warning o duplicato esatto; nessun AAA nel 54HP. Il gate sul campione è superato, mentre retention massima, completezza, offline e copertura del 54HP restano non dimostrati. Il passo successivo confronta lo stesso periodo in una richiesta e in segmenti di cinque minuti; la risposta di 120 ore serve come terzo campione filtrato. Le pendenze elencate sotto mantengono il loro stato.

## Verifica dello storico Nebula pronta per l'operatore, 12/10/2026

Il proprietario ha versionato il poller in `98c5dbd`; alla ripresa `main` è pulito e l'impronta è coerente. Le cinque schede sono state riconciliate al commit del poller, già descritto nel lavoro precedente. Preparato il confronto locale di tutti i sette campi dei cinque accessi AAA dell'08/10, con 13 prove e una mutazione rilevata. Il wrapper privato richiama il consumer esistente della postazione per 120 ore, conserva gli identificativi nel solo output privato e stampa un esito aggregato. Nessuna lettura API nuova ancora eseguita. Prossimo passo dell'utente: lanciare il singolo comando del wrapper e trasmettere esito e percorso; poi l'agente leggerà il report e registrerà la misura, senza confonderla con retention massima o completezza. Le quattro pendenze elencate sotto rimangono aperte.

## Poller HTTPS Nebula preparato, 12/10/2026

La ripresa ha trovato `main` a `2456511`, un solo albero e nessuna modifica non committata; wrapper delle skill allineati e impronta di ripresa coerente. Il confronto rigoroso ha trovato cinque schede con ancora `2ce4cb2` superata: riconciliate per contenuto, correggendo soprattutto iLO e ritenzione già installati, e ancorate a HEAD. Il nuovo lavoro locale è il poller `bin/ads-nebula.py`, con esempio JSON, unità per istanza, diario SQLite prima dell'append, checkpoint, deduplicazione, finestre sovrapposte e arresto sui buchi o sui formati AAA ignoti. Suite Windows 100 passate e una POSIX saltata; suite Nebula Linux 35/35, tre mutazioni rilevate e ripristino SHA-256 verificato. Nessuna credenziale o sorgente è stata installata. Prove e gate in `docs/runbook-componente-3-nebula.md` e ADR-018.

Il prossimo passo è misurare retention, limiti delle risposte e ritardo cloud su eventi reali prima di compilare finestra iniziale e orizzonte di recupero; poi prova con switch offline e collaudo controllato sulla VM. Le notifiche esterne e il coordinamento del diario pendente con D-1 restano da completare prima dell'esercizio. Il lavoro locale non è ancora committato.

## Pendenze da mantenere aperte a ogni ripresa

Il task Proxmox pianificato non è ancora collaudato con il consumer TLS aggiornato; PowerShell 7 resta da provare. I dieci endpoint guest-agent che rispondono 403 al token di sola lettura restano una lacuna opzionale da valutare senza aumentare i privilegi implicitamente. L'audit retrospettivo delle fonti delle ADR di entrambi i progetti resta aperto: le fonti del nuovo poller sono registrate, ma non chiudono quel lavoro generale. La ripresa Nebula non cambia questi quattro stati. Rimangono inoltre i gate già dichiarati su D7 NAS, custodia esterna della prova e altre sorgenti.

## Chiusura TLS dello snapshot Proxmox e ripresa Nebula, 12/10/2026

Nel progetto rete `Get-ProxmoxSnapshot.ps1` ora usa `ProxmoxVerifiedHttp.cs`, che verifica CA privata, nome, validità e pin della foglia per la sola connessione; bypass globale e `-SkipCertificateCheck` rimossi. Dopo un primo dry-run fallito per il corpo vuoto della GET e la relativa correzione, il secondo dry-run reale ha validato lo snapshot senza promuoverlo. Gli endpoint opzionali guest-agent hanno dato dieci 403; task pianificato, PowerShell 7, revoca e rotazione del pin restano limiti dichiarati. Dossier, evidenze, timeline e ISO-41 del progetto rete aggiornati. Il lavoro del collettore riprende dal poller HTTPS Nebula: eventi AAA reali osservati via OpenAPI, ma codice di acquisizione, checkpoint e collaudo sulla VM non ancora realizzati.

## Due rischi MCP Proxmox sanati, 09/10/2026

Nel progetto rete la CA del cluster è stata autenticata con l'impronta SHA-256 letta dalla Shell, il nome del certificato è stato mappato e verificato in Windows, e il solo URL Proxmox nel `.env` privato è stato aggiornato. Il pacchetto MCP 0.1.0 è fissato ai byte esaminati prima dell'import; il nuovo launcher passa solo le tre variabili Proxmox, carica la CA nel solo figlio e forza `PROXMOX_ALLOW_DANGER=false` e `PROXMOX_VERIFY_SSL=true`. Il catalogo espone dieci tool di lettura e respinge `delete_instance`; candidato e configurazione attiva hanno completato `list_nodes` reale. Claude mostra il launcher connesso. SEC-025 è chiuso nel perimetro MCP; `Get-ProxmoxSnapshot.ps1` ha un bypass TLS separato da correggere. Fonti, ratio ed esiti sono nel registro `D:/network-design/docs/evidenze-sicurezza-mcp-proxmox.md`; roadmap ISO-41, timeline e copie HTML propagate. I paragrafi seguenti sono la cronologia di stati precedenti.

## Sicurezza del MCP Proxmox, 09/10/2026

Nel progetto rete il tentativo di disabilitare `PROXMOX_ALLOW_DANGER` ha superato l'avvio ma fatto fallire `list_nodes`; rollback esatto alla baseline e seconda chiamata `list_nodes` riusciti. Il codice safety esaminato sembra richiedere un file di policy per classificare come sicuro anche `list_nodes`, assente nella copia osservata. Non dichiarare risolta SEC-025. Il token `PVEAuditor` resta di sola lettura, ma `.mcp.json` conserva il flag `true` e `PROXMOX_VERIFY_SSL=false` fino a correzione collaudata. `.env` con ACL non isola i valori da Claude Code che gira come lo stesso utente. Dettagli e ISO-41 sono nel runbook M30 di `D:/network-design`.

## Nebula OpenAPI e prossimo sviluppo, 09/10/2026

La prova reale con `Get-NebulaConnectivityHistory.ps1` e `-HoursBack 24` ha letto la chiave direttamente dal `.env` privato del progetto rete. Nel JSON privato di 181.897 byte sono presenti 125 eventi del 30HP e 170 del 54HP. I cinque `AAA/authentication` del 30HP osservati nella GUI NCC dell'08/10 corrispondono uno a uno nella risposta OpenAPI, compresi tre fallimenti, un login e un logout; ogni messaggio contiene account e IP, e l'evento comprende ora e dispositivo. Nessuna installazione sul collettore. Prossimo sviluppo: poller HTTPS di soli accessi locali degli switch, con credenziale di servizio propria, deduplicazione, checkpoint e segnalazione dei buchi; verificare prima limiti, retention e switch offline. I login al portale NCC restano fuori da questa API. Il precedente `chiudi` del collettore è stato fermato dalle regole tipografiche dei documenti correnti: corretti quattro accenti e 28 trattini.

## M30, verifica e bonifica del 09/10/2026

Una nuova sessione stdio del launcher ha completato la lettura `list_nodes` sul Proxmox reale dopo il taglio delle quattro chiavi dal JSON Claude. L'audit nel progetto rete ha trovato una copia storica degli stessi valori in un backup locale del JSON; le quattro voci sono state rimosse e la scansione ripetuta dei due valori segreti correnti trova solo `.env`, senza file saltati. Nel collettore non è stata installata alcuna credenziale né una nuova sorgente. Restano il prossimo task pianificato della postazione, la nuova sessione Claude interattiva e il collaudo della sorgente Nebula per gli accessi.

## M30 dopo il cutover sulla postazione, 09/10/2026

Il progetto rete legge le quattro chiavi da `.env` con ACL limitato; MCP Proxmox connesso dopo la rimozione dal JSON Claude, `list_nodes` e dry-run Nebula/Proxmox riusciti. Il task pianificato e una nuova sessione Claude interattiva restano da osservare; l'ingestione dei login Nebula sul collettore resta da sviluppare con credenziale distinta se necessaria. Timeline, ISO-41 e tre HTML nel progetto rete sono aggiornati.

## M30 in staging sulla postazione, 09/10/2026

`.env` del progetto rete creato con ACL limitato; loader/script e writer locali installati e provati con valori finti. `.mcp.json` e il blocco `env` precedente restano attivi, candidata MCP preparata ma non applicata. Prova OpenAPI Nebula e gate reali di Proxmox/rinfresco pendenti. Timeline MD/SVG e ISO-41 con tre copie HTML allineate.

## Custodia chiavi Nebula e MCP nel progetto rete, 08/10/2026

Progettata in `D:/network-design` la migrazione M30 con ADR-031, SEC-052, runbook, timeline Markdown/SVG e ISO-41 allineata nelle tre copie HTML. Il MCP Proxmox resta sulla configurazione attuale e la prova OpenAPI Nebula non è stata eseguita. La prossima fase è la baseline read-only e la prova isolata del launcher, secondo i gate del runbook del progetto rete. Il futuro poller della VM avrà una credenziale separata.

## Ricognizione Nebula NCC, 08/10/2026

La chiave Nebula è stata localizzata nel blocco `env` privato del progetto rete; verificata la presenza, non il valore. La PowerShell ordinaria non eredita l'iniezione della sessione Claude Code del progetto rete. Per la prova API è stato preparato l'uso del parametro `-ApiKey` con variabile temporanea letta dal JSON privato, senza esporre il valore nel terminale o nella chat. Nessun dato OpenAPI nuovo è ancora arrivato.

Dopo il login NCC controllato, la ricognizione è passata ai due switch. Screenshot 241: navigazione `Site-wide > Monitor > Switches > Event log`. Screenshot 242: pagina reale con 10 eventi nell'ultima ora, tutti cambi link o STP nel campione visibile, nessun accesso amministrativo; filtri per dispositivo, parola, priorità, categoria e tag, più Export. Screenshot 243: Category contiene System, Interface, Switch, AAA, IP e Dropped. La presenza di AAA non attribuisce da sola gli eventi agli amministratori; ricerca System su 30 giorni richiesta. Immagini e impronte nel runbook.

Screenshot 247: Category System nelle ultime 24 ore dà zero corrispondenze su 246 eventi. Screenshot 248: Range 09/09-08/10 UTC+2, 262 corrispondenze System su 6.533 eventi. CSV reale delle 262 righe, due switch, sei colonne, zero righe malformate e zero occorrenze di undici termini di accesso nei campi Tag/Detail. Questa è una misura del campione System, non un login locale controllato. Chiesto il dettaglio del primo switch per la prova sul dispositivo. File privati e SHA nel runbook.

Gli screenshot 252-255 del dettaglio NCC confermano XGS2220-30HP Piano Terra, firmware V5.00(ABXO.1), management DHCP su VLAN 1 e Live tool Remote SSH; la pagina non mostra Syslog. Il progetto rete dispone già di `Get-NebulaConnectivityHistory.ps1` per acquisire via OpenAPI eventi switch e connettività in JSON su richiesta, e di `Get-NebulaSnapshot.ps1` per l'inventario. Sono strumenti del progetto rete, non job del collettore; non scaricano Change log CSV o login NCC. Richiesta apertura in sola lettura della GUI HTTPS locale dello switch prima di inserire credenziali. Immagini private e impronte nel runbook.

Screenshot 258: GUI locale HTTPS del 30HP raggiungibile; il login chiede `Local credentials` gestita da NCC, separata dall'account cloud, e avverte sulla possibile divergenza delle modifiche locali. La guida NCC colloca la password in `Site-wide > Configure > Site settings > Device configuration` e dice che viene generata alla creazione del sito. L'IT Manager non la ricordava; richiesto di leggerla in NCC senza comunicarla o modificarla e poi fare un solo login locale. Nessuna credenziale è stata indovinata o esposta.

Screenshot 259: dopo il login locale compare `Setup Wizard`, compatibile con autenticazione riuscita; la GUI non è ancora stata ispezionata e non è stata osservata una riga del login nei log. Il wizard dichiara che sovrascriverà la configurazione esistente: chiesto `Exit`, senza `Apply & Save`, e screenshot della pagina principale. Copia privata e impronta nel runbook; ISO-30 resta in corso.

Screenshot 261-262: `Exit` ha portato alla dashboard locale del 30HP in Cloud Mode senza salvare il wizard. `Message Center` segnala tre fallimenti dall'ultimo successo, non attribuibili senza dettagli; `System Log` è un Quick Link e ne è stata chiesta la lettura. Ora mostrata 14:57 a fronte di screenshot salvati alle 16:57 CEST, compatibile con UTC ma da verificare. Copie private e SHA nel runbook; nessun evento ancora sul collettore.

Screenshot 263: `MONITOR > System Log` locale contiene login HTTPS `admin` riuscito alle 14:55:47Z e fallimenti alle 14:54:57Z, 14:54:41Z, 14:53:43Z. Le parti destre delle righe sono tronche; chiesto `Download` per leggere IP e account completi. Gli eventi sono prodotti localmente, ma non ne è verificata la presenza in NCC, API o collettore. Il manuale XGS2220 distingue configurazione NCC inviata al dispositivo e modifiche locali non sincronizzate a NCC; `SYSTEM > Syslog Setup` è il prossimo punto da leggere. ISO-30 in corso.

Export locale `syslog.log`: 122.529 byte, SHA-256 `cf028a9827634e848cb740e3dd791de6f14d12f0bb989cf544633daad10e38ad`, 1.966 righe e quattro autenticazioni: successo 14:55:47Z, fallimenti 14:54:17Z, 14:54:11Z, 14:53:43Z. La lettura precedente da screenshot dei due orari più recenti era errata. Le righe complete hanno account e IP; i fallimenti coinvolgono due account distinti, tutte le quattro righe hanno un solo IP sorgente. File e analisi restano privati; chiesta pagina `SYSTEM > Syslog Setup` senza modifiche. Nessun trasporto AdS dello switch è ancora verificato.

Screenshot 264: `SYSTEM > Syslog Setup` locale OFF, System/Interface/Switch/AAA/IP disattivati e nessuna destinazione. Zyxel documenta una destinazione Syslog di sito in NCC Reporting, con invio diretto UDP 514 dai dispositivi; chiesto screenshot reale della sezione prima di configurare un flusso condiviso da switch/AP. Nessuna modifica eseguita e nessuna consegna al collettore dimostrata.

Screenshot 266: NCC Site settings > Reporting mostra nessun server Syslog, `+ Add` disponibile e `Save` disabilitato; timezone per syslog e AP traffic log OFF. Chiesto di aprire solo `+ Add` per leggere tipo e destinazione senza salvare. Nessun invio diretto dal sito configurato; telemetria NCC distinta.

Screenshot 270: `+ Add` aperto senza modifiche; campi obbligatori Server IP e Types, entrambi vuoti, Save disabilitato. Chiesta apertura del menu Types, senza inserire IP, per verificare i tipi di log. Nessun invio configurato.

Screenshot 271: Types distingue Switch log da AP log e log dei firewall. Nessun Save. Nftables permette UDP 514 dalla LAN `/19`, ma rsyslog manda i nuovi mittenti non iLO a `/srv/ads/`; prima del site-wide Switch log serve un filtro di separazione. Chiesto Cancel e ricerca `authentication` nell'Event log NCC dell'ultima ora per capire se il login locale è disponibile via API. ISO-30 in corso.

Screenshot 272: NCC Event log mostra cinque eventi `AAA/authentication` del 30HP nell'ora 16:10-17:10 CEST: tre fallimenti e un login coincidono per timestamp e testo con l'export locale; un logout per timeout è successivo. Chiesta prova del tool API `Get-NebulaConnectivityHistory.ps1` con sei ore di eventi in cartella privata, senza comunicare la chiave. Decisione di collaudo e criteri API/Syslog in ADR-016; nessun canale in esercizio per questi accessi.

L'utente ha aggiunto due obiettivi successivi alla raccolta delle sorgenti: hardening della VM Debian del collettore e una piccola interfaccia web raggiungibile solo dalla LAN, accessibile al solo amministratore di sistema autorizzato. Sono da progettare e collaudare; la nomina AdS formale e l'identificativo definitivo dell'account autorizzato non sono ancora disponibili. Stato e ratio in ADR-017 e roadmap di progetto.

Dopo iLO, la prossima famiglia da verificare è Nebula NCC con due switch e quattro AP. La guida ufficiale indica `More > Recent logins` come cronologia dell'account corrente con IPv4, località e ora; il `Change log` dell'organizzazione registra modifiche. Lo staff Zyxel conferma che la vista dei login è personale. Screenshot 203 e 204 sul tenant reale: la tabella mantiene una sola riga del 09/09/2026 anche dopo F5, mentre il piè di pagina cambia da `Last login: 1 seconds ago` a `15 minute ago`. Dopo Logout e nuovo login riuscito, screenshot 223 mostra una nuova riga del 08/10/2026 13:35:15 UTC: la vista registra questo successo, ma non mostra account per riga, esito o export. Screenshot 205: Change log disponibile con Export e colonne di modifica, zero eventi nel range 01-08/10 e storico dal 12/09/2024. Screenshot 207: ricerca di settembre con 15 modifiche e nessun login/logout nel campione. Screenshot 212: menu Export con CSV e XML. Il CSV reale è stato letto nel livello privato: 15 righe, nove colonne, un amministratore distinto, zero etichette di login/logout; non è dimostrato un canale automatico. I fallimenti NCC restano non verificati. Gli eventi tecnici storici degli switch non hanno mostrato login nel campione di 18.753 righe; chiesta la pagina Event log dei due switch. Fonti, file privati e limiti in `docs/runbook-componente-3-nebula.md`.

> La fonte di verità su cosa è fatto resta `memory/index.md` e il work-log, non le spunte di questo file. Ogni feature si descrive con lo schema fisso sotto, così il lavoro pendente è leggibile senza ricostruire il contesto da capo.

## Modo di lavoro concordato con l'utente

Direttive d'uso date dall'utente durante il lavoro sugli host, valide per ogni sessione finché non le cambia. Sugli apparati si procede un passo alla volta, e ogni risposta finisce con il passo successivo da fare, non soltanto con l'esito registrato. I comandi verso collettore e host si consegnano per la PowerShell di Windows via SSH, non per la console noVNC. L'utente lancia i comandi e trasmette screenshot dalla cartella di Screenpresso; l'agente li legge, registra esiti e misure nel work-log e nel runbook della sorgente nello stesso giro. I runbook si scrivono perché `D:/compilatore-documenti` possa ricavarne in ogni momento un documento per un cliente. Si resta sullo scopo del collettore: i difetti degli apparati emersi strada facendo, come la lentezza di INTRA2, si misurano quanto basta, si annotano e si portano in `D:/network-design`, senza proseguire la diagnosi qui. Da network-design e da compilatore-documenti si legge solo lo stretto necessario.

Il 2026-10-06 l'utente ha precisato che gli ultimi comandi su `B:` partivano da NinjaOne RMM, che offre diversi contesti di esecuzione. Poiché il contesto effettivamente mostrato era sempre elevato, ulteriori prove nella stessa modalità non misurerebbero la sessione ordinaria. L'utente ha chiesto di interrompere quella diagnostica e tornare allo sviluppo del collettore. La riconnessione di `B:` dopo un login Windows reale resta un controllo operativo futuro, senza bloccare il codice del componente seguente.

## Feature: componente 1, VM + Debian + nftables + chrony + TLS

Cosa fa: prepara tutto ciò che serve a creare la VM del collettore e a portarla a una Debian 13 configurata e raggiungibile in TLS, cioè il punto 1 della sezione 7 dell'handoff, che la sezione 0 non blocca. Scadenza dello studio per i punti 1-4: 23/10/2026.

File creati:

```
bin/adsparams.py                  lettura di parametri.yaml senza PyYAML
bin/ads-render.py                 albero di configurazione da config/collettore/ e parametri
bin/ads-vm-command.py             stampa il comando qm create, non lo esegue
bin/ads-pki.sh                    CA e certificato del collettore, sulla postazione admin
bin/ads-bootstrap.sh              installazione sul collettore, con --prova
config/collettore/etc/...         nftables (template), chrony, sshd, unattended-upgrades, qemu-ga
tests/                            pytest, bats, fixture, verifica Debian 13 in container
ruff.toml, .gitattributes         lint Python, LF su script e configurazioni
```

Definition of done:

- [x] codice e configurazioni scritti, lint e test verdi (38 pytest, 14 bats su Windows e Linux, verifica in container `debian:trixie`)
- [x] `config/parametri.yaml` compilato il 2026-09-30: valori Proxmox dallo snapshot di network-design, VMID 210, FQDN, indirizzo del collettore nella serie dei server confermato dall'utente, due amministratori (ADR-007, ADR-008); indirizzo verificato libero il 2026-09-30 dalla postazione di Alessio Sopranzi (ping senza risposta, vicino `Unreachable` con indirizzo fisico nullo)
- [x] PKI emessa il 2026-09-30 in `%USERPROFILE%\ads-pki\` sulla postazione di Alessio Sopranzi; pacchetto per il collettore in `build/pacchetto/`, provato con `--prova`
- [x] netinst `debian-13.7.0-amd64-netinst.iso` scaricata in `local` e verificata con SHA-512 (2026-10-01)
- [x] VM 210 creata sull'host con il comando stampato da `ads-vm-command.py --iso`, configurazione verificata con `qm config` (2026-10-01)
- [x] `ads-bootstrap.sh` imposta il fuso `Europe/Rome` (l'installazione del 2026-10-01 ha il fuso centrale degli Stati Uniti), provato in bats
- [x] Debian 13.7 installata, `scsi1` su `/srv/ads` con `nodev,nosuid,noexec`, chiavi raccolte, `ads-bootstrap.sh` eseguito il 2026-10-01 (via SSH dalla postazione, ADR-012 per il desktop rimasto)
- [x] password locali (`tvezeni` temporanea, da cambiare al suo primo accesso; `asopranzi` quella dell'installer per decisione dell'utente), nome completo di `tvezeni`, ISO staccata, swap file da 1 GB: tutto il 2026-10-01
- [x] collaudo punto 1 superato; punto 2 superato nella parte di rete (SSH scartato dall'host non ammesso, 6514 ammessa), da completare con rsyslog attivo; punto 7 soddisfatto lato collettore, da completare sulle sorgenti

Stato delle voci [Non verificato] del componente, dall'handoff sezioni 1-3:

| Voce | Stato | Come si chiude |
|---|---|---|
| Sintassi di `allow-rpcs` in `/etc/qemu/qemu-ga.conf` | Verificata in container e sull'host il 2026-10-01: `qm agent 210 ping` risponde e `qm guest exec 210 -- id` è rifiutato con «Command guest-exec has been disabled» | Chiusa; collaudo punto 1 superato |
| rsyslog non installato di default su Debian 13 | Aperta: il container non è un'installazione netinst | Irrilevante per il risultato, perché `ads-bootstrap.sh` lo installa comunque; si annota dopo l'installazione con `dpkg -l rsyslog` |
| Modello CPU `x86-64-v2-AES` su PVE 8.x | Verificata il 2026-09-30 sullo snapshot Proxmox di network-design delle 07:30: il nodo è a pve-manager 8.3.4 e sette VM su dieci usano già `x86-64-v2-AES`; la VM100 usa già q35, OVMF ed efidisk con chiavi pre-caricate sullo storage SERVIZI | Chiusa per questo nodo; l'avviso di `ads-vm-command.py` resta perché vale per qualunque host 8.x |
| Origini di sicurezza di unattended-upgrades su Debian 13 | Verificata in container: Debian 13 abilita di default anche l'origine `label=Debian`, e senza `#clear` resterebbe attiva | Chiusa |
| Forma delle righe `pool` in `chrony.conf` di Debian 13 | Verificata in container: una riga `pool`, `sourcedir /etc/chrony/sources.d` presente, `chronyd -p` accetta il risultato | Chiusa |
| Fluent Bit confronta `Host` con il SAN del certificato (Inferenza, sezione 3) | Aperta | Si verifica nel pilota Windows (punto 7): il certificato porta FQDN e IP nel SAN, quindi regge entrambe le scelte |

Domande aperte:

La rete attuale smentisce due presupposti dell'handoff: nessun bridge di Proxmox è VLAN-aware e la LAN è un'unica rete, non una LAN più una VLAN server (scheda `design-and-security.md` di `D:/network-design`). Il codice ne tiene conto rendendo facoltativi `proxmox.vlan_server` e `rete.subnet_server`, ma resta da decidere con chi amministra la rete se il collettore debba nascere su `vmbr0` senza tag, come oggi è possibile, o aspettare la segmentazione del piano firewall di network-design; la regola nftables ammette 514 e 6514 dall'intera LAN finché non ci sono reti più strette. Una volta decisa, la scelta va riportata anche in network-design come nuova VM e nuova sorgente di traffico, secondo ADR-004.

Le due domande di ADR-007 sono chiuse: le postazioni hanno indirizzo fisso, e gli account sono personali (ADR-008). Prima del bootstrap ciascun amministratore genera sulla propria postazione una chiave SSH e consegna il solo file `.pub`, nominato `asopranzi.pub` e `tvezeni.pub` e raccolto nella cartella privata `_notes/chiavi/` della postazione di Alessio Sopranzi, ignorata da git, da cui arriva al collettore insieme al materiale TLS; la chiave è generata come `ads-collector_ed25519` in `.ssh` del profilo utente, senza passphrase per scelta dell'utente; al 2026-09-30 ci sono entrambe; dopo il bootstrap, dalla console, si imposta a ciascuno una password temporanea con scadenza immediata. Aperta dal 2026-10-01, misurata: con il desktop (ADR-012) la VM ha 546 MiB disponibili su 1.9 GiB; chiudere la sessione grafica quando non serve, o portare la RAM a 4 GB a VM spenta. Aperte dal 2026-10-01 per ADR-010 (`docs/modello-di-custodia.md`): chi custodisce la prova, cioè quale TSA e chi amministra il supporto immutabile, che non può essere Intrawelt né l'MSP; se la finestra del giorno in corso vada stretta; se serva un'analisi continua; la verifica annuale del punto 4.4 è decisa (ADR-011: IT Manager e IT Assistant, MSP in loro assenza, con la cautela della verifica incrociata). Candidati per la prova: TSA qualificata via RFC 3161 (InfoCert verificata sul manuale) e, come terzo custode da interrogare, Intrusa. Il componente 5 dipende dalla prima risposta. Aperta dal 2026-10-01: Wazuh. Lo studio `docs/confronto-wazuh.md` propone di tenere il collettore come sistema di registrazione, di aggiungere GravityZone come sorgente e di valutare Wazuh come livello di analisi dopo il pilota Windows; serve la decisione dell'utente e, se possibile, lo studio completo dell'MSP. Il nome `ads-collector.int.intrawelt.com` va registrato nel DNS del firewall, come prevede M25 di network-design, prima di configurare le sorgenti TLS.

## Feature: componente 2, rsyslog ricevente e accessi al collettore

Cosa fa: riceve i log delle sorgenti su 514/udp e 6514/tcp in TLS e li scrive in `/srv/ads/<ip>/<giorno>.log` nel formato `AdsLine`; instrada nello stesso ruleset gli accessi al collettore stesso (`sshd`, `sudo`, `su`, `login`, `systemd-logind`, `gdm-password`), in `/srv/ads/127.0.0.1/`. Punto 2 della sezione 7 dell'handoff.

Definition of done:

- [x] configurazione generata da `config/collettore/etc/rsyslog.d/10-ads.conf.template`, installata e controllata dal bootstrap nella versione precedente al filtro iLO
- [x] verifica in container `debian:trixie`: ricezione UDP e TLS, TCP in chiaro scartato, accessi locali instradati, cinque campi, permessi
- [x] bootstrap rieseguito sul collettore con il pacchetto nuovo il 2026-10-01, senza errori e senza pacchetti nuovi (rieseguibile)
- [x] sul collettore vero: un accesso SSH di un amministratore compare in `/srv/ads/127.0.0.1/` come `sshd-session ... Accepted publickey`, con impronta della chiave (2026-10-01, dopo la correzione del filtro)
- [x] una riga inviata da una sorgente ammessa (l'host Proxmox) compare nella sua cartella, `root:ads` 0750, nel formato a cinque campi (2026-10-01)
- [ ] collaudo punto 2 completo: da una sorgente non ammessa nessuna scrittura; con la LAN unica /19 serve un mittente fuori da quella rete

Rinviato: filtro D7 del QNAP, che dipende dall'elenco AdS approvato (sezione 0, bloccante).

## Feature: punto 3, host Proxmox come sorgente

Cosa fa: l'host invia al collettore, in TLS con verifica del certificato per nome, i login SSH, le autenticazioni di `pvedaemon` e l'access log di `pveproxy`, con coda su disco se il collettore è fermo (handoff, sezione 5). Amministra l'host l'IT Manager; l'MSP vi accede via NinjaOne.

Definition of done:

- [x] ricognizione in sola lettura dell'host: rsyslog assente, nomi dei programmi `sshd` e `pvedaemon`, access log da 8 MB
- [x] `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template` e prova in `debian:bookworm` verdi, con controllo negativo dimostrato
- [x] rsyslog e rsyslog-gnutls 8.2302 installati sull'host il 2026-10-01
- [x] il journal arriva a rsyslog sull'host: un login SSH compare in `/var/log/auth.log` (verificato il 2026-10-01)
- [x] configurazione e CA copiate, `rsyslogd -N1` valido, rsyslog riavviato e attivo (2026-10-01)
- [x] un login SSH e uno web riusciti all'host compaiono in `/srv/ads/<IP host>/` sul collettore, con i cinque campi (2026-10-01 e 2026-10-02); richieste periodiche e task esclusi
- [x] un login SSH e uno web falliti compaiono (2026-10-02): `pvedaemon ... authentication failure; rhost=... user=...` e `sshd ... Failed password`; nessuna riga 401 perché la forma `extjs` dell'API risponde sempre 200; esito letto da `pvedaemon`. Collaudo punto 3 per l'host superato il 2026-10-02

## Feature: punto 3, firewall USG FLEX e NAS QNAP

Cosa fa: il firewall (ZLD 5.42) invia in syslog UDP sulla 514 i propri log, fra cui i login amministrativi; i NAS QNAP inviano gli accessi amministrativi con il metodo che il loro firmware consente. Amministrati dall'IT Manager.

Definition of done:

- [x] firewall: stato attuale di `Log Settings` letto il 2026-10-02: quattro Remote Server vuoti e inattivi, setup da zero
- [x] `D:/network-design` aggiornato il 2026-10-02 con le modifiche a firewall, host Proxmox e collettore (ADR-004), da committare in quel repository
- [ ] decisione aperta: backup del disco di sistema della VM 210, che nessun job seleziona
- [x] firewall: Remote Server 1 verso il collettore, categorie Authenticate e System; login riuscito, fallito e logout registrati con i cinque campi, nella categoria User (2026-10-02)
- [x] firewall: sottocategoria System Monitoring spenta il 2026-10-02; nessun messaggio di stato dopo lo spegnimento
- [ ] domanda aperta: account amministrativi personali sul firewall e su HERO (oggi `admin` generico) e su Proxmox (oggi `root`), come ADR-008
- [x] firewall: NTP su `ntp1.inrim.it`, fuso manuale di Roma, ora legale europea a mano (2026-10-02); [Non verificato] semantica dell'ora di fine, da controllare dopo il 25/10/2026
- [x] collaudo punto 7 per il firewall: ora dichiarata e ora di ricezione coincidono entro il secondo (2026-10-02)
- [ ] domanda aperta: includere la categoria VPN se gli AdS o l'MSP accedono dall'esterno con la VPN del firewall
- [x] NAS: modello e firmware letti sui quattro dispositivi; per INTRA3 la schermata informativa del 2026-10-05 conferma TS-210 e QTS 4.2.6 build 20240618
- [x] HERO: invio TLS sulla 6514 di log eventi e accessi, NTP su INRIM ogni ora, fuso di Roma (2026-10-02)
- [x] INTRA2: invio TLS sulla 6514 di log eventi e accessi, NTP su INRIM ogni ora, fuso di Roma, collaudi punti 3 e 7 (2026-10-02)
- [x] INTRA: QTS 4.2.6, invio UDP sulla 514 di log eventi e connessioni (HTTP, SSH, Telnet, SMB), NTP su INRIM ogni ora, collaudi punti 3 e 7 (2026-10-02)
- [ ] domanda aperta: righe SMB dell'account `backup` di Proxmox su INTRA, una ogni 10 secondi circa: tenerle, filtrarle sul collettore o togliere SMB
- [x] INTRA3: invio syslog UDP 514 di eventi e connessioni applicato secondo l'operatore; file e righe del NAS ricevuti sul collettore
- [x] INTRA3: collaudi 3 e 7 superati con accessi amministrativi controllati, confronto degli orari e `chronyc tracking` sul collettore; contatto NTP del NAS non osservato direttamente
- [ ] D7: separare gli accessi AdS dagli altri log NAS; l'utente conferma che non esistono ancora nomina formale firmata né elenco AdS approvato. Servono inoltre destinazione e politica del flusso ordinario (ADR-014)
- [x] INTRA3: l'utente conferma il 2026-10-05 che l'interfaccia web del NAS è raggiungibile; la sola schermata informativa è stata letta, senza modificare impostazioni
- [x] INTRA3: screenshot 13 del pannello `System Information` letto il 2026-10-05: TS-210, 249 MB di RAM, firmware 4.2.6 build 20240618, fuso di Roma; NTP e invio log ancora da verificare. L'utente dichiara che solo i due amministratori interni montano le condivisioni come unità di rete
- [x] INTRA3: il 2026-10-06 la scheda `System Connection Logs` è vuota e mostra `Start Logging`, quindi la registrazione delle connessioni è spenta; nessuna impostazione è stata cambiata. Non si possono ancora osservare le connessioni effettive o decidere D7. Evidenza privata `_notes/evidenze/NAS-INTRA3-connessioni-2026-10-06.png`
- [x] INTRA3: `Options` letto il 2026-10-06 senza salvare: selezionati HTTP, SSH, FTP e Telnet; SMB, iSCSI, AFP, RADIUS, VPN e archiviazione automatica dei log non selezionati. Evidenza privata `_notes/evidenze/NAS-INTRA3-opzioni-log-2026-10-06.png`
- [x] INTRA3: `Syslog Client Management` letto il 2026-10-06 senza salvare: invio remoto disattivato, server vuoto, porta UDP 514 mostrata ma disabilitata; eventi selezionati ma disabilitati, connessioni non selezionate e disabilitate finché non si avviano i log locali. Evidenza privata `_notes/evidenze/NAS-INTRA3-syslog-2026-10-06.png`
- [x] INTRA3: pagina `Time` letta il 2026-10-06 senza modifiche: sincronizzazione automatica con `pool.ntp.org` ogni 7 giorni, fuso di Roma; successo dell'ultima sincronizzazione e scarto temporale non dimostrati. Evidenza privata `_notes/evidenze/NAS-INTRA3-tempo-2026-10-06.png`
- [x] INTRA3: `Daylight Saving Time` letto il 2026-10-06 senza modifiche: adeguamento automatico attivo, offset di 60 minuti, periodo mostrato 29/03/2026 02:00 - 25/10/2026 03:00, tabella personalizzata disattivata. Evidenza privata `_notes/evidenze/NAS-INTRA3-ora-legale-2026-10-06.png`
- [x] INTRA3: dopo l'autorizzazione dell'utente a configurare come gli altri NAS, lo screenshot 30 del 2026-10-06 mostra nella pagina `Time` `ntp1.inrim.it` e intervallo di 1 ora dopo `Apply`; non prova ancora l'esito della sincronizzazione né lo scarto. Evidenza privata `_notes/evidenze/NAS-INTRA3-ntp-inrim-2026-10-06.png`
- [x] INTRA3: l'utente riferisce di aver applicato `Options` con HTTP, SSH, Telnet e SMB attivi e FTP spento; nessuna schermata di riscontro delle opzioni
- [x] INTRA3: dopo `Start Logging`, l'utente conferma che il pulsante ora dice `Stop Logging`; registrazione locale attiva
- [x] INTRA3: screenshot 32 della tabella aggiornata mostra `Stop Logging`, 326 righe totali e operazioni SMB sui file (`Write`, `Add`, `Delete`, `Read`, `MakeDir`); account, postazione e risorsa sono presenti, ma tasso giornaliero e assenza di utenti non AdS non sono dimostrati. Evidenza privata `_notes/evidenze/NAS-INTRA3-connessioni-attive-2026-10-06.png`
- [x] INTRA3: screenshot 35 di `Syslog Client Management` dopo l'avvio: client ancora spento, campi e caselle disabilitati, inclusa `System Connection Logs`; verificare se si abilita dopo aver spuntato `Enable Syslog`. Evidenza privata `_notes/evidenze/NAS-INTRA3-syslog-dopo-avvio-2026-10-06.png`
- [x] INTRA3: screenshot 36 con `Enable Syslog` spuntato ma non applicato: server vuoto, UDP 514 attivo, eventi selezionati, connessioni selezionabili ma non ancora selezionate. Evidenza privata `_notes/evidenze/NAS-INTRA3-syslog-campi-abilitati-2026-10-06.png`
- [x] INTRA3: screenshot 38 prima di `Apply All` con server del collettore, UDP 514 ed entrambe le categorie selezionate. Evidenza privata `_notes/evidenze/NAS-INTRA3-syslog-preapply-corretto-2026-10-06.png`
- [x] INTRA3: l'utente riferisce `Changes applied` dopo `Apply All` e stessi valori alla riapertura della scheda; persistenza riferita, senza seconda schermata
- [x] INTRA3: l'output del comando `find` eseguito dall'utente mostra un file del giorno aggiornato negli ultimi dieci minuti nella cartella del collettore corrispondente all'indirizzo di INTRA3; contenuto delle righe ancora da leggere
- [x] INTRA3: ultime righe sul collettore da `NAS-INTRA3/qlogd` mostrano tre `SAMBA Login Fail` ripetuti in circa due secondi da una postazione e un account non ancora classificati; per le tre righe ora dichiarata e ricevuta differiscono meno di un secondo. Dettagli identificanti nella nota privata
- [x] INTRA3: la postazione dei tentativi SMB è non AdS; l'utente ha chiesto di conservarne accesso e log, separati da quelli AdS. SMB resta selezionato
- [x] Accesso `B:` di INTRA3 ripristinato nella PowerShell «Utente connesso» a 64 bit della postazione non AdS: radice elencabile e file non vuoto leggibile; riconnessione dopo nuovo accesso Windows non ancora provata
- [x] `screenshot_41.png`: mappatura persistente `B:` ricreata in PowerShell amministratore; `net use` riuscito e `Get-SmbMapping` con stato `OK`. La schermata contiene una password e non è stata copiata nel progetto
- [x] Su richiesta dell'utente, verificato `B:` da PowerShell «Utente connesso» a 64 bit con esito `ACCESSO_OK` e `LETTURA_OK`; la differenza rispetto alla prima shell che non vedeva l'unità resta non chiarita
- [x] Una PowerShell ha restituito «unità B non esiste»; ripetendo lo stesso comando in PowerShell «Utente connesso» a 64 bit, l'utente ha ottenuto `ACCESSO_OK` senza creare una nuova mappatura. La differenza fra le sessioni non è ancora accertata
- [x] Letto un byte da un file non vuoto di `B:` senza mostrarne il contenuto; sul NAS risulta un `Read` dalla medesima postazione, temporalmente coerente ma non associabile con certezza alla prova
- [x] `Get-Item` conferma `CARTELLA` per il percorso del primo `Get-Content`: l'«accesso negato» non dimostra un problema di permessi SMB
- [x] La prova di lettura di un byte da un file non vuoto della condivisione ha restituito `LETTURA_OK` nella PowerShell «Utente connesso» a 64 bit: accesso ripristinato nella sessione corrente
- [ ] Verificare la riconnessione di `B:` dopo un nuovo accesso Windows. L'utente gestisce separatamente la credenziale esposta nello screenshot 41; non risulta ancora cambiata
- [x] Ultime dieci righe del giorno filtrate sulla postazione non AdS: tutte `SAMBA Login Fail` tra le 12:33:38 e le 12:36:08, con `Users: User`; il campione non contiene eventi riusciti
- [x] Conteggio del 2026-10-06 per la postazione non AdS nel file di INTRA3 sul collettore: 71 `Login Fail`, 2 `Login OK`, 1 `Read`, filtrati per `Source IP` e raggruppati per `Action`
- [x] Orari delle azioni riuscite della postazione non AdS: `Login OK` 12:11:40 e 12:24:15, `Read` 12:33:28; le righe `Login Fail` successive iniziano alle 12:33:38 e la causa resta sconosciuta
- [ ] Diagnostica separata dei 71 `Login Fail` della postazione non AdS, senza attribuirli alla mappatura funzionante sulla sola base dell'indirizzo; l'utente ha chiesto di proseguire il collaudo NAS
- [x] Primo controllo dopo il ripristino di `B:`: le ultime otto righe SMB della postazione non AdS nel file del giorno sono tutte `Users: User`, `Login Fail` fra le 13:41:25 e le 13:41:29; al momento della query non risultano righe SMB successive per quella postazione
- [ ] Nella PowerShell ordinaria a 64 bit della postazione non AdS leggere mappatura `B:` e connessioni SMB attive, mostrando solo percorso remoto, stato e identità usata; cercare poi l'origine dei tentativi falliti senza attribuirli automaticamente alla mappatura
- [x] L'ultimo `Get-SmbMapping -LocalPath B:` non trova la mappatura e `Get-SmbConnection` mostra `Public` su INTRA3 con `UserName` riferito alla postazione amministrativa; il comando non include `hostname`, quindi non si può attribuire con certezza l'assenza di `B:` alla postazione non AdS. Verificare prima il nome del computer nella stessa PowerShell
- [x] Un nuovo `hostname` nella PowerShell con prompt `C:\WINDOWS\system32` restituisce `<POSTAZIONE_NON_ADS>`; il prompt del precedente controllo era `C:\Users\Utente`, quindi non è provato che i due comandi siano stati eseguiti nella stessa finestra
- [x] Nella PowerShell appena identificata come `<POSTAZIONE_NON_ADS>`, controllare identità, architettura ed elevazione della sessione, poi mappatura `B:` e connessioni a INTRA3 includendo il campo `Credential`; non mostrare password
- [x] Nella PowerShell di <POSTAZIONE_NON_ADS> l'utente ha riportato `User=<POSTAZIONE_NON_ADS>\User`, `Process64Bit=True`, `Elevated=True`; nel messaggio non compaiono risultati delle query su mappatura e connessioni
- [ ] Aprire una PowerShell ordinaria su <POSTAZIONE_NON_ADS>, confermare `Elevated=False` e `Process64Bit=True`, poi ripetere lì la verifica di `B:` e delle connessioni SMB; la finestra elevata può avere mappature di unità diverse
- [x] Ripetuto il controllo nella PowerShell indicata dall'utente: ancora `<POSTAZIONE_NON_ADS>\User`, 64 bit, `Elevated=True`; non risulta una finestra ordinaria distinta
- [x] Verificare direttamente nella finestra corrente di <POSTAZIONE_NON_ADS> mappatura `B:`, connessione SMB con campo `Credential` e accesso in sola lettura alla radice, senza stampare nomi di file; se l'unità manca, attribuire il risultato solo a questa sessione elevata
- [x] Nella finestra elevata a 64 bit di <POSTAZIONE_NON_ADS> `Get-SmbMapping` mostra `B:` verso la condivisione di INTRA3 con stato `OK` e l'elenco della radice restituisce `ACCESSO_OK`; la query `Get-SmbConnection` eseguita prima dell'elenco non ha mostrato righe
- [x] Dopo l'accesso alla radice di `B:`, ripetere `Get-SmbConnection` nella stessa finestra per leggere `Credential` dell'eventuale connessione ora attiva, senza password
- [x] Dopo l'accesso a `B:`, `Get-SmbConnection` mostra `NAS-INTRA3/Public` attivo con `Credential` dell'account NAS previsto per la postazione, distinto dall'account Windows locale (`UserName`); dialetto SMB 2.1 e due aperture
- [x] Leggere in sola lettura `HKCU:\Network\B` nella stessa sessione per verificare se Windows ha registrato la mappatura da riconnettere al prossimo accesso; la prova reale della riconnessione dopo nuovo login resta separata
- [x] Nella sessione elevata di <POSTAZIONE_NON_ADS> la voce `HKCU:\Network\B` è assente: la mappatura attiva di `B:` non risulta registrata lì per la riconnessione al login
- [x] Elencare in sola lettura le connessioni correnti con `net use` prima di valutare `net use /persistent:yes`, che secondo Microsoft salva le connessioni correnti per i login successivi; non applicarlo senza sapere quali altre connessioni includerebbe
- [x] `net use` sulla sessione elevata di <POSTAZIONE_NON_ADS> elenca una sola connessione, `B:` verso la condivisione INTRA3, con stato `OK`; indica che le nuove connessioni saranno memorizzate, ma `HKCU:\Network\B` resta assente nel controllo precedente
- [x] Eseguire `net use /persistent:yes` nella stessa sessione e verificare subito se compare `HKCU:\Network\B`; il comando riguarda la sola connessione corrente elencata e non deve interromperla
- [x] `net use /persistent:yes` risponde «Esecuzione comando riuscita», ma `HKCU:\Network\B` resta assente: l'impostazione generale non ha registrato la mappatura `B:` già attiva
- [x] Ricreata in modo mirato solo `B:` nella PowerShell elevata: `net use B: /delete` riuscito, nuova mappatura con `/persistent:yes` e password richiesta interattivamente riuscita; la radice restituisce `ACCESSO_OK`
- [x] La lettura immediata di `HKCU:\Network\B` dopo la nuova mappatura dà ancora `PathNotFound`: in questa sessione la registrazione per la riconnessione non è visibile; la causa non è accertata
- [ ] Alla prossima apertura ordinaria di Windows verificare se `B:` si riconnette. Non ripetere cancellazione e rimappatura ora; l'accesso corrente è funzionante
- [x] Sul collettore le ultime otto righe SMB della postazione non AdS mostrano sette `Login Fail` con `Users: User` fra le 16:32:20 e le 16:32:25, seguiti da `Login OK` con l'account NAS previsto alle 16:34:00; nessuna riga successiva nel campione al momento della query
- [x] Il controllo successivo sul client restituisce ancora `Elevated=True` e `ACCESSO_OK`: conferma l'accesso nella finestra amministrativa, senza aggiungere prova per la sessione ordinaria
- [ ] Aprire PowerShell dal desktop con `Win+R`, senza elevazione, e provare `B:` solo se il nuovo processo risulta `Elevated=False`; se è ancora elevato, fermare i controlli ripetuti e chiarire la configurazione UAC
- [ ] Attribuire i fallimenti SMB precedenti solo se ricompaiono dopo il login riuscito o se emergono prove dal client; la sequenza attuale conferma un accesso riuscito ma non identifica la causa dei tentativi falliti
- [x] collaudo punto 3 per il firewall: login riuscito, fallito e logout con i cinque campi (2026-10-02)
- [x] collaudo punti 3 e 7 per HERO (2026-10-02)
- [x] collaudo punti 3 e 7 per INTRA3; gli stessi punti sono già superati per HERO, INTRA2 e INTRA
- [x] Primo passo del collaudo di INTRA3: dalla postazione amministrativa raggiungere la pagina di login web del NAS, uscendo dalla sessione QTS se aperta; modulo confermato dall'utente
- [x] L'utente conferma la pagina di login QTS di INTRA3 visibile dalla postazione amministrativa
- [x] Effettuare un solo login amministrativo riuscito con le credenziali già in uso, riferire pannello aperto e ora locale approssimativa; riga verificata nel file del giorno sul collettore
- [x] L'utente riferisce login amministrativo riuscito su INTRA3 alle 14:05 del 2026-10-06, pannello aperto e ora QTS 14:05
- [x] Login web amministrativo `Login OK` ricevuto alle 14:05:33.736335 con ora NAS 14:05:33, cinque campi `AdsLine`, account, postazione e risorsa `Administration`; differenza osservata 0,736335 s
- [x] Uscire da QTS, confermare la pagina di login, poi eseguire un solo tentativo fallito controllato e cercarlo nel file del collettore
- [x] L'utente conferma di essere uscito da QTS e di vedere di nuovo la pagina di login di INTRA3
- [x] Un solo tentativo con account amministrativo e password volutamente errata; messaggio e ora registrati, `Login Fail` trovato nel file del collettore
- [x] Screenshot 45 delle 14:25: unico tentativo amministrativo con password volutamente errata rifiutato da QTS; messaggio generico di credenziali errate o account non valido, senza blocco visibile. Prova privata copiata
- [x] Cercare nel file del collettore la riga web `Login Fail` delle 14:25, verificarne cinque campi e differenza fra ora NAS e ricezione
- [x] `Login Fail` web amministrativo di INTRA3 ricevuto alle 14:25:05.678072 con ora NAS 14:25:05, cinque campi e differenza 0,678072 s; con il `Login OK` delle 14:05 il collaudo punto 3 è superato
- [x] `chronyc tracking` sul collettore: riferimento `ntp2.inrim.it`, `System time` +0,000443351 s, `Last offset` +0,000479445 s, `Leap status: Normal`; con i due confronti degli eventi sotto un secondo il punto 7 di INTRA3 è superato
- [ ] Verificare separatamente il contatto effettivo del NAS con `ntp1.inrim.it`: la configurazione QTS e il confronto degli orari non mostrano direttamente una risposta NTP

## Feature: componente 4, iLO 5 via Remote Syslog

Stato: lettore IEL, test e unità systemd versionati nel commit `30b4c1c`, ma non installati. Il 2026-10-07 il collettore ha negoziato TLS 1.3 con l'iLO fisico sulla porta 443 senza verificarne la catena del certificato. L'utente ha recuperato la credenziale ed è entrato nella GUI; gli screenshot privati 102-104 mostrano ProLiant DL380 Gen10, iLO 5 3.09, **licenza iLO Advanced** e pagina Remote Syslog inizialmente disabilitata. La funzione è stata abilitata verso UDP 514 del collettore: nel file giornaliero della sorgente sono arrivate una riga di modifica e due righe di test. I primi test mostravano iLO indietro di circa 4 minuti e 34 secondi. Dopo aver configurato SNTP con i server INRIM e fuso di Roma, l'operatore ha letto tre eventi di sincronizzazione nel file del collettore; gli scarti rispetto alla ricezione sono 0,063083, 0,323815 e 0,283542 secondi. La scelta originaria Redfish si basava sull'indicazione errata che Advanced fosse assente. La Security Dashboard mostra stato Risk per RBSU senza login, Secure Boot disabilitato, complessità password disabilitata, SNMPv1 abilitato e certificato predefinito; questi rilievi sono riportati anche a `D:/network-design`. L'archivio KeePassXC che la sua documentazione dichiarava attivo non esiste e la rettifica è stata propagata.

Cosa fa ora: Remote Syslog invia le nuove voci al ricevente del collettore nel formato `AdsLine`. Due login web riusciti e un fallimento controllato sono stati ricevuti prima dello smistamento; il punto 3 è superato, con account tentato assente dal messaggio di fallimento. Tre eventi NTP sotto un secondo e `chronyc tracking` normale superano il punto 7. UDP non offre ritrasmissione. Il timer `ads-ilo.py` resta alternativo e non installato. Dal 08/10 il filtro rsyslog iLO è installato: gli eventi tecnici sono indirizzati a `/var/log/ads-ilo-other/<IP_ILO>/`, gli accessi riconosciuti a `/srv/ads/<IP_ILO>/`. Dopo il cambio, il test tecnico è stato ricevuto nel nuovo file con permessi verificati; nel file AdS sono stati letti login Browser fallito, login riuscito e logout, mentre il test tecnico vi compare zero volte. La ritenzione tecnica di 90 giorni è in esercizio: timer `enabled`/`active`, prossimo giro 09/10 alle 03:00 CEST; il service è stato avviato una volta sotto systemd con `status=ok`, zero eliminati e filesystem al 44%. Restano gli altri canali iLO, la perdita possibile su UDP e un allarme esterno per la capienza. Procedura e limiti in `docs/runbook-componente-4-ilo.md`.

Ricognizione per lo smistamento: il file reale del 07/10 contiene, al momento della lettura, 38 righe ripartite per primo token del messaggio in 24 `iLO5`, 8 `Network`, 5 `SecurityConfiguration` e 1 `DenialofService`. Fra gli 11 testi distinti `iLO5` sono stati osservati i tre prefissi Browser di accesso e otto testi tecnici, di sicurezza o di configurazione. La nuova regola usa l'IP privato della sorgente e prefissi di accesso espliciti; conserva tutti gli altri messaggi in `/var/log/ads-ilo-other/` per revisione. La prova locale WSL con rsyslog 8.2312 ha scritto due accessi e due messaggi tecnici nei file attesi. La prima prova Debian 13 ha trovato e fatto correggere la condizione vuota non valida; la seconda è passata con rsyslog 8.2504: tre accessi nel file AdS, tre eventi tecnici o ignoti nel file distinto.

Definition of done:

- [x] Lettore Redfish, unità e prove locali preparati; non installati
- [x] Licenza Advanced, modello e firmware letti sulla GUI; pagina Remote Syslog osservata disabilitata con porta 514
- [x] Destinazione Remote Syslog salvata; modifica di configurazione e due messaggi di test ricevuti nella cartella dell'iLO sul collettore
- [x] Dopo i due reset del solo controller iLO, tre eventi periodici di sincronizzazione sono arrivati sul collettore con differenza fra ora dichiarata e ricezione inferiore a un secondo
- [x] `chronyc tracking` del 07/10/2026: riferimento `ntp2.inrim.it`, stratum 2, `System time` +0,000148728 s, `Last offset` +0,000056946 s, `Leap status: Normal`; con i tre eventi NTP iLO sotto un secondo, collaudo punto 7 superato. La ricerca mirata dell’eventuale test dopo il secondo reset resta facoltativa.
- [x] Screenshot 110: `Authentication Failure Logging` è `Enabled - Every 3rd Failure`, ritardo 10 secondi dopo la soglia; un solo errore può non comparire nei log
- [x] `Account Service settings have been saved.` dopo la modifica a `Enabled - Every Failure`; modifica registrata nel Syslog e singolo fallimento successivo ricevuto. La persistenza del valore dopo riapertura non è stata verificata direttamente.
- [x] Ricerca nel file iLO: due `Browser login` riusciti con account e IP della postazione, più evento di modifica `AuthenticationFailureLogging`, tutti ricevuti nel formato `AdsLine`
- [x] Dopo Logout un solo tentativo con password volutamente errata è stato rifiutato dalla GUI, senza blocco visibile
- [x] Un solo login iLO volutamente errato rifiutato dalla GUI e ricevuto alle 14:43:16.550058 nel file del collettore con cinque campi `AdsLine`; scarto 0,550058 s, IP della postazione ma nessun account tentato nel messaggio. Collaudo punto 3 superato.
- [x] Ricognizione dei testi iLO reali e filtro parametrico preparato; test del renderer 15/15, prova locale rsyslog 8.2312 e test integrato Debian 13 con rsyslog 8.2504 passati
- [x] Politica di 90 giorni per `/var/log/ads-ilo-other/`, filtro installato e test tecnico della iLO fisica ricevuto nel nuovo file con permessi verificati
- [x] Accessi Browser post-cambio nel file AdS e test tecnico presente una volta nel file tecnico, zero nel file AdS
- [x] Script e unità della ritenzione di 90 giorni installati con impronte verificate e dry-run reale senza file scaduti
- [x] Timer di ritenzione `enabled` e `active`, prossimo giro 09/10/2026 alle 03:00 CEST
- [x] Service di ritenzione eseguito sotto systemd con `status=ok`, zero eliminati e timer ancora attivo
- [ ] Ricognire gli altri canali di accesso iLO e definire un allarme esterno per la capienza
- [ ] Se Remote Syslog non copre gli accessi, collaudare il lettore Redfish con account dedicato, certificato verificato e timer

## Feature: componente 5, catena locale D-1

Stato: `bin/ads-nightly.sh`, `bin/ads-verify.sh`, le unità systemd e `tests/test-nightly.sh` sono versionati nel commit `a031a4c` del 07/10/2026, ma non installati sul collettore. Il test ha superato in WSL Ubuntu la prova su due giorni, con seconda esecuzione idempotente, byte alterato nel log D-1 rilevato, mutazione del verificatore che farebbe passare il difetto, e manifest precedente alterato rilevato. Il test non usa il collettore reale.

Cosa fa: comprime i file del giorno precedente, scrive un manifest SHA-256 concatenato al precedente e verifica archivio e log originario. È lo stadio locale della sezione 5 dello studio; non costituisce ancora la prova indipendente prevista con TSA, WORM e impronta alla Direzione. Gli eventi iLO tecnici nuovi hanno una destinazione separata dal 08/10, con test di ricezione superato; i vecchi file AdS restano misti e le connessioni SMB non AdS di INTRA3 richiedono ancora trattamento prima di attivare il timer, senza cancellare le righe già raccolte. D7 richiede l'elenco AdS approvato. Il runbook è `docs/runbook-componente-5-catena.md`.

Definition of done:

- [x] Stadio locale e unità systemd preparati; prova WSL con alterazione effettiva superata
- [ ] Definire e attuare il trattamento degli eventi iLO non AdS e delle connessioni SMB non AdS; per D7 attendere l'elenco approvato
- [ ] Collaudare permessi, D-1, timer e verifica sul collettore vero, un comando autorizzato alla volta
- [ ] Integrare TSA, WORM e invio dell'impronta quando disponibili destinazioni e credenziali

## Feature: punto 3, macchine virtuali di Proxmox come sorgenti (ADR-013)

Stato: rinviata per decisione dell'utente del 2026-10-05 finché `D:/network-design` non avrà allineato tutte le VM all'impianto tecnico del pilota, M29. I log e gli allarmi tecnici restano nel flusso separato di quel progetto; solo dopo l'allineamento si riprende qui l'invio di accessi AdS e heartbeat. La priorità corrente di questo progetto è la catena locale e la separazione dei flussi.

Cosa fa: ogni VM invia al collettore, in TLS sulla 6514 con coda su disco, i propri accessi amministrativi (`sshd`, `sudo`, `su`, login grafico) e un heartbeat periodico, così che il controllo di silenzio registri anche una VM ferma. Si comincia dalla VM 204, il convertitore dei ruolini, che dal 05/10/2026 è il pilota del presidio sulle VM registrato in `D:/network-design/docs/log-collector-integrazione.md`, sezione sul monitoraggio delle macchine virtuali. Amministra le VM l'IT Manager.

Definition of done:

- [ ] elenco delle VM nel perimetro, con quali sono AdS-rilevanti e chi vi accede; il censimento delle VM e dei loro account sta in `D:/network-design`
- [ ] domanda aperta: le VM Linux si amministrano con un account locale condiviso, lo stesso nome su quattro macchine, quindi il collettore registrerebbe la postazione e non la persona; stesso problema di ADR-008 per firewall, HERO e Proxmox
- [ ] VM 204: configurazione rsyslog di invio, template in `config/`, prova in contenitore, installazione e collaudi punti 3 e 7, runbook dedicato
- [x] contesto, 2026-10-05: la VM 204 ha watchdog collaudato e presidi interni, e la postazione la sorveglia da fuori con notifiche di Windows sui cambi di stato; strumenti in `D:/network-design` (`scripts/vm-health/`, `scripts/Watch-VmHealth.ps1`), fonte unica per i progetti, ed estensione alle altre VM nel suo micro-step M29. È un controllo provvisorio della postazione, non sostituisce il controllo di silenzio qui sotto
- [ ] heartbeat delle sorgenti Linux (D6): forma del messaggio, cadenza e come `ads-silence.sh` lo riconosce
- [ ] `ads-silence.sh` anticipato e cadenza rivalutata rispetto al controllo notturno dell'handoff
- [ ] relay SMTP scelto (bloccante già noto: `smtp_relay`, `mail_direzione`); condiviso con gli allarmi tecnici delle VM, che però non passano dal collettore
- [ ] la VM 210 stessa: stesso profilo di rischio della VM 204 (2 GB con desktop, ADR-012); un blocco del collettore apre un buco nella prova per le sorgenti UDP, quindi watchdog e memoria della VM 210 vanno decisi con lo stesso criterio applicato alla 204 in `D:/network-design`

## Riconciliazione

Al 07/10/2026 il perimetro NAS dichiarato dall'IT Manager include anche l'accesso amministrativo QTS dei PM su HERO e INTRA2, oltre ai permessi completi su file specifici; la sottocartella amministrativa di INTRA2 è dichiarata limitata a due persone. La mappatura reale è privata nel progetto di rete. Per D7 restano da verificare account, gruppi QTS, ACL e l'ambito effettivo della GUI; senza nomina individuale e elenco approvato non si installa un filtro per account. `D:/network-design` ha registrato l'avanzamento parziale ISO-30 e la regola per allineare a ogni avanzamento l'HTML di progetto e la copia sul Desktop.

L'08/10/2026 l'IT Manager ha deciso 90 giorni di ritenzione locale per gli eventi iLO tecnici. Script `bin/ads-ilo-other-retain.sh` e unità systemd preparati, con rotazione già prodotta dai nomi giornalieri, permessi `root:root` per il secondo flusso e avviso nel journal se il filesystem raggiunge l'80%. Prova WSL su soglia e separazione dall'albero AdS passata. Nulla è installato sul collettore: restano verifica dei canali iLO non Browser, backup/rollback, installazione controllata e collaudo. La scelta va propagata all'integrazione e a ISO-30 in `D:/network-design` con le copie HTML.

Preflight della VM reale il 08/10: rsyslog `active`, configurazione corrente `root:root 0644`, directory del flusso tecnico assente; `/var/log` è sul filesystem `/dev/sda2`, occupato al 44%, con 8.590.400 KiB disponibili. Il dato non proietta la ritenzione di 90 giorni. La candidata locale privata è stata generata in 14 file; il suo rsyslog ha SHA-256 registrato nel runbook, due marker del filtro e nessun segnaposto residuo. Il secondo controllo reale non ha trovato `AdsIloOtherFile` nel file attivo, il cui SHA-256 è `6d2f7913d17ea68db7be5e86de03f17d3347f51ed14f6f2c0e9e0892ae688329`: baseline per il backup. Preflight, politica e prove locali sono stati propagati a `D:/network-design`; ISO-30 resta `in_corso`, con HTML e copie allineati.

## Feature: copertura dell'intero inventario di rete (ADR-015)

Stato: matrice documentale iniziale del 08/10/2026, **57/57 nodi topologici classificati**, nessuna nuova sorgente installata. L'utente ha incluso esplicitamente anche apparati del fornitore, telefoni, stampanti e OT; `docs/matrice-sorgenti-rete.md` distingue i casi senza evento autonomo, quelli da ricognire e quelli già collaudati. Le due multifunzione sono state aggiunte individualmente alla revisione 14 della mappa: Kyocera Piano Terra sulla porta 6 del 30HP, Canon Piano 1 senza arco fisico finché la porta non è verificata. Il controllo `tools/verifica-copertura-rete.py` segnala nuovi nodi non classificati. Lo snapshot Proxmox del mattino contiene 11 VM e amplia il nodo aggregato della topologia. Fuori dalla topologia sono censite le console cloud Nebula, NinjaOne, M365 e GravityZone. Il campione storico Nebula dei due switch ha 18.753 eventi tecnici senza messaggi di login; la specifica pubblicata non mostra un'API dei login NCC, mentre la GUI documenta export CSV/XML del registro delle modifiche. Il repository `telegram-notifications` legge alert attivi NinjaOne, non accessi AdS, e non è un componente da installare sul collettore per questa raccolta. Sul collettore il backup rsyslog è verificato e la candidata iLO è stata trasferita e validata; resta installazione e collaudo reale, poi ricognizione delle altre sorgenti dopo i rispettivi gate.

Le cinque schede con `covers-paths` sono state riconciliate con il commit `a031a4c`: descrivono gli script e il test della catena D-1 versionati. Il codice Redfish iLO ha superato le prove locali ma non è installato; Remote Syslog del dispositivo reale ha superato i punti 3 e 7. Anche INTRA3 ha superato i punti 3 e 7. La connessione dalla postazione non AdS è stata provata con elenco della radice e lettura di un byte; 71 `Login Fail` del giorno restano da attribuire. D7 è bloccato perché non esistono ancora nomina formale firmata né elenco AdS approvato. La catena locale D-1 ha superato la prova in WSL; prima dell'installazione restano lo smistamento dei flussi e il collaudo sulla VM.
