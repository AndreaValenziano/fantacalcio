import unittest
from pathlib import Path

from consigliere.listone import ListoneNonValido, abbina, leggi_xlsx, verifica_rosa
from tests.aiuti import crea_xlsx

VERO = Path(__file__).parent / "dati" / "listone_vero.xlsx"


class TestLeggiXlsx(unittest.TestCase):
    def test_legge_il_foglio_classic_con_riga_di_titolo(self):
        x = crea_xlsx({"Tutti": [["Quotazioni"], ["Id", "R", "RM", "Nome", "Squadra", "Qt.A"], [1, "A", "Pc", "Thuram", "Inter", 35]]})
        self.assertEqual(leggi_xlsx(x), [{"nome": "Thuram", "squadra": "Inter", "ruolo": "A"}])

    def test_preferisce_il_foglio_classic_al_mantra(self):
        x = crea_xlsx({
            "Tutti Mantra": [["R", "Nome", "Squadra"], ["A", "Mantra Uno", "Inter"]],
            "Tutti Classic": [["R", "Nome", "Squadra"], ["D", "Classic Uno", "Roma"]],
        })
        self.assertEqual(leggi_xlsx(x), [{"nome": "Classic Uno", "squadra": "Roma", "ruolo": "D"}])

    def test_formato_lista_della_lega_con_fuori_lista(self):
        x = crea_xlsx({"Lista calciatori": [
            ["#", "Nome", "Fuori lista", "Sq.", "Under", "R.", "R.MANTRA", "FantaSquadra", "Costo"],
            [5585, "Malen", "", "Roma", 27, "A", "Pc", "REAL", "631"],
            [1, "Partito", "*", "Lecce", 30, "C", "M", "", ""],
        ]})
        self.assertEqual(leggi_xlsx(x), [{"nome": "Malen", "squadra": "Roma", "ruolo": "A"}])

    def test_caratteri_speciali_decodificati(self):
        x = crea_xlsx({"F": [["R", "Nome", "Squadra"], ["D", "N'Dicka & <Co>", "Roma"]]})
        self.assertEqual(leggi_xlsx(x)[0]["nome"], "N'Dicka & <Co>")

    def test_file_non_excel_da_errore_chiaro(self):
        with self.assertRaises(ListoneNonValido):
            leggi_xlsx(b"ciao")

    def test_excel_senza_colonne_da_errore_chiaro(self):
        with self.assertRaisesRegex(ListoneNonValido, "colonne"):
            leggi_xlsx(crea_xlsx({"Foglio": [["a", "b"], [1, 2]]}))

    @unittest.skipUnless(VERO.exists(), "listone vero non presente")
    def test_listone_vero(self):
        g = leggi_xlsx(VERO.read_bytes())
        self.assertGreater(len(g), 400)
        self.assertEqual({x["ruolo"] for x in g}, {"P", "D", "C", "A"})
        self.assertIn({"nome": "Thuram", "squadra": "Inter", "ruolo": "A"}, g)


class TestAbbina(unittest.TestCase):
    G = [{"nome": "Martinez L.", "squadra": "INT", "ruolo": "A"}, {"nome": "Martinez J.", "squadra": "INT", "ruolo": "P"},
         {"nome": "Thuram", "squadra": "INT", "ruolo": "A"}, {"nome": "Dimarco", "squadra": "INT", "ruolo": "D"}]

    def test_abbina_esatto_cognome_e_accenti(self):
        r = abbina("thuram\nDi Marco\nMartinez\nNessuno", self.G)
        self.assertEqual([x["nome"] for x in r["trovati"]], ["Thuram", "Dimarco"])
        self.assertEqual(len(r["ambigui"][0]["opzioni"]), 2)
        self.assertEqual(r["ambigui"][0]["testo"], "Martinez")
        self.assertEqual(r["non_trovati"], ["Nessuno"])

    def test_esatto_vince_sul_prefisso(self):
        g = self.G + [{"nome": "Thuram K.", "squadra": "JUV", "ruolo": "C"}]
        self.assertEqual(abbina("Thuram", g)["trovati"][0]["squadra"], "INT")

    def test_squadra_nella_riga_risolve_omonimi(self):
        g = [{"nome": "Thuram", "squadra": "Inter", "ruolo": "A"}, {"nome": "Thuram", "squadra": "Juventus", "ruolo": "C"}]
        r = abbina("Thuram JUV\nThuram", g)
        self.assertEqual(r["trovati"], [g[1]])
        self.assertEqual(len(r["ambigui"]), 1)

    def test_righe_vuote_e_ruolo_davanti_ignorati(self):
        r = abbina("\n  A Thuram\n\nA - Thuram\n", self.G)
        self.assertEqual([x["nome"] for x in r["trovati"]], ["Thuram", "Thuram"])
        self.assertEqual(r["non_trovati"], [])


class TestVerificaRosa(unittest.TestCase):
    def test_verifica_rosa_cambio_squadra_e_giocatore_uscito(self):
        rosa = [{"nome": "Thuram", "squadra": "INT", "ruolo": "A"}, {"nome": "Vecchio", "squadra": "ROM", "ruolo": "C"}]
        g = [{"nome": "Thuram", "squadra": "JUV", "ruolo": "A"}]
        v = verifica_rosa(rosa, g)
        self.assertEqual({x["problema"] for x in v}, {"cambio_squadra", "non_trovato"})
        self.assertEqual(next(x for x in v if x["problema"] == "cambio_squadra")["nuova_squadra"], "JUV")

    def test_rosa_in_regola_nessun_problema(self):
        g = [{"nome": "Thuram", "squadra": "Inter", "ruolo": "A"}]
        self.assertEqual(verifica_rosa([dict(g[0])], g), [])


if __name__ == "__main__":
    unittest.main()
