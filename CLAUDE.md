# log-collector

> Istruzioni di team, versionate. Questo file è l'indice del progetto: indicizza i soli file satellite tracciati e descrive la procedura di ripresa. Le preferenze personali vivono in `CLAUDE.local.md`, ignorato da git, non qui.

## Cos'è questo progetto

Collettore centrale open source degli accessi degli amministratori di sistema (provvedimento Garante 27/11/2008), da realizzare come VM Debian 13 su Proxmox.

## Documenti di riferimento

- Cosa e perché: `docs/studio-collettore-ads.md`
- Come e in che ordine: `docs/handoff-sviluppo-collettore.md`
- Che cosa è stato fatto davvero, passo per passo con l'esito: `docs/runbook-componente-1.md`, `docs/runbook-componente-2.md`, `docs/runbook-componente-3-proxmox.md` e `docs/runbook-componente-3-firewall.md`, uno per componente o sorgente, da aggiornare a ogni passo eseguito su un host. Sono scritti per essere letti da chi non ha partecipato e sono la fonte da cui `D:/compilatore-documenti` può ricavare un documento per un cliente (richiesta dell'utente del 2026-10-02); i valori reali non vi compaiono e stanno in `config/parametri.yaml`
- Ratio del progetto, da leggere prima di decidere chi amministra che cosa: `docs/modello-di-custodia.md` (chi è amministratore di sistema non custodisce la prova dei propri accessi; tre livelli: raccolta, prova, analisi)
- Perché non Wazuh, e che cosa si prende dalla proposta dell'MSP: `docs/confronto-wazuh.md`
- Valori dell'ambiente: `config/parametri.yaml` (copia locale di `config/parametri.example.yaml`, fuori da git)

I due documenti non si importano a ogni avvio, perché da soli valgono oltre 30.000 caratteri e porterebbero il progetto sopra la soglia degli instruction file (sezione 24 di `.claude/PROJECT-SYSTEM.md`). Si leggono a richiesta: prima di lavorare su un componente si leggono la sezione dell'handoff che lo descrive e le sezioni dello studio che quella richiama, e la sezione 0 dell'handoff prima di decidere se un componente è bloccato.

## Regole di progetto

