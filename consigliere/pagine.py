"""Lettura delle pagine pubbliche di fantacalcio.it: voti della giornata e listone Classic.

Solo libreria standard (html.parser). Il testo letto dal web è un dato non fidato:
qui viene solo interpretato, mai eseguito. I prezzi del listone non si leggono.
"""
import re
from datetime import date, timedelta
from html.parser import HTMLParser

SQUADRE_ATTESE = 20
GIOCATORI_MINIMI_SQUADRA = 11

_EVENTI = {
    "gol segnati": "gol",
    "gol subiti": "gol_subiti",
    "autoreti": "autogol",
    "autorete": "autogol",
    "rigori segnati": "rigori_segnati",
    "rigori sbagliati": "rigori_sbagliati",
    "rigori parati": "rigori_parati",
    "assist": "assist",
    "assists": "assist",
    "player of the match": "player_of_the_match",
}
_RUOLI = {"p": "P", "d": "D", "c": "C", "a": "A"}
_RE_GIOCATORE = re.compile(r"/serie-a/squadre/([^/?#]+)/[^/?#]+/(\d+)")
_RE_SQUADRA = re.compile(r"/serie-a/squadre/([^/?#]+)/?$")
_RE_DATA = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{1,2}):(\d{2})\s*$")


class PaginaNonValida(Exception):
    """La pagina non ha la struttura attesa (non è quella giusta, o il sito è cambiato)."""


def squadra_da_slug(slug: str) -> str:
    """`hellas-verona` -> `Hellas Verona`."""
    return " ".join(p.capitalize() for p in slug.split("-") if p)


def _ultima_domenica(anno: int, mese: int) -> date:
    giorno = date(anno + (mese == 12), mese % 12 + 1, 1) - timedelta(days=1)
    return giorno - timedelta(days=(giorno.weekday() + 1) % 7)


def ora_italiana(gg_mm_aaaa_hh_mm: str) -> str:
    """`08/11/2026 - 15:00` -> `2026-11-08T15:00:00+01:00`.

    Ora legale (+02:00) dall'ultima domenica di marzo (02:00 locali) all'ultima di
    ottobre (03:00 locali). Niente `zoneinfo`: su Windows il database dei fusi manca.
    """
    m = _RE_DATA.match(gg_mm_aaaa_hh_mm or "")
    if not m:
        raise ValueError(f"data non riconosciuta: {gg_mm_aaaa_hh_mm!r}")
    giorno, mese, anno, ore, minuti = (int(x) for x in m.groups())
    d = date(anno, mese, giorno)  # ValueError se impossibile
    minuto_del_giorno = ore * 60 + minuti
    inizio, fine = _ultima_domenica(anno, 3), _ultima_domenica(anno, 10)
    if inizio < d < fine:
        legale = True
    elif d == inizio:
        legale = minuto_del_giorno >= 2 * 60
    elif d == fine:
        legale = minuto_del_giorno < 3 * 60
    else:
        legale = False
    return f"{anno:04d}-{mese:02d}-{giorno:02d}T{ore:02d}:{minuti:02d}:00{'+02:00' if legale else '+01:00'}"


def _numero(valore: str | None) -> float | None:
    """Voto con virgola; `55` (e ciò che non è un numero) vuol dire senza voto."""
    if valore is None:
        return None
    try:
        n = float(valore.strip().replace(",", "."))
    except ValueError:
        return None
    return None if n == 55 else n


def _intero(valore: str | None) -> int:
    try:
        return int(float((valore or "0").strip().replace(",", ".")))
    except ValueError:
        return 0


def _classi(attrs: dict) -> list[str]:
    return (attrs.get("class") or "").split()


