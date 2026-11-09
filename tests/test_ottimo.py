import copy
import importlib.util
import json
import random
import sys
import time
import unittest
from pathlib import Path

from consigliere import ottimo, pagine, punteggio

RADICE = Path(__file__).resolve().parent.parent
VOTI_VERI = RADICE / "tests" / "dati" / "voti_vero_2026-27_11.html"
OTTIMIZZA = RADICE / "fantalab" / "strumenti" / "ottimizza.py"
LEGHE = ("libera", "grossa", "f1", "pensionati")
VOTI = [4 + 0.5 * i for i in range(9)]  # 4 ... 8 in passi di 0,5
BONUS_FV = [-2, -1, -0.5, 0, 0, 0, 1, 3, 4, 6]


def lega(nome):
    return json.loads((RADICE / "consigliere" / "modelli" / f"{nome}.json").read_text(encoding="utf-8"))


CAPITANO_LIBERA = lega("libera")["capitano"]
FASCE_GROSSA = lega("grossa")["modificatore_difesa"]["fasce"]


def variante(nome, capitano: bool, modificatore: bool) -> dict:
    """Regole della lega con capitano e modificatore accesi o spenti (fasce prese da altre leghe se mancano)."""
    l = copy.deepcopy(lega(nome))
    if capitano:
        if not (l.get("capitano") or {}).get("fasce"):
            l["capitano"] = copy.deepcopy(CAPITANO_LIBERA)
        l["capitano"]["attivo"] = True
    else:
        l["capitano"] = None if l.get("capitano") is None else {**l["capitano"], "attivo": False}
    md = l.get("modificatore_difesa") or {}
    if modificatore:
        l["modificatore_difesa"] = {"attivo": True, "fasce": md.get("fasce") or list(FASCE_GROSSA)}
    else:
        l["modificatore_difesa"] = {**md, "attivo": False}
    return l


def insieme_casuale(rng, quanti, voti=VOTI) -> list[dict]:
    out = []
    for ruolo, (lo, hi) in quanti.items():
        for i in range(rng.randint(lo, hi)):
            voto = rng.choice(voti)
            out.append({"id": f"{ruolo}{i:02d}", "ruolo": ruolo, "voto": voto, "fv": voto + rng.choice(BONUS_FV)})
    rng.shuffle(out)
    return out


PICCOLO = {"P": (2, 3), "D": (6, 8), "C": (5, 7), "A": (4, 6)}


def ricalcola(l, candidati, r) -> float:
    """Totale dell'undici restituito, ricalcolato da zero con le funzioni di punteggio."""
    per_id = {c["id"]: c for c in candidati}
    xi = [per_id[i] for i in r["titolari"]]
    totale = sum(c["fv"] for c in xi)
    md = l.get("modificatore_difesa") or {}
    difensori = [c["voto"] for c in xi if c["ruolo"] == "D"]
    if md.get("attivo") and len(difensori) >= 4:
        portiere = next(c["voto"] for c in xi if c["ruolo"] == "P")
        totale += punteggio.modificatore(portiere, difensori, md["fasce"])[1]
    return totale + max(punteggio.bonus_capitano(c["voto"], l.get("capitano")) for c in xi)


class TestCoerenza(unittest.TestCase):
    def controlla_uscita(self, l, candidati, r):
        per_id = {c["id"]: c for c in candidati}
        self.assertIn(r["modulo"], l["moduli"])
        d, c, a = map(int, r["modulo"].split("-"))
        self.assertEqual(len(set(r["titolari"])), 11)
        ruoli = [per_id[i]["ruolo"] for i in r["titolari"]]
        self.assertEqual([ruoli.count(x) for x in "PDCA"], [1, d, c, a])
        self.assertAlmostEqual(r["totale"], ricalcola(l, candidati, r))
        self.assertAlmostEqual(r["totale"], r["somma_fv"] + r["modificatore"]["bonus"] + r["bonus_capitano"])
        if r["capitano"] is not None:
            self.assertIn(r["capitano"], r["titolari"])
            self.assertEqual(r["bonus_capitano"], punteggio.bonus_capitano(per_id[r["capitano"]]["voto"], l["capitano"]))


