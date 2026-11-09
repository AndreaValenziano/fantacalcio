import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from consigliere import verifica
from consigliere.ricerca import crea_ricerca, stato_ricerca
from tests.aiuti import SQUADRE, lega_prova, listone_prova, risultato_valido

NOMI = {"ATA": "Atalanta", "BOL": "Bologna", "CAG": "Cagliari", "COM": "Como", "CRE": "Cremonese",
        "FIO": "Fiorentina", "GEN": "Genoa", "INT": "Inter", "JUV": "Juventus", "LAZ": "Lazio",
        "LEC": "Lecce", "MIL": "Milan", "NAP": "Napoli", "PAR": "Parma", "PIS": "Pisa", "ROM": "Roma",
        "SAS": "Sassuolo", "TOR": "Torino", "UDI": "Udinese", "VER": "Hellas Verona"}
FUSO = timezone(timedelta(hours=1))
SCADENZA = "2026-11-14T12:15:00+01:00"
IA = {"id": "claude", "nome": "Claude", "comando": "claude", "argomenti": ["{prompt}"], "avviso": None, "garantita": True}


def giocatore(id_, nome, squadra, ruolo, voto):
    return {"id": id_, "nome": nome, "squadra": squadra, "ruolo": ruolo, "voto": voto, "fv_pubblicato": voto,
            "ammonito": False, "espulso": False, "gol": 0, "gol_subiti": 0, "autogol": 0, "rigori_segnati": 0,
            "rigori_sbagliati": 0, "rigori_parati": 0, "assist": 0, "player_of_the_match": 0}


def voti_prova(squadre=SQUADRE) -> dict:
    """Pagina dei voti sintetica: i giocatori del listone di prova, più comparse SV per arrivare a 11 a squadra."""
    giocatori = []
    for i, g in enumerate(listone_prova()):
        if g["squadra"] in squadre:
            voto = 5.0 + (i * 7 % 11) * 0.5  # da 5 a 10, sparsi
            giocatori.append(giocatore(str(1000 + i), g["nome"], NOMI[g["squadra"]], g["ruolo"], voto))
    for s in squadre:
        for k in range(8):
            giocatori.append(giocatore(f"9{SQUADRE.index(s):02d}{k}", f"Comparsa {k}", NOMI[s], "C", None))
    date = {s: ("2026-11-14T12:30:00+01:00" if s == "ROM" else "2026-11-14T15:00:00+01:00") for s in squadre}
    return {"stagione": "2026-27", "giornata": 11, "mancanze": [], "giocatori": giocatori,
            "squadre": {NOMI[s]: {"slug": NOMI[s].lower().replace(" ", "-"), "data": date[s]} for s in squadre}}


def risultato_11(modello):
    r = risultato_valido(modello)
    r["giornata"] = 11
    return r


def consigliata_a_mano(risultato):
    return {"scelta": {"ricerca": "20261113-180000", "risultato": risultato, "fatto_il": "2026-11-13T18:00:00+01:00",
                       "sigillo": "integro"}, "dopo_scadenza": [], "senza_giornata": []}


