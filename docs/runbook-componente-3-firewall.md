# Runbook del punto 3: il firewall USG FLEX come sorgente

> Procedura eseguita dal 2026-10-02 sul firewall Zyxel USG FLEX 500, con impostazioni, esiti e significato di ciascun passo, scritta per essere letta anche da chi non ha partecipato al lavoro e per servire da fonte a un documento per un cliente. Riferimenti: sezione 2 dello studio (matrice dei cinque campi), decisione D5 dello studio (NTP su INRIM), sezione 6 dell'handoff (collaudi punti 3 e 7). I valori reali (indirizzi, identificativi) non compaiono: stanno in `config/parametri.yaml`.

## Che cosa si è fatto e perché

Il firewall è uno dei sistemi a cui gli amministratori accedono, quindi i loro login, i tentativi falliti e i logout devono finire nel collettore con i cinque campi richiesti: ora di ricezione, sorgente, ora dichiarata, sistema, e nel messaggio utente e postazione di provenienza. Il firewall non sa inviare in TLS, quindi invia in syslog UDP sulla porta 514, ammessa dal firewall locale del collettore solo dalla LAN. Lo amministra l'IT Manager.

## 1. Stato di partenza

Le fonti del progetto `D:/network-design` danno il sistema del firewall, ZLD 5.42(ABUJ.1), dal backup della configurazione del 19/05/2026. Nell'interfaccia, `Configuration > Log & Report > Log Settings` mostrava il 2026-10-02 quattro server remoti, tutti senza indirizzo e spenti, e i due server di posta senza configurazione: nessuno riceveva i log del firewall, quindi la configurazione si è fatta da zero senza sovrascrivere nulla.

## 2. Server remoto verso il collettore

In `Log Settings`, `Remote Server 1`, `Edit`: `Active` spuntato, formato `Syslog`, indirizzo del collettore, porta 514, facility `Local 1`. Nella tabella `Active Log` sono attive due sole categorie, a livello `normal`: `Authenticate`, dove ZLD registra login e logout degli amministratori, e `System`, dove registra le operazioni sull'apparato e i comandi della console (`ZySH`). Le altre categorie (Security, Security Service, Network, BWM, VPN, Wireless e le altre) registrano il traffico che attraversa il firewall: utili alla sicurezza, non sono accessi di amministratori, porterebbero sul collettore decine di migliaia di righe al giorno e la navigazione dei dipendenti, che è un tema di privacy dei lavoratori. La tabella `Active Log (AP)`, degli access point, resta spenta. Dopo `OK` e `Apply` la riga del server mostra la lampadina accesa e l'indirizzo del collettore.

Il firewall si presenta al collettore con l'indirizzo della sua interfaccia LAN delle postazioni, e i suoi log finiscono nella cartella con quell'indirizzo.

## 3. Che cosa arriva, e tre correzioni

Un login con password sbagliata, uno riuscito e un logout danno, nella categoria `User`, tre righe con tutti i campi:

| Evento | Testo del messaggio (`msg`) | Altri campi della riga |
|---|---|---|
| login riuscito | `Administrator <account>(MAC=<postazione>) from http/https has logged in Device` | `note="Account: <account>"`, `user="<account>"`, `src="<IP postazione>:0"`, `cat="User"` |
| login fallito | `Failed login attempt to Device from http/https (incorrect password or inexistent username)` | `note="Account: <account>"`, `src="<IP postazione>:0"`, `cat="User"` |
| logout | `Administrator <account>(MAC=<postazione>) from http/https has logged out Device` | `user="<account>"`, `src="<IP postazione>:0"`, `cat="User"` |

