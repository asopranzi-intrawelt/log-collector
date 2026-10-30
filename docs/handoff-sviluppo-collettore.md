# Handoff di sviluppo - Collettore log AdS su Proxmox

Riferimento funzionale: `studio-collettore-ads.md`. Questo file dice **come e in che ordine** costruire. Legenda: **[V]** verificato su fonte · **[Non verificato]** da confermare durante lo sviluppo · **[Inferenza]** dedotto.

---

## 0. Cosa blocca e cosa no

| Si parte subito | Bloccato finché manca |
|---|---|
| VM, Debian, rsyslog, TLS, nftables, NTP | Filtri Windows, QNAP, M365 → **elenco AdS approvato dalla Direzione** |
| Sorgenti firewall, NAS, Proxmox | Estensione Windows oltre il pilota → **parere del consulente privacy** |
| iLO Remote Syslog; lettore Redfish alternativo | Passo 3 della catena notturna → **scelta della TSA** |
| Struttura dei job notturni (senza marca) | Mail alla Direzione → **relay SMTP da usare** |
| | Copia immutabile → **custode/supporto indipendente dagli AdS, politica e credenziali approvati**; il NAS-HERO amministrato dagli stessi AdS non è da solo prova indipendente |

### Pendenze con evidenza, 23/10/2026

Verifica in sola lettura sulla VM del collettore il 23/10, con SSH a chiave, `BatchMode=yes` e host key obbligatoria: `/srv/ads` risulta un mount ext4 `rw,nosuid,nodev,noexec` e `rsyslog` è `active`. `ads-nightly.timer` e `ads-silence.timer` restituiscono `not-found` e `inactive`; lo script notturno e la cartella manifest non sono visibili all'account interrogato. Quest'ultima osservazione non distingue assenza da permessi insufficienti. La catena locale provata in WSL non è installata come servizio: le righe WindTre 89/90 richiedono ancora prova sulla VM, custodia indipendente e conservazione verificabile. Le nuove unità D6 sono solo nel repository; il test su WSL e la verifica sintattica systemd non sostituiscono installazione, heartbeat o allarme consegnato. Nessuna configurazione è stata modificata.

Prima dell'installazione del timer notturno, misurare su volume e dati rappresentativi la durata e il carico della verifica integrale della catena. `bin/ads-measure-verify.py` produce contatori minimizzati e rifiuta un campione che cambia durante la misura; la sua prova WSL su tre archivi sintetici non determina il carico della VM. Il controllo `ads-verify.sh --date` rifiuta anche un manifest precedente simbolico; la prova WSL era verde con il link prima della correzione. Questa modalità controlla il solo giorno richiesto e il suo legame, quindi il job continua a eseguire la verifica storica completa prima di chiudere nuove giornate. Definire la retention degli originali e un ancoraggio verificabile prima di eliminarli: oggi la verifica si ferma se un originale di un manifest conservato manca.

Il candidato ora rifiuta directory simboliche di stato e archivio; il verificatore isolato applica la stessa guardia. La prova WSL usa link controllati in `/tmp` e non dimostra permessi, mount e assenza di cambi concorrenti sulla VM.

Per D6 il ricevente candidato distingue `APP-NAME=ads-heartbeat` dagli accessi Windows: RFC 5424 sulla porta TLS 6514 e IP presente in `sorgenti.windows_pilota` scrivono `/var/lib/ads/heartbeats/<IP>/<giorno>.heartbeat`, letto da `ads-silence.py`; UDP, RFC 3164 e IP estranei scrivono invece `/var/log/ads-heartbeat-rejected/` con permessi `root:root`. Nessun marker entra in `/srv/ads/`. Il test integrato Debian 13 verifica lo smistamento e la lettura D6; resta il collaudo dell'agent Windows con versione fissata, della lista IP e dei permessi reali. TLS autentica il server, non il client anonimo di rsyslog: non descrivere il marker come attestazione di identità della postazione. Il flusso rifiutato richiede politica di ritenzione e misura della capienza prima dell'installazione.

