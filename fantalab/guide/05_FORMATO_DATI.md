# 05 — Contratto dati, nomi e interoperabilità Markdown/IA

L'obiettivo è che un'altra IA possa leggere i documenti senza dipendere da memoria, prompt privati o convenzioni implicite. Ogni dato ha **origine, timestamp, stato e ruolo**.

## Identità del turno

- `stagione`: `2026-27`.
- `giornata`: intero (1–38).
- `deadline`: timestamp con fuso Europa/Roma, per esempio `2026-11-06T20:45:00+01:00` (se la lega chiude prima usare quello effettivo).
- `creato_il`: quando è stata scritta la previsione, non quando è stata vista dopo.
- `tipo`: `PREVISIONE_IA`, `ROSA_EFFETTIVA_LEGA`, `BENCHMARK_EX_POST`, `REVISIONE`.
- `stato`: `BOZZA`, `CONGELATO`, `PROVVISORIO`, `VERIFICATO_DATI`, `CERTIFICATO`.

## CSV dei voti (per l'ottimizzatore)

Intestazioni esatte:

```csv
id,giocatore,squadra,ruolo,voto_puro,fv_lega,stato,fonte_voto,url_fonte,estratto_il
```

- `id`: identificatore **univoco e stabile nella giornata**. Preferire ID ufficiale listone; per documenti storici derivati usare la mappa degli alias del file della previsione. Non cambiare ID silenziosamente.
- `giocatore`: nome pubblico completo.
- `squadra`: squadra in quella giornata.
- `ruolo`: `P`, `D`, `C`, `A` **Classic della lega**.
- `voto_puro`: voto redazionale senza bonus/malus (es. `6.5`); per `SV` lasciare vuoto.
- `fv_lega`: fantavoto come lo applica **questa lega**, compreso +1 imbattibilità al P se previsto; per `SV` lasciare vuoto. Non sommare in seguito gli stessi bonus.
- `stato`: `VALIDO` o `SV`; un 6 politico è `VALIDO`, voto puro 6, FV secondo la regola di lega.
- `fonte_voto`, `url_fonte`, `estratto_il`: metadati di tracciabilità. Il programma non impone campi con URL ai fini del calcolo, ma la revisione umana sì.

**Locale numerico:** usare il **punto** decimale (`6.5`), separatore CSV virgola e codifica UTF-8. Non usare testo `s.v.` nel campo voto puro; usare il campo `stato`.

**Importante:** righe di esempio inventate non devono finire nel dataset ufficiale; `dati/voti_TEMPLATE.csv` contiene solo intestazioni.

## Formato macchina della previsione

JSON opzionale (modello reale storico in `stagioni/2026-27/G11/previsione_macchina.json`):

```json
{
  "stagione": "2026-27",
  "giornata": 11,
  "stato": "CONGELATO_STORICO",
  "capitano": "id_attaccante_1",
  "vicecapitano": "id_centrocampista_1",
  "titolari": {
    "P": ["id_portiere_1"],
    "D": ["id_dif_1", "id_dif_2", "id_dif_3", "id_dif_4"],
    "C": ["id_cen_1", "id_cen_2", "id_cen_3"],
    "A": ["id_att_1", "id_att_2", "id_att_3"]
  },
  "panchina": {
    "P": ["id_portiere_2"],
    "D": ["id_dif_5", "id_dif_6"],
    "C": ["id_cen_4", "id_cen_5"],
    "A": ["id_att_4", "id_att_5"]
  }
}
```

I nomi degli ID nel dataset CSV devono essere IDENTICI a quelli della previsione JSON. Il Markdown storico è il **documento autorevole**; il JSON è una traduzione tecnica da controllare. Se differiscono, fare errata corrige senza alterare l'originale.

## Fonti e verificabilità

Ogni affermazione decisiva dovrebbe avere `dato`, `fonte`, `url`, `pubblicato_il`, `consultato_il`, `validità` e, se è una probabilità, `metodo` e `intervallo` (quando disponibili). In mancanza, scrivere `NON_VERIFICATO` invece di inventare.

## Condivisione tra IA

Consegnare l'intera cartella FantaLab o lo ZIP; aprire **AGENTS.md**, poi **STATO_PROGETTO.md** e la guida pertinente. Le altre IA devono creare copie con nuovi nomi (`PREVISIONE_IA_A.md`, ecc.) e non sovrascrivere l'archivio dell'altra IA. Gli output sono comparabili solo con stesso listone, regole e informazioni disponibili entro il deadline.

## Contratto A/B, da FantaLab 1.1

Da ogni giornata **successiva alla G11**, archiviare due file macchina separati nella cartella della giornata:

- `previsione_A.json`: stesso schema `titolari/panchina/capitano/vicecapitano`, aggiungendo `strategia:"MASSIMA_MEDIA"` e `tipo:"PREVISIONE_IA"`;
- `previsione_B.json`: stesso schema, aggiungendo `strategia:"PRIMO_POSTO"` per **retrocompatibilità tecnica**, ma operativamente indica **`ALTO_POTENZIALE`**; `modello_primo:"PROXY_NON_CALIBRATO"` è un campo legacy e NON rappresenta la probabilità di primo posto. Non chiedere numero dei partecipanti. Per le stime non credibili usare `metodo_stima:"NON_STIMATO"`.

Non modificare gli originali, conservare SHA-256 e orario. L'output `confronto_A_B.json` è sempre derivato e ricostruibile da CSV + i due JSON. Per i metadati dei voti pubblici usare `dati/METADATI_FONTI_TEMPLATE.md` e `guide/09_VOTI_SOLO_PUBBLICI.md`. **Il CSV voti non è atteso dall'utente**: è un file costruito dall'analista a partire da fonti pubbliche citate.
