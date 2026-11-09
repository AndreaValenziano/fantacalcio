# Verifica della giornata — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** leggere voti e listone dalle pagine pubbliche di fantacalcio.it (download su pulsante o pagina salvata a mano) e, per ogni lega, confrontare formazione consigliata, schierata e perfetta con regret scomposto e stato `CERTIFICATO` / `PROVVISORIO` / `DATI_INCOMPLETI`.

**Architecture:** cinque moduli nuovi in `consigliere/` — `pagine.py` (lettura HTML), `fonti.py` (URL ammessi, download, archivio con SHA-256), `punteggio.py` (valore di una formazione), `ottimo.py` (formazione perfetta esatta), `verifica.py` (consigliata, misure, versioni, report) — più API in `server.py`, sigillo in `ricerca.py` e vista Verifica in `web/`. `fantalab/` resta intatto e serve solo come riferimento nei test.

**Tech Stack:** Python 3.11+ sola libreria standard (`html.parser`, `urllib.request`, `hashlib`, `itertools`), `unittest`; HTML/CSS/JS senza librerie.

**Spec:** `docs/superpowers/specs/2026-11-09-verifica-giornata-design.md` (leggerla insieme a questo piano). Contesto: `docs/superpowers/specs/2026-11-09-formazione-fantacalcio-design.md`, `CLAUDE.md`.

## Global Constraints

- Sola libreria standard; niente `xml.etree`/`pyexpat` (i Python di Homebrew non lo importano): HTML con `html.parser`.
- Mai login, credenziali, token, né indirizzi `leghe.fantacalcio.it` / `apileague.fantacalcio.it`; nessuna elusione anti-bot (niente User-Agent di browser, rotazioni, CAPTCHA).
- URL scaricabili solo: `https://www.fantacalcio.it/voti-fantacalcio-serie-a/<AAAA-AA>/<1..38>`, `https://www.fantacalcio.it/quotazioni-fantacalcio`, `https://www.fantacalcio.it/probabili-formazioni-serie-a`.
- Download: solo su azione della persona, ≥ 3 s tra due richieste, timeout 30 s, User-Agent `ConsiglioFormazione/<versione>`, un tentativo.
- Crediti e prezzi non si leggono: le colonne di prezzo del listone vengono saltate. Solo Classic, niente Mantra.
- Non inventare dati: SV non è 6 né 0; regola incerta → `PROVVISORIO` con motivo.
- Nessuna sovrascrittura: copie delle pagine, verifiche, schierate e registro si aggiungono, mai si riscrivono. Scritture atomiche con `archivio.scrivi_json`.
- Nella pagina solo `textContent`; link solo `http`/`https`.
- `fantalab/` e ogni file `CONGELATO`, G10, G11: mai modificati.
- Nomi nel codice, messaggi e documenti in italiano.
- Percorsi con spazi e accenti devono funzionare; sempre `shell=False`.

## Review Focus

