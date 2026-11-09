# Stato del progetto

**Aggiornato:** 7 novembre 2026; precisazione utente v1.2. G11 già avviata, previsione originale non modificabile.

## Situazione attuale

- **G10 (31 ottobre–2 novembre 2026):** benchmark retrospettivo **PROVVISORIO** da 125 punti, già archiviato. Il massimo teorico non è stato certificato per assenza di dataset integrale Fantacalcio.it/lega.
- **G11 (6–8 novembre 2026):** previsione **CONGELATA** come archivio di quanto suggerito dall'IA, non come prova di consegna reale alla lega. Originale in `stagioni/2026-27/G11/PRONOSTICO_ORIGINALE_CONGELATO.md`. File macchina derivato in `previsione_macchina.json`. Prima partita venerdì 6 novembre 20:45 Europa/Roma (orario della scadenza della lega da verificare).
- **G11 risultati:** NON ANCORA AUDITATI nel progetto; compilare dopo la conclusione di tutte le partite. Lo storico G11 ha **una sola previsione**: NON generare retroattivamente B.
- **Prossima azione:** a fine G11 raccogliere voti da **siti pubblici**, auditare il pronostico originale, massimo ex post e confronto col vincitore se noto. **Dalla prima giornata futura non iniziata:** due previsioni complete A (media) e B (alto potenziale di punteggio).

## Questioni residue (non ripetere quelle già risolte)

1. **Numero dei partecipanti: NON NECESSARIO e da NON chiedere.** Con rose completamente libere non cambia quali giocatori possiamo scegliere; B è la strategia alto potenziale. Il punteggio del vincitore, se comunicato spontaneamente, serve solo per un benchmark ex post.
2. In caso di SV del capitano, quando subentra il vice? Eventuali riserve d'ufficio come funzionano?
3. Per il confronto con il vincitore reale della lega, l'utente può riferire il punteggio finale o mandare uno screenshot (facoltativo, NON serve per i voti individuali)?
4. Il «bonus standard» è confermato dall'utente, ma voci opzionali o personalizzabili come assist da fermo/autogol/reti decisive vanno verificate solo se incidono su un audit esatto.

## Invarianti già chiarite — NON chiedere di nuovo

- Nessun limite economico o alla scelta dei giocatori; squadra ricostruibile in ogni turno.
- 4-3-3 fisso: 1P+4D+3C+3A e panchina 1P+2D+2C+2A.
- Fonte voti **redazionali Fantacalcio.it**; +1 porta inviolata.
- Sostituzioni illimitate, ruolo per ruolo.
- Modificatore difesa **attivo** con portiere incluso e fattore capitano **attivo**.
- Bonus/malus **standard Fantacalcio.it** (con caveat su opzioni configurabili); voti reperiti **solo su siti pubblici**, nessun export della lega richiesto.
- Target A: **massimo punteggio atteso**; target B: **alto potenziale/ceiling**, senza modellare avversari o P(primo). Entrambe con 11+7 completi, più alternative safe facoltative.

## Politica versioni

- `CONGELATO`: immutabile.
- `PREVISIONE_vX`: revisione consentita solo se la scadenza non è passata e la precedente resta archiviata.
- `RISULTATI`: successive correzioni di voti sono nuove versioni, non modifiche silenziose.
- `PROVVISORIO` / `CERTIFICATO`: diversi livelli di qualità dati; non promuovere senza controlli.