Fluent Bit 4.1.1 Linux ha superato `--dry-run` e la consegna del marker a un ricevitore TLS fittizio con `tls.verify_hostname on`; spostando il ricevitore a un IP non presente nel SAN, il client ha rifiutato il certificato per `hostname mismatch` e nessun payload è arrivato. Il campione RFC 5424 sintetico del mittente è ora una fixture che il test Debian 13 inoltra al vero rsyslog e fa leggere da D6. La prova non usa il plugin Windows `winevtlog`, la versione ZIP del pilota o la VM reale: restano il collaudo Windows, la policy approvata e la consegna dell'allarme.

Il candidato per il flusso dei marker rifiutati ora dispone di ispezione, dry run e scadenza con giorni espliciti: `bin/ads-heartbeat-rejected-retain.sh` riusa il motore tecnico Seeweb senza toccare `/srv/ads/`. Il test Linux esercita il confine dei giorni, l'isolamento e i link, e cade se il wrapper usa la radice Seeweb. Le unità systemd passano la verifica su copie Linux con permessi 0644, ma non sono installate; durata, volume reale, quota e allarme esterno sono ancora da definire e provare sulla VM.

Il bundle candidato Windows è ora generato da `bin/ads-render-windows.py` e `config/windows-pilota/` soltanto con identità AdS approvate nella forma `DOMINIO/utente`; nomi privi di dominio vengono rifiutati. Fluent Bit 5.1.3 Windows, ZIP ufficiale verificato per SHA-256, accetta la configurazione; `winevtlog` ha restituito su Application i nomi di campo attesi. La query candidata confronta nome e dominio dell'AdS come destinatario o attore: il 4648 distingue `SubjectUserName` dalle credenziali `TargetUserName`, e il 4672 usa `SubjectUserName`. Il binario Windows ha inviato tre eventi sintetici e un heartbeat a un ricevitore TLS locale; la fixture di 740 byte è stata consegnata a rsyslog Debian 13, che ha scritto tre eventi in AdS e il marker nel file D6, conservando i domini nel messaggio. La verifica del nome TLS ha rifiutato un SAN diverso, mentre un controllo con la sola verifica del nome disattivata ha consegnato i messaggi. Un'altra prova locale ha ritrovato dopo l'arresto un record fittizio accodato durante l'assenza del ricevitore, insieme a un record nuovo. Security non era accessibile alla prova locale: valori e grafie effettivi dei domini e degli account, servizio, invio alla VM e recupero degli eventi Security dopo fermo sono ancora da collaudare sul pilota autorizzato. Il limite di coda `500M` dello studio è stato rimosso perché alla saturazione scarta i chunk più vecchi; quota, spazio e allarme della coda restano un gate prima dell'esercizio. Dettaglio e fonti nello studio, sezione 3.

Il bundle include un controllo PowerShell di sola lettura della coda. La prova con il binario Windows vero lo ha visto in allarme quando il ricevitore TLS era assente e un chunk rimaneva sul disco. Richiede il file di configurazione realmente usato dal servizio e ne legge `storage.path`, per evitare un verde falso su una cartella predefinita rimasta vuota. Soglie di byte, spazio libero ed età del chunk sono obbligatorie e ancora da decidere sul pilota; il codice distingue soglia superata da misura non disponibile. Non è installato come job NinjaOne, non controlla da solo il servizio e non dimostra consegna di un avviso esterno.

Il bundle include anche `ads-windows-pilot-preflight.ps1`, da eseguire sul pilota prima dell'installazione del servizio: verifica file e configurazione, corrispondenza del nome macchina, CA pubblica valida, versione 5.1.3 e `--dry-run` con il binario effettivo. Ora rifiuta anche un database bookmark `DB` spostato fuori dalla directory di `storage.path`, che prima passava con `static_ok`. La prova locale del comando è riuscita con il binario Windows; `status=static_ok` è un esito statico. Sul pilota restano la verifica del comando reale del servizio, degli ACL, di Security e del replay del bookmark, del SAN TLS verso la VM, del recapito dei log e dell'avviso NinjaOne. La sequenza e il comando sono nello studio, sezione 3.3.

