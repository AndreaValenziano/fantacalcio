# Consigliere di formazione — guida

Il consigliere ti dice chi schierare nella tua lega di Fantacalcio e ti spiega perché. Lo usi dal browser, ma tutto resta sul tuo computer. Per le ricerche usa un'IA che hai già, Claude o Gemini, e la apre in una finestra a parte.

Non entra mai nella tua lega e non conosce la tua password. La formazione la inserisci sempre tu nell'app.

Le cose da fare una volta sola sono i passi 1–4. Poi, ogni giornata, bastano i passi 6 e 7 (e, a giornata finita, l'8).

---

## 1. Installa Python (una volta)

Python è il programma che fa funzionare il consigliere. Serve la versione **3.11 o successiva**.

**Windows**
1. Vai su https://www.python.org/downloads/ e premi il pulsante giallo "Download Python 3…".
2. Apri il file scaricato.
3. Nella prima schermata **spunta "Add python.exe to PATH"** in basso, poi premi "Install Now".
4. Alla fine premi "Close".

**Mac**
1. Vai su https://www.python.org/downloads/ e premi "Download Python 3…".
2. Apri il file `.pkg` scaricato e segui i passaggi fino a "Chiudi".

## 2. Installa l'IA e fai l'accesso (una volta)

Ti serve il **programma a riga di comando** dell'IA, non solo il sito o l'app per il telefono. Queste istruzioni cambiano spesso: segui quelle ufficiali del momento.

- **Claude** (consigliato su Mac): le istruzioni ufficiali di Claude Code sul sito claude.com. Serve un abbonamento Claude.
- **Gemini** (consigliato su Windows): https://github.com/google-gemini/gemini-cli. Si accede con un account Google.

L'installazione chiede di copiare un comando nel Terminale (Mac) o nel Prompt dei comandi (Windows). È l'unica volta che serve: copialo così com'è, premi Invio, poi scrivi `claude` oppure `gemini` e segui le istruzioni per l'accesso. Quando l'IA ti saluta, chiudi la finestra.

Gemini gratuito ha un limite di richieste al giorno. Se una ricerca si ferma per questo, riprova più tardi.

## 3. Scarica il consigliere (una volta)

Scompatta lo zip `consigliere-formazione.zip` in una cartella a tua scelta, ad esempio Documenti.

## 4. Avvia il consigliere

- **Mac:** fai doppio clic su `avvia.command`.
  La prima volta il Mac può dire che il file "non può essere aperto". In quel caso apri Impostazioni di Sistema → Privacy e sicurezza, scorri in basso e premi **"Apri comunque"** accanto ad `avvia.command`. Le volte successive basta il doppio clic.
- **Windows:** fai doppio clic su `avvia.bat`.
  Se compare "Windows ha protetto il PC", premi **"Ulteriori informazioni"** e poi **"Esegui comunque"**.

Si apre una finestra con alcune scritte e poi il browser con la pagina del consigliere. **Lascia aperta quella finestra** finché usi il consigliere: chiudendola, il programma si ferma.

La prima volta la pagina mostra un avviso sull'uso delle pagine di fantacalcio.it. Leggilo: se sei d'accordo, premi "Ho capito e accetto". Il programma scarica da solo soltanto i voti e il listone, e solo quando premi "Scarica i voti" o "Aggiorna dal sito"; durante "Cerca la formazione" è l'IA a leggere le pagine pubbliche, comprese le probabili formazioni.

## 5. Prepara listone, lega e rosa (una volta, poi solo quando cambiano)

1. **Listone.** Dal browser, senza accedere, apri https://www.fantacalcio.it/quotazioni-fantacalcio e premi "Scarica" per ottenere il file Excel. Va bene anche la "lista calciatori" Classic scaricata dalla tua lega. Nella pagina del consigliere, sotto "Listone", scegli il file. Ricaricalo quando cambia, ad esempio dopo il mercato: il consigliere ti segnala i giocatori della rosa che hanno cambiato squadra o non ci sono più.
2. **Lega.** Apri "Aggiungi una lega", scegli il modello più simile (pensionati, grossa, F1, scelta libera) e dagli un nome. Si apre la pagina delle regole: confrontala con le impostazioni della lega nell'app e correggi ciò che è diverso. I campi "da scegliere" vanno compilati, altrimenti non si può cercare.
3. **Rosa.** Premi "Modifica rosa" e incolla i nomi dei tuoi giocatori, uno per riga. Se due giocatori hanno lo stesso nome, aggiungi la squadra: `Thuram JUV`. Premi "Abbina al listone" e poi "Aggiungi alla rosa". Se un nome non viene trovato, controlla come è scritto nel listone. Se la tua lega ha cambiato il ruolo di un giocatore, correggilo dalla tabella della rosa.

## 6. Cerca la formazione (ogni giornata)

1. Nella pagina "Le mie leghe" scegli la lega, l'IA e lo stile:
   - **Punti sicuri:** il punteggio più alto che ci si può aspettare.
   - **Più rischio:** più possibilità di un punteggio molto alto, con qualche incertezza in più.
2. Premi **"Cerca la formazione"**. Si apre una nuova finestra con l'IA al lavoro.
3. L'IA può chiederti il permesso di leggere una pagina o di eseguire il controllo. Leggi la richiesta e conferma solo se riguarda pagine di calcio o il file `controlla.py`. **Non confermare mai** indirizzi `leghe.fantacalcio.it` o richieste di login.
4. Ci vogliono alcuni minuti. Quando l'IA ti dice di tornare alla pagina, il risultato compare da solo. Puoi chiudere la finestra dell'IA.

Se la finestra dell'IA si chiude o si blocca, nella pagina premi **"Ho chiuso il terminale"**: se il risultato non c'è, la pagina te lo dice e puoi rifare la ricerca.

## 7. Leggi il risultato e inserisci la formazione

- **Campo:** la formazione, con il capitano in giallo e i giocatori in dubbio in arancione. Sotto ci sono la panchina in ordine di ingresso e, dove la lega lo prevede, lo Switch consigliato.
- **Motivi:** perché ogni giocatore è stato scelto, quanto è affidabile la notizia, le fonti lette e chi è rimasto fuori.
- **Confronto:** la tua rosa accanto alla migliore formazione di tutta la Serie A. La migliore non tiene conto dei crediti.

Ricontrolla i giocatori in dubbio prima della scadenza indicata, poi **inserisci tu la formazione nell'app**.

Le ricerche passate restano sotto "Ricerche precedenti". I tuoi dati stanno nella cartella `ConsiglioFormazione` dentro la tua cartella utente.

## 8. Dopo la giornata: la verifica

A giornata finita puoi controllare quanto valeva la formazione consigliata e quella che hai schierato davvero. Nella pagina "Le mie leghe" premi **"Verifica"** sulla lega.

1. **Scegli la giornata.** La stagione è già `2026-27`; indica il numero della giornata.
2. **Scarica i voti.** Premi "Scarica i voti": il programma legge la pagina pubblica dei voti, solo quando premi il pulsante. La pagina ti dice se i voti sono completi e cosa è cambiato rispetto a una copia scaricata prima (i voti vengono corretti nei giorni dopo la partita).
3. **Se il download non riesce**, il programma lo scrive e ti mostra il link della pagina dei voti. Aprilo nel browser, salva la pagina (File → "Salva con nome", formato **"Pagina web, solo HTML"**) e caricala con "Carica la pagina salvata". Lo stesso vale per il listone: "Aggiorna dal sito" oppure "Carica la pagina salvata".
4. **Scrivi cosa hai schierato** (facoltativo): i titolari uno per riga (come per la rosa, con la squadra se ci sono due omonimi, ad esempio `Thuram JUV`), il modulo, la panchina in ordine di ingresso, capitano e vice (solo se la lega usa il fattore capitano). Se un nome non è riconosciuto con certezza o la formazione non rispetta le regole, la pagina elenca cosa correggere.
5. **Premi "Calcola la verifica"** e leggi il risultato:
   - **Stato:** "Certificato" vuol dire dati completi e ricerca fatta prima della scadenza; "Provvisorio" che qualcosa non è certo (i motivi sono elencati); "Dati incompleti" che i voti scaricati non erano completi.
   - **I punti:** la formazione perfetta (assoluta e della tua rosa), la migliore che si poteva fare con gli stessi 18, e quanto hanno ottenuto la consigliata e la schierata. Se il capitano non ha preso voto, c'è anche il totale "senza il subentro del vice": controlla nell'app della lega quale dei due vale.
   - **Dove si sono persi i punti** (il "regret"): quanto è dovuto alla rosa (limite), a chi hai scelto tra i 18 (selezione) e a come li hai disposti (schieramento).
   - **Errori e dettaglio:** chi non ha preso voto, chi è entrato al suo posto, il capitano migliore che c'era.

Puoi ricalcolare quando vuoi, ad esempio dopo che i voti sono stati corretti: le versioni vecchie restano nell'elenco "Verifiche salvate".

---

## Se qualcosa non va

| Cosa vedi | Cosa fare |
|---|---|
| Doppio clic e non succede nulla, o "Non trovo Python 3.11" | Installa Python (passo 1). Su Windows reinstallalo spuntando "Add python.exe to PATH". |
| "Il programma non risponde" | La finestra del consigliere è stata chiusa: riavvialo (passo 4). |
| "Claude non risulta installato" o "Gemini non risulta installato" | Installa l'IA (passo 2), poi chiudi e riapri il consigliere. |
| "Carica prima il listone" | Passo 5.1. |
| "Il file non è un Excel .xlsx valido" o "Non trovo le colonne Ruolo, Nome e Squadra" | Riscarica il listone. Deve essere il file Excel Classic, non Mantra. |
| "Completa le regole della lega" | Apri "Regole" e compila i campi "da scegliere". |
| "La rosa della lega è vuota" | Passo 5.3. |
| "C'è già una ricerca in corso per questa lega" | Apri la ricerca in corso da "Ricerche precedenti" e premi "Ho chiuso il terminale". |
| "La ricerca non è andata a buon fine" | La formazione proposta non rispettava le regole e l'IA non è riuscita a correggerla. Gli errori sono elencati: rifai la ricerca. |
| "Il file … è danneggiato" | Un file della cartella `ConsiglioFormazione` si è rovinato. Spostalo altrove (non cancellarlo) e ricarica la pagina. |
| La finestra dell'IA dice che hai finito le richieste gratuite | Riprova più tardi o usa un'altra IA. |
