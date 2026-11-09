"""Regole di punteggio: fantavoto della lega, bonus capitano, modificatore di difesa.

Funzioni pure, solo libreria standard.
"""

from collections import Counter
from math import factorial

# Bonus con cui è calcolato il FV pubblicato dalla pagina (senza porta inviolata e Player of the match).
BONUS_STANDARD = {
    "gol": 3, "rigore_segnato": 3, "rigore_parato": 3, "rigore_sbagliato": -3, "assist": 1,
    "gol_subito": -1, "autogol": -2, "ammonizione": -0.5, "espulsione": -1,
}
_VOTO_SV_AMMONITO = 5.5
_EPS = 1e-9


def voto_effettivo(g: dict | None, ammonito_senza_voto: bool) -> float | None:
    """Voto usato nel calcolo: None se assente o SV, salvo SV ammonito con regola attiva (5,5)."""
    if g is None:
        return None
    if g.get("voto") is not None:
        return float(g["voto"])
    if ammonito_senza_voto and g.get("ammonito"):
        return _VOTO_SV_AMMONITO
    return None


def fv_lega(g: dict | None, lega: dict) -> float | None:
    """Fantavoto secondo i bonus della lega; None se il giocatore non ha un voto utilizzabile."""
    bonus = lega["bonus"]
    voto = voto_effettivo(g, bool(lega.get("ammonito_senza_voto")))
    if voto is None:
        return None
    if g.get("voto") is None:  # SV ammonito: 5,5 più il solo malus dell'ammonizione
        return voto + bonus["ammonizione"]
    # La pagina conta `gol` ESCLUSI i rigori: gol e rigori segnati si sommano separatamente, mai due volte.
    totale = (
        voto
        + g["gol"] * bonus["gol"]
        + g["rigori_segnati"] * bonus["rigore_segnato"]
        + g["rigori_sbagliati"] * bonus["rigore_sbagliato"]
        + g["rigori_parati"] * bonus["rigore_parato"]
        + g["assist"] * bonus["assist"]
        + g["gol_subiti"] * bonus["gol_subito"]
        + g["autogol"] * bonus["autogol"]
        + (bonus["ammonizione"] if g["ammonito"] else 0)
        + (bonus["espulsione"] if g["espulso"] else 0)
        + g["player_of_the_match"] * bonus.get("player_of_the_match", 0)
    )
    if g["ruolo"] == "P" and g["gol_subiti"] == 0:
        totale += bonus.get("porta_inviolata", 0)
    return totale


def fv_coerente(g: dict) -> bool:
    """Il ricalcolo con i bonus standard coincide con il FV pubblicato (True per gli SV)."""
    if g.get("voto") is None:
        return True
    if g.get("fv_pubblicato") is None:
        return False
    ricalcolato = fv_lega(g, {"bonus": BONUS_STANDARD, "ammonito_senza_voto": False})
    return abs(ricalcolato - g["fv_pubblicato"]) < _EPS


def _soglia(testo: str) -> float:
    return float(testo.lstrip("<>=").strip())


def bonus_capitano(voto: float, capitano: dict | None) -> float:
    """Bonus della fascia con soglia numerica più alta <= voto; 0 sotto la più bassa o se disattivo."""
    if not capitano or not capitano.get("attivo", True) or not capitano.get("fasce"):
        return 0
    bonus = 0
    for testo, valore in sorted(((_soglia(t), v) for t, v in capitano["fasce"]), key=lambda x: x[0]):
        if voto + _EPS >= testo:
            bonus = valore
    # sotto la soglia più bassa il bonus è 0 anche se la fascia più bassa ne indicasse un altro
    minima = min(_soglia(t) for t, _ in capitano["fasce"])
    return bonus if voto + _EPS >= minima else 0


def voto_mezzo(voto: float) -> bool:
    """Multiplo di 0,5; altrimenti il bonus capitano è «da verificare»."""
    return abs(voto * 2 - round(voto * 2)) < _EPS


_NUM_FASCE = 7
_LIMITI_FASCE = (6.0, 6.25, 6.5, 6.75, 7.0, 7.25)


def modificatore(voto_portiere: float | None, voti_difensori: list[float],
                 fasce: list[float]) -> tuple[float | None, float]:
    """(media, bonus): media di portiere e 3 migliori difensori; (None, 0) se mancano i dati."""
    if len(fasce) != _NUM_FASCE:
        raise ValueError(f"Le fasce del modificatore devono essere {_NUM_FASCE}, trovate {len(fasce)}")
    if voto_portiere is None or len(voti_difensori) < 4:
        return None, 0
    migliori = sorted(voti_difensori, reverse=True)[:3]
    media = (voto_portiere + sum(migliori)) / 4
    indice = sum(1 for limite in _LIMITI_FASCE if media + _EPS >= limite)
    return media, fasce[indice]


def fasce_monotone(fasce: list[float]) -> bool:
    """Sono 7 e non decrescono al crescere della media."""
    return len(fasce) == _NUM_FASCE and all(a <= b for a, b in zip(fasce, fasce[1:]))


