# Studio collettore log AdS - completamento

Integra il foglio "Collettore" (verifica documentale del 29/09/2026). Verifica aggiuntiva del 30/09/2026. Legenda: **[V]** verificato su fonte (elenco in fondo) · **[Non verificato]** da confermare nel pilota · **[Inferenza]** dedotto, non documentato.

---

## 1. Decisioni che completano o correggono il foglio

| # | Decisione | Motivo |
|---|---|---|
| D1 | **Fluent Bit solo su Windows** (postazioni e server). Linux, Proxmox e VM restano su rsyslog come da foglio. | Un solo agent aggiuntivo da mantenere; rsyslog copre già Linux. |
| D2 | **Filtro per elenco nominativo AdS**, non per euristica sui privilegi. L'elenco approvato dalla Direzione diventa un Custom Field NinjaOne e genera la query degli eventi. | Il filtro coincide con l'atto di nomina: niente log di utenti non AdS sulle postazioni (tema del parere privacy). |
| D3 | **Sostituire l'HMAC con marca temporale RFC 3161 di una TSA qualificata** sul manifest giornaliero. Resta l'invio dell'impronta alla Direzione. | Il foglio prevede una firma "con una chiave fuori dal collettore", ma la firma notturna gira sul collettore: la chiave deve esserci nel momento in cui firma, quindi chi controlla il collettore la può usare. La marca temporale non richiede chiavi locali e, se qualificata, gode della presunzione di esattezza di data e integrità (Reg. UE 910/2014, art. 41). |
| D4 | **Aggiungere iLO 5 dei server HP Gen10** (assente nel foglio). Il 07/10/2026 il DL380 Gen10 ha mostrato licenza iLO Advanced; Remote Syslog verso 514/udp ha consegnato login web riusciti e falliti. Dopo SNTP tre eventi iLO hanno scarto dalla ricezione sotto un secondo e `chronyc tracking` del collettore è normale. Il lettore Redfish preparato resta alternativo e non installato. | [V] Licenza, ricezione, login riusciti e falliti e collaudo temporale punti 3 e 7. [Limite] Il login fallito non contiene l’account tentato; l’account riuscito è generico e UDP non garantisce consegna. |
| D5 | **NTP unico: INRIM** (`ntp1.inrim.it`, `ntp2.inrim.it`) su collettore, firewall, NAS, Proxmox, iLO; Windows via script NinjaOne (`w32tm`). | Il foglio segnala il rischio NTP ma non prevede l'attività. |
| D6 | **Controllo di silenzio per sorgente**: ogni notte il collettore confronta l'elenco approvato delle sorgenti con il segnale scelto per ciascuna: evento giornaliero atteso oppure heartbeat esplicito. Per Windows filtrato da D2 serve un heartbeat dell'agent. Anche altre sorgenti che emettono solo a fronte di un accesso possono avere giornate vuote legittime: vanno classificate prima di usare l'assenza di file come allarme. | Un file assente segnala mancanza di dati, non dimostra da solo che il dispositivo o il trasporto siano guasti. Un heartbeat deve essere emesso e osservato in modo indipendente dagli accessi. |
| D7 | **QNAP: separare gli accessi AdS dagli altri accessi al NAS prima della scrittura su file.** Solo i primi entrano in `/srv/ads/`; gli altri restano registrati in un flusso distinto, con destinazione e politica proprie da definire. | Il 06/10/2026 le righe reali di INTRA3 hanno mostrato accessi SMB da una postazione non AdS che deve conservare l'accesso alla condivisione. L'utente ha chiesto di registrare anche questi accessi come altra categoria di log. L'elenco degli account AdS approvato è ancora bloccante per attribuire le righe al flusso giusto. |

Precisazione del 07/10: l'IT Manager dichiara che i PM hanno anche accesso amministrativo alla GUI di NAS HERO e NAS INTRA2, con ambito intenzionale limitato a determinate condivisioni; due persone hanno accesso alla sottocartella amministrativa di INTRA2. L'identità degli account e l'efficacia tecnica della limitazione della GUI non sono state verificate. D7 deve distinguere gli eventi QTS amministrativi dagli accessi SMB ai file: un account che può amministrare QTS è candidato al perimetro AdS anche se non è l'IT Manager, mentre il controllo completo sui file da solo non rende ogni operazione SMB un accesso AdS. La nomina individuale e l'elenco approvato non esistono ancora, quindi nessun filtro basato sui soli nomi o sul ruolo PM è pronto per l'installazione.
| D8 | **Accessi alla console Nebula NCC**: trattarli come sistema a sé, distinto dagli accessi locali agli switch e AP. `Recent logins` mostra i successi dell'account corrente, ma non è ancora dimostrato un export automatico centrale di successi e fallimenti di tutti gli amministratori; documentare la lacuna se resta tale. Gli accessi locali ai dispositivi seguono invece il componente 3 e la matrice delle sorgenti. | Il 08/10/2026 il 30HP ha registrato localmente tre fallimenti e un successo HTTPS; le quattro righe compaiono nell'Event log NCC come `AAA/authentication`, con un logout successivo. Il 09/10/2026 la OpenAPI ha restituito tutte le cinque righe con account, IP e ora. Il poller sul collettore non è ancora sviluppato; il Syslog site-wide è spento. Il login al portale NCC resta distinto dal login locale allo switch. Prove e ratio in `docs/runbook-componente-3-nebula.md` e ADR-016. |
| D9 | **Aggiungere Bitdefender GravityZone** come sorgente (assente nel foglio), letta via API dal collettore come NinjaOne, senza ricevere eventi in push da Internet. Decisione dell'utente del 2026-10-01, da `docs/confronto-wazuh.md`. | Gli accessi alla console di GravityZone sono accessi di amministratori a un sistema che governa la sicurezza di tutte le postazioni. La sorgente compare nello schema architetturale dell'MSP e mancava qui. **[Non verificato]** quali eventi di accesso alla console esponga l'API pubblica e con quali campi. |

