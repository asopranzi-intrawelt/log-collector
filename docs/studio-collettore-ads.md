# Studio collettore log AdS - completamento

Integra il foglio "Collettore" (verifica documentale del 29/09/2026). Verifica aggiuntiva del 30/09/2026. Legenda: **[V]** verificato su fonte (elenco in fondo) · **[Non verificato]** da confermare nel pilota · **[Inferenza]** dedotto, non documentato.

---

## 1. Decisioni che completano o correggono il foglio

| # | Decisione | Motivo |
|---|---|---|
| D1 | **Fluent Bit solo su Windows** (postazioni e server). Linux, Proxmox e VM restano su rsyslog come da foglio. | Un solo agent aggiuntivo da mantenere; rsyslog copre già Linux. |
| D2 | **Filtro per elenco nominativo AdS**, non per euristica sui privilegi. L'elenco approvato dalla Direzione diventa un Custom Field NinjaOne e genera la query degli eventi. | Il filtro coincide con l'atto di nomina: niente log di utenti non AdS sulle postazioni (tema del parere privacy). |
| D3 | **Sostituire l'HMAC con marca temporale RFC 3161 di una TSA qualificata** sul manifest giornaliero. Resta l'invio dell'impronta alla Direzione. | Il foglio prevede una firma "con una chiave fuori dal collettore", ma la firma notturna gira sul collettore: la chiave deve esserci nel momento in cui firma, quindi chi controlla il collettore la può usare. La marca temporale non richiede chiavi locali e, se qualificata, gode della presunzione di esattezza di data e integrità (Reg. UE 910/2014, art. 41). |
| D4 | **Aggiungere iLO 5 dei server HP Gen10** (assente nel foglio). Licenza iLO Advanced assente (indicazione del 30/09/2026, da confermare sul campo "License Type" di iLO): **lettura oraria dell'iLO Event Log (IEL) via Redfish dal collettore**, dettaglio in sezione 4.1. Nessun acquisto di licenza. | [V] Remote Syslog richiede iLO Advanced (HPE licensing guide). [V] L'IEL è esposto in Redfish su `/redfish/v1/Managers/1/LogServices/IEL/Entries` e le voci di login hanno categoria Security/Administration (HPE iLO 5 Redfish docs). |
| D5 | **NTP unico: INRIM** (`ntp1.inrim.it`, `ntp2.inrim.it`) su collettore, firewall, NAS, Proxmox, iLO; Windows via script NinjaOne (`w32tm`). | Il foglio segnala il rischio NTP ma non prevede l'attività. |
| D6 | **Controllo di silenzio per sorgente**: ogni notte il collettore confronta l'elenco sorgenti attese con i file del giorno. Per Windows, dato che il filtro D2 produce giornate vuote legittime, serve un **heartbeat** dell'agent. | Senza heartbeat "nessun file" non distingue "nessun accesso AdS" da "agent fermo". |
| D7 | **QNAP: scartare sul collettore le righe dell'access log che non riguardano account AdS**, prima della scrittura su file. | [Inferenza] L'access log QNAP registra anche le connessioni ai file degli utenti ordinari: volume e tema lavoratori. Se QuLog Log Sender consente il filtro alla fonte, preferire quello **[Non verificato]**. |
| D8 | **Accessi alla console Nebula**: trattarli come sistema a sé, con log detenuto da Zyxel. Se senza Pro Pack non esiste export, documentarlo come rischio residuo nel documento AdS. | Gli switch Nebula si amministrano dal cloud: il syslog del dispositivo non vede il login al portale **[Inferenza]**. |
| D9 | **Aggiungere Bitdefender GravityZone** come sorgente (assente nel foglio), letta via API dal collettore come NinjaOne, senza ricevere eventi in push da Internet. Decisione dell'utente del 2026-10-01, da `docs/confronto-wazuh.md`. | Gli accessi alla console di GravityZone sono accessi di amministratori a un sistema che governa la sicurezza di tutte le postazioni. La sorgente compare nello schema architetturale dell'MSP e mancava qui. **[Non verificato]** quali eventi di accesso alla console esponga l'API pubblica e con quali campi. |

