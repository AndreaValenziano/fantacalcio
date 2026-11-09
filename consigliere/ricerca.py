"""Cartella di ricerca, script del terminale e stato della ricerca."""
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

from consigliere.archivio import controlla_id, scrivi_json
from consigliere.controllo import chiave, controlla

QUI = Path(__file__).parent
PROMPT = "Leggi il file SKILL.md in questa cartella e segui le istruzioni per la richiesta in richiesta.json."
ID_RICERCA = re.compile(r"^\d{8}-\d{6}(-\d+)?$")
_BLOCCO_REGISTRO = threading.Lock()


def carica_ia() -> list[dict]:
    voci = json.loads((QUI / "ia.json").read_text(encoding="utf-8"))
    for v in voci:
        v["disponibile"] = shutil.which(v["comando"]) is not None
    return voci


def controlla_id_ricerca(id_: str) -> str:
    if not isinstance(id_, str) or not ID_RICERCA.match(id_):
        raise ValueError(f"Identificativo di ricerca non valido: {id_!r}")
    return id_


def cartella_lega(base: Path, lega_id: str) -> Path:
    return Path(base) / "ricerche" / controlla_id(lega_id)


def _listone_della_lega(lega: dict, giocatori: list[dict]) -> list[dict]:
    ruoli = lega.get("ruoli") or {}
    return [dict(g, ruolo=ruoli.get(chiave(g["nome"], g["squadra"]), g["ruolo"])) for g in giocatori]


def crea_ricerca(base: Path, lega: dict, giocatori: list[dict], ia: dict, stile: str, ora: datetime) -> Path:
    radice = cartella_lega(base, lega["id"])
    radice.mkdir(parents=True, exist_ok=True)
    nome, n = ora.strftime("%Y%m%d-%H%M%S"), 2
    cartella = radice / nome
    while True:
        try:
            cartella.mkdir()
            break
        except FileExistsError:
            cartella, n = radice / f"{nome}-{n}", n + 1
    python = sys.executable
    shutil.copyfile(QUI / "skill" / "SKILL.md", cartella / "SKILL.md")
    shutil.copyfile(QUI / "controllo.py", cartella / "controlla.py")
    richiesta = {
        "lega": lega, "listone": _listone_della_lega(lega, giocatori), "stile": stile, "ia": ia["id"],
        "creata_il": ora.isoformat(timespec="seconds"),
        "comando_controllo": f'"{python}" controlla.py richiesta.json risultato.json'}
    # La copia del programma sta fuori dalla cartella in cui lavora l'IA, che non può modificarla.
    scrivi_json(_copia_richiesta(cartella), richiesta)
    scrivi_json(cartella / "richiesta.json", richiesta)
    scrivi_script(cartella, ia, python, sys.platform)
    return cartella


def _comando(ia: dict, python: str) -> list[str]:
    controllo = f'"{python}" controlla.py richiesta.json risultato.json'
    eseguibile = shutil.which(ia["comando"]) or ia["comando"]
    return [eseguibile] + [a.replace("{prompt}", PROMPT).replace("{controllo}", controllo) for a in ia["argomenti"]]


def scrivi_script(cartella: Path, ia: dict, python: str, sistema: str) -> Path:
    comando = _comando(ia, python)
    if sistema == "win32":
        def q(a):
            return '"' + a.replace('"', '""').replace("%", "%%") + '"'
        righe = ["@echo off", "chcp 65001 >nul", f'cd /d "{cartella}"',
                 "call " + " ".join(q(a) for a in comando),
                 "echo.", "echo Ricerca terminata: torna alla pagina del consigliere.", "pause"]
        s = cartella / "avvia.bat"
        s.write_bytes(("\r\n".join(righe) + "\r\n").encode("utf-8"))
        return s
    righe = ["#!/bin/bash", f"cd {shlex.quote(str(cartella))} || exit 1",
             " ".join(shlex.quote(a) for a in comando),
             "echo", "echo 'Ricerca terminata: torna alla pagina del consigliere. Puoi chiudere questa finestra.'"]
    s = cartella / "avvia.command"
    s.write_text("\n".join(righe) + "\n", encoding="utf-8")
    s.chmod(0o755)
    return s


def avvia_terminale(script: Path, sistema: str) -> None:
    if sistema == "darwin":
        subprocess.Popen(["open", "-a", "Terminal", str(script)], shell=False)
    elif sistema == "win32":
        subprocess.Popen(["cmd", "/c", "start", "", str(script)], shell=False)
    else:
        terminale = shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal")
        if not terminale:
            raise RuntimeError("Non trovo un terminale da aprire su questo sistema.")
        subprocess.Popen([terminale, "--", "bash", str(script)], shell=False)


def _copia_richiesta(cartella: Path) -> Path:
    return cartella.parent / f"{cartella.name}.richiesta.json"


def esiste_ricerca(cartella: Path) -> bool:
    return cartella.is_dir() and _copia_richiesta(cartella).exists()


def chiudi_ricerca(cartella: Path) -> None:
    (Path(cartella) / "CHIUSA").write_text("chiusa dalla pagina", encoding="utf-8")


