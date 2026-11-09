"""Regole di punteggio: fantavoto della lega, bonus capitano, modificatore di difesa.

Funzioni pure, solo libreria standard.
"""

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


_LIMITI_FASCE = (6.0, 6.25, 6.5, 6.75, 7.0, 7.25)


def modificatore(voto_portiere: float | None, voti_difensori: list[float],
                 fasce: list[float]) -> tuple[float | None, float]:
    """(media, bonus): media di portiere e 3 migliori difensori; (None, 0) se mancano i dati."""
    if voto_portiere is None or len(voti_difensori) < 4:
        return None, 0
    migliori = sorted(voti_difensori, reverse=True)[:3]
    media = (voto_portiere + sum(migliori)) / 4
    indice = sum(1 for limite in _LIMITI_FASCE if media + _EPS >= limite)
    return media, fasce[indice]


def fasce_monotone(fasce: list[float]) -> bool:
    """Le fasce non decrescono al crescere della media."""
    return all(a <= b for a, b in zip(fasce, fasce[1:]))