---

## 2. Matrice dei 5 campi per sorgente

| Sorgente | Utente | Evento | Sistema | IP sorgente | Data e ora | Stato |
|---|---|---|---|---|---|---|
| Windows (Fluent Bit) | `TargetUserName`/`TargetDomainName` o `SubjectUserName`/`SubjectDomainName` secondo l'evento | `EventID` + `LogonType` | `Computer` | `IpAddress` | `TimeCreated` | Nomi e domini passati dal Lua sintetico; campo Security reale ancora **[Non verificato]**. `IpAddress` può essere `-` o loopback negli accessi locali alla console: va conservato come osservato. |
| Firewall USG FLEX 500 | nel testo del log admin | login/logout/fallito | IP firewall (`fromhost-ip`) | nel testo del log | ora di ricezione collettore | **[Non verificato]** presenza del login admin nel syslog (già segnalato nel foglio). |
| Switch Nebula locale (30HP) | `admin` nel successo; account tentato nel fallimento | login HTTPS riuscito/fallito, logout per timeout | identificativo switch nel log NCC e API | IP della postazione nel messaggio | ora UTC del dispositivo e ora di acquisizione del poller | [V] Cinque eventi reali in NCC e OpenAPI, con fixture anonimizzata e poller locale provato il 12/10. [Non verificato] ricezione nel collettore reale, retention, completezza e offline cloud. Gli altri switch/AP restano da collaudare; il login al portale NCC è D8 separato. |
| QNAP (QuLog) | campo utente access log | tipo accesso | IP NAS | campo IP access log | ora evento + ora ricezione | Funzione [V] nel foglio; contenuto del messaggio **[Non verificato]**. |
| Proxmox | `user@realm` (pvedaemon), utente sshd | successful auth / authentication failure / sshd accepted | hostname | `rhost` (fallimenti), IP sshd; per i login web riusciti l'IP è in `/var/log/pveproxy/access.log` | ora journal | **[Non verificato]** formato esatto dei messaggi; il login web riuscito potrebbe richiedere l'unione di due righe. |
| iLO 5 (Remote Syslog) | `administrator` nel successo; assente nel fallimento | `Browser login` / `Browser login failure` | IP e hostname iLO | IP postazione nel messaggio | ora UTC dichiarata + ricezione locale | [V] Sul dispositivo reale, due successi e un fallimento; fallimento senza account tentato, account riuscito generico. UDP senza garanzia di consegna. |
| iLO 5 (Redfish IEL) | nel campo `Message` (es. login REST di un utente) | `Message` + `Oem.Hpe.Code` | IP iLO | nel `Message` per i login da browser/SSH **[Non verificato]** | `Created` (UTC) | [V] struttura della voce. Attenzione: l'IEL **accorpa gli eventi ripetuti** in una voce con `Count` (sezione 4.1). |
| Microsoft 365 | `UserId` | `Operation` (UserLoggedIn, UserLoginFailed) | `Workload` | `ClientIP` | `CreationTime` (UTC) | Campi dello schema Management Activity **[Non verificato]** in questa sessione; filtrare sugli UPN dell'elenco AdS. |
| NinjaOne | `user` dell'activity | `type`/`activityType` | `deviceId` → nome dispositivo | **probabile assenza** | `activityTime` | **[Non verificato]** presenza dell'IP: se manca, il 4° campo non è coperto e va dichiarato nel documento. Gli accessi remoti dei tecnici alle postazioni tramite la sessione dell'utente collegato non generano un 4624 col nome del tecnico **[Inferenza]**: la loro traccia dipende solo da questo export. |
| GravityZone (API) | utente della console **[Non verificato]** | login alla console **[Non verificato]** | GravityZone | **[Non verificato]** | **[Non verificato]** | Aggiunta con D9; campi da verificare sulla documentazione dell'API pubblica Bitdefender e con una lettura di prova. |

Regola per il campo "Data e ora": il collettore scrive **sempre due tempi**, ricezione (`timegenerated`) e dichiarato dalla sorgente (`timereported`). I syslog RFC 3164 (firewall, Nebula) non portano anno e fuso: fa fede l'ora di ricezione.

