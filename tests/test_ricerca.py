import json
import os
import shlex
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from consigliere.ricerca import (carica_ia, chiudi_ricerca, crea_ricerca, elenco_ricerche,
                                 ricerca_in_corso, scrivi_script, stato_ricerca)
from tests.aiuti import lega_prova, listone_prova, risultato_valido

ORA = datetime(2026, 11, 13, 18, 0, 0, tzinfo=timezone(timedelta(hours=1)))
IA = {"id": "claude", "nome": "Claude", "comando": "claude", "argomenti": ["{prompt}", "--allowedTools", "Bash({controllo})"],
      "avviso": None, "garantita": True}
GEMINI = {"id": "gemini", "nome": "Gemini", "comando": "gemini", "argomenti": ["--prompt-interactive", "{prompt}"],
          "avviso": "x", "garantita": True}


class TestRicerca(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def nuova(self, modello="grossa", ora=ORA):
        return crea_ricerca(self.base, lega_prova(modello), listone_prova(), IA, "sicuri", ora)

    def scrivi(self, c, risultato, fatto=True):
        testo = risultato if isinstance(risultato, str) else json.dumps(risultato)
        (c / "risultato.json").write_text(testo, encoding="utf-8")
        if fatto:
            (c / "FATTO").write_text("x")

    def test_cartella_contiene_tutto(self):
        c = self.nuova()
        for f in ("richiesta.json", "SKILL.md", "controlla.py", "avvia.command" if os.name != "nt" else "avvia.bat"):
            self.assertTrue((c / f).exists(), f)
        r = json.loads((c / "richiesta.json").read_text(encoding="utf-8"))
        self.assertEqual(r["stile"], "sicuri")
        self.assertIn("controlla.py richiesta.json risultato.json", r["comando_controllo"])
        self.assertEqual(c.parent, self.base / "ricerche" / "grossa")

    def test_ruoli_corretti_della_lega_nel_listone_della_richiesta(self):
        lega = lega_prova("pensionati")
        lega["ruoli"] = {"d01 rossi|ata": "C"}
        c = crea_ricerca(self.base, lega, listone_prova(), IA, "rischio", ORA)
        listone = json.loads((c / "richiesta.json").read_text(encoding="utf-8"))["listone"]
        self.assertEqual(next(g for g in listone if g["nome"] == "D01 Rossi")["ruolo"], "C")

    def test_due_ricerche_non_si_sovrascrivono(self):
        a, b = self.nuova(), self.nuova()
        self.assertNotEqual(a, b)
        self.assertTrue(a.exists() and b.exists())

    def test_nessuna_voce_approva_tutto(self):
        testo = (Path(__file__).resolve().parent.parent / "consigliere" / "ia.json").read_text(encoding="utf-8")
        for vietato in ("yolo", "bypassPermissions", "dangerously"):
            self.assertNotIn(vietato, testo)

    def test_carica_ia_segna_disponibilita(self):
        ia = {x["id"]: x for x in carica_ia()}
        self.assertEqual(set(ia), {"claude", "gemini", "opencode"})
        self.assertTrue(all(isinstance(x["disponibile"], bool) for x in ia.values()))

    def test_script_mac_con_spazi_e_accenti(self):
        c = self.base / "Andrea Città" / "r"
        c.mkdir(parents=True)
        s = scrivi_script(c, IA, "/usr/bin/python 3", "darwin")
        self.assertEqual(s.name, "avvia.command")
        self.assertTrue(os.access(s, os.X_OK))
        subprocess.run(["bash", "-n", str(s)], check=True)
        self.assertIn(shlex.quote(str(c)), s.read_text(encoding="utf-8"))

    def test_script_windows_con_spazi(self):
        c = self.base / "Mario Rossì" / "r"
        c.mkdir(parents=True)
        t = scrivi_script(c, GEMINI, r"C:\Program Files\Python\python.exe", "win32").read_bytes().decode("utf-8")
        self.assertIn("chcp 65001", t)
        self.assertIn(f'cd /d "{c}"', t)
        self.assertIn("\r\n", t)
        self.assertIn("call ", t)

    def test_stato_in_corso_senza_fatto(self):
        s = stato_ricerca(self.nuova())
        self.assertEqual(s["stato"], "in_corso")
        self.assertIsNone(s["risultato"])

    def test_stato_pronto_con_scadenza_calcolata(self):
        # prima partita 15:00, anticipo 15 minuti, scadenza 14:45
        c = self.nuova("pensionati")
        self.scrivi(c, risultato_valido("pensionati"))
        s = stato_ricerca(c)
        self.assertEqual(s["stato"], "pronto", s["errori"])
        self.assertEqual(s["scadenza"], "2026-11-14T14:45:00+01:00")
        self.assertEqual(s["risultato"]["giornata"], 12)

    def test_stato_errore_se_il_controllo_fallisce_al_terzo_tentativo(self):
        c = self.nuova()
        r = risultato_valido("grossa")
        r["formazioni"]["rosa"]["modulo"] = "3-6-1"
        self.scrivi(c, r)
        s = stato_ricerca(c)
        self.assertEqual(s["stato"], "errore")
        self.assertTrue(any("modulo" in e for e in s["errori"]))
        self.assertIsNone(s["risultato"])

    def test_programma_ricontrolla_anche_se_la_copia_di_controlla_e_alterata(self):
        c = self.nuova()
        (c / "controlla.py").write_text("def controlla(a, b):\n    return []\n")
        r = risultato_valido("grossa")
        r["formazioni"]["rosa"]["capitano"] = None
        self.scrivi(c, r)
        self.assertEqual(stato_ricerca(c)["stato"], "errore")

    def test_risultato_troncato_con_fatto_e_errore_senza_formazione(self):
        c = self.nuova()
        self.scrivi(c, '{"giornata": 12, "formazioni": {"ro')
        s = stato_ricerca(c)
        self.assertEqual(s["stato"], "errore")
        self.assertIsNone(s["risultato"])
        self.assertTrue(s["errori"])

    def test_chiudi_ricerca_senza_risultato_mostra_errore(self):
        c = self.nuova()
        chiudi_ricerca(c)
        s = stato_ricerca(c)
        self.assertEqual(s["stato"], "errore")
        self.assertIn("risultato", s["errori"][0])

    def test_chiudi_ricerca_con_risultato_valido_e_pronto(self):
        c = self.nuova()
        self.scrivi(c, risultato_valido("grossa"), fatto=False)
        chiudi_ricerca(c)
        self.assertEqual(stato_ricerca(c)["stato"], "pronto")

    def test_ricerca_in_corso_trova_solo_quella_non_finita(self):
        self.assertIsNone(ricerca_in_corso(self.base, "grossa"))
        vecchia = self.nuova()
        self.scrivi(vecchia, risultato_valido("grossa"))
        self.assertIsNone(ricerca_in_corso(self.base, "grossa"))
        nuova = self.nuova(ora=ORA + timedelta(minutes=5))
        self.assertEqual(ricerca_in_corso(self.base, "grossa"), nuova)

    def test_elenco_ricerche_dalla_piu_recente(self):
        a = self.nuova()
        self.scrivi(a, risultato_valido("grossa"))
        b = self.nuova(ora=ORA + timedelta(hours=1))
        e = elenco_ricerche(self.base, "grossa")
        self.assertEqual([x["id"] for x in e], [b.name, a.name])
        self.assertEqual([x["stato"] for x in e], ["in_corso", "pronto"])

    def test_ia_non_puo_riscrivere_le_regole_nella_cartella(self):
        c = self.nuova()
        r = risultato_valido("grossa")
        r["formazioni"]["rosa"]["modulo"] = "3-6-1"
        q = json.loads((c / "richiesta.json").read_text(encoding="utf-8"))
        q["lega"]["moduli"].append("3-6-1")
        (c / "richiesta.json").write_text(json.dumps(q), encoding="utf-8")
        self.scrivi(c, r)
        self.assertEqual(stato_ricerca(c)["stato"], "errore")

    def test_richiesta_cancellata_dalla_cartella_non_rompe_lo_stato(self):
        c = self.nuova()
        self.scrivi(c, risultato_valido("grossa"))
        (c / "richiesta.json").unlink()
        self.assertEqual(stato_ricerca(c)["stato"], "pronto")
        self.assertEqual([x["id"] for x in elenco_ricerche(self.base, "grossa")], [c.name])

    def test_claude_puo_scrivere_solo_il_risultato_con_regole_separate(self):
        voci = {x["id"]: x for x in json.loads((Path(__file__).resolve().parent.parent / "consigliere" / "ia.json").read_text(encoding="utf-8"))}
        a = voci["claude"]["argomenti"]
        self.assertIn("Write(./risultato.json)", a)
        self.assertIn("Bash({controllo})", a)
        self.assertFalse(any("./**" in x and x.startswith(("Write", "Edit")) for x in a))
        self.assertFalse(any("," in x for x in a if x.startswith(("Read", "Write", "Bash", "WebFetch"))))

    def test_id_con_percorso_rifiutato(self):
        with self.assertRaises(ValueError):
            elenco_ricerche(self.base, "../x")


if __name__ == "__main__":
    unittest.main()
