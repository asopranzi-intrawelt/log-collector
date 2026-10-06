# Runbook del punto 3: i NAS QNAP come sorgente

> Procedura eseguita dal 2026-10-02 sui NAS QNAP, uno per sezione, con impostazioni, esiti e significato, scritta per essere letta anche da chi non ha partecipato e per servire da fonte a un documento per un cliente. Riferimenti: sezione 2 dello studio (matrice dei cinque campi), decisioni D5 (NTP su INRIM) e D7 (filtro delle righe non AdS del NAS), sezione 6 dell'handoff (collaudi punti 3 e 7). I valori reali non compaiono: stanno in `config/parametri.yaml`.

## I quattro NAS

L'inventario del progetto `D:/network-design` elenca quattro NAS QNAP, amministrati dall'IT Manager e senza versione di firmware censita, che quindi si legge sul dispositivo. HERO è il NAS di produzione con l'archivio dei progetti. INTRA2 riceve i backup di HERO e delle postazioni. INTRA riceve il dump delle VM Proxmox. INTRA3 è un NAS vecchio in RAID 1, usato come appoggio e collegato come unità di rete per i soli due amministratori non MSP, con esportazioni statiche di posta: è nel perimetro, perché contiene dati personali e ha un accesso amministrativo.

## HERO

Modello TS-h1677XU-RP, firmware QuTS hero h5.2.10.3577 build 20260731, letti il 2026-10-02 in `Pannello di controllo > Sistema > Stato del sistema`. L'interfaccia si usa con l'account generico `admin`.

Prima di configurare l'invio si sono letti i log locali in `QuLog Center > Dispositivo locale`. Il log di accesso conteneva 54 voci dal 2026-09-01, tutte accessi amministrativi all'interfaccia (`HTTPS`, risorsa `Administration`) dalle due postazioni degli amministratori: le connessioni degli utenti alle cartelle condivise oggi non vengono registrate, quindi il problema della decisione D7 su HERO non si pone. Se un giorno si attivasse la registrazione delle connessioni SMB, il log di accesso porterebbe dati di dipendenti non amministratori e andrebbe applicato il filtro. Il log degli eventi conteneva circa 18.000 voci, per lo più snapshot pianificate e operazioni di sistema, fra cui le modifiche di configurazione, per un centinaio di righe al giorno.

Configurazione, in `QuLog Center > Servizio QuLog > Mittente log > Invia al server Syslog`: una destinazione verso il collettore, porta 6514, protocollo TLS, tipo di log `Log eventi e accessi`, formato RFC-3164, e l'interruttore generale `Invia log al server syslog remoto` acceso. HERO invia quindi cifrato, come l'host Proxmox; si inviano entrambi i log, come per il firewall, perché gli accessi sono il requisito e le operazioni sull'apparato servono alla verifica annuale dell'operato degli amministratori.

Che cosa arriva sul collettore, nella cartella con l'indirizzo di HERO e con il sistema `NAS-HERO`:

| Evento | Riga |
|---|---|
| login riuscito | `conn log: Users: <account>, Source IP: <postazione>, ..., Connection type: HTTPS, Accessed resources: Administration, Action: Login Success` |
| login fallito | `conn log: ... Action: Login Fail`, e nel log eventi `Category: Login and Security, Content: [Users] Failed to log in via user account "<account>". Source IP address: <postazione>.` |
| logout | `conn log: ... Action: Logout` |

Ogni riga porta utente, postazione, tipo di connessione, risorsa ed esito: i cinque campi ci sono. Collaudo punto 3 superato per HERO il 2026-10-02.

Ora. Le prime righe avevano uno scarto costante di 4-5 secondi fra ora dichiarata e ora di ricezione. In `Pannello di controllo > Sistema > Impostazioni generali > Ora` il NAS si sincronizzava con `pool.ntp.org` una volta al giorno, e fra due sincronizzazioni l'orologio derivava. Correzione: server `ntp1.inrim.it`, come prevede la decisione D5 e come collettore e firewall, verificato con `Test connessione` (esito `Riuscita`); intervallo di sincronizzazione 1 ora; fuso `(GMT+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna`, equivalente al precedente e coerente con il firewall. Dopo la correzione un login è ricevuto alle 15:24:17.17 e dichiarato alle 15:24:17: scarto entro il secondo, collaudo punto 7 superato per HERO.

## INTRA2