---

## 3. Windows: Fluent Bit via NinjaOne

### 3.1 Prerequisiti sulla macchina (script NinjaOne, SYSTEM)
1. **Criteri di controllo** impostati con i GUID, non con i nomi (Windows in italiano localizza i nomi delle sottocategorie):
   ```
   auditpol /set /subcategory:"{0CCE9215-69AE-11D9-BED3-505054503030}" /success:enable /failure:enable   # Logon
   auditpol /set /subcategory:"{0CCE9216-69AE-11D9-BED3-505054503030}" /success:enable                   # Logoff
   auditpol /set /subcategory:"{0CCE921B-69AE-11D9-BED3-505054503030}" /success:enable                   # Special Logon
   auditpol /set /subcategory:"{0CCE9237-69AE-11D9-BED3-505054503030}" /success:enable                   # Security Group Management
   auditpol /set /subcategory:"{0CCE922F-69AE-11D9-BED3-505054503030}" /success:enable                   # Audit Policy Change
   ```
   **[Non verificato]** i GUID: confermarli sulla prima macchina con `auditpol /list /subcategory:* /v` prima di distribuire.
2. **Dimensione del Security log** portata a 256 MB (`wevtutil sl Security /ms:268435456`), così che un collettore fermo per qualche giorno non faccia perdere eventi per sovrascrittura prima che l'agent li rilegga dal bookmark.
3. **NTP**: `w32tm /config /manualpeerlist:"ntp1.inrim.it,0x8 ntp2.inrim.it,0x8" /syncfromflags:manual /update`.

