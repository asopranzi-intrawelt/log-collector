# Runbook del pilota Linux e GPU

## Ripristino NVIDIA dopo migrazione Ubuntu, 15/10/2026

Riscontro tecnico del 15/10/2026 dall'host fisico pilota: Ubuntu 26.04.1 LTS e kernel 7.0.0-38-generic. I log di migrazione mostrano aggiornamento e successiva rimozione di nvidia-utils-595 e libnvidia-compute-595; ripristinati entrambi alla versione 595.99.02-0ubuntu0.26.04.1, coerente con il modulo caricato. Verifica indipendente SSH: nvidia-smi identifica RTX 5060 Ti con 16.311 MiB, libcuda/NVML caricabili, cuInit=0 e un dispositivo CUDA. Ollama, Veeam e Netdata active/running; nessun comando di reboot o riavvio servizi richiesto. Nessuna inferenza LLM: uso GPU da Ollama ancora da verificare. Le corrispondenze NVIDIA nell'API Netdata sono soltanto stati di unità systemd, non chart di utilizzo/VRAM/temperatura: collaudo del collector ancora aperto. Veeam nosnap 6.3.2.1501 presente; job riuscito/restore non attestati da questa verifica. Restano invariati configurazione Netdata, flussi al collettore, gate AdS e lavoro già aperto.

Fonte: installazione interattiva autorizzata dall'operatore, poi letture indipendenti via SSH alle 13:53:37 UTC. Il modulo kernel già presente non sostituiva le librerie user-space: libcuda serve al calcolo GPU dal programma; NVML e nvidia-smi espongono stato/risorse. Ripristino limitato ai due pacchetti con versione fissata e simulazione senza rimozioni. I dati della baseline precedente, più avanti nel runbook, restano una fotografia precedente.

Prova privata: [nvidia-post-upgrade-20261015.json](../_notes/linux-observability-20261015/pilot/nvidia-post-upgrade-20261015.json), SHA-256 6924038e39f88a8b302fb611897cb435920d39ae4461366448ebc2aac977db06. Contiene i riferimenti e gli hash delle letture sorgenti. Nessun indirizzo, account o destinazione NAS reale nel testo pubblico. Il controllo CUDA verifica caricamento/inizializzazione e presenza del dispositivo, non accuratezza, prestazioni, energia o inferenza Ollama.

