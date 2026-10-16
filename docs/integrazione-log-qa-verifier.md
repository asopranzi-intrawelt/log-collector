# Integrazione dei log del servizio QA

Stato al 16/10/2026: requisiti dell’operatore, segnalazione del progetto produttore e lettura del codice in lavorazione. Nessun nuovo ambiente QA o flusso verso il collettore è attestato da questa ricognizione. La segnalazione locale è conservata nel progetto collettore come docs/segnalazione-intrawelt-qa-verifier.md; riferimenti reali, commit e impronte dei file letti stanno nel livello privato. Questo documento è condiviso con il progetto rete, dove la segnalazione originale resta un riferimento del progetto collettore.

## Infrastruttura e stato delle fonti

Il produttore prevede due ambienti Debian in LXC su Proxmox, produzione e staging, e un’istanza Ollama dedicata sul fisico GPU esistente. L’operatore parla della futura VM: prima del rilascio si riconciliano la forma effettiva dell’ospite, l’identità censita e le risorse; non si inventa una VM già creata. La segnalazione propone per ciascun LXC 2 vCPU, 4 GiB e circa 16 GiB di disco. Sono richieste di progetto, da includere nel budget del nodo insieme all’hub del collettore, non capacità riservata o accettata.

Il fisico GPU è distinto dall’ospite applicativo già censito. Due servizi Ollama sullo stesso fisico richiedono source_id, unità systemd, porta, utente e directory dei modelli distinti. I campioni hardware Netdata osservati sul fisico non provano installazione o disponibilità dell’istanza QA. Produzione e staging hanno identità e label environment separate.

## Catalogo iniziale per tipologia

| Tipologia | Originale da identificare | Destinazione e condizioni |
|---|---|---|
| Applicazione e tentativi LLM | Logger applicativi, stdout/stderr o journal dell’unità QA | technical: errori, tentativi, attesa, recupero, arresto e passaggio al backup consentito; correlazione per job/batch |
| Job e worker | Eventi di avvio, completamento, annullamento, blocco e recupero | technical: esito e tempi; nessuna lettura del contenuto della coda cifrata |
| Autenticazione e autorizzazione | Applicazione, proxy e sorgente identità, secondo le possibilità effettive | Flusso security da classificare; appartenenza AdS solo dopo verifica dell’evento e dei gate del progetto |
| HTTP e reverse proxy | Access/error log nginx e server ASGI | technical/security secondo evento; escludere corpi, token, cookie e query sensibili; IP e percorsi sono dati da governare |
| Uso e costi | Registro CSV prodotto dall’applicazione | Archivio autorizzato separato: contiene anche nome file e identità del richiedente; non entra integralmente nel flusso tecnico generale |
| Runtime Ollama dedicato | Journal del servizio e diagnostica del runtime | technical: distinguere istanza QA, istanza esistente e hardware comune; nessuna raccolta di prompt o risposte |
| Sistema operativo e amministrazione | Journal, SSH, sudo, servizi, aggiornamenti e agenti | technical oppure AdS secondo classificazione approvata; l’accesso Linux non coincide con quello applicativo |
| Hardware e risorse | Netdata sul livello fisico e sugli ospiti | Metriche separate dagli eventi; un allarme correlato può generare un evento tecnico |
| Backup e ripristino | Esiti dei job del sistema di backup | backup_outcomes, distinti dalla durata delle copie e dalla prova di recupero |

La coda cifrata, i documenti dei clienti, gli export e i risultati della revisione non sono sorgenti da copiare nel collettore. Anche un messaggio di errore del servizio può contenere dati sensibili: il limite a 300 caratteri osservato nel codice non costituisce una sanitizzazione. La conservazione del diagnostico originale richiede un perimetro autorizzato e accessi coerenti; la vista generale usa campi minimizzati. Identificativi dei job, batch, segmenti, utenti e file non diventano label Loki ad alta cardinalità.

## Eventi comprensibili e campi comuni