---

## 2. Matrice dei 5 campi per sorgente

| Sorgente | Utente | Evento | Sistema | IP sorgente | Data e ora | Stato |
|---|---|---|---|---|---|---|
| Windows (Fluent Bit) | `TargetUserName` | `EventID` + `LogonType` | `Computer` | `IpAddress` | `TimeCreated` | Campi Windows noti; nomi nel record Fluent Bit **[Non verificato]** fino alla prova con output `stdout`. `IpAddress` vale `-` o `127.0.0.1` negli accessi locali alla console: accettabile, va scritto nel documento. |
| Firewall USG FLEX 500 | nel testo del log admin | login/logout/fallito | IP firewall (`fromhost-ip`) | nel testo del log | ora di ricezione collettore | **[Non verificato]** presenza del login admin nel syslog (già segnalato nel foglio). |
| Switch/AP Nebula | - | - | - | - | - | Vedi D8. |
| QNAP (QuLog) | campo utente access log | tipo accesso | IP NAS | campo IP access log | ora evento + ora ricezione | Funzione [V] nel foglio; contenuto del messaggio **[Non verificato]**. |
| Proxmox | `user@realm` (pvedaemon), utente sshd | successful auth / authentication failure / sshd accepted | hostname | `rhost` (fallimenti), IP sshd; per i login web riusciti l'IP è in `/var/log/pveproxy/access.log` | ora journal | **[Non verificato]** formato esatto dei messaggi; il login web riuscito potrebbe richiedere l'unione di due righe. |
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
- Pacchetto **ZIP** da `packages.fluentbit.io`, versione fissata, verifica SHA-256 contro l'hash pubblicato, estrazione in `C:\Program Files\fluent-bit`.
- Servizio: `sc.exe create fluent-bit binpath= "\"C:\Program Files\fluent-bit\bin\fluent-bit.exe\" -c \"C:\Program Files\fluent-bit\conf\fluent-bit.conf\"" start= auto` come LocalSystem. [V] La lettura del canale Security richiede privilegi amministrativi (docs.fluentbit.io).
- **Versione**: deve includere `event_data_as_map`. [V] Il parametro è documentato nella pagina corrente del plugin e restituisce EventData come mappa con nomi di campo; non compare nella documentazione 4.0. **[Non verificato]** la versione minima: fissare l'ultima stabile al momento del pilota.
- Custom Fields NinjaOne: `adsAccounts` (testo, elenco separato da virgole), `adsCollector` (host:porta), certificato CA in campo secure. Lo script genera la query e la config dai campi e riavvia il servizio solo se il file cambia.

