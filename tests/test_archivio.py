import tempfile
import unittest
from pathlib import Path

from consigliere.archivio import Archivio, ArchivioDanneggiato, campi_mancanti


class TestArchivio(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.a = Archivio(self.base)

    def tearDown(self):
        self._tmp.cleanup()

    def test_modelli_con_i_valori_degli_screenshot(self):
        m = {x["id"]: x for x in self.a.modelli()}
        sette = {"3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"}
        self.assertEqual(set(m["pensionati"]["moduli"]), sette)
        self.assertEqual(set(m["grossa"]["moduli"]), sette)
        self.assertEqual(set(m["f1"]["moduli"]), sette | {"3-6-1"})
        self.assertEqual(m["grossa"]["panchina"], {"tipo": "fissa", "P": 1, "D": 2, "C": 2, "A": 2})
        self.assertEqual(m["f1"]["panchina"], {"tipo": "libera"})
        self.assertEqual(m["pensionati"]["switch"], "plus")
        self.assertEqual(m["grossa"]["switch"], "no")
        self.assertEqual(m["grossa"]["modificatore_difesa"]["fasce"], [1, 2, 3, 4, 5, 6, 6])
        self.assertEqual(m["f1"]["modificatore_difesa"]["fasce"], [0, 1, 1, 3, 3, 6, 6])
        self.assertEqual([m[k]["bonus"]["player_of_the_match"] for k in ("pensionati", "grossa", "f1")], [0.5, 0, 1])
        self.assertEqual([m[k]["anticipo_minuti"] for k in ("pensionati", "grossa", "f1")], [15, 0, 1])
        self.assertEqual([m[k]["sostituzioni"]["numero"] for k in ("pensionati", "grossa", "f1")], [None, 7, 5])
        self.assertEqual(m["f1"]["sostituzioni"]["tipo"], "hybrid")
        self.assertEqual(m["libera"]["moduli"], ["4-3-3"])
        self.assertEqual(m["libera"]["tipo"], "libera")

    def test_f1_incompleta_finche_mancano_capitano_e_switch(self):
        f1 = self.a.crea_da_modello("f1", "La mia F1")
        self.assertEqual(set(campi_mancanti(f1)), {"capitano", "switch"})
        f1 |= {"capitano": {"attivo": False}, "switch": "no"}
        self.assertEqual(campi_mancanti(f1), [])

    def test_lega_salvata_si_ritrova_riaprendo(self):
        l = self.a.crea_da_modello("grossa", "Grossa")
        l["rosa"] = [{"nome": "Thuram", "squadra": "INT", "ruolo": "A"}]
        self.a.salva_lega(l)
        self.assertEqual(Archivio(self.base).lega(l["id"])["rosa"][0]["nome"], "Thuram")

    def test_id_generato_dal_nome_e_unico(self):
        a = self.a.crea_da_modello("grossa", "Lega Città!")
        b = self.a.crea_da_modello("grossa", "Lega Città!")
        self.assertEqual(a["id"], "lega-citta")
        self.assertEqual(b["id"], "lega-citta-2")
        self.assertEqual(len(self.a.leghe()), 2)

    def test_id_con_percorso_rifiutato(self):
        with self.assertRaises(ValueError):
            self.a.lega("../../segreti")

    def test_file_danneggiato_segnalato_e_non_sovrascritto(self):
        l = self.a.crea_da_modello("grossa", "Grossa")
        p = self.base / "leghe" / f"{l['id']}.json"
        p.write_text("{rotto")
        with self.assertRaises(ArchivioDanneggiato):
            self.a.leghe()
        self.assertEqual(p.read_text(), "{rotto")

    def test_avviso_ricordato(self):
        self.assertFalse(self.a.avviso_accettato())
        self.a.accetta_avviso()
        self.assertTrue(Archivio(self.base).avviso_accettato())

    def test_listone_salvato_con_data(self):
        self.assertIsNone(self.a.listone())
        self.a.salva_listone([{"nome": "Thuram", "squadra": "Inter", "ruolo": "A"}])
        l = Archivio(self.base).listone()
        self.assertEqual(l["giocatori"][0]["nome"], "Thuram")
        self.assertIn("importato_il", l)

    def test_nuova_lega_ha_ruoli_corretti_vuoti(self):
        self.assertEqual(self.a.crea_da_modello("pensionati", "P")["ruoli"], {})


if __name__ == "__main__":
    unittest.main()
