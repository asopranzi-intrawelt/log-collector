# Firewall Seeweb: configurazione osservata e percorso di raccolta

## Risposta del supporto sul ticket, letta il 20/10/2026

La risposta mostrata in una schermata acquisita il 20/10 rimanda a `Sistema -> File di log` per i registri di sistema, a `Firewall -> File di log` per quelli del firewall e a `Sistema -> Configurazione -> Backup` per confrontare la configurazione precedente. Chiede se la GUI debba essere raggiungibile solo da IP determinati e propone di studiare un aggiornamento con eventuale ripristino, contando undici passaggi fra serie principali fino alla release disponibile. Il portale indica il ticket come chiuso; mostra «6 giorni fa», senza una data assoluta del messaggio nella schermata. Originale e impronta sono nel livello privato.

Questo riscontro localizza menu e apre una discussione, ma non identifica righe di login GUI/SSH o modifiche con attore, né specifica retention, rotazione, export, API, Syslog, permessi, canale sul tunnel o buffer. Non attribuisce i servizi raggiungibili tramite la regola WAN 29 e non fornisce un elenco di IP da ammettere, un piano operativo di aggiornamento o il rinnovo del certificato GUI indicato scaduto. Prima di cambiare la regola serve una matrice concordata di interfacce, servizi e provenienze per cliente e provider, con accesso alternativo. La bozza di richiesta puntuale è privata e non inviata; nessuna configurazione è stata cambiata.

## Seguito tecnico e avanzamento da concordare, 20/10/2026

L'utente prepara un seguito al ticket chiuso: chiede a Seeweb l'inoltro Syslog remoto verso l'IP privato del collettore Debian, porta UDP 514, soltanto nel tunnel IPsec sede-cloud e senza apertura Internet. Prima dell'attivazione il provider deve confermare IP sorgente effettivo dell'appliance, selettori e regole IPsec nei due versi, assenza di NAT, categorie disponibili, esempi minimizzati di accesso GUI/SSH, retention locale e comportamento durante fermo VPN. Il collettore deve prima ammettere solo la sorgente verificata e separare i log tecnici OPNsense dall'archivio AdS; il target non è configurato e nessun test di ricezione Seeweb è avvenuto. L'IP di destinazione reale resta nel livello privato del collettore.

L'utente intende concordare con Seeweb un avanzamento della piattaforma OPNsense 21.1.5 e della sicurezza della GUI. Sono ancora da definire release bersaglio supportata, percorso di aggiornamento o sostituzione, backup ripristinabile, console alternativa, finestra, test, rollback, certificato e matrice degli IP amministrativi ammessi. La proposta del provider non è un piano approvato e non autorizza modifiche all'appliance; M31 e SWB-001/002/005 restano aperti.

## Riscontro successivo, proposta di aggiornamento e contratto 2014, 20/10/2026

Nello screenshot_111 il supporto chiede se debbano essere trasferiti tutti i log. La richiesta operativa riguarda invece una selezione di eventi: autenticazioni GUI/SSH e cambi con attore, più PF/IPsec necessari alla diagnosi; categorie, volume, retention e campioni sono ancora da concordare. Il target Debian e il trasporto sul tunnel non sono configurati o collaudati. Seeweb propone più sessioni di aggiornamento fino alla versione disponibile, salvataggio delle configurazioni e analisi delle anomalie, con prezzo comunicato nel ticket; la proposta non è accettata e non specifica release bersaglio, durata dei fermi, compatibilità, backup ripristinabile, console o prove post intervento. Accetta in linea di principio di concordare IP autorizzati e via alternativa prima di restringere la GUI.

Il contratto generale firmato il 26/09/2014 è una scansione di due pagine: p. 1 anagrafica, p. 2 condizioni. Gli artt. 1-2 rinviano alle schede dei singoli servizi; l'art. 4 contempla aggiornamenti hardware/software secondo circostanze contingenti e riferisce lo SLA 99,00-99,90% mensile alle sole risorse di calcolo. L'art. 5 attribuisce al cliente la responsabilità dei dati inseriti; l'art. 6 limita assistenza e manutenzione del fornitore al proprio sistema operativo e ai servizi di base, salvo diverso accordo espresso per altre attività. Nelle due pagine non compare un obbligo specifico di aggiornare OPNsense né una cadenza delle patch: la titolarità di questo firewall va verificata nelle schede del servizio, ordini e accordi successivi. Non usare lo SLA di calcolo come garanzia di sicurezza o disponibilità del firewall. Fonte privata: PDF originale fornito dall'utente, letto visivamente su entrambe le pagine; screenshot_111 conservato privatamente con impronte nel prompt di ripresa.