class TestConsigliata(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def ricerca(self, risultato, fatta: datetime, modello="grossa"):
        c = crea_ricerca(self.base, lega_prova(modello), listone_prova(), IA, "sicuri", fatta - timedelta(minutes=30))
        (c / "risultato.json").write_text(json.dumps(risultato), encoding="utf-8")
        (c / "FATTO").write_text("valido", encoding="utf-8")
        os.utime(c / "FATTO", (fatta.timestamp(), fatta.timestamp()))
        stato_ricerca(c)  # come la pagina che interroga lo stato: sigilla
        return c

    def test_scadenza_dalla_prima_partita(self):
        self.assertEqual(verifica.scadenza(voti_prova(), lega_prova("pensionati")), "2026-11-14T12:15:00+01:00")
        self.assertEqual(verifica.scadenza(voti_prova(), lega_prova("grossa")), "2026-11-14T12:30:00+01:00")
        voti = voti_prova()
        for s in voti["squadre"].values():
            s["data"] = None
        self.assertIsNone(verifica.scadenza(voti, lega_prova("grossa")))

    def test_consigliata_prima_della_scadenza(self):
        prima = self.ricerca(risultato_11("grossa"), datetime(2026, 11, 13, 18, 0, tzinfo=FUSO))
        dopo = self.ricerca(risultato_11("grossa"), datetime(2026, 11, 14, 13, 0, tzinfo=FUSO))
        c = verifica.consigliata(self.base, "grossa", 11, SCADENZA)
        self.assertEqual(c["scelta"]["ricerca"], prima.name)
        self.assertEqual(c["scelta"]["sigillo"], "integro")
        self.assertEqual(c["dopo_scadenza"], [dopo.name])
        self.assertEqual(c["scelta"]["risultato"]["giornata"], 11)

    def test_consigliata_vince_la_piu_recente_prima_della_scadenza(self):
        self.ricerca(risultato_11("grossa"), datetime(2026, 11, 13, 10, 0, tzinfo=FUSO))
        recente = self.ricerca(risultato_11("grossa"), datetime(2026, 11, 14, 11, 0, tzinfo=FUSO))
        self.assertEqual(verifica.consigliata(self.base, "grossa", 11, SCADENZA)["scelta"]["ricerca"], recente.name)

    def test_consigliata_altra_giornata(self):
        self.ricerca(risultato_valido("grossa"), datetime(2026, 11, 13, 18, 0, tzinfo=FUSO))  # giornata 12
        c = verifica.consigliata(self.base, "grossa", 11, SCADENZA)
        self.assertIsNone(c["scelta"])
        self.assertEqual(c["dopo_scadenza"], [])

    def test_consigliata_senza_scadenza_nessuna_scelta(self):
        self.ricerca(risultato_11("grossa"), datetime(2026, 11, 13, 18, 0, tzinfo=FUSO))
        c = verifica.consigliata(self.base, "grossa", 11, None)
        self.assertIsNone(c["scelta"])
        self.assertIn("scadenza", c["motivo"])

    def test_sigillo_alterato(self):
        c = self.ricerca(risultato_11("grossa"), datetime(2026, 11, 13, 18, 0, tzinfo=FUSO))
        r = risultato_11("grossa")
        r["differenza_piu_grande"] = "Scritto dopo."
        (c / "risultato.json").write_text(json.dumps(r), encoding="utf-8")
        scelta = verifica.consigliata(self.base, "grossa", 11, SCADENZA)
        self.assertEqual(scelta["scelta"]["sigillo"], "alterato")
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(), scelta, None)
        self.assertEqual(dati["stato"], "PROVVISORIO")
        self.assertTrue(any("sigillo" in m for m in dati["motivi"]), dati["motivi"])

    def test_sigillo_assente(self):
        c = crea_ricerca(self.base, lega_prova("grossa"), listone_prova(), IA, "sicuri",
                         datetime(2026, 11, 13, 17, 0, tzinfo=FUSO))
        (c / "risultato.json").write_text(json.dumps(risultato_11("grossa")), encoding="utf-8")
        (c / "FATTO").write_text("valido", encoding="utf-8")
        t = datetime(2026, 11, 13, 18, 0, tzinfo=FUSO).timestamp()
        os.utime(c / "FATTO", (t, t))
        scelta = verifica.consigliata(self.base, "grossa", 11, SCADENZA)
        self.assertEqual(scelta["scelta"]["sigillo"], "assente")
        self.assertFalse((self.base / "registro.jsonl").exists())  # la verifica non sigilla a posteriori