Il bundle include un controllo successivo di sola lettura per il servizio Windows: verifica avvio automatico, LocalSystem e corrispondenza del binario e della configurazione fra servizio registrato e processo in esecuzione. Le prove usano risposte CIM sintetiche; nessun servizio è stato installato o interrogato sul pilota. ACL, accesso a Security, bookmark, recapito e allarme restano gate separati. Uso e limiti sono nello studio, sezione 3.3.

Il bundle contiene anche un probe Security di sola lettura: verifica presenza dei cinque GUID, bit della policy di sistema e massimo configurato del Security log, poi campiona i nomi dei campi nei sei eventi di accesso selezionati senza esportare i loro valori. Misura inoltre metadati del file e l'età dello storico osservato tramite il primo e l'ultimo record, senza serializzare gli eventi. Il codice è provato con risposte sintetiche; policy, capacità, eccezioni per utente e schema sul pilota restano da misurare. Codici 2 e 3 indicano requisito incompleto o lettura impossibile, non un pilota pronto. L'età osservata non garantisce il recupero dopo un fermo futuro. Uso e limiti sono nello studio, sezione 3.3.

Lettura della VM del 27/10: `/srv/ads` risulta ext4 montato `rw,nosuid,nodev,noexec`, circa 59,8 GB disponibili sul filesystem e 1% usato nell'istantanea; `rsyslog` è attivo, mentre `ads-nightly.timer` e `ads-silence.timer` risultano `not-found`. La misura dei file nell'archivio non è stata possibile: il comando di sola lettura con `sudo -n` ha chiesto una password. Il dato `df` non misura il volume dei log né il costo della verifica storica. Nessun servizio o archivio è stato modificato.

Queste righe distinguono lavoro interno e attese esterne. Per dichiarare chiusa una pendenza servono un artefatto ricevuto e una prova di integrazione, non soltanto il testo di una proposta. Il dossier tecnico di ciascuna sorgente conserva il dettaglio; questa è la vista di consegna al cliente.

Scadenza indicata dall'utente: 20/12/2026 per le evidenze del questionario cliente, con accettazione interna entro venerdì 18/12. Questo collettore contribuisce direttamente alle righe 89 e 90; il programma esteso delle 59 sorgenti non coincide automaticamente con il perimetro del questionario. L'Annex consegnato indica `12/2026` anche per la riga 90; la proposta interna di completarla solo in parte entro dicembre attende conferma scritta del cliente. Date, capacità e criteri dei gate sono nella [roadmap](../.claude/context/roadmap.md); il mancato arrivo di una decisione o di un campione resta una pendenza con evidenza, non una verifica superata.

