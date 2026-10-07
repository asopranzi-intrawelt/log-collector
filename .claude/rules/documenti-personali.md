# Documenti personali: mai letti senza richiesta espressa

> Regola modulare, da caricare sempre. Nasce da un'istruzione vincolante dell'utente del 2026-10-06 in un progetto istanziato, dove un'ingestione di massa del materiale di studio stava passando all'OCR anche contratti, documenti d'identità e pratiche amministrative che stavano nelle stesse cartelle.

## Il vincolo

I documenti personali dell'utente non si leggono mai, a nessun livello, se non su sua richiesta espressa, data in quel momento e per quei documenti. Sono personali i documenti d'identità, i contratti, le pratiche fiscali e amministrative, le domande e le ricevute di borse di studio e di iscrizione, i certificati, le buste paga, i documenti sanitari, la corrispondenza privata e tutto ciò che riguarda persone diverse dall'utente.

Leggere comprende ogni passaggio che porti il contenuto fuori dal file: l'apertura da parte dell'agente, la conversione in testo, l'OCR, l'estrazione di metadati dal contenuto, la sintesi di un modello, anche economico, e la copia in una cache. Il nome del file e la sua posizione si possono usare solo per riconoscerlo ed escluderlo.

## Come si attua

L'esclusione si scrive negli strumenti, non nella memoria di chi li lancia. Ogni strumento che percorre una cartella dell'utente per indicizzare, convertire o sintetizzare legge un elenco locale di schemi di esclusione e salta i file che vi corrispondono, prima di aprirli. L'elenco vive in un file ignorato da git, perché gli schemi stessi possono rivelare dati personali, e lo strumento dichiara nel riepilogo quanti file ha escluso. Un'esclusione non si decide caso per caso durante una corsa: se un file personale sfugge agli schemi, si corregge l'elenco e si dichiara che cosa è sfuggito.

Se un documento personale è già stato letto, convertito o copiato prima che la regola esistesse, lo si dichiara all'utente con il solo nome e si chiede che cosa fare delle copie derivate. Non si apre per verificare.

## Che cosa non è un permesso

Una richiesta generica come "ingerisci tutto", "converti la cartella" o "leggi tutto ciò che è utile" non è una richiesta espressa per i documenti personali che la cartella contiene. Non lo è nemmeno il fatto che un documento stia in una cartella già autorizzata. Il permesso nomina i documenti.