### 3.2 Installazione
- Pacchetto **ZIP** da `packages.fluentbit.io`, versione fissata, verifica SHA-256 contro l'hash pubblicato, estrazione in `C:\Program Files\fluent-bit`. Il candidato verificato è 5.1.3; il bundle di configurazione si genera separatamente con `bin/ads-render-windows.py`.
- Il bundle compilato va in `C:\ProgramData\fluent-bit\conf\` insieme alla CA pubblica; il binario resta in `C:\Program Files\fluent-bit\bin\`. La registrazione come servizio LocalSystem è ancora da eseguire e collaudare sul pilota autorizzato: il canale Security richiede privilegi amministrativi ([documentazione Windows di Fluent Bit](https://docs.fluentbit.io/manual/installation/downloads/windows)).
- **Versione**: 5.1.3 include `event_data_as_map`, verificato con il binario Windows. La documentazione 4.1 non elenca il parametro: il campione Linux 4.1.1 non qualifica il mittente Windows.
- Distribuzione NinjaOne ancora da realizzare: il bundle generato localmente va trasferito solo sul pilota autorizzato, insieme alla CA pubblica. L'eventuale uso di Custom Fields e il riavvio condizionale del servizio non sono implementati.

### 3.3 Configurazione candidata del pilota

La fonte di configurazione è `config/windows-pilota/`, compilata da `bin/ads-render-windows.py` in un bundle privato per ciascun computer. Il generatore legge `collettore.fqdn` e `ads.elenco_approvato` da `config/parametri.yaml`. Ogni voce approvata ha forma `DOMINIO/utente`, usando i valori esatti dei campi `TargetDomainName`/`TargetUserName` o `SubjectDomainName`/`SubjectUserName` osservati sul pilota; se lo stesso account compare con più domini o grafie, ogni forma va valutata prima di inserirla. Il renderer rifiuta l'elenco vuoto, i nomi senza dominio, i duplicati e i caratteri che potrebbero alterare XPath. Il bundle contiene `fluent-bit.conf`, `ads.lua`, il controllo di coda e il preflight PowerShell; nessun nome reale degli AdS va nel repository. Il parametro `--computer-name` è il nome effettivo del pilota, usato anche nell'heartbeat. La destinazione non deve esistere e, se è dentro il repository, deve stare in `_notes/`.

```powershell
python bin/ads-render-windows.py --parametri config/parametri.yaml --computer-name <NOME_PILOTA> --destinazione _notes/windows-pilota/<NOME_PILOTA>
```

Il candidato è fissato a Fluent Bit Windows **5.1.3**, ZIP `fluent-bit-5.1.3-win64.zip`, SHA-256 `2a06c1a3c0ecddc970f50486a94a775b54fa28bf2ebe42c57a325511d33c0bb5`, verificato sul download ufficiale il 27/10. Le [istruzioni Windows e il checksum](https://docs.fluentbit.io/manual/installation/downloads/windows) sono del produttore; la [scheda `winevtlog`](https://docs.fluentbit.io/manual/data-pipeline/inputs/windows-event-log-winevtlog) documenta `event_data_as_map` e `event_template_cache_size` per la serie corrente. La vecchia prova Linux 4.1.1 riguarda solo il trasporto Syslog dell'heartbeat: la [scheda `winevtlog` 4.1](https://docs.fluentbit.io/manual/4.1/data-pipeline/inputs/windows-event-log-winevtlog) non elenca `event_data_as_map`, quindi 4.1.1 non è una versione qualificata per questo filtro Windows.

Prima del servizio, sul computer pilota con il bundle e la CA pubblica già collocati nei percorsi previsti, eseguire il [preflight statico](../bin/ads-windows-pilot-preflight.ps1): `powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File <BUNDLE>/ads-windows-pilot-preflight.ps1 -BundleDir <BUNDLE> -FluentBitExe <PERCORSO_FLUENT_BIT_EXE>`. Verifica identità del computer, file del bundle, CA valida con estensione CA, TLS e retry per ciascuno dei due output, coda, versione 5.1.3 e il [`--dry-run` documentato da Fluent Bit](https://docs.fluentbit.io/manual/4.2/administration/configuring-fluent-bit). La prova locale con il binario Windows effettivo è riuscita; il parser accetta sia LF sia CRLF e la cattura considera il banner su stderr anche quando il processo termina correttamente. `status=static_ok` significa solo che questi controlli statici sono passati. Il preflight non installa nulla né apre rete e non verifica comando del servizio, ACL, eventi Security, SAN del server in esercizio, consegna alla VM o avviso NinjaOne. Codice 3 e `phase` indicano un controllo fallito senza stampare percorsi o identità; non procedere al servizio con quel risultato.

Sul Windows locale il binario 5.1.3 ha superato `--dry-run` sul bundle generato con due identità fittizie di domini diversi. L'input `winevtlog` su Application ha restituito `EventID`, `Computer`, `TimeCreated`, `EventRecordID` ed `EventData` come mappa; il filtro Lua ha formato record sintetici con quegli stessi campi. Una query XML della stessa forma, con nome e dominio su entrambi i percorsi, è stata accettata da Event Log su Application. Quattro input `dummy` hanno inviato 4624, 4648, 4672 e heartbeat via TLS a un ricevitore locale: 740 byte RFC 5424 sono stati catturati e il test Debian ha smistato i tre eventi in AdS e il segnale in D6. Il messaggio conserva `user_domain` e, per credenziali diverse, `target_domain`. Con `Host` assente dal SAN la verifica del certificato ha impedito la consegna; disattivando solo `tls.verify_hostname` il controllo ha ricevuto i dati. Il canale Security non era leggibile dall'account di prova: **valori esatti dei campi e selezione su eventi reali, permessi, invio alla VM e recupero degli eventi Security dopo fermo richiedono il pilota con privilegi e lista approvati**. Non è stato creato un servizio Windows né modificato un audit policy.

La query prende gli eventi 4624/4625/4634/4647/4648 quando l'AdS coincide con `TargetDomainName` e `TargetUserName`, e 4648/4672 quando coincide con `SubjectDomainName` e `SubjectUserName`; gli eventi globali di controllo restano separati e non sono limitati all'elenco. Per 4648 il messaggio conserva l'attore in `user`/`user_domain` e, se diverso, l'account delle credenziali in `target_user`/`target_domain`. Per 4672 `user` è l'account cui sono stati assegnati i privilegi. I campi e il significato sono documentati da Microsoft per [4648](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4648), [4672](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4672) e [4720](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4720). Il confronto esatto sul dominio evita di includere automaticamente un account omonimo; bisogna però verificare con eventi Security reali che tutte le grafie attese siano coperte, altrimenti il filtro può perdere eventi.

La configurazione usa il bookmark `DB`, `Read_Existing_Events false`, filesystem buffer, TLS con verifica del nome e due output distinti (`ads.win` e `ads.hb`). Il primo avvio parte dalla coda del Security log: l'eventuale recupero storico va progettato con data e base giuridica esplicite. È stato tolto `storage.total_limit_size 500M`: secondo la [documentazione del buffering](https://docs.fluentbit.io/manual/data-pipeline/buffering), quando quel limite si raggiunge Fluent Bit scarta i chunk più vecchi. Spazio del buffer, crescita, saturazione e recupero degli eventi Security dopo fermo restano da misurare e allarmare sul pilota prima dell'esercizio. Il file CA va posto sul pilota in `C:/ProgramData/fluent-bit/conf/ca.pem` con accessi ristretti; il certificato server deve avere nel SAN il nome usato come `Host`.

Una prova sintetica con [prove_backlog.py](../tests/windows/prove_backlog.py) ha fermato il binario 5.1.3 mentre il ricevitore TLS locale era assente. Un chunk era presente sul disco; al riavvio, con lo stesso `storage.path`, il ricevitore ha osservato sia il record vecchio sia uno nuovo, distinguibili dai messaggi. Il replay locale ha richiesto 18,2 secondi nel giro misurato; otto secondi di attesa non bastavano. Questo verifica il percorso di backlog del motore su Windows con input `dummy`, non il bookmark `winevtlog`, il Security log, la capacità della coda, l'assenza di duplicati o la consegna alla VM. La [documentazione Fluent Bit sul backlog](https://docs.fluentbit.io/manual/administration/buffering-and-storage) descrive i chunk ripresi dopo un riavvio.

L'heartbeat (D6) usa un output RFC 5424 con `APP-NAME=ads-heartbeat`, distinto dagli accessi. Sul collettore solo il marker via TLS da un IP presente in `sorgenti.windows_pilota` entra in `/var/lib/ads/heartbeats/`; i marker rifiutati vanno al flusso tecnico. Il server TLS autentica il collettore verso Fluent Bit; il ricevitore rsyslog non autentica crittograficamente il client, quindi l'IP resta un vincolo di rete e non un'identità forte. Per le fixture Linux e Windows e i limiti delle prove vedi il runbook del componente 5.
### 3.4 Monitoraggio NinjaOne
La condition sul servizio `fluent-bit` fermo resta un allarme distinto. Il bundle include `ads-windows-queue-health.ps1`, controllo locale di sola lettura pensato per NinjaOne: richiede `-ConfigFile` puntato allo stesso `fluent-bit.conf` usato dal servizio e tre soglie positive `-MaxQueueBytes`, `-MinFreeBytes` e `-MaxOldestChunkMinutes`, da stabilire dopo la misura dei volumi del pilota. Legge `storage.path` dalla sezione `[SERVICE]` della configurazione, poi misura tutti i file di quella directory, lo spazio sul suo volume e la data di modifica del chunk `.flb` più vecchio. Senza `storage.path` valido fallisce: un'altra cartella preesistente non deve produrre un verde falso. Non apre rete, non legge il contenuto dei log e non riavvia il servizio. Codici di uscita: 0 sotto soglia, 2 soglia raggiunta, 3 misura impossibile; anche gli argomenti assenti danno subito 3 senza prompt interattivo. Directory assente, reparse point e volume indisponibile non diventano stato sano. L'età del file non è l'età dell'evento né una prova di consegna. La prova con Fluent Bit 5.1.3 fa segnalare al controllo il chunk fittizio durante il fermo del ricevitore; quattro prove PowerShell coprono anche la scelta della directory configurata. Prima di distribuire servono soglie fondate su capienza e carico reali, frequenza del job NinjaOne, recapito dell'allarme provato e verifica che `-ConfigFile` corrisponda alla configurazione del servizio. Policy di aggiornamento: nuova versione prima sul gruppo pilota.

---

## 4. Collettore rsyslog (Debian)

La configurazione candidata è il [template rsyslog](../config/collettore/etc/rsyslog.d/10-ads.conf.template); il renderer inserisce gli IP approvati. Il ruleset separa accessi AdS, eventi iLO e Seeweb tecnici e i marker D6. L'ingresso TCP 6514 ha nome `ads-tls`; la porta UDP 514 usa lo stesso parser ma non è ammessa per attestare il marker Windows. Installazione e configurazione reale si seguono dal runbook del componente 2.
- Directory per **IP di provenienza** (`fromhost-ip`), non per hostname dichiarato: l'hostname nel messaggio lo sceglie il mittente.
- `%$year%-%$month%-%$day%` usa l'ora del collettore: il cambio file avviene a mezzanotte locale del collettore.
- TLS lato server con client anonimi; la selezione del mittente si basa sull'IP, senza autenticarne l'identità crittografica: **nftables** sul collettore accetta 514/udp e 6514/tcp solo dalle subnet gestite, SSH solo dall'IP di amministrazione della credenziale non MSP.
- Smistamento D7 per QNAP: prima dell'`omfile`, distinguere con un elenco AdS approvato le righe dei loro accessi da quelle degli altri utenti del NAS. Scrivere le prime in `/srv/ads/` e le seconde in un flusso distinto, con politica di accesso e conservazione autonoma. Finché l'elenco e la destinazione non sono definiti, lo smistamento non è pronto per l'esercizio; le righe non AdS già arrivate in `/srv/ads/` vanno registrate come contaminazione, senza cancellazioni implicite.
- [V] Sintassi dei parametri TLS verificata il 2026-10-01 in container `debian:trixie` con rsyslog 8.2504, la versione installata sul collettore: `rsyslogd -N1` accetta la configurazione, un messaggio inviato in TLS sulla 6514 arriva, uno inviato in TCP in chiaro sulla stessa porta viene scartato (`tests/debian13/verifica-config.sh`).
- Correzione del 2026-10-01, provata nello stesso container: con `%syslogtag%%msg%` i messaggi RFC 5424, il cui tag non finisce con `:` e il cui testo non comincia con uno spazio, uscivano con tag e messaggio fusi (`prova-udpmessaggio udp`); la forma `%msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%`, quella del formato tradizionale di rsyslog, separa i due campi in entrambi i formati. Seconda correzione, del 2026-10-02, che supera la prima: con il firewall Zyxel, che dopo il nome del sistema non scrive un nome di programma, rsyslog prende `src="<ip>:` per tag, e la regola dello spazio aggiunto se manca lo infilava dentro l'indirizzo (`src="192.0.2.73: 0"`), alterando la prova. Il campo messaggio è ora `$!ads_msg`, calcolato nel ruleset: per RFC 3164 tag e testo riattaccati esattamente, per RFC 5424 separati da uno spazio (`$protocol-version`). Inoltre ZLD scrive l'anno dopo l'ora, e senza il parser `pmrfc3164` con `detect.YearAfterTimestamp="on"` il campo sistema valeva `2026`.

