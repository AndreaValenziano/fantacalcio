"""Controllo finale di una formazione proposta contro le regole della lega.

File unico con sola libreria standard: viene copiato in ogni cartella di ricerca
come controlla.py ed eseguito dall'IA con
    python controlla.py richiesta.json risultato.json
"""
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

RUOLI = ("P", "D", "C", "A")
DISPONIBILITA = {"disponibile", "infortunio_dubbio", "infortunato", "squalificato", "sconosciuta"}
DOMINI_VIETATI = ("leghe.fantacalcio.it", "apileague.fantacalcio.it")
MAX_TENTATIVI = 3


def _norm(testo) -> str:
    t = unicodedata.normalize("NFKD", str(testo or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def chiave(nome: str, squadra: str) -> str:
    return f"{_norm(nome)}|{_norm(squadra)}"


def _quanti(modulo: str) -> dict | None:
    if not isinstance(modulo, str) or not re.fullmatch(r"\d-\d-\d", modulo):
        return None
    d, c, a = (int(x) for x in modulo.split("-"))
    return {"P": 1, "D": d, "C": c, "A": a}


def _conta(giocatori) -> dict:
    n = dict.fromkeys(RUOLI, 0)
    for g in giocatori:
        if g.get("ruolo") in n:
            n[g["ruolo"]] += 1
    return n


def _modulo_di(conteggio: dict) -> str:
    return f"{conteggio['D']}-{conteggio['C']}-{conteggio['A']}"


def _data(valore):
    try:
        d = datetime.fromisoformat(valore)
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else None


def _link_errori(nome, link) -> list[str]:
    errori = []
    for u in link:
        try:
            parti = urlsplit(u if isinstance(u, str) else "")
            host = (parti.hostname or "").lower().rstrip(".")
        except ValueError:
            parti, host = None, ""
        if any(host == d or host.endswith("." + d) for d in DOMINI_VIETATI):
            errori.append(f"Scheda di {nome}: link verso una lega privata non ammesso ({u})")
        elif parti is None or parti.scheme not in ("http", "https") or not host:
            errori.append(f"Scheda di {nome}: link non valido ({u!r}), solo http o https")
    return errori


def _per_nome(giocatori, nome):
    trovati = [g for g in giocatori if g.get("nome") == nome]
    return trovati[0] if len(trovati) == 1 else None


def _controlla_formazione(etichetta, f, lega, listone, rosa_lega) -> list[str]:
    e = []
    pre = f"Formazione {etichetta}:"
    titolari, panchina = f.get("titolari") or [], f.get("panchina") or []
    if not isinstance(titolari, list) or not isinstance(panchina, list):
        return [f"{pre} titolari e panchina devono essere elenchi"]
    moduli = lega.get("moduli") or []
    quanti = _quanti(f.get("modulo"))
    if f.get("modulo") not in moduli or quanti is None:
        e.append(f"{pre} modulo {f.get('modulo')!r} non ammesso dalla lega (ammessi: {', '.join(moduli)})")
    if len(titolari) != 11:
        e.append(f"{pre} servono 11 titolari, ce ne sono {len(titolari)}")
    if quanti and _conta(titolari) != quanti:
        e.append(f"{pre} i ruoli dei titolari ({_modulo_di(_conta(titolari))}, {_conta(titolari)['P']} P) non tornano col modulo {f.get('modulo')}")

    visti = set()
    for g in titolari + panchina:
        nome = f"{g.get('nome')} ({g.get('squadra')})"
        k = chiave(g.get("nome"), g.get("squadra"))
        if k in visti:
            e.append(f"{pre} doppione: {nome} compare più volte")
        visti.add(k)
        voce = listone.get(k)
        if voce is None:
            e.append(f"{pre} {nome} non è nel listone: usa nome e squadra esatti")
        elif g.get("ruolo") != voce["ruolo"]:
            e.append(f"{pre} ruolo di {nome} sbagliato: dichiarato {g.get('ruolo')}, nel listone {voce['ruolo']}")
        if rosa_lega is not None and k not in rosa_lega:
            e.append(f"{pre} {nome} non è nella rosa")

    pan, n = lega.get("panchina") or {"tipo": "libera"}, _conta(panchina)
    if pan.get("tipo") == "fissa":
        attesa = {r: pan[r] for r in RUOLI}
        if n != attesa:
            e.append(f"{pre} la panchina deve avere esattamente {attesa}, ha {n}")
    elif pan.get("tipo") == "minimi":
        sotto = {r: m for r, m in pan["min"].items() if n[r] < m}
        if sotto:
            e.append(f"{pre} panchina sotto i minimi per {', '.join(sotto)}: servono {pan['min']}, ci sono {n}")
        if pan.get("max") is not None and len(panchina) > pan["max"]:
            e.append(f"{pre} panchina oltre il massimo di {pan['max']} ({len(panchina)})")

    cap, vice = f.get("capitano"), f.get("vice")
    if (lega.get("capitano") or {}).get("attivo"):
        if not cap:
            e.append(f"{pre} capitano mancante")
        elif _per_nome(titolari, cap) is None:
            e.append(f"{pre} il capitano {cap} non è tra i titolari")
        if not vice:
            e.append(f"{pre} vice mancante")
        elif vice == cap:
            e.append(f"{pre} il vice deve essere diverso dal capitano")
        elif _per_nome(titolari, vice) is None:
            e.append(f"{pre} il vice {vice} non è tra i titolari")
    elif cap or vice:
        e.append(f"{pre} capitano e vice non previsti dalla lega: lasciali a null")

    sw, regola = f.get("switch"), lega.get("switch")
    if sw and regola in (None, "no"):
        e.append(f"{pre} Switch non previsto dalla lega: lascialo a null")
    elif sw:
        t, r = _per_nome(titolari, sw.get("titolare")), _per_nome(panchina, sw.get("riserva"))
        if t is None:
            e.append(f"{pre} Switch: {sw.get('titolare')} non è tra i titolari")
        if r is None:
            e.append(f"{pre} Switch: {sw.get('riserva')} non è in panchina")
        if t and r and t.get("ruolo") != r.get("ruolo"):
            if "P" in (t.get("ruolo"), r.get("ruolo")):
                e.append(f"{pre} Switch: il portiere si scambia solo con un portiere")
            elif regola != "plus":
                e.append(f"{pre} Switch: la lega ammette solo lo scambio nello stesso ruolo")
            else:
                c = _conta(titolari)
                c[t["ruolo"]] -= 1
                c[r["ruolo"]] += 1
                if _modulo_di(c) not in (lega.get("moduli") or []):
                    e.append(f"{pre} Switch: il modulo risultante {_modulo_di(c)} non è ammesso")
    return e


def _controlla(richiesta: dict, risultato: dict) -> list[str]:
    e = []
    lega = richiesta["lega"]
    listone = {chiave(g["nome"], g["squadra"]): g for g in richiesta["listone"]}
    if not isinstance(risultato.get("giornata"), int):
        e.append("giornata deve essere un numero intero")
    for campo in ("prima_partita", "controllato_il"):
        if _data(risultato.get(campo)) is None:
            e.append(f"{campo} deve essere una data ISO con fuso orario, es. 2026-11-14T15:00:00+01:00")

    formazioni = risultato.get("formazioni")
    if not isinstance(formazioni, dict):
        return e + ["formazioni mancante"]
    if lega.get("tipo") == "libera":
        if "rosa" in formazioni:
            e.append("formazioni.rosa non prevista in una lega a scelta libera")
    elif not isinstance(formazioni.get("rosa"), dict):
        e.append("Manca la formazione della rosa (formazioni.rosa)")
    if not isinstance(formazioni.get("assoluta"), dict):
        e.append("Manca la migliore assoluta (formazioni.assoluta)")

    schede = {}
    for s in risultato.get("schede") or []:
        nome = f"{s.get('nome')} ({s.get('squadra')})"
        schede[chiave(s.get("nome"), s.get("squadra"))] = s
        if s.get("disponibilita") not in DISPONIBILITA:
            e.append(f"Scheda di {nome}: disponibilita {s.get('disponibilita')!r} non valida")
        conf, link = s.get("confidenza"), s.get("link")
        if not isinstance(link, list):
            e.append(f"Scheda di {nome}: link deve essere un elenco")
            link = []
        if not isinstance(conf, int) or not 0 <= conf <= 3:
            e.append(f"Scheda di {nome}: confidenza deve essere un intero da 0 a 3")
        elif conf > 0 and not link:
            e.append(f"Scheda di {nome}: confidenza {conf} senza link alle fonti")
        e += _link_errori(nome, link)

    esclusi = risultato.get("esclusi", [])
    if not isinstance(esclusi, list) or not all(
            isinstance(x, dict) and isinstance(x.get("nome"), str) and isinstance(x.get("motivo", ""), str) for x in esclusi):
        e.append('esclusi deve essere un elenco di {"nome": ..., "motivo": ...}')
    fonti = risultato.get("fonti_non_lette", [])
    if not isinstance(fonti, list) or not all(isinstance(x, str) for x in fonti):
        e.append("fonti_non_lette deve essere un elenco di indirizzi")
    else:
        e += [x.replace("Scheda di fonti_non_lette:", "fonti_non_lette:") for x in _link_errori("fonti_non_lette", fonti)]
    if not isinstance(risultato.get("differenza_piu_grande", ""), str):
        e.append("differenza_piu_grande deve essere un testo")

    rosa_lega = {chiave(g["nome"], g["squadra"]) for g in lega.get("rosa") or []}
    for etichetta in ("rosa", "assoluta"):
        f = formazioni.get(etichetta)
        if not isinstance(f, dict) or (etichetta == "rosa" and lega.get("tipo") == "libera"):
            continue
        e += _controlla_formazione(etichetta, f, lega, listone, rosa_lega if etichetta == "rosa" else None)
        for g in f.get("titolari") or []:
            nome = f"{g.get('nome')} ({g.get('squadra')})"
            s = schede.get(chiave(g.get("nome"), g.get("squadra")))
            if g.get("stato") not in ("sicuro", "dubbio"):
                e.append(f"Formazione {etichetta}: stato di {nome} deve essere sicuro o dubbio")
            if s is None:
                e.append(f"Formazione {etichetta}: manca la scheda del titolare {nome}")
                continue
            disp = s.get("disponibilita")
            if disp == "squalificato":
                e.append(f"Formazione {etichetta}: {nome} è squalificato e non può essere titolare")
            elif disp == "infortunato":
                e.append(f"Formazione {etichetta}: {nome} è infortunato e non può essere titolare")
            elif disp == "infortunio_dubbio":
                e.append(f"Formazione {etichetta}: {nome} ha un infortunio in dubbio e va lasciato fuori")
            if g.get("stato") == "sicuro":
                if s.get("fonti_in_disaccordo"):
                    e.append(f"Formazione {etichetta}: fonti in disaccordo su {nome}, va segnato come dubbio")
                if s.get("confidenza") == 0:
                    e.append(f"Formazione {etichetta}: confidenza 0 su {nome}, va segnato come dubbio")
    return e


def controlla(richiesta: dict, risultato: dict) -> list[str]:
    """Errori in italiano; lista vuota se il risultato è valido."""
    if not isinstance(risultato, dict):
        return ["Il risultato deve essere un oggetto JSON"]
    try:
        return _controlla(richiesta, risultato)
    except (KeyError, TypeError, AttributeError, ValueError) as ex:
        return [f"Formato del risultato non valido: {ex!r}"]


def main(argv) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    if len(argv) != 3:
        print("Uso: python controlla.py richiesta.json risultato.json")
        return 2
    p_rich, p_ris = Path(argv[1]), Path(argv[2])
    cartella = p_ris.resolve().parent
    f_tent = cartella / "tentativi.txt"
    try:
        n = int(f_tent.read_text(encoding="utf-8").strip() or 0) + 1
    except (FileNotFoundError, ValueError):
        n = 1
    f_tent.write_text(str(n), encoding="utf-8")

    try:
        richiesta = json.loads(p_rich.read_text(encoding="utf-8"))
        risultato = json.loads(p_ris.read_text(encoding="utf-8"))
        errori = controlla(richiesta, risultato)
    except FileNotFoundError as ex:
        errori = [f"File mancante: {ex.filename}"]
    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        errori = [f"JSON non valido, forse troncato: {ex}"]

    if not errori:
        (cartella / "FATTO").write_text("valido", encoding="utf-8")
        print("Controllo superato. Torna alla pagina del consigliere per vedere la formazione.")
        return 0
    print(f"Controllo NON superato (tentativo {n} di {MAX_TENTATIVI}):")
    for x in errori:
        print(f"- {x}")
    if n >= MAX_TENTATIVI:
        (cartella / "FATTO").write_text("tentativi esauriti", encoding="utf-8")
        print("Tentativi esauriti: torna alla pagina, che mostrerà gli errori.")
    else:
        print("Correggi risultato.json e riesegui il controllo.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
