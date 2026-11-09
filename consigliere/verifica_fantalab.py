"""Verifica di G10 e G11 di FantaLab, lette da `fantalab/` senza mai scriverci.

Uso: python3 -m consigliere.verifica_fantalab --fantalab <cartella> --giornata <n> [--cartella <base>]
La previsione storica di una giornata (previsione_macchina.json) non e' sigillata dal registro: il report e'
PROVVISORIO. Senza previsione si usa il benchmark retrospettivo (BENCHMARK_PROVVISORIO.md) come confronto.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from . import fonti, pagine, verifica
from .archivio import MODELLI, scrivi_json
from .listone import _compatto

STAGIONE = verifica.STAGIONE_CORRENTE
LEGA_ID = "fantalab"
MOTIVO_STORICA = "previsione storica FantaLab (congelata in git), non sigillata dal registro"
_RUOLI = "PDCA"


def abbina_fantalab(slug: str, voti: dict) -> list[dict]:
    """Candidati della pagina dei voti per uno slug: `wesley_roma` = nome e squadra, `maignan` = solo nome.

    Un nome identico allo slug ha la precedenza sui nomi che solo ci iniziano (mora, non morata).
    """
    nome, _, squadra = slug.partition("_")
    nome, squadra = _compatto(nome), _compatto(squadra)
    pagina = voti.get("giocatori") or []
    tutti = [x for x in pagina if nome and _compatto(x["nome"]).startswith(nome)
             and (not squadra or _compatto(x["squadra"]).startswith(squadra))]
    esatti = [x for x in tutti if _compatto(x["nome"]) == nome]
    return esatti or tutti


def formazione_fantalab(previsione: dict, abbinamenti: dict, per_id: dict) -> dict:
    """Formazione nella forma di un risultato (nome, squadra, ruolo, id), titolari e panchina in ordine P, D, C, A.

    Chi non e' abbinato resta con lo slug come nome e senza id: verra' segnalato come non collegato.
    """
    def voce(slug, ruolo):
        x = per_id.get(abbinamenti.get(slug))
        if x is None:
            return {"nome": slug, "squadra": "", "ruolo": ruolo}
        return {"id": x["id"], "nome": x["nome"], "squadra": x["squadra"], "ruolo": x["ruolo"]}

    def gruppo(chiave):
        return [voce(s, r) for r in _RUOLI for s in (previsione.get(chiave) or {}).get(r, [])]
    tit = gruppo("titolari")
    f = {"modulo": "-".join(str(len((previsione.get("titolari") or {}).get(r, []))) for r in "DCA"),
         "titolari": tit, "panchina": gruppo("panchina")}
    for campo, sorgente in (("capitano", "capitano"), ("vice", "vicecapitano")):
        v = voce(previsione.get(sorgente), "")
        f[campo] = {"nome": v["nome"], "squadra": v["squadra"]} if v["squadra"] else {"nome": v["nome"]}
    return f


def risolvi(slugs: list, voti: dict, percorso: Path, input_fn, out) -> dict:
    """Abbinamenti slug -> id; ambigui o assenti chiesti con input(), risposte salvate in `percorso`."""
    try:
        salvati = json.loads(percorso.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        salvati = {}
    ids = {x["id"] for x in voti.get("giocatori") or []}
    risolti, nuovi = {}, False
    for slug in dict.fromkeys(slugs):
        if salvati.get(slug) in ids:
            risolti[slug] = salvati[slug]
            continue
        cand = abbina_fantalab(slug, voti)
        if len(cand) == 1:
            risolti[slug] = cand[0]["id"]
            continue
        if cand:
            out(f"Piu' giocatori per '{slug}':")
            for k, x in enumerate(cand, 1):
                out(f"  {k}) {x['nome']} ({x['squadra']}, {x['ruolo']}, id {x['id']})")
        else:
            out(f"Nessun giocatore trovato per '{slug}'.")
        r = input_fn(f"Numero del giocatore per '{slug}' (invio = non abbinato): ").strip()
        if r.isdigit() and 1 <= int(r) <= len(cand):
            risolti[slug] = cand[int(r) - 1]["id"]
            salvati[slug] = risolti[slug]
            nuovi = True
    if nuovi:
        scrivi_json(percorso, salvati)
    return risolti


def _voti(base: Path, giornata: int, input_fn, scaricatore, out):
    """(voti, meta) dall'ultima copia; se manca, una sola richiesta di scaricamento dopo conferma."""
    chiave = f"{STAGIONE}-{giornata}"
    ultima = fonti.ultima(base, "voti", chiave)
    if ultima:
        return pagine.leggi_voti(ultima[1]), ultima[0]
    out(f"Nessuna copia dei voti della giornata {giornata}.")
    if input_fn(f"Scarico la pagina dei voti da {fonti.url_voti(STAGIONE, giornata)}? [s/N] ").strip().lower() not in ("s", "si", "sì"):
        raise SystemExit("Voti non disponibili: carica la pagina dalla finestra del programma o conferma lo scaricamento.")
    r = fonti.acquisisci_voti(base, STAGIONE, giornata, None, scaricatore or fonti.Scaricatore())
    return r["voti"], r["meta"]