# ---------------------------------------------------------------------------------------------
# Valore di una formazione
# ---------------------------------------------------------------------------------------------
_ORDINE_RUOLI = {"P": 0, "D": 1, "C": 2, "A": 3}
_MOTIVO_HYBRID = "cambio di ruolo diverso (regola Hybrid da verificare)"
_MOTIVO_ORDINE = "ordine dei cambi da verificare"
_MOTIVO_VICE = "subentro del vice da verificare"
_MOTIVO_ORDINE_NON_VERIFICATO = "ordine dei cambi non verificato"
_MAX_ORDINI = 5000  # sequenze di ruoli distinte provate al massimo


def _modulo_di(ruoli: list[str]) -> str:
    return "-".join(str(sum(1 for r in ruoli if r == x)) for x in "DCA")


def _nome(voti: dict, i) -> str:
    g = voti.get(i)
    return g["nome"] if g else str(i)


def _vp(lega: dict, voti: dict, i) -> float | None:
    return voto_effettivo(voti.get(i), bool(lega.get("ammonito_senza_voto")))


def _sostituzioni(lega: dict, voti: dict, f: dict, ordine: list[int]) -> tuple[dict, list[dict]]:
    """Applica i cambi seguendo `ordine` (indici dei titolari senza voto).

    Ritorna (indice del titolare -> riserva entrata, cambi).
    """
    sost = lega["sostituzioni"]
    limite = sost.get("numero")
    ibrida = sost.get("tipo") == "hybrid"
    slot = [t["ruolo"] for t in f["titolari"]]  # ruolo di ogni posizione, cambia con un cambio di ruolo
    usate: set[int] = set()
    entrati: dict[int, dict] = {}
    cambi: list[dict] = []
    for idx in ordine:
        if limite is not None and len(cambi) >= limite:
            break
        ruolo = slot[idx]
        scelta = None
        for j, r in enumerate(f["panchina"]):
            if j not in usate and r["ruolo"] == ruolo and _vp(lega, voti, r["id"]) is not None:
                scelta = j
                break
        if scelta is None and ibrida and ruolo != "P":
            for j, r in enumerate(f["panchina"]):
                if j in usate or r["ruolo"] in (ruolo, "P") or _vp(lega, voti, r["id"]) is None:
                    continue
                nuovi = slot[:idx] + [r["ruolo"]] + slot[idx + 1:]
                if _modulo_di(nuovi) in lega["moduli"]:
                    scelta = j
                    break
        if scelta is None:
            continue
        r = f["panchina"][scelta]
        usate.add(scelta)
        entrati[idx] = r
        slot[idx] = r["ruolo"]
        cambi.append({"esce": f["titolari"][idx]["id"], "entra": r["id"],
                      "ruolo_diverso": r["ruolo"] != f["titolari"][idx]["ruolo"]})
    return entrati, cambi


def _valuta_ordine(lega: dict, voti: dict, f: dict, ordine: list[int]) -> dict:
    ammonito = bool(lega.get("ammonito_senza_voto"))
    entrati, cambi = _sostituzioni(lega, voti, f, ordine)
    usciti = {f["titolari"][idx]["id"] for idx in entrati}
    entrati_id = {r["id"] for r in entrati.values()}
    campo = [t for t in f["titolari"] if t["id"] not in usciti] + list(entrati.values())
    motivi: list[str] = []

    giocatori = []
    for ruolo_t, lista in (("titolare", f["titolari"]), ("riserva", f["panchina"])):
        for r in lista:
            g = voti.get(r["id"])
            in_campo = (r["id"] not in usciti) if ruolo_t == "titolare" else (r["id"] in entrati_id)
            coerente = fv_coerente(g) if g else True
            giocatori.append({
                "id": r["id"], "nome": _nome(voti, r["id"]), "ruolo": r["ruolo"],
                "voto": voto_effettivo(g, ammonito), "fv": fv_lega(g, lega),
                "titolare": ruolo_t == "titolare", "in_campo": in_campo,
                "entrato": r["id"] in entrati_id, "uscito": r["id"] in usciti, "fv_coerente": coerente,
            })
            if in_campo and not coerente:
                motivi.append(f"FV di {_nome(voti, r['id'])} da verificare")
    if any(c["ruolo_diverso"] for c in cambi):
        motivi.append(_MOTIVO_HYBRID)

    totale = sum(g["fv"] for g in giocatori if g["in_campo"] and g["fv"] is not None)

    if (lega.get("modificatore_difesa") or {}).get("attivo"):
        portiere = next((_vp(lega, voti, r["id"]) for r in campo if r["ruolo"] == "P"), None)
        difensori = [v for r in campo if r["ruolo"] == "D" and (v := _vp(lega, voti, r["id"])) is not None]
        media, bonus_mod = modificatore(portiere, difensori, lega["modificatore_difesa"]["fasce"])
    else:
        media, bonus_mod = None, 0
    totale += bonus_mod

    cap_cfg = lega.get("capitano")
    cap_id, vice_id = f.get("capitano"), f.get("vice")
    capitano = {"id": cap_id, "bonus": 0, "da": None}
    bonus_vice = 0
    if cap_cfg and cap_cfg.get("attivo", True):
        in_campo_id = {x["id"] for x in campo}  # il bonus spetta solo a chi e' in campo con un voto
        v_cap = _vp(lega, voti, cap_id) if cap_id in in_campo_id else None
        v_vice = _vp(lega, voti, vice_id) if vice_id in in_campo_id else None
        if v_cap is not None:
            capitano.update(bonus=bonus_capitano(v_cap, cap_cfg), da="capitano")
            beneficiato, voto_b = cap_id, v_cap
        elif cap_id is not None and v_vice is not None:
            bonus_vice = bonus_capitano(v_vice, cap_cfg)
            capitano.update(id=vice_id, bonus=bonus_vice, da="vice")
            if bonus_vice:
                motivi.append(_MOTIVO_VICE)
            beneficiato, voto_b = vice_id, v_vice
        else:
            beneficiato = voto_b = None
        if beneficiato is not None and not voto_mezzo(voto_b):
            motivi.append(f"voto di {_nome(voti, beneficiato)} non multiplo di 0,5: bonus capitano da verificare")
    totale += capitano["bonus"]

    return {"totale": totale, "totale_senza_vice": totale - bonus_vice if capitano["da"] == "vice" else None,
            "motivi": motivi, "giocatori": giocatori, "cambi": cambi,
            "modificatore": {"media": media, "bonus": bonus_mod}, "capitano": capitano}


