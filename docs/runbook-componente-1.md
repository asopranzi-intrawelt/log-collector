# Runbook del componente 1: VM, Debian, nftables, chrony, TLS

> Procedura eseguita, passo per passo, con l'esito di ciascun passo e la data. Documenta come il collettore è stato costruito davvero, non come si potrebbe costruire: le scelte sono motivate in `.claude/memory/decisions.md` e il riferimento funzionale è la sezione 1-3 di `docs/handoff-sviluppo-collettore.md`. I valori dell'ambiente non compaiono qui: ogni segnaposto tra parentesi angolari rimanda a una chiave di `config/parametri.yaml`, copia locale ignorata da git, perché il repository non deve contenere indirizzi né identificativi reali (`.claude/rules/anonymization.md`).

## Valori usati e loro origine

I valori Proxmox sono stati ricavati il 2026-09-30 dallo snapshot `output/proxmox-snapshot.json` del progetto `D:/network-design`, generato alle 07:30 dello stesso giorno; gli altri sono stati confermati dall'utente in sessione. Le schede di contesto di network-design sono anonimizzate con un prefisso segnaposto, quindi un valore di rete si prende dagli snapshot e mai dalle schede.

| Segnaposto | Chiave di parametri.yaml | Origine |
|---|---|---|
| `<VMID>` | `proxmox.vmid` | primo libero nella serie 2xx delle VM di servizio, confermato dall'utente |
| `<STORAGE>` | `proxmox.storage` | thin pool SERVIZI, che ospita le VM di servizio; il volume è su tre SSD (scheda #200 di network-design) |
| `<PVE>` | `proxmox.pve_version` | 8.3.4 dallo snapshot; il modello CPU e la combinazione q35, OVMF ed efidisk con chiavi pre-caricate sono già in uso su VM dello stesso nodo |
| `<BRIDGE>` | `proxmox.bridge` | `vmbr0`, non VLAN-aware, quindi senza tag (ADR-006) |
| `<SUBNET_LAN>` | `rete.subnet_lan` | CIDR di `vmbr0` nello snapshot, una /19 |
| `<GATEWAY>`, `<DNS>` | `rete.gateway`, `rete.dns` | il gateway è quello della serie dei server, lo stesso dell'host Proxmox, indicato dall'utente il 2026-10-01; il DHCP delle postazioni distribuisce un gateway diverso, il firewall, e la ragione dei due gateway va chiarita in network-design. Il DNS è quello dell'host (`/etc/resolv.conf`), pubblico, da rivedere quando i nomi interni saranno sul firewall (M25) |
| `<IP_COLLETTORE>` | `collettore.ip` | serie dei server, fuori dal pool DHCP della LAN; verificato libero il 2026-09-30 con ping senza risposta e vicino `Unreachable` |
| `<FQDN>` | `collettore.fqdn` | `ads-collector.int.intrawelt.com`, forma dei nomi interni di M25; da registrare nel DNS del firewall |
| `<ADMIN_IP>` | `rete.ip_admin_non_msp` | le postazioni fisse dei due amministratori non MSP (ADR-007) |
| `<UTENTI>` | `collettore.amministratori` | `asopranzi` e `tvezeni`, account personali (ADR-008) |

## 1. Sulla postazione dell'amministratore non MSP

La postazione è quella di Alessio Sopranzi, Windows 11. Il rendering produce l'albero di configurazione e si rifiuta se un valore manca; la PKI resta sulla postazione, e sul collettore vanno soltanto certificato, chiave del collettore e certificato della CA.

```powershell
cd "D:/log-collector"
python bin/ads-render.py --parametri config/parametri.yaml --sorgente config/collettore --destinazione build/pacchetto/collettore
python bin/ads-vm-command.py --parametri config/parametri.yaml --iso local:iso/debian-13.7.0-amd64-netinst.iso
```

```bash
bash bin/ads-pki.sh ca "$USERPROFILE/ads-pki"
bash bin/ads-pki.sh server "$USERPROFILE/ads-pki" <FQDN> <IP_COLLETTORE>
```

Esito al 2026-09-30. CA e certificato del collettore in `%USERPROFILE%\ads-pki\`, fuori dalla cartella del repository; certificato con CN e SAN su `<FQDN>` e `<IP_COLLETTORE>`, scadenza 29/09/2028, da rinnovare prima. Il pacchetto da portare sul collettore è `build/pacchetto/`, ignorato da git: l'albero generato, la cartella `tls/` con i soli `ca.pem`, `collector.pem` e `collector.key`, e la cartella `chiavi/` con le due chiavi pubbliche. Provato con `bash bin/ads-bootstrap.sh --prova build/pacchetto/collettore build/pacchetto/tls build/pacchetto/chiavi`.

Le chiavi SSH sono ed25519 senza passphrase, per scelta dell'utente, generate da ciascun amministratore sulla propria postazione come `%USERPROFILE%\.ssh\ads-collector_ed25519`. Su Windows PowerShell 5.1 la forma che funziona è la seguente; con `-N ""` lo strumento risponde `Too many arguments`, perché la stringa vuota non arriva intatta all'eseguibile.

```powershell
ssh-keygen -q -t ed25519 -N '""' -C "<utente>@ads-collector" -f "$env:USERPROFILE\.ssh\ads-collector_ed25519"
```

## 2. Sull'host Proxmox

Comandi eseguiti dall'utente come root nella shell del nodo, uno per uno, il 2026-10-01.

```bash
cd /var/lib/vz/template/iso
qm status <VMID>
wget -q --show-progress https://cdimage.debian.org/debian-cd/13.7.0/amd64/iso-cd/debian-13.7.0-amd64-netinst.iso
echo "<SHA512 da SHA512SUMS di cdimage.debian.org>  debian-13.7.0-amd64-netinst.iso" | sha512sum -c
qm create <VMID> ... (riga intera stampata da ads-vm-command.py)
qm config <VMID>
qm start <VMID>
```

Esito. `qm status` conferma il VMID libero; la ISO, 756 MB, risulta `OK` alla verifica SHA-512 contro l'impronta del file ufficiale `SHA512SUMS`, letto il 2026-09-30 (firma GPG di quel file non verificata). `qm create` crea tre volumi su `<STORAGE>`: efidisk da 4 MB, `scsi0` da 16 GB, `scsi1` da 60 GB con `backup=0`. `qm config` riporta tutti i parametri attesi, compreso `boot: order=scsi0;ide2`, che arriva intatto solo perché `ads-vm-command.py` lo stampa tra apici. Il comando dell'handoff non montava alcuna ISO: la VM sarebbe nata senza supporto di installazione, ed è il motivo dell'opzione `--iso`. All'avvio la console mostra il menu «Debian GNU/Linux UEFI Installer menu» della 13.7.0: la VM parte in UEFI dal CD.

## 3. Installazione di Debian dalla console

Si sceglie la voce `Install` del menu, cioè l'installer in modalità testo, che si usa solo da tastiera. La voce `Graphical install` funziona allo stesso modo, ma la VM è creata con `--tablet 0`, e senza il dispositivo tablet il puntatore del mouse nella console web di Proxmox non segue la posizione reale: in modalità testo il problema non esiste. Le voci di `Advanced options` (installazione esperta, ripristino, automatica) non servono.

| Schermata | Scelta | Motivo |
|---|---|---|
| Lingua, paese, tastiera, fuso orario | a scelta; tastiera italiana; fuso `Europe/Rome` | nell'installazione del 2026-10-01 il paese scelto ha portato al fuso «Central» degli Stati Uniti: corretto dal bootstrap, che imposta `Europe/Rome` |
| Rete | il 2026-10-01 la configurazione manuale non è stata applicata e la VM è partita in DHCP; con il desktop la rete è di NetworkManager, e l'indirizzo fisso si imposta dopo l'installazione, come root, con un comando `nmcli con mod "Wired connection 1"` per ciascuna proprietà (`ipv4.addresses <IP_COLLETTORE>/19`, `ipv4.gateway <GATEWAY>`, `ipv4.dns <DNS>`, `ipv4.method manual`, `ipv6.method disabled`) e poi `nmcli con up "Wired connection 1"`: in una riga sola il comando si è spezzato nel copia-incolla verso la console. Esito del 2026-10-01: indirizzo fisso e gateway attivi, `proto static`, nessun indirizzo IPv6. In alternativa, nell'installer: annullare il DHCP e configurare a mano: `<IP_COLLETTORE>`, maschera `255.255.224.0`, `<GATEWAY>`, `<DNS>` | indirizzo fisso, lo stesso scritto nel certificato e da configurare su ogni sorgente |
| Nome host e dominio | `ads-collector`, `int.intrawelt.com` | coincidono con `<FQDN>`; un primo tentativo con un nome diverso è stato corretto tornando indietro, perché il nome deve coincidere con certificato e DNS |
| Password di root | robusta, nota ai soli amministratori non MSP, copia in busta chiusa alla Direzione, conservata nel gestore di password aziendale; non lasciata vuota | handoff, sezione 2 punto 2; con root bloccato l'installer metterebbe il primo utente in `sudo`, mentre i privilegi passano da `ads-admin`, e la console di root resta la via di recupero |
| Primo utente | `asopranzi`, password temporanea | serve solo a copiare il pacchetto; il bootstrap lo inserisce in `ads-admin` e disattiva l'accesso SSH con password |
| Partizionamento | manuale; disco da 16 GB: partizione EFI da 512 MB e il resto ext4 su `/`; disco da 60 GB: una partizione ext4 su `/srv/ads` con `nodev`, `nosuid`, `noexec`; nessuno swap | handoff, sezione 2 punto 1; lo swap da 1 GB va su file dopo l'installazione |
| Mirror | Italia, `deb.debian.org`, nessun proxy HTTP, nessun supporto aggiuntivo | la rete esce senza proxy, come prova il download della ISO dall'host |
| Software | solo `SSH server` e `standard system utilities`; l'installer propone per difetto `Debian desktop environment` e `GNOME`, da togliere entrambi e da verificare su uno screenshot prima di `<Continue>`: il 2026-10-01 una spunta è rimasta e GNOME è stato installato, mantenuto per decisione dell'utente (ADR-012) | handoff, sezione 2 punto 1: nessun ambiente grafico, per risorse, superficie da aggiornare e accessi da registrare; il collettore si amministra in SSH o dalla console |
| Statistiche d'uso | `<No>` a popularity-contest | nessun invio di dati all'esterno senza necessità |

Esito: installazione completata il 2026-10-01, schermata «Installation complete». Dettaglio dei passi: Sul disco da 16 GB la partizione EFI risulta `#1 510.7 MB ESP`, preceduta da 1.0 MB lasciato libero dall'allineamento, che è normale, e seguita da `#2 16.7 GB ext4` su `/` con opzioni `defaults`. Sul disco da 60 GB una partizione `#1` da 64.4 GB ext4 su `/srv/ads` con `nodev,nosuid,noexec`; due trappole dell'installer da conoscere: il punto di montaggio proposto per difetto è `/home`, e nell'elenco c'è `/srv` ma non `/srv/ads`, che va scritto con `Enter manually`. All'avviso sullo swap mancante si risponde `<No>`, perché lo swap va su file; la scrittura sui dischi è confermata il 2026-10-01.

## 4. Dopo l'installazione

Raggiungibilità, 2026-10-01: dalla postazione dell'amministratore `Test-NetConnection <IP_COLLETTORE> -Port 22` riporta `TcpTestSucceeded True`. Copia del pacchetto dalla postazione, in PowerShell da `D:/log-collector`: `scp -r build/pacchetto bin/ads-bootstrap.sh asopranzi@<IP_COLLETTORE>:/tmp/`, eseguito il 2026-10-01: 13 file copiati. La chiave dell'host accettata al primo collegamento si confronta dalla console della VM con `ssh-keygen -l -f /etc/ssh/ssh_host_ed25519_key.pub`: il 2026-10-01 le due impronte coincidono. Bootstrap: incollata nella console web di Proxmox la riga lunga si spezza, quindi si lancia dalla postazione in PowerShell con `ssh -t asopranzi@<IP_COLLETTORE> "su - -c 'bash /tmp/ads-bootstrap.sh /tmp/pacchetto/collettore /tmp/pacchetto/tls /tmp/pacchetto/chiavi'"`; è sicuro perché l'account entra in `ads-admin` prima del reload di `sshd`, che comunque non chiude la sessione aperta. Esito del 2026-10-01: completato senza errori, 15 pacchetti installati, `systemd-timesyncd` sostituito da chrony, sudoers valido, nftables attivo, sessione SSH rimasta aperta. Verifica con la chiave: `ssh -i "$env:USERPROFILE\.ssh\ads-collector_ed25519" asopranzi@<IP_COLLETTORE> "id; timedatectl | grep 'Time zone'; chronyc sources"`, esito: accesso senza password, gruppo `ads-admin`, fuso `Europe/Rome`, INRIM a stratum 1 con scarto dell'ordine del millisecondo. Password locali: `ssh -t ... "sudo passwd <utente>"` con password temporanea, cambiata dal titolare con `passwd`; non `chage -d 0`, che con SSH solo a chiave può bloccare il login. Il bootstrap crea gli account senza nome completo, che si imposta a mano con `sudo chfn -f '<Nome Cognome>' <utente>` perché compaia nella schermata di login grafica; il primo utente lo ha già dall'installer.

Collaudo punto 1, 2026-10-01, sull'host: `qm set <VMID> --ide2 none,media=cdrom` stacca la ISO; `qm agent <VMID> ping` riesce senza uscita, controllo positivo che l'agent risponda; `qm guest exec <VMID> -- id` è rifiutato con «Command guest-exec has been disabled: the command is not allowed». Superato.

Firewall locale, 2026-10-01, dall'host Proxmox, che non è fra le postazioni ammesse: `timeout 3 bash -c '</dev/tcp/<IP_COLLETTORE>/22'` termina in timeout (esito 124, pacchetto scartato), lo stesso sulla 6514 risponde `Connection refused` (esito 1, porta ammessa dalla LAN, nessun processo in ascolto). Dalla postazione dell'amministratore la 22 risponde. Parte di rete del collaudo punto 2; la prova completa, nessuna scrittura da una sorgente non ammessa, si rifà con rsyslog attivo dopo il componente 2.

Swap, 2026-10-01, via SSH con `sudo`: `fallocate -l 1G /swapfile`, `chmod 600 /swapfile`, `mkswap /swapfile`, `swapon /swapfile`, riga `/swapfile none swap sw 0 0` in `/etc/fstab`. `free -h` dopo: swap 1.0 GiB; RAM 1.9 GiB totali con 546 MiB disponibili, per effetto del desktop mantenuto (ADR-012).

Con questo passo il componente 1 è completo.

Da completare: staccare la ISO dalla VM, copiare `build/pacchetto/` e `bin/ads-bootstrap.sh` sul collettore, eseguire il bootstrap dalla console come root, impostare le password locali dei due amministratori con scadenza immediata, creare lo swap file, e collaudare i punti 1, 2 e 7 della sezione 6 dell'handoff. Ogni passo si aggiunge qui con il comando e l'esito quando viene eseguito.