1. **Nomi di squadra diversi tra le fonti** (listone xlsx "Verona", slug della pagina `hellas-verona`, sigla `VER`): l'abbinamento formazione↔voti deve funzionare o dichiarare il giocatore non trovato, mai abbinarlo a caso. → test in Task 1 e Task 6.
2. **Giornata non finita o pagina parziale** (squadre mancanti, tutti SV per una partita rinviata): `DATI_INCOMPLETI`, la verifica gira lo stesso e la perfetta è "sul sottoinsieme". → test in Task 1 e Task 6.
3. **Nomi con apostrofi, accenti, iniziali** (`N'Dicka`, `Martinez L.`, `Valdepeñas`): lettura e abbinamento corretti. → test in Task 1 e Task 6.
4. **Pagina caricata a mano sbagliata** (HTML di un'altra pagina, file non UTF-8, file enorme): errore chiaro, niente archivio sporco. → test in Task 2 e Task 8.
5. **Ricerca senza `risultato.giornata` coerente o conclusa dopo la scadenza**: non diventa la consigliata. → test in Task 6.

---

### Task 1: lettura delle pagine (`pagine.py`) e vincoli aggiornati

**Files:**
- Create: `consigliere/pagine.py`
- Create: `tests/test_pagine.py`, `tests/dati/voti_ridotta.html`, `tests/dati/quotazioni_ridotta.html`
- Modify: `CLAUDE.md` (sezione Architettura e Vincoli), `docs/superpowers/specs/2026-11-09-formazione-fantacalcio-design.md` (righe 35 e 44: rimandare alla nuova spec), `.gitignore` (aggiungere `tests/dati/voti_vero_*.html`, `tests/dati/quotazioni_vero.html`)

**Interfaces:**
- Produces:
  - `class PaginaNonValida(Exception)`
  - `leggi_voti(html: str) -> dict` → `{"stagione": str|None, "giornata": int|None, "squadre": {nome: {"slug": str, "data": str ISO con fuso|None}}, "giocatori": [Giocatore], "mancanze": [str]}`
  - Giocatore: `{"id": str, "nome": str, "squadra": str, "ruolo": "P"|"D"|"C"|"A", "voto": float|None, "fv_pubblicato": float|None, "ammonito": bool, "espulso": bool, "gol": int, "gol_subiti": int, "autogol": int, "rigori_segnati": int, "rigori_sbagliati": int, "rigori_parati": int, "assist": int, "player_of_the_match": int}`
  - `leggi_listone(html: str) -> list[dict]` → `[{"id", "nome", "squadra", "ruolo"}]`
  - `squadra_da_slug(slug: str) -> str` (es. `hellas-verona` → `Hellas Verona`)
  - `ora_italiana(gg_mm_aaaa_hh_mm: str) -> str` ISO con `+01:00`/`+02:00`
  - `completezza(voti: dict) -> list[str]` (mancanze; vuota se completa)

Struttura reale verificata il 9/11/2026 (pagina G11): ogni squadra è una `table.grades-table` preceduta da `a.team-name` con href `/serie-a/squadre/<slug>` e da un `.match-date` `"08/11/2026 - 15:00"`; ogni riga ha `span.role[data-value=p|d|c|a]`, `a.player-name` con href `/serie-a/squadre/<slug>/<nome>/<id>` e `<span>Nome</span>`; tre `div.pill`, il primo è Redazione Fantacalcio, ognuno con `span.player-grade[data-value]` (classi `yellow-card`, `red-card`) e `span.player-fanta-grade[data-value]`; voti con virgola, SV = `55`; eventi `span.player-bonus[title=...]` con `data-value`: "Gol segnati", "Gol subiti", "Autoreti", "Rigori segnati", "Rigori sbagliati", "Rigori parati", "Assist", "Player of the match". Listone: `tr.player-row[data-filter-role-classic]`, `a.player-name` come sopra, poi celle di prezzo (`data-col-key` `c_qi`, `c_qa`, `c_fvm`, `m_*`) da ignorare.

- [ ] **Step 1: Preparare i dati di prova.** Scaricare una volta a mano (con `curl`) voti G11 e quotazioni in `tests/dati/voti_vero_2026-27_11.html` e `tests/dati/quotazioni_vero.html` (esclusi da git). Ricavarne a mano `voti_ridotta.html` (3 squadre: una con un SV, un ammonito, un espulso, un rigore parato, un gol subito, un Player of the match, un nome con apostrofo; una seconda squadra con slug a due parole) e `quotazioni_ridotta.html` (6 righe, una con accento). Versionare solo i file ridotti.

- [ ] **Step 2: Scrivere i test** in `tests/test_pagine.py`:
  - `test_voti_campi`: per un giocatore noto della pagina ridotta, tutti i campi del Giocatore con i valori attesi (voto `6.5` da `"6,5"`, `fv_pubblicato`, eventi).
  - `test_voti_solo_redazione`: in una riga dove i tre pill hanno voti diversi, si legge il primo.
  - `test_sv`: `data-value="55"` → `voto is None`, `fv_pubblicato is None`.
  - `test_cartellini`: `ammonito`/`espulso` dalle classi CSS.
  - `test_squadra_e_data`: `squadre["Hellas Verona"]` (o lo slug a due parole scelto) con `data` `"2026-11-08T15:00:00+01:00"`.
  - `test_ora_italiana`: `"29/03/2026 - 12:00"` → `+02:00`; `"28/03/2026 - 12:00"` → `+01:00`; `"25/10/2026 - 12:00"` → `+01:00`; `"24/10/2026 - 12:00"` → `+02:00`.
  - `test_stagione_giornata`: dal `<title>` / meta, `"2026-27"` e `11`.
  - `test_completezza_mancano_squadre`: la ridotta ha 3 squadre → `completezza` contiene "mancano 17 squadre".
  - `test_completezza_squadra_corta`: squadra con meno di 11 righe → mancanza che la nomina.
  - `test_pagina_sbagliata`: HTML senza `grades-table` → `PaginaNonValida`; listone senza `player-row` → `PaginaNonValida`.
  - `test_listone`: 6 righe con `id`, `nome`, `squadra` (da slug), `ruolo` maiuscolo; nessuna chiave con prezzi.
  - `test_pagina_vera` (`skipUnless` il file esiste): G11 vero → 20 squadre, ≥ 300 giocatori, `completezza == []`, nessun `id` duplicato; listone vero ≥ 500 righe.

- [ ] **Step 3: Eseguire** `python3 -m unittest tests.test_pagine -v` → FAIL (modulo mancante).

- [ ] **Step 4: Implementare `consigliere/pagine.py`** con una sottoclasse di `html.parser.HTMLParser` per pagina, guidata dalle classi CSS sopra. `ora_italiana`: ora legale dall'ultima domenica di marzo all'ultima di ottobre (cambio alle 02:00/03:00 locali), senza `zoneinfo` (su Windows manca il database dei fusi).

- [ ] **Step 5: Eseguire** `python3 -m unittest tests.test_pagine -v` → PASS; poi l'intera suite `python3 -m unittest discover -s tests -v` → PASS.

- [ ] **Step 6: Aggiornare i vincoli.** In `CLAUDE.md`: il programma scarica su pulsante solo le tre pagine ammesse (rimando alla nuova spec), il listone può venire dal sito o dall'xlsx; nuovi moduli nell'architettura. Nella spec principale, righe 35 e 44, una nota che rimanda alla nuova spec.

- [ ] **Step 7: Commit**
```bash
git add consigliere/pagine.py tests/test_pagine.py tests/dati/voti_ridotta.html tests/dati/quotazioni_ridotta.html CLAUDE.md docs/superpowers/specs/2026-11-09-formazione-fantacalcio-design.md .gitignore
git commit -m "feat: lettura delle pagine pubbliche di voti e listone"
```

---

### Task 2: download e archivio delle copie (`fonti.py`)

**Files:**
- Create: `consigliere/fonti.py`, `tests/test_fonti.py`

**Interfaces:**
- Consumes: `pagine.leggi_voti`, `pagine.leggi_listone`, `pagine.completezza`, `pagine.PaginaNonValida`, `archivio.scrivi_json`
- Produces:
  - `VERSIONE = "1"` (anche nello User-Agent `ConsiglioFormazione/1`)
  - `class FonteNonAccessibile(Exception)` (messaggio in italiano con il motivo e l'invito a salvare la pagina dal browser)
  - `url_voti(stagione: str, giornata: int) -> str`; `URL_LISTONE`; `URL_PROBABILI` — `ValueError` per stagione non `AAAA-AA` o giornata fuori 1–38
  - `ammesso(url: str) -> bool`
  - `class Scaricatore` con `__init__(self, apri=urllib.request.urlopen, orologio=time.monotonic, dormi=time.sleep)` e `scarica(self, url: str) -> bytes` (rifiuta URL non ammessi con `ValueError` prima di aprire; aspetta fino a 3 s dall'ultima richiesta; HTTP ≠ 200, errore di rete o timeout → `FonteNonAccessibile`). Un'istanza unica condivisa dal server.
  - `archivia(base: Path, tipo: "voti"|"listone"|"probabili", chiave: str, html: bytes, url: str, origine: "scaricata"|"caricata_a_mano", riepilogo: dict) -> dict` → scrive `fonti/<tipo>/<chiave>/<AAAAMMGG-HHMMSS>.html` e `.json` `{url, ora, origine, sha256, versione_lettore, riepilogo, file}`; se il nome esiste già aggiunge `-2`, `-3`…; ritorna i metadati.
  - `ultima(base: Path, tipo: str, chiave: str) -> tuple[dict, str] | None` (metadati e HTML dell'ultima copia)
  - `copie(base, tipo, chiave) -> list[dict]` (metadati, più recente prima)
  - `differenze_voti(prima: dict, dopo: dict) -> list[dict]` (`{"id", "nome", "campo", "prima", "dopo"}` per voto, fv_pubblicato ed eventi cambiati, più giocatori comparsi/scomparsi)
  - `acquisisci_voti(base, stagione, giornata, html: bytes|None, scaricatore: Scaricatore|None) -> dict` → se `html` è `None` scarica, altrimenti `origine="caricata_a_mano"`; decodifica UTF-8 (errore chiaro se fallisce); `leggi_voti`; controlla che stagione e giornata della pagina coincidano con quelle chieste (altrimenti `PaginaNonValida`, niente archivio); archivia con `riepilogo={"giocatori": n, "mancanze": [...]}`; ritorna `{"meta", "voti", "differenze"}` (differenze con la copia precedente, se c'è)
  - `acquisisci_listone(base, html: bytes|None, scaricatore) -> dict` → idem con `chiave="listone"`; ritorna `{"meta", "giocatori"}`

- [ ] **Step 1: Scrivere i test** in `tests/test_fonti.py` (cartella temporanea, nessuna rete):
  - `test_url_ammessi`: `url_voti("2026-27", 11)` esatto; `ammesso` vero per le tre forme; falso per `http://`, `leghe.fantacalcio.it/...`, `www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/11?x=1`, `.../2026-27/39`, `.../../`; `url_voti("2026", 1)` → `ValueError`.
  - `test_rifiuta_prima_di_aprire`: `Scaricatore(apri=finto)`, `scarica("https://example.com")` → `ValueError` e `finto` mai chiamato.
  - `test_pausa_e_user_agent`: con orologio e `dormi` finti, due `scarica` ravvicinati → `dormi` chiamato con ≈ 3 − trascorso; la richiesta passata ad `apri` ha `User-Agent == "ConsiglioFormazione/1"` e `timeout=30`.
  - `test_errore_http`: `apri` che solleva `HTTPError 403` → `FonteNonAccessibile` col codice nel messaggio.
  - `test_archivia_sha_e_nessuna_sovrascrittura`: due `archivia` nello stesso secondo → due file distinti; `sha256` uguale a `hashlib.sha256(html).hexdigest()`; il primo file intatto.
  - `test_acquisisci_manuale_giornata_sbagliata`: `voti_ridotta.html` (G11) caricata chiedendo G10 → `PaginaNonValida`, cartella `fonti/` vuota.
  - `test_acquisisci_non_utf8`: `b"\xff\xfe..."` → errore con messaggio "non è una pagina salvata in UTF-8"; nulla archiviato.
  - `test_differenze`: due versioni con un voto cambiato e un giocatore in più → due voci attese.

- [ ] **Step 2: Eseguire** `python3 -m unittest tests.test_fonti -v` → FAIL.
- [ ] **Step 3: Implementare `consigliere/fonti.py`** secondo le interfacce.
- [ ] **Step 4: Eseguire** `python3 -m unittest tests.test_fonti -v` → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: download controllato e archivio delle pagine con impronta"` (aggiungere i due file).

---

### Task 3: regole di punteggio (`punteggio.py`, parte 1)

**Files:**
- Create: `consigliere/punteggio.py`, `tests/test_punteggio.py`

**Interfaces:**
- Consumes: forma del Giocatore (Task 1), forma della lega (`consigliere/modelli/*.json`)
- Produces:
  - `BONUS_STANDARD = {"gol": 3, "rigore_segnato": 3, "rigore_parato": 3, "rigore_sbagliato": -3, "assist": 1, "gol_subito": -1, "autogol": -2, "ammonizione": -0.5, "espulsione": -1}` (senza porta inviolata e Player of the match: così è il FV pubblicato)
  - `voto_effettivo(g: dict|None, ammonito_senza_voto: bool) -> float|None` → `None` se assente o SV, salvo SV ammonito con la regola attiva → `5.5`
  - `fv_lega(g: dict|None, lega: dict) -> float|None` → voto effettivo + Σ eventi × `lega["bonus"]` + `porta_inviolata` al ruolo `P` con voto e `gol_subiti == 0`. SV ammonito: `5.5 + bonus["ammonizione"]`.
  - `fv_coerente(g: dict) -> bool` → con `BONUS_STANDARD` il ricalcolo coincide con `fv_pubblicato` (tolleranza 1e-9); `True` per gli SV
  - `bonus_capitano(voto: float, capitano: dict) -> float` → `capitano["fasce"]` è `[["<=5.5", 0], ["6", 0.5], ..., [">=7.5", 2]]`: bonus della fascia con soglia numerica più alta ≤ voto, 0 sotto la più bassa
  - `voto_mezzo(voto: float) -> bool` (multiplo di 0,5; altrimenti il bonus capitano è "da verificare")
  - `modificatore(voto_portiere: float|None, voti_difensori: list[float], fasce: list[float]) -> tuple[float|None, float]` → `(media, bonus)`; `(None, 0)` se il portiere è senza voto o i difensori con voto sono meno di 4; media = (portiere + 3 voti più alti)/4; indici di fascia `<6, [6,6.25), [6.25,6.5), [6.5,6.75), [6.75,7), [7,7.25), ≥7.25` → `fasce[0..6]`
  - `fasce_monotone(fasce: list[float]) -> bool`

Con `lega["modificatore_difesa"]["attivo"]` falso il modificatore vale 0; con `lega["capitano"]["attivo"]` falso il bonus capitano vale 0.

- [ ] **Step 1: Scrivere i test:**
  - `test_fv_gol_assist_cartellino`: voto 6,5, 1 gol, 1 assist, ammonito, lega `libera` → `6.5+3+1-0.5 = 10.0`.
  - `test_fv_porta_inviolata`: P voto 6, 0 gol subiti → libera `7.0`; con 2 gol subiti → `4.0`; P SV → `None`.
  - `test_fv_player_of_the_match`: voto 7 con POTM → pensionati `7.5`, f1 `8.0`, libera `7.0`.
  - `test_sv_ammonito`: SV ammonito → pensionati `5.0` (5,5 − 0,5), libera `None`.
  - `test_fv_coerente`: giocatore con `fv_pubblicato` uguale al ricalcolo → `True`; con assist e FV pubblicato di 0,5 più basso → `False`.
  - `test_capitano_confini` (fasce di `libera.json`): 5.5→0, 6→0.5, 6.5→1, 7→1.5, 7.5→2, 8.5→2, 5→0, 6.25→0.5 e `voto_mezzo(6.25)` falso.
  - `test_modificatore_confini` (fasce `[1,2,3,4,5,6,6]`): medie 5.99→1, 6→2, 6.24→2, 6.25→3, 6.5→4, 6.75→5, 7→6, 7.25→6; fasce F1 `[0,1,1,3,3,6,6]` media 6.75→3.
  - `test_modificatore_tre_migliori`: portiere 7, difensori `[7, 6.5, 6.5, 4]` → media 6.75 → `+5`.
  - `test_modificatore_pochi_difensori`: 3 difensori con voto → `(None, 0)`; portiere `None` → `(None, 0)`.
  - `test_fv_pagina_vera` (`skipUnless` G11 vero): `fv_coerente` vero per almeno il 95% dei giocatori con voto; stampare i casi falsi (servono a scoprire voci come l'assist da fermo).

- [ ] **Step 2: Eseguire** `python3 -m unittest tests.test_punteggio -v` → FAIL.
- [ ] **Step 3: Implementare** le funzioni in `consigliere/punteggio.py`.
- [ ] **Step 4: Eseguire** → PASS. Se `test_fv_pagina_vera` scende sotto il 95%, guardare i casi stampati: se gol e rigori segnati sono contati due volte nella pagina, correggere `fv_lega` e `BONUS_STANDARD` di conseguenza e annotarlo in un commento.
- [ ] **Step 5: Commit** `git commit -m "feat: fantavoto della lega, capitano e modificatore"`.

---

### Task 4: valore di una formazione (`punteggio.valuta`)

**Files:**
- Modify: `consigliere/punteggio.py`, `tests/test_punteggio.py`

**Interfaces:**
- Consumes: Task 3
- Produces:
  - Formazione in ingresso: `{"modulo": "4-3-3", "titolari": [{"id", "ruolo"}], "panchina": [{"id", "ruolo"}] (in ordine), "capitano": id|None, "vice": id|None, "switch": {"titolare": id, "riserva": id}|None}`
  - `valuta(lega: dict, voti: dict[str, dict], f: dict) -> dict` con `voti` = Giocatori per `id` (assente = SV) →
    `{"totale": float, "totale_senza_vice": float|None, "stato": "ESATTO"|"PROVVISORIO"|"DATI_INCOMPLETI", "motivi": [str], "giocatori": [{"id", "nome", "ruolo", "voto", "fv", "titolare": bool, "in_campo": bool, "entrato": bool, "uscito": bool, "fv_coerente": bool}], "cambi": [{"esce": id, "entra": id, "ruolo_diverso": bool}], "modificatore": {"media", "bonus"}, "capitano": {"id", "bonus", "da": "capitano"|"vice"|None}, "con_switch": dict|None}`

Regole (dalla spec, sezione 2):
- Titolari con voto effettivo restano; ogni titolare senza voto viene trattato nell'ordine P→D→C→A e, dentro il ruolo, nell'ordine dei titolari.
- `traditional`: entra la prima riserva in panchina, non ancora entrata, con voto e stesso ruolo; si contano i cambi fino a `lega["sostituzioni"]["numero"]` (`None` = illimitati).
- `hybrid`: se manca il pari ruolo, la prima riserva con voto di qualsiasi ruolo (mai un portiere per un non portiere e viceversa) tale che il modulo risultante sia in `lega["moduli"]`; se un cambio così entra, motivo "cambio di ruolo diverso (regola Hybrid da verificare)".
- Se i titolari senza voto sono più dei cambi possibili, ricalcolare il totale con ogni ordine dei titolari senza voto (`itertools.permutations`); totali diversi → motivo "ordine dei cambi da verificare".
- Capitano senza voto: `bonus_capitano` del vice se ha voto; `totale_senza_vice` = totale senza quel bonus; motivo "subentro del vice da verificare". Capitano con voto non multiplo di 0,5 → motivo.
- Modificatore sugli 11 in campo dopo i cambi.
- Un giocatore in campo con `fv_coerente` falso → motivo "FV di <nome> da verificare".
- `stato`: `PROVVISORIO` se ci sono motivi, altrimenti `ESATTO` (`DATI_INCOMPLETI` lo decide `verifica.py`).
- `switch` presente: `con_switch = valuta(...)` sulla formazione con titolare e riserva scambiati (stessa posizione in panchina), senza ulteriore Switch.

- [ ] **Step 1: Scrivere i test** (piccole leghe e voti costruiti nei test, modelli reali per le regole):
  - `test_tutti_con_voto`: 4-3-3 libera senza SV → totale = Σ FV + modificatore + capitano a mano; nessun cambio; `ESATTO`.
  - `test_cambio_stesso_ruolo`: D titolare SV → entra il primo D di panchina con voto, saltando un D SV prima di lui.
  - `test_limite_cambi_grossa`: 8 titolari SV, `numero: 7` → 7 cambi, il totale conta un solo SV a 0.
  - `test_ordine_cambi_ininfluente` e `test_ordine_cambi_influente`: con un solo cambio disponibile e due titolari SV di ruolo diverso, motivo presente solo quando i totali differiscono.
  - `test_hybrid_ruolo_diverso`: F1, A titolare SV, nessun A in panchina, un C con voto: entra se 4-4-2 → modulo ammesso; motivo presente; in una lega con soli moduli che non lo ammettono non entra.
  - `test_portiere_solo_portiere`: P SV e nessun P in panchina con voto → nessun cambio anche in Hybrid.
  - `test_capitano_sv_vice`: capitano SV, vice voto 7 → `capitano.da == "vice"`, bonus 1.5, `totale_senza_vice == totale - 1.5`, `PROVVISORIO`.
  - `test_ammonito_senza_voto_non_sostituito`: pensionati, titolare SV ammonito → resta in campo con 5.0, nessun cambio.
  - `test_modificatore_dopo_cambi`: un D titolare SV sostituito da un D con voto 7 cambia la fascia.
  - `test_switch`: pensionati, `switch` titolare→riserva: `con_switch.totale` calcolato sullo scambio; `totale` senza.
  - `test_fv_incoerente_provvisorio`: giocatore in campo con `fv_coerente` falso → motivo.

- [ ] **Step 2: Eseguire** `python3 -m unittest tests.test_punteggio -v` → FAIL sui nuovi test.
- [ ] **Step 3: Implementare `valuta`** in `consigliere/punteggio.py`.
- [ ] **Step 4: Eseguire** → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: punteggio di una formazione con sostituzioni, capitano e Switch"`.

---

### Task 5: formazione perfetta (`ottimo.py`)

**Files:**
- Create: `consigliere/ottimo.py`, `tests/test_ottimo.py`

**Interfaces:**
- Consumes: `punteggio.bonus_capitano`, `punteggio.modificatore`, `punteggio.fasce_monotone`
- Produces:
  - Candidato: `{"id": str, "ruolo": str, "voto": float, "fv": float}` (solo giocatori con voto effettivo; il chiamante calcola `fv` con `fv_lega`)
  - `migliore(lega: dict, candidati: list[dict]) -> dict|None` → `{"totale", "modulo", "titolari": [id], "capitano": id|None, "bonus_capitano", "modificatore": {"media", "bonus"}, "somma_fv"}`; `None` se nessun modulo ammesso è completabile
  - `enumera(lega, candidati) -> dict|None` stessa uscita, per enumerazione completa (riferimento per i test e insiemi ≤ 18 giocatori)

Algoritmo di `migliore`, per ogni modulo `d-c-a` in `lega["moduli"]` (n_P = 1):
1. **Potatura esatta per dominanza:** in ogni ruolo con quota n si scarta un giocatore se almeno n altri dello stesso ruolo hanno voto ≥ e fv ≥ (con almeno una disuguaglianza stretta, o parità risolta per id). Vale se le fasce del modificatore sono monotone (`fasce_monotone`); altrimenti, per la difesa, si torna alla riduzione di FantaLab (i migliori n per fv a ogni livello di voto).
2. **Pacchetti portiere+difesa:** combinazioni di n_D difensori potati × portieri potati; per ognuno somma fv + modificatore (0 se non attivo o n_D < 4) e `cap_max` = miglior bonus capitano del pacchetto; per ogni livello di bonus capitano si tiene il pacchetto migliore con `cap_max` ≥ livello.
3. **Centrocampo e attacco:** per ogni livello `b` i migliori n per fv con almeno uno di bonus ≥ b (come `group_best_k` di FantaLab: i primi n se ne contengono uno, altrimenti i primi n−1 più il miglior idoneo).
4. Per ogni livello `b` della lega (solo 0 senza capitano): massimo tra "il livello lo garantisce la difesa / il centrocampo / l'attacco", con gli altri reparti al livello 0. Totale = pacchetto + C + A + b.
5. Massimo su moduli e livelli; a pari totale vince l'undici con la tupla di id ordinata più piccola; capitano = titolare con bonus più alto (poi voto, fv, id).

Tempo: perfetta assoluta di una lega a 7 moduli su una giornata vera sotto 10 s.

- [ ] **Step 1: Scrivere i test:**
  - `test_uguale_a_enumera_casuale`: 300 insiemi casuali (seme fisso `random.Random(n)`), 2–3 P, 6–8 D, 5–7 C, 4–6 A, voti in passi di 0,5 tra 4 e 8, fv = voto + bonus casuali; per le regole di `libera`, `grossa`, `f1`, `pensionati` (con capitano e modificatore attivi e non) → `migliore(...)["totale"] == enumera(...)["totale"]`.
  - `test_uguale_a_fantalab`: 50 insiemi casuali più grandi in 4-3-3 libera, confronto con `solve_best_xi` di `fantalab/strumenti/ottimizza.py` (import con `importlib.util.spec_from_file_location`, Player costruiti dai candidati) → stesso totale.
  - `test_difensore_per_la_fascia`: costruito a mano, il quarto difensore con fv più basso ma voto più alto fa salire il modificatore e vince.
  - `test_attaccante_per_il_capitano`: un attaccante con fv più basso ma voto 8 batte uno con fv più alto e voto 6.
  - `test_ruolo_insufficiente`: 3 attaccanti in tutto e moduli che ne chiedono 3 → ok; con 2 → `None`.
  - `test_tempo_pagina_vera` (`skipUnless` G11 vero): `migliore` con le regole `grossa` (7 moduli) sotto 10 s.

- [ ] **Step 2: Eseguire** `python3 -m unittest tests.test_ottimo -v` → FAIL.
- [ ] **Step 3: Implementare `enumera`** (tutte le combinazioni per modulo; capitano = miglior bonus dell'undici) e far passare i test che la usano da sola.
- [ ] **Step 4: Implementare `migliore`** come sopra.
- [ ] **Step 5: Eseguire** → PASS.
- [ ] **Step 6: Commit** `git commit -m "feat: formazione perfetta esatta per ogni modulo e lega"`.

---

### Task 6: sigillo e verifica (`ricerca.py`, `controllo.py`, `verifica.py`)

**Files:**
- Modify: `consigliere/ricerca.py` (sigillo in `stato_ricerca`), `consigliere/controllo.py` (funzione pubblica), `tests/test_ricerca.py`, `tests/test_controllo.py`
- Create: `consigliere/verifica.py`, `tests/test_verifica.py`

**Interfaces:**
- Consumes: Task 2 (`fonti.ultima`), Task 3–5, `controllo.chiave`, `listone._compatto`
- Produces:
  - `ricerca.sigilla(cartella: Path) -> dict` → se non c'è già una riga per questa ricerca in `<base>/registro.jsonl` (base = `cartella.parents[2]`), aggiunge `{"ricerca", "lega", "fatto_il" (mtime di FATTO, ISO con fuso), "sigillato_il", "sha256_risultato", "sha256_richiesta"}` con apertura in aggiunta (`"a"`); ritorna la riga. Chiamata da `stato_ricerca` quando lo stato è `pronto`.
  - `ricerca.sigillo(base: Path, lega_id: str, rid: str) -> dict|None`
  - `controllo.controlla_formazione(f: dict, lega: dict, listone: list[dict]) -> list[str]` (involucro pubblico di `_controlla_formazione` con etichetta "schierata", rosa della lega se `tipo == "rosa"`)
  - `verifica.STAGIONE_CORRENTE = "2026-27"`
  - `verifica.scadenza(voti: dict, lega: dict) -> str|None` (data più presto tra `voti["squadre"]` − `anticipo_minuti`)
  - `verifica.consigliata(base, lega_id, giornata: int, scadenza: str|None) -> dict` → `{"scelta": {"ricerca", "risultato", "fatto_il", "sigillo": "integro"|"alterato"|"assente"}|None, "dopo_scadenza": [id], "senza_giornata": [id]}`; candidate: ricerche `pronto` con `risultato["giornata"] == giornata` e `fatto_il < scadenza` (senza scadenza: nessuna scelta, motivo); vince il `fatto_il` più recente; `sigillo` confronta l'impronta attuale di `risultato.json` col registro.
  - `verifica.collega(giocatori: list[dict], voti: dict, listone: list[dict]) -> tuple[list[dict], list[dict]]` → giocatori della formazione (`nome`, `squadra`, `ruolo`, `id` facoltativo) arricchiti con `id` di fantacalcio.it e ruolo; abbinamento per `id` se c'è, poi per `chiave(nome, squadra)` con squadra confrontata come in `listone._squadra_coincide` sui nomi compatti (prefisso ≥ 3 lettere in un senso o nell'altro); più candidati o nessuno → nella seconda lista, mai scelti a caso. Un giocatore assente dalla pagina dei voti ma presente nel listone con `id` resta collegato (sarà SV).
  - `verifica.formazione_da(f_risultato: dict, collegati: list[dict]) -> dict` (forma di `punteggio.valuta`)
  - `verifica.calcola(lega: dict, voti: dict, listone: list[dict], consigliata: dict|None, schierata: dict|None) -> dict` → `{"giornata", "lega", "stato", "motivi", "voti": {"sha256", "ora", "origine", "mancanze"}, "misure": {"perfetta_assoluta", "perfetta_rosa"|None, "consigliata": {"ottenuto": valuta, "migliore_tra_18", "assoluta_ottenuto"|None}, "schierata": {...}|None}, "regret": {"totale", "limite_rosa", "selezione", "schieramento"}` per consigliata e schierata, `"errori": [...]}`
  - `verifica.salva(base, lega_id, stagione, giornata, dati) -> Path` → `verifiche/<lega>/<stagione>/G<nn>/v<k>/verifica.json` e `report.md`, k = successivo al massimo esistente
  - `verifica.versioni(base, lega_id, stagione, giornata) -> list[dict]` (k, ora, stato, totali)
  - `verifica.salva_schierata(base, lega_id, stagione, giornata, f: dict) -> int` (`schierata-v<k>.json` nella cartella della giornata) e `verifica.schierata(base, lega_id, stagione, giornata) -> dict|None` (l'ultima)
  - `verifica.report_md(dati: dict) -> str`

Regole di `calcola` (spec, sezioni 3–4):
- Candidati per `ottimo.migliore`: giocatori della pagina con voto effettivo, `fv = fv_lega`; per i giocatori della rosa vale `lega["ruoli"]` se presente.
- Perfetta della rosa: solo i candidati collegati alla rosa (`tipo == "rosa"`). Migliore tra i 18: i candidati tra titolari e panchina della formazione.
- Regret: `limite_rosa` = assoluta − rosa (0 se libera); `selezione` = (rosa o assoluta) − migliore tra 18; `schieramento` = migliore tra 18 − ottenuto; `totale` = somma delle tre.
- Per le leghe a rosa anche `formazioni.assoluta` della consigliata si valuta contro la perfetta assoluta (`assoluta_ottenuto`).
- `errori`: titolari SV con punti recuperati (FV di chi è entrato) o persi (titolare SV non sostituito); capitano scelto contro miglior capitano del proprio undici in campo; modificatore ottenuto contro quello del `migliore_tra_18`; giocatori della perfetta non tra i 18 con fv.
- `stato`: `DATI_INCOMPLETI` se `pagine.completezza` non è vuota; altrimenti `PROVVISORIO` se ci sono motivi (dalle `valuta`, sigillo non integro o assente, giocatori non collegati, nessuna consigliata); altrimenti `CERTIFICATO`.
- Report: titolo con lega, giornata, stato in evidenza e motivi; tabella misure; regret; dettaglio giocatori; errori; impronte; "uno degli ottimi" accanto alla perfetta.

- [ ] **Step 1: Test del sigillo** in `tests/test_ricerca.py`: `test_sigillo_una_volta` (due `stato_ricerca` su ricerca pronta → una sola riga), `test_sigillo_registro_solo_aggiunta` (righe precedenti intatte dopo un nuovo sigillo). In `tests/test_controllo.py`: `test_controlla_formazione_pubblica` (formazione valida → `[]`; con un doppione → errore).
- [ ] **Step 2: Test della verifica** in `tests/test_verifica.py` (voti e ricerche costruiti con `tests/aiuti.py` e Giocatori sintetici con `id`):
  - `test_consigliata_prima_della_scadenza`: due ricerche pronte, una prima e una dopo → scelta la prima, l'altra in `dopo_scadenza`.
  - `test_consigliata_altra_giornata`: ricerca con `giornata` 12 per la verifica della 11 → esclusa.
  - `test_sigillo_alterato`: `risultato.json` modificato dopo il sigillo → `sigillo == "alterato"`, stato `PROVVISORIO`.
  - `test_collega_omonimi_e_squadre`: due "Rossi" in squadre diverse si abbinano con la squadra; "Rossi" senza squadra → non collegato; "Verona" ↔ "Hellas Verona" collegato; `N'Dicka` con apostrofo collegato.
  - `test_regret_somma`: lega a rosa, i tre addendi sommano a `regret.totale` e ognuno è ≥ 0.
  - `test_libera_limite_rosa_zero`.
  - `test_dati_incompleti`: voti con 3 squadre → stato `DATI_INCOMPLETI`, misure calcolate comunque.
  - `test_versioni_non_sovrascritte`: due `salva` → `v1` e `v2`, `v1` invariata.
  - `test_schierata_versioni`: due `salva_schierata` → si legge l'ultima, la prima resta.
- [ ] **Step 3: Eseguire** `python3 -m unittest tests.test_ricerca tests.test_controllo tests.test_verifica -v` → FAIL sui nuovi.
- [ ] **Step 4: Implementare** sigillo, `controlla_formazione` e `consigliere/verifica.py`.
- [ ] **Step 5: Eseguire** l'intera suite → PASS.
- [ ] **Step 6: Commit** `git commit -m "feat: sigillo delle ricerche e verifica della giornata con regret"`.

---

### Task 7: G10 e G11 di FantaLab

**Files:**
- Modify: `consigliere/verifica.py` (blocco `main`), `tests/test_verifica.py`

**Interfaces:**
- Consumes: Task 2 (`fonti.ultima`, `fonti.acquisisci_voti`), Task 6
- Produces:
  - `verifica.abbina_fantalab(slug: str, voti: dict) -> list[dict]` (candidati: `wesley_roma` → nome compatto che inizia con `wesley` e squadra che inizia con `roma`; `maignan` → solo nome)
  - `verifica.formazione_fantalab(previsione: dict, abbinamenti: dict[str, str]) -> dict` (forma di `valuta`: titolari e panchina nell'ordine P, D, C, A; capitano `previsione["capitano"]`, vice `previsione["vicecapitano"]`)
  - `python3 -m consigliere.verifica --fantalab <cartella fantalab> --giornata <n> [--cartella <base>]`: usa l'ultima copia dei voti (o la scarica, chiedendo conferma su terminale); G11 → abbina gli slug di `stagioni/2026-27/G11/previsione_macchina.json` (casi ambigui o assenti chiesti con `input()`, risposte salvate in `<base>/fantalab/abbinamenti.json`), valuta con le regole di `consigliere/modelli/libera.json` e salva in `verifiche/fantalab/2026-27/G11/`; G10 → perfetta assoluta, confronto con 125 e con l'undici di `BENCHMARK_PROVVISORIO.md` (elencato nel report come testo), salvataggio in `verifiche/fantalab/2026-27/G10/`. Non scrive mai dentro `<cartella fantalab>`.

- [ ] **Step 1: Scrivere i test:** `test_abbina_slug` (con squadra, senza, ambiguo → 2 candidati); `test_formazione_fantalab` (dalla vera `previsione_macchina.json` con abbinamenti finti → 11 titolari, 7 riserve, capitano e vice); `test_cli_non_scrive_in_fantalab` (copia temporanea di `fantalab/`, impronte di tutti i file prima e dopo uguali, con voti sintetici e `input` simulato).
- [ ] **Step 2: Eseguire** → FAIL.
- [ ] **Step 3: Implementare** le funzioni e `main` con `argparse`.
- [ ] **Step 4: Eseguire** → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: verifica di G10 e G11 di FantaLab senza modificarli"`.

---

### Task 8: API, listone dal sito e avviso aggiornato

**Files:**
- Modify: `consigliere/server.py`, `consigliere/archivio.py`, `tests/test_server.py`, `tests/test_archivio.py`

**Interfaces:**
- Consumes: Task 2, Task 6
- Produces (API, tutte dietro `_ammessa`):
  - `POST /api/fonti/voti` — JSON `{"stagione", "giornata"}` → scarica; oppure corpo HTML grezzo con query `?stagione=2026-27&giornata=11` → caricata a mano. Limite 8 MB (`MAX_PAGINA`). Risposta `{"meta", "giocatori": n, "mancanze", "differenze"}`. `FonteNonAccessibile` → 502 con messaggio; `PaginaNonValida` → 400.
  - `POST /api/fonti/listone` — senza corpo → scarica; con HTML → caricato. Salva con `archivio.salva_listone(giocatori, origine)`; risposta `{"numero", "meta"}`.
  - `GET /api/verifica/<lega>/<stagione>/<giornata>` → `{"versioni": [...], "ultima": dati|None, "schierata": dict|None, "voti": meta|None}`
  - `POST /api/verifica/<lega>/<stagione>/<giornata>` → calcola con l'ultima copia dei voti (409 "Scarica prima i voti della giornata." se manca) e salva una nuova versione; risposta `{"versione", "dati"}`
  - `POST /api/verifica/<lega>/<stagione>/<giornata>/schierata` — `{"testo", "modulo", "panchina": [testo...], "capitano", "vice"}` → abbina con `listone.abbina` (ambigui/non trovati → 409 con l'elenco), controlla con `controllo.controlla_formazione` (errori → 409), salva; risposta `{"versione"}`
  - `archivio.salva_listone(giocatori, origine="xlsx")` aggiunge `origine`; `archivio.avviso_accettato()` vero solo se `avviso.json` ha `versione >= 2`; `accetta_avviso()` scrive `versione: 2`.
  - Scaricatore unico per server (rispetta la pausa tra richieste di più pagine aperte).

- [ ] **Step 1: Scrivere i test** in `tests/test_server.py` (server su porta libera come i test esistenti, `Scaricatore` finto iniettato tramite parametro nuovo `crea_server(..., scaricatore=None)`):
  - `test_voti_scaricati` e `test_voti_caricati_a_mano` (pagina ridotta) → 200 e copia archiviata.
  - `test_voti_fonte_non_accessibile` → 502 col messaggio che invita a salvare la pagina.
  - `test_voti_pagina_troppo_grande` → 413; `test_voti_non_utf8` → 400.
  - `test_verifica_senza_voti` → 409; `test_verifica_crea_versioni` → due POST, `versioni` lunga 2.
  - `test_schierata_ambigua` → 409 con l'elenco.
  - `test_host_estraneo_verifica` → 403 sulle nuove API.
  - In `tests/test_archivio.py`: `test_avviso_vecchio_da_riaccettare` (`avviso.json` senza `versione` → non accettato).
- [ ] **Step 2: Eseguire** `python3 -m unittest tests.test_server tests.test_archivio -v` → FAIL.
- [ ] **Step 3: Implementare** le API e le modifiche ad `archivio.py`.
- [ ] **Step 4: Eseguire** l'intera suite → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: API per voti, listone dal sito e verifica della giornata"`.

---

### Task 9: vista Verifica nell'interfaccia e guida

**Files:**
- Modify: `consigliere/web/app.js`, `consigliere/web/style.css`, `GUIDA.md`

**Interfaces:**
- Consumes: API del Task 8.
- Produces: vista `verifica` registrata in `disegna()`; pulsante "Verifica" in `cartaLega`; in `cartaListone` "Aggiorna dal sito" e "Carica la pagina salvata".

Contenuto (spec, sezione 4):
- Scelta di stagione (predefinita `2026-27`) e giornata.
- "Scarica i voti" e "Carica la pagina salvata" (input file `.html`); dopo l'errore 502 il messaggio del server e il link alla pagina da salvare (costruito dal programma, non dal server).
- Mancanze e differenze tra versioni dei voti.
- Campo per la schierata (testo come per la rosa, modulo, panchina in ordine, capitano, vice) con elenco di ambigui/non trovati.
- Report: stato in grande con i motivi; tabella misure (perfetta assoluta, perfetta della rosa, migliore tra i 18, ottenuto) per consigliata e schierata; regret scomposto; dettaglio giocatori con entrati/usciti; errori; elenco versioni.
- Testo dell'`AVVISO` aggiornato: ora anche il programma scarica, su pulsante, voti, listone e probabili formazioni.
- Tutto con `el(...)`/`textContent`; link solo tramite `link(url, testo)` esistente.

- [ ] **Step 1: Implementare** la vista e i pulsanti in `app.js`/`style.css`.
- [ ] **Step 2: Verificare** `python3 -m unittest discover -s tests -v` → PASS (nessuna regressione).
- [ ] **Step 3: Verificare nel browser** con `python3 -m consigliere --cartella <dir temporanea> --porta 8766 --senza-browser` e l'anteprima: accettare il nuovo avviso; caricare a mano `tests/dati/voti_ridotta.html` per una lega di prova; calcolare la verifica; controllare stato `DATI_INCOMPLETI`, misure, versioni, nessun errore in console. Non premere "Cerca la formazione".
- [ ] **Step 4: Aggiornare `GUIDA.md`** con un paragrafo "Dopo la giornata: la verifica" (scaricare i voti, cosa fare se il download fallisce, scrivere la schierata, leggere stato e regret).
- [ ] **Step 5: Commit** `git commit -m "feat: vista Verifica e guida"`.

---

### Task 10: prova reale e chiusura

**Files:**
- Modify: `CLAUDE.md` (stato del repository), `fantalab/` **no**.

- [ ] **Step 1: Download reale una tantum** (dichiarato all'utente): `python3 -m consigliere.verifica --fantalab fantalab --giornata 10` e `--giornata 11` con `--cartella` di prova; annotare esito HTTP, numero giocatori, `completezza`, percentuale `fv_coerente`, casi incoerenti.
- [ ] **Step 2: Riportare all'utente** totale perfetta G10 contro 125 e verifica della previsione G11, con lo stato e i motivi. Non dichiarare `CERTIFICATO` se i motivi lo impediscono.
- [ ] **Step 3: Aggiornare `CLAUDE.md`** (stato del repository: verifica implementata, cosa resta della spec "Fuori da questa spec") e commit `git commit -m "docs: CLAUDE.md aggiornato alla verifica della giornata"`.
