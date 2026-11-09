# 09 — Raccolta voti da fonti PUBBLICHE e certificazione del perfetto

**Vincolo confermato:** non richiedere al proprietario della lega un export privato dei voti. La pipeline deve cercare e verificare prima di tutto informazioni disponibili sul web pubblico. L'utente può eventualmente dare il punteggio del vincitore o uno screenshot come conferma, ma non è necessario per avviare l'audit.

## Fonti e campi obbligatori

1. Preferire la tabella **Redazione Fantacalcio** della pagina pubblica voti per la corretta stagione/giornata: `https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/NN` (verificare che la risorsa sia effettivamente disponibile e aggiornata). Escludere Voto Statistico e Voti Italia.
2. Listone Classic della stessa stagione su fonte ufficiale pubblica: `https://www.fantacalcio.it/quotazioni-fantacalcio/2026-27` (filtrare su Classic e, se disponibile, confrontare con listone lega).
3. Per **ogni calciatore** identificare `id`, nome, squadra, ruolo Classic, voto puro o SV, FV corretto per la lega, URL fonte, orario di consultazione. Registrare i casi di omonimia e trasferimenti, non indovinare il ruolo.
4. Il FV pubblicato può differire da quello della lega (es. +1 porta inviolata, assist da fermo o opzioni): normalizzare soltanto con eventi ufficialmente verificati; riportare in `note_normalizzazione` ciò che si è aggiunto/tolto, senza duplicazioni.
5. Se i voti sono ancora provvisori, la pagina non carica i numeri, alcuni giocatori mancano o l'accesso è limitato: scrivere `DATI_INCOMPLETI` e **non attribuire punteggi inventati**.

## Ciclo operativo a giornata terminata

1. Verificare che **tutte le gare** siano terminate, compresi eventuali rinvii; annotare l'orario della prima raccolta.
2. Ricavare l'**universo** dei calciatori del listone Classic eleggibili nella giornata, compresi SV. Salvare numero di ID e fonte usata come elenco di controllo.
3. Per tutte le squadre della giornata, confrontare righe presenti e voti assegnati; distinguere `SV` da voto vuoto perché non recuperato.
4. Compilare `dati/voti_GNN_completi.csv` nel formato di `guide/05_FORMATO_DATI.md`. Eseguire controllo di unicità, 4 ruoli, completezza, FV e audit del +1 imbattibilità. Conservare metadati e versioni delle fonti, senza fare scraping contro termini d'uso o aggirare limiti di accesso.
5. Calcolare `P_opt` e i punteggi delle due formazioni con `strumenti/confronta_strategie.py`. Se l'universo non è completo, usare **OTTIMO_SUL_SOTTOINSIEME**, mai *formazione perfetta assoluta*.
6. Conciliare i 18 giocatori e il totale con le regole della lega; segnalare divergenze. Registrare l'eventuale punteggio vincitore noto all'utente come `P_vinc` (indipendente dal perfetto).
7. Archiviare CSV/URL/metadati con timestamp, calcoli, convalide e `modelli/05_CONFRONTO_A_B.md`. Se i voti vengono corretti dopo, creare **v2**, senza sostituire silenziosamente v1.

## Controlli che vietano la certificazione

- Listone incompleto o non riferibile univocamente al Classic della lega;
- voti parziali, status SV non identificabile, dati di altra redazione, bonus portiere non riconciliati;
- regole di sostituzioni/vice non applicabili in modo deterministico al pronostico;
- fantavoti derivati da tabellini incompleti o senza provenienza;
- subset dei migliori marcatori usato al posto di TUTTI i calciatori.

**Le pagine web sono fonti da consultare, non una promessa di accesso futuro.** Se non sono accessibili il giorno dell'audit, registrare il blocco e produrre il risultato provvisorio o sospendere il massimo, senza attribuire all'utente l'obbligo di inviare file privati.