class TestCollega(unittest.TestCase):
    def test_collega_omonimi_e_squadre(self):
        voti = {"giocatori": [giocatore("1", "Rossi", "Roma", "D", 6), giocatore("2", "Rossi", "Lazio", "D", 6),
                              giocatore("3", "Bianchi", "Hellas Verona", "C", 6),
                              giocatore("4", "N'Dicka", "Roma", "D", 6),
                              giocatore("5", "Neri", "Inter", "A", 6), giocatore("6", "Neri", "Inter", "A", 6)]}
        listone = [{"id": "9", "nome": "Verdi", "squadra": "Inter", "ruolo": "A"}]
        formazione = [{"nome": "Rossi", "squadra": "ROM", "ruolo": "D"},
                      {"nome": "Rossi", "squadra": "Lazio", "ruolo": "D"},
                      {"nome": "Rossi", "squadra": "", "ruolo": "D"},
                      {"nome": "Bianchi", "squadra": "Verona", "ruolo": "C"},
                      {"nome": "N'Dicka", "squadra": "ROM", "ruolo": "D"},
                      {"nome": "Neri", "squadra": "Inter", "ruolo": "A"},
                      {"nome": "Verdi", "squadra": "INT", "ruolo": "A"},
                      {"nome": "Gialli", "squadra": "Inter", "ruolo": "A"}]
        collegati, non = verifica.collega(formazione, voti, listone)
        self.assertEqual([(g["nome"], g["squadra"], g["id"]) for g in collegati],
                         [("Rossi", "ROM", "1"), ("Rossi", "Lazio", "2"), ("Bianchi", "Verona", "3"),
                          ("N'Dicka", "ROM", "4"), ("Verdi", "INT", "9")])
        self.assertEqual([(g["nome"], g["squadra"]) for g in non],
                         [("Rossi", ""), ("Neri", "Inter"), ("Gialli", "Inter")])
        self.assertTrue(all(g["motivo"] for g in non))

    def test_collega_per_id(self):
        voti = {"giocatori": [giocatore("7", "Rossi", "Roma", "D", 6)]}
        collegati, non = verifica.collega([{"id": "7", "nome": "Rossi Mario", "squadra": "?", "ruolo": "D"}], voti, [])
        self.assertEqual((collegati[0]["id"], non), ("7", []))


class TestCalcola(unittest.TestCase):
    def test_certificato(self):
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(),
                                consigliata_a_mano(risultato_11("grossa")), None,
                                meta_voti={"sha256": "abc", "ora": "2026-11-15T10:00:00+01:00", "origine": "scaricata"})
        self.assertEqual(dati["stato"], "CERTIFICATO", dati["motivi"])
        self.assertEqual(dati["voti"]["sha256"], "abc")
        self.assertEqual(dati["voti"]["mancanze"], [])
        self.assertEqual((dati["giornata"], dati["lega"]), (11, "grossa"))

    def test_regret_somma(self):
        lega = lega_prova("grossa")
        dati = verifica.calcola(lega, voti_prova(), listone_prova(), consigliata_a_mano(risultato_11("grossa")), None)
        m, rg = dati["misure"], dati["regret"]["consigliata"]
        parti = (rg["limite_rosa"], rg["selezione"], rg["schieramento"])
        self.assertAlmostEqual(sum(parti), rg["totale"])
        self.assertTrue(all(x >= 0 for x in parti), rg)
        self.assertAlmostEqual(rg["totale"], m["perfetta_assoluta"]["totale"] - m["consigliata"]["ottenuto"]["totale"])
        self.assertIsNotNone(m["consigliata"]["assoluta_ottenuto"])
        self.assertGreater(rg["totale"], 0)

    def test_libera_limite_rosa_zero(self):
        dati = verifica.calcola(lega_prova("libera"), voti_prova(), listone_prova(),
                                consigliata_a_mano(risultato_11("libera")), None)
        self.assertIsNone(dati["misure"]["perfetta_rosa"])
        self.assertIsNone(dati["misure"]["consigliata"]["assoluta_ottenuto"])
        self.assertEqual(dati["regret"]["consigliata"]["limite_rosa"], 0)

    def test_dati_incompleti(self):
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(SQUADRE[:3]), listone_prova(),
                                consigliata_a_mano(risultato_11("grossa")), None)
        self.assertEqual(dati["stato"], "DATI_INCOMPLETI")
        self.assertIsNotNone(dati["misure"]["perfetta_assoluta"])
        self.assertTrue(dati["voti"]["mancanze"])

    def test_senza_consigliata_provvisorio(self):
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(), None, None)
        self.assertEqual(dati["stato"], "PROVVISORIO")
        self.assertIsNone(dati["misure"]["consigliata"])

    def test_schierata_e_errori(self):
        lega, voti = lega_prova("grossa"), voti_prova()
        f = risultato_11("grossa")["formazioni"]["rosa"]
        sv = f["titolari"][1]  # un difensore SV: entra la riserva
        next(g for g in voti["giocatori"] if g["nome"] == sv["nome"])["voto"] = None
        dati = verifica.calcola(lega, voti, listone_prova(), None, f)
        self.assertIsNotNone(dati["misure"]["schierata"])
        rg = dati["regret"]["schierata"]
        self.assertAlmostEqual(rg["limite_rosa"] + rg["selezione"] + rg["schieramento"], rg["totale"])
        tipi = {e["tipo"] for e in dati["errori"] if e["formazione"] == "schierata"}
        self.assertIn("titolare_sv", tipi)
        self.assertIn("fuori_dai_18", tipi)
        testo = verifica.report_md(dati)
        self.assertIn("uno degli ottimi", testo)
        self.assertIn("PROVVISORIO", testo)

    def test_schierata_non_valida_provvisorio(self):
        f = risultato_11("grossa")["formazioni"]["rosa"]
        f["panchina"][-1] = dict(f["titolari"][-1])
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(),
                                consigliata_a_mano(risultato_11("grossa")), f)
        self.assertTrue(any("doppione" in m for m in dati["motivi"]), dati["motivi"])


