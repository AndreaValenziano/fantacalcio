# DOPPIA PREVISIONE — [STAGIONE], G[NN]

**Deadline reale:** [timestamp Europa/Roma, verificato / non verificato]  
**Cutoff informativo comune:** [timestamp]  
**Autore/IA e versione:** [MODELLO — v1]  
**Fonte listone Classic:** [URL, consultato il]  
**Stato:** BOZZA / CONGELATO PRIMA DEL DEADLINE / ARCHIVIO STORICO  
**Consegna all'app (non presumerla):** NON_CONFERMATA / A / B / ALTRA

## Strategia A — MASSIMA_MEDIA

**Razionale:** massimizzazione del punteggio medio atteso; predizione numerica [METODO/INPUT oppure NON_STIMATA].

| Slot | ID Classic | Giocatore e squadra | Avversario | Perché | Rischio SV/bonus |
|---|---|---|---|---|---|
| P | | | | | |
| D1 | | | | | |
| D2 | | | | | |
| D3 | | | | | |
| D4 | | | | | |
| C1 | | | | | |
| C2 | | | | | |
| C3 | | | | | |
| A1 | | | | | |
| A2 | | | | | |
| A3 | | | | | |

**Panchina (in ordine):** P [ ]; D1 [ ]; D2 [ ]; C1 [ ]; C2 [ ]; A1 [ ]; A2 [ ].  
**Capitano:** [ ] | **Vice:** [ ]  
**E(punti):** [VALORE+METODO / NON_STIMATO]  
**P(modificatore ≥+4):** [VALORE+METODO / NON_STIMATA]

## Strategia B — ALTO POTENZIALE / CEILING (codice JSON legacy `PRIMO_POSTO`)

**Razionale:** [motivi del possibile punteggio alto, chance ragionata di bonus multipli, protezione SV/modificatore]; non chiedere numero di avversari, non inventare probabilità di primo posto.

| Slot | ID Classic | Giocatore e squadra | Avversario | Perché rispetto ad A | Rischio / upside |
|---|---|---|---|---|---|
| P | | | | | |
| D1 | | | | | |
| D2 | | | | | |
| D3 | | | | | |
| D4 | | | | | |
| C1 | | | | | |
| C2 | | | | | |
| C3 | | | | | |
| A1 | | | | | |
| A2 | | | | | |
| A3 | | | | | |

**Panchina (in ordine):** P [ ]; D1 [ ]; D2 [ ]; C1 [ ]; C2 [ ]; A1 [ ]; A2 [ ].  
**Capitano:** [ ] | **Vice:** [ ]  
**E(punti):** [VALORE+METODO / NON_STIMATO]  
**P(primo):** [CALIBRATO+INPUT / NON_STIMABILE]  
**Proxy alto punteggio:** [QUANTILE+MODELLO / NON_STIMATO]

## Differenze A vs B (anche se sono identiche)

| Differenza | Cambia perché | Compromesso media / coda alta |
|---|---|---|
| | | |

## Alternative SAFE (fuori gara, a meno di snapshot separato)

- [2–3 cambi più prudenti, con ragione; NON contano come una terza formazione congelata].

## Fonti disponibili PRIMA del cutoff

- [timestamp] — [URL] — [dato utilizzato] — [quale scelta cambia].

## Verifiche e congelamento

- A: 18 diversi e ruoli corretti [ ]; capitano e vice validi [ ]; 4 D potenzialmente a voto [ ].
- B: 18 diversi e ruoli corretti [ ]; capitano e vice validi [ ]; 4 D potenzialmente a voto [ ].
- Due JSON indipendenti `previsione_A.json` e `previsione_B.json` secondo `guide/05_FORMATO_DATI.md` [ ].
- Hash SHA-256 (file A, B, questo documento): [ ]. Congelati il [timestamp] **prima** della scadenza: [ ].
- Non alterare dopo il deadline; eventuali correzioni sono versioni nuove marcate come successive.
