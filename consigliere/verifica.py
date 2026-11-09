"""Verifica di una giornata: formazione consigliata, collegamento ai voti, misure, regret, errori e archivio.

Solo libreria standard. Le verifiche e le schierate si aggiungono come nuove versioni, mai sovrascritte.
"""
import json
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from . import ottimo, pagine, punteggio, ricerca
from .archivio import controlla_id, scrivi_json
from .controllo import _norm, chiave, controlla_formazione
from .listone import _compatto

STAGIONE_CORRENTE = "2026-27"
VERSIONE = "1"
_STAGIONE = re.compile(r"^\d{4}-\d{2}$")
_VERSIONE_DIR = re.compile(r"^v(\d+)$")
_SCHIERATA = re.compile(r"^schierata-v(\d+)\.json$")
_EPS = 1e-9


def _data(valore):
    try:
        d = datetime.fromisoformat(valore)
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else None


def scadenza(voti: dict, lega: dict) -> str | None:
    """Prima partita della giornata meno l'anticipo della lega; None se nessuna data è nota."""
    date = [d for s in (voti.get("squadre") or {}).values() if (d := _data((s or {}).get("data")))]
    if not date:
        return None
    return (min(date) - timedelta(minutes=lega.get("anticipo_minuti") or 0)).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------------------------
# Formazione consigliata
# ---------------------------------------------------------------------------------------------
def _stato_sigillo(cartella: Path, riga: dict | None, limite: datetime) -> tuple[str, str]:
    """integro, alterato (impronte diverse), tardivo (apposto alla scadenza o dopo) o assente."""
    attuale = ricerca.impronta(cartella / "risultato.json")
    if riga is None:
        return "assente", attuale
    copia = cartella.parent / f"{cartella.name}.richiesta.json"
    if riga.get("sha256_risultato") != attuale or riga.get("sha256_richiesta") != ricerca.impronta(copia):
        return "alterato", attuale
    sigillato = _data(riga.get("sigillato_il"))
    if sigillato is None or sigillato >= limite:
        return "tardivo", attuale
    return "integro", attuale


def consigliata(base: Path, lega_id: str, giornata: int, scadenza: str | None) -> dict:
    """Ultima ricerca valida per la giornata conclusa prima della scadenza. Non sigilla nulla.

    Con un sigillo, l'ora di conclusione è quella registrata, mai quella attuale dei file.
    """
    esito = {"scelta": None, "dopo_scadenza": [], "senza_giornata": [], "scadenza": scadenza, "motivo": None}
    limite = _data(scadenza)
    candidate = []
    for c in ricerca._cartelle(base, lega_id):
        s = ricerca._stato(c)  # senza sigillo: una verifica non deve sigillare a posteriori
        if s["stato"] != "pronto":
            continue
        g = s["risultato"].get("giornata")
        if not isinstance(g, int) or isinstance(g, bool):
            esito["senza_giornata"].append(c.name)
            continue
        riga = ricerca.sigillo(base, lega_id, c.name)
        quando = _data(riga.get("fatto_il") if riga else ricerca.fatto_il(c))
        if g != giornata or quando is None:
            continue
        if limite is not None and quando >= limite:
            esito["dopo_scadenza"].append(c.name)
            continue
        candidate.append((quando, c, s, riga))
    if limite is None:
        return esito | {"motivo": "scadenza della giornata sconosciuta: mancano le date delle partite nei voti"}
    if not candidate:
        return esito | {"motivo": "nessuna ricerca valida per la giornata conclusa prima della scadenza"}
    quando, c, s, riga = max(candidate, key=lambda x: x[0])
    sigillo, impronta = _stato_sigillo(c, riga, limite)
    esito["scelta"] = {"ricerca": c.name, "risultato": s["risultato"], "fatto_il": quando.isoformat(timespec="seconds"),
                       "sigillo": sigillo, "sha256_risultato": impronta}
    return esito


# ---------------------------------------------------------------------------------------------
# Collegamento ai voti
# ---------------------------------------------------------------------------------------------
def _forme(squadra) -> set[str]:
    """Nome compatto della squadra da ogni inizio di parola: "Hellas Verona" -> hellasverona, verona."""
    parole = _norm(squadra).split()
    return {"".join(parole[i:]) for i in range(len(parole))}


