# Modello di custodia: raccolta, prova, analisi

> Ratio del progetto, posta dall'utente il 2026-10-01 e da leggere prima di ogni scelta su chi amministra che cosa. Riorganizza lo studio in tre livelli che hanno requisiti, responsabili e costi diversi, e dichiara le conseguenze sulle decisioni già prese. Il testo del provvedimento citato è quello del Garante del 27/11/2008, letto il 2026-10-01 da garanteprivacy.it, docweb 1577499.

## Il principio

Nelle parole dell'utente: «gli amministratori di sistema non possono essere anche i custodi della prova dei nostri accessi, e vale per qualsiasi sistema gestito da noi». Il principio non riguarda solo l'MSP, a cui `docs/confronto-wazuh.md` lo applicava, ma chiunque amministri i sistemi registrati, cioè anche il personale interno di Intrawelt. Ne discende che chi amministra il collettore, essendo a sua volta un amministratore di sistema, può raccogliere i log ma non può essere l'ultima garanzia della loro integrità: quella deve stare in mano a qualcuno che non ha accesso in scrittura alla prova.

## Che cosa chiede il provvedimento

Il punto 4.5 chiede sistemi idonei alla registrazione degli accessi logici degli amministratori di sistema, con registrazioni che abbiano «caratteristiche di completezza, inalterabilità e possibilità di verifica della loro integrità adeguate al raggiungimento dello scopo di verifica per cui sono richieste», con riferimenti temporali e descrizione dell'evento, conservate «per un congruo periodo, non inferiore a sei mesi». Il punto 4.4 chiede che l'operato degli amministratori di sistema sia oggetto, «con cadenza almeno annuale», di un'attività di verifica da parte dei titolari o dei responsabili del trattamento. La parola «adeguate» rende il requisito proporzionato allo scopo: non prescrive una tecnologia, e la scelta di quanto spingere l'inalterabilità è una valutazione del titolare, da motivare.

## I tre livelli

Il primo livello è la raccolta: ricevere i log da tutte le sorgenti, normalizzarli nel formato `AdsLine` e scriverli per giorno e per sorgente. È il lavoro della VM Debian `ads-collector` costruita con il componente 1, e una VM Debian amministrata internamente va bene per questo livello, perché la raccolta non è la prova.

Il secondo livello è la custodia della prova: rendere le registrazioni di ciascun giorno inalterabili e verificabili da qualcuno che non può riscriverle. Gli elementi sono due, e servono entrambi. Un'ancora temporale esterna, cioè la marca temporale RFC 3161 di un servizio esterno sul manifest giornaliero, già prevista dallo studio (D3), che richiede un abbonamento a un fornitore di marche temporali. E un supporto immutabile su cui né Intrawelt né l'MSP abbiano accesso in scrittura o in cancellazione: lo studio prevedeva una cartella WORM sul NAS-HERO, ma il NAS-HERO è amministrato da chi è registrato, quindi la proposta dell'utente è un NAS dedicato a quel solo scopo, o un servizio equivalente, la cui amministrazione stia fuori da Intrawelt e dall'MSP.

Il terzo livello è l'analisi: qualcuno deve guardare i log, almeno una volta l'anno per il punto 4.4, e con una frequenza maggiore se lo scopo è anche accorgersi di un abuso quando accade. L'analisi richiede uno strumento, per esempio Wazuh, e soprattutto una persona o un servizio che lo usi, perché un sistema che nessuno guarda produce costo senza effetto. Il verificatore del punto 4.4 è il titolare o un responsabile del trattamento, non l'amministratore di sistema verificato.

## Chi amministra che cosa, al 2026-10-01

Il nodo Proxmox lo amministra l'IT Manager; lo stesso nodo è gestito da NinjaOne RMM, amministrato dall'MSP, che quindi vi accede attraverso l'agent. Il collettore lo amministrano Alessio Sopranzi e Tommaso Vezeni (ADR-007, ADR-008). Tutti e tre i soggetti sono amministratori di sistema dei sistemi registrati: è il dato da cui discende la richiesta di un custode della prova esterno a ciascuno di loro.

## Che cosa cambia nelle decisioni già prese

ADR-007 e ADR-008 restano validi per il primo livello: Alessio Sopranzi e Tommaso Vezeni amministrano la VM di raccolta, con account personali i cui accessi il collettore registra. Non bastano per il secondo livello, e non devono essere letti come se bastassero: la loro posizione è la stessa che `docs/confronto-wazuh.md` contestava all'MSP. Il residuo che resta scoperto anche con la custodia esterna va dichiarato: chi amministra il collettore può ancora alterare o sopprimere le righe del giorno in corso prima che la catena notturna le chiuda (studio, sezione 6), e la mitigazione possibile è ridurre quella finestra, per esempio con una marca temporale più frequente della giornaliera, o con un inoltro in tempo reale verso il custode.

Il componente 1 non cambia: la VM, il sistema operativo, il firewall locale, il tempo e il TLS servono al primo livello qualunque sia la scelta sugli altri due. Cambiano invece i presupposti del componente 5, il job notturno, che oggi scrive la copia WORM sul NAS-HERO e va ripensato quando il custode sarà scelto.

## Le scelte, con il tipo di costo