### 3.3 Configurazione (template)
```
[SERVICE]
    Flush          5
    Log_Level      info
    storage.path   C:\ProgramData\fluent-bit\storage
    storage.sync   full

[INPUT]
    Name                       winevtlog
    Tag                        ads.win
    Channels                   Security
    DB                         C:\ProgramData\fluent-bit\winevtlog.sqlite
    Event_Data_As_Map          true
    Event_Template_Cache_Size  256
    storage.type               filesystem
    Event_Query                <QueryList><Query Id="0" Path="Security"><Select Path="Security">*[System[(EventID=4624 or EventID=4625 or EventID=4634 or EventID=4647 or EventID=4648)]] and *[EventData[(Data[@Name='TargetUserName']='__ADS1__' or Data[@Name='TargetUserName']='__ADS2__')]]</Select><Select Path="Security">*[System[(EventID=1102 or EventID=4719 or EventID=4720 or EventID=4732 or EventID=4733)]]</Select></Query></QueryList>

[FILTER]
    Name    lua
    Match   ads.*
    script  C:\Program Files\fluent-bit\conf\ads.lua
    call    ads

[OUTPUT]
    Name                syslog
    Match               ads.*
    Host                ${ADS_COLLECTOR}
    Port                6514
    Mode                tls
    tls.verify          on
    tls.ca_file         C:\Program Files\fluent-bit\conf\ca.pem
    Syslog_Format       rfc5424
    Syslog_Hostname_Key Computer
    Syslog_Appname_Preset ads-win
    Syslog_Message_Key  message
    Retry_Limit         no_limits
    storage.total_limit_size 500M
```
- [V] `mode tls` abilita TLS senza `tls on`; `syslog_message_key` indica la chiave del messaggio; formato rfc5424 predefinito (docs.fluentbit.io, output Syslog).
- [V] Senza `DB` il plugin riparte dalla coda a ogni avvio: `DB` è obbligatorio per non perdere eventi durante i riavvii.
- Il secondo `Select` (log cancellato, criteri modificati, account creati, membri aggiunti/rimossi dai gruppi) non è filtrato per utente: sono eventi rari che rilevano la creazione di amministratori fuori elenco.
- **[Non verificato]** sensibilità a maiuscole/minuscole del confronto su `TargetUserName` nella query XPath: provare con un account scritto in modo diverso.
- **[Non verificato]** comportamento con account Entra ID sulle postazioni (formato del nome in `TargetUserName`).
- `ads.lua` (nomi dei campi da confermare con un giro `-o stdout` nel pilota):
```lua
function ads(tag, ts, r)
  local ed = r["EventData"] or {}
  r["message"] = string.format("user=%s event=%s logon_type=%s system=%s src_ip=%s time=%s",
    ed["TargetUserName"] or ed["SubjectUserName"] or "-",
    tostring(r["EventID"]), ed["LogonType"] or "-",
    r["Computer"] or "-", ed["IpAddress"] or "-", r["TimeCreated"] or "-")
  return 1, ts, r
end
```
- **Heartbeat (D6)**: un secondo input `dummy` con tag `ads.hb` e intervallo di 1 ora, inoltrato dallo stesso output. **[Non verificato]** nome del parametro di intervallo del plugin `dummy` sulla versione fissata.

### 3.4 Monitoraggio NinjaOne
Condition sul servizio `fluent-bit` non in esecuzione → alert + script di riavvio. Policy di aggiornamento: nuova versione prima sul gruppo pilota.

---

## 4. Collettore rsyslog (Debian)

