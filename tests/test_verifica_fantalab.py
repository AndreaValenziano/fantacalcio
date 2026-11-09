import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from consigliere import fonti, pagine, verifica_fantalab as vf

RADICE = Path(__file__).resolve().parent.parent
FANTALAB = RADICE / "fantalab"
DATI = Path(__file__).parent / "dati"
VERI = {g: DATI / f"voti_vero_2026-27_{g}.html" for g in (10, 11)}


def g(id_, nome, squadra, ruolo="C"):
    return {"id": id_, "nome": nome, "squadra": squadra, "ruolo": ruolo, "voto": 6.0}


class TestAbbina(unittest.TestCase):
    VOTI = {"giocatori": [g("1", "Wesley", "Roma", "D"), g("2", "Wesley", "Flamengo", "D"), g("3", "Maignan", "Milan", "P"),
                          g("4", "Miranda J.", "Bologna", "D"), g("5", "Mora", "Roma"), g("6", "Morata", "Milan", "A"),
                          g("7", "Mora", "Bologna")]}

    def test_con_squadra(self):
        self.assertEqual([x["id"] for x in vf.abbina_fantalab("wesley_roma", self.VOTI)], ["1"])

    def test_senza_squadra(self):
        self.assertEqual([x["id"] for x in vf.abbina_fantalab("maignan", self.VOTI)], ["3"])
        self.assertEqual([x["id"] for x in vf.abbina_fantalab("miranda", self.VOTI)], ["4"])

    def test_ambiguo_due_candidati(self):
        self.assertEqual(sorted(x["id"] for x in vf.abbina_fantalab("wesley", self.VOTI)), ["1", "2"])
        self.assertEqual(sorted(x["id"] for x in vf.abbina_fantalab("mora", self.VOTI)), ["5", "7"])  # esatti, non Morata

    def test_assente(self):
        self.assertEqual(vf.abbina_fantalab("pippo", self.VOTI), [])