| Livello | Opzione | Tipo di costo | Chi la tiene |
|---|---|---|---|
| Raccolta | VM Debian sul Proxmox esistente (fatto) | nessun costo ricorrente esterno | amministratori interni (ADR-007, ADR-008) |
| Prova, ancora temporale | TSA qualificata in abbonamento (studio, D3) | ricorrente, per marca o a pacchetto | il fornitore della TSA, esterno per costruzione |
| Prova, supporto | NAS dedicato, amministrato da un terzo | acquisto più gestione del terzo | da decidere: né Intrawelt né l'MSP |
| Prova, supporto | archivio a oggetti con blocco in modalità di conformità presso un fornitore cloud [Inferenza] | ricorrente, a volume | da decidere; [Non verificato] se il blocco di conformità regga anche contro il titolare dell'account, come dichiarano i fornitori |
| Analisi | verifica annuale interna del titolare (punto 4.4) | tempo di persone | titolare o responsabile del trattamento, non gli AdS |
| Analisi | SIEM, per esempio Wazuh, con una persona che lo guarda | infrastruttura più tempo di analisi continuo | interno o MSP, su una copia dei log (`docs/confronto-wazuh.md`) |
| Analisi | SOC esterno, spesso dagli stessi fornitori delle VA | ricorrente, a contratto | il fornitore del SOC |

Gli importi non sono stimati qui, perché nessuna offerta è stata vista: la tabella dice di che natura è ciascun costo, non quanto vale.

## Opzioni di mercato, ricerca del 2026-10-01

Marca temporale. Le autorità di marcatura temporale qualificate italiane citate dalle fonti lette sono InfoCert, Aruba, Namirial e Intesi Group; prima di un contratto la qualifica va controllata sull'elenco di fiducia europeo, che qui non è stato consultato. Il manuale operativo del servizio di marcatura temporale di InfoCert (`pki.infocert.it/pdf/ICERT_INDI_TSA.pdf`, letto il 2026-10-01) dice che il richiedente «può utilizzare un proprio software attraverso protocollo definito in RFC 3161, RFC 5816 e profilato dallo standard ETSI 319 422 utilizzando URL e credenziali concordate con InfoCert»: è esattamente l'uso previsto dal job notturno, che invia l'impronta del manifest con `openssl ts` e riceve il file `.tsr`, senza mandare i log al fornitore. I prezzi trovati sono listini pubblici di rivenditori, annotati nel layer privato (`_notes/ricerca-tsa-prezzi.md`) perché gli importi non si scrivono nei file tracciati, e vanno confermati con un'offerta diretta. Sui quantitativi, una marca al giorno fa 365 marche l'anno e una all'ora 8.760: con gli stessi listini la cadenza oraria costa circa ventiquattro volte la giornaliera, ed è il prezzo di stringere la finestra del giorno in corso, che resta comunque un costo ricorrente piccolo rispetto alle altre voci della tabella. Un servizio REST di rivenditore che chiede l'URL del file da marcare, invece della sola impronta, non è adatto, perché porterebbe i log fuori dal collettore.

Intrusa (`intrusa.io`). È una piattaforma cloud di una società di Udine, certificata ISO 9001 e ISO 27001, che dichiara Log Manager, gestione delle vulnerabilità e valutazione della sicurezza, integrata con Microsoft 365 e Google Workspace, offerta anche attraverso MSP e distributori; un suo articolo cita il provvedimento del 27/11/2008 e i sei mesi di conservazione. Né la home né quell'articolo dicono come renda inalterabili i log, dove li conservi o chi amministri l'archivio, e il listino non è pubblico. In questo modello potrebbe coprire il livello della prova, e in parte quello dell'analisi, come terzo che non è né Intrawelt né l'MSP, a condizione che risponda per iscritto a quattro domande: con che cosa ancora l'integrità dei log (marca temporale qualificata, firma, supporto WORM); chi presso di loro e presso il cliente può cancellare o modificare un log prima della scadenza; dove sono conservati i dati e con quale retention; come si esporta la prova in una forma verificabile senza la loro piattaforma. Se la vendita passa dall'MSP, va chiarito anche che l'MSP non diventi amministratore della console, perché tornerebbe la posizione di ADR-010. Rispetto al collettore cambierebbe il primo livello, perché la raccolta andrebbe verso il loro cloud invece che verso una VM interna, e le sorgenti senza agent né API di rete (iLO, Proxmox) andrebbero verificate una per una [Non verificato].

## Chi fa la verifica annuale

Indicazione dell'utente del 2026-10-01: la verifica la fanno l'IT Manager e l'IT Assistant, e l'MSP in loro assenza. Il punto 4.4 la affida ai titolari o ai responsabili del trattamento, e il principio di questo documento vale anche qui: se l'IT Manager e l'IT Assistant sono a loro volta amministratori di sistema, verificherebbero il proprio operato, e l'MSP, in loro assenza, il proprio. Una forma che regge è la verifica incrociata con la firma di chi non è verificato: l'IT Manager e l'IT Assistant verificano gli accessi dell'MSP, l'MSP o un terzo verifica quelli interni, e il verbale annuale lo sottoscrive la Direzione o un responsabile del trattamento designato, che non è amministratore di sistema. Va scritto nel documento di nomina degli AdS.

## Domande per decidere

Chi custodisce la prova, cioè chi amministra il supporto immutabile e quale fornitore dà la marca temporale. Quanto stringere la finestra del giorno in corso, cioè se la marca temporale giornaliera sia adeguata allo scopo o serva una cadenza più fitta. Chi fa la verifica annuale del punto 4.4, e se oltre a quella si vuole un'analisi continua, interna con uno strumento come Wazuh o esterna con un SOC. Le tre risposte sono indipendenti e si possono dare in tempi diversi; finché non ci sono, si costruisce il primo livello, che serve comunque.
