# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario. Vale per la branch dichiarata qui sotto e non per il progetto: se il progetto usa più alberi di lavoro e questa non è la branch più avanti, la memoria valida è quella dell'albero autorevole indicato (norma `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`).

## Stato

```
Branch attivo:        main
Commit di riferimento: 8d834dd
Data snapshot:        2026-10-06
Albero autorevole:    unico
Remoto:               git@github-corp:asopranzi-intrawelt/log-collector.git (primo push di 9ee87b4 il 2026-09-30)
Template:             E:\template-claude-developing @ d732a25
```

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | 8d834dd | componenti 1 e 2 e sorgente Proxmox descritti dal codice |
| design-and-security.md | 8d834dd | confini di fiducia e rischi residui descritti dal codice |
| deployment.md | 8d834dd | ambienti osservati; gate separazione-ambienti ancora aperto |
| dev-testing.md | 8d834dd | quattro livelli di prova, 44 pytest passati e 22 Bats censiti |
| current-work.md | 8d834dd | priorità: NAS INTRA3; VM come sorgenti rinviate dopo M29 (ADR-013) |
| roadmap.md | 9ee87b4 | solo struttura |

## Punto di ripresa

Al 2026-10-02 i componenti 1 e 2 sono installati e verificati sul collettore vero, e l'host Proxmox invia al collettore i propri accessi: collaudo punto 3 superato per l'host (login web e SSH, riusciti e falliti, con i cinque campi). Procedure ed esiti nei tre runbook di `docs/`. Il 2026-10-02 il firewall USG FLEX è completo come sorgente (collaudi punti 3 e 7 superati, runbook `docs/runbook-componente-3-firewall.md`); dei NAS QNAP sono completi come sorgenti HERO e INTRA2 (TLS sulla 6514) e INTRA (TS-410U, solo UDP sulla 514, rischio residuo fino alla sostituzione del 2027), tutti con NTP su INRIM e collaudi punti 3 e 7 superati, runbook `docs/runbook-componente-3-nas.md`; aperta la decisione sulle righe SMB periodiche dell'account `backup` di Proxmox su INTRA; resta INTRA3 (TS-210, nel perimetro), da leggere sul dispositivo. Rinviati: filtro D7 del QNAP (elenco AdS bloccante), prova negativa del collaudo punto 2. Decisioni aperte: memoria della VM (ADR-012), custode della prova e analisi (ADR-010), Wazuh (ADR-009). Portato in network-design il 2026-10-02 (ADR-004) tutto quanto fatto fino ad allora: VM 210, regole del collettore, host Proxmox e firewall come sorgenti, modifiche agli apparati, fatti emersi. Da portare ancora: NAS quando configurati, con la correzione dell'inventario (INTRA2 è un TS-435XeU con QTS 5.2.9, non un TS-451U), la lentezza dell'interfaccia di INTRA2 con le misure del 02/10 per NAS-003 (diagnosi fermata qui per restare sullo scopo), l'accesso HTTP in chiaro e il firmware non aggiornato di INTRA2, nome DNS quando registrato, alias SSH Windows quando aggiunto, decisione sul backup della VM 210.

Il 2026-10-05, da una sessione dedicata alla VM 204 (bloccata dal 12/09 senza che nessuno se ne accorgesse), l'utente ha deciso ADR-013: le macchine virtuali di Proxmox entrano fra le sorgenti, a partire dalla VM 204, con accessi e heartbeat; il controllo di silenzio diventa anche il controllo di disponibilità delle VM e va anticipato; gli allarmi tecnici restano fuori dal collettore e condividono solo il relay SMTP, che diventa più urgente. Feature aperta in `current-work.md`; la parte tecnica è registrata in `D:/network-design` (#205-#207). Da valutare anche per la VM 210 watchdog e memoria, con lo stesso criterio.

Precisazione del 2026-10-05: prima si allineano tutte le VM all'impianto tecnico del pilota in `D:/network-design` (M29), poi si attivano qui come sorgenti AdS con accessi e heartbeat, mantenendo separati i log e gli allarmi tecnici. La priorità corrente torna al NAS INTRA3. L'utente raggiunge la sua interfaccia web; restano da leggere log locali, uso effettivo, possibilità di invio syslog e sincronizzazione dell'ora. L'inventario di `network-design` lo dichiara vuoto e dismesso nel 2025, in contrasto con l'uso descritto nel runbook: decide la verifica sul dispositivo, non il solo accesso alla pagina.

