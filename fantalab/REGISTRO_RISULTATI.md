# Registro storico e misurazione FantaLab

Ogni turno completato aggiunge una riga. Non inserire valori non misurati e non dividere per zero. Non trattare la 10ª come pronostico: non ne esiste uno congelato. **G11 ha una sola previsione storica: non ricostruire B dopo la partita.**

| Stagione | G | Previsione congelata | Punti previsione | Miglior 11 ex post | Gap ex post | Vincitore lega | Δ sul vincitore | Stato dati | Lezione verificata |
|---|---:|---|---:|---:|---:|---:|---:|---|---|
| 2026-27 | 10 | NO (solo benchmark) | — | 125,0 (stima) | — | 91,5 nell'esempio mostrato, **non verificato come vincitore definitivo** | — | PROVVISORIO | Nessuna: non c'è previsione da valutare |
| 2026-27 | 11 | SÌ, originale archiviato | DA CALCOLARE | DA CALCOLARE | DA CALCOLARE | DA OTTENERE | DA CALCOLARE | PREVISIONE CONGELATA | DA ANALIZZARE |

## KPI costanti

- `P_pred`: punteggio effettivo della formazione congelata, comprese sostituzioni, modifica e capitano.
- `P_opt`: massimo matematico con 4-3-3, ruoli e bonus reali, su dati completi.
- `P_vinc`: formazione con il maggior punteggio **davvero giocata** nella lega (fornita dall'utente).
- `regret = P_opt - P_pred`. Più basso è meglio; 0 solo se la previsione coincide con l'ottimo ex post.
- `cattura = P_pred/P_opt` soltanto se `P_opt>0`, e sempre insieme ai punti assoluti.
- `vantaggio_su_vincitore = P_pred - P_vinc`, senza confonderlo con il massimo teorico.
- Ulteriori indicatori: bonus difesa previsto/ottenuto, SV, copertura panchina, FV per ruolo, fattore capitano, tasso di titolarità, qualità delle probabilità.

## Baseline da battere (non ancora fissate quantitativamente)

A. Top per fantamedia stagionale per ruolo; B. top per forma ultime 5; C. consenso di pronostici di terze parti. Per essere onesti, questi baseline devono usare solo dati disponibili prima del turno e le stesse restrizioni della nostra rosa.

## Criterio di miglioramento

Le variazioni strategiche si giudicano su più giornate (es. minimo 6-10, preferibilmente più) e con gli stessi dati temporali delle baseline. Un caso fortunato o una doppietta non costituiscono da soli un miglioramento stabile.

## Registro parallelo A/B — dalla prima giornata futura non avviata

| Stagione | G | P_A | P_B | Delta B−A | P_opt | Gap A | Gap B | P_vinc (se noto) | A supera P_vinc? | B supera P_vinc? | Dati | Metodo / lezione |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 2026-27 | 11 | NON_APPLICABILE (storico singolo) | NON_APPLICABILE | — | — | — | — | — | — | — | G11 in verifica | Non è una gara A/B retroattiva |
| 2026-27 | 12+ | DA CALCOLARE | DA CALCOLARE | — | — | — | — | — | — | — | IN ATTESA | Due previsioni congelate prima del deadline |

**Interpretazione:** una A/B che avrebbe superato P_vinc è una **simulazione ipotetica**, non una vittoria realmente ottenuta senza conferma di schieramento. La strategia B è una ricerca del **ceiling** e non richiede il numero dei partecipanti. Le frequenze di superamento a posteriori non sono automaticamente probabilità previste; **non chiedere** quanti avversari partecipano.
