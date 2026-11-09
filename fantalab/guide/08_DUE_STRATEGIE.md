# 08 — Due strategie indipendenti: massimo punteggio atteso vs alto potenziale

**Decisione utente confermata il 7 novembre 2026:** tutti i partecipanti possono usare tutti i giocatori della Serie A, senza budget o limiti di squadra. Per costruire la miglior formazione non serve conoscere il numero degli avversari, e **non va più chiesto**. La strategia B non pretende di calcolare una probabilità matematica di vittoria contro il campo.

**Compatibilità tecnica:** il codice storico `PRIMO_POSTO`, il campo `modello_primo` e l'opzione CLI `--primo` restano solo per non rompere gli strumenti e i file esistenti. Il loro **significato operativo dalla v1.2 è `ALTO_POTENZIALE`**, non P(primo) calibrata. Non cambiare i JSON già congelati; i nuovi JSON B possono conservare il codice `PRIMO_POSTO` spiegando questa equivalenza.

## A — MASSIMA_MEDIA

Funzione obiettivo: massimizzare **E[punteggio finale]**, compresi FV, panchina, bonus/malus, +1 portiere imbattuto, modificatore difesa e fattore capitano. Privilegiare i giocatori con alta probabilità di voto, buon rendimento medio, continuità e vantaggio di matchup. Non confondere sicurezza con rinuncia ai bonus.

## B — ALTO_POTENZIALE (etichetta tecnica legacy `PRIMO_POSTO`)

Funzione obiettivo operativa: ricercare una **distribuzione di punteggio con coda superiore elevata**, per esempio il percentile 85/90 o la probabilità di superare una soglia di punti **dichiarata e giustificata**. Valorizzare giocatori con potenziale di multi-bonus, piazzati, rigori, match-up che favoriscono molte occasioni e combinazioni coerenti di squadra. Non confondere alto potenziale con scelte casualmente rischiose: rischio di SV, espulsione e rotazioni può distruggere il ceiling.

Se non esiste un modello probabilistico credibile, descrivere la B **qualitativamente** e scrivere `CEILING_QUALITATIVO / NON_STIMATO`, senza inventare quantili o percentuali. Non stimare P(primo) e non chiedere il numero dei partecipanti. Il numero degli avversari influirebbe su P(primo) in astratto, ma non è necessario all'attuale obiettivo.

A e B possono avere anche **gli stessi 18 nomi**: non introdurre differenze fittizie soltanto per avere due schede diverse.

## Procedura prima della giornata

1. Identico cutoff informativo, ruoli Classic, regole e fonti per A e B.
2. Preparare due rose **complete di 18 elementi ciascuna**: 1P+4D+3C+3A titolari e 1P+2D+2C+2A panchinari; capitano e vice, ordine panchina, motivazione per ogni giocatore.
3. A: motivare la previsione del punteggio medio, titolarità, affidabilità dei voti e modificatore. B: motivare realisticamente possibilità di doppiette, più assist, grandi risultati di squadra e punteggi molto alti, mantenendo copertura SV e difesa valida.
4. Quantificare media/ceiling **solo** se stime e modello sono verificabili, altrimenti qualificarli come giudizi esperti e non numeri scientifici.
5. Proporre 2–3 sostituzioni **safe** separate (non una terza previsione in classifica, a meno di congelarla esplicitamente).
6. Congelare prima del deadline due snapshot A/B con ora, fonti e hash; registrare la formazione eventualmente schierata davvero, senza dedurla.

## Procedura dopo la giornata

1. Reperire da fonti pubbliche i voti puri Redazione Fantacalcio.it, i FV adeguati alle regole, i ruoli Classic e gli SV. Annotare provenienza/completezza.
2. Calcolare sul **medesimo dataset** `P_A`, `P_B` e ottimo matematico `P_opt` (solo se dataset completo).
3. Confrontare `P_B-P_A`, gap A/B dal perfetto, SV, modificatore, capitano, medie e frequency dei punteggi alti su almeno 8–10 giornate.
4. Facoltativo: se l'utente comunica il miglior punteggio della lega, aggiungere gli scarti rispetto a quella soglia. **Non richiedere** numero di partecipanti.
5. Spiegare il gap tramite errori correggibili con prove pre-deadline e varianza imprevedibile. Proporre modifiche falsificabili, non retrofitting.

## Metriche corrette

- `media_A` vs `media_B` e differenza media su più giornate.
- Percentuale di giornate sopra soglie di punteggio **predefinite** (es. soglie definite da una baseline storica verificata, non adattate dopo i risultati).
- Tassi di SV, copertura panchina, fasce modificatore, bonus capitano e punteggi offensivi.
- `regret_A=P_opt-P_A`, `regret_B=P_opt-P_B`, se il massimo teorico è certificato.
- Scarto dal miglior risultato comunicato della lega **solo se disponibile**, come confronto descrittivo, non P(primo).

**Non ottimizzare il numero di avversari. Ottimizzare i fantapunti.**