### 4.1 iLO 5: Remote Syslog in prova, Redfish come alternativa

La premessa del 30/09/2026, cioè che iLO Advanced fosse assente, è stata smentita dalla pagina Overview il 07/10/2026. Sul DL380 Gen10 con iLO 5 3.09, Remote Syslog è stato abilitato verso il collettore su UDP 514; modifica della configurazione e due messaggi di test sono arrivati nel file giornaliero della sorgente. I test iniziali mostravano iLO circa 4 minuti e 34 secondi indietro. Dopo `ntp1.inrim.it`, `ntp2.inrim.it`, fuso di Roma e due reset del solo controller iLO, tre eventi `iLO clock has been synchronized` hanno mostrato differenze fra ora dichiarata e ricevuta di 0,063083, 0,323815 e 0,283542 secondi. `chronyc tracking` del collettore il 07/10 indica `System time` +0,000148728 secondi e `Leap status: Normal`: il punto 7 è superato. Il trasporto UDP non conferma o ritrasmette i messaggi.

Il file iLO contiene due `Browser login` riusciti con account generico `administrator` e IP della postazione, ricevuti alle 12:45:24.778078 e 14:26:17.014716, e un `Browser login failure from: <IP_POSTAZIONE>` ricevuto alle 14:43:16.550058 dopo un solo tentativo controllato rifiutato dalla GUI. Le tre righe hanno i cinque campi `AdsLine`; lo scarto osservato sul fallimento è 0,550058 secondi. Il cambio di `Authentication Failure Logging` da `Every 3rd Failure` a `Every Failure` è stato salvato dalla GUI e registrato nel Syslog alle 14:32:58.889734; la persistenza del valore dopo riapertura non è stata verificata direttamente. Il fallimento Syslog non contiene l’account tentato, mentre l’account riuscito è generico: questi limiti di attribuzione vanno riportati nel documento AdS. Il flusso include anche eventi tecnici di sicurezza e rete, da separare prima della catena di conservazione degli accessi.

