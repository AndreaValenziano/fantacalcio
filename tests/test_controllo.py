import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from consigliere.controllo import chiave, controlla, controlla_formazione
from tests.aiuti import lega_prova, listone_prova, richiesta_prova, risultato_valido

CONTROLLO = Path(__file__).resolve().parent.parent / "consigliere" / "controllo.py"


def rosa(r):
    return r["formazioni"]["rosa"]


def cambia_ruolo_primo_difensore_in_C(r):
    next(g for g in rosa(r)["titolari"] if g["ruolo"] == "D")["ruolo"] = "C"


def metti_giocatore_del_listone_non_in_rosa(r):
    estraneo = next(g for g in listone_prova() if g["ruolo"] == "A" and g["nome"] == "A20 Rossi")
    rosa(r)["panchina"][-1] = dict(estraneo)


def metti_nome_inventato_in_assoluta(r):
    r["formazioni"]["assoluta"]["panchina"][-1]["nome"] = "Inventato Bianchi"


def cambia_ruolo_dichiarato(r):
    next(g for g in rosa(r)["panchina"] if g["ruolo"] == "D")["ruolo"] = "A"


def copia_titolare_in_panchina(r):
    f = rosa(r)
    tit = next(g for g in f["titolari"] if g["ruolo"] == "A")
    i = next(i for i, g in enumerate(f["panchina"]) if g["ruolo"] == "A")
    f["panchina"][i] = {k: tit[k] for k in ("nome", "squadra", "ruolo")}


def togli_una_riserva(r):
    rosa(r)["panchina"].pop()


def togli_riserva_portiere(r):
    f = rosa(r)
    i = next(i for i, g in enumerate(f["panchina"]) if g["ruolo"] == "P")
    f["panchina"].pop(i)


def aggiungi_quindicesima_riserva(r):
    f = rosa(r)
    f["panchina"].append(dict(f["panchina"][0], nome="Extra Verdi"))


def capitano_preso_dalla_panchina(r):
    rosa(r)["capitano"] = rosa(r)["panchina"][0]["nome"]


def vice_uguale_capitano(r):
    rosa(r)["vice"] = rosa(r)["capitano"]


def imposta_capitano(r):
    f = rosa(r)
    f["capitano"] = f["titolari"][-1]["nome"]


def imposta_switch(r):
    f = rosa(r)
    f["switch"] = {"titolare": f["titolari"][-1]["nome"], "riserva": f["panchina"][-1]["nome"]}


def switch_con_riserva_inventata(r):
    rosa(r)["switch"]["riserva"] = "Nessuno Neri"


def switch_verso_modulo_vietato(r):
    f = rosa(r)
    d = next(g for g in f["titolari"] if g["ruolo"] == "D")
    a = next(g for g in f["panchina"] if g["ruolo"] == "A")
    f["switch"] = {"titolare": d["nome"], "riserva": a["nome"]}


def switch_portiere_con_attaccante(r):
    f = rosa(r)
    p = next(g for g in f["titolari"] if g["ruolo"] == "P")
    a = next(g for g in f["panchina"] if g["ruolo"] == "A")
    f["switch"] = {"titolare": p["nome"], "riserva": a["nome"]}


def _scheda_primo_titolare(r):
    t = rosa(r)["titolari"][0]
    return next(s for s in r["schede"] if s["nome"] == t["nome"] and s["squadra"] == t["squadra"])


def scheda_titolare_squalificato(r):
    _scheda_primo_titolare(r)["disponibilita"] = "squalificato"


def scheda_titolare_infortunio_dubbio(r):
    _scheda_primo_titolare(r)["disponibilita"] = "infortunio_dubbio"


def disaccordo_con_stato_sicuro(r):
    _scheda_primo_titolare(r)["fonti_in_disaccordo"] = True


def confidenza_zero_con_stato_sicuro(r):
    s = _scheda_primo_titolare(r)
    s["confidenza"], s["link"] = 0, []


def togli_scheda_primo_titolare(r):
    r["schede"].remove(_scheda_primo_titolare(r))


def togli_link_da_scheda(r):
    _scheda_primo_titolare(r)["link"] = []


def link_javascript(r):
    _scheda_primo_titolare(r)["link"] = ["javascript:alert(1)"]


def link_a_leghe_fantacalcio(r):
    _scheda_primo_titolare(r)["link"] = ["https://leghe.fantacalcio.it/i-pensionati/rosa"]


def link_a_apileague(r):
    _scheda_primo_titolare(r)["link"] = ["https://apileague.fantacalcio.it/x"]