Il rischio tecnico di lasciare 21.1.5 è la mancanza delle correzioni successive e del supporto upstream della serie, con possibili compromissione e disservizio; l'esposizione effettiva richiede la verifica dei servizi raggiungibili, in particolare della regola WAN 29. Nessuna CVE o violazione contrattuale è attribuita per deduzione. [Release 21.1](https://docs.opnsense.org/releases/CE_21.1.html); [aggiornamenti e accesso console](https://docs.opnsense.org/manual/updates.html); [backup configurazione](https://docs.opnsense.org/manual/backups.html). L'appliance osservata usa UFS: non presupporre snapshot ZFS del guest; verificare un ripristino tramite backup della configurazione e/o snapshot dell'hypervisor. Prima di autorizzare il lavoro: scheda contrattuale vigente, responsabile delle patch, percorso di migrazione testato, finestra, console, piano di ritorno e prove di VPN, GroupShare, amministrazione, regole e log.

## Evidenza e perimetro, 14/10/2026

Letti visivamente tutti gli 81 originali screenshot_100.png-screenshot_180.png forniti dall'operatore, alla risoluzione originale 1920×911. Due ulteriori originali screenshot_196.png e screenshot_197.png completano la tabella WAN:83 schermate lette in totale. Ulteriori dieci screenshot_202.png-screenshot_211.png portano a 93 il totale letto e completano le 14 rotte e le sei pagine Activity; il nuovo manifesto è _notes/archivio-sessioni/seeweb-email/risultati/seeweb-firewall-system-20261014/manifest.json. Il supplemento WAN è in _notes/archivio-sessioni/seeweb-email/risultati/seeweb-firewall-wan-20261014/manifest.json; la serie 100-180 rimane nel suo manifesto originale. Gli originali, le impronte SHA-256 e una nota per ciascuna schermata sono conservati in _notes/archivio-sessioni/seeweb-email/risultati/seeweb-firewall-20261014/manifest.json e screens/ nei due progetti. Il manifesto distingue fonte, acquisizione e lettura; i valori reali rimangono privati. Nessuna interrogazione o modifica del firewall eseguita dall'agente.

Sono tutte le schermate ricevute, non un export completo della configurazione: le29 righe manuali WAN sono ora lette fino a fine tabella, ma le dieci automatiche rimangono ripiegate; le 14 rotte sono ora lette nelle 202/203, le regole automatiche sono ripiegate e alcuni pannelli hanno uno scorrimento interno. Restano non letti i dettagli di ogni regola, il contenuto dei file di logging, utenti/privilegi, bind/configurazione SSH, DNS e firmware. Il menu Sistema mostrato non espone Logging/Targets o utenti: si chiede al provider come ottenere quei dati, senza richiedere di nuovo la stessa ricognizione all'operatore. Le pagine Reset e Riavvia sono moduli di conferma; non provano che quelle azioni siano state eseguite. L'aspetto del menu non basta a determinare i privilegi dell'account.

La raccolta automatica Seeweb sulla VM del collettore resta non attiva. I log visualizzati qui sono registri locali del firewall. Il lettore dei report email resta un diverso canale locale, nell'archivio backup_outcomes.

## Identità, piattaforma e disponibilità

| Campo | Riscontro | Schermate |
|---|---|---|
| Apparato | OPNsense 21.1.5-amd64; hostname pubblico e LAN privata coincidono con SWB-02 e SWB-07 | 100, 115-116 |
| Sistema | FreeBSD 12.1-RELEASE-p16-HBSD; OpenSSL 1.1.1k del 25/03/2021 | 100 |
| Risorse | Intel Xeon virtuale, un core; RAM totale 2007 MB, 344 MB usati; filesystem UFS 1,8/27 GB | 100 |
| Tempi | Uptime 609 giorni; orologio GUI 14/10/2026 CEST; ultima configurazione dichiarata 04/02/2026 CET | 100 |
| Stato | Gateway WAN Online; LAN/WAN up, vtnet1/vtnet0, MTU 1500, media virtuale 10 Gb/s | 100, 115-116 |
| Servizi | Syslog-ng, syslogd, OpenSSH, strongSwan, NTP, PF, Web GUI e servizi di sistema mostrati attivi | 100, 113-114 |
| Alta disponibilità | Firewall di backup non accessibile o non configurato; nessuna interfaccia CARP definita rilevata; zero VIP | 109, 117-118 |
| Certificato GUI | Un solo certificato auto-firmato indicato in uso dalla Web GUI; scaduto il 23/11/2020; nessuna CA nella tabella GUI | 111-112 |

