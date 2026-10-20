# Runbook del punto 3: l'host Proxmox come sorgente

> Procedura in corso dal 2026-10-01, con comandi, esiti e significato di ciascun passo. Riferimenti: sezione 5 dell'handoff (configurazione dell'host), sezione 2 dello studio (matrice dei cinque campi), sezione 6 dell'handoff (collaudo punto 3). I segnaposto tra parentesi angolari rimandano a `config/parametri.yaml`. I comandi si lanciano dalla PowerShell della postazione dell'amministratore, via SSH.

## Chi amministra l'host

L'host lo amministra l'IT Manager; lo stesso host è gestito anche da NinjaOne RMM, amministrato dall'MSP, che quindi vi accede attraverso l'agent di NinjaOne. Gli accessi diretti all'host, via SSH e interfaccia web, li registra questa sorgente; quelli che passano da NinjaOne li registra la sorgente NinjaOne (`ads-ninja.py`, punto 8 dell'ordine di sviluppo).

## 1. Ricognizione in sola lettura

Prima di scrivere la configurazione si guarda l'host com'è, per non ripetere l'errore del componente 2, dove il nome di un programma era stato ipotizzato e si è rivelato sbagliato.

```powershell
ssh root@<IP_HOST> "dpkg -l rsyslog rsyslog-gnutls 2>/dev/null | grep ^ii; systemctl is-active rsyslog; systemd-analyze cat-config systemd/journald.conf | grep -iE '^(ForwardToSyslog|Storage)'; ls -l /var/log/pveproxy/access.log; journalctl --since today -o short | grep -E 'pvedaemon.*auth|Accepted' | tail -n 4"
```

Esito del 2026-10-01 e significato. rsyslog non è installato, quindi l'host oggi scrive solo nel journal di systemd e non può inoltrare niente: va installato. I messaggi di autenticazione si chiamano `sshd` (Debian 12 ha un OpenSSH precedente alla 9.8, che invece rinomina i login in `sshd-session`) e `pvedaemon` con il testo «successful auth for user». L'access log dell'interfaccia web esiste e pesa già 8 MB: letto dall'inizio rimanderebbe mesi di storico. L'host accetta il login SSH di root con password, dato da portare in network-design.

## 2. Configurazione e prova in container

La configurazione è il template `config/proxmox-host/etc/rsyslog.d/90-ads.conf.template`, che `bin/ads-render.py` riempie con indirizzo e nome del collettore. Invia in TLS sulla 6514 e verifica il certificato del collettore per nome (`x509/name`): il nome permesso è il FQDN scritto nel certificato, mentre la destinazione è l'indirizzo, così l'invio non dipende dal DNS interno, che per il collettore non è ancora registrato. Se il collettore è fermo i messaggi restano in una coda su disco dell'host e partono alla ripresa.

La prova `tests/debian12/verifica-sorgente-proxmox.sh` gira in `debian:bookworm`, la stessa base dell'host, con due rsyslog nello stesso container, uno da collettore e uno da host, e certificati emessi con `bin/ads-pki.sh`. Verifica che arrivino `sshd`, `pvedaemon` e le righe nuove dell'access log, e che non arrivino lo storico, i messaggi estranei e nulla da un rsyslog che ha un nome permesso diverso da quello del certificato. Il controllo negativo è dimostrato: dando al terzo rsyslog il nome giusto la prova fallisce.

## 3. Installazione sull'host

```powershell
scp -r "D:\log-collector\build\<pacchetto-host>" root@<IP_HOST>:/root/
ssh root@<IP_HOST> "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y rsyslog rsyslog-gnutls"
ssh root@<IP_HOST> "grep -h 'Accepted' /var/log/auth.log | tail -n 2"
ssh root@<IP_HOST> "install -D -m 0644 /root/<pacchetto-host>/tls/ca.pem /etc/rsyslog.d/tls/ca.pem && install -D -m 0644 /root/<pacchetto-host>/host/etc/rsyslog.d/90-ads.conf /etc/rsyslog.d/90-ads.conf && rsyslogd -N1 && systemctl restart rsyslog && systemctl is-active rsyslog"
```

