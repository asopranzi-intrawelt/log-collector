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