| Pendenza | Evidenza disponibile | Riscontro necessario | Effetto finché manca |
|---|---|---|---|
| Direzione: nomina ed elenco AdS | Perimetro AdS nello studio; la copia locale dei parametri si legge ma ha zero voci approvate al 28/10 | Atto di nomina ed elenco approvato con data/versione | Bundle Windows reale, filtri QNAP/M365 e D7 non finalizzabili |
| Consulente privacy: estensione Windows | Pilota tecnico distinto dall'estensione | Parere sul perimetro e sui dati da conservare | Estensione Windows sospesa |
| Direzione/fornitori: TSA, relay e custodia indipendente | Catena e opzioni progettate, non installate | Scelta TSA, relay SMTP e custode/supporto immutabile con titolarità e accessi | Marca temporale, avvisi alla Direzione e copia indipendente non collaudabili |
| Team interno: mittenti Syslog non censiti | Il ruleset in esercizio manda in AdS anche messaggi LAN senza corrispondenza esplicita; strict e controllo della quarantena sono candidati provati in Debian. I parametri privati elencano una iLO; la sonda SSH ha raggiunto la VM ma non ha potuto aprire `/srv/ads/` | Lettura autorizzata delle directory dei mittenti, confronto con inventario e proprietari inclusi i silenziosi, prova per fonte; durata approvata, quota o filesystem isolato, costo della scansione e allarme ricevuto da un responsabile | Il filtro in esercizio non si può restringere sulla sola base dei parametri attuali; monitor e ritenzione non sono installati |
| Seeweb: log e percorso di rete | IP sorgente e pacchetti nel tunnel confermati negli screenshot_269/82; test UDP con cattura proposto. Bundle dal live e controllo del ruleset attivo provati localmente; due impronte VM riconfermate il 29/10. Sonda SSH: servizi attivi, UDP 514 in ascolto, `/srv/ads` all'1% e `/var/log` al 44%; bundle v2 applicato e postcheck locale verde | Prova Syslog UDP 514 con pochi eventi GUI/SSH, campi e categorie reali, volume, retention e comportamento al fermo VPN | Nessun evento Seeweb ricevuto né classificazione AdS degli accessi |
| Seeweb: aggiornamento OPNsense | Intervento gratuito proposto; screenshot_135 indica target 26.7.7, snapshot hypervisor, backup configurazione, attività prevista entro due ore e rischio VPN. Il contratto generale 2014 è letto, scheda del servizio non disponibile | Console e backup ripristinabile, finestra, soglia di rollback e prove congiunte del tunnel e dei servizi, compreso il certificato GUI | Upgrade non autorizzato né attestato; test Syslog separato |
| MyOffice: Canon e ReadMeter 7 | Una sola Canon gestita da MyOffice. Nello screenshot_170 il fornitore propone un host Windows spesso acceso e dice di non poter fornire i log richiesti; l'utente indica la VM100 Windows Server 2022 per ReadMeter. Modello iR-ADV C5840 confermato dall'utente; Remote Operation Viewer 2.4 mostra il pannello remoto, non l'audit. La guida Canon della serie C5800 documenta audit e Syslog nativi | Prima di installare ReadMeter sulla VM100 multiservizio: requisiti, privilegi, destinazioni, dati, finestra e ritorno. Per l'audit: controllo remoto in sola lettura di firmware, menu e TLS; poi campione di login e cambi, export e minimizzazione | Nessun agente ReadMeter installato o flusso di audit Canon dimostrato; ricognizione subito, integrazione dopo il gate Seeweb |
| Vianova UCC: centralino cloud | Softphone attivi e Panasonic rimosso secondo il progetto rete; MyOffice è il referente commerciale | Disponibilità di audit accessi amministrativi e cambi configurazione, export/API, campioni e retention; separare eventi di servizio e dati di chiamata | Nessun audit del PBX cloud raccolto |
| Produttore QA e infrastruttura | QA `02f1e40` e collettore `b29612c` chiusi; outbox prima del backup, ricevitore con budget e riserva di spazio. Candidato SSH con ricevuta/replay provato solo in locale e WSL; nel nuovo diff il ricevitore richiede un mount dedicato. Due LXC previsti | Collaudo SSH fra host con chiavi/host key e identità per ambiente, quota fisica/allarme, indice minimizzato, ACL/retention/restore dell'originale, LXC e campioni dal job | QA non collegabile alla raccolta reale; backup esterno spento per default |
| Team interno: capacità hub e spool | Preflight, due bind mount su tmpfs Linux 16 MiB, soglia disco ed ENOSPC provati nel namespace WSL; lock residuo corretto; marker e blocco dei casi incerti su fixture | Budget Proxmox con hub e due LXC QA; perdita di alimentazione, carico, triage e consegna/silenzio dell'allarme | Pilot locale soltanto; prova fisica circoscritta, nessuna prontezza operativa |

---

## 1. VM sul Proxmox

[V] Versione corrente di Proxmox VE: 9.2 su Debian 13.5 (maggio 2026). Il foglio parla di PVE 8: controllare con `pveversion` prima di iniziare, i parametri sotto valgono per 8.x e 9.x **[Non verificato]** su 8.x per `x86-64-v2-AES`.

