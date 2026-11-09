# 04 — Audit degli errori e apprendimento ripetibile

## I tre confronti, non intercambiabili

1. **Punteggio previsione** `P_pred` (fantapunti reali del pronostico congelato, con sostituzioni).
2. **Punteggio perfetto ex post** `P_opt` (massimo teorico con tutti i voti ufficiali): scarto `regret=P_opt-P_pred`.
3. **Punteggio migliore formazione giocata nella lega** `P_lega`: confronto agonistico `P_pred-P_lega`. Il vincitore potrebbe essere ben sotto il perfetto teorico.

Se manca uno dei dati, lasciare la metrica `NON_CALCOLABILE` e spiegarne la causa.

## Prima di giudicare la previsione, rispondi a 6 domande

1. Il pronostico era valido e disponibile prima della scadenza? Era quello che l'utente ha effettivamente schierato?
2. Quali giocatori sono rimasti SV, chi è subentrato e come è cambiato il modificatore?
3. I voti puri e i FV rispettano esattamente le impostazioni della lega?
4. Quali alternative avremmo potuto scegliere sulla base delle **sole informazioni pre-deadline**?
5. Quali bonus sono stati eventi eccezionali (rigore, rosso, doppietta improbabile) e quali erano segnalati da buoni indicatori?
6. Il gap deriva da mancata copertura, squadra schierata male, pessima stima di un match-up o sola varianza?

## Classificare ogni errore

| Tipo | Descrizione | Esempio | Correzione possibile |
|---|---|---|---|
| `DATI` | Ruoli, trasferimenti, fonti o numeri sbagliati | A usato per C | Convalida automatica sul listone |
| `DISPONIBILITA` | Ignorato rischio SV/ballottaggio | titolare non convocato | Aumentare peso probabili e notizie recenti |
| `MATCHUP` | Valutata male difesa o vulnerabilità avversaria | fasce sistematicamente lasciate libere | Metriche xGA per zona |
| `FORMA` | Sopra/sottopesato rendimento rispetto a sottostante | hype post doppietta | Media regolarizzata su stagionale/ultime 5 |
| `MODIFICATORE` | Voti puri della difesa scelti male | media 6,74 vs 6,75 | Ottimizzazione congiunta P+4D |
| `CAPITANO` | Bonus fascia sottovalutato | punta con FV alto ma voto puro 6 | Modello sulla distribuzione del voto |
| `PANCHINA` | SV non coperto / priorità errata | 4º difensore SV | Migliorare probabilità voto riserve |
| `VARIANZA` | Evento non realisticamente anticipabile | doppietta con due tiri improbabili | Non cambiare metodo sulla sola anomalia |

Una decisione può essere **corretta ex ante ma sfortunata ex post**. Esplicitare questo senza nascondere il gap.

## Metriche ripetibili

- Punti totali e `regret` per giornata; mediana e media delle ultime 5/10 giornate.
- `regret_per_ruolo`: sostituire un ruolo alla volta **ricalcolando** tutti i modificatori; non sommare ingenuamente contributi non indipendenti.
- Punti potenzialmente persi sul modificatore = `MOD_perfetto - MOD_previsione`, da interpretare insieme ai FV diversi.
- Capitano: bonus ottenuto vs bonus massimo disponibili nell'11 predetto; se capitano SV la sostituzione si considera incerta finché regolamento non chiarito.
- % titolari a voto, % SV coperti, % cambi per ruolo, % difese con 4 voti validi.
- Migliore dei benchmark di partenza (top FM, ultime 5, consenso esterno), costruiti **con dati temporali uguali**.
- Se stimiamo vere probabilità: log-loss/Brier per `P(voto valido)`, `P(segna)`; confrontare predetto e osservato su molte giornate, non su un caso.

## Retrospettiva standard (4 blocchi)

1. **Dati:** quale era il punteggio congelato? Qual era l'ottimo? Quale il migliore realmente giocato?
2. **Decisioni:** tre scelte più rilevanti, motivazione originale e risultato, causa con data/ora dell'informazione prepartita.
3. **Controfattuali:** 1–3 cambi plausibili prima della scadenza e loro punteggio ex post (non trasformarli in "avrei certamente scelto").
4. **Esperimento per G+1:** una modifica precisa, quale problema risolve, test/criterio di successo per i turni successivi, rischio di overfitting.

## Come migliorare davvero

Tenere una baseline congelata e un modello nuovo in parallelo per 6–10 turni almeno. Annotare la qualità delle fonti e il punteggio atteso solo dove è stato stimato con metodo consistente. Analizzare errori ripetuti (SV, modificatore, capitano, eccesso di recentismo) anziché cercare di indovinare a posteriori ogni marcatore. Aggiornare una regola operativa alla volta; riesaminare se produce guadagno su più settimane.

## Valutazione aggiuntiva A vs B, obbligatoria dalla 1.1

Ogni giornata futura completa registra **due valori** `P_A`, `P_B` basati sullo STESSO CSV, più `P_opt` e `P_vinc` (se disponibile). Calcolare `gap_A = P_opt - P_A`, `gap_B = P_opt - P_B`, `delta_BA = P_B - P_A`, `vantaggio_A = P_A - P_vinc`, `vantaggio_B = P_B - P_vinc`. Non richiedere il numero degli avversari né stimare `P(primo)`: B è ottimizzata per il punteggio alto. Se si conosce il vincitore, misurare `superamento_ipotetico` (o pareggio) solo come confronto ex post, NON come probabilità predetta.

Tenere per almeno **8–10 giornate** sia media punti sia frequenza delle code alte; scegliere la preferita solo dopo un campione ragionevole. **G11 è un pronostico storico singolo**, non una A/B comparabile. Report consigliato: `modelli/05_CONFRONTO_A_B.md`.