Applicare il [contratto di normalizzazione](normalizzazione-retention-capienza.md), preservando originale, localizzatore, parser e stato del parsing. Nel corpo del diagnostico, quando presenti, mantenere spiegazione in italiano, tipo di errore, codice HTTP, messaggio Ollama autorizzato, modello, job, batch, segmenti coinvolti, durata e tentativo n su m. Un errore DNS o di connessione può non avere un codice HTTP: il campo resta assente/null, senza inventare un numero. Distinguere tentativo della chiamata, ciclo di recupero del backend e stato finale del job.

La lettura del 16/10 trova un formato comune in app/logging_setup.py richiamato dalla webapp e dalla CLI: data e ora, livello, modulo e messaggio. Il formato della data è YYYY-MM-DD HH:MM:SS, senza offset. Non è quindi un timestamp UTC dimostrato: mantenere event_time_original e observed_at con offset noto; event_at rimane null finché il fuso della sorgente non è verificato. Il codice legge un intervallo tra primo e ultimo ID dei segmenti: non ricostruire da quell’intervallo una lista completa se gli ID non sono contigui.

app/local_client.py contiene messaggi italiani per tentativi falliti e riuscita dopo retry, distingue errori permanenti e transitori e misura la durata con orologio monotono. Il default letto è due tentativi e timeout di 120 secondi per chiamata: sono diversi dalla finestra di recupero del job. Non si deduce la durata effettiva sommando i soli default.

## Attesa senza consenso al backup

Requisito dell’operatore: senza consenso al backend esterno, attendere almeno dieci minuti il recupero del locale con tentativi regolari prima dell’arresto per indisponibilità transitoria. Il codice letto in app/fallback.py dichiara default di 600 secondi e intervallo di 60 secondi; un job riservato non abilita il backup anche se la preferenza generale lo consentisse. L’errore permanente, come un modello inesistente, segue un percorso distinto e può fermare subito il job. Questa è una lettura del codice in modifica, non una prova del tempo osservato o della configurazione finale distribuita.

Gli eventi da correlare sono indisponibilità, ingresso in attesa, tentativi periodici, eventuale recupero, scadenza e arresto; il passaggio al backend esterno richiede il consenso effettivo del job e un evento distinguibile. Nella verifica si registrano punto di partenza della finestra, durata monotona, timeout delle chiamate e concorrenza: dieci minuti non diventano un numero di tentativi presunto. Il silenzio di un job in attesa non deve essere scambiato automaticamente per perdita del processo.

## Accettazione prima dell’ingestione

Il produttore resta responsabile delle modifiche applicative e delle proprie prove; il collettore realizza e prova l’adattatore su campioni autorizzati. Servono esempi fittizi di connessione rifiutata, timeout, HTTP transitorio, errore permanente, recupero e scadenza, con confronto originale/campi/vista. Verificare formato sconosciuto e multilinea, offset assente, riavvio e rotazione, assenza di contenuti e credenziali, mancato consenso e identità dei due ambienti. I campioni reali richiesti devono essere minimizzati e conservati nel livello privato.

Prima di dichiarare operativo un nuovo flusso occorrono ambiente effettivamente creato e censito, versione/configurazione del produttore, origine e percorso del log, trasporto e coda, parser verificato, retention e budget approvati, permessi e prova di arrivo centrale. Nessuno di questi passi è chiuso dalla sola presenza del codice o dall’installazione Netdata sul fisico.

## Fonti e responsabilità

Fonti locali lette il 16/10/2026: segnalazione del produttore ricevuta nel collettore; istruzioni e decisioni infrastrutturali richiamate da quella segnalazione; file app/logging_setup.py, app/main.py, app/cli.py, app/local_client.py, app/fallback.py e app/usage_log.py. L’implementazione è ancora in lavorazione nell’altra sessione: impronte e passaggi effettivamente letti sono registrati privatamente e non sostituiscono il futuro commit. Il registro conserva separatamente requisiti riferiti dall’operatore, codice osservato e prove di esercizio ancora assenti. Fonti del contratto, retention e cardinalità nel [registro condiviso](fonti-osservabilita-linux.md).
