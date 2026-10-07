# Componente 4 - iLO 5 via Redfish

## Stato

Il codice del lettore IEL e le unità systemd sono preparati nel repository. La suite locale completa passa con 63 pytest e i nuovi file Python passano `ruff check` e `ruff format --check` il 2026-10-06. Il controllo di anonimizzazione passa dopo aver distinto la chiave Redfish `Members@odata.nextLink` da un indirizzo email. Nessun iLO reale è stato interrogato e nessun timer è stato attivato. Il collaudo punto 3 dell'handoff per iLO resta aperto.

L'ordine del progetto ammette questo componente prima della scelta della TSA e dell'elenco AdS. Prima di usarlo su un dispositivo si verifica la licenza: se l'iLO dispone di Remote Syslog nella licenza effettiva, si rivaluta l'uso del polling. Il solo privilegio `Login` per l'account `ads-reader`, l'accessibilità della porta 443 e l'ora SNTP sul dispositivo richiedono ancora verifica sul campo.

## Contratto del lettore

`bin/ads-ilo.py` usa una sessione Redfish creata con `POST /redfish/v1/SessionService/Sessions/`, legge tutte le pagine dell'IEL e cancella la sessione con `DELETE` della `Location` ricevuta. La documentazione HPE descrive [la sessione, il token e la sua cancellazione](https://servermanagementportal.ext.hpe.com/docs/concepts/redfishauthentication) e mostra [il percorso IEL e i campi `Id`, `Created`, `Message`, `Code`, `Count` e `Updated`](https://hewlettpackard.github.io/ilo-rest-api-docs/ilo5/); entrambe le fonti sono state rilette il 06/10/2026. La forma esatta delle risposte del dispositivo va confrontata nel primo collaudo; i test locali usano l'esempio pubblicato da HPE.

La connessione HTTPS richiede contemporaneamente una CA attendibile tramite `--ca-file` e l'impronta SHA-256 del certificato presentato dall'iLO tramite `--fingerprint-file`; non esiste un'opzione per disattivare la verifica TLS. La password dell'account lettore vive in un file separato, leggibile solo dal servizio. Le richieste non seguono redirect, non usano proxy ereditati e rifiutano URI che escano dall'iLO configurato.

Il primo giro registra una riga per ogni voce IEL già presente, con `Count` e, quando disponibile, `Updated`. Nei giri successivi una voce invariata non produce una seconda riga; un aumento di `Count` produce una riga con `repeat_delta` e con `Updated` come ora dichiarata. Se `Updated` manca o vale l'ora nulla HPE, il terzo campo della riga usa l'ora di lettura e il messaggio dice `repeat_time=unknown`: non inventa l'ora delle ripetizioni. Una voce che riusa `Id` con un nuovo `Created`, oppure riparte da un `Count` minore, è trattata come nuova. I login REST generati dall'account `ads-reader` non sono copiati nel file degli accessi, ma avanzano comunque lo stato.

Le righe hanno i cinque campi `AdsLine`: ora locale della lettura, IP iLO, ora dichiarata dalla voce o ora della lettura quando l'ultima ripetizione è ignota, sistema `ilo5`, messaggio con `Id`, `Code`, `Count` e testo IEL. Lo script scrive direttamente nella cartella `/srv/ads/<IP_ILO>/` già predisposta per l'utente `ads` e aggiunge una riga `ads-ilo status=ok` a ogni lettura riuscita. Un errore produce `ads-ilo status=error`, uscita non zero e un messaggio nel journal senza credenziali o token. Il futuro `ads-silence.sh` dovrà valutare lo stato dell'ultimo giro, non la sola presenza del file, perché il file può contenere anche un errore.

Il file JSON sotto `/var/lib/ads/ilo/` conserva `Id`, `Created` e `Count`. Le righe vengono sincronizzate su disco prima di sostituire atomicamente lo stato. Se il processo cade fra le due operazioni, il giro seguente può ripetere una riga; i valori `Id` e `Count` permettono di riconoscerla. Le ripetizioni aggregate dall'iLO fra due letture non hanno singoli orari recuperabili dall'IEL; il lettore conserva il loro numero e l'ultima ora disponibile. Se il registro dell'iLO sovrascrive una voce prima del giro successivo, il polling non può ricostruirla.

## Preparazione e collaudo ancora da eseguire

1. Verificare su iLO modello, firmware, `License Type`, accesso all'IEL con `ads-reader` e presenza di `Updated` nelle voci ripetute. Nessuna di queste proprietà è stata misurata sul dispositivo.
2. Preparare su ciascun iLO un certificato TLS con nome o IP nel SAN, la CA attendibile per il collettore e l'impronta SHA-256 del certificato del dispositivo. Un cambio di certificato richiede aggiornamento esplicito dell'impronta prima del giro successivo.
3. Sul collettore, predisporre `/etc/ads/secrets/ilo/<IP_ILO>.password` con proprietario `ads`, modalità `0600`, `/etc/ads/certs/ilo/<IP_ILO>.pem` e `.sha256` leggibili da `ads`, `/var/lib/ads/ilo/` scrivibile da `ads` e `/srv/ads/<IP_ILO>/` con proprietario `ads:ads`, modalità `0750`. Il file `.sha256` contiene soltanto 64 cifre esadecimali; non contiene la password.
4. Installare `bin/ads-ilo.py` come `/opt/ads/bin/ads-ilo.py` e le due unità da `config/collettore/etc/systemd/system/`, senza attivare ancora il timer. Eseguire prima un giro manuale controllato e verificare file, cinque campi, checkpoint e logout della sessione; ripeterlo senza nuovi eventi e attendere solo la riga `status=ok`.
5. Provocare separatamente un accesso iLO riuscito e uno fallito con un account amministrativo e leggere le relative righe nel file del giorno. Provare anche la perdita di raggiungibilità o una credenziale errata senza mostrare password: il servizio deve fallire e registrare `status=error`. Solo dopo queste prove attivare `ads-ilo@<IP_ILO>.timer`.

I comandi per la preparazione sul collettore si consegnano all'operatore un'azione alla volta, con l'indirizzo letto dal livello privato del progetto e dopo aver verificato licenza e prerequisiti. Nessun comando di questo runbook è stato eseguito su un host reale.