class TestFormazione(unittest.TestCase):
    def test_dalla_vera_previsione(self):
        prev = json.loads((FANTALAB / "stagioni/2026-27/G11/previsione_macchina.json").read_text(encoding="utf-8"))
        slugs = [s for r in "PDCA" for s in prev["titolari"][r] + prev["panchina"][r]]
        per_id = {str(i): g(str(i), f"Nome{i}", "Roma", r) for i, (s, r) in enumerate(
            (s, r) for r in "PDCA" for s in prev["titolari"][r] + prev["panchina"][r])}
        abb = {s: str(i) for i, s in enumerate(slugs)}
        f = vf.formazione_fantalab(prev, abb, per_id)
        self.assertEqual(len(f["titolari"]), 11)
        self.assertEqual(len(f["panchina"]), 7)
        self.assertEqual([x["ruolo"] for x in f["titolari"]], list("PDDDDCCCAAA"))
        self.assertEqual(f["capitano"], {"nome": per_id[abb["malen"]]["nome"], "squadra": "Roma"})
        self.assertEqual(f["vice"]["nome"], per_id[abb["calo"]]["nome"])

    def test_non_abbinato_resta_per_slug(self):
        prev = {"capitano": "x", "vicecapitano": "y", "titolari": {"P": ["x"]}, "panchina": {"P": ["y"]}}
        f = vf.formazione_fantalab(prev, {}, {})
        self.assertIsNone(f["titolari"][0].get("id"))
        self.assertEqual(f["titolari"][0]["nome"], "x")


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.fl = self.dir / "fantalab"
        shutil.copytree(FANTALAB, self.fl)
        self.base = self.dir / "base"

    def tearDown(self):
        self._tmp.cleanup()

    def impronte(self):
        return {str(p.relative_to(self.fl)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(self.fl.rglob("*")) if p.is_file()}

    class Scaricatore:
        def __init__(self, html):
            self.html, self.urls = html, []

        def scarica(self, url):
            self.urls.append(url)
            return self.html

    def esegui(self, giornata, risposte, html=None):
        domande = []

        def inp(testo=""):
            domande.append(testo)
            return risposte.pop(0) if risposte else ""
        scar = self.Scaricatore(html or (DATI / "voti_ridotta.html").read_bytes())
        out = []
        rc = vf.main(["--fantalab", str(self.fl), "--giornata", str(giornata), "--cartella", str(self.base)],
                     input_fn=inp, scaricatore=scar, out=out.append)
        return rc, domande, scar, out

    def test_non_scrive_in_fantalab(self):
        prima = self.impronte()
        rc, _, _, _ = self.esegui(11, ["s"])
        self.assertEqual(rc, 0)
        self.assertEqual(prima, self.impronte())

    def test_g11_salva_report_provvisorio_con_sha(self):
        rc, domande, scar, _ = self.esegui(11, ["s"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(scar.urls), 1)
        v1 = self.base / "verifiche/fantalab/2026-27/G11/v1"
        dati = json.loads((v1 / "verifica.json").read_text(encoding="utf-8"))
        self.assertIn(dati["stato"], ("PROVVISORIO", "DATI_INCOMPLETI"))  # pagina ridotta: voti incompleti
        self.assertIn("previsione storica FantaLab (congelata in git), non sigillata dal registro", dati["motivi"])
        sha = hashlib.sha256((self.fl / "stagioni/2026-27/G11/previsione_macchina.json").read_bytes()).hexdigest()
        self.assertEqual(dati["ricerca"]["sha256_risultato"], sha)
        self.assertIn(sha, (v1 / "report.md").read_text(encoding="utf-8"))

    def test_benchmark_letto_dal_file(self):
        testo = (FANTALAB / "stagioni/2026-27/G10/BENCHMARK_PROVVISORIO.md").read_text(encoding="utf-8")
        righe, totale = vf._benchmark(testo)
        self.assertEqual(len(righe), 11)
        self.assertEqual(totale, 125.0)
        self.assertIn("Moreira", " ".join(righe))

    def test_confronto_con_125(self):
        self.assertIn("confermato", vf._confronto(125.0, 125.0))
        self.assertIn("superato", vf._confronto(126.5, 125.0))
        self.assertIn("non e' raggiunto", vf._confronto(120.0, 125.0))

    def test_giornata_senza_dati(self):
        rc, _, _, _ = self.esegui(12, [])
        self.assertNotEqual(rc, 0)

    def test_rifiuta_scaricamento(self):
        rc, _, scar, _ = self.esegui(11, ["n"])
        self.assertNotEqual(rc, 0)
        self.assertEqual(scar.urls, [])

    def test_ambiguo_chiesto_e_salvato(self):
        voti = {"giocatori": [g("1", "Wesley", "Roma", "D"), g("2", "Wesley", "Flamengo", "D")]}
        rig = vf.risolvi(["wesley"], voti, self.base / "fantalab" / "abbinamenti.json", lambda t="": "2", lambda *_: None)
        self.assertEqual(rig, {"wesley": "2"})
        self.assertEqual(json.loads((self.base / "fantalab/abbinamenti.json").read_text()), {"wesley": "2"})
        # seconda volta: niente domanda
        def mai(t=""):
            raise AssertionError("non doveva chiedere")
        self.assertEqual(vf.risolvi(["wesley"], voti, self.base / "fantalab" / "abbinamenti.json", mai, lambda *_: None),
                         {"wesley": "2"})

    def test_base_dentro_fantalab_rifiutata(self):
        rc = vf.main(["--fantalab", str(self.fl), "--giornata", "11", "--cartella", str(self.fl / "x")],
                     input_fn=lambda t="": "s", scaricatore=None, out=lambda *_: None)
        self.assertNotEqual(rc, 0)

    def lancia(self, base, risposte=("s",)):
        r = list(risposte)
        return vf.main(["--fantalab", str(self.fl), "--giornata", "11", "--cartella", str(base)],
                       input_fn=lambda t="": r.pop(0) if r else "",
                       scaricatore=self.Scaricatore((DATI / "voti_ridotta.html").read_bytes()), out=lambda *_: None)

    def test_base_genitore_di_fantalab_non_scrive_in_fantalab(self):
        prima = self.impronte()
        self.lancia(self.dir)  # self.dir contiene fantalab/ come figlio diretto
        self.assertEqual(prima, self.impronte())

    def test_base_con_fantalab_collegamento_simbolico(self):
        self.base.mkdir()
        (self.base / "fantalab").symlink_to(self.fl, target_is_directory=True)
        prima = self.impronte()
        self.lancia(self.base)
        self.assertEqual(prima, self.impronte())

    def test_sottocartelle_collegate_dentro_fantalab_rifiutate(self):
        for nome in ("verifiche", "fonti", "abbinamenti"):
            with self.subTest(nome):
                base = self.dir / f"b-{nome}"
                base.mkdir()
                (base / nome).symlink_to(self.fl, target_is_directory=True)
                prima = self.impronte()
                self.assertEqual(self.lancia(base), 2)
                self.assertEqual(prima, self.impronte())

    def test_input_terminato(self):
        def eof(t=""):
            raise EOFError
        rc = vf.main(["--fantalab", str(self.fl), "--giornata", "11", "--cartella", str(self.base)],
                     input_fn=eof, scaricatore=None, out=lambda *_: None)
        self.assertEqual(rc, 1)

    def test_previsione_non_valida(self):
        (self.fl / "stagioni/2026-27/G11/previsione_macchina.json").write_text('{"titolari": {}}', encoding="utf-8")
        msgs = []
        rc = vf.main(["--fantalab", str(self.fl), "--giornata", "11", "--cartella", str(self.base)],
                     input_fn=lambda t="": "s", scaricatore=self.Scaricatore((DATI / "voti_ridotta.html").read_bytes()),
                     out=msgs.append)
        self.assertEqual(rc, 1)
        self.assertTrue(any("non valida" in m for m in msgs))


@unittest.skipUnless(VERI[10].exists() and VERI[11].exists(), "pagine vere dei voti assenti")
class TestVere(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        for gn, p in VERI.items():
            fonti.acquisisci_voti(self.base, "2026-27", gn, p.read_bytes(), None)

    def tearDown(self):
        self._tmp.cleanup()

    def test_g10_e_g11(self):
        for gn in (10, 11):
            out = []
            rc = vf.main(["--fantalab", str(FANTALAB), "--giornata", str(gn), "--cartella", str(self.base)],
                         input_fn=lambda t="": "", scaricatore=None, out=out.append)
            self.assertEqual(rc, 0)
            dati = json.loads(next((self.base / f"verifiche/fantalab/2026-27/G{gn}/v1").glob("verifica.json")).read_text())
            self.assertIsNotNone(dati["misure"]["perfetta_assoluta"])
            if gn == 11:
                self.assertEqual(dati["stato"], "PROVVISORIO")
                self.assertIn(vf.MOTIVO_STORICA, dati["motivi"])
                self.assertEqual(dati["misure"]["consigliata"]["non_collegati"], [])
        rep = (self.base / "verifiche/fantalab/2026-27/G10/v1/report.md").read_text(encoding="utf-8")
        self.assertIn("125", rep)