CASI = [
    ("modulo_non_ammesso", "grossa", lambda r: r["formazioni"]["rosa"].update(modulo="3-6-1"), "modulo"),
    ("ruoli_non_tornano_col_modulo", "grossa", cambia_ruolo_primo_difensore_in_C, "modulo"),
    ("giocatore_fuori_rosa", "grossa", metti_giocatore_del_listone_non_in_rosa, "rosa"),
    ("assoluta_non_nel_listone", "grossa", metti_nome_inventato_in_assoluta, "listone"),
    ("ruolo_diverso_dal_listone", "grossa", cambia_ruolo_dichiarato, "ruolo"),
    ("doppione_titolare_panchina", "grossa", copia_titolare_in_panchina, "doppione"),
    ("panchina_fissa_sbagliata", "grossa", togli_una_riserva, "panchina"),
    ("panchina_sotto_minimi", "pensionati", togli_riserva_portiere, "panchina"),
    ("panchina_oltre_massimo", "pensionati", aggiungi_quindicesima_riserva, "panchina"),
    ("capitano_mancante", "grossa", lambda r: r["formazioni"]["rosa"].update(capitano=None), "capitano"),
    ("capitano_non_titolare", "grossa", capitano_preso_dalla_panchina, "capitano"),
    ("vice_uguale_capitano", "grossa", vice_uguale_capitano, "vice"),
    ("capitano_dove_non_previsto", "pensionati", imposta_capitano, "capitano"),
    ("switch_dove_non_previsto", "grossa", imposta_switch, "switch"),
    ("switch_riserva_fuori_panchina", "pensionati", switch_con_riserva_inventata, "switch"),
    ("switch_modulo_non_ammesso", "pensionati", switch_verso_modulo_vietato, "switch"),
    ("switch_portiere_con_movimento", "pensionati", switch_portiere_con_attaccante, "switch"),
    ("squalificato_titolare", "grossa", scheda_titolare_squalificato, "squalificato"),
    ("infortunio_dubbio_titolare", "grossa", scheda_titolare_infortunio_dubbio, "infortunio"),
    ("disaccordo_ma_sicuro", "grossa", disaccordo_con_stato_sicuro, "dubbio"),
    ("confidenza_zero_ma_sicuro", "grossa", confidenza_zero_con_stato_sicuro, "dubbio"),
    ("titolare_senza_scheda", "grossa", togli_scheda_primo_titolare, "scheda"),
    ("confidenza_senza_link", "grossa", togli_link_da_scheda, "link"),
    ("link_javascript", "grossa", link_javascript, "link"),
    ("link_a_lega", "grossa", link_a_leghe_fantacalcio, "lega"),
    ("link_a_api_lega", "grossa", link_a_apileague, "lega"),
    ("data_illeggibile", "grossa", lambda r: r.update(prima_partita="sabato"), "prima_partita"),
    ("link_a_lega_con_punto_finale", "grossa", lambda r: _scheda_primo_titolare(r).update(link=["http://leghe.fantacalcio.it./x"]), "lega"),
    ("fonte_non_letta_di_una_lega", "grossa", lambda r: r.update(fonti_non_lette=["https://leghe.fantacalcio.it/x"]), "lega"),
    ("fonte_non_letta_javascript", "grossa", lambda r: r.update(fonti_non_lette=["javascript:alert(1)"]), "link"),
    ("esclusi_non_elenco", "grossa", lambda r: r.update(esclusi="nessuno"), "esclusi"),
    ("esclusi_con_null", "grossa", lambda r: r.update(esclusi=[None]), "esclusi"),
    ("differenza_non_testo", "grossa", lambda r: r.update(differenza_piu_grande=["x"]), "differenza"),
    ("rosa_mancante", "grossa", lambda r: r["formazioni"].pop("rosa"), "rosa"),
]


def f1_completa():
    q = richiesta_prova("f1")
    q["lega"] |= {"capitano": {"attivo": False}, "switch": "no"}
    return q


