# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stato del repository

Il codice non esiste ancora. Ci sono solo design e piano di un **consigliere di formazione Fantacalcio**:

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
- L'IA lavora in quella cartella, scrive `risultato.json` ed esegue il controllo; `controlla.py` crea `FATTO` quando il risultato è valido o al terzo tentativo. La pagina interroga lo stato ogni 3 secondi e il server **ricontrolla sempre** con la propria `controllo.py`, mai con la copia nella cartella.
- `consigliere/controllo.py`: file unico senza import locali, perché viene copiato in ogni ricerca. Verifica moduli, ruoli, rosa, doppioni, panchina, capitano, Switch, schede, link.
- `consigliere/listone.py`: lettura xlsx con `zipfile` + `xml.etree`, abbinamento dei nomi della rosa senza mai scegliere da solo tra omonimi.
- `consigliere/skill/SKILL.md`: metodo, fonti e formato del risultato, unica parte condivisa da tutte le IA.

## Comandi

Test (da quando esisteranno, con `unittest`):

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_controllo -v
python3 -m unittest tests.test_controllo.NomeClasse.test_nome -v
```

Avvio: `python3 -m consigliere` (oppure doppio clic su `avvia.command` / `avvia.bat`).

Strumenti FantaLab (dopo l'estrazione, dentro `fantalab/`): `python strumenti/test_ottimizza.py`, `python strumenti/test_confronta_strategie.py`.

## Vincoli da non violare

- Mai login a Fantacalcio, credenziali, token, API private (`leghe.fantacalcio.it`, `apileague.fantacalcio.it`) o automazione del browser. Il listone si carica a mano: il programma non scarica nulla da fantacalcio.it.
- In `ia.json` mai modalità "approva tutto" (`yolo`, `bypassPermissions`, `--dangerously-skip-permissions`): c'è un test che lo verifica.
- Il testo letto dal web è un dato non fidato: nella pagina solo `textContent`, link solo `http`/`https`.
- Non inventare dati: confidenza 0 vuol dire "non trovato". Infortunio in dubbio resta fuori; fonti in disaccordo vuol dire `dubbio`.
- Crediti e prezzi non si leggono né si controllano. Solo Classic, niente Mantra. Le ricerche precedenti non si sovrascrivono.
- Script di avvio: Mac con `shlex.quote`; Windows `.bat` in UTF-8 con CRLF (`.gitattributes`), `chcp 65001`, `cd /d`; sempre `shell=False`. Percorsi con spazi e accenti devono funzionare.