def _stessa_squadra(a, b) -> bool:
    return any(min(len(x), len(y)) >= 3 and (x.startswith(y) or y.startswith(x)) for x in _forme(a) for y in _forme(b))


def _trova(g: dict, elenco: list[dict]) -> list[dict]:
    nome = _compatto(g.get("nome"))
    return [x for x in elenco if nome and _compatto(x.get("nome")) == nome and _stessa_squadra(g.get("squadra"), x.get("squadra"))]


def collega(giocatori: list[dict], voti: dict, listone: list[dict]) -> tuple[list[dict], list[dict]]:
    """(collegati con l'id di fantacalcio.it, non collegati con il motivo). Mai una scelta a caso tra omonimi."""
    pagina = voti.get("giocatori") or []
    con_id = [x for x in listone if x.get("id") is not None]
    collegati, non = [], []
    for g in giocatori:
        if g.get("id") is not None:
            collegati.append(dict(g))
            continue
        candidati = _trova(g, pagina) or _trova(g, con_id)  # assente dalla pagina ma nel listone: sarà SV
        ids = sorted({x["id"] for x in candidati})
        if len(ids) == 1:
            collegati.append(dict(g, id=ids[0], ruolo=g.get("ruolo") or candidati[0].get("ruolo")))
        elif ids:
            opzioni = [f"{x['nome']} ({x['squadra']}, id {x['id']})" for x in candidati]
            non.append(dict(g, motivo="più giocatori possibili: " + "; ".join(opzioni), opzioni=ids))
        else:
            non.append(dict(g, motivo="non trovato nella pagina dei voti né nel listone", opzioni=[]))
    return collegati, non


def _riferimento(valore, elenco: list[dict], ids: list):
    """Id del giocatore indicato per {"nome", "squadra"} o per nome (solo se unico); None altrimenti."""
    if isinstance(valore, dict):
        if valore.get("squadra"):
            k = chiave(valore.get("nome"), valore.get("squadra"))
            trovati = [i for g, i in zip(elenco, ids) if chiave(g.get("nome"), g.get("squadra")) == k]
            return trovati[0] if len(trovati) == 1 else None
        valore = valore.get("nome")
    if not valore:
        return None
    trovati = [i for g, i in zip(elenco, ids) if g.get("nome") == valore]
    return trovati[0] if len(trovati) == 1 else None


def formazione_da(f_risultato: dict, collegati: list[dict]) -> dict:
    """Formazione per `punteggio.valuta`; chi non è collegato ha un id fittizio e vale come SV.

    Capitano, vice e Switch: per nome e squadra se c'è la squadra, per nome solo se unico.
    """
    ids = {chiave(g.get("nome"), g.get("squadra")): g["id"] for g in collegati}

    def voce(g):
        id_ = ids.get(chiave(g.get("nome"), g.get("squadra")), f"non collegato: {g.get('nome')} ({g.get('squadra')})")
        return {"id": id_, "ruolo": g.get("ruolo")}

    tit_r, pan_r = f_risultato.get("titolari") or [], f_risultato.get("panchina") or []
    titolari, panchina = [voce(g) for g in tit_r], [voce(g) for g in pan_r]
    id_t, id_p = [v["id"] for v in titolari], [v["id"] for v in panchina]
    sw, switch = f_risultato.get("switch"), None
    if isinstance(sw, dict):
        t, r = _riferimento(sw.get("titolare"), tit_r, id_t), _riferimento(sw.get("riserva"), pan_r, id_p)
        if t is not None and r is not None:
            switch = {"titolare": t, "riserva": r}
    return {"modulo": f_risultato.get("modulo"), "titolari": titolari, "panchina": panchina,
            "capitano": _riferimento(f_risultato.get("capitano"), tit_r, id_t),
            "vice": _riferimento(f_risultato.get("vice"), tit_r, id_t), "switch": switch}