def _con_switch(f: dict) -> dict | None:
    """Formazione con titolare e riserva dello Switch scambiati (stessa posizione in panchina)."""
    s = f.get("switch")
    if not s:
        return None
    titolari = list(f["titolari"])
    panchina = list(f["panchina"])
    i = next((k for k, r in enumerate(titolari) if r["id"] == s["titolare"]), None)
    j = next((k for k, r in enumerate(panchina) if r["id"] == s["riserva"]), None)
    if i is None:
        raise ValueError(f"Switch: il titolare {s['titolare']} non e' tra i titolari")
    if j is None:
        raise ValueError(f"Switch: la riserva {s['riserva']} non e' in panchina")
    titolari[i], panchina[j] = panchina[j], titolari[i]
    return {**f, "titolari": titolari, "panchina": panchina, "switch": None}


def _sequenze_distinte(conteggi: Counter, lunghezza: int):
    """Tutte le sequenze distinte di ruoli con i conteggi dati."""
    if lunghezza == 0:
        yield ()
        return
    for ruolo in sorted(conteggi):
        if conteggi[ruolo]:
            conteggi[ruolo] -= 1
            for resto in _sequenze_distinte(conteggi, lunghezza - 1):
                yield (ruolo,) + resto
            conteggi[ruolo] += 1


def _ordine_da_ruoli(f: dict, mancanti: list[int], sequenza: tuple) -> list[int]:
    """Traduce una sequenza di ruoli negli indici dei titolari (dentro il ruolo, nell'ordine dei titolari).

    Con i cambi per ruolo l'ordine fra titolari dello stesso ruolo non cambia il totale: contano solo i ruoli.
    """
    per_ruolo = {x: [i for i in mancanti if f["titolari"][i]["ruolo"] == x] for x in "PDCA"}
    prossimo = Counter()
    ordine = []
    for ruolo in sequenza:
        ordine.append(per_ruolo[ruolo][prossimo[ruolo]])
        prossimo[ruolo] += 1
    return ordine


def valuta(lega: dict, voti: dict, f: dict) -> dict:
    """Punteggio di una formazione: cambi, capitano/vice, modificatore, Switch. `voti` = id -> Giocatore."""
    mancanti = [i for i, t in enumerate(f["titolari"]) if _vp(lega, voti, t["id"]) is None]
    mancanti.sort(key=lambda i: (_ORDINE_RUOLI[f["titolari"][i]["ruolo"]], i))
    r = _valuta_ordine(lega, voti, f, mancanti)

    sost = lega["sostituzioni"]
    limite = sost.get("numero")
    ordine_conta = len(mancanti) > 1 and (sost.get("tipo") == "hybrid" or (limite is not None and len(mancanti) > limite))
    if ordine_conta:
        conteggi = Counter(f["titolari"][i]["ruolo"] for i in mancanti)
        n_ordini = factorial(len(mancanti))
        for c in conteggi.values():
            n_ordini //= factorial(c)
        if n_ordini > _MAX_ORDINI:
            r["motivi"].append(_MOTIVO_ORDINE_NON_VERIFICATO)
        else:
            for sequenza in _sequenze_distinte(conteggi, len(mancanti)):
                ordine = _ordine_da_ruoli(f, mancanti, sequenza)
                if abs(_valuta_ordine(lega, voti, f, ordine)["totale"] - r["totale"]) > _EPS:
                    r["motivi"].append(_MOTIVO_ORDINE)
                    break

    s = _con_switch(f)
    r["con_switch"] = valuta(lega, voti, s) if s else None
    r["stato"] = "PROVVISORIO" if r["motivi"] else "ESATTO"
    return r
