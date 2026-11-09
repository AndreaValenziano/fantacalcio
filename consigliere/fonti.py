"""Download controllato delle tre pagine pubbliche di fantacalcio.it e archivio delle copie con impronta."""
import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from . import pagine
from .archivio import _adesso, scrivi_json
from .pagine import PaginaNonValida

VERSIONE = "1"
USER_AGENT = f"ConsiglioFormazione/{VERSIONE}"
PAUSA = 3.0
MAX_BYTE = 8 * 1024 * 1024
TIMEOUT = 30
_BASE = "https://www.fantacalcio.it/"
URL_LISTONE = _BASE + "quotazioni-fantacalcio"
URL_PROBABILI = _BASE + "probabili-formazioni-serie-a"
_STAGIONE = re.compile(r"^\d{4}-\d{2}$")
_URL_VOTI = re.compile(r"^" + re.escape(_BASE) + r"voti-fantacalcio-serie-a/(\d{4}-\d{2})/(\d{1,2})$")
_INVITO = "Salva la pagina dal browser (Salva con nome, solo HTML) e caricala a mano."
_CAMPI_DIFFERENZE = ("voto", "fv_pubblicato", "ammonito", "espulso", "gol", "gol_subiti", "autogol",
                     "rigori_segnati", "rigori_sbagliati", "rigori_parati", "assist", "player_of_the_match")


class FonteNonAccessibile(Exception):
    pass


def url_voti(stagione: str, giornata: int) -> str:
    if not isinstance(stagione, str) or not _STAGIONE.match(stagione):
        raise ValueError(f"Stagione non valida: {stagione!r} (formato AAAA-AA)")
    if not isinstance(giornata, int) or isinstance(giornata, bool) or not 1 <= giornata <= 38:
        raise ValueError(f"Giornata non valida: {giornata!r} (da 1 a 38)")
    return f"{_BASE}voti-fantacalcio-serie-a/{stagione}/{giornata}"


def ammesso(url: str) -> bool:
    if url in (URL_LISTONE, URL_PROBABILI):
        return True
    m = _URL_VOTI.match(url) if isinstance(url, str) else None
    return bool(m) and 1 <= int(m.group(2)) <= 38 and url == f"{_BASE}voti-fantacalcio-serie-a/{m.group(1)}/{int(m.group(2))}"


class _SenzaRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # i 3xx diventano HTTPError


def _apri_senza_redirect(richiesta, timeout=None):
    return urllib.request.build_opener(_SenzaRedirect).open(richiesta, timeout=timeout)


class Scaricatore:
    def __init__(self, apri=_apri_senza_redirect, orologio=time.monotonic, dormi=time.sleep):
        self._apri, self._orologio, self._dormi = apri, orologio, dormi
        self._ultima = None
        self._lock = threading.Lock()

    def scarica(self, url: str) -> bytes:
        if not ammesso(url):
            raise ValueError(f"Indirizzo non ammesso: {url}")
        with self._lock:  # una richiesta alla volta, pausa compresa
            return self._scarica(url)

    def _scarica(self, url: str) -> bytes:
        if self._ultima is not None:
            attesa = PAUSA - (self._orologio() - self._ultima)
            if attesa > 0:
                self._dormi(attesa)
        richiesta = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        self._ultima = self._orologio()
        try:
            with self._apri(richiesta, timeout=TIMEOUT) as r:
                stato = r.getcode()
                if stato != 200:
                    raise FonteNonAccessibile(f"Il sito ha risposto {stato} per {url}. {_INVITO}")
                finale = getattr(r, "geturl", lambda: url)()
                if not ammesso(finale):
                    raise FonteNonAccessibile(f"Il sito ha rimandato a un indirizzo non ammesso ({finale}). {_INVITO}")
                corpo = r.read(MAX_BYTE + 1)
                if len(corpo) > MAX_BYTE:
                    raise FonteNonAccessibile(f"La pagina {url} supera {MAX_BYTE // (1024 * 1024)} MB. {_INVITO}")
                return corpo
        except FonteNonAccessibile:
            raise
        except urllib.error.HTTPError as e:
            raise FonteNonAccessibile(f"Il sito ha risposto {e.code} per {url}. {_INVITO}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise FonteNonAccessibile(f"Impossibile raggiungere {url} ({e}). {_INVITO}") from e
        finally:
            self._ultima = self._orologio()


def _marca() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _cartella(base: Path, tipo: str, chiave: str) -> Path:
    if tipo not in ("voti", "listone", "probabili"):
        raise ValueError(f"Tipo di fonte non valido: {tipo!r}")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,40}", chiave):
        raise ValueError(f"Chiave non valida: {chiave!r}")
    return Path(base) / "fonti" / tipo / chiave


