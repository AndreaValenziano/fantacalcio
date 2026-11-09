# 07 — Protocollo multi-IA: gara leale e apprendimento comune

## Come confrontare più IA

1. Fornire a tutte lo stesso ZIP e `AGENTS.md`, identico regolamento e stessa data limite per le fonti (corte informativo).
2. Chiedere a ciascuna `GNN_PREVISIONE_<MODELLO>_v1.md` con A/B **e due JSON congelati** conformi a `guide/05_FORMATO_DATI.md`; identificare il modello senza presupporne la superiorità.
3. Richiedere **due formazioni complete di 18 nomi distinti ciascuna**, A (punteggio atteso) e B (alto potenziale/ceiling senza dati avversari), con capitano/vice e motivazioni, più eventuali sostituzioni safe facoltative fuori gara.
4. Congelare tutti i risultati **prima** della scadenza. Usare hash SHA-256 o commit Git e salvare l'ora. Non scartare un pronostico sbagliato dopo aver visto i risultati.
5. A fine giornata usare **lo stesso CSV di voti della lega**, lo stesso calcolatore e le medesime regole per tutti.
6. Calcolare **sia A sia B**, scarto dal perfetto, gap sul vincitore, SV, modificatore e capitano. Verificare ogni eventuale differenza di interpretazione delle sostituzioni.
7. Discussione tra IA: ogni modello indica i suoi errori evitabili, analizza due scelte ben fatte e propone un cambiamento testabile. Il coordinatore registra conclusioni senza retrofittare il turno già giocato.

## Evitare il consenso apparente

- Prima ogni IA fa un pronostico **indipendente**; solo dopo si possono confrontare le scelte e proporre una versione di consenso separata.
- Non appiattire differenze su un'unica lista senza esplicitare chi suggeriva chi, motivazione e probabilità.
- Un modello che indovina una doppietta non è automaticamente migliore: valutare per più giornate e dati temporali uguali.
- Non attribuire alle altre IA voti, fonti o affermazioni che non hanno dato.

## Formato di una disputa sulla scelta

- Candidato A vs B, ruolo/avversario.
- Insieme di informazioni note prima del deadline.
- Stima di voto valido/minuti, xG/xA/forma, possibili gol/assist, variabilità.
- Per difesa: effetto sul **pacchetto P+4D**, non solo sul singolo.
- Decisione originaria di ciascuna IA; decisione di eventuale consenso; criterio di verifica ex post.

## Prompt pronto da copiare in un'altra IA

> Leggi nell'ordine `AGENTS.md`, `STATO_PROGETTO.md`, `guide/01_REGOLAMENTO.md`, `guide/02_PREVISIONE.md`, `guide/05_FORMATO_DATI.md`. Agisci come analista Fantacalcio Classic con rosa completamente libera, 4-3-3 e panchina 1P2D2C2A. Usa soltanto dati verificabili disponibili prima della scadenza che annoterai, motivando ogni giocatore, alternativa safe e capitano. Massimizza il punteggio complessivo atteso tenendo conto della distribuzione del modificatore difesa, e non cambiare più lo snapshot dopo il termine. Dopo che la giornata si conclude, con un dataset completo dei voti di Fantacalcio.it ricalcolati secondo la lega, usa `guide/03_OTTIMO_EX_POST.md` per ottenere il massimo, `guide/04_VALUTAZIONE.md` per misurare il gap e proporre un miglioramento misurabile; distingui sorte da errori realmente evitabili. Non inventare dati, non affermare che un subset è un massimo globale, non correggere retroattivamente altri modelli.

## Gara tra strategie per ogni IA (FantaLab 1.1)

Ogni IA consegna, con **identico cutoff informativo**, sia A=`MASSIMA_MEDIA` sia B=`PRIMO_POSTO` e due JSON separati. Non chiedere il numero degli avversari e non dichiarare P(primo); valutare B sui punti reali e sulla frequenza di punteggi elevati. `PRIMO_POSTO` resta soltanto una chiave tecnica legacy nel JSON. Nell'audit tutte le IA utilizzano lo stesso dataset di voti **pubblici**, con un unico `P_opt` e gli stessi `P_vinc`/vincoli. I consigli G11 pre-1.1 non costituiscono una competizione A/B ex ante e non possono essere riscritti.