Lo screenshot 13 del 2026-10-05 verifica su INTRA3 modello TS-210, firmware 4.2.6 build 20240618, 249 MB di memoria e fuso di Roma; l'utente dichiara che soltanto i due amministratori interni usano le condivisioni come unità di rete. I fatti sono stati riportati in `D:/network-design` nello stesso giro, correggendo le voci che lo indicavano vuoto e dismesso; numero di serie e indirizzo restano nel livello privato. NTP non è stato ancora verificato.

Lo screenshot 21 del 2026-10-06 mostra su INTRA3 `System Connection Logs` vuoto con pulsante `Start Logging`: la registrazione è spenta; la scheda `Syslog Client Management` esiste ma non è stata aperta. Nessuna impostazione è stata modificata. Senza log di connessione non si possono verificare l'uso effettivo delle condivisioni né la necessità di D7.

Lo screenshot 22 dello stesso giorno mostra in `Options` HTTP, SSH, FTP e Telnet selezionati; SMB, iSCSI, AFP, RADIUS, VPN e archiviazione automatica a 10.000 voci non selezionati. Non è stato premuto `Apply` né avviata la registrazione. Con queste selezioni SMB non sarebbe registrato, quindi l'uso delle condivisioni resta non misurabile.

Lo screenshot 27 mostra `Syslog Client Management` con invio remoto spento, server vuoto e campo UDP 514 disabilitato. Il log degli eventi è selezionato ma inattivo; quello delle connessioni è inattivo e non selezionato finché non si avvia la registrazione locale. Non è stato premuto `Apply All`.

Lo screenshot 28 mostra sulla pagina `Time` la sincronizzazione automatica con `pool.ntp.org` ogni 7 giorni e il fuso di Roma. Non dimostra il successo dell'ultima sincronizzazione né lo scarto dell'orologio; la configurazione è diversa da D5, applicata alle altre sorgenti con INRIM ogni ora. Non è stato premuto alcun comando di modifica o sincronizzazione.

Lo screenshot 29 mostra l'adeguamento automatico all'ora legale attivo, offset di 60 minuti e periodo 29/03/2026 02:00 - 25/10/2026 03:00; la tabella personalizzata è disattivata. La ricognizione in sola lettura è completa. Il 2026-10-06 l'utente ha autorizzato a configurare INTRA3 come gli altri NAS, un'azione alla volta. Lo screenshot 30, fornito dopo `Apply`, mostra `ntp1.inrim.it` ogni ora nella pagina `Time`, senza errore visibile; il successo della sincronizzazione e lo scarto restano da verificare. Secondo intervento consegnato: opzioni HTTP, SSH, Telnet e SMB, FTP spento, archiviazione automatica spenta; attendere riscontro prima di avviare i log locali. Seguono lettura delle prime righe, invio remoto e collaudi; accessi effettivi e filtro D7 richiedono log reali.

L'utente riferisce di aver applicato correttamente le opzioni HTTP, SSH, Telnet e SMB con FTP spento, senza fornire una schermata. È stato quindi consegnato il passo `Start Logging`; si attende conferma che il pulsante diventi `Stop Logging` o il testo dell'eventuale errore. La persistenza delle opzioni e la produzione delle prime righe restano da verificare sul dispositivo.

L'utente conferma che dopo `Start Logging` il pulsante è diventato `Stop Logging`: registrazione locale attiva. È stata richiesta una schermata della tabella aggiornata, anche vuota, prima di configurare l'invio syslog. La produzione delle righe e la copertura SMB restano da verificare.

Lo screenshot 32 mostra `Stop Logging`, 326 righe totali e operazioni `SAMBA` sui file (`Write`, `Add`, `Delete`, `Read`, `MakeDir`), con account, postazione e risorsa. La copertura SMB è verificata; volume giornaliero, uso da parte di eventuali non AdS e scarto temporale restano da misurare. È stata richiesta la schermata di `Syslog Client Management` dopo l'avvio dei log locali, prima di attivare l'invio remoto.

