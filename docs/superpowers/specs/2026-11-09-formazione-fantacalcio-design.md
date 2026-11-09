# Consigliere di formazione Fantacalcio — design

**Data:** 9 novembre 2026 · **Stato:** approvato da Andrea il 9 novembre 2026

Nel documento, *(tua scelta)* indica ciò che ha deciso Andrea e *(scelta di Claude)* ciò che ho deciso io e che può essere cambiato.

## Perché

Andrea e i suoi due fratelli giocano in leghe diverse su Leghe Fantacalcio. Ogni giornata vogliono sapere chi schierare, tenendo conto di notizie, probabili formazioni, statistiche e avversari, senza inserire ogni volta la rosa e capendo il perché delle scelte.

Il progetto FantaLab 1.2 contiene già regole, metodo e calcoli a giornata finita, ma una sola lega con il 4-3-3 fisso e nessuna interfaccia: oggi serve un'IA in chat guidata a mano.

## Obiettivi

1. Dire la **migliore formazione tra i giocatori della propria rosa**, con le regole della propria lega. *(tua scelta)*
2. Dire la **migliore formazione in assoluto** tra tutti i giocatori della Serie A, e confrontarla con la propria. *(tua scelta)*
3. Tenere salvate più leghe, ciascuna con rosa e regole, modificabili quando serve. *(tua scelta)*
4. Spiegare le scelte: motivo per ogni giocatore, esclusi, dubbi, fonti e ora del controllo. *(tua scelta)*
5. Funzionare su Windows e Mac con un'interfaccia grafica, avviando con un pulsante la ricerca in un terminale e riportando poi i risultati nell'interfaccia. *(tua scelta)*
6. Funzionare con diverse IA, anche locali, senza chiavi API: lo strumento lancia il programma a riga di comando dell'IA scelta. *(tua scelta)*

## Non obiettivi

- Inserire la formazione nell'app: la inserisce sempre la persona. *(tua scelta)*
- Asta, mercato automatico, notifiche, app per cellulare, versione online.
- Crediti e prezzi dei giocatori: non si leggono e non si controllano, perché i prezzi cambiano e i crediti di una persona possono aumentare. *(richiesta del fratello di Andrea sulla lega grossa)* Di conseguenza la migliore assoluta ignora il costo e può contenere giocatori che non ci si può permettere.
- Mantra nella prima versione: solo Classic. *(scelta di Claude)*
- Modalità senza IA. L'avevo proposta, ma l'interfaccia più la riga di comando la rendono superflua. *(scelta di Claude)*
- Stimare probabilità di vittoria o chiedere il numero degli avversari, come già stabilito in FantaLab.
- Due formazioni in gara con hash e congelamento come in FantaLab: qui si sceglie uno stile alla volta. Ogni risultato resta comunque salvato con data e ora. *(scelta di Claude)*

## Cosa non deve mai succedere

- **Accedere a una lega.** Niente login a Fantacalcio, credenziali, token, API private (`leghe.fantacalcio.it`, `apileague.fantacalcio.it`) o automazione del browser. *(tua scelta)*
- Scaricare in massa pagine di fantacalcio.it o aggirare un blocco.
- Inventare un dato: se una fonte non è leggibile, il risultato lo dice.
- Consegnare una formazione che viola moduli, ruoli o rosa.
- Dare per sicuro un giocatore su cui le fonti non concordano: va segnato come dubbio e, se l'infortunio è in dubbio, resta fuori.

## Fonti e rischio accettato

Si possono leggere le **pagine pubbliche di fantacalcio.it**, senza login: voti *(tua scelta)*; probabili formazioni *(ipotesi di Claude, che Andrea non ha contestato)*. Per il resto si usano siti di club e testate sportive.

Il **listone** con i ruoli Classic non viene letto in automatico: la persona lo scarica a mano e lo carica nello strumento, una volta e poi quando cambia. *(tua scelta)*

Si legge solo quando qualcuno preme il pulsante, e solo le pagine necessarie.

