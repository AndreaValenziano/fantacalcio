import unittest
from pathlib import Path

from consigliere import pagine
from consigliere.pagine import PaginaNonValida, completezza, leggi_listone, leggi_voti, ora_italiana, squadra_da_slug

DATI = Path(__file__).resolve().parent / "dati"
VOTI_VERI = DATI / "voti_vero_2026-27_11.html"
QUOTAZIONI_VERE = DATI / "quotazioni_vero.html"


def _leggi(nome):
    return (DATI / nome).read_text(encoding="utf-8")


class TestVoti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.voti = leggi_voti(_leggi("voti_ridotta.html"))
        cls.per_nome = {g["nome"]: g for g in cls.voti["giocatori"]}

    def test_voti_campi(self):
        self.assertEqual(self.per_nome["Orban"], {
            "id": "6112", "nome": "Orban", "squadra": "Hellas Verona", "ruolo": "A",
            "voto": 7.5, "fv_pubblicato": 10.5, "ammonito": False, "espulso": False,
            "gol": 1, "gol_subiti": 0, "autogol": 0, "rigori_segnati": 0, "rigori_sbagliati": 0,
            "rigori_parati": 0, "assist": 0, "player_of_the_match": 0})

    def test_eventi(self):
        m = self.per_nome["Montipo"]
        self.assertEqual((m["rigori_parati"], m["gol_subiti"], m["ruolo"]), (1, 2, "P"))
        self.assertEqual(self.per_nome["Carnesecchi"]["player_of_the_match"], 1)
        self.assertEqual(self.per_nome["Anguissa"]["assist"], 1)

    def test_nome_con_apostrofo(self):
        self.assertEqual(self.per_nome["N'Dri"]["id"], "8001")

    def test_voti_solo_redazione(self):
        # Obric: i tre pill dicono 55, 6, 55; Montipo: 6,5 / 7 / 6. Vale solo il primo.
        self.assertEqual(self.per_nome["Montipo"]["voto"], 6.5)
        self.assertIsNone(self.per_nome["Obric"]["voto"])

    def test_sv(self):
        o = self.per_nome["Obric"]
        self.assertIsNone(o["voto"])
        self.assertIsNone(o["fv_pubblicato"])

    def test_cartellini(self):
        self.assertTrue(self.per_nome["Kolasinac"]["ammonito"])
        self.assertFalse(self.per_nome["Kolasinac"]["espulso"])
        self.assertTrue(self.per_nome["De Roon"]["espulso"])
        self.assertFalse(self.per_nome["Carnesecchi"]["ammonito"] or self.per_nome["Carnesecchi"]["espulso"])

    def test_squadra_e_data(self):
        self.assertEqual(self.voti["squadre"]["Hellas Verona"],
                         {"slug": "hellas-verona", "data": "2026-11-08T15:00:00+01:00"})
        self.assertEqual(self.voti["squadre"]["Napoli"]["data"], "2026-10-24T20:45:00+02:00")

    def test_squadra_da_slug(self):
        self.assertEqual(squadra_da_slug("hellas-verona"), "Hellas Verona")
        self.assertEqual(squadra_da_slug("milan"), "Milan")

    def test_ora_italiana(self):
        self.assertEqual(ora_italiana("29/03/2026 - 12:00"), "2026-03-29T12:00:00+02:00")
        self.assertEqual(ora_italiana("28/03/2026 - 12:00"), "2026-03-28T12:00:00+01:00")
        self.assertEqual(ora_italiana("25/10/2026 - 12:00"), "2026-10-25T12:00:00+01:00")
        self.assertEqual(ora_italiana("24/10/2026 - 12:00"), "2026-10-24T12:00:00+02:00")
        with self.assertRaises(ValueError):
            ora_italiana("domani")

    def test_stagione_giornata(self):
        self.assertEqual(self.voti["stagione"], "2026-27")
        self.assertEqual(self.voti["giornata"], 11)

    def test_completezza_mancano_squadre(self):
        self.assertIn("mancano 17 squadre", completezza(self.voti))

    def test_completezza_squadra_corta(self):
        mancanze = completezza(self.voti)
        self.assertTrue(any("Hellas Verona" in m for m in mancanze), mancanze)

    def test_pagina_sbagliata(self):
        with self.assertRaises(PaginaNonValida):
            leggi_voti("<html><body><p>niente</p></body></html>")
        with self.assertRaises(PaginaNonValida):
            leggi_listone("<html><body><table></table></body></html>")


class TestListone(unittest.TestCase):
    def test_listone(self):
        righe = leggi_listone(_leggi("quotazioni_ridotta.html"))
        self.assertEqual(len(righe), 6)
        self.assertEqual(righe[1], {"id": "5585", "nome": "Malen", "squadra": "Roma", "ruolo": "A"})
        self.assertIn("Calò", [r["nome"] for r in righe])
        for r in righe:
            self.assertEqual(set(r), {"id", "nome", "squadra", "ruolo"})
            self.assertIn(r["ruolo"], "PDCA")


@unittest.skipUnless(VOTI_VERI.exists() and QUOTAZIONI_VERE.exists(), "pagine vere non scaricate")
class TestPagineVere(unittest.TestCase):
    def test_pagina_vera(self):
        voti = leggi_voti(VOTI_VERI.read_text(encoding="utf-8"))
        self.assertEqual(len(voti["squadre"]), 20)
        self.assertGreaterEqual(len(voti["giocatori"]), 300)
        self.assertEqual(completezza(voti), [])
        ids = [g["id"] for g in voti["giocatori"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(leggi_listone(QUOTAZIONI_VERE.read_text(encoding="utf-8"))), 500)


if __name__ == "__main__":
    unittest.main()