Lo screenshot 35 di `Syslog Client Management` mostra il client ancora spento dopo l'avvio dei log locali; server, porta e caselle sono disabilitati. È stato consegnato il passo di spuntare solo `Enable Syslog` e vedere quali campi si attivano, senza compilare né applicare.

Lo screenshot 36 mostra che spuntando `Enable Syslog` si attivano server, UDP 514 e casella `System Connection Logs`; `System Event Logs` resta selezionato. Il modulo non è ancora stato applicato. È stata consegnata la compilazione del server privato del collettore e di entrambe le categorie, con schermata di verifica prima di `Apply All`.

Lo screenshot 37 ha mostrato server e UDP 514 corretti ma la casella delle connessioni ancora non selezionata. Nello screenshot 38 entrambe le categorie sono selezionate con server e porta corretti; è stato consegnato `Apply All` e chiesto di riaprire la scheda per verificare la persistenza. L'invio e la ricezione sul collettore non sono ancora confermati.

L'utente riferisce che dopo `Apply All` è comparso `Changes applied` e che alla riapertura della scheda i valori erano gli stessi. La configurazione remota risulta applicata secondo l'operatore; la consegna delle righe al collettore resta da verificare. È stato consegnato un comando PowerShell di sola lettura via SSH per elencare i file recenti sotto `/srv/ads/` e individuare la cartella di INTRA3.

L'output del comando `find` eseguito dall'utente mostra un file aggiornato negli ultimi dieci minuti nella cartella del collettore corrispondente a INTRA3. È stata consegnata la lettura delle ultime cinque righe per verificare che contengano i log attesi e confrontare gli orari; nessun comando è stato eseguito dall'agente su host reali.

Le ultime righe lette dall'utente sul collettore sono tre `SAMBA Login Fail` di `NAS-INTRA3/qlogd`, ripetuti in circa due secondi da una postazione e un account non ancora classificati rispetto ai due AdS dichiarati. I cinque campi sono presenti e l'ora del NAS differisce meno di un secondo dalla ricezione in questi esempi. La consegna syslog è verificata; NTP effettivo, accessi amministrativi riusciti e D7 restano da verificare. È stato chiesto all'utente di identificare la postazione prima di decidere il trattamento dei log SMB.

L'utente ha classificato la postazione dei tre `SAMBA Login Fail` come non AdS e ha precisato che deve continuare ad accedere alla condivisione di INTRA3. Ha chiesto di conservare anche i log di questi accessi, separati da quelli AdS (ADR-014); la precedente proposta di disattivare SMB è stata ritirata e SMB è rimasto selezionato. Lo studio e il runbook NAS registrano la decisione. D7 richiede ancora l'elenco AdS approvato, una destinazione e una politica per il flusso ordinario; le righe non AdS già scritte in `/srv/ads/` sono una contaminazione da trattare senza cancellazioni implicite. La sessione interrotta aveva lasciato questa decisione fuori dall'indice e dal work-log: la ripresa del 2026-10-06 li riallinea conservando i nove file modificati.

Priorità immediata indicata dall'utente: ripristinare dalla postazione Windows non AdS l'unità di rete di INTRA3. I tre errori SMB dal collettore dimostrano un tentativo fallito, non ne identificano la causa. Il primo passo è leggere sul client la mappatura e il messaggio di errore senza cambiare credenziali, permessi o configurazione del NAS; il ripristino sarà verificato aprendo la condivisione e leggendo un file già esistente dalla postazione, con riscontro del relativo accesso nel log. Nessun intervento sul client è ancora eseguito o confermato.

Lo `screenshot_41.png` ricevuto dopo il crash mostra che l'operatore ha ricreato la mappatura persistente `B:` verso INTRA3 in una PowerShell elevata: `net use` ha avuto successo e `Get-SmbMapping` indica `OK`. Resta da provare che `B:` sia accessibile da Esplora file nella sessione ordinaria e che si possa leggere un file. La schermata contiene una password in chiaro, quindi non è stata copiata nelle evidenze del progetto; la credenziale deve essere cambiata. È stata chiesta la sola verifica in Esplora file, senza altri interventi.