def _finita(cartella: Path) -> bool:
    return (cartella / "FATTO").exists() or (cartella / "CHIUSA").exists()


def _scadenza(risultato: dict, lega: dict) -> str | None:
    try:
        prima = datetime.fromisoformat(risultato["prima_partita"])
    except (KeyError, TypeError, ValueError):
        return None
    return (prima - timedelta(minutes=lega.get("anticipo_minuti") or 0)).isoformat(timespec="seconds")


def _stato(cartella: Path) -> dict:
    """Stato della ricerca senza effetti sul disco."""
    cartella = Path(cartella)
    richiesta = json.loads(_copia_richiesta(cartella).read_text(encoding="utf-8"))
    s = {"id": cartella.name, "stato": "in_corso", "avviata_il": richiesta.get("creata_il"),
         "ia": richiesta.get("ia"), "stile": richiesta.get("stile"), "errori": [], "risultato": None, "scadenza": None}
    if not _finita(cartella):
        return s
    p = cartella / "risultato.json"
    try:
        risultato = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return s | {"stato": "errore", "errori": ["L'IA non ha scritto il risultato (risultato.json mancante)."]}
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return s | {"stato": "errore", "errori": [f"Il risultato è incompleto o illeggibile: {e}"]}
    errori = controlla(richiesta, risultato)
    if errori:
        return s | {"stato": "errore", "errori": errori}
    return s | {"stato": "pronto", "risultato": risultato, "scadenza": _scadenza(risultato, richiesta["lega"])}


def stato_ricerca(cartella: Path) -> dict:
    s = _stato(cartella)
    if s["stato"] == "pronto":
        sigilla(Path(cartella))
    return s


def _registro(base: Path) -> Path:
    return Path(base) / "registro.jsonl"


def _righe_registro(base: Path) -> list[dict]:
    try:
        testo = _registro(base).read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    righe = []
    for x in testo.splitlines():
        try:
            r = json.loads(x)
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict):
            righe.append(r)
    return righe


def sigillo(base: Path, lega_id: str, rid: str) -> dict | None:
    return next((r for r in _righe_registro(base) if r.get("ricerca") == rid and r.get("lega") == lega_id), None)


def impronta(percorso: Path) -> str:
    return hashlib.sha256(Path(percorso).read_bytes()).hexdigest()


def fatto_il(cartella: Path) -> str | None:
    """Quando la ricerca si è conclusa, ISO con fuso: il più tardi tra FATTO (o CHIUSA) e risultato.json.

    Un risultato scritto dopo FATTO o CHIUSA conta dal momento in cui è stato scritto.
    """
    cartella = Path(cartella)
    for nome in ("FATTO", "CHIUSA"):
        try:
            t = (cartella / nome).stat().st_mtime
        except FileNotFoundError:
            continue
        try:
            t = max(t, (cartella / "risultato.json").stat().st_mtime)
        except FileNotFoundError:
            pass
        return datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")
    return None


def sigilla(cartella: Path) -> dict:
    """Aggiunge al registro (solo in coda) l'impronta di una ricerca conclusa, una volta sola."""
    cartella = Path(cartella)
    base, lega_id, rid = cartella.parents[2], cartella.parent.name, cartella.name
    with _BLOCCO_REGISTRO:  # due interrogazioni contemporanee non scrivono due righe
        esistente = sigillo(base, lega_id, rid)
        if esistente is not None:
            return esistente
        return _aggiungi_sigillo(cartella, base, lega_id, rid)


def _aggiungi_sigillo(cartella: Path, base: Path, lega_id: str, rid: str) -> dict:
    riga = {"ricerca": rid, "lega": lega_id, "fatto_il": fatto_il(cartella),
            "sigillato_il": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sha256_risultato": impronta(cartella / "risultato.json"),
            "sha256_richiesta": impronta(_copia_richiesta(cartella))}
    with open(_registro(base), "a+b") as f:  # "a": solo in coda, le righe precedenti restano intatte
        f.seek(0, os.SEEK_END)
        a_capo = b""
        if f.tell():
            f.seek(-1, os.SEEK_END)
            a_capo = b"" if f.read(1) == b"\n" else b"\n"  # riga precedente troncata: non la si fonde
        f.write(a_capo + (json.dumps(riga, ensure_ascii=False) + "\n").encode("utf-8"))
    return riga


def _cartelle(base: Path, lega_id: str) -> list[Path]:
    radice = cartella_lega(base, lega_id)
    if not radice.exists():
        return []
    return sorted((c for c in radice.iterdir() if ID_RICERCA.match(c.name) and esiste_ricerca(c)),
                  key=lambda c: c.name, reverse=True)


def ricerca_in_corso(base: Path, lega_id: str) -> Path | None:
    return next((c for c in _cartelle(base, lega_id) if not _finita(c)), None)


def elenco_ricerche(base: Path, lega_id: str) -> list[dict]:
    out = []
    for c in _cartelle(base, lega_id):
        s = stato_ricerca(c)
        out.append({k: s[k] for k in ("id", "stato", "avviata_il", "ia", "stile", "scadenza")})
    return out