Modello TS-435XeU con 4 GB di RAM, firmware QTS 5.2.9.3451 build 20260327, letti il 2026-10-02 in `Pannello di controllo > Sistema > Stato del sistema`; il NAS ha sostituito pochi mesi fa un modello precedente guastato, quindi l'inventario di `D:/network-design` va corretto. Il 2026-10-02 il NAS segnalava aggiornamenti del firmware disponibili, non applicati in questo lavoro. L'interfaccia si usa con l'account generico `admin`, e in HTTP invece che in HTTPS: la password dell'amministratore viaggia in chiaro sulla rete a ogni accesso al pannello, rilievo portato in network-design.

Il log di accesso locale, letto in `QuLog Center > Dispositivo locale > Log accessi`, conteneva 34 voci, tutte accessi amministrativi di `admin` alla risorsa `Administration`, e nessuna connessione di utenti ordinari alle cartelle: come su HERO, il problema della decisione D7 oggi non si pone.

Configurazione dell'invio, in `QuLog Center > Servizio QuLog > Mittente log > Invia al server Syslog`, identica a HERO: una destinazione verso il collettore, porta 6514, protocollo TLS, formato RFC-3164, tipo di log `Log eventi e accessi`, interruttore generale `Invia log al server syslog remoto` acceso.

Ora, in `Pannello di controllo > Sistema > Impostazioni generali > Ora`, impostata subito come su HERO: sincronizzazione automatica con `ntp1.inrim.it`, verificata con `Test connessione` (esito `Riuscita`), intervallo 1 ora, fuso `(GMT+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna`.

Che cosa arriva sul collettore, nella cartella con l'indirizzo di INTRA2 e con il sistema `NAS-INTRA2`:

| Evento | Riga |
|---|---|
| login riuscito | `conn log: Users: <account>, Source IP: <postazione>, ..., Connection type: HTTP, Accessed resources: Administration, Action: Login Success` |
| login fallito | `conn log: ... Action: Login Fail`, e nel log eventi `Category: Login and Security, Content: [Users] Failed to log in via user account "<account>". Source IP address: <postazione>.` |
| logout | `conn log: ... Action: Logout` |
| modifica di configurazione | `event log: Users: <account>, Source IP: <postazione>, ..., Application: General Settings, Category: Date & Time, Content: [General Settings] Modified date/time settings.` |

Ogni riga porta utente, postazione, tipo di connessione o applicazione, ed esito: i cinque campi ci sono, e arrivano anche le operazioni sull'apparato, come la modifica dell'ora appena fatta. Collaudo punto 3 superato per INTRA2 il 2026-10-02.

Le due righe scritte prima della sincronizzazione con INRIM avevano uno scarto di 3-5 secondi fra ora dichiarata e ora di ricezione, la stessa deriva osservata su HERO; dopo la sincronizzazione un login è ricevuto alle 16:05:05.02 e dichiarato alle 16:05:05, e un login fallito ricevuto alle 16:16:11.81 è dichiarato alle 16:16:11: scarto entro il secondo, collaudo punto 7 superato per INTRA2.

## INTRA

Modello TS-410U con 503 MB di memoria, firmware QTS 4.2.6 build 20240618, letti il 2026-10-02 in `Control Panel > System Status > System Information`, con 591 giorni di attività senza riavvio. È un modello vecchio, la cui sostituzione nel 2027 per la ISO 27001 è già pianificata in `D:/network-design`. L'interfaccia, in inglese, si usa con l'account generico `admin` e in HTTP sulla 8080, come INTRA2.

QTS 4.2 non ha QuLog Center. Prima di questo lavoro la registrazione dei log di connessione era spenta (`No connection logs or logging is not enabled`): gli accessi degli amministratori al pannello non restavano registrati da nessuna parte, nemmeno in locale.

Configurazione, in `Control Panel > System > System Logs`. Nella scheda `System Connection Logs`, con `Options`, si registrano i soli tipi di connessione HTTP, SSH, Telnet e SMB (Windows), e si tolgono FTP, AFP, iSCSI, RADIUS e VPN; poi `Start Logging`. SMB si registra per scelta dell'utente, per vedere anche chi accede alle cartelle; NFS non è fra i tipi registrabili. Nella scheda `Syslog Client Management`: `Enable Syslog`, indirizzo del collettore, porta UDP 514, `System Event Logs` e `System Connection Logs`, `Apply All`.

Rischio residuo dichiarato: QTS 4.2 invia soltanto in UDP, senza TCP né TLS, quindi le righe di INTRA viaggiano in chiaro sulla LAN e una riga persa non lascia traccia né sul NAS né sul collettore. È lo stesso canale del firewall, che non sa fare di meglio; il rischio si chiude con la sostituzione del NAS prevista nel 2027, quando il modello nuovo invierà in TLS come HERO e INTRA2.

