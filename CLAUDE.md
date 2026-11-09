# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stato del repository

Il **consigliere di formazione Fantacalcio** è implementato (Task 1–7 del piano). Del Task 8 restano le prove reali: Claude su Mac, Gemini su Windows, controllo degli indirizzi contattati. Il registro delle decisioni prese durante l'implementazione sta in `.superpowers/sdd/2026-11-09-consigliere-formazione/progress.md` (non versionato).

La **verifica della giornata** (seconda fase) è implementata: voti e listone dalle pagine pubbliche, punteggio di una formazione, formazione perfetta esatta, regret scomposto, sigillo delle ricerche, vista Verifica, verifica di G10/G11 di FantaLab. Spec `docs/superpowers/specs/2026-11-09-verifica-giornata-design.md`, piano `docs/superpowers/plans/2026-11-09-verifica-giornata.md`. Prova reale del 9/11/2026: G10 perfetta 125 (benchmark confermato), G11 previsione 83 contro perfetta 114,5. Restano fuori (sezione "Fuori da questa spec"): strategie A/B nell'app, modello quantitativo, dati passati all'IA, andamento su più giornate, esportazioni.

- Spec (approvata): `docs/superpowers/specs/2026-11-09-formazione-fantacalcio-design.md`, con le bozze dell'interfaccia in `bozze-interfaccia/s1–s5.png`.
- Piano a task (TDD, un commit per task): `docs/superpowers/plans/2026-11-09-consigliere-formazione.md`. Contiene interfacce, formati JSON (lega, `richiesta.json`, `risultato.json`, `ia.json`), tabella API e test da scrivere. **È la fonte di verità per l'implementazione**: leggerlo prima di toccare il codice.
- `FantaLab_v1.2_2026-27.zip`: progetto preesistente (regole, metodo A/B, `strumenti/ottimizza.py` e `confronta_strategie.py`, solo 4-3-3 fisso). Il piano prevede di estrarlo invariato in `fantalab/`. Le giornate archiviate G10/G11 e ogni file marcato `CONGELATO` non vanno mai modificati.
- `PROMPT_FANTALAB.md`: prompt portabile di FantaLab per altre IA.
- `regole/` (in `.gitignore`, non nel clone): screenshot delle impostazioni delle tre leghe reali; i valori sono già riportati nella tabella "Regole di una lega" della spec.

Documenti, interfaccia e messaggi d'errore sono in italiano; i nomi nel codice anche (`archivio`, `controlla`, `rosa`, `panchina`…).

## Architettura prevista

Python 3.11+ con **sola libreria standard**, HTML/CSS/JS senza librerie, nessuna chiave API.

