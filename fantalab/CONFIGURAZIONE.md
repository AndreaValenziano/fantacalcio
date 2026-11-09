# Configurazione confermata — FantaLab

**Versione:** 1.2 — 7 novembre 2026 (Europa/Roma)  
**Fonte:** risposte esplicite dell'utente e screenshot dei modificatori.  
**Priorità:** questo file riassume le preferenze; per i calcoli fanno fede `guide/01_REGOLAMENTO.md` e le eventuali future conferme dell'utente. Non alterare le previsioni già congelate.

## Regole e scelte

| Voce | Valore | Stato |
|---|---|---|
| Stagione iniziale | Serie A 2026/27 | CONFERMATO |
| Acquisto / budget | Rosa libera, nessun tetto di crediti o giocatori della stessa squadra, nuova rosa ogni turno | CONFERMATO |
| Undici | 1 P + 4 D + 3 C + 3 A | CONFERMATO |
| Panchina | 1 P + 2 D + 2 C + 2 A | CONFERMATO |
| Sostituzioni | Illimitate, solo ruolo per ruolo | CONFERMATO |
| Ruoli | Classic della lega / Fantacalcio.it | CONFERMATO |
| Voti | Redazionali Fantacalcio.it | CONFERMATO |
| Bonus ordinari | Impostazione standard Fantacalcio.it | CONFERMATO COME CATEGORIA; vedere precisazioni sotto |
| Portiere imbattuto | +1 | CONFERMATO |
| Modificatore difesa | ATTIVO, portiere incluso + 3 migliori difensori su quattro, su voti puri | CONFERMATO |
| Fattore capitano | ATTIVO, su voto puro; nessun raddoppio | CONFERMATO |
| Altri modificatori | Disattivati | CONFERMATO |
| Origine dei voti finali | **Solo siti pubblici**; NON contare su export privato dell'utente | CONFERMATO |
| Obiettivo strategico A | Massimizzare i fantapunti **attesi** | CONFERMATO |
| Obiettivo strategico B | **ALTO POTENZIALE**: massimizzare un punteggio molto alto (ceiling/coda superiore), senza modellare gli avversari | AGGIORNATO SU PRECISAZIONE UTENTE |
| Controllo settimanale | Confrontare A e B, XI perfetto ex post e miglior risultato della lega **solo se comunicato**, senza richiedere numero dei partecipanti | CONFERMATO |

## Modificatore difesa (bonus squadra)

Media voto puro del portiere e dei migliori tre fra i quattro difensori, diviso quattro, soltanto con quattro voti difensivi validi. Fasce: `<6→+1`; `[6,6.25)→+2`; `[6.25,6.5)→+3`; `[6.5,6.75)→+4`; `[6.75,7)→+5`; `≥7→+6`.

## Fattore capitano

Voto puro `≤5,5→0`; `6→+0,5`; `6,5→+1`; `7→+1,5`; `≥7,5→+2`. Il comportamento per voti intermedi e il subentro del vice restano da verificare quando rilevanti.

## Bonus ordinari: riferimento pubblico e particolarità

Il regolamento pubblico Fantacalcio.it indica la tabella convenzionale: gol +3 (anche su rigore), gol subito -1, ammonizione -0,5, espulsione -1, rigore sbagliato -3, rigore parato +3, assist +1 e assist da fermo consigliato +0,5. Altre voci opzionali (es. autogol -2, bonus gol decisivo) e l'esatto preset possono variare in una lega privata. Fonte: https://www.fantacalcio.it/regolamenti/leghe-private . L'utente ha confermato **standard**, non ogni voce personalizzabile: NON presumere impostazioni opzionali non verificate; preferire il fantavoto ufficiale della stessa lega quando disponibile o marcare la ricostruzione come **PROVVISORIA**.

L'utente ha confermato separatamente +1 porta inviolata; aggiungerlo al FV una sola volta se non è già compreso.

## Questioni ancora utili, senza bloccare il progetto

- **Non chiedere più il numero dei partecipanti.** Il bacino di calciatori è identico e illimitato per tutti; il numero degli avversari non cambia le scelte consentite né gli obiettivi A/B. Una probabilità matematica di arrivare primi richiederebbe anche il numero di concorrenti e il loro comportamento, ma non è un obiettivo operativo di FantaLab.
- Il miglior punteggio reale della lega può essere comunicato **facoltativamente** per il confronto dopo la giornata; non è un prerequisito per la previsione.
- Regola sul vicecapitano in caso di SV (e automatismi d'ufficio se non esiste sostituto a voto).
- Eventuali varianti fra più assist / autogol / reti decisive e l'esatto momento di blocco formazione; chiarire solo quando incidono sul calcolo.

## Garanzie temporali

Il pronostico **G11 è uno storico precedente a questa versione** e non si divide artificiosamente in A e B. Le due strategie saranno presentate e congelate come vere previsioni separate **dalla prossima giornata non ancora iniziata**.