# ---------------------------------------------------------------------------------------------
# Misure, regret, errori
# ---------------------------------------------------------------------------------------------
def _candidati(lega: dict, voti: dict) -> list[dict]:
    ammonito = bool(lega.get("ammonito_senza_voto"))
    out = []
    for g in voti.get("giocatori") or []:
        v = punteggio.voto_effettivo(g, ammonito)
        if v is not None:
            out.append({"id": g["id"], "ruolo": g["ruolo"], "voto": v, "fv": punteggio.fv_lega(g, lega)})
    return out


def _con_nomi(r: dict | None, candidati: dict, voti_id: dict) -> dict | None:
    if r is None:
        return None
    dettaglio = [{"id": i, "nome": (voti_id.get(i) or {}).get("nome", str(i)), "ruolo": candidati[i]["ruolo"],
                  "voto": candidati[i]["voto"], "fv": candidati[i]["fv"]} for i in r["titolari"]]
    return r | {"giocatori": dettaglio}


def _misura(lega, voti, voti_id, candidati, ruoli_id, listone, f_ris, etichetta, motivi) -> dict | None:
    elenco = (f_ris.get("titolari") or []) + (f_ris.get("panchina") or []) if isinstance(f_ris, dict) else None
    if not isinstance(elenco, list) or not all(isinstance(g, dict) for g in elenco):
        motivi.append(f"{etichetta}: formazione mancante o non leggibile")
        return None
    collegati, non = collega(elenco, voti, listone)
    motivi += [f"{etichetta}: {g.get('nome')} ({g.get('squadra')}) non collegato ai voti, {g['motivo']}" for g in non]
    f = formazione_da(f_ris, collegati)
    # stessi ruoli delle perfette (pagina o correzione della lega): lo schieramento non può essere negativo
    for v in f["titolari"] + f["panchina"]:
        v["ruolo"] = ruoli_id.get(v["id"], v["ruolo"])
    try:
        ottenuto = punteggio.valuta(lega, voti_id, f)
    except (ValueError, KeyError, TypeError) as e:
        motivi.append(f"{etichetta}: formazione non valutabile ({e})")
        return None
    motivi += [f"{etichetta}: {m}" for m in ottenuto["motivi"]]
    for campo in ("capitano", "vice"):
        if f_ris.get(campo) and f[campo] is None:
            motivi.append(f"{etichetta}: {campo} non individuato tra i titolari (nome assente o ambiguo)")
    if f_ris.get("switch") and f["switch"] is None:
        motivi.append(f"{etichetta}: Switch non individuato (nome assente o ambiguo)")
    # stessi ruoli delle perfette (pagina o correzione della lega): la selezione non può essere negativa
    nei_18 = {x["id"] for x in f["titolari"] + f["panchina"]}
    per_id = {c["id"]: c for c in candidati}
    m18 = ottimo.migliore(lega, [c for c in candidati if c["id"] in nei_18])
    if m18 is None:
        motivi.append(f"{etichetta}: migliore tra i 18 non calcolabile, nessun modulo completo con i giocatori a voto")
    return {"ottenuto": ottenuto, "migliore_tra_18": _con_nomi(m18, per_id, voti_id), "non_collegati": non}


def _arrotonda(x):
    return None if x is None else round(x, 2) + 0.0


def _regret(assoluta, rosa, a_rosa: bool, mis: dict | None) -> dict | None:
    if mis is None:
        return None
    a = assoluta["totale"] if assoluta else None
    r = (rosa["totale"] if rosa else None) if a_rosa else a
    m18 = mis["migliore_tra_18"]["totale"] if mis["migliore_tra_18"] else None
    o = mis["ottenuto"]["totale"]

    def diff(x, y):
        return None if x is None or y is None else _arrotonda(x - y)
    return {"totale": diff(a, o), "limite_rosa": diff(a, r) if a_rosa else 0,
            "selezione": diff(r, m18), "schieramento": diff(m18, o)}


