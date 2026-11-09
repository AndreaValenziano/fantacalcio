"""Lettura del listone (.xlsx) e abbinamento dei nomi della rosa.

L'XML dell'xlsx si legge con espressioni regolari e non con xml.etree: i Python
di Homebrew su macOS recenti hanno pyexpat rotto, e xml.etree non si importa.
"""
import html
import io
import posixpath
import re
import zipfile

from consigliere.controllo import _norm, chiave

ALIAS = {"ruolo": {"r", "ruolo"}, "nome": {"nome", "calciatore"}, "squadra": {"squadra", "sq"},
         "fuori": {"fuori lista"}}
RUOLI = {"P", "D", "C", "A"}
RUOLO_DAVANTI = re.compile(r"^[PDCA]\s*[-–:.]?\s+(?=\S)", re.IGNORECASE)
ATTRIBUTO = re.compile(r'([\w:]+)\s*=\s*"([^"]*)"')
TESTO = re.compile(r"<(?:\w+:)?t\b[^>]*>(.*?)</(?:\w+:)?t>", re.S)
RIGA = re.compile(r"<(?:\w+:)?row\b[^>]*?(?:/>|>(.*?)</(?:\w+:)?row>)", re.S)
CELLA = re.compile(r"<(?:\w+:)?c\b([^>]*?)(?:/>|>(.*?)</(?:\w+:)?c>)", re.S)
VALORE = re.compile(r"<(?:\w+:)?v\b[^>]*>(.*?)</(?:\w+:)?v>", re.S)


class ListoneNonValido(Exception):
    pass


def _attributi(testo: str) -> dict:
    return {k: html.unescape(v) for k, v in ATTRIBUTO.findall(testo)}


def _testo(xml: str) -> str:
    return html.unescape("".join(TESTO.findall(xml)))


def _colonna(rif: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", rif).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def _fogli(z: zipfile.ZipFile):
    wb = z.read("xl/workbook.xml").decode("utf-8")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    target = {a.get("Id"): a.get("Target") for a in map(_attributi, re.findall(r"<(?:\w+:)?Relationship\b([^>]*)>", rels))}
    condivise = []
    if "xl/sharedStrings.xml" in z.namelist():
        sst = z.read("xl/sharedStrings.xml").decode("utf-8")
        condivise = [_testo(si) for si in re.findall(r"<(?:\w+:)?si\b[^>]*>(.*?)</(?:\w+:)?si>", sst, re.S)]
    for attr in re.findall(r"<(?:\w+:)?sheet\b([^>]*)>", wb):
        coppie = dict(ATTRIBUTO.findall(attr))
        rid = next(v for k, v in coppie.items() if k.endswith(":id"))
        t = target[rid].lstrip("/")
        percorso = t if t.startswith("xl/") else posixpath.normpath(posixpath.join("xl", t))
        yield html.unescape(coppie.get("name", "")), percorso, condivise


def _righe(xml: bytes, condivise):
    for corpo in RIGA.findall(xml.decode("utf-8")):
        celle = {}
        for i, (attr, interno) in enumerate(CELLA.findall(corpo or "")):
            a = dict(ATTRIBUTO.findall(attr))
            col = _colonna(a["r"]) if a.get("r") else i
            tipo, v = a.get("t"), VALORE.search(interno or "")
            if tipo == "s" and v:
                val = condivise[int(v.group(1))]
            elif tipo == "inlineStr":
                val = _testo(interno)
            else:
                val = html.unescape(v.group(1)) if v else ""
            celle[col] = str(val).strip()
        yield [celle.get(i, "") for i in range(max(celle) + 1)] if celle else []


def _intestazione(riga):
    nomi = [_norm(x) for x in riga]
    pos = {}
    for campo, alias in ALIAS.items():
        for i, n in enumerate(nomi):
            if n in alias:
                pos[campo] = i
                break
    return pos if {"ruolo", "nome", "squadra"} <= pos.keys() else None


def leggi_xlsx(dati: bytes) -> list[dict]:
    try:
        z = zipfile.ZipFile(io.BytesIO(dati))
        fogli = list(_fogli(z))
    except (zipfile.BadZipFile, KeyError, StopIteration, UnicodeDecodeError) as e:
        raise ListoneNonValido("Il file non è un Excel .xlsx valido: scarica di nuovo il listone.") from e
    fogli.sort(key=lambda f: "classic" not in f[0].lower())
    for _, percorso, condivise in fogli:
        try:
            righe = _righe(z.read(percorso), condivise)
            pos = None
            giocatori = []
            for riga in righe:
                if pos is None:
                    pos = _intestazione(riga)
                    continue
                valore = lambda campo: riga[pos[campo]] if pos.get(campo, 99999) < len(riga) else ""
                ruolo, nome, squadra = valore("ruolo").upper(), valore("nome"), valore("squadra")
                if ruolo in RUOLI and nome and squadra and not valore("fuori"):
                    giocatori.append({"nome": nome, "squadra": squadra, "ruolo": ruolo})
        except (KeyError, IndexError, ValueError, UnicodeDecodeError) as e:
            raise ListoneNonValido("Il file Excel è danneggiato o in un formato inatteso.") from e
        if pos is not None and giocatori:
            return giocatori
    raise ListoneNonValido("Non trovo le colonne Ruolo, Nome e Squadra con giocatori Classic: è il listone giusto?")


def _compatto(t: str) -> str:
    return _norm(t).replace(" ", "")


def _candidati(testo: str, giocatori):
    esatti = [g for g in giocatori if _compatto(g["nome"]) == _compatto(testo)]
    if esatti:
        return esatti
    parole = _norm(testo).split()
    return [g for g in giocatori if parole and _norm(g["nome"]).split()[:len(parole)] == parole]


def _squadra_coincide(token: str, squadra: str) -> bool:
    s, t = _compatto(squadra), _compatto(token)
    return len(t) >= 3 and s.startswith(t)


def abbina(testo: str, giocatori: list[dict]) -> dict:
    esito = {"trovati": [], "ambigui": [], "non_trovati": []}
    for riga in testo.splitlines():
        riga = RUOLO_DAVANTI.sub("", riga.strip()).strip()
        if not riga:
            continue
        candidati = None
        parole = riga.split()
        if len(parole) > 1:
            nome, squadra = " ".join(parole[:-1]), parole[-1]
            nella_squadra = [g for g in _candidati(nome, giocatori) if _squadra_coincide(squadra, g["squadra"])]
            if nella_squadra:
                candidati = nella_squadra
        if candidati is None:
            candidati = _candidati(riga, giocatori)
        if len(candidati) == 1:
            esito["trovati"].append(candidati[0])
        elif candidati:
            esito["ambigui"].append({"testo": riga, "opzioni": candidati})
        else:
            esito["non_trovati"].append(riga)
    return esito


def verifica_rosa(rosa: list[dict], giocatori: list[dict]) -> list[dict]:
    chiavi = {chiave(g["nome"], g["squadra"]) for g in giocatori}
    problemi = []
    for r in rosa:
        if chiave(r["nome"], r["squadra"]) in chiavi:
            continue
        omonimi = [g for g in giocatori if _compatto(g["nome"]) == _compatto(r["nome"])]
        if len(omonimi) == 1:
            problemi.append({"nome": r["nome"], "squadra": r["squadra"], "problema": "cambio_squadra",
                             "nuova_squadra": omonimi[0]["squadra"]})
        else:
            problemi.append({"nome": r["nome"], "squadra": r["squadra"], "problema": "non_trovato", "nuova_squadra": None})
    return problemi