- `consigliere/server.py`: server HTTP solo su `127.0.0.1` (porta 8765, poi una libera), API JSON e file statici di `consigliere/web/`. Controlla `Host` e `Origin`.
- `consigliere/archivio.py`: leghe, listone e avviso in `~/ConsiglioFormazione/` (fuori dal repo), scritture atomiche.
- `consigliere/ricerca.py`: per ogni ricerca crea `ricerche/<lega>/<AAAAMMGG-HHMMSS>/` con `richiesta.json`, `SKILL.md`, `controlla.py` e uno script (`.command` / `.bat`), poi apre un **terminale interattivo** con la CLI dell'IA scelta (Claude, Gemini, OpenCode) secondo `consigliere/ia.json`.
- L'IA lavora in quella cartella, scrive `risultato.json` ed esegue il controllo; `controlla.py` crea `FATTO` quando il risultato è valido o al terzo tentativo. La pagina interroga lo stato ogni 3 secondi e il server **ricontrolla sempre** con la propria `controllo.py` e con la propria copia della richiesta (`<id>.richiesta.json`, fuori dalla cartella dell'IA), mai con i file che l'IA può modificare. "Ho chiuso il terminale" crea `CHIUSA`.
- `consigliere/controllo.py`: file unico senza import locali, perché viene copiato in ogni ricerca. Verifica moduli, ruoli, rosa, doppioni, panchina, capitano, Switch, schede, link.
- `consigliere/pagine.py`: lettura con `html.parser` delle pagine pubbliche di fantacalcio.it (voti della giornata, listone Classic dalle quotazioni), guidata dalle classi CSS e dai `data-value`; `ora_italiana` calcola l'ora legale senza `zoneinfo`. Pagine di prova in `tests/dati/` (`*_ridotta.html` versionate, `*_vero*.html` escluse da git).
- `consigliere/fonti.py`: elenco chiuso di URL ammessi, download (pausa 3 s, nessun redirect, massimo 8 MB) e archivio append-only delle copie in `fonti/<tipo>/<chiave>/` con SHA-256 (chiave `<stagione>-<giornata>` per i voti, `listone` per il listone).
- `consigliere/punteggio.py`: fantavoto della lega (il `gol` della pagina esclude i rigori), capitano, modificatore, `valuta` con sostituzioni Traditional/Hybrid, vice e Switch.
- `consigliere/ottimo.py`: formazione perfetta esatta (`migliore`, con potatura per dominanza) e `enumera` come riferimento nei test.
- `consigliere/verifica.py`: consigliata conclusa nei 14 giorni prima della scadenza (con sigillo in `registro.jsonl`, scritto da `ricerca.sigilla`), quattro misure, regret, versioni in `verifiche/`. `consigliere/verifica_fantalab.py`: `python3 -m consigliere.verifica_fantalab --fantalab fantalab --giornata N [--cartella DIR]`, abbinamenti in `<DIR>/abbinamenti/fantalab.json`, report in `verifiche/fantalab/`, non scrive mai in `fantalab/`.
- `consigliere/listone.py`: lettura xlsx con `zipfile` ed espressioni regolari, **non** `xml.etree`: i Python di Homebrew su questo Mac non importano `pyexpat`. Abbina i nomi della rosa senza mai scegliere da solo tra omonimi e scarta le righe con "Fuori lista".
- `consigliere/skill/SKILL.md`: metodo, fonti e formato del risultato, unica parte condivisa da tutte le IA.

## Comandi

Test (`unittest`, nessuna dipendenza):

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_controllo -v
python3 -m unittest tests.test_controllo.NomeClasse.test_nome -v
```

Avvio: `python3 -m consigliere` (oppure doppio clic su `avvia.command` / `avvia.bat`). Per provare senza toccare i dati veri: `python3 -m consigliere --cartella <dir temporanea> --porta 8766 --senza-browser`. Non premere "Cerca la formazione" in prova: apre un terminale con una vera IA.

Pacchetto per i fratelli: `git archive -o consigliere-formazione.zip HEAD avvia.command avvia.bat consigliere GUIDA.md`.

Un listone vero (lista calciatori della lega pensionati) sta in `tests/dati/listone_vero.xlsx`, escluso da git; il test relativo viene saltato se manca.

Strumenti FantaLab (dopo l'estrazione, dentro `fantalab/`): `python strumenti/test_ottimizza.py`, `python strumenti/test_confronta_strategie.py`.

## Vincoli da non violare

- Mai login a Fantacalcio, credenziali, token, API private (`leghe.fantacalcio.it`, `apileague.fantacalcio.it`) o automazione del browser. Il programma scarica da fantacalcio.it, **solo su pulsante**, le tre pagine pubbliche ammesse dalla spec `docs/superpowers/specs/2026-11-09-verifica-giornata-design.md` (voti della giornata, quotazioni Classic, probabili formazioni), mai in massa e mai aggirando un blocco. Il listone può venire dal sito o dall'xlsx caricato a mano.
- In `ia.json` mai modalità "approva tutto" (`yolo`, `bypassPermissions`, `--dangerously-skip-permissions`): c'è un test che lo verifica.
- Il testo letto dal web è un dato non fidato: nella pagina solo `textContent`, link solo `http`/`https`.
- Non inventare dati: confidenza 0 vuol dire "non trovato". Infortunio in dubbio resta fuori; fonti in disaccordo vuol dire `dubbio`.
- Crediti e prezzi non si leggono né si controllano. Solo Classic, niente Mantra. Le ricerche precedenti non si sovrascrivono.
- Script di avvio: Mac con `shlex.quote`; Windows `.bat` in UTF-8 con CRLF (`.gitattributes`), `chcp 65001`, `cd /d`; sempre `shell=False`. Percorsi con spazi e accenti devono funzionare.