La lettura reale del 07/10/2026 ha contato 38 righe iLO (24 `iLO5`, 8 `Network`, 5 `SecurityConfiguration`, 1 `DenialofService`) e 11 testi distinti `iLO5`: tre prefissi Browser di accesso, otto testi di sincronizzazione, configurazione, allerta o test. È stato preparato un filtro rsyslog parametrico per IP sorgente che conserva i login e logout espliciti in `/srv/ads/` e scrive il resto in `/var/log/ads-ilo-other/` per revisione. Nessuna riga è scartata. Il test del renderer (15 casi), una prova locale WSL e la prova integrata Debian 13 con rsyslog 8.2504 sono passati; quest'ultima ha scritto tre accessi e tre altri eventi nei file attesi. Il primo tentativo aveva trovato un errore di sintassi per la lista iLO vuota, poi corretto. La regola non è installata: servono la politica del secondo flusso, la verifica degli altri canali di accesso iLO e il collaudo sul collettore. I file storici misti non vengono modificati. Il dettaglio tecnico e le fonti HPE sono nel runbook del componente 4.

L'08/10/2026 l'IT Manager ha scelto **90 giorni locali** per il secondo flusso iLO. I file sono giornalieri per sorgente, con permessi `root:root 0640` e directory `0750`; lo script di ritenzione e il timer alle 03:00 sono preparati ma non installati. Il job conserva il giorno corrente e gli 89 precedenti, fa prima una lettura `--dry-run`, elimina soltanto con `--apply` e scrive nel journal l'occupazione del filesystem con avviso dall'80%. Una prova WSL su dati fittizi è passata; non esiste ancora allarme esterno sulla capienza né revisione automatica dei prefissi non classificati. La decisione non cambia i 213 giorni previsti per i log AdS.

Il lettore Redfish seguente è già versionato ma non installato; diventa l'alternativa se Remote Syslog non offre la copertura necessaria. Non attivare contemporaneamente le due vie senza definire una deduplicazione.

Script Python sul collettore (`python3-requests`), eseguito ogni ora da un timer systemd:
1. **Account iLO dedicato** `ads-reader`, con il solo privilegio di login. **[Non verificato]** che il solo privilegio "Login" basti a leggere l'IEL: provarlo, e aggiungere il minimo privilegio necessario solo se la lettura fallisce.
2. **Sessione Redfish** (`POST /redfish/v1/SessionService/Sessions/`) e **logout esplicito** (`DELETE` della sessione) a fine giro. [Inferenza] Senza logout le sessioni restano aperte fino al timeout e iLO ne gestisce un numero limitato.
3. **Certificato iLO fissato**: impronta del certificato salvata sul collettore, niente `--insecure`.
4. `GET /redfish/v1/Managers/1/LogServices/IEL/Entries` e per ogni voce confronto con lo stato salvato (`Id`, `Count`):
   - **voce nuova** → una riga;
   - **`Count` aumentato** → una riga con l'incremento. L'IEL mostra un contatore delle ripetizioni dello stesso evento e l'esempio ufficiale iLO 5 espone `Oem.Hpe.Updated` ([V] sulla documentazione HPE; presenza sul dispositivo ancora da collaudare). Quando `Updated` è presente e valido si registra come ora dell'ultima ripetizione; se manca o ha il valore nullo HPE, si registra l'ora della lettura come limite noto e si dichiara ignota l'ora della ripetizione. Le ripetizioni intermedie non hanno orari individuali recuperabili dall'IEL. Questo limite va scritto nel documento AdS.