class _LettoreVoti(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titolo = ""
        self._in_titolo = False
        self.squadre: dict[str, dict] = {}
        self.giocatori: list[dict] = []
        self.tabelle = 0
        self.righe_incomplete: list[str] = []
        self._in_li_squadra = False
        self._data_testo: str | None = None   # testo del match-date in corso
        self._data_squadra: str | None = None  # data letta, in attesa della tabella
        self._in_tabella = False
        self._squadra: str | None = None
        self._riga: dict | None = None
        self._pill = -1
        self._in_nome_span = False
        self._in_nome_link = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        c = _classi(a)
        if tag == "title":
            self._in_titolo = True
        elif tag == "li" and "team-table" in c:
            self._in_li_squadra = True
            self._data_squadra = None
        elif tag == "div" and "match-date" in c and self._in_li_squadra and not self._in_tabella:
            self._data_testo = ""
        elif tag == "table" and "grades-table" in c:
            self._in_tabella = True
            self.tabelle += 1
            self._squadra = None
        elif not self._in_tabella:
            return
        elif tag == "a" and "team-name" in c and self._squadra is None:
            m = _RE_SQUADRA.search(a.get("href") or "")
            if m:
                self._squadra = squadra_da_slug(m.group(1))
                self.squadre[self._squadra] = {"slug": m.group(1), "data": self._data_squadra}
        elif tag == "tbody":
            self._riga = None
        elif tag == "tr" and self._squadra is not None:
            self._riga = None
            self._pill = -1
        elif tag == "span" and "role" in c and "data-value" in a:
            if a["data-value"] in _RUOLI:
                self._riga = {"ruolo": _RUOLI[a["data-value"]], "eventi": {}, "voto": None, "fv_pubblicato": None,
                              "ammonito": False, "espulso": False}
                self._pill = -1
        elif self._riga is None:
            return
        elif tag == "a" and "player-name" in c:
            self._in_nome_link = True
            m = _RE_GIOCATORE.search(a.get("href") or "")
            if m:
                self._riga["squadra"] = squadra_da_slug(m.group(1))
                self._riga["id"] = m.group(2)
        elif tag == "span" and self._in_nome_link:
            self._in_nome_span = True
            self._riga.setdefault("nome", "")
        elif tag == "div" and "pill" in c and "header" not in c:
            self._pill += 1
        elif tag == "span" and self._pill == 0 and "player-grade" in c:
            self._riga["voto"] = _numero(a.get("data-value"))
            self._riga["ammonito"] = "yellow-card" in c
            self._riga["espulso"] = "red-card" in c
        elif tag == "span" and self._pill == 0 and "player-fanta-grade" in c:
            self._riga["fv_pubblicato"] = _numero(a.get("data-value"))
        elif tag == "span" and "player-bonus" in c:
            chiave = _EVENTI.get((a.get("title") or "").strip().lower())
            if chiave:
                self._riga["eventi"][chiave] = _intero(a.get("data-value"))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_titolo = False
        elif tag == "div" and self._data_testo is not None:
            try:
                self._data_squadra = ora_italiana(self._data_testo)
            except ValueError:
                self._data_squadra = None
            self._data_testo = None
        elif tag == "li":
            self._in_li_squadra = False
        elif tag == "span":
            self._in_nome_span = False
        elif tag == "a":
            self._in_nome_link = False
        elif tag == "tr" and self._riga is not None:
            self._chiudi_riga()
        elif tag == "table":
            self._in_tabella = False
            self._riga = None

    def handle_data(self, data):
        if self._in_titolo:
            self.titolo += data
        elif self._data_testo is not None:
            self._data_testo += data
        elif self._in_nome_span and self._riga is not None:
            self._riga["nome"] += data

    def _chiudi_riga(self):
        r, self._riga = self._riga, None
        r["nome"] = " ".join((r.get("nome") or "").split())
        if not r["nome"] or "id" not in r:
            self.righe_incomplete.append(f"riga senza nome o id ({self._squadra})")
            return
        e = r.pop("eventi")
        self.giocatori.append({
            "id": r["id"], "nome": r["nome"], "squadra": r["squadra"], "ruolo": r["ruolo"],
            "voto": r["voto"], "fv_pubblicato": r["fv_pubblicato"],
            "ammonito": r["ammonito"], "espulso": r["espulso"],
            "gol": e.get("gol", 0), "gol_subiti": e.get("gol_subiti", 0), "autogol": e.get("autogol", 0),
            "rigori_segnati": e.get("rigori_segnati", 0), "rigori_sbagliati": e.get("rigori_sbagliati", 0),
            "rigori_parati": e.get("rigori_parati", 0), "assist": e.get("assist", 0),
            "player_of_the_match": e.get("player_of_the_match", 0),
        })


def leggi_voti(html: str) -> dict:
    """Voti di una giornata: squadre (con slug e data), giocatori, mancanze."""
    lettore = _LettoreVoti()
    lettore.feed(html)
    lettore.close()
    if not lettore.tabelle:
        raise PaginaNonValida("la pagina non contiene tabelle di voti (grades-table)")
    titolo = " ".join(lettore.titolo.split())
    giornata = re.search(r"(\d+)\D{0,3}\s*giornata", titolo, re.I)
    stagione = re.search(r"(\d{4})\s*[/-]\s*(\d{2,4})", titolo)
    voti = {
        "stagione": f"{stagione.group(1)}-{stagione.group(2)[-2:]}" if stagione else None,
        "giornata": int(giornata.group(1)) if giornata else None,
        "squadre": lettore.squadre,
        "giocatori": lettore.giocatori,
        "mancanze": list(lettore.righe_incomplete),
    }
    return voti


def completezza(voti: dict) -> list[str]:
    """Elenco di ciò che manca nella pagina letta; vuoto se è completa."""
    mancanze = list(voti.get("mancanze", []))
    if voti.get("stagione") is None or voti.get("giornata") is None:
        mancanze.append("stagione o giornata non riconosciute")
    n = len(voti["squadre"])
    if n < SQUADRE_ATTESE:
        mancanze.append(f"mancano {SQUADRE_ATTESE - n} squadre")
    per_squadra: dict[str, int] = {}
    for g in voti["giocatori"]:  # solo chi ha un voto: una squadra tutta SV non ha giocato
        if g.get("voto") is not None:
            per_squadra[g["squadra"]] = per_squadra.get(g["squadra"], 0) + 1
    for nome, info in voti["squadre"].items():
        k = per_squadra.get(nome, 0)
        if k == 0:
            mancanze.append(f"{nome}: nessun voto, partita non giocata o rinviata")
        elif k < GIOCATORI_MINIMI_SQUADRA:
            mancanze.append(f"{nome}: solo {k} giocatori con voto")
        if info.get("data") is None:
            mancanze.append(f"{nome}: data della partita non riconosciuta")
    return mancanze


class _LettoreListone(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.righe: list[dict] = []
        self._riga: dict | None = None
        self._in_link = False
        self._in_span = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        c = _classi(a)
        if tag == "tr" and "player-row" in c:
            ruolo = (a.get("data-filter-role-classic") or "").strip().lower()
            self._riga = {"ruolo": _RUOLI.get(ruolo), "nome": ""}
        elif self._riga is None:
            return
        elif tag == "a" and "player-name" in c:
            self._in_link = True
            m = _RE_GIOCATORE.search(a.get("href") or "")
            if m:
                self._riga["squadra"] = squadra_da_slug(m.group(1))
                self._riga["id"] = m.group(2)
        elif tag == "span" and self._in_link:
            self._in_span = True

    def handle_endtag(self, tag):
        if tag == "span":
            self._in_span = False
        elif tag == "a":
            self._in_link = False
        elif tag == "tr" and self._riga is not None:
            r, self._riga = self._riga, None
            nome = " ".join(r["nome"].split())
            if nome and "id" in r and r["ruolo"]:
                self.righe.append({"id": r["id"], "nome": nome, "squadra": r["squadra"], "ruolo": r["ruolo"]})

    def handle_data(self, data):
        if self._in_span and self._riga is not None:
            self._riga["nome"] += data


def leggi_listone(html: str) -> list[dict]:
    """Listone Classic: id, nome, squadra e ruolo. I prezzi non si leggono."""
    lettore = _LettoreListone()
    lettore.feed(html)
    lettore.close()
    if not lettore.righe:
        raise PaginaNonValida("la pagina non contiene righe di giocatori (player-row)")
    return lettore.righe