def _f(x) -> str:
    return "—" if x is None else f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _errori(lega: dict, etichetta: str, mis: dict | None, perfetta: dict | None) -> list[dict]:
    if mis is None:
        return []
    out, ott = [], mis["ottenuto"]
    gioc = {g["id"]: g for g in ott["giocatori"]}
    entra = {c["esce"]: c["entra"] for c in ott["cambi"]}
    for g in ott["giocatori"]:
        if not g["titolare"] or g["voto"] is not None:
            continue
        if g["id"] in entra:
            e = gioc[entra[g["id"]]]
            out.append({"formazione": etichetta, "tipo": "titolare_sv", "giocatore": g["nome"], "entrato": e["nome"],
                        "recuperati": e["fv"], "persi": None,
                        "testo": f"{g['nome']} senza voto: entra {e['nome']}, punti recuperati {_f(e['fv'])}"})
        else:
            libere = [r["fv"] for r in ott["giocatori"]
                      if not r["titolare"] and not r["in_campo"] and r["fv"] is not None and r["ruolo"] == g["ruolo"]]
            persi = max(libere, default=0)
            out.append({"formazione": etichetta, "tipo": "titolare_sv", "giocatore": g["nome"], "entrato": None,
                        "recuperati": None, "persi": persi,
                        "testo": f"{g['nome']} senza voto e non sostituito: punti persi {_f(persi)} "
                                 "(miglior riserva dello stesso ruolo rimasta fuori)"})
    cap = lega.get("capitano") or {}
    in_campo = [g for g in ott["giocatori"] if g["in_campo"] and g["voto"] is not None]
    if cap.get("attivo", True) and cap.get("fasce") and in_campo:
        best = max(in_campo, key=lambda g: (punteggio.bonus_capitano(g["voto"], cap), g["voto"]))
        bb, scelto = punteggio.bonus_capitano(best["voto"], cap), ott["capitano"]
        if bb > scelto["bonus"] + _EPS:
            nome = (gioc.get(scelto["id"]) or {}).get("nome", scelto["id"])
            out.append({"formazione": etichetta, "tipo": "capitano", "scelto": nome, "bonus": scelto["bonus"],
                        "migliore": best["nome"], "bonus_migliore": bb, "differenza": bb - scelto["bonus"],
                        "testo": f"Capitano {nome} (bonus {_f(scelto['bonus'])}): {best['nome']} avrebbe dato "
                                 f"{_f(bb)}, differenza {_f(bb - scelto['bonus'])}"})
    m18 = mis["migliore_tra_18"]
    if (lega.get("modificatore_difesa") or {}).get("attivo") and m18:
        a, b = ott["modificatore"]["bonus"], m18["modificatore"]["bonus"]
        if abs(a - b) > _EPS:
            out.append({"formazione": etichetta, "tipo": "modificatore", "ottenuto": a, "possibile": b,
                        "testo": f"Modificatore ottenuto {_f(a)}, possibile con gli stessi 18 {_f(b)}"})
    if perfetta:
        for g in perfetta["giocatori"]:
            if g["id"] not in gioc:
                out.append({"formazione": etichetta, "tipo": "fuori_dai_18", "giocatore": g["nome"],
                            "ruolo": g["ruolo"], "fv": g["fv"],
                            "testo": f"{g['nome']} ({g['ruolo']}, FV {_f(g['fv'])}) nella perfetta ma non tra i 18"})
    return out


