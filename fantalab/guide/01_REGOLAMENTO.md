# 01 — Regolamento della lega (fonte: utente e screenshot)

**Versione regole:** 2026-11-06 (risposte aggiornate 23:35 Europa/Roma). **Non modificare senza nuova conferma.**

## Rosa e modulo

- Scelta gratuita di tutti i calciatori di Serie A, senza limiti di budget o per squadra; nuova rosa ogni giornata.
- Titolari: 4-3-3 = **1 portiere, 4 difensori, 3 centrocampisti, 3 attaccanti**.
- Panchina: **1 P, 2 D, 2 C, 2 A** (sette; ordine rilevante per le sostituzioni).
- **Sostituzioni illimitate ma solo ruolo per ruolo**, senza cambiare il 4-3-3.
- Ruoli del **listone Classic utilizzato dalla lega**, non ruoli tattici o Mantra.

## Voti e bonus

- Fonte: **voti redazionali di Fantacalcio.it**, non voti statistici o medie di altre redazioni.
- **+1 portiere per rete inviolata**. Nel dataset ex post, includerlo una sola volta nel `fv_lega`.
- Altri bonus/malus: utente ha confermato **preset standard Fantacalcio.it**. Tabella di riferimento pubblica: gol +3 (anche rigore), gol subito -1, giallo -0,5, rosso -1, rigore sbagliato -3, parato +3, assist +1; assist da fermo consigliato +0,5. Fonte: https://www.fantacalcio.it/regolamenti/leghe-private . Voci configurabili/opzionali (come autogol e reti decisive) o scelta del valore per assist da fermo possono differire: **non presumere varianti non verificate**; marcare l’audit `PROVVISORIO` se incidono sul punteggio.

## Modificatore difesa, ATTIVO

- Richiede almeno quattro difensori con voto valido **dopo le sostituzioni**.
- Media dei **voti puri senza bonus/malus** del portiere e dei **tre difensori con voto più alto sui quattro**: `(voto_P + top3(voto_D1, D2, D3, D4)) / 4`.
- Se il portiere non prende voto, trattare secondo le regole ufficiali della lega, non inventare il dato; quando è presente un portiere con voto, usarlo nel modificatore.
- I **6 politici valgono** come voti validi; le riserve d'ufficio in difesa **NON** attivano il modificatore.

| Media dei quattro voti puri | Bonus squadra |
|---|---:|
| <6 | +1 |
| da 6 a <6,25 | +2 |
| da 6,25 a <6,50 | +3 |
| da 6,50 a <6,75 | +4 |
| da 6,75 a <7,00 | +5 |
| da 7,00 in su | **+6** |

**Nota:** +6 è ottenibile già da media **7,00**. Un buon quartetto di difensori è importante, ma serve anche il quarto voto valido. Il portiere può incrementare sia il +1 imbattibilità sia il modificatore.

## Fattore capitano, ATTIVO

Calcolato sul **voto puro**, non sul fantavoto e **senza raddoppiare** i bonus o malus.

| Voto puro del capitano | Bonus squadra |
|---|---:|
| fino a 5,5 | 0 |
| 6,0 | +0,5 |
| 6,5 | +1 |
| 7,0 | +1,5 |
| da 7,5 in su | **+2** |

Per valori intermedi non standard, verificare impostazioni o dettaglio regolamento prima di attribuire bonus arbitrari. Regola del vice quando il capitano è SV: ancora da verificare.

## Disattivati

Modificatore portiere dedicato; modificatore centrocampo; modificatore attacco; modificatore modulo; fattore rendimento; fattore fairplay. **Non** confondere modificatore portiere dedicato disattivato con l'inclusione del portiere nel modificatore difesa.

## Esempio di calcolo

Portiere 7; migliori tre difensori 7, 6,5, 6,5 ⇒ media `(7+7+6,5+6,5)/4 = 6,75`, bonus **+5**. Se il capitano ottiene voto puro 7,5, aggiungere altri **+2**. Tutti i FV singoli vanno sommati separatamente. 

**Fonte primaria:** screenshot fornito dall'utente il 6 novembre 2026 (`image(20261106-162646).png`, disponibile nell'archivio della conversazione).

## Politica confermata di reperimento e obiettivi

- I voti finali vanno ricercati su **siti pubblici**; l'utente NON dispone di export privati da consegnare. Vedi `guide/09_VOTI_SOLO_PUBBLICI.md`.
- Ogni giornata futura richiede due formazioni complete, **A (massimo punti attesi)** e **B (alto potenziale / ceiling)**; dati e limiti in `guide/08_DUE_STRATEGIE.md`.
- Non considerare questi nuovi requisiti un permesso a modificare il G11 congelato.
