---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - config/**
  - docs/handoff-sviluppo-collettore.md
last-verified-commit: 05137cd920e98ed1c629a7832615f2d22cb9c476
---

# Deployment

## Unità candidate della quarantena, 28/10/2026

Per una futura installazione servono `ads-unclassified-retain.sh` e `ads-technical-retain.sh` in `/opt/ads/bin/`, più `ads-unclassified-retain@.service/.timer` e `ads-unclassified-health.service/.timer` a 0644. `systemd-analyze verify` passa su copie Debian. Il timer di ritenzione richiede l'istanza dei giorni approvati; quello di salute fa solo `--inspect`. Nessuna unità è installata. La soglia attuale dell'80% è sul filesystem intero e produce solo stato locale: prima dell'attivazione servono quota o volume isolato, prova del recapito dell'allarme e misura del costo orario sulla VM.

## Gate della variante strict, 28/10/2026

Il rendering strict non viene installato: con i parametri privati attuali manca una lista AdS di rete e il censimento dell'archivio VM è fallito per permessi. La chiave SSH e l'host key hanno consentito di raggiungere la VM, ma l'account non ha letto `/srv/ads/`; nessuna directory o riga di log è stata acquisita. Occorrono lettura autorizzata, riconciliazione dei mittenti silenziosi, test per fonte e decisione su ritenzione, capienza e allarme di `/var/log/ads-unclassified/`.

## Preflight inventario prima del nuovo filtro, 28/10/2026

Il comando candidato `ads-source-inventory.py` richiede la copia privata dei parametri e accesso di lettura alle directory immediate di `/srv/ads/`; non apre file di log. Non è installato sulla VM. Una sonda SSH equivalente di sola lettura è stata tentata il 28/10, ma l'accesso all'archivio è stato negato all'account usato. Un risultato locale `ok` non certifica sorgenti silenziose o flussi futuri. Prima di cambiare il catch-all del servizio occorrono inventario reale, proprietari, confronto con i parametri e smoke test per ogni sorgente attiva.

## Gate di attivazione Seeweb, 28/10/2026

Il supporto può verificare IP sorgente e rotta del tunnel. Il via all'inoltro segue la comunicazione dell'IP e l'installazione del ricevitore filtrato per la sola sorgente. Il percorso confermato dal provider non prova ancora ricezione, isolamento o persistenza sulla VM; nessun servizio è stato modificato in questo giro.

## Benchmark prima del timer, 28/10/2026

Il misuratore Linux va collocato accanto a `ads-verify.sh` ed eseguito con l'account che leggerà gli archivi. Il JSON minimizzato può alimentare il dossier privato di collaudo, ma serve ancora una misura su dati e carico rappresentativi della VM. Nessuna unità notturna è stata installata o attivata.

## Verifica dei manifest prima del timer, 28/10/2026

Il verificatore candidato rifiuta ora anche un manifest precedente simbolico nella modalità `--date`. La prova è locale in WSL; non sostituisce permessi, mount, misura dei volumi e prova della catena sulla VM. Nessuna unità notturna è stata installata o avviata.

## Gate dei parametri Windows, 28/10/2026

La copia privata di `config/parametri.yaml` è leggibile dopo l'accettazione del BOM iniziale, ma non contiene alcuna voce in `ads.elenco_approvato`. La prova locale del renderer si arresta senza creare il bundle. Installazione e ACL del servizio restano successive all'elenco approvato e alla prova sul pilota; non è stato modificato alcun host.

## Percorso di stato del pilota Windows, 28/10/2026

Prima della registrazione del servizio, il preflight candidato ora conferma che database `winevtlog.sqlite` e cartella `storage` siano nello stesso runtime. Questa è una guardia sul file di configurazione, non sui permessi effettivi: il runtime e il bundle dovranno ancora essere collocati con ACL ristrette e misurati sul pilota. Nessuna registrazione o avvio è stato eseguito.

## Servizio del pilota ancora da installare, 27/10/2026

Il bundle candidato include un controllo successivo all'installazione: richiede il servizio `fluent-bit` in esecuzione come LocalSystem e con avvio automatico, e confronta la riga di comando registrata con quella del processo attivo e i file verificati dal preflight. La prova locale sostituisce CIM con risposte sintetiche. Il controllo non modifica la macchina e non qualifica ACL, lettura Security, bookmark, recapito TLS o allarme. Prima dell'installazione servono nomina ed elenco AdS approvati, campioni reali e soglie di coda; nessun servizio è stato creato.

## Bundle Windows non distribuito, 27/10/2026

Il probe pubblicato legge policy effettiva e dimensione massima configurata del Security log, senza cambiare la macchina. Nel diff corrente misura anche dimensione del file, numero di record, modalità del canale, età del record più vecchio e ampiezza dello storico. Il minimo candidato di 256 MB è da confermare con il volume osservato; nemmeno l'età dello storico garantisce il replay dopo un fermo futuro. Un errore di permessi su `auditpol /get`, come il 1314 sul PC di sviluppo, produce stato non verificabile. Nessuna esecuzione sul pilota o installazione del servizio.

Il bundle candidato include un probe Security da lanciare soltanto sul pilota autorizzato, con accesso sufficiente al canale: la sua uscita non contiene identità né contenuto degli eventi. Un codice 0 qualifica GUID, bit della policy di sistema, dimensione massima configurata e schema dei sei ID campionati; non qualifica filtro sugli account reali, durata futura del log o esercizio. Il servizio e il probe non sono stati distribuiti.

Il candidato Fluent Bit Windows 5.1.3 è generato localmente per ciascun nome macchina con `bin/ads-render-windows.py`; la destinazione con le identità AdS reali `DOMINIO/utente` deve essere privata. I file `fluent-bit.conf` e `ads.lua` e la CA pubblica appartengono alla configurazione del pilota, ma la CA non è inclusa nel bundle. La prova con il binario Windows ha consegnato tre eventi e un heartbeat sintetici a un ricevitore TLS locale; il test Debian 13 ne ha verificato lo smistamento e la conservazione dei domini. Una prova locale separata ha recuperato un chunk dopo riavvio con input `dummy` e ricevitore inizialmente assente. Prima di installare il servizio: nomina ed elenco approvati, valori e grafie esatti dei domini sui campioni Security, certificato con SAN corrispondente, ACL del buffer, monitor della saturazione, consegna alla VM e replay degli eventi Security dopo fermo. Nessuna modifica a Windows o a NinjaOne eseguita.

Il renderer copia anche `ads-windows-queue-health.ps1` nel bundle. Il job NinjaOne candidato deve passare con `-ConfigFile` il medesimo `fluent-bit.conf` usato dal servizio; il monitor ne legge `storage.path` e rifiuta l'assenza o l'ambiguità del percorso. Prima di pianificarlo vanno misurate coda e spazio del pilota per fissare tre soglie esplicite, protetto il percorso dello script e provata la consegna dell'allarme. Il codice 3 indica controllo non riuscito, non stato sano; il servizio Fluent Bit richiede una condition separata.

Il bundle comprende `ads-windows-pilot-preflight.ps1`; sul pilota, dopo aver collocato il certificato CA pubblico, eseguirlo con `-BundleDir` e `-FluentBitExe` assoluti prima del servizio. Un esito `static_ok` qualifica solo i file e il dry run del binario 5.1.3 presenti in quel momento. Comando del servizio, permessi Security, TLS verso la VM, recapito e allarme restano passi di collaudo distinti.

Sulla VM il 27/10 `/srv/ads` è montato ext4 e rsyslog è attivo; `ads-nightly.timer` e `ads-silence.timer` non sono caricati. La misura dell'archivio non è riuscita perché l'account SSH non ha sudo senza password. Nessun timer attivato.

## Chiusura giornaliera AdS candidata, 26/10/2026

`ads-nightly.service` e `.timer` non sono installati sulla VM. Il servizio delle 00:15 ora locale chiuderebbe fino a 213 giorni mancanti, leggendo `/srv/ads` e scrivendo archivi e manifest in `/var/lib/ads`. `RequiresMountsFor=/srv/ads` ordina il servizio dopo il volume; `--require-log-mount` rifiuta il percorso non montato prima di qualsiasi scrittura. Oltre la finestra si ferma senza scrivere; al primo avvio non ricostruisce giorni anteriori a D-1. Prima dell'esercizio vanno risolti D7 e il perimetro AdS, provati utente `ads`, spazio e mount sulla VM, e predisposti TSA, WORM e allarme esterno.

Il preflight verifica tutta la catena locale, inclusi archivi e originali: prima di attivare il timer vanno misurati tempo e carico su dati rappresentativi e definito come mantenere l'ancoraggio verificabile dopo la futura retention.

Il job e il verificatore rifiutano directory simboliche nei percorsi dello stato. Prima della messa in esercizio va comunque verificato che mount e permessi reali impediscano a processi concorrenti di sostituire tali directory.

## Timer D6 candidato, 26/10/2026

`ads-silence.service` e `.timer` sono nel repository, non sulla VM: esecuzione alle 00:45 come `ads`, politica privata `/etc/ads/silence-policy.json`, report nel journal e uscita non zero in caso di assenza o errore. Il servizio verifica il mount `/srv/ads` e non apre rete. Chiede 213 giorni retrospettivi, entro la data `active_from` di ciascuna sorgente; oltre quell'orizzonte e senza prova di custodia resta un buco da esaminare. Il ricevente Windows candidato richiede l'IP pilota in `sorgenti.windows_pilota`; i marker non validi finiscono in `/var/log/ads-heartbeat-rejected/`. Per l'esercizio mancano lista e policy approvate, produttore Windows provato, ACL sulla VM, ritenzione del flusso rifiutato e allarme esterno. Il ricevitore QA su mount reale è stato provato solo nel namespace WSL, non sul volume di destinazione.

I test locali dell'output Syslog usano certificati fittizi: Fluent Bit 4.1.1 Linux e 5.1.3 Windows verificano il SAN grazie a `tls.verify_hostname on`. La versione ZIP Windows e l'hash sono fissati nel progetto; sul pilota restano interpolazione del nome macchina, CA e SAN reali, persistenza della coda e ricezione sulla VM durante e dopo un fermo, prima di abilitare l'avvio automatico.

Il servizio candidato `ads-heartbeat-rejected-retain@.service` cancella solo file giornalieri tecnici dopo una durata passata nell'istanza `%i`; il timer candidato gira alle 03:20 con `Persistent=true`. Entrambi restano nel repository. Prima di installarli servono misura del volume reale, durata approvata, prova dei permessi `root:root` e del namespace systemd e un allarme esterno per spazio o fallimento.

## Consegna QA ancora fuori dalla VM, 23/10/2026

Il candidato `--ssh-stdin` e il mittente QA sono nei due repository, non sul Debian e non nelle due LXC ancora da creare. Prima di qualsiasi invio reale: budget Proxmox e quota dell'archivio, account e chiave distinti per ambiente con comando forzato e `restrict`, fingerprint host verificata, valori di riserva misurati, ACL e retention dell'originale, allarme di saturazione e prova di restore. Il percorso operativo e i comandi segnaposto sono in `docs/integrazione-log-qa-verifier.md`; la promozione nella vista generale riguarda soltanto il record minimizzato.

## Mount Linux collaudati solo nel namespace locale, 21/10/2026

Due bind mount sullo stesso tmpfs di 16 MiB sono stati provati nella Ubuntu WSL locale, senza modificare il namespace principale o la VM Debian. Questo non decide dimensione e posizione del filesystem operativo: dipendenze systemd dal mount, ritenzione, allarme esterno, budget Proxmox e prova di carico restano da definire. Nessun deploy o cambio di rete.

## Confine QA ancora offline, 21/10/2026

Il controllo locale non è installato sul Debian e non apre un trasporto. Il produttore non chiama ancora il builder `qa-tech-v1`; i due LXC e l'archivio riservato non esistono. Prima del collegamento servono identità censite, canale autenticato, redazione provata all'indice, retention/budget e prova di recupero sotto guasto. M32e e ISO-30 restano in corso.

## Replay incerto ancora solo nel pilot, 21/10/2026

Il marker di tentativo vive nella stessa directory dei segmenti e richiede spazio riservato. Nessun servizio o timer del Debian è stato modificato; lo stato di invio incerto richiede esame umano e il codice non elimina marker o originali. Prima dell'esercizio servono prova Linux di mount limitato, fsync directory e arresto improvviso, budget di capacità, destinatario degli allarmi e procedura approvata di triage. Nessun cambiamento di rete o sorgente reale.

## Candidato spool vincolato, 21/10/2026

Nessun mount è stato creato e nessun file è stato installato sul Debian. Per passare dal pilot PC al percorso vincolato servono un filesystem piccolo dedicato con i due mountpoint verificati, dipendenze del servizio dal mount, prova di saturazione fisica e osservatore esterno degli allarmi. I due segmenti storici rimangono privati e non sono compatibili con la modalità vincolata senza trattamento manuale. Nessuna modifica a rete, apparati o VM in questo giro.

## Percorso del pilot ancora locale, 21/10/2026

L'isolamento degli originali riguarda solo il codice e i test del pilot sul PC. Nessun file è stato distribuito alla VM e nessuna nuova porta o sorgente è stata abilitata. La stima di completamento aggiunta nell'handoff non cambia i gate di installazione.

## Candidata Seeweb ancora fuori dalla VM, 20/10/2026

Il render dell'ingresso Seeweb e le unità `ads-seeweb-technical-retain@` sono nel repository, ma non installati sul collettore. La prova `tests/debian13/verifica-config.sh` ha validato nftables, rsyslog e isolamento dell'archivio con una sorgente loopback distinta; il test Linux della ritenzione usa file fittizi. Prima dell'installazione servono l'IPv4 reale, il percorso VPN verificato, campioni e categorie concordati con Seeweb, una durata di conservazione fondata sul volume e la prova del namespace systemd con archivio assente. Nessun evento Seeweb reale è stato raccolto.

## Login fallito 54HP verificato, tre casi API completati, 13/10/2026

La postazione ha osservato via API anche il fallimento locale del 54HP; successo, logout e fallimento sono verificati nei campioni. Questo riguarda il canale dalla sorgente a NCC/API, senza installazione del poller o token VM. Gate di produzione e parametri invariati; dettaglio nei passi 65-67 del runbook.

## Logout 54HP reale, correzione ancora locale

Il logout manuale è verificato nel payload API reale del 13/10 e nel parser corretto localmente, con 105 prove passate e una POSIX saltata su Windows. Non installato sulla VM. Wrapper failure 54HP preparato, prova reale attesa. Non ripetere il logout per il solo ricalcolo del parser; il report originale resta errore e i tempi positivi mancanti non sono ricostruiti. Gate di produzione invariati.

> Stato riconciliato al commit `2456511`, con poller Nebula preparato nel lavoro locale del 12/10. Commit, push e interventi sugli host restano operazioni manuali dell'utente.

## Modello di separazione fra test e produzione

Il gate di scelta del modello del catalogo `.claude/skills/separazione-ambienti/RIFERIMENTO.md` non risulta concluso né registrato in un ADR: non si assegnano sigle ai suoi assi per deduzione. Stato di fatto: i test locali e nei container usano fixture con indirizzi di documentazione; la produzione è la VM 210 Debian 13 su Proxmox, installata e verificata nei runbook. Il repository ha la sola branch `main`, un solo albero di lavoro e nessuna pipeline CI presente. Generazione, trasferimento e installazione della configurazione sono azioni manuali. Restano da decidere e documentare con l'utente il modello di separazione e una procedura di ritorno alla configurazione precedente; nessun ambiente staging del collettore risulta predisposto.

## Livelli

Il primo livello esegue `pytest`, Bats e controlli statici senza accedere alla rete di produzione. Il secondo verifica la configurazione generata in container `debian:trixie` per il collettore e `debian:bookworm` per l'host Proxmox, usando dati fittizi. Il terzo è il collaudo manuale sulla VM e sulle sorgenti reali, registrato in `docs/runbook-componente-1.md`, `docs/runbook-componente-2.md` e nei runbook del componente 3. I domini, gli indirizzi e gli account dell'ambiente reale sono nel file privato `config/parametri.yaml`, non in questa scheda.

Il componente iLO ha uno script Redfish preparato al primo livello, con unità e prove locali nel repository, ma non installato. La GUI mostra iLO Advanced; Remote Syslog è stato abilitato verso il ricevente UDP 514 e sul collettore reale sono arrivati login riusciti e fallito, con punti 3 e 7 superati come nel `docs/runbook-componente-4-ilo.md`. Redfish resta alternativo, con account di lettura, certificato e cartelle da collaudare solo se servirà. Il componente 5 è alla prova locale in WSL: script, servizio e timer sono preparati ma non installati sul collettore, per le ragioni nel `docs/runbook-componente-5-catena.md`.

## Alberi di lavoro

Un solo albero di lavoro, `D:/log-collector` su `main`; non è un ambiente di produzione. La VM di esercizio non è un albero git di questo repository.

## Comandi

Il wrapper dedicato 54HP è eseguito il 13/10: login osservato nella seconda risposta e risultato verificato localmente dai grezzi, nessuna installazione VM. Il comando sotto descrive una prova conclusa, non un nuovo login da ripetere. Prossimo collaudo dopo la chiusura della milestone: logout del 54HP con criterio predisposto per quel tipo di evento; l'osservatore attuale seleziona soltanto login.

Comando del nuovo collaudo 54HP: `powershell -NoProfile -ExecutionPolicy Bypass -File "D:/log-collector/_notes/archivio-sessioni/nebula-ilo/strumenti/watch-nebula-publication-54hp.ps1"` sulla postazione Windows. URL della GUI locale fornito dal proprietario e registrato soltanto nel livello privato. Preparare la pagina di login prima dell'avvio, entrare soltanto dopo «Osservazione avviata» e premere Invio appena compare il pannello. Modello esplicito nello snapshot, budget dieci minuti/41 POST più due diagnostici dopo timeout; controllo storico del medesimo 54HP, senza API dell'agente o installazione VM. Il risultato reale resta atteso.

Il wrapper finale del 30HP è stato eseguito dalla postazione il 12/10: cinque richieste, un login osservato, conferma umana e risultato verificati; nessuna installazione VM. Il prossimo passo è individuare la GUI locale del 54HP dalla sua scheda Nebula. Il comando del 30HP descritto sotto resta documentazione della prova conclusa: non riusarlo per il secondo switch senza un mapping esplicito.

Prossima prova richiesta dall'operatore: `powershell -NoProfile -ExecutionPolicy Bypass -File "D:/log-collector/_notes/archivio-sessioni/nebula-ilo/strumenti/watch-nebula-publication-final.ps1"` sulla postazione Windows. Preparare prima la pagina locale di login del 30HP, attendere l'avviso di osservazione effettivamente avviata, eseguire un solo accesso e premere Invio nello stesso terminale subito dopo il pannello del browser. Osservazione fino a dieci minuti più richiesta in corso; report e conferma privati, nessuna installazione sulla VM. Questo tentativo sostituisce come prossimo lavoro il chiarimento dell'ora precedente; non ne risolve retroattivamente l'ambiguità.

Il confronto storico è versionato in `8dba118`, finestre ed estremi in `48be07b`, misurati sul campione 30HP. La prima osservazione di pubblicazione produce venti array vuoti con login locale confermato. Il wrapper privato `_notes/archivio-sessioni/nebula-ilo/strumenti/check-nebula-publication-followup.ps1` è già stato eseguito dall'operatore: due POST, controllo presente e candidato login alle 15:12:23, fuori dalla prima finestra. Report, mapping e token via stdin restano privati. Alla ripresa dopo il riavvio non serve ripetere il comando: resta da chiarire l'ora umana del login. Nessuna installazione o modifica al timer sulla VM. Il runbook distingue diagnosi, prima comparsa e ritardo massimo non misurato.

Sulla postazione di sviluppo, `python bin/ads-render.py --parametri config/parametri.yaml --sorgente config/collettore --destinazione <cartella-privata>` genera la configurazione del collettore; la stessa utility con `--sorgente config/proxmox-host` genera quella dell'host. `bin/ads-vm-command.py` stampa il comando per creare la VM e `bin/ads-pki.sh` emette i certificati sulla postazione amministrativa. `bin/ads-bootstrap.sh --prova <albero-generato> <cartella-tls> <cartella-chiavi>` mostra le azioni previste; l'esecuzione reale e ogni intervento sugli host richiedono un passo esplicito dell'utente e sono registrati nei runbook. I controlli prima dell'attivazione sono `nft -c`, `sshd -t`, `visudo -c` e `rsyslogd -N1`. Non c'è uno script di rilascio o rollback verificato nel repository; gli aggiornamenti eseguiti finora sono descritti nel runbook corrispondente.

Il nuovo script `bin/ads-ilo.py` usa un'istanza per IP iLO e le unità `config/collettore/etc/systemd/system/ads-ilo@.service` e `.timer`. I file di password, CA e impronta hanno percorsi privati sulla VM; prima dell'attivazione si esegue un giro manuale e si controllano formato delle righe, checkpoint e logout. L'installazione non è automatizzata dal bootstrap attuale. Il filtro rsyslog iLO è generato dal template usando `sorgenti.ilo` del file privato ed è stato installato l'08/10 sul collettore reale dopo backup, verifica delle impronte e validazione `rsyslogd -N1`. Il test inviato dalla iLO fisica è arrivato una volta nel file tecnico e zero volte nel file AdS; i login Browser riusciti, falliti e il logout restano nel file AdS. Per il flusso tecnico è attiva la ritenzione locale di 90 giorni: file giornalieri `root:root 0640`, directory `0750`, script di scadenza e timer alle 03:00. Il dry-run e un avvio manuale del service hanno trovato zero file scaduti; il timer è `enabled` e `active`. Restano da verificare gli altri canali di accesso iLO e la capienza nel tempo. Comandi, impronte e rollback sono nel `docs/runbook-componente-4-ilo.md`.

Lo stadio locale `bin/ads-nightly.sh` legge `/srv/ads` e scrive `/var/lib/ads`; `ads-nightly.service` lo esegue come `ads` e `ads-nightly.timer` lo pianifica alle 00:15. Prima dell'installazione vanno separati gli eventi tecnici e gli accessi non AdS, quindi verificati permessi e funzionamento sulla VM reale. Gli script e le unità del componente 5 sono versionati in `a031a4c`; il filtro iLO è versionato in `934aebd` e la configurazione generata è installata sul collettore dal 08/10.

## Variabili d'ambiente e segreti

Nebula: script, esempio JSON e unità `ads-nebula@` preparati e provati localmente, non installati. La futura configurazione privata è `/etc/ads/nebula/<SOURCE_LABEL>.json`, la chiave distinta dalla postazione è `/etc/ads/secrets/nebula/<SOURCE_LABEL>.key` (`root:root 0600`), consegnata al servizio con `LoadCredential`. Occorre predisporre stato e log `ads:ads 0750` e far coincidere etichetta `source` e nome dell'istanza. L'esempio blocca l'avvio finché mancano istante iniziale e finestra di recupero espliciti. Nessuna attivazione prima dei gate nel runbook Nebula, compresi completezza cloud, notifica esterna e interazione con D-1.

Il commit manuale `98c5dbd` contiene il poller e le unità. La prima verifica reale successiva è stata eseguita il 12/10 con `_notes/archivio-sessioni/nebula-ilo/strumenti/check-nebula-retention.ps1`: consumer del progetto rete per 120 ore di eventi e confronto locale dei cinque accessi noti, superato. Il proprietario esegue i singoli comandi e riferisce soltanto l'esito aggregato e il percorso privato, come prescritto per i comandi reali. Nessun file o credenziale installato sulla VM.

I valori di rete, sorgenti, amministratori e API sono raccolti in `config/parametri.yaml`, ignorato da git e compilato a partire da `config/parametri.example.yaml`. Gli alberi prodotti in `build/` possono contenerli e restano ignorati da git. Le credenziali dei componenti futuri appartengono a `/etc/ads/secrets/` sul collettore; i certificati TLS e le chiavi private seguono la procedura descritta nella scheda di sicurezza. `ADS_ROOT` è usata da `ads-bootstrap.sh` per indirizzare l'installazione in un albero di prova, non contiene un segreto.