Esiti del 2026-10-01. La copia porta sull'host la sola configurazione e il certificato della CA, nessuna chiave privata. L'installazione aggiunge rsyslog e rsyslog-gnutls 8.2302 con tre librerie e non rimuove nulla; mostra anche che sull'host ci sono 242 pacchetti non aggiornati e un repository configurato due volte, dati per network-design. Il terzo comando chiude l'ultima voce [Non verificato] dell'handoff per l'host: un login SSH compare in `/var/log/auth.log`, quindi il journal arriva a rsyslog senza altra configurazione. Il quarto installa i file, controlla la sintassi e riavvia solo se il controllo passa: esito `End of config validation run` e `active`.

## 6. Verifica del filtro sul vero

Una prima lettura dopo il riavvio mostrava ancora due richieste periodiche, e non si è corretto niente prima di sapere perché. La diagnosi, in sola lettura, ha confrontato l'ora del riavvio sull'host (`systemctl show rsyslog -p ActiveEnterTimestamp`, 16:41:04) con l'ora dell'ultima richiesta periodica sul collettore (16:41:04, nello stesso secondo): erano le ultime della configurazione vecchia. Nei quasi quattro minuti successivi, con l'interfaccia aperta che interroga l'host ogni due secondi circa, non ne è arrivata nessuna; le 163 presenti nel file del giorno sono tutte dei dieci minuti con il filtro vecchio. Il login web compare in due forme, `POST /api2/json/access/ticket` e `POST /api2/extjs/access/ticket`, e il filtro su `/access/ticket` le copre entrambe. La prova con la configurazione nuova, il 2026-10-02: un login web compare con le due righe dello stesso secondo, e nel file del giorno le richieste periodiche sono zero. Il file del 2026-10-02 si è creato dopo la mezzanotte, a conferma che il cambio di giorno funziona.

## 7. Collaudo punto 3 per l'host

Il 2026-10-02 un login fallito e uno riuscito, sia dall'interfaccia web sia in SSH, letti sul collettore con `sudo grep -E 'authentication failure|Failed password' /srv/ads/<IP_HOST>/<giorno>.log`. Il login web fallito compare come `pvedaemon[...]: authentication failure; rhost=::ffff:<postazione> user=root@pam`, che a differenza del riuscito porta utente e IP nella stessa riga; il login SSH fallito come `sshd[...]: Failed password for root from <postazione> port ...`, accompagnato dalla riga di PAM con `rhost` e `user`. Nell'access log un login web fallito non ha esito 401: la forma `extjs` dell'API risponde sempre 200 e mette l'esito nel corpo, e riuscito e fallito differiscono solo per la dimensione della risposta (77 byte contro circa 760, letti in `/var/log/pveproxy/access.log`). Per questo l'esito si legge da `pvedaemon`, e l'access log serve per l'IP dei login riusciti, che `pvedaemon` non scrive.

| Evento | Riga che lo registra | Campi |
|---|---|---|
| login web riuscito | `pvedaemon: <utente> successful auth for user '<utente>'` e, nello stesso secondo, `pveproxy-access: <IP> - - [...] "POST /api2/.../access/ticket ..." 200` | utente dalla prima, IP dalla seconda |
| login web fallito | `pvedaemon: authentication failure; rhost=<IP> user=<utente>` | tutti nella stessa riga |
| login SSH riuscito | `sshd: Accepted password for <utente> from <IP> port ...` | tutti nella stessa riga |
| login SSH fallito | `sshd: Failed password for <utente> from <IP> port ...` | tutti nella stessa riga |

Collaudo superato. Gli accessi che l'MSP fa attraverso NinjaOne non passano da qui: li registrerà la sorgente NinjaOne.

## 8. Consumer HTTPS dello snapshot nel progetto rete, 12/10/2026