Su richiesta dell'utente, la verifica è stata fatta nella PowerShell ordinaria della stessa postazione: `Get-ChildItem` sulla radice `B:` risponde che l'unità non esiste. La mappatura riuscita nel terminale amministrativo non è visibile nella sessione ordinaria. Il prossimo passo è crearla lì con password richiesta interattivamente e controllare l'accesso ai file. La password apparsa nello screenshot 41 va cambiata dopo il ripristino, senza reinserirla in una riga di comando.

Correzione immediata: l'utente ha ripetuto lo stesso comando in una PowerShell «Utente connesso» a 64 bit e ha ottenuto `ACCESSO_OK`, senza eseguire il nuovo `net use` proposto. È provata la possibilità di elencare `B:` in questa sessione, mentre resta ignota la differenza di contesto rispetto alla sessione che non vedeva l'unità. La precedente attribuzione del difetto alla sola elevazione non è dimostrata. Prossimo passo: leggere senza mostrarne il contenuto un byte di un file già esistente e non vuoto, poi cercare un evento coerente nei log del NAS. Resta necessaria la rotazione della password apparsa nello screenshot 41.

Il primo tentativo di lettura ha usato un percorso dell'archivio che potrebbe essere una cartella e ha restituito «Accesso al percorso negato». `Get-Content` su una cartella non prova un problema di permessi ai file. È stata consegnata una verifica del tipo del percorso con `Get-Item` nella medesima PowerShell, prima di scegliere un file per la prova. Nessuna modifica al NAS o alla mappatura è stata richiesta.

`Get-Item` ha restituito `CARTELLA`: il percorso del primo test non era un file. È stata consegnata una prova che seleziona un file immediato non vuoto nella stessa cartella e ne legge un byte senza mostrarne nome o contenuto. Resta da riceverne l'esito; nessun problema di permessi SMB è dimostrato dal precedente errore di `Get-Content`.

La prova successiva ha restituito `LETTURA_OK`: `B:` è accessibile e un file esistente è leggibile nella sessione PowerShell «Utente connesso» a 64 bit della postazione non AdS. Il ripristino della connessione è verificato per la sessione corrente. Restano da vedere un evento coerente nel log del NAS e la riconnessione dopo un nuovo accesso a Windows. La password visibile nello screenshot 41 va cambiata; è stata chiesta all'utente l'estensione d'uso dell'account prima della rotazione.

L'utente ha chiesto di continuare il collaudo e di occuparsi separatamente della credenziale e della sessione SMB; non risulta un cambio di password eseguito. È stato consegnato un comando di sola lettura dalla postazione amministrativa verso il collettore per cercare le ultime righe di INTRA3 riferite alla postazione non AdS e verificare un'azione riuscita dopo la prova `LETTURA_OK`. L'esito è in attesa.

L'output del collettore mostra, nelle ultime dieci righe del giorno filtrate sulla postazione non AdS, solo `SAMBA Login Fail` fra le 12:33:38 e le 12:36:08, con `Users: User`. La prova `LETTURA_OK` sul client rimane valida, ma il campione non contiene un evento riuscito e non spiega i tentativi falliti. È stato consegnato un conteggio per `Action` di tutte le righe del giorno per la medesima postazione, senza mostrare nomi o risorse, prima di attribuire una causa o dichiarare completo il collaudo dei log.

Il conteggio sul file giornaliero intero, filtrato sulla postazione non AdS, ha prodotto 71 `Login Fail`, 2 `Login OK` e 1 `Read` (74 righe). La registrazione di accessi riusciti e di una lettura è verificata per quella postazione; l'associazione temporale con la prova `LETTURA_OK` e la causa dei fallimenti restano aperte. È stata consegnata una query che stampa solo ora di ricezione e `Action` delle tre righe riuscite.

Le due righe `Login OK` sono ricevute alle 12:11:40.114724 e 12:24:15.900765, la riga `Read` alle 12:33:28.267900 del 2026-10-06. La lettura è coerente con il test `LETTURA_OK`, senza associazione certa perché il test non ha registrato un proprio orario. Le ultime righe `Login Fail` iniziano alle 12:33:38 e continuano fino alle 12:36:08: i fallimenti della stessa postazione restano un'anomalia distinta dall'accesso a `B:` che funziona nella sessione provata. La priorità del componente torna al collaudo controllato di login AdS riuscito e fallito su INTRA3, poi al confronto dell'ora dichiarata con quella di ricezione; D7 è bloccato dall'elenco AdS approvato.