```
module(load="imudp")
module(load="imtcp" StreamDriver.Name="gtls" StreamDriver.Mode="1" StreamDriver.AuthMode="anon")
global(DefaultNetstreamDriverCAFile="/etc/rsyslog.d/tls/ca.pem"
       DefaultNetstreamDriverCertFile="/etc/rsyslog.d/tls/collector.pem"
       DefaultNetstreamDriverKeyFile="/etc/rsyslog.d/tls/collector.key")

template(name="AdsFile" type="string" string="/srv/ads/%fromhost-ip%/%$year%-%$month%-%$day%.log")
template(name="AdsLine" type="string"
  string="%timegenerated:::date-rfc3339% %fromhost-ip% %timereported:::date-rfc3339% %hostname% %$!ads_msg:::drop-last-lf%\n")

ruleset(name="ads") {
  action(type="omfile" dynaFile="AdsFile" template="AdsLine"
         dirCreateMode="0750" fileCreateMode="0640")
}
input(type="imudp" port="514"  ruleset="ads")
input(type="imtcp" port="6514" ruleset="ads")
```
- Directory per **IP di provenienza** (`fromhost-ip`), non per hostname dichiarato: l'hostname nel messaggio lo sceglie il mittente.
- `%$year%-%$month%-%$day%` usa l'ora del collettore: il cambio file avviene a mezzanotte locale del collettore.
- TLS lato server con client anonimi; l'autenticazione del mittente è data dall'IP: **nftables** sul collettore accetta 514/udp e 6514/tcp solo dalle subnet gestite, SSH solo dall'IP di amministrazione della credenziale non MSP.
- Filtro D7 per QNAP: regola prima dell'`omfile` che scarta le righe dell'IP del NAS non contenenti un account dell'elenco AdS.
- [V] Sintassi dei parametri TLS verificata il 2026-10-01 in container `debian:trixie` con rsyslog 8.2504, la versione installata sul collettore: `rsyslogd -N1` accetta la configurazione, un messaggio inviato in TLS sulla 6514 arriva, uno inviato in TCP in chiaro sulla stessa porta viene scartato (`tests/debian13/verifica-config.sh`).
- Correzione del 2026-10-01, provata nello stesso container: con `%syslogtag%%msg%` i messaggi RFC 5424, il cui tag non finisce con `:` e il cui testo non comincia con uno spazio, uscivano con tag e messaggio fusi (`prova-udpmessaggio udp`); la forma `%msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%`, quella del formato tradizionale di rsyslog, separa i due campi in entrambi i formati. Seconda correzione, del 2026-10-02, che supera la prima: con il firewall Zyxel, che dopo il nome del sistema non scrive un nome di programma, rsyslog prende `src="<ip>:` per tag, e la regola dello spazio aggiunto se manca lo infilava dentro l'indirizzo (`src="192.0.2.73: 0"`), alterando la prova. Il campo messaggio è ora `$!ads_msg`, calcolato nel ruleset: per RFC 3164 tag e testo riattaccati esattamente, per RFC 5424 separati da uno spazio (`$protocol-version`). Inoltre ZLD scrive l'anno dopo l'ora, e senza il parser `pmrfc3164` con `detect.YearAfterTimestamp="on"` il campo sistema valeva `2026`.

### 4.1 iLO 5 senza licenza Advanced: raccolta via Redfish