def calcola(lega: dict, voti: dict, listone: list[dict], consigliata: dict | None, schierata: dict | None,
            *, meta_voti: dict | None = None) -> dict:
    motivi: list[str] = []
    mancanze = pagine.completezza(voti)
    if mancanze:
        motivi.append("voti incompleti: le perfette sono calcolate sul sottoinsieme disponibile")
    voti_id = {g["id"]: g for g in voti.get("giocatori") or []}
    a_rosa = lega.get("tipo") == "rosa"
    # ruoli corretti dalla lega (chiave nome|squadra del listone), collegati ai voti come la formazione
    corretti = [{"nome": k.split("|", 1)[0], "squadra": k.split("|", 1)[-1], "ruolo": r}
                for k, r in (lega.get("ruoli") or {}).items()]
    correzioni = {g["id"]: g["ruolo"] for g in collega(corretti, voti, listone)[0]}
    candidati = [dict(c, ruolo=correzioni.get(c["id"], c["ruolo"])) for c in _candidati(lega, voti)]
    ruoli_id = correzioni | {g["id"]: correzioni.get(g["id"], g["ruolo"]) for g in voti.get("giocatori") or []}
    rosa_ids = set()
    if a_rosa:
        rosa_col, rosa_non = collega(lega.get("rosa") or [], voti, listone)
        motivi += [f"rosa: {g.get('nome')} ({g.get('squadra')}) non collegato ai voti, {g['motivo']}" for g in rosa_non]
        rosa_ids = {g["id"] for g in rosa_col}
    per_id = {c["id"]: c for c in candidati}
    assoluta = _con_nomi(ottimo.migliore(lega, candidati), per_id, voti_id)
    rosa = _con_nomi(ottimo.migliore(lega, [c for c in candidati if c["id"] in rosa_ids]), per_id, voti_id) if a_rosa else None
    if assoluta is None:
        motivi.append("perfetta assoluta non calcolabile: nessun modulo completo con i giocatori a voto")
    if a_rosa and rosa is None:
        motivi.append("perfetta della rosa non calcolabile: nessun modulo completo con i giocatori a voto")
    riferimento = rosa if a_rosa else assoluta

    scelta = (consigliata or {}).get("scelta")
    mis_c = None
    if scelta is None:
        motivi.append("nessuna formazione consigliata: " + ((consigliata or {}).get("motivo")
                                                             or "nessuna ricerca valida prima della scadenza"))
    else:
        if scelta.get("sigillo") == "alterato":
            motivi.append("sigillo alterato: il risultato della ricerca è cambiato dopo la conclusione")
        elif scelta.get("sigillo") == "tardivo":
            motivi.append("sigillo apposto dopo la scadenza")
        elif scelta.get("sigillo") == "storico":
            motivi.append("previsione storica FantaLab (congelata in git), non sigillata dal registro")
        elif scelta.get("sigillo") != "integro":
            motivi.append("ricerca senza sigillo: impronta non registrata alla conclusione")
        forme = scelta["risultato"].get("formazioni") or {}
        mis_c = _misura(lega, voti, voti_id, candidati, ruoli_id, listone, forme.get("rosa" if a_rosa else "assoluta"),
                        "consigliata", motivi)
        if mis_c is not None:
            extra = (_misura(lega, voti, voti_id, candidati, ruoli_id, listone, forme.get("assoluta"), "consigliata (assoluta)",
                             motivi) if a_rosa else None)
            mis_c["assoluta_ottenuto"] = extra["ottenuto"] if extra else None
    mis_s = None
    if schierata is not None:
        motivi += controlla_formazione(schierata, lega, listone)
        mis_s = _misura(lega, voti, voti_id, candidati, ruoli_id, listone, schierata, "schierata", motivi)

    motivi = list(dict.fromkeys(motivi))
    stato = "DATI_INCOMPLETI" if mancanze else ("PROVVISORIO" if motivi else "CERTIFICATO")
    meta = meta_voti or {}
    return {
        "versione": VERSIONE, "stagione": voti.get("stagione"), "giornata": voti.get("giornata"),
        "lega": lega.get("id"), "nome_lega": lega.get("nome"), "stato": stato, "motivi": motivi,
        "voti": {"sha256": meta.get("sha256"), "ora": meta.get("ora"), "origine": meta.get("origine"),
                 "mancanze": mancanze},
        "ricerca": None if scelta is None else {
            "id": scelta["ricerca"], "fatto_il": scelta.get("fatto_il"), "sigillo": scelta.get("sigillo"),
            "sha256_risultato": scelta.get("sha256_risultato")},
        "scadenza": (consigliata or {}).get("scadenza"),
        "dopo_scadenza": (consigliata or {}).get("dopo_scadenza") or [],
        "misure": {"perfetta_assoluta": assoluta, "perfetta_rosa": rosa, "consigliata": mis_c, "schierata": mis_s},
        "regret": {"consigliata": _regret(assoluta, rosa, a_rosa, mis_c),
                   "schierata": _regret(assoluta, rosa, a_rosa, mis_s)},
        "errori": _errori(lega, "consigliata", mis_c, riferimento) + _errori(lega, "schierata", mis_s, riferimento),
    }


# ---------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------
def _tot(r) -> str:
    return _f(r["totale"]) if r else "—"