```
qm create <VMID> --name ads-collector --ostype l26 \
  --machine q35 --bios ovmf \
  --efidisk0 <STORAGE>:1,efitype=4m,pre-enrolled-keys=1 \
  --cpu x86-64-v2-AES --sockets 1 --cores 2 \
  --memory 2048 --balloon 0 \
  --scsihw virtio-scsi-single \
  --scsi0 <STORAGE>:16,iothread=1,discard=on,ssd=1 \
  --scsi1 <STORAGE>:60,iothread=1,discard=on,ssd=1,backup=0 \
  --net0 virtio,bridge=vmbr0,tag=<VLAN_SERVER> \
  --agent enabled=1,fstrim_cloned_disks=1 \
  --onboot 1 --startup order=1,up=30 \
  --protection 1 --tablet 0
```

| Parametro | Scelta | Motivo |
|---|---|---|
| `q35` + `ovmf` con chiavi pre-caricate | Secure Boot attivo | Debian 13 avvia con Secure Boot; riduce la manomissione del boot. |
| `x86-64-v2-AES`, 2 core | Default Proxmox, migrabile | rsyslog e gli script sono leggeri. |
| 2 GB, `balloon 0` | RAM fissa | Il collettore non deve rallentare sotto pressione di memoria dell'host. [Inferenza] 2 GB sufficienti: confermare con la prova dei volumi. |
| `virtio-scsi-single` + `iothread=1` | Un thread I/O per disco | Prestazioni e isolamento dell'I/O. |
| `discard=on` | Restituisce spazio allo storage thin | Utile su LVM-thin e ZFS. |
| `ssd=1` | Solo se lo storage è SSD | Altrimenti togliere. |
| **Due dischi**: `scsi0` 16 GB sistema, `scsi1` 60 GB dati | Dati separati dal sistema | Si estende `scsi1` senza toccare il sistema. 60 GB = WORM da 50 GB + margine: **ridimensionare dopo la misura dei volumi**. |
| `backup=0` su `scsi1` | Log esclusi dai backup vzdump | La copia dei log è la cartella WORM. Un backup ulteriore conserverebbe i log oltre i 213 giorni **[Inferenza]** tema di minimizzazione. Si perde al massimo il giorno in corso se l'host si guasta. |
| `onboot 1`, `order=1` | Parte per prima | Riceve i log degli altri servizi durante l'avvio. |
| `protection 1` | Blocca la rimozione della VM e dei dischi | Evita cancellazioni accidentali da GUI. |
| Rete sulla VLAN server | Raggiunge le sorgenti LAN e la porta 443 di iLO | Se iLO è su rete di management separata: regola dedicata sul firewall. |

**Guest agent: installato ma ristretto.** [V] Il QEMU guest agent consente all'host di leggere e scrivere file nel guest e di impostare password utente (qemu.readthedocs.io). Senza restrizioni l'amministratore di Proxmox otterrebbe così un accesso diretto alla VM che scavalca la credenziale distinta. [V] Il file `/etc/qemu/qemu-ga.conf` accetta un elenco di RPC ammessi: definendolo, tutto il resto è bloccato. Consentire solo:
```
[general]
allow-rpcs=guest-sync-delimited,guest-sync,guest-ping,guest-info,guest-shutdown,guest-fsfreeze-status,guest-fsfreeze-freeze,guest-fsfreeze-freeze-list,guest-fsfreeze-thaw,guest-fstrim,guest-network-get-interfaces,guest-get-osinfo,guest-get-host-name,guest-get-time
```
Restano spegnimento pulito, freeze per backup coerenti del disco di sistema, IP in GUI. Sono esclusi `guest-exec`, `guest-file-*`, `guest-set-user-password`, `guest-ssh-*`. **[Non verificato]** la sintassi della chiave nel file: controllare con `qemu-ga --dump-conf` e provare dall'host `qm guest exec <VMID> -- id`, che deve fallire.

Resta vero (studio, sezione 6) che l'amministratore dell'hypervisor può accedere al disco della VM: la restrizione toglie la via immediata, non quella offline.

---

## 2. Debian 13 nella VM