def _benchmark(testo: str) -> tuple[list[str], float | None]:
    """Undici del benchmark come testo e totale dichiarato."""
    righe = [f"{m.group(1)} {m.group(2).strip()} ({m.group(3).strip()}), {m.group(4).strip()}"
             for m in re.finditer(r"^\|\s*([PDCA])\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([\d,.]+)\s*\|", testo, re.M)]
    t = re.search(r"Totale:\*\*.*?=\s*\*\*([\d,.]+)\s*punti", testo)
    return righe, float(t.group(1).replace(",", ".")) if t else None


def _confronto(perfetta: float | None, dichiarato: float | None) -> str:
    if perfetta is None or dichiarato is None:
        return "Confronto con il benchmark non possibile: totale della perfetta o del benchmark mancante."
    d = f"{dichiarato:g}".replace(".", ",")
    p = f"{perfetta:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    if abs(perfetta - dichiarato) < 0.01:
        return f"Il benchmark di {d} punti e' confermato: la perfetta con le regole libere ottiene {p}."
    if perfetta > dichiarato:
        return f"Il benchmark di {d} punti e' superato: la perfetta con le regole libere ottiene {p}."
    return f"Il benchmark di {d} punti non e' raggiunto: la perfetta con le regole libere ottiene {p}."


def _controlla_previsione(prev) -> None:
    if not isinstance(prev, dict):
        raise ValueError("deve essere un oggetto JSON")
    for k in ("titolari", "panchina"):
        gruppi = prev.get(k)
        if not isinstance(gruppi, dict):
            raise ValueError(f"manca '{k}' (un oggetto con P, D, C, A)")
        for r in _RUOLI:
            if not isinstance(gruppi.get(r), list) or not all(isinstance(x, str) and x for x in gruppi[r]):
                raise ValueError(f"'{k}.{r}' deve essere un elenco di nomi")
    for k in ("capitano", "vicecapitano"):
        if not isinstance(prev.get(k), str) or not prev[k]:
            raise ValueError(f"'{k}' deve essere un nome")


class _DentroFantalab(Exception):
    pass


def _guardia(fl: Path, *percorsi: Path) -> None:
    """Rifiuta se un percorso, risolto (collegamenti simbolici degli antenati compresi), cade in fantalab."""
    for p in percorsi:
        r = Path(p).resolve()
        if r == fl or fl in r.parents:
            raise _DentroFantalab(f"Non si scrive mai dentro la cartella fantalab: {p} ci porta dentro.")


def _scritture(a, base: Path, abbinamenti: Path) -> tuple:
    """Cartelle finali in cui questa esecuzione puo' scrivere."""
    return (base, fonti._cartella(base, "voti", f"{STAGIONE}-{a.giornata}"), abbinamenti.parent, abbinamenti,
            verifica._cartella_giornata(base, LEGA_ID, STAGIONE, a.giornata))


def _lega() -> dict:
    modello = json.loads((MODELLI / "libera.json").read_text(encoding="utf-8"))
    return modello | {"id": LEGA_ID, "nome": "FantaLab"}