- Segui l'ordine di sviluppo della sezione 7 dell'handoff. Non iniziare un componente elencato come bloccato nella sezione 0 finché il relativo valore in `parametri.yaml` è vuoto: fermati e chiedi.
- Prima di implementare un componente, elenca le voci **[Non verificato]** che lo riguardano nei due documenti e proponi come verificarle. Non trattarle come fatti.
- Non inventare valori dell'ambiente (IP, nomi, VLAN, account AdS, URL): se mancano in `parametri.yaml`, chiedi.
- Nessun segreto nel repository: credenziali solo in `/etc/ads/secrets/` sul collettore; nel repo solo esempi con segnaposto.
- Nessun dato identificante reale nei file pubblicabili (IP, nomi, caselle personali dell'infrastruttura Intrawelt): criterio in `.claude/rules/anonymization.md`, controllo `python tools/Test-Anonymization.py`, che il pre-commit esegue e che blocca; i valori da cercare stanno in `_notes/.anonymization-patterns.json`, da estendere appena si scrive `config/parametri.yaml`.
- Non eseguire comandi su host reali (Proxmox, collettore, iLO, NAS, firewall) senza conferma esplicita per ogni comando. Il lavoro di default è scrivere codice, config e test in questo repository.
- Ogni riga di log scritta dagli script segue il formato `AdsLine` (sezione 4 dello studio): ora ricezione, sorgente, ora dichiarata, sistema, messaggio.
- I job notturni lavorano solo su D-1; un passo fallito fa fallire il job, nessun errore viene ignorato.

## Convenzioni di codice

- Documentazione e commenti in italiano; nomi di file, funzioni e variabili in inglese.
- Bash: `set -euo pipefail`, verificato con `shellcheck`; test con `bats`.
- Python 3 della distribuzione Debian 13, solo `requests` come dipendenza esterna; lint con `ruff`; test con `pytest` e risposte API registrate in `tests/fixtures/` (nessuna chiamata reale nei test).
- Struttura: `bin/` script, `config/` template di configurazione (rsyslog, nftables, chrony, fluent-bit, systemd), `tests/`.

## Progetto collegato: network-design

Il contesto della rete Intrawelt vive nel repository `D:\network-design` (schede in `.claude/context/`, storia degli interventi, snapshot Proxmox). Quando un componente del collettore dipende dalla rete (VLAN, firewall, sorgenti, NTP, raggiungibilità di iLO e NAS) se ne leggono le schede pertinenti prima di decidere, senza copiarle qui. Quando il collettore cambia qualcosa che riguarda la rete, per esempio una regola di firewall, una sorgente nuova o un indirizzo, l'aggiornamento va portato anche in network-design, con una sessione e un commit in quel repository. Il legame è registrato come ADR-004 in `.claude/memory/decisions.md`; la sua attuazione operativa è ancora da fare.

## Procedura di ripresa in una sessione nuova

Lo stato del progetto è interamente recuperabile su disco. All'inizio di una sessione si esegue `python tools/sync-codex-skills.py --check`, che controlla che Claude Code e Codex scoprano le stesse skill, poi si segue il percorso fisso che comincia con una verifica e non con una lettura: la skill `riprendi` esegue `tools/verifica-ripresa.py`, che confronta l'impronta registrata alla chiusura precedente con lo stato reale di git e dice che cosa una sessione caduta a metà non ha scritto. Solo dopo si legge `.claude/memory/index.md`, che dà branch, commit di riferimento, stato di verifica di ogni scheda e punto di ripresa. Se il progetto usa più alberi di lavoro, la memoria vale per la branch su cui è scritta: quando la verifica segnala un albero con la memoria più avanti, `index.md`, `progress.md` e `decisions.md` si leggono da quell'albero per percorso assoluto, senza copiarli né fonderli qui, come prescrive `.claude/skills/alberi-di-lavoro/RIFERIMENTO.md`. Si legge poi `.claude/context/current-work.md` se c'è una feature attiva, per sapere cosa è in lavorazione e quali sono i TODO e i limiti d'ambiente. Si invoca la skill `sync-context` per verificare il drift tra schede e codice, e si leggono solo le schede pertinenti al task, mai tutte insieme. Il work-log `.claude/memory/progress.md` e il registro `.claude/memory/decisions.md` forniscono la storia e le decisioni quando servono. Il materiale grezzo sotto `_notes/` si apre solo per verificare un requisito originale. Per una ripresa rapida esiste, quando presente, `_notes/RESUME-PROMPT.md`, privato e ignorato: riporta lo stato raggiunto e un prompt pronto da incollare. Va aggiornato alla fine di ogni sessione con il punto in cui si è arrivati, mentre lo stato canonico resta `.claude/memory/index.md`. Nello stesso momento l'agente scrive in `_notes/COMMIT-MSG.txt` il messaggio di commit proposto, una riga di al massimo 72 caratteri, e la chiusura la esegue l'utente con `chiudi-sessione.ps1` (in `.claude/templates/tools/`) dopo aver chiuso la sessione. Lo stesso vale per ogni milestone a metà sessione: a blocco concluso l'agente scrive il messaggio e propone `chiudi`, una milestone per commit, secondo la sezione "Milestone" di `.claude/rules/git-commands-format.md`.

## Indice dei file satellite tracciati

Memoria e meta-stato, sotto `.claude/memory/`, letti sempre a inizio sessione.

```
.claude/memory/index.md       snapshot e tabella di sincronizzazione, da leggere per primo
.claude/memory/progress.md    work-log append-only di passi e riconciliazioni
.claude/memory/decisions.md   registro ADR-lite delle decisioni architetturali
```

Schede tecniche, sotto `.claude/context/`, con frontmatter di riconciliazione.

```
.claude/context/STACK.md                stack, flussi di codice, ruolo architetturale dei file
.claude/context/design-and-security.md  paradigmi di design e sicurezza applicativa
.claude/context/deployment.md           livelli test e produzione, alberi di lavoro, hosting, comandi
.claude/context/dev-testing.md          test di sviluppo, runner, rotte mockate, hook
.claude/context/current-work.md         feature attiva, definition of done, domande aperte
.claude/context/roadmap.md              direzione e priorità
```

Regole sempre attive, sotto `.claude/rules/`, e skill canoniche richiamabili, sotto `.claude/skills/`. La distinzione fra i due livelli non è di forma ma di costo, e va conosciuta prima di aggiungere una regola: ogni file `.md` sotto `.claude/rules/` senza frontmatter `paths:` entra in contesto a ogni sessione e concorre al budget degli instruction file, mentre una skill si carica quando serve. Una norma che vale solo in certe situazioni vive quindi come `RIFERIMENTO.md` dentro la propria skill, e l'indice qui sotto dice quando invocarla. Lo strumento `tools/misura-istruzioni.py` misura il carico e fallisce oltre la soglia. Codex scopre le skill attraverso adapter sottili sotto `.agents/skills/`, che rimandano alla fonte canonica senza duplicarla. Lo standard di sistema completo è in `.claude/PROJECT-SYSTEM.md`.

Norme caricate su richiesta, una riga per situazione con le parole con cui si presenta, così che il caricamento non dipenda dal ricordare che la norma esista.

- Si scrive o si valuta una prova automatica, si chiude un difetto, una verifica manuale smentisce una suite verde, si sta per dichiarare completo un intervento il cui scopo era un effetto misurabile: skill `prove-che-misurano`.
- Un recupero web fallisce con 403 o con una pagina di verifica anti-bot, la fonte sta su Reddit o su Discord, serve la trascrizione di un video, si sta per annotare una fonte non letta: skill `fonti-non-recuperabili`.
- `git worktree list` mostra più di un albero, se ne crea o se ne rimuove uno, si deve decidere da dove leggere la memoria versionata: skill `alberi-di-lavoro`.
- Si inizializza o si allinea il progetto, oppure cambia il modo in cui si prova e si rilascia, e va deciso come separare test e produzione: skill `separazione-ambienti`.

## Apprendimenti recenti

Voci brevi e datate per le decisioni e le scoperte operative che non hanno ancora una casa definitiva. La voce nasce qui e migra appena possibile nella sede propria, `memory/decisions.md` se è una decisione architetturale, la scheda di contesto pertinente se è conoscenza strutturale, e si cancella da qui una volta migrata: questa sezione è un buffer, non un archivio.

```
- [2026-09-30] Le schede di network-design sono anonimizzate (IP sostituiti da un prefisso segnaposto): i valori dell'ambiente si prendono dagli snapshot in D:/network-design/output/, non dalle schede. Da migrare nella procedura di ADR-004.
```

## Vincoli di team

Le operazioni di `git add`, commit e push restano sempre manuali dell'utente: l'agente prepara i file, non committa. L'identità git è impostata a livello locale del repo secondo `.claude/rules/git-identity-and-repo.md`: autore `Alessio Sopranzi <asopranzi@intrawelt.com>`, remoto `git@github-corp:asopranzi-intrawelt/log-collector.git`. Questo progetto diverge dal template su un punto solo, registrato come ADR-002: i contributori umani sono due, e ogni commit porta il trailer `Co-authored-by: Tommaso Vezeni <tvezeni@intrawelt.com>`, che l'hook `.githooks/commit-msg` aggiunge da sé se manca; lo stesso hook continua a rifiutare qualunque attribuzione a un agente, come prescrive `.claude/rules/git-commands-format.md`. Lo stile di documentazione e di interazione è quello di `.claude/rules/interaction-style.md`, la cui sezione "Formattazione dei file Markdown" vincola anche la forma dei file `.md`: paragrafi su una riga sorgente continua, senza a capo manuali a metà frase. La convenzione si attua eseguendo `python tools/md-unwrap.py <file>` sul file appena scritto, e si verifica prima di un commit con `python tools/md-unwrap.py --check .`. Le convenzioni tipografiche si attuano con `tools/fix-accents.py`, `tools/fix-missing-accents.py` e `tools/fix-dashes.py` (verifica con `--check`), e i segni del testo generato si cercano con `python tools/lint-prosa.py <file>`, che il pre-commit esegue sui file in stage come avviso; la guida è in `docs/anti-slop/`. Claude aggiorna i file di memoria e di contesto in automatico a ogni giro di lavoro sostanziale, senza attendere una richiesta, secondo `.claude/rules/chat-non-e-memoria.md`; il versionamento resta sotto controllo umano perché commit e push sono manuali.