1. **Installazione netinst**, selezionare solo "SSH server" e "standard system utilities". `scsi0`: ext4 unico + swap file da 1 GB. `scsi1`: ext4 montato su `/srv/ads` con `nodev,nosuid,noexec`.
2. **Account**: utente `adsadmin` con chiave SSH, `PermitRootLogin no`, `PasswordAuthentication no`. Password di root nota solo all'amministratore non MSP, con una copia in busta chiusa alla Direzione [Inferenza: prassi, non requisito].
3. **Pacchetti**:
   ```
   apt install rsyslog rsyslog-gnutls chrony nftables openssl curl \
               python3-requests msmtp-mta cifs-utils unattended-upgrades qemu-guest-agent
   ```
   `rsyslog-gnutls` serve per il driver TLS `gtls` di imtcp. Debian recente non installa rsyslog di default: va installato esplicitamente **[Non verificato]** su Debian 13.
4. **chrony**: in `/etc/chrony/sources.d/inrim.sources` le righe `server ntp1.inrim.it iburst` e `server ntp2.inrim.it iburst`; commentare il pool Debian.
5. **unattended-upgrades**: solo aggiornamenti di sicurezza, riavvio automatico disattivato.
6. **nftables** (`/etc/nftables.conf`):
   ```
   table inet filter {
     chain input {
       type filter hook input priority 0; policy drop;
       ct state established,related accept
       iif lo accept
       ip saddr { <SUBNET_LAN>, <SUBNET_SERVER> } udp dport 514 accept
       ip saddr { <SUBNET_LAN>, <SUBNET_SERVER> } tcp dport 6514 accept
       ip saddr <IP_ADMIN_NON_MSP> tcp dport 22 accept
       icmp type echo-request accept
     }
   }
   ```
   Uscita libera verso: NTP INRIM, iLO:443, TSA, relay SMTP, custode immutabile approvato, API Microsoft e NinjaOne.
7. **Accessi al collettore stesso**: anche il login SSH al collettore è un accesso AdS. Instradare `sshd`, `sudo` e `su` locali nel ruleset `ads` verso `/srv/ads/127.0.0.1/`.

---

## 3. PKI minima per TLS 6514

