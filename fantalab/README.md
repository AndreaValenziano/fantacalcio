# FantaLab — laboratorio di previsione e apprendimento, Serie A

**Versione del progetto:** 1.2 — 7 novembre 2026  
**Obiettivo:** confrontare due strategie complete a ogni giornata: **A (massimo punteggio atteso)** e **B (alto potenziale / ceiling)**, poi misurare il risultato con i voti redazionali pubblici e l’ottimo ex post.  
**Compatibile con:** esseri umani, ChatGPT e altre IA capaci di leggere Markdown.  
**Lingua di lavoro:** italiano.

## In 60 secondi

Un ciclo ha **cinque fasi indipendenti**:

1. **Prima della chiusura:** acquisire calendario, listone Classic, forma, xG/xA, probabili, ballottaggi, squalifiche, conferenze e regole. Produrre **due formazioni complete A e B** (ciascuna 4-3-3, 7 riserve, capitano, vice) + alternative safe separate; non chiedere il numero degli avversari e non inventare probabilità di primo posto.
2. **Congelare:** salvare **due snapshot indipendenti** A e B prima del calcio d'inizio: giocatori, ordine panchina, data/ora, fonti, eventuali ipotesi. **Non modificarli** dopo la scadenza.
3. **Dopo la giornata:** raccogliere **da siti pubblici** tutti i voti **redazionali Fantacalcio.it**, ruoli Classic e fantavoti conformi alla lega; calcolare **entrambi** i punteggi con gli SV e le sostituzioni.
4. **Costruire l'ottimo ex post:** cercare l'undici matematicamente migliore, non soltanto i migliori fantavoti per ruolo. Valutare modificatore (portiere + migliori 3 difensori su 4) e capitano.
5. **Imparare:** confrontare **A vs B**, ottimo ex post e vincitore reale della lega, distinguere errori correggibili da eventi casuali, registrare solo modifiche di metodo testabili.

**Regola d'oro:** il benchmark perfetto ex post NON è una previsione; il gap dalla perfezione è una metrica di opportunità, non prova automatica di un pessimo pronostico.

## Dove iniziare

| File | Funzione |
|---|---|
| `AGENTS.md` | Prima lettura obbligatoria per qualsiasi IA; istruzioni riutilizzabili |
| `CONFIGURAZIONE.md` | **Preferenze permanenti confermate**: bonus standard, fonti pubbliche, doppia strategia |
| `STATO_PROGETTO.md` | Giornata corrente, storico e questioni aperte |
| `guide/01_REGOLAMENTO.md` | Regole confermate della lega, soglie esatte |
| `guide/02_PREVISIONE.md` | Metodo ex ante, formazione aggressiva e safe |
| `guide/03_OTTIMO_EX_POST.md` | Definizione dell'ottimo e validazione del calcolo |
| `guide/04_VALUTAZIONE.md` | Analisi degli errori, KPI e miglioramento |
| `guide/05_FORMATO_DATI.md` | Contratto di dati per IA, CSV e identificatori |
| `guide/06_FONTI.md` | Priorità delle fonti, timestamp e prevenzione errori |
| `guide/07_COLLABORAZIONE_IA.md` | Come confrontare più IA con pari opportunità |
| `guide/08_DUE_STRATEGIE.md` | Definizioni operative e metriche delle strategie A e B |
| `guide/09_VOTI_SOLO_PUBBLICI.md` | Raccolta, controllo di completezza e provenienza dei voti pubblici |
| `modelli/` | Modelli da copiare a ogni giornata |
| `stagioni/2026-27/G10/` | Benchmark retrospettivo provvisorio della 10ª |
| `stagioni/2026-27/G11/` | Pronostico originale congelato dell'11ª; dati pronti per il confronto |
| `strumenti/ottimizza.py` | Calcolo deterministico di 11 ideale e punteggio previsione |
| `strumenti/test_ottimizza.py` | Test del calcolo contro ricerca esaustiva |
| `strumenti/confronta_strategie.py` | Confronto automatico A/B + ottimo ex post |
| `strumenti/test_confronta_strategie.py` | Test del confronto A/B |