class TestEnumeraVsMigliore(TestCoerenza):
    def test_uguale_a_enumera_casuale(self):
        varianti = [(True, True), (False, False), (True, False), (False, True)]
        for n in range(300):
            rng = random.Random(n)
            candidati = insieme_casuale(rng, PICCOLO)
            for k, nome in enumerate(LEGHE):
                cap, mod = varianti[(n + k) % 4]
                l = variante(nome, cap, mod)
                with self.subTest(seme=n, lega=nome, capitano=cap, modificatore=mod):
                    atteso = ottimo.enumera(l, candidati)
                    r = ottimo.migliore(l, candidati)
                    self.assertAlmostEqual(r["totale"], atteso["totale"])
                    self.controlla_uscita(l, candidati, r)
                    self.controlla_uscita(l, candidati, atteso)

    def test_uguale_a_enumera_capitano_raro(self):
        """Voti quasi tutti bassi: il bonus capitano alto è raro e decide in quale reparto prenderlo."""
        voti_bassi = [4, 4.5, 5, 5, 5.5, 5.5, 6, 6] * 3 + [6.5, 7, 7.5, 8]
        varianti = [(True, True), (True, False)]
        for n in range(200):
            candidati = insieme_casuale(random.Random(2000 + n), PICCOLO, voti_bassi)
            for k, nome in enumerate(LEGHE):
                cap, mod = varianti[(n + k) % 2]
                l = variante(nome, cap, mod)
                with self.subTest(seme=n, lega=nome, modificatore=mod):
                    r = ottimo.migliore(l, candidati)
                    self.assertAlmostEqual(r["totale"], ottimo.enumera(l, candidati)["totale"])
                    self.controlla_uscita(l, candidati, r)

    def test_fasce_non_monotone(self):
        """Fasce del modificatore e del capitano non monotone: la potatura per dominanza non vale, il risultato sì."""
        l = variante("grossa", True, True)
        l["modificatore_difesa"]["fasce"] = [6, 0, 4, 1, 5, 2, 3]
        l["capitano"]["fasce"] = [["6", 2], ["7", 0.5], ["8", 1]]
        solo_capitano = variante("grossa", True, True)  # modificatore monotono, capitano no
        solo_capitano["capitano"]["fasce"] = l["capitano"]["fasce"]
        voti_6_raro = [x for x in VOTI if x not in (6, 6.5)] * 4 + [6, 6.5]  # il bonus 2 (voto 6-6,5) è raro
        for n in range(80):
            candidati = insieme_casuale(random.Random(1000 + n), PICCOLO, VOTI if n % 2 else voti_6_raro)
            for regole in (l, solo_capitano):
                with self.subTest(seme=n, fasce=regole["modificatore_difesa"]["fasce"]):
                    r = ottimo.migliore(regole, candidati)
                    self.assertAlmostEqual(r["totale"], ottimo.enumera(regole, candidati)["totale"])
                    self.controlla_uscita(regole, candidati, r)


def carica_fantalab():
    spec = importlib.util.spec_from_file_location("fantalab_ottimizza", OTTIMIZZA)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # le dataclass di ottimizza.py cercano il proprio modulo
    spec.loader.exec_module(modulo)
    return modulo


@unittest.skipUnless(OTTIMIZZA.exists(), "fantalab non estratto")
class TestFantalab(TestCoerenza):
    def test_uguale_a_fantalab(self):
        fl = carica_fantalab()
        l = lega("libera")
        grande = {"P": (3, 6), "D": (10, 20), "C": (10, 20), "A": (6, 14)}
        for n in range(50):
            candidati = insieme_casuale(random.Random(5000 + n), grande)
            giocatori = [fl.Player(c["id"], c["id"], "Prova", c["ruolo"], c["voto"], c["fv"], True) for c in candidati]
            with self.subTest(seme=n):
                r = ottimo.migliore(l, candidati)
                self.assertAlmostEqual(r["totale"], fl.solve_best_xi(giocatori)["totale"])
                self.controlla_uscita(l, candidati, r)


def c(i, ruolo, voto, fv):
    return {"id": i, "ruolo": ruolo, "voto": voto, "fv": fv}


def base_433():
    """Undici di base per 4-3-3: portiere 6, centrocampisti 6, attaccanti 6."""
    return ([c("P1", "P", 6, 6)]
            + [c(f"C{i}", "C", 6, 6) for i in range(1, 4)]
            + [c(f"A{i}", "A", 6, 6) for i in range(1, 4)])