Questo controllo riguarda la postazione amministrativa e non cambia l'inoltro Syslog dall'host al collettore. Nel progetto `D:/network-design` il client `Get-ProxmoxSnapshot.ps1` aveva un bypass globale della verifica TLS in Windows PowerShell 5.1 e `-SkipCertificateCheck` in PowerShell 7. Un preflight sul nodo reale con Windows PowerShell 5.1, senza HTTP e senza token, ha verificato impronta del certificato, nome, validità e catena fino alla CA privata autenticata. Sono stati installati un client .NET con verifica limitata alla singola connessione e pin della foglia, e un file privato con i pin; i due bypass sono stati rimossi. Le prove locali hanno respinto pin, nome, host, porta e URL errati.

Il primo `Invoke-RefreshFonti.ps1 -Fonte proxmox -DryRun` si è fermato quando PowerShell ha convertito un argomento `$null` in stringa vuota e il client C# ha aggiunto un corpo alla GET; non ha promosso alcuno snapshot. Dopo aver limitato il corpo HTTP alle POST, il test locale del caso difettoso è passato. Il secondo dry-run reale del 12/10/2026 alle 09:36 CEST ha terminato con codice 0 e `PROVA proxmox misura valida, non promossa (-DryRun)`. Dieci endpoint opzionali del guest agent hanno risposto 403 al token di sola lettura: lo snapshot è valido, ma quegli indirizzi IP possono mancare. Il task pianificato e PowerShell 7 non sono ancora stati collaudati. La verifica della revoca è disattivata nel client per mancanza di un percorso CRL/OCSP interno provato; il pin della foglia richiede manutenzione alla rotazione.