def _dettaglio(titolo: str, mis: dict) -> list[str]:
    o = mis["ottenuto"]
    righe = [f"## Dettaglio {titolo}", "", "| Giocatore | Ruolo | Voto | FV | Posto |", "|---|---|---|---|---|"]
    for g in o["giocatori"]:
        posto = "titolare" if g["titolare"] else "riserva"
        posto += ", uscito" if g["uscito"] else ", entrato" if g["entrato"] else ", in campo" if g["in_campo"] else ""
        righe.append(f"| {g['nome']} | {g['ruolo']} | {_f(g['voto'])} | {_f(g['fv'])} | {posto} |")
    nomi = {g["id"]: g["nome"] for g in o["giocatori"]}
    righe += ["", f"Cambi: {', '.join(f'{nomi[c['esce']]} → {nomi[c['entra']]}' for c in o['cambi']) or 'nessuno'}.",
              f"Modificatore: {_f(o['modificatore']['bonus'])} (media {_f(o['modificatore']['media'])}).",
              f"Capitano: {nomi.get(o['capitano']['id'], o['capitano']['id'] or '—')}, bonus {_f(o['capitano']['bonus'])}"
              + (" (dal vice)." if o["capitano"]["da"] == "vice" else ".")]
    if o.get("con_switch"):
        righe.append(f"Con lo Switch il totale sarebbe {_f(o['con_switch']['totale'])} (non conteggiato nelle misure).")
    return righe + [""]


def report_md(dati: dict) -> str:
    m, rg = dati["misure"], dati["regret"]
    r = [f"# Verifica {dati.get('nome_lega') or dati.get('lega')}, giornata {dati.get('giornata')}", "",
         f"**Stato: {dati['stato']}**", ""]
    if dati["motivi"]:
        r += ["Motivi:", ""] + [f"- {x}" for x in dati["motivi"]] + [""]
    r += ["## Misure", "", "| Misura | Punti |", "|---|---|",
          f"| Perfetta assoluta (uno degli ottimi) | {_tot(m['perfetta_assoluta'])} |"]
    if m["perfetta_rosa"] is not None:
        r.append(f"| Perfetta della rosa (uno degli ottimi) | {_tot(m['perfetta_rosa'])} |")
    for nome in ("consigliata", "schierata"):
        x = m[nome]
        if x:
            r += [f"| Migliore tra i 18 della {nome} | {_tot(x['migliore_tra_18'])} |",
                  f"| Ottenuto dalla {nome} | {_tot(x['ottenuto'])} |"]
            if x.get("assoluta_ottenuto"):
                r.append(f"| Ottenuto dalla migliore assoluta consigliata | {_tot(x['assoluta_ottenuto'])} |")
    r += ["", "## Regret", "", "| Formazione | Totale | Limite della rosa | Selezione | Schieramento |", "|---|---|---|---|---|"]
    for nome, x in rg.items():
        if x:
            r.append(f"| {nome} | {_f(x['totale'])} | {_f(x['limite_rosa'])} | {_f(x['selezione'])} | {_f(x['schieramento'])} |")
    for titolo, p in (("Perfetta assoluta", m["perfetta_assoluta"]), ("Perfetta della rosa", m["perfetta_rosa"])):
        if p:
            r += ["", f"## {titolo} (uno degli ottimi), {p['modulo']}", "",
                  ", ".join(f"{g['nome']} ({g['ruolo']}, {_f(g['fv'])})" for g in p["giocatori"]) + "."]
    r.append("")
    for nome in ("consigliata", "schierata"):
        if m[nome]:
            r += _dettaglio(nome, m[nome])
    r += ["## Errori", ""] + ([f"- {e['formazione']}: {e['testo']}" for e in dati["errori"]] or ["Nessuno."]) + [""]
    v, ric = dati["voti"], dati.get("ricerca")
    r += ["## Impronte", "", f"- Voti: sha256 {v['sha256'] or '—'}, {v['origine'] or '—'} il {v['ora'] or '—'}"]
    if ric:
        r.append(f"- Ricerca {ric['id']} conclusa il {ric['fatto_il']}: sigillo {ric['sigillo']}, "
                 f"sha256 {ric['sha256_risultato'] or '—'}")
    if dati.get("dopo_scadenza"):
        r.append(f"- Dopo la scadenza (non contano): {', '.join(dati['dopo_scadenza'])}")
    r.append(f"- Versione del codice: {dati.get('versione')}")
    if dati.get("sezioni_extra"):
        r += ["", "## Note", ""] + dati["sezioni_extra"]
    return "\n".join(r) + "\n"