class TestCasiCostruiti(unittest.TestCase):
    def test_difensore_per_la_fascia(self):
        l = lega("libera")
        difesa = [c(f"D{i}", "D", 6.5, 7) for i in range(1, 4)] + [c("D4", "D", 5, 6), c("D5", "D", 8, 5.5)]
        resto = [dict(x, voto=8) if x["id"] == "A1" else x for x in base_433()]  # capitano da 2 comunque
        r = ottimo.migliore(l, resto + difesa)
        # con D4: media (6 + 19,5) / 4 = 6,375 -> 4; con D5: (6 + 21) / 4 = 6,75 -> 5, ma fv -0,5
        self.assertIn("D5", r["titolari"])
        self.assertNotIn("D4", r["titolari"])
        self.assertEqual(r["modificatore"], {"media": 6.75, "bonus": 5})
        self.assertEqual(r["capitano"], "A1")
        self.assertAlmostEqual(r["totale"], 6 + 21 + 5.5 + 18 + 18 + 5 + 2)
        self.assertEqual(r, ottimo.enumera(l, resto + difesa))

    def test_attaccante_per_il_capitano(self):
        l = lega("libera")
        difesa = [c(f"D{i}", "D", 6, 6) for i in range(1, 5)]
        attacco = [c("A1", "A", 6, 7), c("A2", "A", 6, 7), c("A3", "A", 6, 7), c("A9", "A", 8, 6.5)]
        candidati = [x for x in base_433() if x["ruolo"] != "A"] + difesa + attacco
        r = ottimo.migliore(l, candidati)
        self.assertIn("A9", r["titolari"])
        self.assertEqual(r["capitano"], "A9")
        self.assertEqual(r["bonus_capitano"], 2)
        self.assertAlmostEqual(r["totale"], 6 + 24 + 18 + 14 + 6.5 + 2 + 2)  # modificatore: media 6 -> 2
        self.assertEqual(r, ottimo.enumera(l, candidati))

    def test_centrocampista_per_il_capitano(self):
        l = lega("libera")
        difesa = [c(f"D{i}", "D", 6, 6) for i in range(1, 5)]
        centro = [c("C1", "C", 6, 7), c("C2", "C", 6, 7), c("C3", "C", 6, 7), c("C9", "C", 7.5, 6)]
        candidati = [x for x in base_433() if x["ruolo"] != "C"] + difesa + centro
        r = ottimo.migliore(l, candidati)
        self.assertEqual((r["capitano"], r["bonus_capitano"]), ("C9", 2))
        self.assertAlmostEqual(r["totale"], 6 + 24 + 14 + 6 + 18 + 2 + 2)
        self.assertEqual(r, ottimo.enumera(l, candidati))

    def test_portiere_e_difensore_per_il_capitano(self):
        """Senza modificatore il portiere (o il difensore) con fv più basso ma voto 8 dà il capitano."""
        l = variante("libera", True, False)
        difesa = [c(f"D{i}", "D", 6, 6) for i in range(1, 5)]
        portieri = [c("P2", "P", 8, 5.5)]
        r = ottimo.migliore(l, base_433() + difesa + portieri)
        self.assertEqual((r["capitano"], r["bonus_capitano"]), ("P2", 2))
        self.assertAlmostEqual(r["totale"], 5.5 + 24 + 36 + 2)
        difesa.append(c("D9", "D", 8, 5.5))
        r = ottimo.migliore(l, base_433() + difesa)
        self.assertEqual((r["capitano"], r["bonus_capitano"]), ("D9", 2))
        self.assertAlmostEqual(r["totale"], 6 + 18 + 5.5 + 36 + 2)
        self.assertEqual(r, ottimo.enumera(l, base_433() + difesa))

    def test_ruolo_insufficiente(self):
        l = lega("grossa")
        l["moduli"] = ["3-4-3", "4-3-3"]
        difesa = [c(f"D{i}", "D", 6, 6) for i in range(1, 5)]
        centro = [c("C4", "C", 6, 6)]
        candidati = base_433() + difesa + centro
        self.assertIsNotNone(ottimo.migliore(l, candidati))
        self.assertIsNotNone(ottimo.enumera(l, candidati))
        senza = [x for x in candidati if x["id"] != "A3"]
        self.assertIsNone(ottimo.migliore(l, senza))
        self.assertIsNone(ottimo.enumera(l, senza))

    def test_capitano_spento(self):
        l = lega("pensionati")
        r = ottimo.migliore(l, base_433() + [c(f"D{i}", "D", 6, 6) for i in range(1, 5)])
        self.assertIsNone(r["capitano"])
        self.assertEqual(r["bonus_capitano"], 0)
        self.assertEqual(r["modificatore"], {"media": None, "bonus": 0})
        self.assertEqual(r["totale"], 66)


@unittest.skipUnless(VOTI_VERI.exists(), "pagina vera G11 assente")
class TestPaginaVera(unittest.TestCase):
    def test_tempo_pagina_vera(self):
        l = lega("grossa")
        voti = pagine.leggi_voti(VOTI_VERI.read_text(encoding="utf-8"))
        candidati = []
        for g in voti["giocatori"]:
            voto = punteggio.voto_effettivo(g, bool(l.get("ammonito_senza_voto")))
            if voto is not None:
                candidati.append({"id": g["id"], "ruolo": g["ruolo"], "voto": voto, "fv": punteggio.fv_lega(g, l)})
        inizio = time.perf_counter()
        r = ottimo.migliore(l, candidati)
        durata = time.perf_counter() - inizio
        print(f"\nperfetta assoluta grossa G11: {r['totale']} ({r['modulo']}) in {durata * 1000:.1f} ms, {len(candidati)} giocatori")
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r["totale"], ricalcola(l, candidati, r))
        self.assertLess(durata, 10)


if __name__ == "__main__":
    unittest.main()