## Procedura rapida per una nuova giornata N

- Creare `stagioni/YYYY-YY/GNN/` copiando **`modelli/04_DOPPIA_PREVISIONE.md`** e **`modelli/05_CONFRONTO_A_B.md`**.
- Acquisire soltanto informazioni disponibili **prima** del deadline; segnare orario e link per ogni dato decisivo.
- Schierare **due 11+7 completi** A e B, con giocatori distinti *all’interno di ciascuna*, rispettando i ruoli Classic. Salvare entrambe v1 e, se serve, revisione pre-deadline v2. Congelare entrambe; lasciare intatti gli snapshot. Per i file macchina, partire da `modelli/previsione_A_TEMPLATE.json` e `modelli/previsione_B_TEMPLATE.json` e aggiornare `stato` a `CONGELATO` prima del deadline.
- Terminato il turno, cercare il **dataset voti integralmente su siti pubblici** e creare `dati/voti_GNN_completi.csv` da `dati/voti_TEMPLATE.csv`, con `dati/METADATI_FONTI_TEMPLATE.md`; verificare FV e regole di lega. Se incompleto, usare soltanto `SUBSET_ONLY`.
- Eseguire `strumenti/confronta_strategie.py` sui **due JSON congelati** e sul CSV comune; compilare `modelli/05_CONFRONTO_A_B.md` e aggiornare `REGISTRO_RISULTATI.md`. Conciliare con i risultati pubblici e, quando disponibile, il punteggio vincitore della lega.
- Produrre una sola revisione operativa del metodo; nelle giornate seguenti misurare se migliora davvero.

## Comandi (facoltativi)

```bash
python strumenti/test_ottimizza.py
python strumenti/ottimizza.py dati/voti_G11_completi.csv \
  --previsione stagioni/2026-27/G11/previsione_macchina.json \
  --output stagioni/2026-27/G11/calcolo_risultati.json
```

Non sono inclusi voti completi: il CSV è un modello vuoto. Senza dataset integrale l'algoritmo fornisce **soltanto un ottimo nel sottoinsieme analizzato** e non può certificare il massimo assoluto.

## Limiti e integrità

- **Nessuna esecuzione automatica**: l'IA esegue il processo quando l'utente torna in chat o attiva separatamente un'automazione.
- Non riscrivere gli originali congelati. Non inventare voti, ruoli, statistiche o percentuali di primo posto; evidenziare i dati assenti. Il pronostico G11 resta storico unico: non crearne una versione B a posteriori.
- L'analisi delle prestazioni di un'IA deve basarsi su snapshot firmati temporalmente, non su ricostruzioni inventate dopo.
- Non dichiarare "perfetta" una formazione senza dataset integrale e regole verificate, specie per il voto del portiere, SV e +1 rete inviolata.

## Confronto A/B (nuovo dalla versione 1.1)

```bash
python strumenti/test_ottimizza.py
python strumenti/test_confronta_strategie.py
python strumenti/confronta_strategie.py dati/voti_GNN_completi.csv \
  --media stagioni/2026-27/GNN/previsione_A.json \
  --primo stagioni/2026-27/GNN/previsione_B.json \
  --output stagioni/2026-27/GNN/confronto_A_B.json
```

**Precisazione utente v1.2:** tutti possono utilizzare tutti i giocatori, quindi il numero degli avversari **non è necessario e non va richiesto**. B cerca il massimo potenziale di punti (non una P(primo) stimata). L’etichetta tecnica `PRIMO_POSTO` nel JSON e nell’opzione `--primo` è mantenuta per retrocompatibilità; leggere la guida 08. L’ottimizzatore ex post non è un predittore; il dataset pubblico deve essere completo per dichiarare una «formazione perfetta» globale.