Riferimenti: [installazione NVIDIA su Ubuntu](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/), [CUDA Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/), [NVML](https://docs.nvidia.com/deploy/nvml-api/nvml-api-reference.html), [collector NVIDIA Netdata](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/nvidia-gpu).

Il riconoscimento nel daemon e i campioni GPU sono verificati il 16/10, come nell’ultima sezione. Il ripristino delle librerie del 15/10 rimane una prova distinta; impatto sostenuto e raccolta centrale restano aperti.

Stato al 15/10/2026: Netdata 2.12.1 installato dall’operatore sul fisico Ollama, dopo il recupero del bundle. Script e archivio verificati, servizio avviato e active/running, abilitazione al boot già osservata, listener loopback verificato e opt-out presente. Export CPU/RAM presente e ACLK non claimed/non online; GPU locale verificata nel daemon il 16/10 (1/3/1); impatto a regime ancora da verificare; nessun invio di eventi al collettore aggiunto. Il piano generale è in [Osservabilità Linux](osservabilita-linux-netdata.md); la scelta della console locale senza abbonamenti rimane valida. Questo runbook è riportato anche nel progetto rete, insieme a M32 e alla timeline comune.

## Scelta del pilota e ambiente

La richiesta dell’operatore supera per questo monitoraggio la proposta iniziale di provare prima una VM: si comincia dal fisico con GPU, poi si estende alle VM. Non cambia il pilota vm-health di M29 né il gate per estendere gli accessi AdS degli ospiti. L’operatore indica il Debian del collettore come successivo punto di sviluppo dell’integrazione; la collocazione di tutti i database del monitoraggio deve ancora essere dimensionata. L’hub separato rimane una proposta, non una decisione imposta.

Il pilota riguarda un’applicazione di terze parti su una macchina reale, scelta dall’operatore: modello R0 del catalogo di separazione degli ambienti, con pacchetto fissato e ripristino documentato. Il fisico non dispone per definizione dello snapshot di un ospite Proxmox. L’installazione deve fermarsi davanti a un’installazione Netdata precedente non censita; prima di cambiare configurazioni esistenti occorrono copia, proprietà, permessi e impronte. Nessuna operazione sui driver NVIDIA o sul servizio Ollama è inclusa nell’installazione dell’Agent.

## Baseline riferita dall’operatore

La fonte delle misure è l’output incollato dall’operatore il 15/10/2026, non una connessione SSH eseguita dall’agente. Il primo gruppo legge sistema, risorse, `nvidia-smi` e presenza di Netdata nel PATH; il secondo PCI, dispositivi grafici, modelli caricati e metadati APT. Trascrizione sintetica, identità reale e stato strutturato sono nel livello privato `_notes/linux-observability-20261015/pilot/`. L’impronta di questi file identifica il materiale conservato, non certifica autonomamente l’esecuzione remota.

| Controllo | Output riferito | Limite |
|---|---|---|
| Sistema | Ubuntu 26.04.1 LTS, `resolute`, `x86_64` | API successiva: kernel 7.0.0-38-generic, i7-7700 con 8 CPU logiche; non un inventario completo dei servizi |
| Memoria | 15 GiB totali, 1,4 GiB usati, 13 GiB disponibili; swap 29 GiB, 636 KiB usati | Istantanea arrotondata di `free -h`, non misura dell’overhead |
| Disco | Radice e `/var` sullo stesso filesystem: 73 GB, 46 GB usati, 24 GB disponibili, uso 67% | Non prova salute SMART, quota o crescita |
| GPU | NVIDIA GeForce RTX 5060 Ti, famiglia GB206; `Kernel driver in use: nvidia` | Modulo 595.99.02 letto nel terzo riscontro; VRAM e temperature ancora da misurare |
| Dispositivi grafici | `card1` nel gruppo video e `renderD128` nel gruppo render | Non prova i permessi del futuro utente Netdata |
| Utility NVIDIA | `nvidia-smi` non trovato | Non equivale ad assenza del driver, che PCI mostra in uso |
| Ollama | `ollama ps` restituisce soltanto l’intestazione | Nessun modello caricato sull’endpoint interrogato in quel momento; non prova guasto né uso CPU/GPU |
| Netdata | Assente dal PATH; APT installato nessuno e candidato nessuno | Terzo riscontro: servizio not-found, directory statiche e native assenti; non prova indisponibilità dei pacchetti del produttore per Ubuntu 26.04 |

La presenza nei moduli possibili di `nouveau` e `nvidiafb` non dimostra che siano quelli in uso: il campo del driver attivo indica `nvidia`. Non si installano i pacchetti suggeriti dal command-not-found scegliendo arbitrariamente la serie 580 o 595. Il collector NVIDIA documentato usa `nvidia-smi`; la versione delle utility deve essere compatibile con il modulo già caricato. Le metriche generali dell’Agent possono essere collaudate prima della GPU.

## Comandi iniziali già eseguiti

Destinazione: Bash sul fisico pilota. Queste letture hanno prodotto la baseline precedente, senza installazioni. Il primo blocco verifica sistema e capacità e cerca Netdata; il secondo distingue driver PCI in uso, dispositivi, modelli Ollama caricati e disponibilità APT. Gli errori di nvidia-smi e l’assenza del candidato Netdata sono esiti conservati, non motivi per cambiare driver automaticamente. Il modulo NVIDIA è stato letto nel successivo blocco di dry-run.

```bash
cd /
hostname
cat /etc/os-release
uname -m
free -h
df -h / /var
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu --format=csv
if command -v netdata >/dev/null 2>&1; then netdata -v; else printf 'Netdata non presente nel PATH\n'; fi
```

```bash
cd /
lspci -nnk
ls -l /dev/dri
ollama ps
apt-cache policy netdata
```

## Percorso di installazione preparato

Scelta tecnica per il pilota: build statica ufficiale x86_64 in `/opt/netdata`, versione candidata 2.12.1, pubblicata come stabile nella pagina delle release consultata. Il motivo è mantenere il pacchetto separato dalle librerie di sistema e poter rinviare il primo avvio; non è una dichiarazione di mancato supporto del repository nativo. Il `kickstart.sh` del tag v2.12.1 è stato scaricato nel livello privato e letto prima di proporlo. SHA-256 dello script: `a3a6e66f0784fb105c926c4503f023a41f3fad1992b7b4b855248d5d730075dc`.

Il codice di questa versione riconosce `--static-only`, `--install-version`, `--dont-start-it`, `--no-updates`, `--disable-telemetry` e `--dry-run`. Il mancato avvio vale per installazioni statiche e build locali, non è una garanzia da trasferire ai pacchetti nativi. Il vecchio argomento `--disable-cloud` produce un avviso e non disabilita Cloud: non si usa come controllo. Il percorso locale prevede nessun claim, telemetria disattivata e aggiornamenti gestiti; il comportamento della release installata deve essere verificato.

Osservazione sul codice dell’installer fissato: il ramo statico online salta il confronto SHA-256 esterno quando `INSTALL_VERSION` è valorizzato. L’hash dello script non è l’hash del pacchetto che scaricherà. Prima dell’esecuzione che installa servirà quindi verificare separatamente l’archivio ufficiale e il suo checksum, oppure usare una sorgente offline già verificata. Il solo dry-run non certifica integrità del pacchetto o compatibilità runtime. La sequenza di installazione con privilegi è ora preparata sotto; la sua esecuzione rimane da confermare con l’output dell’operatore.

### Comandi del dry-run già eseguito

Destinazione: Bash del fisico pilota, nel terminale SSH già aperto dall’operatore; nessun ramo Git coinvolto. Sono letture e scaricamento dello script in una directory temporanea privata dell’utente. Il dry-run non installa Netdata. `ls` può segnalare directory inesistenti, dato utile per il controllo di un’installazione pregressa. Se il download o il checksum falliscono, l’ultima riga impedisce di eseguire lo script.

```bash
cd /
cat /sys/module/nvidia/version
systemctl show netdata.service --property=LoadState --property=ActiveState --property=FragmentPath
ls -ld /opt/netdata /etc/netdata
netdata_pilot_dir=$(mktemp -d /tmp/netdata-pilot.XXXXXXXX)
printf 'Directory della prova: %s\n' "$netdata_pilot_dir"
curl --fail --location --proto '=https' --tlsv1.2 --output "$netdata_pilot_dir/kickstart.sh" https://raw.githubusercontent.com/netdata/netdata/v2.12.1/packaging/installer/kickstart.sh
printf '%s  %s\n' a3a6e66f0784fb105c926c4503f023a41f3fad1992b7b4b855248d5d730075dc "$netdata_pilot_dir/kickstart.sh" | sha256sum --check - && sh "$netdata_pilot_dir/kickstart.sh" --dry-run --stable-channel --install-version 2.12.1 --static-only --dont-start-it --no-updates --disable-telemetry
```

Output ricevuto: modulo 595.99.02, servizio non trovato e inattivo, entrambi i percorsi assenti, script con SHA-256 coincidente. Il dry-run seleziona l’archivio x86_64 della versione 2.12.1 e stampa le operazioni previste; il suo banner finale «Successfully installed the Netdata Agent» è generico e non dimostra un’installazione. Nel codice il riepilogo viene emesso anche dopo le operazioni simulate. La richiesta sudo visibile alla fine riguarda la rimozione della directory temporanea del kickstart; non è una richiesta per avviare il servizio. L’operatore torna al prompt senza errori riportati, ma non fornisce un codice di uscita separato. Directory effettiva conservata solo nell’evidenza privata, senza dipendere dalla variabile del terminale.

## Bundle scaricato e difetto della prima procedura

L’operatore ha scaricato l’archivio x86_64 2.12.1 e il file dei checksum ufficiali. La preparazione stampa `./netdata-x86_64-latest.gz.run: OK`, copia lo script e salva il canale. L’installazione non parte: il controllo successivo cerca il file in una directory differente e fallisce prima di sudo. Le righe indipendenti successive chiedono la password per una copia di configurazione inesistente e restituiscono altri file assenti; non dimostrano una modifica riuscita. Il servizio rimane non trovato e inattivo. Percorso effettivo e output sintetico sono nel livello privato.

La causa è nel [parser del kickstart 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/packaging/installer/kickstart.sh): l’argomento di `--prepare-offline-install-source` passa attraverso `sanitize_string`, che elimina gli slash. La procedura precedente aveva controllato il cambio directory, ma non questa trasformazione. Non basta aggiungere virgolette al percorso. Per una nuova preparazione si passa il solo nome `offline`, dalla directory di staging; l’argomento di `--offline-install-source` invece è conservato e deve essere assoluto, perché il programma cambia directory. La versione fissata non supporta spazi arbitrari in tutti gli argomenti: lo staging del pacchetto deve essere generato con nome semplice e validato.

Il controllo è stato ripetuto in WSL con le funzioni originali di parsing, validazione e costruzione degli URL, escludendo main, payload e trap finale del programma. La prima versione dell’harness non escludeva il trap e usciva senza fornire una prova valida; corretta prima di misurare il difetto. Il comando con preparazione semplice conserva il nome; reintroducendo il vecchio assoluto il confronto fallisce. La sorgente assoluta conserva l’URL file anche dopo il cambio directory; reintroducendo una relativa il confronto fallisce. Ripristinato il comando corretto, controllo verde e SHA dello script originale invariato. Questa prova misura i percorsi, non esegue l’installazione completa e non dimostra compatibilità runtime.

### Preparazione corretta per un nuovo pilota

Solo per una nuova istanza; il pilota corrente ha già un bundle e deve usare il recupero seguente. Bash, staging con nome semplice; nessun download da ripetere sul fisico corrente.

```bash
cd '<DIRECTORY_PILOTA_NETDATA>'
printf '%s  %s\n' a3a6e66f0784fb105c926c4503f023a41f3fad1992b7b4b855248d5d730075dc ./kickstart.sh | sha256sum --check - && sh ./kickstart.sh --stable-channel --install-version 2.12.1 --static-only --offline-architecture x86_64 --prepare-offline-install-source offline --disable-telemetry
```

### Recupero del bundle già verificato

Destinazione: Bash sul fisico, dentro la directory effettiva del bundle restituita dalla preparazione. Il primo percorso viene compilato dal riscontro dell’operatore, non ricostruito applicando una trasformazione a un dato futuro. Il blocco ricontrolla gli hash dello script e dell’archivio prima di sudo. Tutte le modifiche sono concatenate: un fallimento impedisce installazione, copia o scrittura successive. Le ultime righe sono letture di verifica.

Il [bundle offline ufficiale](https://learn.netdata.cloud/docs/netdata-agent/installation/linux/offline-systems) contiene il nome alias `netdata-x86_64-latest.gz.run`. Il checksum atteso è quello [pubblicato per 2.12.1](https://github.com/netdata/netdata/releases/download/v2.12.1/sha256sums.txt), `f4a73a7b2641f5d962afdf648948e3d472ab18759e906e9e3164cbb7c697147e`: il nome alias non seleziona una release diversa. Non si passa `--install-version` insieme alla sorgente offline. Il sorgente statico del tag conferma il mancato avvio con `--dont-start-it` e la creazione del marker di opt-out; non è ancora una misura del fisico.

```bash
cd '<DIRECTORY_BUNDLE_NETDATA>'
printf '%s  %s\n' a3a6e66f0784fb105c926c4503f023a41f3fad1992b7b4b855248d5d730075dc ./kickstart.sh f4a73a7b2641f5d962afdf648948e3d472ab18759e906e9e3164cbb7c697147e ./netdata-x86_64-latest.gz.run | sha256sum --check - && sudo sh ./kickstart.sh --stable-channel --static-only --offline-install-source "$PWD" --dont-start-it --no-updates --disable-telemetry --non-interactive && test ! -e /opt/netdata/etc/netdata/netdata.conf.before-linux-monitoring && sudo cp -a /opt/netdata/etc/netdata/netdata.conf /opt/netdata/etc/netdata/netdata.conf.before-linux-monitoring && printf '%s\n' '[web]' '    bind to = 127.0.0.1:19999' | sudo tee /opt/netdata/etc/netdata/netdata.conf
/opt/netdata/bin/netdata -v
systemctl show netdata.service --property=LoadState --property=ActiveState --property=UnitFileState --property=FragmentPath
sudo ls -l /opt/netdata/etc/netdata/.opt-out-from-anonymous-statistics /opt/netdata/etc/netdata/netdata.conf.before-linux-monitoring
```

Il blocco modifica il sistema installando l’Agent e la configurazione, ma lascia fermo il servizio. Non installa utility NVIDIA e non modifica driver o unità Ollama. Ci si attende versione 2.12.1, servizio presente e inattivo, bind loopback, backup e marker di opt-out. Output del recupero ricevuto: installazione completata, binario v2.12.1 e servizio loaded/inactive/enabled; dettagli nella sezione seguente. Timer e cron dell’updater vanno verificati prima di dichiarare l’assenza di auto-update sul fisico.

## Installazione reale ricevuta

Il recupero dal bundle effettivo è riuscito secondo l’output dell’operatore. I due confronti SHA-256 restituiscono OK prima di sudo; l’installer copia i file locali, estrae in `/opt/netdata`, crea l’account di servizio e installa le integrazioni di sistema. Il binario interrogato per percorso completo risponde `netdata v2.12.1`. Systemd restituisce `LoadState=loaded`, `ActiveState=inactive`, `UnitFileState=enabled` e unità in `/usr/lib/systemd/system/netdata.service`. Nonostante il banner iniziale generico annunci un riavvio, il risultato misurato è servizio fermo: l’opzione di mancato avvio ha avuto effetto. `enabled` indica l’avvio al prossimo boot, non un processo già in esecuzione né l’abilitazione dell’updater.

La riga successiva dell’operatore scrive `[web]` con `bind to = 127.0.0.1:19999`; il file iniziale è copiato in `netdata.conf.before-linux-monitoring`, 301 byte, `root:root 0644`. Il marker `.opt-out-from-anonymous-statistics` è presente, vuoto, `root:root 0664`. La disattivazione dell’updater restituisce `Auto-updates have been DISABLED` nel proprio output. Quest’ultimo è un riscontro della procedura, non ancora una ricerca indipendente di timer e cron. Il permesso del marker non contiene un segreto; proprietari, permessi e configurazione effettiva vanno conservati nell’inventario del pilota.

L’installazione ha aggiunto l’utente Netdata ai gruppi Docker e video e assegnato capability o setuid a plugin specifici. Sono modifiche osservate, da includere nel ripristino e nella revisione dei privilegi prima dell’estensione: la [documentazione Docker](https://docs.docker.com/engine/install/linux-postinstall/) descrive l’accesso privilegiato al daemon tramite quel gruppo; necessità e accesso effettivo vanno verificati per l’istanza, senza presumere il tipo di socket dal solo nome del gruppo. Nessun gruppo viene modificato in questo giro. Gli identificativi numerici effettivi restano nell’evidenza privata. L’installer ha scritto logrotate, configurazione journald per il namespace Netdata, tmpfiles e unità systemd, oltre al solo prefisso `/opt/netdata`: cancellare quella directory non descriverebbe una rimozione completa.

## Primo avvio e lettura delle metriche: esecuzione ricevuta

Destinazione Bash sul fisico pilota, già installato con bind locale. Il solo comando di modifica avvia il servizio Netdata; i successivi leggono API, listener, memoria del servizio e stato ACLK. Non avvia un modello Ollama, non modifica il driver e non crea il ricevitore sul Debian. [Controllo del servizio](https://learn.netdata.cloud/docs/netdata-agent/maintenance/service-control) e [CLI](https://learn.netdata.cloud/docs/netdata-agent/agent-cli) documentano avvio, API info e stato Cloud; l’[endpoint Prometheus](https://learn.netdata.cloud/docs/exporting-metrics/prometheus) è il punto di prova delle metriche.

```bash
cd /
sudo systemctl start netdata.service
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --max-time 10 http://127.0.0.1:19999/api/v1/info
systemctl show netdata.service --property=ActiveState --property=SubState --property=MainPID --property=MemoryCurrent --property=Result
sudo ss -lntp '( sport = :19999 )'
sudo /opt/netdata/bin/netdatacli aclk-state
netdata_metrics_file=$(mktemp /tmp/netdata-metrics.XXXXXXXX)
curl --fail --silent --show-error --max-time 10 'http://127.0.0.1:19999/api/v1/allmetrics?format=prometheus&source=as-collected' --output "$netdata_metrics_file" && awk '/^netdata_system_cpu/ {cpu++; if(cpu<=2) print} /^netdata_system_ram/ {ram++; if(ram<=2) print} END {printf "cpu_samples=%d ram_samples=%d\n",cpu,ram; if(cpu==0 || ram==0) exit 1}' "$netdata_metrics_file"
```

Output ricevuto dall’operatore il 15/10/2026. Il criterio preparato richiedeva il listener soltanto `127.0.0.1:19999`, non una wildcard; lo stato del servizio deve essere active/running senza risultato di errore. Il collector CPU e quello RAM devono entrambi fornire campioni: il riepilogo conta le righe metriche dei due prefissi, non macchine né secondi. Lo scaricamento su un file temporaneo precede il filtro, e il filtro si esegue solo se curl riesce; una risposta assente non viene contata come una prova verde. La disponibilità iniziale ha retry limitati; un risultato senza campioni richiede distinguere inizializzazione da collector assente prima di cambiare la configurazione.

Lo stato ACLK deve distinguere build con supporto Cloud da nodo claimed/connected: una feature compilata non dimostra una connessione attiva. Il marker di opt-out e il mancato claim non sostituiscono il controllo dello stato effettivo. Questa lettura non è un monitoraggio prolungato del traffico. `MemoryCurrent` è un’istantanea del servizio e non chiude la misura di impatto prima/dopo sullo stesso carico. La GPU resta da collaudare dopo aver riconciliato l’utility con il modulo 595.99.02; il solo Agent non rende disponibile `nvidia-smi`.

## Configurazione prima del primo avvio

La configurazione è stata scritta con HTTP e metriche limitati a `127.0.0.1:19999`; l’ascolto effettivo è ora verificato su loopback, con la lettura ss dell’operatore. L’accesso del futuro Prometheus sarà una modifica esplicita, con indirizzi e percorso di rete verificati. Per il primo collaudo non si apre una porta a tutta la LAN. La sola installazione dell’Agent non invia gli eventi di sistema al collettore e non crea Grafana, Prometheus o Loki.

Un Agent non collegato a Cloud, con telemetria e aggiornamenti automatici disattivati, può funzionare autonomamente secondo la documentazione ufficiale. Questo riguarda il runtime standard: installazione, eventuali collector configurati verso destinazioni esterne e risorse caricate da una UI sono percorsi distinti. Il collaudo usa le API locali e deve verificare versione, configurazione effettiva, stato non collegato e traffico, senza dedurre l’isolamento dal nome di un flag.

## Collaudo e ripristino da eseguire

| Fase | Criterio di riuscita | Stato |
|---|---|---|
| Assenza di conflitti e driver | Servizio e percorsi pregressi identificati, versione NVIDIA letta | Riscontro ricevuto: servizio e percorsi assenti, modulo 595.99.02 |
| Pacchetto | Archivio della release verificato, installazione senza avvio e senza aggiornamenti automatici | Installato 2.12.1, hash entrambi OK, mancato avvio iniziale verificato, successivamente avviato; opt-out presente; updater conferma DISABLED |
| Primo avvio locale | Servizio attivo, unico ascolto autorizzato, versione e dati API coerenti | Active/running, listener loopback, CPU/RAM presenti e ACLK non online; resto aperto |
| Metriche di sistema | Campioni CPU, memoria, disco e rete presenti; carico e crescita prima/dopo registrati | CPU/RAM locali presenti; disco/rete, crescita e impatto prima/dopo ancora da misurare |
| GPU | Utility compatibile, query eseguibile dall’utente Agent, metriche reali e non soli grafici vuoti | Ripristino già documentato e nvidia-smi riuscito nella verifica separata; APT non propone operazioni; utente Netdata verificato; campioni recenti del daemon verificati il 16/10: GPU/VRAM/temperatura 1/3/1; impatto sostenuto aperto |
| Servizio applicativo | Ollama ancora raggiungibile; confronto prima/dopo sullo stesso carico concordato | Non eseguito; nessun modello avviato per la prova |
| Eventi al collettore | Originali tecnici separati dagli accessi AdS, ricezione, code e silenzio verificati | Non configurato |
| Console comune | Raccolta Prometheus e ricerca tecnica Grafana/Loki con autenticazione e risorse dimensionate | Non installata |

La baseline attuale della memoria non misura l’impatto dell’Agent e `ollama ps` vuoto non è un test prestazionale. Prima di dichiarare concluso il pilota si misurano servizio, memoria del processo, CPU e crescita disco nello stesso contesto; un’inferenza Ollama può essere usata solo dopo aver scelto un carico ripetibile. Nessuna prova richiede OOM, crash GPU o riavvio del fisico.

Per un problema dopo il primo avvio, il primo ripristino previsto è fermare e disabilitare il solo servizio Netdata, conservando configurazione e dati per la diagnosi. L’eventuale rimozione completa segue il disinstallatore ufficiale e il file `.environment` dell’installazione effettiva, dopo averne verificato i percorsi; non è un comando di cancellazione ricorsiva generico. Se Netdata era già presente, si ripristina la copia iniziale invece di trattarlo come una nuova installazione. Driver, modelli e unità Ollama rimangono fuori da questa procedura.

## Fonti ufficiali lette il 15/10/2026

| Fonte | Uso nel runbook |
|---|---|
| [Release v2.12.1](https://github.com/netdata/netdata/releases/tag/v2.12.1) | Identifica la versione candidata; non prova il funzionamento sull’host |
| [Installer del tag v2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/packaging/installer/kickstart.sh) | Copia scaricata e letta: flag effettivi, avvio rinviato e limite del controllo del checksum con versione fissata |
| [Installazione Linux](https://learn.netdata.cloud/docs/netdata-agent/installation/linux) e [build statica](https://learn.netdata.cloud/docs/netdata-agent/installation/linux/static-binary-linux-packages) | Percorsi supportati, architettura e separazione dalle librerie del sistema |
| [Protezione dell’Agent](https://learn.netdata.cloud/docs/netdata-agent/configuration/securing-agents) | Porta predefinita e bind esplicito prima di esporre le metriche |
| [Comunicazioni in uscita](https://learn.netdata.cloud/docs/security-and-privacy-design/netdata-agent#outbound-network-communication) | Claim, telemetria e aggiornamenti sono controlli distinti per il runtime autonomo |
| [Collector NVIDIA](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/nvidia-gpu) e [CLI Ollama](https://docs.ollama.com/cli) | Prerequisito `nvidia-smi` e significato dell’elenco dei modelli caricati |
| [Disinstallazione](https://learn.netdata.cloud/docs/netdata-agent/maintenance/uninstall) | Rimozione coerente con metodo e `.environment` effettivi |

## Estrazione nel template richiesta dall’operatore

Il 15/10 l’operatore richiede, al termine del lavoro, un pacchetto utile in altri progetti: procedura, strumenti e stack locale riproducibili e parametrizzati. La [specifica del pacchetto](progetto-pacchetto-linux-observability.md) è condivisa con il progetto rete e registrata anche nel template, fuori dal catalogo dei pacchetti eseguibili fino al completamento. Destinazione proposta `.claude/templates/linux-observability/`, con profili Agent/hub/log, esempi senza valori reali, release e hash fissati, preflight, rendering, controlli negativi, persistenza, aggiornamento e ripristino.

L’estrazione dovrà includere Netdata, Prometheus, Grafana OSS e Loki/Alloy locali, con accesso e risorse configurati per l’istanza. Non si considera completata copiando questi comandi: servono primo avvio, metriche reali, ricezione degli eventi, consultazione e recupero dello stack misurati. L’adozione in un altro progetto deve superare una prova con parametri diversi, senza identità, percorsi temporanei o credenziali del pilota. Commit, push e propagazione del template restano manuali.

## Riscontro del primo avvio e limiti della misura

| Controllo eseguito dall’operatore | Riscontro | Che cosa non dimostra |
|---|---|---|
| systemctl show | active/running, Result success | Stabilità dopo reboot e prestazioni a regime |
| ss sulla porta 19999 | Un listener TCP su 127.0.0.1:19999 del processo Netdata | Accesso remoto da Prometheus o cifratura del percorso futuro |
| API info | v2.12.1, una macchina locale, stream disabilitato, dbengine | Campi di build HTTPS/Cloud non provano trasporti attivi; zero grafici/metriche in questa risposta non risolve il conteggio reale |
| netdatacli aclk-state | Claimed No, Online No, reconnect count zero | Assenza di qualsiasi traffico esterno durante un periodo prolungato |
| Export Prometheus locale | 14 righe col prefisso CPU e 4 RAM; righe campione di system.cpu e system.ram | Numero complessivo delle serie, GPU, salute di tutti i collector o integrazione centrale |
| MemoryCurrent | 389820416 byte, 371,76 MiB, circa 372 MiB | È memoria del cgroup, non RSS del solo processo né misura prima/dopo |

Il campo API charts-count=0 e metrics-count=0 precede l’export con campioni. Entrambi i riscontri sono conservati: non si attribuisce senza prova il primo valore all’inizializzazione né si usa per negare i campioni successivi. I valori guest/guest_nice zero nelle due righe mostrate non equivalgono a utilizzo complessivo CPU nullo. I conteggi del filtro riguardano prefissi; non sono 14 macchine o 14 secondi. La funzione journal elencata nell’API non dimostra che i log siano già inoltrati, e exporting-enabled=false non impedisce l’endpoint di pull appena letto.

La capacità disco aggregata riportata nell’API non è lo spazio libero della radice. La quota dbengine e il page-cache-size riportati non sono un limite totale dell’installazione. Dati identificanti, PID, API selezionata e campioni con timestamp sono nell’evidenza privata operator-first-start-excerpts.txt e operator-first-start-selected.json; sono estratti fedeli e campi selezionati, non una cattura completa di rete o una copia integrale dell’API. La [normalizzazione e capienza](normalizzazione-retention-capienza.md) distingue log, metriche ed evidenze; il [registro fonti e passi](fonti-osservabilita-linux.md) collega la sequenza completa.

## Inventario utility GPU: lettura ricevuta

Destinazione: stesso terminale Bash del fisico pilota. Sono inventario locale e metadati APT, senza aggiornamento dei repository o installazione. Servono a confrontare pacchetti user-space e modulo già caricato 595.99.02; i precedenti suggerimenti command-not-found indicavano anche 595.71.05, quindi scegliere soltanto il numero di ramo non basta. La [documentazione del collector NVIDIA](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/nvidia-gpu) richiede nvidia-smi; il percorso e la configurazione della release installata saranno verificati dopo questa lettura.

```bash
cd /
command -v nvidia-smi || printf 'nvidia-smi assente dal PATH\n'
cat /proc/driver/nvidia/version
dpkg-query -W -f='${db:Status-Abbrev}\t${binary:Package}\t${Version}\n' '*nvidia*'
apt-cache policy nvidia-utils-595 nvidia-utils-595-server libnvidia-compute-595 libnvidia-compute-595-server
```

Output ricevuto il 15/10/2026: la tabella seguente distingue componenti installati e candidati della cache APT. Un elenco vuoto o pacchetto assente è un dato di inventario; non autorizza a installare un driver differente. La fase successiva del Debian richiederà una baseline separata di spazio, mount, CPU, RAM, servizi e code prima di installare lo stack centrale.

## Riscontro GPU: componenti e versione candidata

Il modulo caricato è NVIDIA UNIX Open Kernel Module 595.99.02, compilato con GCC 15.2.0 secondo il testo ricevuto. Dpkg mostra installati il modulo per il kernel 7.0.0-38, firmware NVIDIA e kernel-common 595.99.02, oltre al firmware grafico della distribuzione. Le righe rc dei tre vecchi moduli sono pacchetti rimossi con configurazione residua; le righe un sono voci non installate, non prove di ulteriori driver in uso. Il [manuale dpkg-query](https://manpages.debian.org/trixie/dpkg/dpkg-query.1.en.html) documenta gli stati abbreviati. Non è stata richiesta o eseguita pulizia di tali residui. Le versioni dei vecchi pacchetti non dimostrano da sole la storia dell’aggiornamento del sistema.

| Pacchetto interrogato | Installato | Candidato nella cache riferita | Interpretazione |
|---|---|---|---|
| nvidia-utils-595 | Nessuno | 595.99.02-0ubuntu0.26.04.1 | Candidato standard corrispondente al modulo 595.99.02 |
| libnvidia-compute-595 | Nessuno | 595.99.02-0ubuntu0.26.04.1 | Libreria candidata alla stessa versione delle utility |
| nvidia-utils-595-server | Nessuno | 595.91.07-0ubuntu0.26.04.2 | Versione diversa, non selezionata per il modulo attuale |
| libnvidia-compute-595-server | Nessuno | 595.91.07-0ubuntu0.26.04.2 | Versione diversa, non selezionata per il modulo attuale |

Le quattro policy indicano anche la versione base 595.58.03; i candidati aggiornati sono proposti da resolute-updates/restricted e resolute-security/restricted amd64 a priorità 500. È una misura della cache locale ricevuta, non un aggiornamento degli indici o una prova di download. Le precedenti proposte command-not-found 595.71.05 sono uno stato storico diverso, senza prova qui di quando siano cambiate le liste. La [guida Ubuntu](https://documentation.ubuntu.com/server/how-to/graphics/install-nvidia-drivers/) distingue pacchetti standard e server e descrive il rischio di disallineamento fra libreria e modulo. Le due versioni standard sono quindi candidate motivate; la compatibilità operativa rimane da provare tramite lettura della GPU.

## Simulazione delle dipendenze APT: esecuzione ricevuta

Destinazione: stesso terminale Bash del fisico pilota, cartella radice; nessun repository Git interessato. Il [manuale APT](https://manpages.debian.org/trixie/apt/apt-get.8.en.html) documenta la simulazione senza applicazione delle operazioni, il blocco delle rimozioni e la selezione per versione. Il manuale della variante Ubuntu resolute non è stato recuperato; la fonte Debian documenta la semantica dei flag, mentre il resolver sulla macchina reale fornirà la misura delle dipendenze effettive. Si usa sudo per evitare letture parziali della configurazione APT segnalate dal manuale per le simulazioni senza privilegi. Non si esegue apt update o upgrade, non si installano pacchetti e non si riavviano servizi.

```bash
cd /
sudo apt-get --simulate --no-install-recommends --no-remove install nvidia-utils-595=595.99.02-0ubuntu0.26.04.1 libnvidia-compute-595=595.99.02-0ubuntu0.26.04.1
```

Il comando fissa entrambe le versioni richieste, omette i pacchetti soltanto raccomandati e interrompe il resolver se occorrono rimozioni. Quest’ultima opzione non vieta da sola ogni possibile aggiornamento: per questo il piano intero va letto prima di preparare l’installazione. Le righe Inst, Conf e Remv sono operazioni simulate, non modifiche avvenute. Criterio da verificare sull’output integrale: dipendenze risolte, nessuna rimozione, nessuna sostituzione/aggiornamento di driver, moduli o pacchetti inattesi, sole aggiunte comprese e versioni coerenti. Errori, pacchetti held o proposte inattese lasciano il passo aperto; non si ripete senza simulate per tentare di risolverli.

Output della simulazione ricevuto: entrambi i pacchetti risultano già alla versione richiesta, con zero aggiornati, zero installati, zero da rimuovere e zero non aggiornati. Non viene proposta una seconda installazione; il ripristino già documentato in testa al runbook spiega il cambiamento rispetto all’inventario precedente. Il prossimo controllo riguarda l’utente Netdata e il collector. Il testo dell’inventario ricevuto è conservato integralmente nella trascrizione privata operator-gpu-packages-transcript.txt; operator-gpu-packages-selected.json mantiene i campi e i limiti. La sua impronta identifica il testo conservato, non certifica autonomamente l’esecuzione remota. Le nuove evidenze e lo stesso stato sono già riportati nel contesto e nella timeline del progetto rete.

## Riconciliazione fra inventario, ripristino e simulazione

Il nuovo output APT non contraddice il mancato nvidia-smi del preflight: fra i due stati il dossier condiviso registra il ripristino delle utility e della libreria. La simulazione non può essere la causa dell’installazione: il [manuale APT](https://manpages.debian.org/trixie/apt/apt-get.8.en.html) ne documenta il carattere senza applicazione delle operazioni. Il riepilogo tutto a zero vale per questa richiesta sullo stato attuale, non certifica ogni possibile manutenzione del sistema. Non è stato fornito un codice di uscita separato e non si inventa un timestamp dell’esecuzione dell’operatore.

La prova privata nvidia-post-upgrade-20261015.json, già presente e identica nei due progetti, ha SHA verificato e riporta una lettura separata riuscita alle 13:53:37 UTC: GPU riconosciuta, librerie caricabili e un dispositivo CUDA. Questa è evidenza trasferita dal progetto d’origine, non una nuova misura remota di questo giro. I riferimenti sorgenti rimangono nel file; non sono stati aperti per importare risultati di benchmark. L’esecuzione di un’inferenza Ollama e l’effettiva raccolta Netdata di utilizzo, VRAM e temperatura non risultano collaudate da quella prova. Le precedenti ricerche di nomi NVIDIA avevano trovato soltanto stati delle unità systemd: non equivalgono a metriche hardware.

La trascrizione integrale del testo APT ricevuto è in operator-gpu-apt-simulation-transcript.txt e il suo riepilogo è in operator-gpu-apt-simulation-selected.json. Lo stato corrente dei pacchetti è ora presente, mentre l’inventario precedente resta conservato come fotografia storica. La parte di ripristino aggiunta da un altro lavoro al dossier non viene sovrascritta; nessuna operazione Git viene compiuta dall’assistente corrente.

## Utente del collector e file effettivi: riscontro ricevuto

Il [file distribuito nel tag 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/config/go.d/nvidia_smi.conf) contiene già un job nvidia_smi. Il [codice del collector](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/collector/nvidia_smi/collector.go) usa il binario nvidia-smi e un controllo che fallisce senza metriche; lo [schema di configurazione](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/collector/nvidia_smi/config_schema.json) documenta binary_path, timeout e loop_mode. La presenza del job distribuito non prova che il processo corrente lo stia eseguendo: configurazione locale, permessi ed errori di avvio vanno letti. Non si assume automaticamente che l’installazione tardiva delle utility abbia fatto ripartire il collector.

Destinazione: stesso terminale Bash del fisico pilota. Si leggono la GPU come utente netdata, il file originale nel prefisso statico e l’eventuale override locale. La query è diagnostica, senza caricare un modello o cambiare driver. Il comando journal segue il [percorso ufficiale del collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/nvidia-gpu): namespace Netdata, solo messaggi del modulo, giornata corrente e massimo 40 righe. Nessun riavvio o nuova configurazione è incluso.

```bash
cd /
sudo -u netdata /usr/bin/nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu --format=csv
sudo cat /opt/netdata/usr/lib/netdata/conf.d/go.d/nvidia_smi.conf
if sudo test -f /opt/netdata/etc/netdata/go.d/nvidia_smi.conf; then sudo cat /opt/netdata/etc/netdata/go.d/nvidia_smi.conf; else printf 'Nessuna configurazione NVIDIA personalizzata\n'; fi
sudo journalctl --namespace=netdata --since today --no-pager --grep nvidia_smi -n 40
```

Criterio: query GPU riuscita anche come netdata, file e job effettivi identificati e diagnostica di avvio disponibile. File assente, accesso negato o zero messaggi sono risultati da conservare, non prove di raccolta riuscita. In particolare, nessun messaggio nel journal non dimostra un collector sano; il controllo conclusivo dovrà leggere chart e campioni con contesto nvidia_smi, escludendo i soli stati systemd. Output ricevuto: query come netdata riuscita, job distribuito presente, override assente e comando enable accettato nel journal. I campioni Netdata rimangono da verificare; prima di qualunque modifica si prepara il delta e il ripristino sul file realmente osservato.

## Riscontro dell’utente di servizio e comando accettato

| Lettura riferita dall’operatore | Risultato | Limite |
|---|---|---|
| Query nvidia-smi come netdata | NVIDIA GeForce RTX 5060 Ti, driver 595.99.02; 16311 MiB totali, 34 MiB usati, 36 Celsius | Il binario è leggibile/eseguibile per quell’utente; non prova inferenza Ollama o pipeline del collector |
| File distribuito nvidia_smi.conf | jobs con name nvidia_smi, testo mostrato coerente con quello del tag | È confronto del testo ricevuto, non hash autonomamente letto dal filesystem remoto |
| Configurazione personalizzata | Assente nel percorso interrogato | Non è una verifica di ogni possibile override globale o dinamico |
| Journal, 15/10 alle 15:12:21 | Job manager go.d: command enable, state accepted, result_status 202 | Evento di accettazione; esecuzione del job, durata, autore e metriche non dedotti da questa sola riga |

La trascrizione integrale ricevuta è nel livello privato operator-gpu-netdata-user-transcript.txt; i campi e i limiti sono in operator-gpu-netdata-user-selected.json. Non è stata aperta una nuova connessione SSH dall’assistente e non è stata cambiata la configurazione. La lettura del journal limitata ai messaggi del modulo e alla giornata non dimostra assenza di altri messaggi o errori. I valori VRAM e temperatura sono una singola osservazione nvidia-smi: non certificano l’impatto dell’Agent o l’assenza di carichi applicativi.

## Campioni hardware nell’export locale: criterio non raggiunto

Il [sorgente charts.go del tag 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/collector/nvidia_smi/charts.go) definisce i contesti nvidia_smi.gpu_utilization, nvidia_smi.gpu_frame_buffer_memory_usage e nvidia_smi.gpu_temperature. Le [regole dell’export Prometheus](https://learn.netdata.cloud/docs/exporting-metrics/prometheus) collegano il nome al contesto e distinguono as-collected dalle medie. Il controllo fissa prefix=netdata e richiede quei tre nomi, escludendo gli stati delle unità systemd che contengono soltanto la parola NVIDIA. Questa verifica riguarda il pilota con una GPU osservata; l’estensione a più GPU richiederà il confronto per identificativo del dispositivo.

Destinazione: stesso terminale Bash del fisico pilota, directory radice. Si scarica l’export in un file temporaneo e si filtra solo se curl riesce. Il file resta disponibile per la diagnosi. Il filtro richiede numeri finiti e timestamp non più vecchi di 60 secondi, con tolleranza di 5 secondi verso il futuro rispetto al date della stessa macchina. Sono criteri interni del collaudo, non limiti dichiarati dal produttore; errore di clock o formato inatteso lascia la prova aperta. Il valore di utilizzo zero è ammesso, perché una GPU a riposo può essere correttamente monitorata.

```bash
cd /
netdata_gpu_metrics_file=$(mktemp /tmp/netdata-gpu-metrics.XXXXXXXX)
curl --fail --silent --show-error --max-time 15 'http://127.0.0.1:19999/api/v1/allmetrics?format=prometheus&source=as-collected&prefix=netdata&timestamps=yes' --output "$netdata_gpu_metrics_file" && awk -v now_ms="$(date +%s%3N)" 'function fresh(s,a){sub(/^.*}[ \t]+/,"",s); if(split(s,a,/[ \t]+/)!=2) return 0; return a[1] ~ /^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$/ && a[2] ~ /^[0-9]+$/ && now_ms-a[2]>=-5000 && now_ms-a[2]<=60000} /^netdata_nvidia_smi_gpu_utilization\{/ && fresh($0){gpu++; if(gpu<=2) print} /^netdata_nvidia_smi_gpu_frame_buffer_memory_usage\{/ && fresh($0){vram++; if(vram<=3) print} /^netdata_nvidia_smi_gpu_temperature\{/ && fresh($0){temp++; if(temp<=1) print} END{printf "gpu_samples=%d vram_samples=%d temp_samples=%d\n",gpu,vram,temp; if(gpu==0 || vram==0 || temp==0) exit 1}' "$netdata_gpu_metrics_file"
```

Ci si attendono righe con i tre contesti, identificativi/chart, valori e timestamp, seguite da gpu_samples, vram_samples e temp_samples tutti maggiori di zero. I totali contano righe corrispondenti, non dispositivi o secondi; le dimensioni VRAM possono produrre più righe. In questa sorgente as-collected si leggono i valori con le unità e le eventuali scale del contesto, senza chiamare percentuale un contatore o assumere unità da una stringa arbitraria. Il controllo dimostra presenza e freschezza puntuale; continuità, impatto e invio al Debian restano prove separate.

La procedura è stata provata in WSL senza rete o servizi: sintassi Bash, 14 fixture con tre gruppi, gruppi mancanti, zero valido, etichette con spazi, stati systemd, HTML/commenti, dati vecchi/futuri, NaN/Inf, timestamp assenti e contesto simile errato. Togliendo la guardia VRAM il suo caso mancante passa erroneamente; togliendo il limite di età il caso vecchio passa erroneamente. Comando originale ripristinato/verificato invariato; un curl fittizio fallito impedisce il filtro. È verifica della procedura, non dei campioni del pilota. L’output reale ora ricevuto è gpu_samples=0, vram_samples=0, temp_samples=0: criterio non raggiunto, causa ancora da individuare.

## Esito negativo e diagnosi, registrati il 16/10/2026

L’operatore restituisce tre conteggi a zero dopo curl e filtro. Nessun messaggio di errore curl riportato; l’esecuzione del filtro indica il successo del download nella catena consegnata. Il codice di uscita separato e l’export grezzo non sono stati trasmessi: non si inventano né il nome concreto del file temporaneo né l’ora originale. Il comando e le tre righe ricevute sono conservati privatamente in operator-gpu-metrics-zero-record-20261016.txt, con la provenienza della ricostruzione del comando dichiarata.

| Dato | Stato che autorizza |
|---|---|
| Query come netdata già riuscita | Accesso al binario/GPU verificato in quella lettura |
| enable accepted/202 | Accettazione del comando osservata; raccolta non dimostrata |
| Tre contatori validi a zero | Il criterio delle tre famiglie con numeri finiti e tempi recenti non è soddisfatto |
| Corpo dell’export assente dal riscontro | Non distingue ancora assenza, nomi diversi, valori o timestamp esclusi dal filtro |
| Fixture locali verdi | La procedura esercita i casi costruiti; non sostituisce il formato reale o la misura sull’host |

La diagnosi mantiene la guardia e allarga soltanto la vista dei dati da esaminare. Non si elimina la verifica del tempo né si tratta un gruppo mancante come successo. Al cambio di giornata non si presume che la variabile della shell o il file temporaneo precedente siano ancora disponibili: il blocco seguente crea un nuovo export, conserva il corpo e mostra le prime 60 righe che contengono nvidia, includendo commenti e stati di unità. Il totale e il limite stampato esplicitano il campionamento; non sono un conteggio di GPU. Se il totale supera 60, una riga non mostrata non si può dichiarare assente.

Destinazione: stesso terminale Bash del fisico pilota, directory plugins.d dell’installazione statica. Il [debug ufficiale del collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/nvidia-gpu) avvia un processo separato come utente netdata; non riavvia il servizio esistente e non è un’installazione. Questo processo interroga la GPU e produce output diagnostico per il modulo, senza lanciare un modello Ollama. La documentazione avverte che il debug non copre i job creati dalla UI/Dyncfg: il risultato va confrontato con l’export del daemon, non trasferito automaticamente al job in esercizio.

Il [manuale GNU timeout](https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html) documenta TERM a 20 secondi e l’eventuale KILL dopo altri 5. Si conserva il codice in debug_exit: 124 indica la scadenza, 137 un segnale KILL, gli altri codici si leggono insieme all’output; nessuno di questi è da solo una prova di metriche corrette. Si mantiene il controllo dell’orologio nello stesso blocco per confrontare i timestamp delle righe mostrate. Non si chiede di aggiornare, reinstallare o riavviare driver, Ollama o Netdata.

```bash
cd /opt/netdata/usr/libexec/netdata/plugins.d
netdata_gpu_debug_metrics_file=$(mktemp /tmp/netdata-gpu-diagnostic.XXXXXXXX)
curl --fail --silent --show-error --max-time 15 'http://127.0.0.1:19999/api/v1/allmetrics?format=prometheus&source=as-collected&prefix=netdata&timestamps=yes' --output "$netdata_gpu_debug_metrics_file" && awk 'tolower($0) ~ /nvidia/ {n++; if(n<=60) print} END {printf "nvidia_lines=%d shown=%d\n",n,(n<60?n:60)}' "$netdata_gpu_debug_metrics_file"
date '+epoch_ms=%s%3N local=%Y-%m-%dT%H:%M:%S%z'
sudo -u netdata timeout --signal=TERM --kill-after=5s 20s ./go.d.plugin -d -m nvidia_smi
printf 'debug_exit=%s\n' "$?"
```

Output atteso per la diagnosi, non per una promozione automatica del collaudo: righe e nomi effettivi dell’export, eventuali timestamp, totale/limite delle righe selezionate, orologio e log del processo separato con debug_exit. L’output completo del debug va conservato, compresi eventuali errori; una scadenza a 124 è prevista se il processo resta attivo fino al limite. La raccolta GPU rimane non verificata finché non sono presenti campioni hardware validi dal daemon. Diagnostica eseguita dall’operatore il 16/10: export senza hardware e debug separato con raccolta riuscita, dettagli nella sezione seguente. Nessun comando remoto dell’assistente.

## Debug separato riuscito ed export del servizio senza GPU, 16/10/2026

L’export restituito dall’operatore mostra nvidia_lines=21 e shown=21: in questo filtro non c’è troncamento. Le corrispondenze sono un contatore interrupt NVIDIA e venti dimensioni degli stati di quattro unità systemd; nessuna è un campione di utilizzo, frame buffer o temperatura del collector. Non si deduce nulla sul funzionamento di quelle unità dai loro valori in questa prova GPU. L’orologio mostrato è 2026-10-16T09:26:09+0200, epoch_ms=1792135569610; i campioni corrispondenti hanno timestamp 1792135535264 e 1792135530008/9. Sono numeri dell’export osservato, non tempi attribuiti ai campioni assenti.

Il processo separato go.d.plugin v2.12.1 gira come netdata, legge go.d.conf e nvidia_smi.conf dalla directory stock e avvia nvidia-smi tramite nd-run. Il log dichiara check success e intervallo di raccolta 10 secondi, poi produce CHART/BEGIN/SET per la GPU in due cicli. La presenza dei messaggi nel terminale non significa che quel protocollo sia stato acquisito dal daemon o dal suo database: questa è proprio la distinzione che spiega perché il debug positivo non chiuda ancora l’export negativo.

| Contesto nel protocollo del processo separato | Primo ciclo | Secondo ciclo | Interpretazione |
|---|---|---|---|
| nvidia_smi.gpu_utilization | gpu=0 | gpu=0 | Utilizzo zero è un dato valido, non assenza della GPU |
| nvidia_smi.gpu_frame_buffer_memory_usage | free=16582180864, used=35651584, reserved=487587840 | Stessi valori | Byte dichiarati dal contesto; used equivale a 34 MiB |
| nvidia_smi.gpu_temperature | temperature=36 | temperature=36 | Celsius dichiarati dal contesto |
| Stato interno della raccolta | success=1, failed=0 | success=1, failed=0 | Stato del processo diagnostico soltanto |
| Durata interna dell’ultima raccolta | 7 ms | 7 ms | Non è misura dell’overhead totale dell’Agent |

Al limite temporale il processo riceve TERM alle 09:26:40.044+02:00, ferma il job, rilascia il tentativo contenuto e termina; debug_exit=124. Gli eventi error/warn sul containment sono successivi al segnale e vanno conservati con questa sequenza, senza riscriverli come un errore nvidia-smi durante i due cicli riusciti. Per l’esatta durata e ogni altro comportamento resta autorevole l’output ricevuto, non una ricostruzione retroattiva dell’intero sistema. Estratti fedeli dei passaggi e campi selezionati sono conservati nei file operator-gpu-debug-excerpts-20261016.txt e operator-gpu-debug-selected-20261016.json: non sono una trascrizione integrale di tutti i chart o dell’intero protocollo.

## Abilitazione esplicita del modulo e riavvio circoscritto preparati

Il [go.d.conf ufficiale 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/config/go.d.conf) riporta nella lista dei valori predefiniti la riga commentata nvidia_smi: no, mentre enabled e default_run sono yes. La [guida di configurazione dei collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors-configuration) descrive l’override locale di go.d.conf e il riavvio dell’Agent dopo la modifica. L’abilitazione esplicita è quindi il prossimo intervento motivato da verificare nel servizio; il valore effettivo del job nel daemon non è ricostruito dal solo processo lanciato con -m.

La modifica copia l’intero file distribuito nel livello locale, trasformando una sola riga, senza cambiare gli altri default. Prima richiede lo SHA-256 della sorgente fissata. La shell con noclobber si ferma se go.d.conf esiste già, anche evitando di sovrascrivere una configurazione comparsa nel frattempo. Solo scrittura riuscita e riga NVIDIA presente consentono il riavvio. Se il checksum non coincide o esiste un override, la catena si ferma e occorre rileggere quella configurazione: non si forza la sovrascrittura o si salta l’hash. Il file distribuito rimane intatto.

Destinazione: Bash del fisico pilota, directory della configurazione statica Netdata. Questa è la prima modifica di configurazione proposta dopo il debug: crea il solo override go.d.conf e riavvia Netdata, con una breve interruzione delle sue metriche. Non è un aggiornamento del pacchetto o dei driver e non riavvia il sistema, Ollama o Veeam. I database e il bind loopback non sono oggetto di modifica. L’output successivo dell’operatore conferma modifica e ricezione nel daemon; dettagli nella sezione finale del 16/10.

```bash
cd /opt/netdata/etc/netdata
printf '%s  %s\n' f9252399e7234c8168b10f7b3db371334af344969b1b872188193590a7233d92 /opt/netdata/usr/lib/netdata/conf.d/go.d.conf | sha256sum --check - && sudo sh -c 'set -euC; umask 022; sed "s/^#  nvidia_smi: no$/  nvidia_smi: yes/" /opt/netdata/usr/lib/netdata/conf.d/go.d.conf > /opt/netdata/etc/netdata/go.d.conf; grep -n "^  nvidia_smi: yes$" /opt/netdata/etc/netdata/go.d.conf' && sudo systemctl restart netdata.service
sleep 15
systemctl show netdata.service --property=ActiveState --property=SubState --property=Result
netdata_gpu_metrics_file=$(mktemp /tmp/netdata-gpu-metrics.XXXXXXXX)
curl --fail --silent --show-error --max-time 15 'http://127.0.0.1:19999/api/v1/allmetrics?format=prometheus&source=as-collected&prefix=netdata&timestamps=yes' --output "$netdata_gpu_metrics_file" && awk -v now_ms="$(date +%s%3N)" 'function fresh(s,a){sub(/^.*}[ \t]+/,"",s); if(split(s,a,/[ \t]+/)!=2) return 0; return a[1] ~ /^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$/ && a[2] ~ /^[0-9]+$/ && now_ms-a[2]>=-5000 && now_ms-a[2]<=60000} /^netdata_nvidia_smi_gpu_utilization\{/ && fresh($0){gpu++; if(gpu<=2) print} /^netdata_nvidia_smi_gpu_frame_buffer_memory_usage\{/ && fresh($0){vram++; if(vram<=3) print} /^netdata_nvidia_smi_gpu_temperature\{/ && fresh($0){temp++; if(temp<=1) print} END{printf "gpu_samples=%d vram_samples=%d temp_samples=%d\n",gpu,vram,temp; if(gpu==0 || vram==0 || temp==0) exit 1}' "$netdata_gpu_metrics_file"
```

La pausa di 15 secondi consente l’avvio dei primi cicli; è una scelta del collaudo, non un tempo garantito. Il filtro finale è quello già verificato e mantiene tutte le guardie su contesti, valori e tempi. Riscontro necessario: hash OK, riga nvidia_smi yes mostrata, servizio active/running e tutti e tre i contatori maggiori di zero con righe recenti. Un servizio attivo senza questi campioni non chiude la prova; un problema residuo richiederà stato/log del daemon, non una nuova installazione delle utility.

La trasformazione è stata provata in WSL con il file stock reale e sudo/systemctl sostituiti: copia nuova con sola riga NVIDIA cambiata, override preesistente preservato senza riavvio, sorgente con hash errato respinta prima della scrittura e riga attesa mancante che impedisce il riavvio. Rimuovendo noclobber il caso di sovrascrittura fallisce il criterio; rimuovendo il controllo dell’hash la sorgente alterata procede erroneamente. Ripristinati i comandi corretti e verificati invariati sorgente e script. Sono quattro casi isolati e due mutazioni, non una modifica già applicata al fisico.

## Ripristino dell’abilitazione, solo se necessario

Lo stato precedente osservato usa il file stock senza override go.d.conf. Il ripristino preparato verifica l’impronta della copia appena generata, la sposta in un archivio con nome distinto e riavvia il solo Netdata dopo aver verificato che go.d.conf non esista più. Il backup non viene cancellato. Un file modificato dopo l’intervento o una destinazione già esistente lascia la catena ferma, senza sovrascrittura. La sintassi è verificata; il ripristino sul fisico non è stato eseguito.

```bash
cd /opt/netdata/etc/netdata
printf '%s  %s\n' b1e511f160fd41e17442d09e3578db1940b6eecb55012c980b423f17d95974a4 /opt/netdata/etc/netdata/go.d.conf | sha256sum --check - && sudo mv -n /opt/netdata/etc/netdata/go.d.conf /opt/netdata/etc/netdata/go.d.conf.gpu-enabled-20261016 && test ! -e /opt/netdata/etc/netdata/go.d.conf && sudo systemctl restart netdata.service
```

## Raccolta GPU nel servizio confermata, 16/10/2026

L’operatore ha eseguito il blocco di abilitazione sopra: checksum dello stock OK, creazione del solo override locale e riga 84 nvidia_smi: yes. Dopo il riavvio di Netdata e l’attesa di 15 secondi, systemctl mostra ActiveState=active, SubState=running e Result=success. Il filtro dell’export è rimasto identico e restituisce gpu_samples=1, vram_samples=3, temp_samples=1. Sono cinque serie della stessa GPU, non cinque GPU e non cinque intervalli di misura.

| Contesto dell’export del daemon | Dimensioni e valori osservati | Criterio soddisfatto |
|---|---|---|
| nvidia_smi.gpu_utilization | gpu=0 | Un campione numerico finito; zero è utilizzo valido |
| nvidia_smi.gpu_frame_buffer_memory_usage | free=16582180864, used=35651584, reserved=487587840 byte | Tre dimensioni; used equivale a 34 MiB |
| nvidia_smi.gpu_temperature | temperature=36 Celsius | Un campione numerico finito |

Tutte le righe mostrano il timestamp sorgente 1792136744011 ms, corrispondente a 2026-10-16T07:45:44.011Z (09:45:44.011+02:00). La conversione è aritmetica dal valore ricevuto: non è l’ora di ricezione né quella del riavvio, che non sono state incollate. Il filtro confronta ogni timestamp con l’orologio dell’host, accetta età massima 60000 ms e anticipo massimo 5000 ms, oltre a contesto e valore finito; l’età esatta non compare nell’output. UUID e prodotto nelle cinque righe identificano la stessa scheda; l’identità rimane privata.

La precedente assenza di metriche hardware è risolta nell’osservazione successiva all’abilitazione esplicita e al riavvio. È una prova positiva della raccolta locale del daemon, oltre al debug separato precedente. Non isola l’effetto del solo riavvio da quello della configurazione. L’hash dell’override atteso deriva dal rendering locale; l’operatore ha letto la riga e il risultato funzionale, non ha riletto l’hash del file risultante. Non sono stati ripetuti dopo questo riavvio i controlli del listener e di ACLK: valgono come prove precedenti, non come nuove letture.

Restano misure su un intervallo rappresentativo dell’impatto CPU/RAM/I/O, raccolta sotto carico e dopo reboot, inferenza Ollama su GPU e ricezione sul Debian. La configurazione è persistita nel file e il servizio era già enabled, ma non è stata fatta una prova di reboot. Nessuna esposizione del listener o installazione centrale è attestata da questi cinque campioni.

Evidenze private: operator-gpu-enabled-record-20261016.txt conserva comandi/output selezionati e tutte le cinque righe restituite; operator-gpu-enabled-selected-20261016.json conserva campi, provenienza, criteri e limiti. Non è stato ricevuto il file integrale dell’export, né il suo nome temporaneo effettivo. Manifest SHA-256 aggiornato nei due progetti; l’impronta documenta i byte conservati, non certifica autonomamente l’esecuzione. Le fonti che motivano configurazione e formato sono [stock 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/config/go.d.conf), [configurazione collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors-configuration), [contesti NVIDIA 2.12.1](https://raw.githubusercontent.com/netdata/netdata/v2.12.1/src/go/plugin/go.d/collector/nvidia_smi/charts.go) ed [export Prometheus](https://learn.netdata.cloud/docs/exporting-metrics/prometheus), già consultate e registrate. Nessun nuovo comando remoto dell’assistente.

## Baseline del Debian del collettore preparata, 16/10/2026

Il passo successivo legge la VM Debian del collettore per verificare risorse effettive prima di scegliere RAM, vCPU, volumi e budget dello stack. L’indirizzo, l’account e la chiave SSH provengono dalla configurazione privata e dai runbook di installazione esistenti. Il comando di connessione compilato è conservato privatamente in collector-baseline-connection.ps1; si esegue dalla PowerShell della postazione Windows. Ottenuta la shell SSH sul Debian, il seguente blocco si incolla in quella shell. Non contiene installazioni, pulizie, resize o riavvii. Letture eseguite dall’operatore: riscontro ricevuto nella sezione successiva.

```bash
cd /
date --iso-8601=seconds
hostname
cat /etc/os-release
nproc
free -b
df -B1 --output=source,fstype,size,used,avail,pcent,target / /var /srv
df -i / /var /srv
lsblk -b -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS
findmnt -T /srv/ads -o SOURCE,TARGET,FSTYPE,OPTIONS
systemctl show rsyslog.service --property=LoadState --property=ActiveState --property=SubState --property=MemoryCurrent --property=CPUUsageNSec
systemctl list-timers ads-ilo-other-retain.timer --all --no-pager
sudo journalctl --disk-usage
```

free -b distingue memoria disponibile, cache e swap; df riporta byte disponibili e inode sui percorsi, senza sommarli quando appartengono allo stesso filesystem. lsblk con colonne esplicite descrive dispositivi/partizioni e mount; findmnt -T risale al filesystem che contiene il percorso, perciò un risultato sulla root non dimostra un volume dedicato né l’esistenza del percorso interrogato. La lettura di rsyslog descrive stato e contatori disponibili: MemoryCurrent è un’istantanea del cgroup e CPUUsageNSec è cumulativo, non una percentuale o un consumo sostenuto; proprietà non disponibili non si trasformano in zero. list-timers osserva pianificazione/ultimo giro, non certifica la cancellazione dei file. journalctl --disk-usage conta occupazione del journal del sistema visibile con sudo, non tutti i possibili namespace, spool o archivi. Conservare anche eventuali errori e righe mancanti, senza promuovere il blocco a riuscito per il solo ultimo comando.

Criterio di questo passo: confermare il bersaglio e OS, RAM/vCPU viste dal guest, byte/inode per filesystem, catena dei dispositivi e stato base della raccolta/retention. Non si dichiara ancora il dimensionamento accettato. Seguiranno conteggi e crescita degli archivi, code, serie temporali, pressione e picchi; prima di assegnare risorse servirà anche il margine reale del nodo/storage Proxmox. I 2 GiB dello snapshot restano un dato storico fino all’output di questa lettura. Fonti ufficiali e sezioni consultate nel registro delle fonti, sezione baseline Debian.

## Baseline Debian ricevuta; spazio AdS e attività swap da misurare, 16/10/2026

La prima baseline del Debian del collettore è stata eseguita dall’operatore nella shell SSH. Il comando date mostra 2026-10-16T10:29:01+02:00; quel valore precede le letture successive e non ne misura la durata o l’ora di ricezione. La trascrizione ricevuta è conservata nel livello privato collector/operator-baseline-transcript-20261016.txt, con campi separati in operator-baseline-selected-20261016.json e manifest SHA. Le misure riguardano questa VM, distinta dal fisico Ollama.

| Oggetto | Dato riferito | Significato e limite |
|---|---|---|
| OS e CPU | Debian 13 trixie, DEBIAN_VERSION_FULL=13.7; nproc=2 | Due unità di elaborazione disponibili al processo; non misura del carico o della capacità libera del nodo Proxmox |
| Memoria | total=2030473216, used=1107357696, free=223571968, shared=864256, buff/cache=884400128, available=923115520 byte | Totale 1936,41 MiB, disponibile 880,35 MiB; istantanea, non budget disponibile per tutto lo stack |
| Swap | total=1073737728, used=482140160, free=591597568 byte | Usata 459,80 MiB; non prova trasferimenti attivi o rallentamento attuale |
| Root ext4 | /dev/sda2, totale 16296308736, usati 6660640768, disponibili 8785534976 byte; 44% | 8,182 GiB disponibili su questa root, non sul volume AdS |
| Inode root | 1018000 totali, 153121 usati, 864879 liberi; 16% | Le tre righe di df riguardano lo stesso filesystem; non vanno sommate |
| Disco di sistema | sda=17179869184 byte (16 GiB); sda1=510656512 vfat /boot/efi; sda2=16667115520 ext4 / | Dimensioni del dispositivo/partizioni distinte dalla capacità utile del filesystem |
| Disco AdS | sdb=64424509440 byte (60 GiB), sdb1=64422412288 ext4 /srv/ads | Spazio libero e inode del filesystem non ancora interrogati |
| Mount AdS | findmnt: /dev/sdb1 su /srv/ads, ext4, rw,nosuid,nodev,noexec,relatime | Il volume dedicato risulta montato nella lettura; non misura dello spazio o prova della protezione dei futuri indici |
| Supporto ottico | sr0=792723456 byte, iso9660, nessun mount mostrato | Non verificati backing o impostazioni del dispositivo in Proxmox; nessuno sgancio effettuato |
| rsyslog | loaded/active/running; MemoryCurrent=10113024 byte; CPUUsageNSec=24227915000 | Cgroup circa 9,64 MiB, CPU cumulativa 24,227915 s; non RSS, percentuale o prova di consegna di ogni sorgente |
| Timer tecnico iLO | LAST 16/10 03:00:08, NEXT 17/10 03:00:00; un timer elencato | Etichette del fuso e unità attivata troncate nella stampa; risultato del service non letto |
| Journal del sistema | Archived and active journals take up 24M | Lettura sudo completata dopo un tentativo respinto; nessuna password nel materiale ricevuto, altri namespace/archivi non misurati |

Correzione dell’interpretazione iniziale in chat: df interrogava /, /var e /srv. Il mount separato è nella sottocartella /srv/ads; le tre righe sulla root sono quindi coerenti con lsblk e findmnt. Non è dimostrata alcuna divergenza o assenza del mount. Il comando iniziale non copriva spazio e inode del sottomount: la mancanza è nel perimetro della lettura, non un errore del Debian. Si completa con i percorsi effettivi dei due archivi. Riferimento: [df Debian](https://manpages.debian.org/trixie/coreutils/df.1.en.html), che descrive il filesystem contenente ciascun argomento.

Il margine osservato non autorizza ancora a installare e dimensionare Grafana, Loki, Prometheus o altri componenti. La crescita degli originali e delle copie, picchi e pressione, RAM/storage del nodo Proxmox e finestra di recupero restano da misurare. Nessun resize, remount, pulizia o riavvio è stato eseguito dall’assistente.

### Letture successive preparate, stesso terminale SSH del Debian

Il blocco seguente legge byte/inode dei due archivi, ne misura l’occupazione con una scansione circoscritta e osserva brevemente l’attività del sistema. Non legge il contenuto dei log. Output ancora atteso; conservare anche errori e il codice du_exit.

```bash
cd /
date --iso-8601=seconds
df -B1 --output=source,fstype,size,used,avail,pcent,target /srv/ads /var/log/ads-ilo-other
df -i /srv/ads /var/log/ads-ilo-other
sudo timeout --signal=TERM --kill-after=2s 20s du -x -B1 -s /srv/ads /var/log/ads-ilo-other
printf 'du_exit=%s\n' "$?"
vmstat -w -t 1 6
```

du -B1 misura spazio allocato in byte, distinto dalla lunghezza apparente dei file; -s limita la stampa ai totali, -x evita di attraversare filesystem annidati diversi. L’avvio con sudo può chiedere la password; il limite di timeout riguarda il comando dopo l’autenticazione, non il tempo per digitarla. Dopo 20 secondi viene inviato TERM, poi KILL dopo altri due se necessario: du_exit=124 indica scadenza, 137 un KILL; risultati incompleti o errori non diventano totali accettati. Il limite contiene la durata ordinaria della scansione, non è un limite di I/O né una garanzia temporale contro un processo bloccato nel kernel. Nessuna pulizia dei dati.

vmstat stampa sei rapporti, il primo con i tassi medi dal boot e i cinque successivi su intervalli di un secondo; i campi di memoria sono istantanei anche nella prima riga. Si leggono soprattutto si/so per i trasferimenti swap, wa per attesa I/O e r/b per processi pronti/bloccati. Un campione breve senza trasferimenti non certifica assenza di pressione nei picchi o adeguatezza dello stack. Fonti: [du](https://manpages.debian.org/trixie/coreutils/du.1.en.html), [timeout](https://manpages.debian.org/trixie/coreutils/timeout.1.en.html), [vmstat](https://manpages.debian.org/trixie/procps/vmstat.8.en.html), consultate il 16/10/2026.

## Archivi misurati e processo snapshot della postazione tracciato, 16/10/2026

L’operatore esegue le letture mirate del Debian. Date riporta 16/10 alle 10:45:30+02:00; la scansione du termina con du_exit=0. Il successivo vmstat mostra sei rapporti, con cinque intervalli correnti alle 10:45:48-52. Il tempo tra Date e il primo rapporto non è il tempo di esecuzione di du: include anche l’autenticazione e gli altri comandi.

| Area | Misura | Limite |
|---|---|---|
| Volume AdS /dev/sdb1 ext4 | Totale 63088406528, usati 45211648, disponibili 59805298688 byte; uso 1% | Disponibili 55,70 GiB; distingue capacità del filesystem dalla partizione e dal disco di 60 GiB |
| Inode AdS | 3932160 totali, 111 usati, 3932049 liberi, 1% riportato | Non misura crescita futura o numero di eventi |
| Archivio AdS | du 43110400 byte, 41,11 MiB | Spazio allocato del percorso, distinto dal totale di df; non byte/giorno |
| Tecnici iLO | du 45056 byte, 44 KiB; filesystem /dev/sda2 root | Restano sulla root, disponibile 8785526784 byte e uso 44%; non sono isolati sul volume AdS |
| Swap occupata | vmstat swpd=470840 KiB | Coerente con la prima baseline, non è un tasso di trasferimento |
| Cinque intervalli correnti | si=0, so=0, wa=0, idle=100 come riportato; r=b=0 | Cinque secondi osservati; percentuali arrotondate, non copertura dei picchi |

La prima riga vmstat dà i tassi dal boot e non si conta come sesto intervallo corrente. Un esito du riuscito chiude la scansione circoscritta, non dimostra salute storage, assenza di perdite o conservazione per l’intero periodo. Trascrizione integrale del testo ricevuto e campi strutturati nei file privati operator-capacity-followup-transcript-20261016.txt e operator-capacity-followup-selected-20261016.json, con SHA nel manifest. Restano fonti già lette: [df](https://manpages.debian.org/trixie/coreutils/df.1.en.html), [du](https://manpages.debian.org/trixie/coreutils/du.1.en.html), [vmstat](https://manpages.debian.org/trixie/procps/vmstat.8.en.html).

La lettura del solo snapshot Proxmox già sul disco delle 07:30:17, senza fuso dichiarato nel campo generated_at, aggiunge dati del nodo: RAM totale 134670643200 byte, used 107384188928, free 27286454272; swap usata 8589766656 su 8589930496. Le dieci VM running hanno massimi configurati per 135168 MiB (132 GiB), superiori ai 125,42 GiB fisici riportati: è una somma di configurazioni, non l’uso corrente o una prova di swapping attivo. Le sette fotografie giornaliere del 10-16/10 mostrano swap quasi piena; non misurano i picchi o le attività tra una fotografia e l’altra. Il pool thin che ospita il collettore riporta 367971323085 byte disponibili; data/metadata percent e margine sotto carico da verificare sul nodo prima di assegnare risorse.

Nello stesso snapshot la VM collettore ha 2048 MiB, balloon=0, due core, dischi 16G e 60G; il disco AdS riporta backup=0. È una proprietà osservata della configurazione, non prova di copie esterne o autorizzazione a modificarla. Configurazione e storia selezionate sono nel JSON privato proxmox-capacity-snapshots-20261016.json, con percorso e SHA della fonte. Nessuna interrogazione o modifica dell’hypervisor in questo giro. Le nuove risorse dello stack, il volume dati analitico, i budget e il percorso di custodia restano da definire.

La domanda sull’origine dello snapshot ha aperto una parentesi richiesta dall’utente: processo delle fonti vive sulla postazione, retention e tracciamento ISO nel progetto rete. Il task automatico è stato letto localmente; codice della retention verificato, cancellazione pianificata da abilitare manualmente. La parentesi non installa lo stack centrale né applica nuove politiche agli archivi del Debian.

## Sorgenti QA catalogate e ripresa con altro account preparata, 16/10/2026

Ricevuta chiusura manuale rete bff861b con push e verifica remoto riusciti; policy snapshot abilitata dall’operatore a 90 giorni, zero candidati/eliminati su 127 copie, primo giro pianificato ancora da osservare. Ripreso il focus Linux e poi richiesta la chiusura della sessione. Solo scaricate sul PC le immagini ufficiali Prometheus 3.13.4 LTS e Grafana OSS 13.2.4, digest registrati; nessuno stack/configurazione o container del pilota avviato, nessun nuovo flusso al Debian. Letta la segnalazione del produttore QA e il suo codice in lavorazione: due LXC Debian previsti (produzione/staging), istanza Ollama dedicata sul fisico GPU, non ancora censiti come in esercizio. Catalogo in docs/integrazione-log-qa-verifier.md: tecnici applicativi e tentativi, job, autenticazione, proxy, uso/costi riservati, runtime, OS e backup separati; coda cifrata e documenti esclusi dalla raccolta. Requisiti: messaggi italiani con tempi/codice/errore/batch/segmenti/tentativo; senza consenso, recupero locale transitorio almeno dieci minuti. Codice letto con default 600 s e intervallo 60 s, distinto dai retry della chiamata; nessuna prova runtime o finale del produttore svolta qui. Timestamp applicativo senza offset, intervallo segmenti non promosso a elenco completo; troncamento del messaggio non è sanitizzazione. Memoria, fonti, timeline, ISO e integrazione rete aggiornati nello stesso giro; specifica template e procedura di passaggio account aggiornate. Punto di ripresa: margine live Proxmox e pilota centrale metriche/log con guardie, normalizzazione e retention; GPU locale resta verificata 1/3/1, impatto aperto. Offline Nebula rimandato, Seeweb atteso, D7 e gate AdS invariati. Pulizia Codex in due tempi, sessioni vive protette e chiusura Git solo manuale. Nessun add/commit/push/deploy dell’assistente; modifiche parallele preservate.