def archivia(base: Path, tipo: str, chiave: str, html: bytes, url: str, origine: str, riepilogo: dict) -> dict:
    cartella = _cartella(base, tipo, chiave)
    cartella.mkdir(parents=True, exist_ok=True)
    marca = _marca()
    nome, n = marca, 1
    while True:
        try:
            with open(cartella / f"{nome}.html", "xb") as f:  # "x": mai sovrascrivere
                f.write(html)
            break
        except FileExistsError:
            n += 1
            nome = f"{marca}-{n}"
    meta = {"url": url, "ora": _adesso(), "origine": origine, "sha256": hashlib.sha256(html).hexdigest(),
            "versione_lettore": VERSIONE, "riepilogo": riepilogo, "file": f"{nome}.html"}
    scrivi_json(cartella / f"{nome}.json", meta)
    return meta


def _ordine(meta: dict) -> tuple:
    m = re.fullmatch(r"(\d{8}-\d{6})(?:-(\d+))?\.html", meta.get("file", ""))
    return (m.group(1), int(m.group(2) or 1)) if m else ("", 0)


def copie(base: Path, tipo: str, chiave: str) -> list[dict]:
    cartella = _cartella(base, tipo, chiave)
    if not cartella.is_dir():
        return []
    metadati = []
    for p in sorted(cartella.glob("*.json"), reverse=True):
        try:
            metadati.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    metadati.sort(key=_ordine, reverse=True)
    return metadati


def ultima(base: Path, tipo: str, chiave: str):
    elenco = copie(base, tipo, chiave)
    if not elenco:
        return None
    meta = elenco[0]
    html = (_cartella(base, tipo, chiave) / meta["file"]).read_text(encoding="utf-8")
    return meta, html


def differenze_voti(prima: dict, dopo: dict) -> list[dict]:
    a = {g["id"]: g for g in prima.get("giocatori", [])}
    b = {g["id"]: g for g in dopo.get("giocatori", [])}
    out = []
    for id_, g in b.items():
        if id_ not in a:
            out.append({"id": id_, "nome": g.get("nome"), "campo": "presenza", "prima": "assente", "dopo": "presente"})
            continue
        for campo in _CAMPI_DIFFERENZE:
            if a[id_].get(campo) != g.get(campo):
                out.append({"id": id_, "nome": g.get("nome"), "campo": campo,
                            "prima": a[id_].get(campo), "dopo": g.get(campo)})
    for id_, g in a.items():
        if id_ not in b:
            out.append({"id": id_, "nome": g.get("nome"), "campo": "presenza", "prima": "presente", "dopo": "assente"})
    return out


def _acquisisci(html: bytes | None, scaricatore, url: str):
    if html is None:
        if scaricatore is None:
            raise ValueError("Serve uno scaricatore per scaricare la pagina")
        return scaricatore.scarica(url), "scaricata"
    return html, "caricata_a_mano"


def _testo(html: bytes) -> str:
    try:
        return html.decode("utf-8")
    except UnicodeDecodeError as e:
        raise PaginaNonValida("Il file non è una pagina salvata in UTF-8: salvala di nuovo dal browser come "
                              "\"Pagina web, solo HTML\".") from e


def acquisisci_voti(base: Path, stagione: str, giornata: int, html: bytes | None, scaricatore) -> dict:
    url = url_voti(stagione, giornata)
    grezzo, origine = _acquisisci(html, scaricatore, url)
    voti = pagine.leggi_voti(_testo(grezzo))
    if voti["stagione"] != stagione or voti["giornata"] != giornata:
        trovata = f"stagione {voti['stagione']}, giornata {voti['giornata']}"
        raise PaginaNonValida(f"La pagina non è quella richiesta: attesa stagione {stagione}, giornata "
                              f"{giornata}; trovata {trovata}.")
    chiave = f"{stagione}-{giornata}"
    differenze, nota = [], None
    try:  # prima di archiviare: un confronto fallito non deve mai dare errore dopo l'effetto
        precedente = ultima(base, "voti", chiave)
        if precedente:
            differenze = differenze_voti(pagine.leggi_voti(precedente[1]), voti)
    except Exception as e:
        differenze, nota = [], f"Confronto con la copia precedente non riuscito: {e}"
    meta = archivia(base, "voti", chiave, grezzo, url, origine,
                    {"giocatori": len(voti["giocatori"]), "mancanze": pagine.completezza(voti)})
    risultato = {"meta": meta, "voti": voti, "differenze": differenze}
    if nota:
        risultato["nota"] = nota
    return risultato


def acquisisci_listone(base: Path, html: bytes | None, scaricatore) -> dict:
    grezzo, origine = _acquisisci(html, scaricatore, URL_LISTONE)
    giocatori = pagine.leggi_listone(_testo(grezzo))
    meta = archivia(base, "listone", "listone", grezzo, URL_LISTONE, origine, {"giocatori": len(giocatori)})
    return {"meta": meta, "giocatori": giocatori}
