# 02 — Protocollo ex ante: pronostico della giornata

## Scopo e unità di analisi

Non massimizzare soltanto la somma delle fantamedie: massimizzare la distribuzione plausibile del **punteggio totale del 4-3-3**, con modificatore difesa + capitano + bonus portiere e copertura di panchina.

## Calendario di lavoro (tempi relativi al deadline)

1. **2–4 giorni prima:** calendario, avversari, giocatori del listone, forma e dati tattici; primo ranking lungo per ruolo.
2. **24–12 ore prima:** infortuni, convocazioni, allenamenti, rotazioni, conferenze, difese avversarie e quote indicative. Ridurre ai candidati con voto atteso affidabile.
3. **Ultime 1–2 ore prima della consegna:** aggiornare indisponibili e ballottaggi, e verificare eventuali formazioni ufficiali già pubblicate. Produrre versione finale e `CONGELARE` prima del deadline.
4. **Dopo il deadline:** nessun cambio retroattivo. Se gli eventi suggeriscono un pronostico diverso, scriverlo come commento a posteriori, non sostituire la previsione registrata.

## Fattori da valutare per ogni giocatore

### Ruolo e minuti

- Disponibilità (infortunio, squalifica, convocazione); probabilità di partenza dal 1'; probabile minutaggio; possibilità di SV.
- Ballottaggi e impegni ravvicinati, coppe, viaggio, fase di stagione. Un titolare da 90' non è equivalente a una possibile sostituzione al 65'.
- Ruolo **Classic** del giorno: vietato usare categorie di siti non corrispondenti.

### Produzione offensiva/forma

- Goal e assist recenti *e* sottostante: `xG/90`, `xA/90`, tiri in area, tiri in porta, occasioni grandi, rigori, punizioni, corner, cross e passaggi chiave.
- Forma ultime 3 e 5 gare, ma correggere per piccoli campioni, livello avversari e regressione alla media. Non inseguire solo chi ha segnato nell'ultima.
- Voto puro atteso e **distribuzione** del voto puro: rileva per capitano e difesa, indipendentemente dai bonus.

### Match-up e stili

- Gol, xG, xGA concessi dall'avversario; possesso, pressione, altezza del blocco, vulnerabilità alle transizioni/palle inattive e sulle fasce.
- Casa/trasferta, stato infortunati, giocatore avversario diretto, possibili marcature, ritmo/under-over, portiere avversario.
- Segnare la correlazione: più giocatori della stessa squadra possono massimizzare un'esplosione offensiva ma aumentare il rischio di un flop collettivo.

## Come valutare P + 4 D

Non selezionare separatamente P e D. Valutare una **unità da cinque**, stimando:

- Somma FV attesi dei cinque;
- probabilità di quattro voti validi D e uno P;
- probabilità di raggiungere ognuna delle fasce di media 6 / 6,25 / 6,5 / 6,75 / 7;
- probabilità di clean sheet del portiere (+1); rischio del portiere che prende tanti gol;
- affidabilità dei voti puri, portatori di cross/assist, piazzati e bonus difensivi.

Il modificatore è **a scatti**, non lineare: passare da media 6,74 a 6,75 vale +1, mentre passare da 6,50 a 6,60 non cambia fascia. Usare simulazioni o scenari, non la sola media dei voti medi stagionali.

## Capitano e vice

La fascia conferisce 0–2 punti sul **voto puro**. Scegliere il giocatore con alta probabilità di voto 7–7,5+, non necessariamente la punta con la migliore probabilità di doppietta. Stimare `E[bonus_capitano]` con probabilità delle diverse fasce; verificare che il capitano prenda voto. Se ci sono alternative con medesimo valore atteso, preferire affidabilità minutaggio. L'utilizzo del vice in caso di SV è da riconciliare con la lega.

## Due obiettivi obbligatori A e B, più alternative safe facoltative

- **A — MASSIMA_MEDIA:** massimizza il **punteggio atteso** della formazione finale (compreso modificatore, panchina e capitano).
- **B — ALTO POTENZIALE:** cerca un ceiling elevato (ad esempio possibilità plausibile di bonus multipli), senza dipendere dal numero dei partecipanti e senza stimare P(primo). Se non è possibile stimare percentili con metodo attendibile, presentare il ceiling qualitativamente.
- **SAFE:** cambi facoltativi che riducono P(SV) e volatilità, *fuori dalla gara A/B* a meno che si congeli una terza previsione esplicita.

A e B richiedono **due liste complete da 18** e capitano/vice per ognuna; possono essere uguali senza forzare differenze. Dettaglio in `guide/08_DUE_STRATEGIE.md`. Non basta offrire 2 cambi rispetto alla stessa formazione.

## Stime strutturate (non inventate)

Per ogni candidato si può registrare: `P(voto valido)`, `E(minuti)`, `E(FV | voto valido)`, probabilità di 1+ gol, 2+ gol, 1+ assist, voto >=6,5/7/7,5. Ogni stima indica fonte, timestamp, campione e, se non modellata realmente, campo `NON_STIMATO`. Le percentuali di terze parti vanno attribuite alla fonte, non presentate come calcolo autonomo.

## Output obbligatorio prepartita

- **DUE set** di 11 titolari nel 4-3-3 + sette in ordine per ruolo; 18 diversi **in ogni set** (strategie A e B).
- Capitano e vice separati per A e per B; 1–3 alternative safe facoltative fuori dal confronto.
- Una motivazione sintetica per **ogni titolare**, più criterio di panchina.
- Difficoltà avversario, forma, prova su ruolo Classic, probabilità SV/minuti e potenziale modificatore.
- Fonti citabili e controllo di scadenza, indicatore `PREVISIONE` / `CONGELATO`.
- Previsione numerica con range **solo se stimata**. Altrimenti descrivere scenari e dire esplicitamente che manca la calibrazione quantitativa.

## Controllo qualità automatico / manuale

Nessun duplicato, 1/4/3/3, 1/2/2/2, listone Classic, presenze reali nelle squadre aggiornate, nessuno squalificato confermato, panchina con priorità chiare, etichette corrette su tempo/fonti, capitano appartenente alla rosa, dichiarazione rischio.