- CA creata **fuori dal collettore** (postazione dell'amministratore non MSP); la chiave della CA non va sul collettore.
- Certificato server del collettore con SAN = FQDN **e** IP del collettore; validità 2 anni, rinnovo a calendario.
- Con `tls.verify_hostname on` oltre a `tls.verify on`, Fluent Bit confronta `Host` con il SAN: usare in `adsCollector` lo stesso nome o IP presente nel certificato. Il solo `tls.verify on` non esegue il confronto del nome, secondo la [documentazione TLS di Fluent Bit 4.1](https://docs.fluentbit.io/manual/4.1/administration/transport-security).
- File: `/etc/rsyslog.d/tls/{ca.pem,collector.pem,collector.key}`, chiave in modalità 0600.

---

## 4. Struttura del codice sul collettore

```
/opt/ads/bin/        script (in un repository git, versionati)
/etc/ads/            configurazione: sorgenti attese, elenco AdS, parametri TSA/SMTP/NAS
/var/lib/ads/        stato: manifest, .tsr, stato letture iLO/M365/NinjaOne
/srv/ads/<ip>/       log giornalieri (disco scsi1)
```

| Componente | Linguaggio | Timer systemd | Input → output |
|---|---|---|---|
| `ads-ilo.py` | Python | ogni ora | IEL via Redfish → `/srv/ads/<ip-ilo>/` (studio 4.1) |
| `ads-m365.py` | Python | ogni ora | Management Activity API, UPN in elenco AdS → `/srv/ads/m365/` |
| `ads-ninja.py` | Python | ogni giorno 00:05 | `/v2/activities` → `/srv/ads/ninjaone/` |
| `ads-gravityzone.py` | Python | ogni ora **[Non verificato]** cadenza | accessi alla console via API pubblica → `/srv/ads/gravityzone/` (studio, D9) |
| `ads-nightly.sh` | Bash | ogni giorno 00:15 | gzip, manifest a catena, marca TSA, copia WORM, mail (studio sez. 5) |
| `ads-silence.py` | Python | timer candidato alle 00:45, non installato | finestra retrospettiva fino a 213 giorni dalla data di attivazione per sorgente; report nel journal e uscita non zero per assenza del segnale; mail dopo scelta del relay |
| `ads-verify.sh` | Bash | manuale, mensile | ricalcolo catena + `openssl ts -verify` → verbale |

Regole comuni:
- Ogni script scrive le righe nello **stesso formato** del template `AdsLine`: ora di ricezione, sorgente, ora dichiarata, sistema, messaggio.
- Credenziali API (M365, NinjaOne, iLO) in `/etc/ads/secrets/` con modalità 0600, proprietario un utente di servizio `ads`. Gli script girano come `ads`, non come root.
- `ads-nightly.sh` chiude i giorni mancanti fino a **D-1**, in ordine e per un massimo di 213 giorni dopo l'ultimo manifest. Il servizio candidato richiede `/srv/ads` montato e lo script lo controlla prima di scrivere. Al primo avvio crea `GENESIS` su D-1: lo storico precedente richiede un bootstrap separato. Un errore ferma la catena sul giorno interessato; la mail di errore resta uno stadio futuro, vincolato al relay e a una prova di consegna.
- La cartella WORM si monta solo durante il job e si smonta alla fine.
- Pulizia dei file oltre 213 giorni solo dopo aver verificato che il file sia presente in WORM.

---

## 5. Proxmox host come sorgente

Sull'host (a cura di chi amministra Proxmox, con la configurazione fornita da voi):
```
apt install rsyslog rsyslog-gnutls
```
`/etc/rsyslog.d/90-ads.conf`:
```
module(load="imfile")
input(type="imfile" File="/var/log/pveproxy/access.log" Tag="pveproxy-access:")

if $programname == ["pvedaemon","pveproxy","sshd","sudo","su","login","pveproxy-access"] then {
  action(type="omfwd" target="<FQDN_COLLETTORE>" port="6514" protocol="tcp"
         StreamDriver="gtls" StreamDriverMode="1"
         StreamDriverAuthMode="x509/name" StreamDriverPermittedPeers="<FQDN_COLLETTORE>"
         queue.type="LinkedList" queue.filename="ads_fwd" queue.maxDiskSpace="500m"
         queue.saveOnShutdown="on" action.resumeRetryCount="-1")
}
```
- Coda su disco: se il collettore è giù, i messaggi restano sull'host e partono alla ripresa.
- CA del collettore in `/etc/rsyslog.d/tls/ca.pem` e `global(DefaultNetstreamDriverCAFile=...)`.
- **[Non verificato]** su PVE 9: che rsyslog riceva il journal senza configurazione aggiuntiva (imjournal o ForwardToSyslog di journald), che `pveproxy-access` venga filtrato da `$programname` con il tag impostato, e i nomi dei programmi nei messaggi di autenticazione. Controllare con `journalctl -t pvedaemon` dopo un login riuscito e uno fallito.
- Nota di dipendenza: il collettore gira **su** questo host. Se l'host si ferma, si fermano sia la sorgente che il collettore: nessuna perdita, perché non si generano eventi da registrare.

---

## 6. Collaudo (criteri di accettazione)

1. `qm guest exec <VMID> -- id` dall'host → **rifiutato**.
2. Da una sorgente non ammessa, 514/udp e 6514/tcp → **nessuna scrittura**.
3. Per ogni sorgente: un login riuscito e uno fallito di un AdS compaiono nel file del giorno con **i 5 campi** (o con la lacuna documentata nella matrice dello studio).
4. Collettore fermo per 1 ora: al riavvio arrivano gli eventi di Windows (bookmark + buffer) e di Proxmox (coda su disco). Gli eventi UDP di firewall e Nebula del periodo sono persi (rischio noto).
5. `ads-nightly.sh`: modificare un byte di un file di D-1 già catenato → `ads-verify.sh` **segnala la rottura**.
6. Una sorgente attesa senza file o senza heartbeat → report di `ads-silence.py`; mail ancora da integrare e collaudare.
7. Offset NTP di tutte le sorgenti < 1 s rispetto al collettore (`chronyc tracking` sul collettore; confronto degli orari di un evento noto).

---

## 7. Ordine di sviluppo

1. VM + Debian + nftables + chrony + TLS (0,5-1 gg-p)
2. rsyslog ricevente + accessi al collettore stesso
3. Firewall, NAS, Proxmox host → collaudo punti 2-3
4. iLO Remote Syslog → collaudo punti 3 e 7; `ads-ilo.py` resta alternativo se serve
5. `ads-nightly.sh` senza marca e senza WORM, poi aggiunta WORM, poi TSA quando scelta
6. `ads-silence.py`
7. Pilota Windows (2 postazioni + 1 server) con Fluent Bit → misura volumi → ridimensionamento `scsi1` e WORM
8. `ads-m365.py`, `ads-ninja.py`, `ads-gravityzone.py` (studio, D9)
9. Collaudo completo sezione 6 → estensione Windows dopo il parere privacy
10. Copertura di tutto l'inventario di rete: matrice per nodo, verifica di accessi locali, cloud e applicativi, esito motivato anche per nodi senza log autonomo; procedere per sorgente rispettando i blocchi della sezione 0 e i collaudi della sezione 6. Stato e ordine operativo in `docs/matrice-sorgenti-rete.md`.
11. Hardening della VM Debian del collettore dopo la raccolta delle sorgenti: rilevare la baseline reale, definire controlli di accesso, aggiornamenti, backup e monitoraggio, poi misurare anche i casi di accesso negato. Perimetro richiesto dall'utente il 08/10/2026; dettagli tecnici da progettare.
12. Piccola interfaccia web per consultare i log, raggiungibile solo dalla LAN e autenticata per il sysadmin autorizzato: definire identità, permessi di sola lettura, registrazione delle consultazioni e prova negativa degli accessi non autorizzati prima di aprire il servizio. Nessuna porta web è stata ancora configurata.

Stato al 08/10/2026: iLO Remote Syslog ha superato i punti 3 e 7 sul dispositivo reale. Lo smistamento iLO per IP sorgente e prefissi di accesso ha superato il test integrato Debian 13 ed è installato sul collettore: backup con SHA-256 verificato, candidata e configurazione completa accettate da rsyslog 8.2504.0, servizio riavviato e attivo. Il test tecnico post-cambio è arrivato nel file separato, mentre login Browser fallito, riuscito e logout sono nel file AdS; il test compare una volta nel primo e zero nel secondo. Per il file tecnico sono stati decisi 90 giorni locali: script e timer installati, timer attivo per le 03:00, service avviato sotto systemd con `status=ok` e zero eliminati. Restano altri canali iLO, affidabilità UDP e allarme esterno di capienza. Lo stadio locale di `ads-nightly.sh` e `ads-verify.sh` ha superato una prova funzionale in WSL, compresa l'alterazione di un byte del log D-1 richiesta dal punto 5; il suo timer e servizio non sono installati. Prima della loro attivazione va completato il trattamento delle connessioni SMB non AdS; D7 richiede ancora l'elenco AdS approvato. La prova su VM reale e l'ancoraggio esterno TSA/WORM restano aperti. Il nuovo mandato di copertura completa ha censito 57/57 nodi della topologia corrente, comprese due multifunzione individuali, con metodi e lacune in `docs/matrice-sorgenti-rete.md`; questa è una matrice, non 57 sorgenti in servizio.

Scadenze dello studio originario: punti 1-4 entro il 23/10/2026, il resto entro il 13/11/2026. Queste date non coprono il perimetro ampliato in seguito con QA, Seeweb, osservabilità, tre archivi, interfaccia e censimento completo. La stima residua condizionata e i gate correnti sono in `.claude/context/roadmap.md`.
