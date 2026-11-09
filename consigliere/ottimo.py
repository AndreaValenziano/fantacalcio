"""Formazione perfetta: l'undici migliore a posteriori secondo le regole di una lega.

Candidato: {"id", "ruolo", "voto", "fv"}, solo giocatori con voto effettivo (il chiamante calcola
`fv` con `punteggio.fv_lega`). Il totale di un undici è somma dei fv + modificatore di difesa
(se attivo e con almeno 4 difensori) + bonus capitano del titolare che ne ha di più.

`enumera` prova tutte le combinazioni (riferimento, insiemi piccoli); `migliore` dà lo stesso totale
con riduzioni esatte, abbastanza veloce per tutti i giocatori di una giornata.
Solo libreria standard, funzioni pure.
"""
import itertools

from . import punteggio

RUOLI = ("P", "D", "C", "A")
_EPS = 1e-9


# ---------------------------------------------------------------------------------------------
# Regole e valore di un undici
# ---------------------------------------------------------------------------------------------
def _quote(modulo: str) -> dict:
    d, c, a = (int(x) for x in modulo.split("-"))
    return {"P": 1, "D": d, "C": c, "A": a}


def _capitano_attivo(lega: dict) -> bool:
    cap = lega.get("capitano")
    return bool(cap and cap.get("attivo", True) and cap.get("fasce"))


def _fasce_modificatore(lega: dict, n_difensori: int) -> list | None:
    """Fasce del modificatore se si applica a un modulo con `n_difensori`, altrimenti None."""
    md = lega.get("modificatore_difesa") or {}
    return md["fasce"] if md.get("attivo") and n_difensori >= 4 else None


def _livelli(lega: dict) -> list:
    """Valori possibili del bonus capitano, in ordine crescente (solo 0 senza capitano)."""
    if not _capitano_attivo(lega):
        return [0]
    return sorted({0, *(v for _, v in lega["capitano"]["fasce"])})


def _prepara(lega: dict, candidati: list[dict]) -> dict:
    """Candidati per ruolo, con il bonus capitano già calcolato ("b")."""
    cap = lega.get("capitano") if _capitano_attivo(lega) else None
    per_ruolo = {r: [] for r in RUOLI}
    for c in candidati:
        b = punteggio.bonus_capitano(c["voto"], cap) if cap else 0
        per_ruolo[c["ruolo"]].append({**c, "b": b})
    for r in RUOLI:
        per_ruolo[r].sort(key=lambda g: g["id"])
    return per_ruolo


def _chiave(xi) -> tuple:
    """Tupla ordinata degli id: a pari totale vince la più piccola."""
    return tuple(sorted(g["id"] for g in xi))


def _risultato(lega: dict, modulo: str, xi: list[dict]) -> dict:
    """Valore di un undici, ricalcolato da zero con le funzioni di `punteggio`."""
    somma_fv = sum(g["fv"] for g in xi)
    fasce = _fasce_modificatore(lega, _quote(modulo)["D"])
    if fasce is not None:
        portiere = next(g["voto"] for g in xi if g["ruolo"] == "P")
        media, bonus_mod = punteggio.modificatore(portiere, [g["voto"] for g in xi if g["ruolo"] == "D"], fasce)
    else:
        media, bonus_mod = None, 0
    if _capitano_attivo(lega):
        cap = min(xi, key=lambda g: (-g["b"], -g["voto"], -g["fv"], g["id"]))
        capitano, bonus_cap = cap["id"], cap["b"]
    else:
        capitano, bonus_cap = None, 0
    ordine = {r: i for i, r in enumerate(RUOLI)}
    return {
        "totale": somma_fv + bonus_mod + bonus_cap,
        "modulo": modulo,
        "titolari": [g["id"] for g in sorted(xi, key=lambda g: (ordine[g["ruolo"]], g["id"]))],
        "capitano": capitano,
        "bonus_capitano": bonus_cap,
        "modificatore": {"media": media, "bonus": bonus_mod},
        "somma_fv": somma_fv,
    }


def _meglio(nuovo: tuple, attuale: tuple | None) -> bool:
    """(totale, chiave, ...): totale più alto, a parità chiave più piccola."""
    if attuale is None or nuovo[0] > attuale[0] + _EPS:
        return True
    return abs(nuovo[0] - attuale[0]) <= _EPS and nuovo[1] < attuale[1]


