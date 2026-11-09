import json
import unittest
from pathlib import Path

from consigliere import pagine, punteggio

RADICE = Path(__file__).resolve().parent.parent
VOTI_VERI = RADICE / "tests" / "dati" / "voti_vero_2026-27_11.html"


def lega(nome):
    return json.loads((RADICE / "consigliere" / "modelli" / f"{nome}.json").read_text(encoding="utf-8"))


def gioc(**k):
    g = {"id": 1, "nome": "X", "squadra": "Y", "ruolo": "C", "voto": 6.0, "fv_pubblicato": None,
         "ammonito": False, "espulso": False, "gol": 0, "gol_subiti": 0, "autogol": 0,
         "rigori_segnati": 0, "rigori_sbagliati": 0, "rigori_parati": 0, "assist": 0,
         "player_of_the_match": 0}
    g.update(k)
    return g


class TestFv(unittest.TestCase):
    def test_fv_gol_assist_cartellino(self):
        g = gioc(voto=6.5, gol=1, assist=1, ammonito=True)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 10.0)

    def test_fv_porta_inviolata(self):
        L = lega("libera")
        self.assertAlmostEqual(punteggio.fv_lega(gioc(ruolo="P", voto=6.0), L), 7.0)
        self.assertAlmostEqual(punteggio.fv_lega(gioc(ruolo="P", voto=6.0, gol_subiti=2), L), 4.0)
        self.assertIsNone(punteggio.fv_lega(gioc(ruolo="P", voto=None), L))

    def test_fv_player_of_the_match(self):
        g = gioc(voto=7.0, player_of_the_match=1)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("pensionati")), 7.5)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("f1")), 8.0)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 7.0)

    def test_sv_ammonito(self):
        g = gioc(voto=None, ammonito=True)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("pensionati")), 5.0)
        self.assertIsNone(punteggio.fv_lega(g, lega("libera")))
        self.assertIsNone(punteggio.fv_lega(None, lega("pensionati")))

    def test_porta_inviolata_solo_portiere(self):
        for ruolo in "DCA":
            g = gioc(ruolo=ruolo, voto=6.0, gol_subiti=0)
            self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 6.0, msg=ruolo)

    def test_rigore_segnato_non_doppio(self):
        g = gioc(voto=7.0, gol=0, rigori_segnati=1)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 10.0)

    def test_fv_coerente(self):
        ok = gioc(voto=6.0, assist=1, fv_pubblicato=7.0)
        self.assertTrue(punteggio.fv_coerente(ok))
        self.assertFalse(punteggio.fv_coerente(gioc(voto=6.0, assist=1, fv_pubblicato=6.5)))
        self.assertTrue(punteggio.fv_coerente(gioc(voto=None)))


class TestCapitano(unittest.TestCase):
    def test_capitano_confini(self):
        c = lega("libera")["capitano"]
        for v, atteso in [(5.5, 0), (6, 0.5), (6.5, 1), (7, 1.5), (7.5, 2), (8.5, 2), (5, 0), (6.25, 0.5)]:
            self.assertEqual(punteggio.bonus_capitano(v, c), atteso, v)
        self.assertFalse(punteggio.voto_mezzo(6.25))
        self.assertTrue(punteggio.voto_mezzo(6.5))

    def test_capitano_disattivo(self):
        self.assertEqual(punteggio.bonus_capitano(8, {"attivo": False}), 0)
        self.assertEqual(punteggio.bonus_capitano(8, None), 0)


class TestModificatore(unittest.TestCase):
    def test_modificatore_confini(self):
        f = [1, 2, 3, 4, 5, 6, 6]
        for media, atteso in [(5.99, 1), (6, 2), (6.24, 2), (6.25, 3), (6.5, 4), (6.75, 5), (7, 6), (7.25, 6)]:
            # portiere e difensori tutti uguali alla media: la media restituita coincide
            m, b = punteggio.modificatore(media, [media] * 4, f)
            self.assertAlmostEqual(m, media)
            self.assertEqual(b, atteso, media)
        self.assertEqual(punteggio.modificatore(6.75, [6.75] * 4, [0, 1, 1, 3, 3, 6, 6])[1], 3)

    def test_modificatore_tre_migliori(self):
        m, b = punteggio.modificatore(7, [7, 6.5, 6.5, 4], [1, 2, 3, 4, 5, 6, 6])
        self.assertAlmostEqual(m, 6.75)
        self.assertEqual(b, 5)

    def test_modificatore_pochi_difensori(self):
        f = [1, 2, 3, 4, 5, 6, 6]
        self.assertEqual(punteggio.modificatore(7, [7, 7, 7], f), (None, 0))
        self.assertEqual(punteggio.modificatore(None, [7, 7, 7, 7], f), (None, 0))

    def test_fasce_lunghezza_errata(self):
        with self.assertRaisesRegex(ValueError, "devono essere 7, trovate 5"):
            punteggio.modificatore(7, [7] * 4, [1, 2, 3, 4, 5])
        self.assertFalse(punteggio.fasce_monotone([1, 2, 3, 4, 5]))
        self.assertFalse(punteggio.fasce_monotone([0, 1, 2, 3, 4, 5, 6, 7]))

    def test_fasce_monotone(self):
        self.assertTrue(punteggio.fasce_monotone([0, 1, 1, 3, 3, 6, 6]))
        self.assertFalse(punteggio.fasce_monotone([0, 2, 1, 3, 3, 6, 6]))


@unittest.skipUnless(VOTI_VERI.exists(), "pagina vera G11 assente")
class TestPaginaVera(unittest.TestCase):
    def test_fv_pagina_vera(self):
        voti = pagine.leggi_voti(VOTI_VERI.read_text(encoding="utf-8"))
        con_voto = [g for g in voti["giocatori"] if g["voto"] is not None]
        falsi = [g for g in con_voto if not punteggio.fv_coerente(g)]
        perc = 100 * (len(con_voto) - len(falsi)) / len(con_voto)
        print(f"\nfv_coerente: {perc:.1f}% ({len(falsi)} incoerenti su {len(con_voto)})")
        for g in falsi:
            print("  ", g["nome"], g["ruolo"], g["voto"], "pubb.", g["fv_pubblicato"],
                  "ricalc.", punteggio.fv_lega(g, {"bonus": punteggio.BONUS_STANDARD, "ammonito_senza_voto": False}))
        self.assertGreaterEqual(perc, 95)


if __name__ == "__main__":
    unittest.main()