Script Python sul collettore (`python3-requests`), eseguito ogni ora da un timer systemd:
1. **Account iLO dedicato** `ads-reader`, con il solo privilegio di login. **[Non verificato]** che il solo privilegio "Login" basti a leggere l'IEL: provarlo, e aggiungere il minimo privilegio necessario solo se la lettura fallisce.
2. **Sessione Redfish** (`POST /redfish/v1/SessionService/Sessions/`) e **logout esplicito** (`DELETE` della sessione) a fine giro. [Inferenza] Senza logout le sessioni restano aperte fino al timeout e iLO ne gestisce un numero limitato.
3. **Certificato iLO fissato**: impronta del certificato salvata sul collettore, niente `--insecure`.
4. `GET /redfish/v1/Managers/1/LogServices/IEL/Entries` e per ogni voce confronto con lo stato salvato (`Id`, `Count`):
   - **voce nuova** → una riga;
   - **`Count` aumentato** → una riga con l'incremento. L'IEL mostra un contatore delle ripetizioni dello stesso evento ([V] il campo `Count` compare nell'esempio HPE). **[Non verificato]** se esista un campo con l'ora dell'ultima ripetizione: se c'è, va registrato; se non c'è, delle ripetizioni intermedie si conosce il numero ma non l'ora esatta, salvo l'intervallo di lettura di un'ora. Questo limite va scritto nel documento AdS.
5. **Scarto delle voci generate dallo script stesso** (login REST di `ads-reader`), altrimenti ogni giro produce rumore.
6. Scrittura diretta in `/srv/ads/<ip-ilo>/AAAA-MM-GG.log` con lo stesso formato di riga del collettore (ora di lettura, IP iLO, `Created`, `Code`, `Message`). I file entrano nella catena notturna come le altre sorgenti.
7. **NTP su iLO**: impostare i server INRIM nelle impostazioni SNTP di iLO, altrimenti `Created` non è confrontabile con le altre sorgenti.
8. **Controllo di silenzio**: se lo script non riesce a leggere l'iLO (rete, credenziale, certificato), scrive una riga di errore e il controllo notturno la segnala.

Rete: il collettore deve raggiungere la porta 443 dell'interfaccia iLO; se l'iLO è su una rete di management separata, serve una regola dedicata sul firewall.

Verifica della licenza (1 minuto): pagina iLO **Information → Overview**, campo **License Type**, oppure `GET /redfish/v1/Managers/1/LicenseService/`. Se risultasse iLO Advanced, si passa al Remote Syslog verso 514/udp del collettore e lo script non serve.

---

## 5. Inalterabilità: catena notturna (sostituisce il punto HMAC)

Job alle 00:15 sul giorno D-1 (file chiusi):
1. `gzip -9` di ogni file del giorno.
2. `manifest-D.txt` = prima riga `prev: <sha256 di manifest-(D-1).txt>`, poi `sha256sum` di ogni `.log.gz`.
3. Marca temporale: `openssl ts -query -data manifest-D.txt -sha256 -cert -out D.tsq`, invio alla TSA (`Content-Type: application/timestamp-query`), salvataggio `D.tsr`.
4. Copia su cartella WORM Compliance del NAS-HERO di `.log.gz`, manifest e `.tsr`. **[Non verificato]** se la cartella WORM consente il rename finale che rsync esegue per default: provare, altrimenti `rsync --inplace`.
5. Mail alla casella della Direzione con impronta del manifest e numero di serie della marca.
6. Controllo di silenzio (D6) ed eliminazione dal collettore dei file oltre 213 giorni.

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
| iLO via Redfish (script, account, certificato, prova) | 0,5 | 0,75 |
| NTP su tutte le sorgenti | 0,25 | 0,25 |
| Criteri di controllo, dimensione log, filtro da Custom Field | 0,25 | 0,5 |
| Heartbeat e controllo di silenzio | 0,25 | 0,5 |
| Marca temporale al posto dell'HMAC (differenza) | 0 | 0,25 |
| **Totale aggiornato (foglio 7,5-9,5)** | **8,75** | **11,75** |

[Inferenza] Compatibile con il 13/11/2026 se sono dedicati almeno 2 gg-p a settimana da ottobre. Entro il 23/10 aggiungere NTP e iLO; entro il 13/11 marca temporale e heartbeat.

---

## 8. Punti da confermare prima di procedere

1. ~~Licenza iLO Advanced~~ → indicata come assente: scelta Redfish (D4). Resta da confermare il campo License Type.
2. Chi amministra **NAS-HERO** e la **casella della Direzione**: MSP o interno? (sezione 6)
3. Budget per una **TSA qualificata** (circa 365 marche/anno)? Il fornitore va scelto; prezzi e condizioni **[Non verificato]**.
4. Esistono **postazioni Linux** o solo Proxmox e VM? (D1)
5. Postazioni con **account Entra ID** o solo account locali?
6. Il sito Nebula ha il **Pro Pack**? (D8)

---

## Fonti consultate in questa verifica
- Garante privacy, provvedimento 27/11/2008 (mod. 25/06/2009): access log con completezza, inalterabilità, verificabilità dell'integrità; conservazione non inferiore a sei mesi; verifica almeno annuale dell'operato degli AdS.
- docs.fluentbit.io - input Windows Event logs (winevtlog), pagina corrente: `event_data_as_map`, `event_query` XPath/XML Query, `db`, privilegi per il canale Security.
- docs.fluentbit.io - output Syslog: modalità udp/tcp/tls/dtls, `syslog_message_key`, formato rfc5424.
- HPE, iLO standard and licensed features: Remote Syslog incluso in iLO Advanced, non in iLO Standard.
- HPE iLO 5 Redfish API docs (logging): IEL su `/redfish/v1/Managers/1/LogServices/IEL/Entries`, campi `Created`, `Message`, `Oem.Hpe.Categories`, `Code`, `Count`.
- Reg. UE 910/2014 (eIDAS), art. 41: effetti giuridici della validazione temporale elettronica qualificata.