5. **Scarto delle voci generate dallo script stesso** (login REST di `ads-reader`), altrimenti ogni giro produce rumore.
6. Scrittura diretta in `/srv/ads/<ip-ilo>/AAAA-MM-GG.log` con lo stesso formato di riga del collettore (ora di lettura, IP iLO, `Created`, `Code`, `Message`). I file entrano nella catena notturna come le altre sorgenti.
7. **NTP su iLO**: impostare i server INRIM nelle impostazioni SNTP di iLO, altrimenti `Created` non è confrontabile con le altre sorgenti.
8. **Controllo di silenzio**: se lo script non riesce a leggere l'iLO (rete, credenziale, certificato), scrive una riga di errore e il controllo notturno la segnala.

Rete: il collettore deve raggiungere la porta 443 dell'interfaccia iLO; se l'iLO è su una rete di management separata, serve una regola dedicata sul firewall.

Licenza osservata: **iLO Advanced** nella pagina **Information → Overview** dello screenshot 102 del 07/10/2026. Il test Remote Syslog sul dispositivo decide se il lettore Redfish serva ancora.

---

## 5. Inalterabilità: catena notturna (sostituisce il punto HMAC)

Job alle 00:15 sul giorno D-1 (file chiusi):
1. `gzip -9` di ogni file del giorno.
2. `manifest-D.txt` = prima riga `prev: <sha256 di manifest-(D-1).txt>`, poi `sha256sum` di ogni `.log.gz`.
3. Marca temporale: `openssl ts -query -data manifest-D.txt -sha256 -cert -out D.tsq`, invio alla TSA (`Content-Type: application/timestamp-query`), salvataggio `D.tsr`.
4. Copia su cartella WORM Compliance del NAS-HERO di `.log.gz`, manifest e `.tsr`. **[Non verificato]** se la cartella WORM consente il rename finale che rsync esegue per default: provare, altrimenti `rsync --inplace`.
5. Mail alla casella della Direzione con impronta del manifest e numero di serie della marca.
6. Controllo di silenzio (D6) ed eliminazione dal collettore dei file oltre 213 giorni.

Stato al 07/10/2026: il solo stadio locale di compressione `gzip -n -9`, manifest concatenati e verifica degli hash è preparato in `bin/ads-nightly.sh` e `bin/ads-verify.sh`, con servizio e timer ancora non installati. `tests/test-nightly.sh` ha superato in WSL una prova su due giorni fittizi: seconda esecuzione idempotente, un byte alterato nel log D-1 rilevato, legame del manifest precedente alterato rilevato. Una copia mutata del verificatore senza confronto fra archivio e log passa sul byte alterato, confermando che la prova esercita proprio quel controllo. Lo stadio locale non è ancora una prova indipendente: mancano marca TSA, WORM e impronta alla Direzione. Lo smistamento iLO è ora preparato e provato localmente, ma non installato; la separazione delle connessioni SMB non AdS già presenti in `/srv/ads/` resta aperta e D7 è bloccato dall'elenco AdS approvato. Dettaglio in `docs/runbook-componente-5-catena.md`.

Verifica mensile con verbale: ricalcolo della catena dall'inizio, `openssl ts -verify -in D.tsr -data manifest-D.txt -CAfile <CA TSA>` su tutti i giorni, confronto collettore / WORM / mail.

Il collettore deve poter raggiungere la TSA in uscita (HTTP/HTTPS): regola da aprire sul firewall.

---

## 6. Rischi da aggiungere al foglio

- **Hypervisor gestito dall'MSP.** La credenziale distinta sulla VM non protegge dall'amministratore di Proxmox, che può leggere o modificare il disco della VM **[Inferenza]**. Mitigazione: i dati fino a D-1 sono resi verificabili da WORM + marca temporale + mail. Il giorno in corso resta esposto: dichiararlo.
- **Chi amministra NAS-HERO e la casella della Direzione.** Se è l'MSP, può distruggere il pool WORM (limite già nel foglio) e cancellare le mail. La marca temporale qualificata è l'unico ancoraggio fuori dal suo controllo.
- **Security log sovrascritto** prima della rilettura dell'agent se il collettore resta fermo oltre la capienza del log (mitigato dal punto 3.1.2 e dal buffer su disco).
- **Filtro per elenco**: un nuovo AdS non inserito nel Custom Field non viene registrato sulle postazioni. Procedura: l'aggiornamento dell'elenco AdS e del Custom Field è un unico passo.
- **Accessi remoti MSP via NinjaOne**: la loro traccia dipende solo dall'export dell'activity log (sezione 2).

