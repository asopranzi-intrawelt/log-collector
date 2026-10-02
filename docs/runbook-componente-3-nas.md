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