class TestArchivio(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_versioni_non_sovrascritte(self):
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(),
                                consigliata_a_mano(risultato_11("grossa")), None)
        p1 = verifica.salva(self.base, "grossa", verifica.STAGIONE_CORRENTE, 11, dati)
        prima = (p1 / "verifica.json").read_bytes()
        p2 = verifica.salva(self.base, "grossa", verifica.STAGIONE_CORRENTE, 11, dati)
        self.assertEqual((p1.name, p2.name), ("v1", "v2"))
        self.assertEqual(p1.parent, self.base / "verifiche" / "grossa" / "2026-27" / "G11")
        self.assertEqual((p1 / "verifica.json").read_bytes(), prima)
        self.assertTrue((p2 / "report.md").read_text(encoding="utf-8").startswith("#"))
        v = verifica.versioni(self.base, "grossa", "2026-27", 11)
        self.assertEqual([x["k"] for x in v], [1, 2])
        self.assertEqual(v[0]["stato"], "CERTIFICATO")
        self.assertIsNotNone(v[0]["totali"]["consigliata"])
        self.assertEqual(verifica.versioni(self.base, "grossa", "2026-27", 12), [])
        with self.assertRaises(ValueError):
            verifica.salva(self.base, "../x", "2026-27", 11, dati)

    def test_schierata_versioni(self):
        self.assertIsNone(verifica.schierata(self.base, "grossa", "2026-27", 11))
        a = risultato_11("grossa")["formazioni"]["rosa"]
        b = dict(a, modulo="4-4-2")
        self.assertEqual(verifica.salva_schierata(self.base, "grossa", "2026-27", 11, a), 1)
        self.assertEqual(verifica.salva_schierata(self.base, "grossa", "2026-27", 11, b), 2)
        self.assertEqual(verifica.schierata(self.base, "grossa", "2026-27", 11)["modulo"], "4-4-2")
        cartella = self.base / "verifiche" / "grossa" / "2026-27" / "G11"
        self.assertEqual(json.loads((cartella / "schierata-v1.json").read_text(encoding="utf-8"))["modulo"], a["modulo"])


if __name__ == "__main__":
    unittest.main()