Ora, in `Control Panel > System > General Settings > Time`: sincronizzazione automatica con `ntp1.inrim.it`, intervallo 1 ora, fuso `(GMT+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna`. QTS 4.2 non offre la prova di connessione, quindi la sincronizzazione si verifica sulle righe ricevute.

Che cosa arriva sul collettore, nella cartella con l'indirizzo di INTRA e con il sistema `NAS-INTRA`, programma `qlogd`:

| Evento | Riga |
|---|---|
| login riuscito | `conn log: Users: <account>, Source IP: <postazione>, Computer name: ---, Connection type: HTTP, Accessed resources: Administration, Action: Login OK` |
| login fallito | `conn log: ... Connection type: HTTP, Accessed resources: Administration, Action: Login Fail` |
| logout | `conn log: ... Connection type: HTTP, Accessed resources: ---, Action: Logout` |
| connessione SMB | `conn log: Users: <account>, Source IP: <host>, Computer name: <nome host>, Connection type: SAMBA, Accessed resources: ---, Action: Login OK` |

Rispetto a QTS 5 il login riuscito si chiama `Login OK` invece di `Login Success`, e il login fallito arriva una volta sola, senza la riga gemella nel log degli eventi. Ogni riga porta utente, postazione, tipo di connessione ed esito: i cinque campi ci sono, collaudo punto 3 superato per INTRA il 2026-10-02. Un login fallito è dichiarato alle 17:09:37 e ricevuto alle 17:09:37.08, un login riuscito dichiarato alle 17:09:40 e ricevuto alle 17:09:40.27: scarto entro il secondo, ora legale applicata correttamente, collaudo punto 7 superato per INTRA.

Effetto della registrazione di SMB, misurato nella prima prova: l'host Proxmox, che usa INTRA come archivio dei dump, apre una connessione SMB con l'account di servizio `backup` circa ogni 10 secondi, perché controlla periodicamente lo stato dello storage. Sono circa 8.600 righe al giorno, dell'ordine di 2 MB, contro poche decine di accessi amministrativi. Non sono dati di lavoratori, ma un account di servizio, e restano utili come prova: le credenziali di `backup` sono nella configurazione di Proxmox, che l'amministratore dell'host può leggere, e un loro uso da una postazione comparirebbe proprio qui. La decisione su come trattarle è aperta: tenerle tutte, filtrarle sul collettore oppure togliere SMB sul NAS.

## INTRA3: ricognizione in corso

Il 2026-10-05 l'utente ha aperto l'interfaccia web e fornito `screenshot_13.png` della scheda `Control Panel > System Status > System Information`, conservato nel livello privato del progetto come `_notes/evidenze/NAS-INTRA3-sistema-2026-10-05.png`. La schermata mostra nome `NAS-INTRA3`, modello TS-210, 249 MB di memoria totale, firmware 4.2.6 build 20240618, attività da 13 ore e 35 minuti, fuso `(GMT+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna` e sessione dell'account generico `admin`. Il numero di serie e l'indirizzo reale restano solo nell'evidenza privata. Nessuna impostazione è stata modificata; il fuso visibile non dimostra che l'orologio sia sincronizzato via NTP.

L'utente precisa che soltanto i due amministratori interni accedono alle condivisioni di INTRA3, tramite unità di rete mappate. È una dichiarazione sul modo d'uso, da distinguere da ciò che i log locali registrano: non abbiamo ancora letto le connessioni né verificato se vi siano accessi ordinari o di account di servizio. Il runbook lo descrive come appoggio con esportazioni di posta, mentre `D:/network-design/docs/vendor-management.md` lo dichiarava vuoto e dismesso dopo la formattazione del 2025. Il modello e il firmware sono ora verificati dal pannello; contenuti e uso effettivo richiedono una lettura delle condivisioni e dei log sul dispositivo.

Da verificare prima di configurare l'invio: esistenza dei log degli accessi amministrativi e dei log di connessione, presenza di accessi di utenti non AdS che richiederebbero D7 e l'elenco nominativo approvato, disponibilità di `Syslog Client Management` o funzione equivalente, protocolli offerti e impostazioni NTP. Solo dopo si sceglie il canale ammesso dal firmware e si collaudano login riuscito, fallito e scarto temporale con i punti 3 e 7 dell'handoff. Se manca l'invio remoto, il limite si registra come rischio residuo con la schermata che lo dimostra.
