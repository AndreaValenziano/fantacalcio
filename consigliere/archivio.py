"""Leghe, listone e avviso salvati su disco come JSON, con scritture atomiche."""
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

MODELLI = Path(__file__).parent / "modelli"
ID_VALIDO = re.compile(r"^[a-z0-9-]{1,40}$")
VERSIONE_AVVISO = 2  # 2: l'avviso copre anche il download delle pagine di fantacalcio.it
CAMPI_OBBLIGATORI = ("moduli", "panchina", "sostituzioni", "switch", "capitano", "modificatore_difesa", "bonus")


class ArchivioDanneggiato(Exception):
    def __init__(self, percorso):
        super().__init__(f"File danneggiato: {percorso}")
        self.percorso = str(percorso)


def campi_mancanti(lega: dict) -> list[str]:
    return [c for c in CAMPI_OBBLIGATORI if lega.get(c) is None]


def controlla_id(id_: str) -> str:
    if not isinstance(id_, str) or not ID_VALIDO.match(id_):
        raise ValueError(f"Identificativo non valido: {id_!r}")
    return id_


def _slug(nome: str) -> str:
    t = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:36].strip("-")
    return t or "lega"


def scrivi_json(percorso: Path, dati) -> None:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=percorso.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=1)
        os.replace(tmp, percorso)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def leggi_json(percorso: Path):
    try:
        return json.loads(percorso.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ArchivioDanneggiato(percorso) from e


class Archivio:
    def __init__(self, base: Path):
        self.base = Path(base)
        self.cartella_leghe = self.base / "leghe"

    def _percorso_lega(self, id_: str) -> Path:
        return self.cartella_leghe / f"{controlla_id(id_)}.json"

    def leghe(self) -> list[dict]:
        if not self.cartella_leghe.exists():
            return []
        return [leggi_json(p) for p in sorted(self.cartella_leghe.glob("*.json"))]

    def lega(self, id_: str) -> dict:
        p = self._percorso_lega(id_)
        if not p.exists():
            raise KeyError(id_)
        return leggi_json(p)

    def salva_lega(self, lega: dict) -> None:
        scrivi_json(self._percorso_lega(lega["id"]), lega)

    def modelli(self) -> list[dict]:
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(MODELLI.glob("*.json"))]

    def crea_da_modello(self, modello: str, nome: str) -> dict:
        p = MODELLI / f"{controlla_id(modello)}.json"
        if not p.exists():
            raise KeyError(modello)
        lega = json.loads(p.read_text(encoding="utf-8"))
        base = _slug(nome)
        id_, n = base, 2
        while self._percorso_lega(id_).exists():
            id_, n = f"{base}-{n}", n + 1
        lega.update(id=id_, nome=nome.strip() or lega["nome"], modello=modello)
        self.salva_lega(lega)
        return lega

    def avviso_accettato(self) -> bool:
        p = self.base / "avviso.json"
        if not p.exists():
            return False
        dati = leggi_json(p)
        v = dati.get("versione") if isinstance(dati, dict) else None
        return isinstance(v, int) and not isinstance(v, bool) and v >= VERSIONE_AVVISO

    def accetta_avviso(self) -> None:
        scrivi_json(self.base / "avviso.json", {"accettato_il": _adesso(), "versione": VERSIONE_AVVISO})

    def listone(self) -> dict | None:
        p = self.base / "listone.json"
        return leggi_json(p) if p.exists() else None

    def salva_listone(self, giocatori: list[dict], origine: str = "xlsx") -> None:
        scrivi_json(self.base / "listone.json", {"importato_il": _adesso(), "origine": origine, "giocatori": giocatori})


def _adesso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