class TestControllo(unittest.TestCase):
    def test_risultati_validi_per_tutte_le_leghe(self):
        for m in ("pensionati", "grossa", "libera"):
            self.assertEqual(controlla(richiesta_prova(m), risultato_valido(m)), [], m)
        self.assertEqual(controlla(f1_completa(), risultato_valido("f1")), [])

    def test_casi_errati(self):
        for nome, modello, guasta, parola in CASI:
            with self.subTest(nome):
                r = risultato_valido(modello)
                guasta(r)
                errori = controlla(richiesta_prova(modello), r)
                self.assertTrue(any(parola in e.lower() for e in errori), f"{nome}: {errori}")

    def test_3_6_1_ammesso_solo_in_f1(self):
        self.assertEqual(controlla(f1_completa(), risultato_valido("f1", "3-6-1")), [])
        errori = controlla(richiesta_prova("grossa"), risultato_valido("grossa", "3-6-1"))
        self.assertTrue(any("modulo" in e for e in errori), errori)

    def test_switch_plus_ruolo_diverso_ammesso_se_modulo_valido(self):
        # 3-4-3 con un attaccante scambiato con un centrocampista diventa 3-5-2
        r = risultato_valido("pensionati")
        f = r["formazioni"]["rosa"]
        a = next(g for g in f["titolari"] if g["ruolo"] == "A")
        c = next(g for g in f["panchina"] if g["ruolo"] == "C")
        f["switch"] = {"titolare": a["nome"], "riserva": c["nome"]}
        self.assertEqual(controlla(richiesta_prova("pensionati"), r), [])

    def test_titolare_in_dubbio_dichiarato_e_ammesso(self):
        r = risultato_valido("grossa")
        r["formazioni"]["rosa"]["titolari"][0]["stato"] = "dubbio"
        disaccordo_con_stato_sicuro(r)
        self.assertEqual(controlla(richiesta_prova("grossa"), r), [])

    def test_rosa_presente_in_lega_libera_rifiutata(self):
        r = risultato_valido("libera")
        r["formazioni"]["rosa"] = r["formazioni"]["assoluta"]
        self.assertTrue(any("rosa" in e for e in controlla(richiesta_prova("libera"), r)))

    def test_chiave_ignora_accenti_e_punteggiatura(self):
        self.assertEqual(chiave("Martínez L.", "Inter"), chiave("martinez l", "INTER"))
        self.assertNotEqual(chiave("Thuram", "Inter"), chiave("Thuram", "Juventus"))


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "richiesta.json").write_text(json.dumps(richiesta_prova("grossa")), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def scrivi(self, risultato):
        testo = risultato if isinstance(risultato, str) else json.dumps(risultato)
        (self.dir / "risultato.json").write_text(testo, encoding="utf-8")

    def esegui(self):
        return subprocess.run([sys.executable, str(CONTROLLO), "richiesta.json", "risultato.json"],
                              cwd=self.dir, capture_output=True, text=True)

    def test_cli_valido_scrive_fatto_e_esce_zero(self):
        self.scrivi(risultato_valido("grossa"))
        p = self.esegui()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((self.dir / "FATTO").exists())

    def test_cli_al_terzo_fallimento_chiude_comunque(self):
        r = risultato_valido("grossa")
        r["formazioni"]["rosa"]["modulo"] = "3-6-1"
        self.scrivi(r)
        for n in (1, 2, 3):
            p = self.esegui()
            self.assertEqual(p.returncode, 1)
            self.assertIn("modulo", p.stdout)
            self.assertEqual((self.dir / "FATTO").exists(), n == 3, n)

    def test_cli_json_troncato_conta_come_tentativo(self):
        self.scrivi('{"giornata": 12, "formaz')
        p = self.esegui()
        self.assertEqual(p.returncode, 1)
        self.assertEqual((self.dir / "tentativi.txt").read_text().strip(), "1")
        self.assertFalse((self.dir / "FATTO").exists())



class TestRiferimentiSoloNomi(unittest.TestCase):
    def test_vice_oggetto_uguale_al_capitano_rifiutato(self):
        r = risultato_valido("grossa")
        f = r["formazioni"]["rosa"]
        cap = next(g for g in f["titolari"] if g["nome"] == f["capitano"])
        f["vice"] = {"nome": cap["nome"], "squadra": cap["squadra"]}
        errori = controlla(richiesta_prova("grossa"), r)
        self.assertTrue(any("vice" in e for e in errori), errori)

    def test_capitano_oggetto_rifiutato(self):
        r = risultato_valido("grossa")
        f = r["formazioni"]["rosa"]
        cap = next(g for g in f["titolari"] if g["nome"] == f["capitano"])
        f["capitano"] = {"nome": cap["nome"], "squadra": cap["squadra"]}
        self.assertTrue(any("capitano" in e for e in controlla(richiesta_prova("grossa"), r)))


class TestControllaFormazione(unittest.TestCase):
    def test_controlla_formazione_pubblica(self):
        lega, listone = lega_prova("grossa"), listone_prova()
        f = risultato_valido("grossa")["formazioni"]["rosa"]
        self.assertEqual(controlla_formazione(f, lega, listone), [])
        f["panchina"][-1] = dict(f["titolari"][-1])
        errori = controlla_formazione(f, lega, listone)
        self.assertTrue(any("doppione" in e for e in errori), errori)
        self.assertTrue(all(e.startswith("Formazione schierata:") for e in errori), errori)

    def test_controlla_formazione_fuori_rosa_e_ruoli_della_lega(self):
        lega, listone = lega_prova("grossa"), listone_prova()
        f = risultato_valido("grossa")["formazioni"]["assoluta"]
        self.assertTrue(any("non è nella rosa" in e for e in controlla_formazione(f, lega, listone)))
        f = risultato_valido("grossa")["formazioni"]["rosa"]
        d = next(g for g in f["titolari"] if g["ruolo"] == "D")
        lega["ruoli"] = {chiave(d["nome"], d["squadra"]): "C"}
        self.assertTrue(any("ruolo di" in e for e in controlla_formazione(f, lega, listone)))


if __name__ == "__main__":
    unittest.main()
