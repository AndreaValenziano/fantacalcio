# 03 — Come trovare la formazione PERFETTA dopo la giornata

## Definizione esatta

**Formazione perfetta ex post = massimo di punteggio realizzabile** scegliendo liberamente qualsiasi 11 calciatori **con voto valido** del listone Classic della giornata, sotto vincolo P1-D4-C3-A3, portiere imbattuto incluso nei rispettivi FV, modificatore difesa e massimo bonus capitano sul voto puro.

Non confonderla con la formazione più forte *prevedibile* ex ante o con la miglior formazione **effettivamente schierata** nella lega. La panchina del massimo ex post non è identificabile come unica "migliore": se tutti gli 11 prendono voto, nessuna riserva entra e molte panchine producono lo stesso punteggio.

## Formula

Sia `S` l'undici valido (1P,4D,3C,3A) e `c` il capitano scelto tra i giocatori di `S`.

`TOT(S,c) = Σ FV_lega(p) [p∈S] + MOD_D(P,D1,D2,D3,D4) + CAP(voto_puro(c))`

Dove `MOD_D` usa `media = (voto_P + 3 voti puri più alti tra i 4 D)/4`, con soglie del regolamento. I fantascores `FV_lega` **devono già includere** il +1 clean sheet se applicabile (una sola volta), altrimenti il risultato è sbagliato.

Ottimizzare congiuntamente `S` e `c`. Non basta ordinare i quattro difensori per FV: un difensore con 0,5 FV in meno potrebbe far scattare una fascia del modificatore superiore. Non basta neanche usare gli attaccanti con FV migliore se una scelta diversa migliora la fascia capitano di più di quanto perde in FV.

## Dati necessari

Per ogni calciatore (non soltanto gli 11 top): identificatore, nome, squadra nella giornata, **ruolo Classic ufficiale**, voto puro redazionale, fantavoto **ricalcolato secondo la lega**, stato `VALIDO`/`SV`, fonte e timestamp. Non interpretare un missing come `0`, né mischiare provider diversi.

## Algoritmo esatto incluso

`strumenti/ottimizza.py`:

1. Scarta gli SV dall'ottimo teorico; chi non ha voto non può essere titolare di un undici ex post senza necessità di sostituzioni.
2. Per la difesa raggruppa i difensori per **voto puro** e conserva i quattro FV migliori di ciascun gruppo. Questa riduzione è esatta: più di quattro difensori dello stesso livello non possono entrare nell'undici e scambiare un difensore con un altro che ha identico voto puro e FV superiore non peggiora né modificatore né potenziale capitano.
3. Enumera le combinazioni di 4 D tra i candidati ridotti e tutti i P con voto. Per ogni pacchetto calcola Σ FV e modifica, annota il più alto bonus capitano disponibile nel pacchetto.
4. Per C e A sceglie i migliori 3 per FV, considerando anche l'eventuale necessità di includere un capitano con voto alto.
5. Prova tutte le cinque soglie di bonus capitano (0 / 0,5 / 1 / 1,5 / 2), imponendo che il giocatore che le giustifica sia nell'undici. Confronta i casi capitano in P/D, C, A e sceglie il massimo globale.
6. Emette squadra, punteggio base, media difesa, bonus difesa, capitano e bonus, numero calciatori valutati.

**Esattezza matematica:** con dati completi e regole stabilite, l'algoritmo esplora una rappresentazione che preserva almeno un ottimo globale. I test `strumenti/test_ottimizza.py` confrontano la risposta con enumerazione esaustiva su campioni sintetici.

## Come usarlo

```bash
# 1) Completare un CSV separato usando dati/voti_TEMPLATE.csv
# 2) Testare l'algoritmo
cd FantaLab
python strumenti/test_ottimizza.py
# 3) Calcolare la formazione perfetta e la previsione storica
python strumenti/ottimizza.py dati/voti_G11_completi.csv \
 --previsione stagioni/2026-27/G11/previsione_macchina.json \
 --output stagioni/2026-27/G11/calcolo_risultati.json
```

Il `--previsione` simula sostituzioni **in ordine di ruolo** per i titolari SV: prima riserva valida del medesimo ruolo, senza limiti al numero di cambi. Se mancano voti validi sufficienti, oppure il capitano è SV, emette stato non definitivo, perché mancano chiarimenti su riserve d'ufficio/vice. **Non spacciare tali casi per punteggi ufficiali.**

## Livelli di attendibilità del risultato

- `SUBSET_ONLY`: sono stati importati solo alcuni giocatori; il valore è **il massimo nel sottoinsieme**, NON il perfetto della giornata.
- `PROVVISORIO`: archivio quasi completo o fonti terze; manca controllo su ruoli, voti o regole.
- `VERIFICATO_DATI`: tutti i giocatori e i voti di lega presenti, controlli tecnici superati.
- `CERTIFICATO`: dati completi e corretti + riconciliazione con il totale ufficiale Fantacalcio.it/lega + nessuna ambiguità sulle regole.

## Archivio 10ª giornata

`stagioni/2026-27/G10/BENCHMARK_PROVVISORIO.md` riporta **125,0 punti** stimati, senza prova del massimo globale. Mantenerlo `PROVVISORIO` finché non esistono CSV integrale e calcolo esatto certificato.