---

## 7. Stima e calendario aggiornati

| Voce aggiunta | gg-p min | gg-p max |
|---|---|---|
| iLO via Remote Syslog (configurazione e prova) | 0,25 | 0,5 |
| NTP su tutte le sorgenti | 0,25 | 0,25 |
| Criteri di controllo, dimensione log, filtro da Custom Field | 0,25 | 0,5 |
| Heartbeat e controllo di silenzio | 0,25 | 0,5 |
| Marca temporale al posto dell'HMAC (differenza) | 0 | 0,25 |
| **Totale aggiornato (foglio 7,5-9,5)** | **8,5** | **11,5** |

[Inferenza] Compatibile con il 13/11/2026 se sono dedicati almeno 2 gg-p a settimana da ottobre. Entro il 23/10 aggiungere NTP e iLO; entro il 13/11 marca temporale e heartbeat.

---

## 8. Punti da confermare prima di procedere

1. **D4: collaudi iLO 5 punti 3 e 7 superati** sul dispositivo reale il 07/10/2026: licenza Advanced, login web riusciti e fallito nel file `AdsLine`, tre eventi NTP coerenti e `chronyc tracking` normale. Restano aperti il trattamento degli eventi tecnici non AdS, l’attribuzione personale dell’account generico e la perdita possibile di datagrammi UDP.
2. Chi amministra **NAS-HERO** e la **casella della Direzione**: MSP o interno? (sezione 6)
3. Budget per una **TSA qualificata** (circa 365 marche/anno)? Il fornitore va scelto; prezzi e condizioni **[Non verificato]**.
4. Esistono **postazioni Linux** o solo Proxmox e VM? (D1)
5. Postazioni con **account Entra ID** o solo account locali?
6. Il sito Nebula ha il **Pro Pack**? (D8)

---

## Fonti consultate in questa verifica
- Garante privacy, provvedimento 27/11/2008 (mod. 25/06/2009): access log con completezza, inalterabilità, verificabilità dell'integrità; conservazione non inferiore a sei mesi; verifica almeno annuale dell'operato degli AdS.
- docs.fluentbit.io - input Windows Event logs (winevtlog), pagina corrente: `event_data_as_map`, `event_query` XPath/XML Query, `db`, privilegi per il canale Security.
- [Fluent Bit 4.1, output Syslog](https://docs.fluentbit.io/manual/4.1/data-pipeline/outputs/syslog): `mode` tcp/udp, TLS separato, `syslog_message_key`, formato RFC 5424.
- [Fluent Bit 4.1, input Dummy](https://docs.fluentbit.io/manual/4.1/data-pipeline/inputs/dummy): `Interval_sec` e `Dummy`.
- [HPE iLO 5 Licensing Guide](https://support.hpe.com/hpesc/public/docDisplay?docId=sd00001039en_us&docLocale=en_US): matrice delle funzioni per licenza, da confrontare con `License Type` sul dispositivo prima di scegliere definitivamente fra Remote Syslog e polling.
- [HPE iLO 5 User Guide, iLO details](https://support.hpe.com/hpesc/public/docDisplay?docId=a00105236en_us&docLocale=en_US&page=GUID-33F615FB-B545-4045-9EBF-20569EB01EBF.html): `License Type` e versione firmware in Overview, confrontati con lo screenshot 102 il 07/10/2026.
- [HPE iLO 5 User Guide, Remote syslog options](https://support.hpe.com/hpesc/public/docDisplay?docId=a00105236en_us&docLocale=en_US&page=GUID-D7147C7F-2016-0901-06D0-000000001272.html): server e porta configurabili; porta predefinita 514.
- [HPE iLO 5 User Guide, Configuring iLO SNTP settings](https://support.hpe.com/hpesc/public/docDisplay?docId=a00105236en_us&docLocale=en_US&page=GUID-D7147C7F-2016-0901-06D0-0000000010B0.html): scelta tra server DHCP e manuali, fuso orario e possibile reset del controller dopo Apply.
- [HPE iLO 5 Redfish API Reference](https://hewlettpackard.github.io/ilo-rest-api-docs/ilo5/), sezione IEL verificata il 06/10/2026: percorso `/redfish/v1/Managers/1/LogServices/IEL/Entries/`, campi `Id`, `Created`, `Message`, `Oem.Hpe.Categories`, `Code`, `Count` e `Updated` nell'esempio pubblicato; presenza e valori effettivi restano da collaudare sul dispositivo.
- [HPE Redfish authentication and sessions](https://servermanagementportal.ext.hpe.com/docs/concepts/redfishauthentication), verificata il 06/10/2026: il token arriva in `X-Auth-Token` e la `Location` identifica la sessione da cancellare con `DELETE`.
- Reg. UE 910/2014 (eIDAS), art. 41: effetti giuridici della validazione temporale elettronica qualificata.
