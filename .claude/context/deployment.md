---
generated-from-commit: 9ee87b4
generated-from-branch: main
generated-date: 2026-09-30
covers-paths:
  - config/**
  - docs/handoff-sviluppo-collettore.md
last-verified-commit: 48be07b
---

# Deployment

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

Comando del nuovo collaudo 54HP: `powershell -NoProfile -ExecutionPolicy Bypass -File "D:/log-collector/_notes/watch-nebula-publication-54hp.ps1"` sulla postazione Windows. URL della GUI locale fornito dal proprietario e registrato soltanto nel livello privato. Preparare la pagina di login prima dell'avvio, entrare soltanto dopo «Osservazione avviata» e premere Invio appena compare il pannello. Modello esplicito nello snapshot, budget dieci minuti/41 POST più due diagnostici dopo timeout; controllo storico del medesimo 54HP, senza API dell'agente o installazione VM. Il risultato reale resta atteso.

Il wrapper finale del 30HP è stato eseguito dalla postazione il 12/10: cinque richieste, un login osservato, conferma umana e risultato verificati; nessuna installazione VM. Il prossimo passo è individuare la GUI locale del 54HP dalla sua scheda Nebula. Il comando del 30HP descritto sotto resta documentazione della prova conclusa: non riusarlo per il secondo switch senza un mapping esplicito.

Prossima prova richiesta dall'operatore: `powershell -NoProfile -ExecutionPolicy Bypass -File "D:/log-collector/_notes/watch-nebula-publication-final.ps1"` sulla postazione Windows. Preparare prima la pagina locale di login del 30HP, attendere l'avviso di osservazione effettivamente avviata, eseguire un solo accesso e premere Invio nello stesso terminale subito dopo il pannello del browser. Osservazione fino a dieci minuti più richiesta in corso; report e conferma privati, nessuna installazione sulla VM. Questo tentativo sostituisce come prossimo lavoro il chiarimento dell'ora precedente; non ne risolve retroattivamente l'ambiguità.

Il confronto storico è versionato in `8dba118`, finestre ed estremi in `48be07b`, misurati sul campione 30HP. La prima osservazione di pubblicazione produce venti array vuoti con login locale confermato. Il wrapper privato `_notes/check-nebula-publication-followup.ps1` è già stato eseguito dall'operatore: due POST, controllo presente e candidato login alle 15:12:23, fuori dalla prima finestra. Report, mapping e token via stdin restano privati. Alla ripresa dopo il riavvio non serve ripetere il comando: resta da chiarire l'ora umana del login. Nessuna installazione o modifica al timer sulla VM. Il runbook distingue diagnosi, prima comparsa e ritardo massimo non misurato.

Sulla postazione di sviluppo, `python bin/ads-render.py --parametri config/parametri.yaml --sorgente config/collettore --destinazione <cartella-privata>` genera la configurazione del collettore; la stessa utility con `--sorgente config/proxmox-host` genera quella dell'host. `bin/ads-vm-command.py` stampa il comando per creare la VM e `bin/ads-pki.sh` emette i certificati sulla postazione amministrativa. `bin/ads-bootstrap.sh --prova <albero-generato> <cartella-tls> <cartella-chiavi>` mostra le azioni previste; l'esecuzione reale e ogni intervento sugli host richiedono un passo esplicito dell'utente e sono registrati nei runbook. I controlli prima dell'attivazione sono `nft -c`, `sshd -t`, `visudo -c` e `rsyslogd -N1`. Non c'è uno script di rilascio o rollback verificato nel repository; gli aggiornamenti eseguiti finora sono descritti nel runbook corrispondente.

Il nuovo script `bin/ads-ilo.py` usa un'istanza per IP iLO e le unità `config/collettore/etc/systemd/system/ads-ilo@.service` e `.timer`. I file di password, CA e impronta hanno percorsi privati sulla VM; prima dell'attivazione si esegue un giro manuale e si controllano formato delle righe, checkpoint e logout. L'installazione non è automatizzata dal bootstrap attuale. Il filtro rsyslog iLO è generato dal template usando `sorgenti.ilo` del file privato ed è stato installato l'08/10 sul collettore reale dopo backup, verifica delle impronte e validazione `rsyslogd -N1`. Il test inviato dalla iLO fisica è arrivato una volta nel file tecnico e zero volte nel file AdS; i login Browser riusciti, falliti e il logout restano nel file AdS. Per il flusso tecnico è attiva la ritenzione locale di 90 giorni: file giornalieri `root:root 0640`, directory `0750`, script di scadenza e timer alle 03:00. Il dry-run e un avvio manuale del service hanno trovato zero file scaduti; il timer è `enabled` e `active`. Restano da verificare gli altri canali di accesso iLO e la capienza nel tempo. Comandi, impronte e rollback sono nel `docs/runbook-componente-4-ilo.md`.

Lo stadio locale `bin/ads-nightly.sh` legge `/srv/ads` e scrive `/var/lib/ads`; `ads-nightly.service` lo esegue come `ads` e `ads-nightly.timer` lo pianifica alle 00:15. Prima dell'installazione vanno separati gli eventi tecnici e gli accessi non AdS, quindi verificati permessi e funzionamento sulla VM reale. Gli script e le unità del componente 5 sono versionati in `a031a4c`; il filtro iLO è versionato in `934aebd` e la configurazione generata è installata sul collettore dal 08/10.

## Variabili d'ambiente e segreti

Nebula: script, esempio JSON e unità `ads-nebula@` preparati e provati localmente, non installati. La futura configurazione privata è `/etc/ads/nebula/<SOURCE_LABEL>.json`, la chiave distinta dalla postazione è `/etc/ads/secrets/nebula/<SOURCE_LABEL>.key` (`root:root 0600`), consegnata al servizio con `LoadCredential`. Occorre predisporre stato e log `ads:ads 0750` e far coincidere etichetta `source` e nome dell'istanza. L'esempio blocca l'avvio finché mancano istante iniziale e finestra di recupero espliciti. Nessuna attivazione prima dei gate nel runbook Nebula, compresi completezza cloud, notifica esterna e interazione con D-1.

Il commit manuale `98c5dbd` contiene il poller e le unità. La prima verifica reale successiva è stata eseguita il 12/10 con `_notes/check-nebula-retention.ps1`: consumer del progetto rete per 120 ore di eventi e confronto locale dei cinque accessi noti, superato. Il proprietario esegue i singoli comandi e riferisce soltanto l'esito aggregato e il percorso privato, come prescritto per i comandi reali. Nessun file o credenziale installato sulla VM.

I valori di rete, sorgenti, amministratori e API sono raccolti in `config/parametri.yaml`, ignorato da git e compilato a partire da `config/parametri.example.yaml`. Gli alberi prodotti in `build/` possono contenerli e restano ignorati da git. Le credenziali dei componenti futuri appartengono a `/etc/ads/secrets/` sul collettore; i certificati TLS e le chiavi private seguono la procedura descritta nella scheda di sicurezza. `ADS_ROOT` è usata da `ads-bootstrap.sh` per indirizzare l'installazione in un albero di prova, non contiene un segreto.
