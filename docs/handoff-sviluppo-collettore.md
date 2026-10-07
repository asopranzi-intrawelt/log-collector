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
| | Copia WORM → **cartella WORM Compliance creata su NAS-HERO** e credenziale di scrittura |

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
   Uscita libera verso: NTP INRIM, iLO:443, TSA, relay SMTP, NAS-HERO (SMB), API Microsoft e NinjaOne.
7. **Accessi al collettore stesso**: anche il login SSH al collettore è un accesso AdS. Instradare `sshd`, `sudo` e `su` locali nel ruleset `ads` verso `/srv/ads/127.0.0.1/`.

---

## 3. PKI minima per TLS 6514

- CA creata **fuori dal collettore** (postazione dell'amministratore non MSP); la chiave della CA non va sul collettore.
- Certificato server del collettore con SAN = FQDN **e** IP del collettore; validità 2 anni, rinnovo a calendario.
- [Inferenza] Con `tls.verify on` Fluent Bit confronta il nome in `Host` con il SAN: usare in `adsCollector` lo stesso nome presente nel certificato.
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
| `ads-silence.sh` | Bash | ogni giorno 00:45 | sorgenti attese senza file/heartbeat → mail |
| `ads-verify.sh` | Bash | manuale, mensile | ricalcolo catena + `openssl ts -verify` → verbale |

Regole comuni:
- Ogni script scrive le righe nello **stesso formato** del template `AdsLine`: ora di ricezione, sorgente, ora dichiarata, sistema, messaggio.
- Credenziali API (M365, NinjaOne, iLO) in `/etc/ads/secrets/` con modalità 0600, proprietario un utente di servizio `ads`. Gli script girano come `ads`, non come root.
- `ads-nightly.sh` lavora **solo su D-1**, file già chiusi. Un errore in un passo fa fallire il job e manda la mail di errore: nessun passo viene saltato in silenzio.
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
6. Una sorgente attesa senza file o senza heartbeat → mail di `ads-silence.sh`.
7. Offset NTP di tutte le sorgenti < 1 s rispetto al collettore (`chronyc tracking` sul collettore; confronto degli orari di un evento noto).

---

## 7. Ordine di sviluppo

1. VM + Debian + nftables + chrony + TLS (0,5-1 gg-p)
2. rsyslog ricevente + accessi al collettore stesso
3. Firewall, NAS, Proxmox host → collaudo punti 2-3
4. iLO Remote Syslog → collaudo punti 3 e 7; `ads-ilo.py` resta alternativo se serve
5. `ads-nightly.sh` senza marca e senza WORM, poi aggiunta WORM, poi TSA quando scelta
6. `ads-silence.sh`
7. Pilota Windows (2 postazioni + 1 server) con Fluent Bit → misura volumi → ridimensionamento `scsi1` e WORM
8. `ads-m365.py`, `ads-ninja.py`, `ads-gravityzone.py` (studio, D9)
9. Collaudo completo sezione 6 → estensione Windows dopo il parere privacy

Stato al 07/10/2026: iLO Remote Syslog ha superato i punti 3 e 7 sul dispositivo reale. Lo smistamento iLO per IP sorgente e prefissi di accesso è preparato e ha superato il test integrato Debian 13, ma non è installato; conservazione e rotazione del file separato restano da definire. Lo stadio locale di `ads-nightly.sh` e `ads-verify.sh` ha superato una prova funzionale in WSL, compresa l'alterazione di un byte del log D-1 richiesta dal punto 5; timer e servizio non sono installati. Prima dell'attivazione va completato il trattamento delle connessioni SMB non AdS; D7 richiede ancora l'elenco AdS approvato. La prova su VM reale e l'ancoraggio esterno TSA/WORM restano aperti.

Scadenze dello studio: punti 1-4 entro il 23/10/2026, il resto entro il 13/11/2026.