Il metodo, il codice, i due dry-run, i risultati negativi e il rollback sono in `D:/network-design/docs/dossier-sicurezza-mcp-proxmox.md` §10 e `D:/network-design/docs/evidenze-sicurezza-mcp-proxmox.md` SEC-PS-01..04. La [documentazione Microsoft del callback di `HttpClientHandler`](https://learn.microsoft.com/en-us/dotnet/api/system.net.http.httpclienthandler.servercertificatecustomvalidationcallback?view=netframework-4.8.1) e di [`X509ChainPolicy.ExtraStore`](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.x509certificates.x509chainpolicy.extrastore?view=netframework-4.8.1) descrive le primitive usate; la [guida Proxmox VE](https://pve.proxmox.com/pve-docs/pve-admin-guide.pdf) descrive la CA del cluster. La decisione di vincolare host, CA e foglia, e gli esiti del nodo reale, sono evidenze locali. La raccolta dei log di accesso Proxmox sul collettore è indipendente da questo snapshot: il collaudo del punto 7 rimane la sua prova specifica.

## 8. Sicurezza del client MCP sulla postazione, 09/10/2026

Questa verifica riguarda il client MCP di `D:/network-design`, non il filtro Syslog dell'host appena collaudato. La configurazione attiva usa un token Proxmox con ruolo `PVEAuditor`, ma aveva `PROXMOX_ALLOW_DANGER=true` e `PROXMOX_VERIFY_SSL=false`. La prova con il primo flag a `false` aveva bloccato anche `list_nodes`; dopo il rollback, la chiamata di sola lettura era tornata riuscita. L'ispezione del pacchetto effettivamente avviato `proxmox-mcp` 0.1.0 conferma che il wheel non contiene `config/safety_policy.json`: la funzione `load_safety_policy` restituisce una lista sicura vuota, quindi la policy predefinita impedisce anche `list_nodes`. <!-- ref-assente --> Questa è la causa osservata del difetto, non una limitazione di Proxmox. Il [progetto upstream del server MCP](https://github.com/josky-com/proxmox-mcp) descrive `list_nodes` fra i tool sicuri e avverte che il software è in sviluppo e può esporre azioni distruttive; l'esito reale è stato perciò confrontato con il codice del pacchetto installato.

Una candidata locale, ancora non attivata, fissa il pacchetto alla versione e agli SHA-256 dei moduli esaminati, registra dieci soli tool di lettura e carica in memoria la lista di quelli permessi. La prova offline con credenziali finte mostra dieci tool, `list_nodes` consentito, `delete_instance` bloccato e nessun tool di modifica nel catalogo. La candidata di avvio passa al processo figlio le sole tre variabili Proxmox, forza i due flag a `false` e `true` rispettivamente per pericolo e verifica TLS, usa `SSL_CERT_FILE` e fallisce se manca la CA privata. Nulla è ancora stato installato nel progetto rete; servono la verifica TLS e una prova reale read-only prima del cambio.

La lettura del certificato HTTPS, fatta senza token, mostra una CA interna Proxmox e un certificato del nodo valido fino al 23/01/2027. L'IP nell'URL API privato corrente non figura nei Subject Alternative Names del certificato; il nome DNS del nodo vi figura, ma dalla postazione non si risolve ancora. Il certificato pubblico della CA è stato copiato dalla Shell Proxmox nel livello privato; la prima trascrizione mancava di quattro caratteri Base64, recuperati con `sed` sulla sola riga incompleta. La copia corretta si decodifica, ha autofirma valida e scade il 21/01/2035. L'impronta SHA-256 della copia locale è registrata nel livello privato; resta da confrontarla con l'impronta prodotta sulla Shell del nodo, prima di considerarla ancora di fiducia. Poi servono una risoluzione locale controllata del nome verso l'IP di gestione e una prova TLS con CA e nome verificati, senza inviare token durante il preflight. La [guida ufficiale Proxmox VE](https://pve.proxmox.com/pve-docs/pve-admin-guide.pdf) spiega che il certificato del nodo è firmato dalla CA del cluster, non automaticamente fidata dai client. La [documentazione HTTPX](https://www.python-httpx.org/environment_variables/) documenta l'uso di `SSL_CERT_FILE`; la verifica del nome resta necessaria.

La prima prova TLS senza HTTP e senza token, fatta con Python 3.13 e la CA corretta, ha fallito con `CA cert does not include key usage extension`. La causa è specifica della verifica X.509 rigorosa attivata per default da Python 3.13: la CA Proxmox osservata non contiene l'estensione `keyUsage`, mentre Python 3.12 usato dal pacchetto MCP non attiva quel flag. Il confronto dei flag è stato fatto offline e ha motivato la prova separata con Python 3.12, senza interpretare i flag da soli come prova di connessione. Non è stato disattivato alcun controllo nel MCP attivo. La [documentazione Python 3.13](https://docs.python.org/en/3.13/library/ssl.html) descrive `VERIFY_X509_STRICT` predefinito; la [documentazione OpenSSL](https://docs.openssl.org/3.4/man1/openssl-verification-options/) dice che il controllo rigoroso richiede `keyUsage` nelle CA.

La prova TLS separata con Python 3.12 del pacchetto MCP è riuscita: `TLS_VERIFIED_OK TLSv1.3`, collegandosi all'IP di gestione ma presentando il nome DNS del certificato come `server_hostname`, con la CA privata caricata esplicitamente. Non è stata inviata alcuna richiesta HTTP né alcun token. Questo dimostra la verifica della catena e del nome per il runtime attuale; non risolve la mancanza di risoluzione DNS locale, non cambia il fatto che Python 3.13 rigoroso rifiuta la CA e non sostituisce il confronto dell'impronta con la Shell.

Il registro di audit con metodo, esiti positivi e negativi, significato probatorio e gate residui è `D:/network-design/docs/evidenze-sicurezza-mcp-proxmox.md`; le prove grezze e il PEM restano nei rispettivi livelli privati. Il documento dichiara separatamente che `Get-ProxmoxSnapshot.ps1` usa ancora un bypass TLS: la riuscita del MCP non prova la sicurezza di quel consumer distinto.

L'impronta SHA-256 della CA calcolata il 09/10/2026 direttamente nella Shell Proxmox con `openssl x509 -in /etc/pve/pve-root-ca.pem -noout -fingerprint -sha256` coincide con quella della copia privata, dopo aver tolto i due punti e normalizzato le maiuscole. Questo supera il gate di provenienza della CA. La prova negativa dello script per la mappatura del nome, eseguito da un processo Windows non elevato, si è fermata prima di scrivere nel file `hosts`: il requisito di privilegi amministrativi è applicato. In quel momento mappatura, URL, prova MCP e cutover erano ancora pendenti; l'esito successivo è riportato qui sotto.

**Esito finale del 09/10/2026.** La voce `hosts` è stata installata da PowerShell elevata con esito `HOSTS_PROXMOX_OK` e la risoluzione è stata verificata una seconda volta. Il solo `PROXMOX_URL` privato ora usa il nome presente nel SAN del certificato, con vecchio URL salvato per rollback. La CA pubblica autenticata è stata copiata nel livello privato del progetto rete e il client HTTPX del pacchetto è stato verificato usare `verify=True`; il launcher passa `SSL_CERT_FILE` solo al processo MCP. Il filtro verifica i byte dei 19 moduli del pacchetto prima dell'import, ammette dieci tool di lettura e respinge `delete_instance`. Il candidato ha completato `list_nodes` sul nodo reale. Dopo il cambio guardato di `.mcp.json`, `claude mcp list` ha mostrato `Connected` e una sonda vincolata all'hash della configurazione attiva ha ripetuto catalogo, rifiuto del tool di modifica e `list_nodes` reale. I flag attivi sono `PROXMOX_ALLOW_DANGER=false` e `PROXMOX_VERIFY_SSL=true`: i due rischi MCP sono sanati per il runtime attuale. Il token resta nel `.env` privato e rimane leggibile da processi dello stesso account Windows; il client PowerShell `Get-ProxmoxSnapshot.ps1` usa ancora un bypass TLS e richiede correzione separata. Un aggiornamento a Python 3.13 richiederà nuovo collaudo della CA senza `keyUsage`. Il registro di audit è in `D:/network-design/docs/evidenze-sicurezza-mcp-proxmox.md` e le fonti ufficiali sono collegate lì.

La spiegazione completa dei due flussi, dei quattordici passaggi misurati, dei confini delle credenziali e dei criteri per superare i limiti residui è nel documento versionato `D:/network-design/docs/dossier-sicurezza-mcp-proxmox.md`. Il grafico statico originale/attuale è in `_notes/fonti-private/schemi-visivi/schema-mcp-proxmox-prima-e-dopo-20261009.html`, ignorato da Git, e ne esiste una copia privata in `D:/network-design/_notes/`.

## 4. Prima verifica sul collettore, e che cosa ha mostrato

```powershell
ssh -t -i "$env:USERPROFILE\.ssh\ads-collector_ed25519" asopranzi@<IP_COLLETTORE> "sudo grep -E 'sshd|pvedaemon|pveproxy-access' /srv/ads/<IP_HOST>/`$(date +%F).log | tail -n 6"
```

Sul collettore arrivano le righe dell'access log, con postazione, utente, ora e richiesta, ma sono le chiamate che l'interfaccia web aperta ripete ogni due secondi circa per aggiornare lo stato (risorse del cluster, stato della VM, attività). Non sono accessi: il provvedimento chiede di registrare l'autenticazione, non ogni richiesta di una sessione già autenticata, e inoltrarle tutte produrrebbe milioni di righe al mese da conservare, marcare e copiare. Le stesse righe, poi, entrano nel ruleset predefinito dell'host e duplicano il suo `/var/log/syslog`. La correzione in corso: dall'access log si inoltrano solo le richieste di autenticazione, lette su un ruleset dedicato che non tocca il syslog dell'host.

## 5. Le righe reali di un login, e la correzione del filtro

```powershell
ssh -t -i "$env:USERPROFILE\.ssh\ads-collector_ed25519" asopranzi@<IP_COLLETTORE> "sudo grep -E 'sshd|pvedaemon|access/ticket' /srv/ads/<IP_HOST>/`$(date +%F).log | tail -n 6"
```

Dopo un'uscita e un rientro nell'interfaccia web, sul collettore un login web si presenta come due righe dello stesso secondo, e ciascuna porta una metà dell'informazione. L'access log scrive `::ffff:<postazione> - - [...] "POST /api2/extjs/access/ticket HTTP/1.1" 200 763`: c'è l'IP, ma l'utente è `-`, perché quando arriva la richiesta di login l'utente non è ancora autenticato; il percorso è `extjs`, non `json` come si era supposto. `pvedaemon` scrive `<root@pam> successful auth for user 'root@pam'`: c'è l'utente, non l'IP. Insieme danno i cinque campi, come prevede la matrice dello studio. Nella stessa uscita compaiono le attività di `pvedaemon` sulle VM (`starting task`, `end task`, `vncproxy`), che non sono accessi.

Il filtro è stato quindi riscritto. L'access log va su un ruleset proprio, `ads_pveproxy`, che inoltra solo le righe con `/access/ticket` in entrambe le forme e non entra nel ruleset predefinito dell'host; di `pvedaemon` passano solo i messaggi di autenticazione. La prova in container usa ora le righe reali, con indirizzi di documentazione, e la sua capacità di fallire è dimostrata due volte: senza il filtro sull'access log fallisce sulla richiesta periodica, senza la condizione su `pvedaemon` fallisce sul task.

Installazione della versione corretta sull'host, 2026-10-01: `scp -r` del pacchetto nuovo, poi `install -D -m 0644 .../90-ads.conf /etc/rsyslog.d/90-ads.conf && rsyslogd -N1 && systemctl restart rsyslog && systemctl is-active rsyslog`; esito `End of config validation run` e `active`.

## 6. Verifica del filtro sul vero

Una prima lettura dopo il riavvio mostrava ancora due richieste periodiche, e non si è corretto niente prima di sapere perché. La diagnosi, in sola lettura, ha confrontato l'ora del riavvio sull'host (`systemctl show rsyslog -p ActiveEnterTimestamp`, 16:41:04) con l'ora dell'ultima richiesta periodica sul collettore (16:41:04, nello stesso secondo): erano le ultime della configurazione vecchia. Nei quasi quattro minuti successivi, con l'interfaccia aperta che interroga l'host ogni due secondi circa, non ne è arrivata nessuna; le 163 presenti nel file del giorno sono tutte dei dieci minuti con il filtro vecchio. Il login web compare in due forme, `POST /api2/json/access/ticket` e `POST /api2/extjs/access/ticket`, e il filtro su `/access/ticket` le copre entrambe. La prova con la configurazione nuova, il 2026-10-02: un login web compare con le due righe dello stesso secondo, e nel file del giorno le richieste periodiche sono zero. Il file del 2026-10-02 si è creato dopo la mezzanotte, a conferma che il cambio di giorno funziona.

## 7. Collaudo punto 3 per l'host

Il 2026-10-02 un login fallito e uno riuscito, sia dall'interfaccia web sia in SSH, letti sul collettore con `sudo grep -E 'authentication failure|Failed password' /srv/ads/<IP_HOST>/<giorno>.log`. Il login web fallito compare come `pvedaemon[...]: authentication failure; rhost=::ffff:<postazione> user=root@pam`, che a differenza del riuscito porta utente e IP nella stessa riga; il login SSH fallito come `sshd[...]: Failed password for root from <postazione> port ...`, accompagnato dalla riga di PAM con `rhost` e `user`. Nell'access log un login web fallito non ha esito 401: la forma `extjs` dell'API risponde sempre 200 e mette l'esito nel corpo, e riuscito e fallito differiscono solo per la dimensione della risposta (77 byte contro circa 760, letti in `/var/log/pveproxy/access.log`). Per questo l'esito si legge da `pvedaemon`, e l'access log serve per l'IP dei login riusciti, che `pvedaemon` non scrive.

| Evento | Riga che lo registra | Campi |
|---|---|---|
| login web riuscito | `pvedaemon: <utente> successful auth for user '<utente>'` e, nello stesso secondo, `pveproxy-access: <IP> - - [...] "POST /api2/.../access/ticket ..." 200` | utente dalla prima, IP dalla seconda |
| login web fallito | `pvedaemon: authentication failure; rhost=<IP> user=<utente>` | tutti nella stessa riga |
| login SSH riuscito | `sshd: Accepted password for <utente> from <IP> port ...` | tutti nella stessa riga |
| login SSH fallito | `sshd: Failed password for <utente> from <IP> port ...` | tutti nella stessa riga |

Collaudo superato. Gli accessi che l'MSP fa attraverso NinjaOne non passano da qui: li registrerà la sorgente NinjaOne.