def main(argv=None, *, input_fn=input, scaricatore=None, out=print) -> int:
    p = argparse.ArgumentParser(prog="consigliere.verifica_fantalab")
    p.add_argument("--fantalab", type=Path, required=True)
    p.add_argument("--giornata", type=int, required=True)
    p.add_argument("--cartella", type=Path, default=Path.home() / "ConsiglioFormazione")
    a = p.parse_args(argv)
    fl, base = a.fantalab.resolve(), a.cartella.resolve()
    abbinamenti = base / "abbinamenti" / "fantalab.json"
    try:
        _guardia(fl, *_scritture(a, base, abbinamenti))
    except _DentroFantalab as e:
        out(str(e))
        return 2
    giorn = fl / "stagioni" / STAGIONE / f"G{a.giornata:02d}"
    prev_file, bench_file = giorn / "previsione_macchina.json", giorn / "BENCHMARK_PROVVISORIO.md"
    if not prev_file.is_file() and not bench_file.is_file():
        out(f"Niente da verificare in {giorn}: manca previsione_macchina.json e BENCHMARK_PROVVISORIO.md.")
        return 2
    try:
        return _esegui(a, fl, base, abbinamenti, input_fn, scaricatore, out)
    except _DentroFantalab as e:
        out(str(e))
        return 2
    except EOFError:
        out("Input terminato: risposta non data. Riprova da un terminale interattivo.")
        return 1


def _esegui(a, fl, base, abbinamenti, input_fn, scaricatore, out) -> int:
    giorn = fl / "stagioni" / STAGIONE / f"G{a.giornata:02d}"
    prev_file, bench_file = giorn / "previsione_macchina.json", giorn / "BENCHMARK_PROVVISORIO.md"
    _guardia(fl, *_scritture(a, base, abbinamenti))  # subito prima di un eventuale scaricamento
    try:
        voti, meta = _voti(base, a.giornata, input_fn, scaricatore, out)
    except SystemExit as e:
        out(str(e))
        return 1
    except (fonti.FonteNonAccessibile, pagine.PaginaNonValida, ValueError) as e:
        out(f"Voti non ottenuti: {e}")
        return 1
    lega, listone = _lega(), voti.get("giocatori") or []
    extra = []
    if prev_file.is_file():
        grezzo = prev_file.read_bytes()
        sha = hashlib.sha256(grezzo).hexdigest()
        try:
            prev = json.loads(grezzo.decode("utf-8"))
            _controlla_previsione(prev)
        except (ValueError, TypeError) as e:
            out(f"previsione_macchina.json non valida: {e}")
            return 1
        slugs = [s for k in ("titolari", "panchina") for r in _RUOLI for s in (prev.get(k) or {}).get(r, [])]
        slugs += [prev.get("capitano"), prev.get("vicecapitano")]
        _guardia(fl, abbinamenti.parent, abbinamenti)
        abb = risolvi([s for s in slugs if s], voti, abbinamenti, input_fn, out)
        f = formazione_fantalab(prev, abb, {x["id"]: x for x in listone})
        consigliata = {"scelta": {"ricerca": f"FantaLab G{a.giornata:02d} previsione_macchina.json",
                                  "risultato": {"giornata": a.giornata, "formazioni": {"assoluta": f}},
                                  "fatto_il": "n/d (previsione storica)", "sigillo": "storico",
                                  "sha256_risultato": sha}, "dopo_scadenza": [], "scadenza": None}
        extra = [f"Previsione storica: previsione_macchina.json, sha256 {sha}."]
    else:
        consigliata = {"scelta": None, "dopo_scadenza": [], "scadenza": None,
                       "motivo": "nessuna previsione per questa giornata (benchmark retrospettivo)"}
    dati = verifica.calcola(lega, voti, listone, consigliata, None, meta_voti=meta)
    if bench_file.is_file() and not prev_file.is_file():
        righe, dichiarato = _benchmark(bench_file.read_text(encoding="utf-8"))
        pa = dati["misure"]["perfetta_assoluta"]
        extra += ["Undici del benchmark (BENCHMARK_PROVVISORIO.md, ricostruzione retrospettiva):", ""]
        extra += [f"- {r}" for r in righe] + ["", _confronto(pa["totale"] if pa else None, dichiarato)]
        dati["benchmark"] = {"dichiarato": dichiarato, "undici": righe}
    dati["sezioni_extra"] = extra
    _guardia(fl, verifica._cartella_giornata(base, LEGA_ID, STAGIONE, a.giornata))
    cartella = verifica.salva(base, LEGA_ID, STAGIONE, a.giornata, dati)
    out(f"Verifica salvata in {cartella} (stato {dati['stato']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
