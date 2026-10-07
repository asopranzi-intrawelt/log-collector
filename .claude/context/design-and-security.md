---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - bin/**
  - config/**
last-verified-commit: b516232
---

# Design e sicurezza applicativa

> Stato letto dal codice e dalle configurazioni al commit `30b4c1c`. Le scelte di custodia della prova restano in `docs/modello-di-custodia.md` e ADR-010.

## Paradigmi di software design

`bin/adsparams.py` interpreta solo il sottoinsieme di YAML usato da `parametri.yaml` e segnala gli errori con la riga; `bin/ads-render.py` sostituisce i segnaposto nei due alberi di configurazione senza scrivere un albero parziale o sovrascrivere una destinazione esistente. `bin/ads-vm-command.py` genera un comando da eseguire manualmente, non opera sull'host. `bin/ads-pki.sh` emette CA e certificato sulla postazione amministrativa, mentre `bin/ads-bootstrap.sh` valida gli ingressi e installa la configurazione sulla VM. Questa separazione permette di provare generazione e configurazione in container prima dell'installazione reale.

Sul collettore rsyslog riceve da sorgenti UDP e TLS nello stesso ruleset, aggiunge ora di ricezione e IP osservato e salva i cinque campi di `AdsLine`. L'host Proxmox filtra in origine i soli messaggi di autenticazione e li inoltra con due code su disco, una per il journal e una per l'access log di `pveproxy`. I NAS e il firewall sono configurati nelle loro interfacce; i runbook documentano l'esito di ogni sorgente.

Nel componente iLO versionato il client Redfish separa recupero delle pagine, trasformazione delle voci e scrittura del checkpoint. L'intero giro è esclusivo per sorgente tramite lock sul collettore Linux. Il log viene sincronizzato prima del checkpoint atomico: un arresto fra i due può duplicare una riga, identificabile da `Id` e `Count`, ma non far avanzare lo stato oltre eventi mai scritti. Un giro fallito scrive `status=error` e termina con codice non zero; il controllo di silenzio futuro dovrà leggere l'esito, non soltanto vedere se esiste un file.

## Sicurezza applicativa

L'accesso SSH al collettore richiede una chiave personale, un indirizzo amministrativo ammesso da nftables e l'appartenenza a `ads-admin`; il login di root e l'autenticazione SSH con password sono disabilitati. `sudo` richiede la password locale dell'account personale. Il bootstrap controlla nomi e chiavi pubbliche prima di installare gli account e ricaricare SSH; ne verifica la sintassi e quella di sudoers e nftables. L'utente di servizio `ads` non ha shell di login né privilegi sudo. Il guest agent permette le sole RPC elencate in `allow-rpcs`, escludendo l'esecuzione di comandi e la gestione di file o credenziali dalla console dell'hypervisor.

`config/parametri.yaml` e gli alberi generati sotto `build/` sono privati e ignorati da git. La chiave della CA rimane sulla postazione amministrativa; sul collettore arrivano solo certificato della CA, certificato server e relativa chiave, installata 0600. I segreti applicativi appartengono a `/etc/ads/secrets/` sulla VM. Il bootstrap si ferma se nella cartella TLS trova `ca.key`. Lo script PKI rifiuta di sovrascrivere file esistenti e verifica il certificato emesso contro la CA.

La porta 6514/tcp accetta TLS ma il ricevente non autentica il certificato del mittente: `StreamDriver.AuthMode="anon"`; nftables limita gli IP alle reti configurate. L'host Proxmox verifica invece il nome del certificato del collettore con `x509/name` e conserva i messaggi in coda durante un'interruzione. La porta 514/udp serve gli apparati che non offrono TLS e trasporta i log in chiaro, senza conferma di consegna. Finché la LAN è un'unica subnet, nftables ammette i messaggi syslog da tutta quella rete: l'indirizzo del mittente non è da solo una prova di autenticità. I log sono scritti `root:ads`, file 0640 e directory 0750; la protezione contro alterazioni da parte degli amministratori del collettore è ancora una decisione aperta sulla custodia esterna della prova (ADR-010).

L'iLO reale ha licenza Advanced e Remote Syslog sulla porta 514/udp ha superato il collaudo degli accessi e degli orologi: eredita i limiti del trasporto in chiaro senza conferma di consegna descritti sopra, con file prodotti da rsyslog come `root:ads`. Il login fallito non riporta l'account tentato; i successi riportano l'account generico `administrator`. Il flusso contiene anche eventi tecnici non AdS e non va catenato indiscriminatamente come prova dei soli accessi. La pagina Security Dashboard del 2026-10-07 segnala certificato SSL predefinito, SNMPv1 attivo, Secure Boot e complessità password disabilitati e login iLO RBSU non richiesto; la correzione di questi rilievi appartiene al progetto di rete. Il client Redfish alternativo richiede sia una CA attendibile sia l'impronta SHA-256 del certificato presentato durante ogni handshake HTTPS. Non eredita proxy né segue redirect; rifiuta URI Redfish di origine diversa. La password è letta da un file privato con permessi 0600 sul collettore, il token della sessione non entra nei log e la sessione è cancellata a fine giro. Il sistema `ilo5` scriverebbe file propri come utente `ads`, in una directory della sorgente posseduta da `ads:ads`; la sicurezza e la compatibilità del certificato andrebbero provate prima dell'attivazione.

La catena locale preparata in `ads-nightly.sh` e `ads-verify.sh` rileva modifiche ai log dopo la chiusura D-1 confrontando origine, gzip e manifest concatenati. I manifest e i log restano però sulla stessa VM e un amministratore che possa riscriverli entrambi può creare una nuova catena coerente: l'indipendenza della prova dipende da TSA, WORM e impronta comunicata alla Direzione, che non sono ancora implementati. Il servizio systemd previsto scrive solo in `/var/lib/ads` e legge `/srv/ads` in sola lettura; il test dei permessi reali e l'installazione restano aperti.

## Diagrammi

Nessun diagramma di questi componenti è presente nel repository al commit verificato. Una tabella dei diagrammi sarà aggiunta quando esisteranno sorgente e derivato corrispondenti al codice.
