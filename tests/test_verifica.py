import json
import os
import tempfile
import threading
import unittest
from unittest import mock
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
# Le ricerche dei test si sigillano adesso: date lontane nel futuro perché il sigillo sia prima della scadenza.
ANNO = 2036
SCADENZA_FUTURA = f"{ANNO}-11-14T12:15:00+01:00"
IA = {"id": "claude", "nome": "Claude", "comando": "claude", "argomenti": ["{prompt}"], "avviso": None, "garantita": True}


def giocatore(id_, nome, squadra, ruolo, voto):
    return {"id": id_, "nome": nome, "squadra": squadra, "ruolo": ruolo, "voto": voto, "fv_pubblicato": voto,
            "ammonito": False, "espulso": False, "gol": 0, "gol_subiti": 0, "autogol": 0, "rigori_segnati": 0,
            "rigori_sbagliati": 0, "rigori_parati": 0, "assist": 0, "player_of_the_match": 0}


def voti_prova(squadre=SQUADRE) -> dict:
    """Pagina dei voti sintetica: i giocatori del listone di prova, più comparse a voto basso (4) per arrivare
    ad almeno 11 giocatori con voto a squadra."""
    giocatori = []
    for i, g in enumerate(listone_prova()):
        if g["squadra"] in squadre:
            voto = 5.0 + (i * 7 % 11) * 0.5  # da 5 a 10, sparsi
            giocatori.append(giocatore(str(1000 + i), g["nome"], NOMI[g["squadra"]], g["ruolo"], voto))
    for s in squadre:
        for k in range(8):
            giocatori.append(giocatore(f"9{SQUADRE.index(s):02d}{k}", f"Comparsa {k}", NOMI[s], "C", 4.0))
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
        for nome in ("FATTO", "risultato.json"):
            os.utime(c / nome, (fatta.timestamp(), fatta.timestamp()))
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
        prima = self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO))
        dopo = self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 14, 13, 0, tzinfo=FUSO))
        c = verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)
        self.assertEqual(c["scelta"]["ricerca"], prima.name)
        self.assertEqual(c["scelta"]["sigillo"], "integro")
        self.assertEqual(c["dopo_scadenza"], [dopo.name])
        self.assertEqual(c["scelta"]["risultato"]["giornata"], 11)

    def test_consigliata_vince_la_piu_recente_prima_della_scadenza(self):
        self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 13, 10, 0, tzinfo=FUSO))
        recente = self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 14, 11, 0, tzinfo=FUSO))
        self.assertEqual(verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)["scelta"]["ricerca"], recente.name)

    def test_consigliata_altra_giornata(self):
        self.ricerca(risultato_valido("grossa"), datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO))  # giornata 12
        c = verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)
        self.assertIsNone(c["scelta"])
        self.assertEqual(c["dopo_scadenza"], [])

    def test_consigliata_senza_scadenza_nessuna_scelta(self):
        self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO))
        c = verifica.consigliata(self.base, "grossa", 11, None)
        self.assertIsNone(c["scelta"])
        self.assertIn("scadenza", c["motivo"])

    def test_sigillo_alterato(self):
        c = self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO))
        r = risultato_11("grossa")
        r["differenza_piu_grande"] = "Scritto dopo."
        (c / "risultato.json").write_text(json.dumps(r), encoding="utf-8")
        scelta = verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)
        self.assertEqual(scelta["scelta"]["sigillo"], "alterato")
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(), scelta, None)
        self.assertEqual(dati["stato"], "PROVVISORIO")
        self.assertTrue(any("sigillo" in m for m in dati["motivi"]), dati["motivi"])

    def test_sigillo_assente(self):
        c = crea_ricerca(self.base, lega_prova("grossa"), listone_prova(), IA, "sicuri",
                         datetime(ANNO, 11, 13, 17, 0, tzinfo=FUSO))
        (c / "risultato.json").write_text(json.dumps(risultato_11("grossa")), encoding="utf-8")
        (c / "FATTO").write_text("valido", encoding="utf-8")
        t = datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO).timestamp()
        os.utime(c / "FATTO", (t, t))
        scelta = verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)
        self.assertEqual(scelta["scelta"]["sigillo"], "assente")
        self.assertFalse((self.base / "registro.jsonl").exists())  # la verifica non sigilla a posteriori


    def test_scenario_a_fatto_spostato_indietro_dopo_il_sigillo(self):
        c = self.ricerca(risultato_11("grossa"), datetime(ANNO, 11, 14, 13, 0, tzinfo=FUSO))  # dopo la scadenza
        prima = datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO).timestamp()
        for nome in ("FATTO", "risultato.json"):
            os.utime(c / nome, (prima, prima))  # ora dei file spostata prima della scadenza
        esito = verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)
        self.assertIsNone(esito["scelta"])
        self.assertEqual(esito["dopo_scadenza"], [c.name])

    def test_scenario_b_chiusa_prima_risultato_dopo(self):
        c = crea_ricerca(self.base, lega_prova("grossa"), listone_prova(), IA, "sicuri",
                         datetime(ANNO, 11, 13, 17, 0, tzinfo=FUSO))
        (c / "CHIUSA").write_text("chiusa dalla pagina", encoding="utf-8")
        (c / "risultato.json").write_text(json.dumps(risultato_11("grossa")), encoding="utf-8")
        chiusa, scritto = (datetime(ANNO, 11, 13, 18, 0, tzinfo=FUSO).timestamp(),
                           datetime(ANNO, 11, 14, 13, 0, tzinfo=FUSO).timestamp())
        os.utime(c / "CHIUSA", (chiusa, chiusa))
        os.utime(c / "risultato.json", (scritto, scritto))
        stato_ricerca(c)  # sigillata più tardi, per esempio aprendo l'elenco delle ricerche
        esito = verifica.consigliata(self.base, "grossa", 11, SCADENZA_FUTURA)
        self.assertIsNone(esito["scelta"])
        self.assertEqual(esito["dopo_scadenza"], [c.name])

    def test_sigillo_tardivo(self):
        # conclusa (secondo i file) nel 2020, sigillata adesso: dopo la scadenza del 2021
        c = self.ricerca(risultato_11("grossa"), datetime(2020, 11, 13, 18, 0, tzinfo=FUSO))
        scelta = verifica.consigliata(self.base, "grossa", 11, "2021-01-01T00:00:00+01:00")
        self.assertEqual((scelta["scelta"]["ricerca"], scelta["scelta"]["sigillo"]), (c.name, "tardivo"))
        dati = verifica.calcola(lega_prova("grossa"), voti_prova(), listone_prova(), scelta, None)
        self.assertEqual(dati["stato"], "PROVVISORIO")
        self.assertIn("sigillo apposto dopo la scadenza", dati["motivi"])

    def test_sigillo_concorrente_una_riga(self):
        c = crea_ricerca(self.base, lega_prova("grossa"), listone_prova(), IA, "sicuri",
                         datetime(ANNO, 11, 13, 17, 0, tzinfo=FUSO))
        (c / "risultato.json").write_text(json.dumps(risultato_11("grossa")), encoding="utf-8")
        (c / "FATTO").write_text("valido", encoding="utf-8")
        fili = [threading.Thread(target=stato_ricerca, args=(c,)) for _ in range(8)]
        for f in fili:
            f.start()
        for f in fili:
            f.join()
        self.assertEqual(len((self.base / "registro.jsonl").read_text(encoding="utf-8").splitlines()), 1)


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


    def test_formazione_da_omonimi_capitano_vice_switch(self):
        f = {"modulo": "4-3-3",
             "titolari": [{"nome": "Rossi", "squadra": "Roma", "ruolo": "C"},
                          {"nome": "Rossi", "squadra": "Lazio", "ruolo": "C"},
                          {"nome": "Bianchi", "squadra": "Inter", "ruolo": "A"}],
             "panchina": [{"nome": "Rossi", "squadra": "Milan", "ruolo": "C"}],
             "capitano": {"nome": "Rossi", "squadra": "Lazio"}, "vice": "Rossi",
             "switch": {"titolare": {"nome": "Rossi", "squadra": "Roma"}, "riserva": "Rossi"}}
        collegati = [dict(f["titolari"][0], id="1"), dict(f["titolari"][1], id="2"),
                     dict(f["titolari"][2], id="3"), dict(f["panchina"][0], id="4")]
        r = verifica.formazione_da(f, collegati)
        self.assertEqual(r["capitano"], "2")
        self.assertIsNone(r["vice"])  # "Rossi" è ambiguo tra i titolari: non si sceglie
        self.assertEqual(r["switch"], {"titolare": "1", "riserva": "4"})  # unico Rossi in panchina
        self.assertEqual(verifica.formazione_da(dict(f, capitano="Bianchi"), collegati)["capitano"], "3")


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


    def test_migliore_tra_18_con_i_ruoli_delle_perfette(self):
        from consigliere.controllo import chiave
        lega, voti = lega_prova("libera"), voti_prova()
        r = risultato_11("libera")
        f = r["formazioni"]["assoluta"]
        x = next(g for g in f["panchina"] if g["ruolo"] == "D")
        lega["ruoli"] = {chiave(x["nome"], x["squadra"]): "C"}  # correzione della lega: D -> C
        x["ruolo"] = "A"  # ruolo dichiarato diverso: non deve contare per il migliore tra i 18
        pagina = next(g for g in voti["giocatori"] if g["nome"] == x["nome"])
        pagina["voto"] = pagina["fv_pubblicato"] = 10.0
        dati = verifica.calcola(lega, voti, listone_prova(), consigliata_a_mano(r), None)
        m = dati["misure"]
        ruoli = {g["nome"]: g["ruolo"] for p in (m["perfetta_assoluta"], m["consigliata"]["migliore_tra_18"])
                 for g in p["giocatori"]}
        self.assertEqual(ruoli[x["nome"]], "C")
        ottenuto = {g["nome"]: g["ruolo"] for g in m["consigliata"]["ottenuto"]["giocatori"]}
        self.assertEqual(ottenuto[x["nome"]], "C")  # anche l'ottenuto usa il ruolo corretto, non quello dichiarato
        rg = dati["regret"]["consigliata"]
        self.assertGreaterEqual(rg["selezione"], 0)
        self.assertGreaterEqual(rg["schieramento"], 0)
        self.assertAlmostEqual(rg["limite_rosa"] + rg["selezione"] + rg["schieramento"], rg["totale"])


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

    def test_schierata_scrittura_fallita_e_file_illeggibile(self):
        a = risultato_11("grossa")["formazioni"]["rosa"]
        verifica.salva_schierata(self.base, "grossa", "2026-27", 11, a)
        cartella = self.base / "verifiche" / "grossa" / "2026-27" / "G11"
        with mock.patch("consigliere.verifica.scrivi_json", side_effect=OSError("disco pieno")):
            with self.assertRaises(OSError):
                verifica.salva_schierata(self.base, "grossa", "2026-27", 11, dict(a, modulo="4-4-2"))
        self.assertFalse((cartella / "schierata-v2.json").exists())
        (cartella / "schierata-v2.json").write_text('{"modulo": "4-4', encoding="utf-8")  # troncata
        self.assertEqual(verifica.schierata(self.base, "grossa", "2026-27", 11)["modulo"], a["modulo"])


if __name__ == "__main__":
    unittest.main()
