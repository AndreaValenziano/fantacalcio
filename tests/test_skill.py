import json
import re
import unittest
from pathlib import Path

from tests.aiuti import risultato_valido

SKILL = Path(__file__).resolve().parent.parent / "consigliere" / "skill" / "SKILL.md"


class TestSkill(unittest.TestCase):
    def setUp(self):
        self.t = SKILL.read_text(encoding="utf-8")

    def test_skill_contiene_vincoli_e_formato(self):
        self.assertTrue(self.t.startswith("---\nname: "))
        self.assertIn("\ndescription: ", self.t.split("---")[1])
        for testo in ("leghe.fantacalcio.it", "apileague.fantacalcio.it", "/probabili-formazioni-serie-a",
                      "Scarica", "comando_controllo", "FATTO", "confidenza", "fonti_non_lette", "riassunto.json"):
            self.assertIn(testo, self.t)

    def test_skill_guida_la_scelta_del_modulo(self):
        sezione = self.t.split("## 5.")[1].split("## 6.")[0]
        for testo in ("Confronta", "3-4-3", "4-3-3", "senza modificatore", "con il modificatore"):
            self.assertIn(testo, sezione)

    def test_esempio_nella_skill_ha_le_chiavi_del_controllo(self):
        blocco = re.search(r"```json\n(.*?)\n```", self.t, re.S)
        self.assertIsNotNone(blocco, "manca il blocco JSON di esempio")
        esempio = json.loads(blocco.group(1))
        valido = risultato_valido("grossa")
        self.assertEqual(set(esempio), set(valido))
        f_es, f_ok = esempio["formazioni"]["rosa"], valido["formazioni"]["rosa"]
        self.assertEqual(set(f_es), set(f_ok))
        self.assertEqual(set(f_es["titolari"][0]), set(f_ok["titolari"][0]))
        self.assertEqual(set(esempio["schede"][0]), set(valido["schede"][0]))


if __name__ == "__main__":
    unittest.main()