Primo passo del collaudo amministrativo consegnato: dalla postazione amministrativa aprire la pagina di login web di INTRA3, uscendo dalla sessione QTS se aperta, e confermare che il modulo di accesso sia visibile. Nessun tentativo di login è stato ancora richiesto in questo giro.

L'utente conferma la pagina di login di INTRA3 visibile. È stato chiesto un solo login amministrativo riuscito con le credenziali già in uso, senza comunicarle, e il riscontro del pannello aperto con ora locale approssimativa. L'esito e la riga sul collettore sono in attesa; il tentativo fallito è un passo successivo distinto.

L'utente riferisce un login amministrativo riuscito su INTRA3 alle 14:05 del 2026-10-06, con pannello QTS aperto e orologio del NAS a 14:05. La riga nel file del collettore non è ancora stata letta: consegnata una query sulle ultime `Action: Login OK` del giorno per verificarne contenuto e orari. Il login fallito controllato segue separatamente.

La riga del login amministrativo web di INTRA3 è stata letta nel file del collettore: ricevuta alle 14:05:33.736335, ora dichiarata 14:05:33, differenza osservata 0,736335 secondi. Porta i cinque campi `AdsLine`, account amministrativo, postazione, tipo `HTTP`, risorsa `Administration` ed esito `Login OK`. La metà riuscita del collaudo punto 3 è verificata; il tentativo fallito è ancora aperto. La soglia temporale è soddisfatta per questa riga, mentre il contatto NTP effettivo e `chronyc tracking` del collettore restano da verificare per chiudere il punto 7. È stato chiesto all'utente di uscire dalla sessione QTS e confermare la pagina di login prima del tentativo fallito.

L'utente conferma di trovarsi di nuovo alla pagina di login di INTRA3. È stato consegnato un solo tentativo con l'account amministrativo e una password intenzionalmente errata, senza comunicarla; attendere messaggio e ora approssimativa, poi leggere il file del collettore. Nessun esito del tentativo fallito è ancora disponibile.

Lo screenshot 45 delle 14:25 mostra il login amministrativo rifiutato da QTS dopo l'unico tentativo con password volutamente errata; il messaggio è «Your login credentials are incorrect or your account is no longer valid», senza avviso di blocco. Il campo password è vuoto nella schermata. La prova privata è conservata sotto `_notes/evidenze/`; il caso sul dispositivo è verificato, mentre la riga nel file del collettore è ancora da leggere. È stato consegnato un comando SSH di sola lettura che filtra `Connection type: HTTP` e `Action: Login Fail`.

Il `Login Fail` web amministrativo di INTRA3 è nel file del collettore alle 14:25:05.678072, con ora NAS 14:25:05 e differenza osservata 0,678072 secondi. Account, postazione, tipo `HTTP`, risorsa `Administration`, esito e i cinque campi `AdsLine` sono presenti. Con il `Login OK` delle 14:05:33 il collaudo punto 3 è superato per INTRA3. Per chiudere il punto 7, i due confronti temporali sono sotto un secondo ma resta da leggere `chronyc tracking` sul collettore; il contatto NTP del NAS con INRIM non è provato direttamente. È stato consegnato il comando di sola lettura dalla postazione amministrativa.

L'utente ha letto `chronyc tracking` sul collettore il 2026-10-06: riferimento `ntp2.inrim.it`, stratum 2, tempo di sistema 0,000443351 secondi avanti rispetto a NTP, ultimo offset +0,000479445 secondi, stato `Normal`. I due eventi amministrativi noti di INTRA3 differiscono dalla ricezione di 0,736335 e 0,678072 secondi; il criterio operativo del punto 7 è soddisfatto insieme al punto 3 già superato. Questi timestamp includono il tempo di consegna del log e non provano il contatto diretto del NAS con `ntp1.inrim.it`, configurato in QTS ogni ora. Prossimi lavori distinti: prova diretta del contatto NTP se disponibile, separazione D7 dei log ordinari da quelli AdS dopo l'elenco approvato, e diagnosi dei tentativi SMB falliti della postazione non AdS.