# ---------------------------------------------------------------------------------------------
# Enumerazione completa (riferimento)
# ---------------------------------------------------------------------------------------------
def _gruppi(giocatori: list[dict], n: int) -> list[tuple]:
    """Tutte le combinazioni di n giocatori: (somma fv, bonus capitano massimo, giocatori)."""
    return [(sum(g["fv"] for g in gr), max((g["b"] for g in gr), default=None), gr)
            for gr in itertools.combinations(giocatori, n)]


def enumera(lega: dict, candidati: list[dict]) -> dict | None:
    """Undici migliore provando tutte le combinazioni di ogni modulo; None se nessun modulo è completabile."""
    per_ruolo = _prepara(lega, candidati)
    migliore = None  # (totale, chiave, modulo, undici)
    for modulo in lega["moduli"]:
        q = _quote(modulo)
        if any(len(per_ruolo[r]) < q[r] for r in RUOLI):
            continue
        fasce = _fasce_modificatore(lega, q["D"])
        pacchetti = []
        for portiere in per_ruolo["P"]:
            for s_d, b_d, difesa in _gruppi(per_ruolo["D"], q["D"]):
                mod = 0
                if fasce is not None:
                    mod = punteggio.modificatore(portiere["voto"], [g["voto"] for g in difesa], fasce)[1]
                b = portiere["b"] if b_d is None else max(portiere["b"], b_d)
                pacchetti.append((portiere["fv"] + s_d + mod, b, (portiere, *difesa)))
        centro = _gruppi(per_ruolo["C"], q["C"])
        attacco = _gruppi(per_ruolo["A"], q["A"])
        for v_pd, b_pd, pd in pacchetti:
            for v_c, b_c, cc in centro:
                base = v_pd + v_c
                m = b_pd if b_c is None or b_pd >= b_c else b_c
                for v_a, b_a, aa in attacco:
                    totale = base + v_a + (m if b_a is None or m >= b_a else b_a)
                    if migliore is None or totale > migliore[0] - _EPS:
                        xi = (*pd, *cc, *aa)
                        nuovo = (totale, _chiave(xi), modulo, xi)
                        if _meglio(nuovo, migliore):
                            migliore = nuovo
    if migliore is None:
        return None
    return _risultato(lega, migliore[2], list(migliore[3]))


# ---------------------------------------------------------------------------------------------
# Ottimo con riduzioni esatte
# ---------------------------------------------------------------------------------------------
def _domina(y: dict, x: dict, chiavi: tuple) -> bool:
    """y domina x: non peggiore su ogni chiave e migliore su una, o uguale con id più piccolo."""
    vy = [y[k] for k in chiavi]
    vx = [x[k] for k in chiavi]
    if any(a < b for a, b in zip(vy, vx)):
        return False
    return vy != vx or y["id"] < x["id"]


def _potati(giocatori: list[dict], n: int, chiavi: tuple) -> list[dict]:
    """Scarta chi ha almeno n giocatori dello stesso ruolo che lo dominano su `chiavi`.

    Esatto se ogni chiave non può che migliorare il totale quando cresce: in un undici con un
    giocatore scartato almeno uno dei suoi n dominatori resta fuori, e lo scambio non peggiora.
    """
    tenuti = []
    for x in giocatori:
        dominatori = 0
        for y in giocatori:
            if y is not x and _domina(y, x, chiavi):
                dominatori += 1
                if dominatori >= n:
                    break
        if dominatori < n:
            tenuti.append(x)
    return tenuti


def _migliori_per_voto(giocatori: list[dict], n: int) -> list[dict]:
    """Riduzione di FantaLab: per ogni voto i migliori n per fv (stesso voto, stesso contributo)."""
    per_voto: dict[float, list[dict]] = {}
    for g in giocatori:
        per_voto.setdefault(g["voto"], []).append(g)
    tenuti = []
    for gruppo in per_voto.values():
        tenuti.extend(sorted(gruppo, key=lambda g: (-g["fv"], g["id"]))[:n])
    return tenuti