Così si è chiusa una voce [Non verificato] dello studio: i login amministrativi di ZLD 5.42 stanno nella categoria `User`, che nell'interfaccia è sotto `Authenticate`. Con il login, se l'account ha l'autenticazione a due fattori, compaiono alcune righe `Cannot create admin's secret-file ... note="two-factor auth."`: sono il meccanismo del secondo fattore, poche e solo al momento del login, e si lasciano passare.

Le prime righe hanno mostrato tre difetti, corretti uno per uno.

Il primo, sul collettore: ZLD scrive l'anno dopo l'ora (`Oct  2 05:35:37 2026 usgflex500 ...`) e rsyslog prendeva l'anno per nome del sistema. La correzione è il parser `pmrfc3164` con `detect.YearAfterTimestamp`, nella configurazione del collettore. Provandola in container è emerso un difetto più grave della regola sul formato scritta per il componente 2: dopo il nome del sistema ZLD non scrive un nome di programma, rsyslog prendeva `src="<ip>:` per tale nome e la regola inseriva uno spazio dentro l'indirizzo. Ora tag e testo si riattaccano esattamente come erano nella riga, così la registrazione resta identica a quella scritta dal firewall. Dopo la correzione le righe hanno il sistema `usgflex500`.

Il secondo, sul firewall: la sottocategoria `System Monitoring` della categoria `System` invia ogni 16 secondi circa lo stato di CPU, memoria e sessioni, circa 5.400 righe al giorno senza alcun accesso. In `Remote Server 1`, `Edit`, il `+` di `System` apre dodici sottocategorie; si è spenta solo `System Monitoring`. Le altre restano attive, perché `ZySH` registra i comandi della console e `System` le operazioni sull'apparato, e le restanti non avevano prodotto righe: si spengono solo se, misurate, risultano rumore.

Il terzo, sul firewall: l'ora dichiarata era indietro di 7 ore rispetto a quella di ricezione. In `Configuration > System > Date/Time` l'orologio era giusto, ma il fuso era sincronizzato automaticamente sul centro degli Stati Uniti (`UTC-06:00`, con ora legale americana); il formato syslog di ZLD non porta il fuso, quindi il firewall scriveva l'ora locale americana e il collettore la leggeva come ora di Roma. Correzione: NTP su `ntp1.inrim.it` al posto di `0.pool.ntp.org`, come prevede la decisione D5 dello studio e come il collettore, e fuso manuale `(UTC+01:00) Berlin, Stockholm, Rome, Bern, Brussels`, su indicazione dell'utente perché l'azienda è italiana. Dopo `Apply` l'ora corrente risulta in `UTC+02:00`, cioè l'ora legale italiana. Le date dell'ora legale mostrate erano però quelle americane (seconda domenica di marzo, prima di novembre): si impostano a mano quelle europee, ultima domenica di marzo e ultima di ottobre, per evitare un'ora di errore fra le due date di fine ottobre. Impostate il 2026-10-02 con la regolazione automatica tolta: inizio ultima domenica di marzo alle 2:00, fine ultima domenica di ottobre alle 2:00, offset 1 ora. Su ZLD le due ore si contano probabilmente in ora solare, quindi le 2:00 di fine ottobre corrispondono alle 3:00 legali in cui l'Italia torna all'ora solare; [Non verificato], da controllare nei log dopo il 25/10/2026.

## 4. Collaudo

Il 2026-10-02, dopo le tre correzioni, un'uscita e un rientro nell'interfaccia del firewall, letti sul collettore con `sudo grep 'logged in' /srv/ads/<IP_FIREWALL>/<giorno>.log | tail -n 1`: il login è ricevuto alle 14:46:43.13 e dichiarato dal firewall alle 14:46:43 con fuso `+02:00`, cioè i due orari coincidono entro il secondo, che è la risoluzione con cui il firewall dichiara l'ora. Collaudo punto 7 superato per il firewall. L'ultimo messaggio `System Monitoring` è delle 14:29:12, il momento in cui la sottocategoria è stata spenta, ed è anche l'ultima riga con l'ora americana: da allora non ne arrivano. Con la tabella della sezione 3, che mostra login riuscito, fallito e logout con i cinque campi, è superato anche il collaudo punto 3 per il firewall.

## 5. Domande aperte

Gli amministratori entrano nel firewall con l'account generico `admin`: la riga dice da quale postazione, non quale persona. È lo stesso problema risolto sul collettore con gli account personali (ADR-008), e vale anche per `root` sull'host Proxmox. Da valutare se includere la categoria `VPN`, se gli amministratori o l'MSP accedono dall'esterno con la VPN del firewall.
