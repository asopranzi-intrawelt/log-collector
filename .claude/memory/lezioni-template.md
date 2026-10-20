# Lezioni per il template

> Le lezioni nate in questo progetto che valgono oltre il progetto, cioè che passano le due domande della sezione 16 di `.claude/PROJECT-SYSTEM.md`: restano vere tolti i nomi propri, e non sono già nella testa di chi lavora bene. Una voce per lezione, creata con `python .claude/templates/tools/lezioni-template.py nuova` nel giro di lavoro in cui la lezione nasce. Lo stato non si scrive qui: una lezione è recepita quando il template la elenca in `.claude/templates/lezioni-recepite.json`, che arriva con l'allineamento.

Adottato il: 2026-10-20

## L-001 - 2026-10-20 - La chiusura deve preservare gli argomenti del controllo lezioni

Nel template al commit `953e506`, `.claude/templates/tools/chiudi-sessione.ps1` assegna `$argLez = if (...) { @("raccogli", "--solo-locali") } else { @("controlla") }`. PowerShell riduce il ramo con un solo elemento a `System.String`; lo splatting `@argLez` passa `c`, `o`, `n` e così via al programma Python. Nei due progetti `chiudi -SoloControlli` stampava `invalid choice: 'c'` ma usciva con successo: la verifica delle lezioni non veniva eseguita.

Riprodotto con una funzione PowerShell che stampa gli argomenti ricevuti. Le copie eseguibili `tools/chiudi-sessione.ps1` del collettore e della rete sono state corrette con `$argLez = @(if ($bundle) { "raccogli"; "--solo-locali" } else { "controlla" })`; dopo la correzione `chiudi -SoloControlli` stampa l'esito reale di `lezioni-template.py controlla` ed è verde. La fonte del template va corretta, provata per entrambi i rami e propagata: le correzioni locali non sostituiscono il pacchetto canonico.