def _pacchetti(portieri: list[dict], difensori: list[dict], n_d: int, fasce: list | None,
               livelli: list) -> dict:
    """Per ogni livello b: miglior portiere+difesa (valore, chiave, giocatori) con un bonus capitano >= b."""
    per_bonus: dict = {}
    cache_mod: dict = {}
    for difesa in itertools.combinations(difensori, n_d):
        s_d = sum(g["fv"] for g in difesa)
        b_d = max((g["b"] for g in difesa), default=None)
        voti_d = tuple(sorted((g["voto"] for g in difesa), reverse=True))
        for portiere in portieri:
            mod = 0
            if fasce is not None:
                k = (portiere["voto"], voti_d)
                if k not in cache_mod:
                    cache_mod[k] = punteggio.modificatore(portiere["voto"], list(voti_d), fasce)[1]
                mod = cache_mod[k]
            b = portiere["b"] if b_d is None else max(portiere["b"], b_d)
            valore = portiere["fv"] + s_d + mod
            attuale = per_bonus.get(b)
            if attuale is None or valore > attuale[0] - _EPS:
                xi = (portiere, *difesa)
                nuovo = (valore, _chiave(xi), xi)
                if _meglio(nuovo, attuale):
                    per_bonus[b] = nuovo
    out = {}
    for livello in livelli:
        scelto = None
        for b, p in per_bonus.items():
            if b >= livello and _meglio(p, scelto):
                scelto = p
        out[livello] = scelto
    return out


def _migliori_k(giocatori: list[dict], n: int, livello, tutti: bool) -> tuple | None:
    """I migliori n per fv con almeno uno di bonus capitano >= livello (`group_best_k` di FantaLab).

    Se i primi n non ne hanno, l'ottimo vincolato è il miglior idoneo più i primi n-1: nessuno dei
    primi n è idoneo, quindi i primi n-1 restano i migliori fra i non scelti.
    """
    ordinati = sorted(giocatori, key=lambda g: (-g["fv"], g["id"]))
    if len(ordinati) < n:
        return None
    primi = ordinati[:n]
    if tutti or any(g["b"] >= livello for g in primi):
        return tuple(primi)
    idoneo = next((g for g in ordinati[n:] if g["b"] >= livello), None)
    if idoneo is None or n == 0:
        return None
    return (*primi[:n - 1], idoneo)


def migliore(lega: dict, candidati: list[dict]) -> dict | None:
    """Undici migliore su tutti i moduli della lega, con riduzioni esatte; None se nessun modulo è completabile.

    Per ogni modulo e ogni livello b del bonus capitano, il livello lo "garantisce" un reparto
    (portiere+difesa, centrocampo o attacco) e gli altri due sono liberi: il massimo su questi casi
    è l'ottimo, perché il caso del reparto che contiene il capitano dell'ottimo lo raggiunge.
    """
    per_ruolo = _prepara(lega, candidati)
    livelli = _livelli(lega)
    minimo = livelli[0]  # ogni bonus possibile è >= minimo: nessun vincolo
    cache_pacchetti: dict = {}
    scelto = None  # (totale, chiave, modulo, undici)
    for modulo in lega["moduli"]:
        q = _quote(modulo)
        if any(len(per_ruolo[r]) < q[r] for r in RUOLI):
            continue
        fasce = _fasce_modificatore(lega, q["D"])
        if (q["D"], fasce is not None) not in cache_pacchetti:
            if fasce is None:
                portieri = _potati(per_ruolo["P"], 1, ("b", "fv"))
                difensori = _potati(per_ruolo["D"], q["D"], ("b", "fv"))
            elif punteggio.fasce_monotone(fasce):
                portieri = _potati(per_ruolo["P"], 1, ("voto", "b", "fv"))
                difensori = _potati(per_ruolo["D"], q["D"], ("voto", "b", "fv"))
            else:
                portieri = _migliori_per_voto(per_ruolo["P"], 1)
                difensori = _migliori_per_voto(per_ruolo["D"], q["D"])
            cache_pacchetti[(q["D"], fasce is not None)] = _pacchetti(portieri, difensori, q["D"], fasce, livelli)
        pacchetti = cache_pacchetti[(q["D"], fasce is not None)]
        centro = {b: _migliori_k(per_ruolo["C"], q["C"], b, b == minimo) for b in livelli}
        attacco = {b: _migliori_k(per_ruolo["A"], q["A"], b, b == minimo) for b in livelli}
        for b in livelli:
            casi = ((pacchetti[b], centro[minimo], attacco[minimo]),
                    (pacchetti[minimo], centro[b], attacco[minimo]),
                    (pacchetti[minimo], centro[minimo], attacco[b]))
            for pd, cc, aa in casi:
                if pd is None or cc is None or aa is None:
                    continue
                xi = (*pd[2], *cc, *aa)
                # totale vero dell'undici (>= pacchetto + reparti + b): il massimo resta l'ottimo
                r = _risultato(lega, modulo, list(xi))
                nuovo = (r["totale"], _chiave(xi), modulo, xi)
                if _meglio(nuovo, scelto):
                    scelto = nuovo
    if scelto is None:
        return None
    return _risultato(lega, scelto[2], list(scelto[3]))