# ---------------------------------------------------------------------------------------------
# Archivio delle verifiche e delle schierate
# ---------------------------------------------------------------------------------------------
def cartella_giornata(base: Path, lega_id: str, stagione: str, giornata: int) -> Path:
    controlla_id(lega_id)
    if not isinstance(stagione, str) or not _STAGIONE.match(stagione):
        raise ValueError(f"Stagione non valida: {stagione!r}")
    if not isinstance(giornata, int) or isinstance(giornata, bool) or not 1 <= giornata <= 38:
        raise ValueError(f"Giornata non valida: {giornata!r}")
    return Path(base) / "verifiche" / lega_id / stagione / f"G{giornata:02d}"


def _numeri(cartella: Path, modello: re.Pattern) -> list[int]:
    if not cartella.is_dir():
        return []
    return sorted(int(m.group(1)) for p in cartella.iterdir() if (m := modello.match(p.name)))


def _scrivi_testo(percorso: Path, testo: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=percorso.parent, prefix=".tmp-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(testo)
        os.replace(tmp, percorso)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _adesso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def salva(base: Path, lega_id: str, stagione: str, giornata: int, dati: dict) -> Path:
    g = cartella_giornata(base, lega_id, stagione, giornata)
    g.mkdir(parents=True, exist_ok=True)
    k = max(_numeri(g, _VERSIONE_DIR), default=0) + 1
    while True:
        try:
            (g / f"v{k}").mkdir()  # mai riusare una versione esistente
            break
        except FileExistsError:
            k += 1
    c = g / f"v{k}"
    dati = dati | {"versione_verifica": k, "salvata_il": _adesso()}
    scrivi_json(c / "verifica.json", dati)
    _scrivi_testo(c / "report.md", report_md(dati))
    return c


def versioni(base: Path, lega_id: str, stagione: str, giornata: int) -> list[dict]:
    g = cartella_giornata(base, lega_id, stagione, giornata)
    out = []
    for k in _numeri(g, _VERSIONE_DIR):
        try:
            d = json.loads((g / f"v{k}" / "verifica.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            out.append({"k": k, "ora": None, "stato": "illeggibile", "totali": {}})
            continue
        m = d.get("misure") or {}

        def tot(x):
            return x["totale"] if x else None
        out.append({"k": k, "ora": d.get("salvata_il"), "stato": d.get("stato"), "totali": {
            "perfetta_assoluta": tot(m.get("perfetta_assoluta")), "perfetta_rosa": tot(m.get("perfetta_rosa")),
            "consigliata": tot((m.get("consigliata") or {}).get("ottenuto")),
            "schierata": tot((m.get("schierata") or {}).get("ottenuto"))}})
    return out


def salva_schierata(base: Path, lega_id: str, stagione: str, giornata: int, f: dict) -> int:
    g = cartella_giornata(base, lega_id, stagione, giornata)
    g.mkdir(parents=True, exist_ok=True)
    k = max(_numeri(g, _SCHIERATA), default=0) + 1
    while True:
        try:
            open(g / f"schierata-v{k}.json", "x").close()  # prenota il nome: mai sovrascrivere
            break
        except FileExistsError:
            k += 1
    try:
        scrivi_json(g / f"schierata-v{k}.json", f)
    except BaseException:
        (g / f"schierata-v{k}.json").unlink(missing_ok=True)  # niente versione vuota lasciata indietro
        raise
    return k


def schierata(base: Path, lega_id: str, stagione: str, giornata: int) -> dict | None:
    g = cartella_giornata(base, lega_id, stagione, giornata)
    for k in reversed(_numeri(g, _SCHIERATA)):  # l'ultima leggibile
        try:
            return json.loads((g / f"schierata-v{k}.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
    return None