SWB-02 e SWB-07 diventano due ingressi della stessa sorgente, identificata privatamente con hostname e interfacce: non due firewall da contare due volte. La velocità della scheda virtuale non misura il contratto di banda o il throughput VPN. L'assenza di CA nella tabella non descrive il trust store del sistema operativo. La scadenza è quella del certificato indicato dalla GUI: il certificato effettivamente servito sulla connessione e il suo SAN non sono stati letti separatamente. Le righe CARP e gli identificativi pfsync osservati negli stati non dimostrano un cluster HA funzionante.

La [cronologia ufficiale OPNsense 21.1](https://docs.opnsense.org/releases/CE_21.1.html) data 21.1.5 al 21/04/2021 e la fine vita della serie al 27/07/2021. È quindi un firmware della serie fuori supporto upstream. Responsabilità del provider, eventuali backport e percorso di aggiornamento o sostituzione vanno confermati; non sono dedotti dal logo Seeweb. Il certificato scaduto e la piattaforma fuori supporto richiedono interventi progettati con accesso alternativo e ripristino verificato.

## Interfacce, rotte e vicini

| Elemento | Riscontro | Schermate |
|---|---|---|
| LAN | <RETE_CLOUD_LAN>/24, gateway <IP_FIREWALL_CLOUD_LAN>, scheda vtnet1; IPv6 link-local | 115 |
| WAN | <RETE_CLOUD_WAN>/26, <IP_FIREWALL_CLOUD_WAN>, gateway <IP_GATEWAY_PROVIDER>, scheda vtnet0; IPv6 link-local | 116 |
| Routing IPv4 visibile | Default al gateway provider; LAN/WAN connesse; loopback; aggregato privato di sede /16 instradato al gateway WAN | 110 |
| Politica IPsec | Selettori LAN cloud /24 ↔ aggregato sede /16; endpoint WAN cloud ↔ peer di sede | 157, 163 |
| Vicini ARP LAN | Firewall, hypervisor, due VM e un ulteriore vicino riconosciuto dalla GUI come NetApp | 119 |
| Vicini ARP WAN | Gateway del provider, firewall e due indirizzi riconosciuti come Juniper | 119 |
| NDP | Due indirizzi link-local delle interfacce del firewall | 120 |

La rotta dell'aggregato privato via WAN è osservata insieme a una VPN basata su policy e due SA ESP installate: da quella rotta non si deduce una fuga in chiaro. Restano da verificare il comportamento quando la SA manca, l'assenza di percorsi alternativi e gli effetti delle rotte e delle policy quando il tunnel è assente. La tabella di 14 rotte è ora tutta letta (202-203): sette IPv4 e sette IPv6. Le quattro righe prima mancanti sono link-local LAN e loopback; nessuna default IPv6 nella tabella mostrata. Questo non misura la raggiungibilità o la configurazione IPv6 dell'intera rete.

Il vicino <IP_STORAGE_CLOUD> ha due sessioni TCP stabilite sulla porta 445 da due postazioni della sede, presenti in pfTop e States Dump. L'OUI è attribuito a NetApp dalla GUI; è un riscontro di utilizzo compatibile con SMB, senza ispezione del protocollo applicativo. Proprietario, share, quota, dialetto, audit e copertura backup restano ignoti. Non si equipara automaticamente allo storage storico del Word, né si aggiunge un server aziendale alla topologia.

## Alias e NAT

Sono lette tutte le 12 righe degli alias, su due pagine. Tre alias aziendali abilitati rappresentano il server GroupShare, le provenienze aziendali e due provenienze pubbliche dei dipendenti. Un quarto alias di dipendenti è disabilitato e ha contenuto troncato: la sua lista non è stata ricostruita integralmente. Quattro alias del provider abilitati rappresentano accesso, antispam, monitoraggio e Munin. Completano il totale le quattro tabelle interne bogons, bogonsv6, sshlockout e virusprot, i cui membri dinamici non sono aperti. L'alias aziendale include tre reti /24 e un IP pubblico /32; l'alias provider di accesso include due reti IPv4 /25 e due IPv6 /64. Valori e nomi effettivi sono nel manifesto privato (124-125).

| NAT | Configurazione visibile | Schermate |
|---|---|---|
| Inoltro porte | Nessun inoltro personalizzato visibile; riga automatica anti-blocco LAN TCP 22/80/443, senza ridirezione | 126 |
| Uno-a-uno WAN | Tre mapping abilitati: <IP_PUBBLICO_ESXI> ↔ <IP_ESXI_CLOUD>, <IP_PUBBLICO_GROUPSHARE> ↔ <IP_GROUPSHARE_CLOUD>, <IP_PUBBLICO_RDP> ↔ <IP_RDP_CLOUD> | 127 |
| Uscita | Hybrid; zero regole manuali e due famiglie automatiche: ISAKMP porta 500 con static-port e SNAT ordinario verso WAN | 128, 152 |
| NPTv6 | Nessuna riga | 129 |
| Reflection | Port-forward, uno-a-uno e outbound automatico per reflection tutti non selezionati | 139 |

Un mapping uno-a-uno non apre da solo tutte le porte: vanno combinati filtro, servizio in ascolto e percorso effettivo. La schermata pubblica non contiene credenziali, indirizzi o liste reali.

## Filtri osservati e traffico effettivo

Le regole IPsec e LAN sono pass, in e quick. IPsec ha una regola IPv4 any→any con icona log blu. LAN ha due regole LAN net→any, IPv4 e IPv6, con icone log grigie. Floating e Loopback non mostrano regole manuali; restano rispettivamente 15 e una regola automatica ripiegate. Una automatica IPsec e una LAN sono ripiegate (130-133).

La serie iniziale 134 mostrava19 righe manuali. Le 196-197 completano la tabella: 29 manuali, 19 abilitate e 10 disabilitate; dieci automatiche rimangono ripiegate. Le righe sono pass/in/quick, con logging abilitato nelle 6 e 29 secondo icone e legenda; le altre icone log sono grigie. Conteggio e campo log riferiti alle regole manuali, non a tutto il ruleset.

| Ordine visibile WAN | Stato e provenienza | Destinazione e servizio |
|---|---|---|
| 1 | Abilitata, qualunque origine | Qualunque destinazione, ICMP IPv4; descrizione chiede di conservarla |
| 2-3 | Abilitate, alias accesso provider | Questo firewall e qualunque destinazione, qualsiasi protocollo IPv4 |
| 4 | Abilitata, alias monitoraggio provider | LAN net, qualsiasi protocollo IPv4 |
| 5 | Abilitata, alias antispam provider | LAN net TCP 25 |
| 6 | Abilitata, alias provenienze aziendali | Questo firewall, qualsiasi protocollo IPv4 |
| 7-8 | Abilitate, alias provenienze aziendali | LAN net TCP 80 e TCP 3389 |
| 9-10 | Abilitate, alias dipendenti e alias accesso provider | LAN net TCP 3389 |
| 11 | Abilitata, alias provenienze aziendali | LAN net TCP 443 |
| 12-13 | Disabilitate, qualunque origine | Questo firewall TCP 443 e 80 |
| 14-17 | Disabilitate, qualunque origine | LAN net TCP 21, 22, 25 e 587 |
| 18-19 | Abilitate, qualunque origine | Alias GroupShare TCP 80 e 8080; ultima descritta come Tomcat dall'esterno |
| 20-21 | Disabilitate, qualunque origine | LAN net TCP 110 (POP3) e 143 (IMAP) |
| 22 | Abilitata, qualunque origine | Alias GroupShare TCP 443 (HTTPS) |
| 23 | Abilitata, qualunque origine | LAN net TCP 902 |
| 24-25 | Disabilitate, qualunque origine | LAN net TCP 993 (IMAPS) e 995 (POP3S) |
| 26-27 | Abilitate, qualunque origine | Indirizzo WAN UDP 500 (ISAKMP) e 4500 (IPsec NAT-T) |
| 28 | Abilitata, qualunque origine | Qualunque destinazione, IPv4 ESP |
| 29 | Abilitata, qualunque origine; logging abilitato | Indirizzo WAN, qualsiasi protocollo IPv4 e porte qualsiasi |

Le righe dedicate a Questo firewall TCP 80/443 (12-13) restano disabilitate. La nuova lettura della 29 cambia la conclusione sul perimetro: esiste un pass/in/quick da qualsiasi origine verso l'indirizzo WAN per tutto IPv4, con log abilitato. Un pacchetto destinato a un servizio sull'indirizzo WAN, se non intercettato dalle regole precedenti, può essere ammesso da questa regola. Le regole disabilitate non agiscono come un divieto e la 29 non è limitata a IPsec, dato che UDP 500/4500 ed ESP hanno righe separate. Non è una prova dell'ascolto/raggiungibilità della GUI o SSH da Internet: bind, restrizioni del servizio, regole automatiche, filtri upstream e prova di connessione restano non verificati. Va comunque verificato per primo con Seeweb quali servizi siano realmente raggiungibili e perché esista quel permesso, preservando una via amministrativa alternativa. Nessuna disabilitazione proposta senza lettura delle dipendenze.

Il [manuale OPNsense sulle regole](https://docs.opnsense.org/manual/firewall.html) descrive il primo match per quick; la legenda della 197 conferma in, first match, abilitazione e log nella GUI osservata. Si applica qui solo quella semantica di base, senza attribuire alla 21.1.5 funzionalità delle release successive. Le descrizioni dei permessi provider chiedono di conservarli: proprietà del servizio e matrice dei flussi concordate prima di restringerli.

GroupShare ha ora tre permessi WAN da qualunque origine: 80, 8080 e 443. Il NAT e gli stati 153-154 provavano già connessioni HTTP 80 stabilite; la 22 aggiunge la configurazione HTTPS, non un handshake o un certificato validi osservati. La roadmap deve verificare l'ingresso 443, il comportamento 80, il backend 8080 e i vincoli applicativi prima di decidere reverse proxy o cambiamenti. Non assumere che HTTPS sia assente.

TCP 902 è consentito da qualunque origine verso LAN net, che comprende i tre mapping uno-a-uno. È un candidato di gestione VMware: [Broadcom documenta l'uso della 902 da ESXi](https://knowledge.broadcom.com/external/article/319455/tcp-and-udp-ports-required-to-access-esx.html), mentre la build e i processi del tenant non sono letti. Servizio in ascolto, host destinatario e raggiungibilità effettiva restano da attribuire; il permesso non è un login riuscito.

Le regole ampie di transito LAN/IPsec non separano management, VM e storage sullo stesso segmento cloud. Una conversazione sullo stesso livello 2 può non attraversare il firewall. La segmentazione cloud richiede anche verifica di VLAN, rete privata del provider, vSwitch dell'hypervisor e filtri dei guest: cambiare soltanto una regola LAN non garantisce isolamento fra quei sistemi.

## Altri parametri e servizi

| Famiglia | Campi letti | Schermate |
|---|---|---|
| Shaper | Nessuna pipe, coda o regola; stato senza righe | 135-138 |
| Avanzate | IPv6 consentito; bogon mensile; sticky connections e shared forwarding selezionati; ottimizzazione firewall normal e regole basic | 139-141 |
| Protezioni e percorso | Firewall non disabilitato; anti-blocco amministrativo conservato; bind state all'interfaccia non selezionato; bypass stesso-interfaccia, disable reply-to WAN e disable force gateway non selezionati | 140-141 |
| Parametri non valorizzati | Timeout source tracking/adattivi, limiti stati/frammenti/tabelle e intervallo alias vuoti nella form; runtime PF separatamente letto | 139-141, 148-149 |
| Alias URL | Verifica certificati HTTPS per download non selezionata; nessun alias URL configurato nelle 12 righe visibili | 141, 124-125 |
| Normalizzazione | Scrub non disabilitato; IP do-not-fragment e random-id non selezionati; zero scrub personalizzati | 142 |
| Scheduling | Nessuna pianificazione di regole | 143 |
| Limiti PF runtime | 200.000 stati e source nodes, 5.000 frammenti, 1.000.000 table entries; TCP established 86.400 s | 148-149 |
| DHCPv4 | Server LAN e WAN non abilitati, zero mapping statici visibili e zero lease. Pool LAN memorizzato estraneo alla subnet; residuo su servizio disabilitato, non guasto operativo dimostrato | 172-178 |
| DHCPv6 | Zero lease e prefissi delegati nella vista; server e RA non esaminati | 179 |

Il valore vuoto in una form non significa limite zero. Nella form avanzata state killing su guasto gateway e skip rules su gateway down non sono disabilitati/abilitati rispettivamente; il manifesto conserva il nome esatto dei checkbox negativi per evitare l'inversione del significato. I contatori accumulati delle interfacce, gli stati PF e i processi sono fotografie, non SLA o log delle azioni amministrative.

## VPN corrente

| Campo | Configurato o osservato | Schermate |
|---|---|---|
| IPsec | Abilitato, un tunnel Phase 1 e una Phase 2 | 157 |
| Phase 1 | IKEv1, aggressive, Mutual PSK, AES-128, SHA-1, DH2 | 157, 160 |
| Phase 2 | ESP IPv4 tunnel; LAN cloud /24 ↔ aggregato sede /16; AES-128/SHA-1 e PFS gruppo 2 a 1024 bit | 157, 163 |
| Stato effettivo | Due SA ESP installate, entrata/uscita, rijndael-cbc e hmac-sha1; contatori entrambi non zero | 162 |
| Continuità osservata | Log charon con DPD/DPD_ACK e INFORMATIONAL_V1 fra peer UDP 500 | 164-165 |
| Client mobili | Non abilitati; nessun pool IPsec | 158, 161 |
| Tabella PSK aggiuntive | Vuota; non prova assenza o rotazione della PSK del tunnel | 159 |
| OpenVPN | Nessun server/client/override o istanza definita; log vuoto | 166-171 |

Lifetimes, DPD completo, NAT-T, failover, PSK effettiva e data di rotazione non sono esposti nelle form lette. Il riscontro conferma e rende attuale M14/FW-006 della rete; SEC-023 sulla possibile PSK del 2018 resta aperto. La [RFC 9395](https://www.rfc-editor.org/rfc/rfc9395.html) depreca IKEv1: la progettazione deve coordinare IKEv2 e algoritmi correnti sui due peer, non copiare automaticamente il vecchio profilo. AES-128 da solo non è la ragione per dichiarare debole l'intero tunnel. Nessun cambio di VPN applicato.

## Menu Sistema e processi: riscontro conclusivo 202-211

Il menu visibile comprende Alta disponibilità, Instradamenti/Stato, Trust/Autorità/Certificati e Diagnostica/Activity/Servizi. Non compare una pagina per Logging/Targets, utenti/ruoli o firmware. È un limite osservato della sessione/account, non una prova dell'assenza dei registri o dell'esatta causa (privilegi, personalizzazione provider o configurazione). L'operatore aveva già fornito l'intera navigazione visibile: il passo successivo sul firewall è un riscontro del provider sulle funzionalità accessibili, non un altro giro sugli stessi menu.

Le sei pagine Activity (205-210) mostrano complessivamente 59 righe e 59 PID distinti; tutte lette, con il limite della paginazione dinamica. Fra i processi compaiono lighttpd con il file di configurazione Web GUI, sshd listener, filterlog/pflog0, charon con Syslog, ntpd, syslogd legacy e due processi syslog-ng con percorsi di configurazione diversi. Il contenuto dei file, l'eventuale inoltro remoto e i bind non sono stati letti. Il thread kernel audit non certifica un sistema di audit configurato o un evento umano; le righe root indicano l'account Unix dei processi. In 211 la riga login «Utenti e Gruppi» è un controllo di servizio, non l'inventario degli utenti. Dodici servizi verdi e nessuna azione eseguita sui pulsanti.

204 riconferma il medesimo certificato scaduto già descritto da 112, senza export o lettura indipendente della leaf servita. Le 202/203 completano 14 rotte e chiudono la sola lacuna di paginazione, senza prova del comportamento durante il guasto del tunnel.

Richiesta tecnica a Seeweb preparata e non inviata nel livello privato: registri amministrativi esistenti, campioni minimizzati, identità/origine/esito/tempi, retention, export/API/Syslog consentiti e permessi minimi; titolarità dell'intervento, canale protetto verso la sede e funzionamento senza VPN. Include verifica dei servizi dietro la regola WAN 29 e pianificazione di piattaforma/certificato con console e rollback. Nessun flusso viene configurato o dichiarato raccolto prima di campione e ricezione reali.

## Registri osservati e canali ancora da collaudare

| Categoria | Evidenza locale | Collocazione e lacuna |
|---|---|---|
| Traffico PF | Live View con pass/block, interfaccia, data, sorgente/destinazione, protocollo e etichetta; plain view filterlog con campi CSV | Archivio tecnico. Campione nativo, schema/versione, volume, rotazione e percorso Syslog da ottenere |
| VPN tecnica | 40 righe charon visibili su due pagine; DPD/ACK e traffico fra peer | Archivio tecnico. Export/download presente in UI, non eseguito; campioni errore/rekey/disconnessione ancora necessari |
| Autenticazioni GUI/SSH | Nome dell'utente autenticato nel menu e servizio OpenSSH attivo | Archivio AdS soltanto dopo evento reale con account, origine, esito e tempi. Registro amministrativo e copertura successi/fallimenti/logout non verificati |
| Cambi configurazione | Data ultima configurazione e processo config_changed visibili | Non sono un audit completo con attore e modifica. Registro e retention da leggere separatamente |
| Metriche | RRD abilitato, 11 grafici; picco LAN inpass, grafici traffico; Flow Totals No Data e Details vuoto | Stato tecnico. Vuoto nella vista selezionata non prova assenza globale di dati, traffico o autenticazioni |
| Stati connessione | Sessioni HTTP e TCP 445, NAT e contatori | Evidenza dei flussi per progettare; nessuna identità umana ricavata dalla porta o dallo stato |

Le etichette delle righe PF non si trasformano in login o identità del mittente: NAT e interfaccia d'uscita possono dare righe diverse dallo stesso flusso. La panoramica mostra 1.612 block e 1.365 pass (54/46%) senza finestra temporale esplicita: non è una misura del volume giornaliero o della percentuale di tutto il traffico.

La cronologia OPNsense citata documenta il target audit aggiunto in 21.1.6 e le opzioni Syslog-ng TLS aggiunte in 21.1.7, entrambe successive alla 21.1.5 osservata; in 21.1.9 cambia anche il formato filterlog. Non si prescrive per questa release la procedura TLS o audit delle versioni successive e non si deduce che la release vecchia non registri affatto gli accessi. Il [manuale corrente delle impostazioni di logging](https://docs.opnsense.org/manual/settingsmenu.html#logging) descrive destinazioni remote, selezione di applicazioni, livelli e facility: è un riferimento per il progetto e per la versione che sarà supportata, non una prova che i menu siano disponibili a questo utente.

Il canale di produzione verrà scelto dopo lettura della configurazione Logging/Targets o riscontro del provider, campione originale e prova di ricezione. IPsec verso la sede è osservato; indirizzo sorgente, filtri, protocollo di trasporto, buffering e comportamento senza tunnel non sono ancora verificati. Non si apre una porta Syslog sulla WAN pubblica per deduzione. Non si abilita il log di tutte le regole prima di misurare volume e selezionare gli eventi.

## Piano di ricognizione e ottimizzazione per network-design

| Ordine | Lavoro da preparare | Criterio di chiusura e dipendenze |
|---|---|---|
| 1 | Leggere regole automatiche e dipendenze della 29; WAN manuale e 14 rotte complete. Chiedere al provider registri/permessi/canali di logging, utenti/ruoli e titolarità Seeweb | Configurazione esportata o evidenze complete; accesso amministrativo alternativo, backup esportato e recupero concordati |
| 2 | Pianificare piattaforma supportata e certificato valido per la GUI | Provider/responsabile, finestre, compatibilità, restore e verifica client definiti; firmware nuovo e certificato poi misurati sull'apparato |
| 3 | M14: IKEv2 e parametri correnti, rotazione PSK e selettori aderenti ai flussi | Due peer coordinati; SMB, GroupShare, amministrazione, backup e log provati; failover e rollback verificati |
| 4 | Perimetro cloud: separare gestione, applicazioni pubblicate e storage; rivedere alias/provider, HTTP e 8080 | Matrice dei flussi comprensiva delle due sessioni TCP 445; verifica L2/vSwitch/provider/guest prima di scegliere VLAN, ACL, reverse proxy o subnet |
| 5 | ISO-30: flussi amministrativi e tecnici selezionati verso il collettore | Eventi reali distinti ricevuti una volta, tempi e origine leggibili, ritardo/retention/silenzio e indisponibilità del tunnel misurati |

M22 della LAN della sede e il perimetro cloud sono collegati dai flussi e dalla VPN, ma non si impone alla rete cloud lo stesso schema VLAN della sede. L'ottimizzazione non è ancora applicata. In particolare HTTP, manutenzione provider, accessi RDP e storage non vanno rimossi senza proprietario e prova delle dipendenze.

## Indice della lettura

| Schermate | Pagine lette |
|---|---|
| 100-107 | Dashboard, licenza, cambio password, health, flow totals/details/export e RRD |
| 108-116 | Traffico, HA, rotte, CA/certificati, processi, servizi e interfacce |
| 117-125 | VIP/CARP, ARP/NDP, form capture/probe/traceroute e due pagine alias |
| 126-134 | NAT, NPTv6 e regole Floating/IPsec/LAN/Loopback/WAN superiore |
| 135-143 | Shaper, impostazioni avanzate, normalizzazione e scheduling |
| 144-152 | Log PF, panoramica/grezzo e pfInfo info/memoria/timeout/interfacce/regole/NAT |
| 153-161 | pfTop, stati/reset/riepilogo, tunnel/client/PSK/status/lease IPsec |
| 162-170 | SAD/SPD, due pagine charon e configurazione/stato OpenVPN |
| 171-180 | Log OpenVPN, DHCPv4 LAN/WAN/lease, DHCPv6 lease e conferma riavvio |
| 196-197 | Tabella WAN manuale completa e legenda: 29 righe, 19 attive, 10 disabilitate; dieci automatiche ripiegate |
| 202-211 | Due pagine con tutte 14 rotte, certificato, sei pagine Activity con 59 righe/PID distinti e servizi; menu Sistema visibile ricognito |

Fonti ufficiali consultate il 14/10/2026: cronologia OPNsense 21.1, manuale logging corrente e RFC 9395. Dati del tenant misurati soltanto nelle schermate. Manifesto e PNG privati conservano i dettagli di ogni pagina; i riferimenti numerici rendono verificabile ciascun riscontro senza pubblicare gli originali.

Preparati gli allegati della richiesta al provider: sei PNG già analizzati (100, 211, 146, 164, 197 e 204), selezionati per versione, menu Sistema e servizi, log PF, log IPsec, ultima regola WAN e certificato GUI. Copie rinominate sul Desktop e nel livello privato dei due progetti, originali invariati e SHA-256 verificati dopo la copia. Inclusi elenco esplicativo e copia del testo del ticket attualmente presente nel collettore, comprese le integrazioni dell’operatore. Selezione interna basata sulle schermate: non sei nuove prove o nuovi eventi amministrativi. Invio e numero del ticket non ancora confermati; audit/export e raccolta automatica Seeweb restano da verificare. Nessuna modifica al firewall.

L’operatore segnala che il portale Seeweb accetta al massimo quattro allegati. La selezione per il primo invio è quindi ridotta alle schermate 100, 211, 197 e 204: versione, menu Sistema e servizi, regola WAN finale e certificato GUI. Copiati i quattro PNG originali nella sottocartella privata del Desktop «Da allegare - 4 file», con corrispondenza SHA-256 verificata; gli esempi filterlog/charon restano disponibili per eventuali integrazioni. Corrette le istruzioni del pacchetto precedente. Il limite è dichiarato dall’operatore, non misurato tramite invio automatico. Ticket ancora senza conferma di invio o numero; nessuna raccolta Seeweb attivata.

Il 14/10/2026 l’operatore riferisce che, dopo essere tornato indietro nel portale Seeweb, la UI non ha più consentito il caricamento degli allegati e decide di attendere la risposta del provider. Stato operativo: attesa risposta dichiarata dall’operatore; numero/ricevuta del ticket e allegati effettivamente associati non verificati. Le quattro schermate selezionate restano pronte per eventuale integrazione nello stesso ticket. Nessun nuovo tentativo nel portale richiesto, nessun ticket o messaggio inviato dall’agente e nessuna modifica al firewall. Audit amministrativo, export e raccolta automatica restano aperti; prossimo passo sul firewall: esaminare la risposta Seeweb quando disponibile.