I [termini d'uso di Fantacalcio](https://www.fantacalcio.it/termini-e-condizioni) vietano l'accesso automatico alle pagine senza autorizzazione scritta, e prevedono sanzioni fino alla cancellazione di account e leghe in cui avvengono violazioni. Leggere le pagine pubbliche resta quindi un **rischio accettato da Andrea**: non accedere alle leghe lo riduce, ma non lo elimina. Anche i suoi fratelli devono poterlo valutare per i propri account: al primo avvio lo strumento mostra questo avviso e chiede una conferma esplicita. *(scelta di Claude)*

## Come funziona

### Le quattro schermate

Bozze approvate in `docs/superpowers/specs/bozze-interfaccia/` (dati inventati):

1. **Le mie leghe** (`s1.png`): leghe salvate, rosa, regole, scelta dell'IA, stile, pulsante "Cerca la formazione".
2. **Ricerca in corso** (`s2.png`): si apre un terminale in cui si vede il lavoro dell'IA.
3. **Risultato**, con tre schede:
   - **Campo** (`s3.png`): formazione, capitano, giocatori in dubbio evidenziati, panchina in ordine.
   - **Motivi** (`s4.png`): motivo e affidabilità per ogni giocatore, esclusi spiegati, link alle fonti.
   - **Confronto** (`s5.png`): propria rosa accanto alla migliore assoluta, con la differenza più grande.
4. **Stile:** "Punti sicuri" corrisponde alla strategia A di FantaLab, "Più rischio" alla B. *(aggiunta di Claude, approvata con le bozze)*

Una lega a scelta libera, come quella di FantaLab, non ha una rosa: mostra solo la migliore assoluta e niente Confronto.

Le bozze mostrano un caso solo. Il risultato si adatta alla lega: il capitano compare solo dove il fattore capitano è attivo e, dove lo Switch è attivo, si aggiunge il cambio consigliato, che nelle bozze non è disegnato. *(scelta di Claude)*

### Le parti

*(scelta di Claude: solo Python con la libreria standard, gli script esistenti sono già in Python e non serve installare altro)*

- **Programmino locale:** si avvia con un doppio clic (`.command` su Mac, `.bat` su Windows), apre la pagina nel browser e ascolta solo su `127.0.0.1`.
- **Dati:** file JSON in una cartella locale, uno per lega, più una cartella per ogni ricerca con richiesta, risultato e data. Le ricerche precedenti non vengono sovrascritte.
- **Skill `SKILL.md`:** nel formato comune delle Agent Skills, contiene metodo, criteri, elenco delle fonti e formato del risultato. È l'unica parte da mantenere per tutte le IA.
- **Collegamenti alle IA:** una tabella con il comando per ogni programma (Gemini CLI, Claude Code, Codex, OpenCode con Ollama), modificabile senza toccare il codice.
- **Controllo finale:** codice che verifica la proposta contro le regole della lega.

### Una ricerca, passo per passo

1. La persona preme il pulsante. Il programmino crea la cartella della ricerca con rosa, regole, stile, data e ora.
2. Apre un terminale nativo con il comando dell'IA scelta, che riceve la skill e la cartella.
3. L'IA cerca le partite della giornata, compila una scheda per i giocatori della rosa e per i candidati alla migliore assoluta, poi propone le formazioni.
4. Scrive il risultato in un file JSON con un formato stabilito.
5. Il controllo finale lo verifica. L'IA lo esegue dentro la stessa sessione, così non perde la ricerca già fatta, e corregge gli errori al massimo due volte. Il programmino lo ripete comunque prima di mostrare il risultato: se fallisce, mostra l'errore senza formazione. *(scelta di Claude)*
6. La pagina, che controlla periodicamente la cartella, mostra il risultato.

**Scheda giocatore** (idea presa da fantabot): disponibilità, titolarità, forma, rigori e piazzati, avversario, riassunto, link letti e confidenza, dove zero significa "non ho trovato nulla", non "giocatore medio".

**Quanto cercare:** niente ricerca su tutti i 500 giocatori. La ricerca parte dalle partite della giornata e si concentra su rosa e candidati, così funziona anche con IA più lente. *(scelta di Claude)*

### Regole di una lega

Si impostano una volta con un modulo. Le tre leghe reali, lette dagli screenshot in `regole/`, sono già pronte come modelli modificabili; FantaLab resta un quarto modello per la lega a scelta libera. *(scelta di Claude)*

Tutte e tre sono Classic, con rosa 3P+8D+8C+6A e voti Fantacalcio.

| Regola | Pensionati | Grossa | F1 |
|---|---|---|---|
| Moduli | 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1 | gli stessi 7 | gli stessi 7 più 3-6-1 |
| Panchina | minimo 2P e 3 per D, C, A; massimo 14 | esattamente 1P+2D+2C+2A | libera |
| Sostituzioni | illimitate, stesso ruolo (Traditional) | 7, stesso ruolo (Traditional) | 5, anche di ruolo diverso se manca il pari ruolo e il modulo risulta ammesso (Hybrid) |
| Switch | sì, Plus | no | non visibile |
| Capitano | no | sì: voto ≤5,5 +0; 6 +0,5; 6,5 +1; 7 +1,5; ≥7,5 +2, senza raddoppio | non visibile |
| Modificatore difesa | no | fasce da <6 a ≥7,25: 1, 2, 3, 4, 5, 6, 6 | stesse fasce: 0, 1, 1, 3, 3, 6, 6 |
| Player of the match | +0,5 | 0 | +1 |
| Ammonito senza voto | conta 5,5 | no | no |
| Anticipo sulla scadenza | 15 minuti | 0 minuti | 1 minuto |

Dove è attivo, il modificatore difesa si calcola sul voto senza bonus, con il portiere e i 3 migliori difensori, e solo schierando almeno 4 difensori: per questo può influire sulla scelta del modulo. Gli altri bonus coincidono: gol e rigore segnato +3, rigore parato +3, rigore sbagliato −3, assist +1, porta inviolata +1, gol subito −1, autogol −2, ammonizione −0,5, espulsione −1.

**Cosa deve saper gestire il modulo delle regole:**
- **Panchina:** numero fisso per ruolo, minimi e massimo, oppure libera.
- **Switch:** dove è attivo, lo strumento consiglia un cambio tra il titolare più in dubbio e una riserva. Il controllo verifica che la riserva sia in panchina e che il modulo risultante sia ammesso. *(scelta di Claude: un solo cambio, perché gli screenshot non dicono se ne sono ammessi di più)*
- **Dati non visibili:** capitano e Switch della lega F1 restano da compilare, e la lega non può avviare una ricerca finché non sono impostati. *(scelta di Claude)*

**Cosa non viene salvato,** perché non cambia la formazione consigliata in questa versione: crediti, soglie gol, punteggi della competizione F1, limita vittoria e pareggio, rose invisibili, formazioni nascoste, formazione non schierata. *(scelta di Claude)*

**Scadenza:** si calcola dall'orario della prima partita meno l'anticipo della lega. *(ipotesi di Claude, da confermare nell'app)*

Ogni lega ha anche le sue preferenze, ad esempio "questi giocano sempre se disponibili" (idea presa da fanta-lineup-bot).

La rosa si incolla come testo o si scrive nome per nome. I nomi vengono abbinati al listone caricato, e quelli non trovati o ambigui sono segnalati alla persona senza tirare a indovinare. Il ruolo di un giocatore si può correggere per singola lega, perché una lega può personalizzare i ruoli: la lega dei pensionati ha l'opzione "Definizione ruoli". *(scelta di Claude)*

### Sicurezza

L'IA legge pagine web, che potrebbero contenere istruzioni malevole. Il suo testo è trattato come dato. Dove il programma dell'IA lo consente, i permessi si limitano a lettura del web, scrittura nella cartella della ricerca ed esecuzione del controllo. Non si usano mai le modalità "approva tutto" e non si conservano credenziali. Un'IA che non consente questi limiti resta utilizzabile: le conferme compaiono nel terminale e la persona le dà a mano, con un avviso accanto al suo nome nella lista delle IA. *(tua scelta)*

### Confronto a fine giornata (seconda fase)

Dopo la prima versione: lettura dei voti pubblici, punteggio della formazione proposta e migliore formazione possibile a posteriori, per capire se i consigli migliorano. Si riusano `ottimizza.py` e `confronta_strategie.py` di FantaLab, che oggi gestiscono solo il 4-3-3 fisso e vanno estesi. Le giornate G10 e G11 archiviate restano intatte.

## Cosa resta da verificare

Nessuno di questi punti è stato provato. La pianificazione deve iniziare da una prova rapida, perché possono cambiare il progetto.

1. **Lettura delle fonti:** le pagine di voti e probabili di fantacalcio.it potrebbero non essere leggibili dagli strumenti delle IA. Nel caso, servono altre fonti o un inserimento a mano.
2. **Listone:** va verificato che il file sia scaricabile dalla pagina pubblica, senza login, e in quale formato. Se non lo è, serve un'altra fonte o un inserimento a mano.
3. **Comandi e permessi reali** di Claude Code su Mac e Gemini CLI su Windows, inclusa la lettura delle skill: il supporto a `SKILL.md` è stato verificato soltanto su fonti di terzi.
4. **Gemini:** i fratelli devono avere il programma a riga di comando, non solo il sito o l'app, e le fonti non concordano sui limiti attuali dell'accesso gratuito. Una ricerca intera deve starci dentro.
5. **Modelli locali:** vanno provati su un modello preciso. Non si promette che funzionino tutti; un modello locale può non avere una ricerca web, ed è per questo che la skill elenca le pagine da leggere.
6. **Termini degli altri siti:** vanno controllati prima di inserirli nell'elenco delle fonti.
7. **Regole non certe della lega F1 e dello Switch:** capitano e Switch della F1 non si vedono negli screenshot, l'elenco dei moduli F1 potrebbe continuare oltre il 3-6-1, e va chiarito quanti Switch ammette la lega dei pensionati.

## Requisiti per chi lo usa

Python 3 e almeno un programma IA installato e con accesso già fatto. Nella prima versione sono garantiti **Claude su Mac** (Andrea) e **Gemini su Windows** (i fratelli). *(tua scelta)* Le altre IA restano in tabella, anche quelle locali, ma senza garanzia: un modello locale non blocca l'uscita. *(scelta di Claude)* Serve una guida passo per passo adatta a chi non usa il terminale, perché i fratelli non devono scrivere comandi. *(scelta di Claude: nessun pacchetto installabile nella prima versione, si può aggiungere se Python risulta un ostacolo)*

## Quando è finito

- Partendo da zero con la guida, Andrea con Claude su Mac e un fratello con Gemini su Windows salvano lega e rosa e ottengono una formazione valida, su una giornata vera.
- Riaprendo lo strumento, lega e rosa sono ancora lì.
- Il controllo finale ha test su moduli, ruoli, rosa, doppioni, panchina, capitano e Switch, con le regole di tutte e tre le leghe.
- Una prova conferma che durante una ricerca non viene contattato alcun indirizzo di `leghe.fantacalcio.it` o `apileague.fantacalcio.it`, per quanto osservabile dai log dell'IA.

## Lasciato a chi costruisce

Struttura dei file, formato esatto dei JSON, aspetto finale nel rispetto delle bozze, numero di candidati per ruolo, come aprire il terminale su ciascun sistema, dove estrarre FantaLab nel progetto.

## Riferimenti

- `regole/`: screenshot delle impostazioni delle tre leghe
- `FantaLab_v1.2_2026-27.zip`, in particolare `guide/01_REGOLAMENTO.md`, `guide/02_PREVISIONE.md`, `guide/08_DUE_STRATEGIE.md`, `strumenti/`
- [eltondy93code/fantabot](https://github.com/eltondy93code/fantabot) e [francecesco/fanta-lineup-bot](https://github.com/francecesco/fanta-lineup-bot): da consultare solo come spunto. Le loro parti di login e invio non vanno riusate. fanta-lineup-bot non dichiara una licenza, quindi non va copiato codice.
