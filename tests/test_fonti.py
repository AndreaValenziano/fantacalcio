import copy
import hashlib
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from consigliere import fonti
from consigliere.fonti import FonteNonAccessibile, Scaricatore, ammesso, url_voti
from consigliere.pagine import PaginaNonValida

DATI = Path(__file__).resolve().parent / "dati"
BASE_URL = "https://www.fantacalcio.it/"


class _Risposta:
    def __init__(self, corpo=b"ok", status=200):
        self.corpo, self.status = corpo, status

    def read(self):
        return self.corpo

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestUrl(unittest.TestCase):
    def test_url_ammessi(self):
        self.assertEqual(url_voti("2026-27", 11), BASE_URL + "voti-fantacalcio-serie-a/2026-27/11")
        for u in (url_voti("2026-27", 1), url_voti("2026-27", 38), fonti.URL_LISTONE, fonti.URL_PROBABILI):
            self.assertTrue(ammesso(u), u)
        for u in ("http://www.fantacalcio.it/quotazioni-fantacalcio",
                  "https://leghe.fantacalcio.it/pippo",
                  BASE_URL + "voti-fantacalcio-serie-a/2026-27/11?x=1",
                  BASE_URL + "voti-fantacalcio-serie-a/2026-27/39",
                  BASE_URL + "voti-fantacalcio-serie-a/2026-27/0",
                  BASE_URL + "voti-fantacalcio-serie-a/../../",
                  "https://example.com"):
            self.assertFalse(ammesso(u), u)

    def test_url_voti_non_valido(self):
        with self.assertRaises(ValueError):
            url_voti("2026", 1)
        with self.assertRaises(ValueError):
            url_voti("2026-27", 39)


class TestScaricatore(unittest.TestCase):
    def test_rifiuta_prima_di_aprire(self):
        finto = mock.Mock()
        with self.assertRaises(ValueError):
            Scaricatore(apri=finto).scarica("https://example.com")
        finto.assert_not_called()

    def test_pausa_e_user_agent(self):
        tempo = [100.0]
        dormite = []
        richieste = []

        def apri(req, timeout=None):
            richieste.append((req, timeout))
            return _Risposta(b"corpo")

        def dormi(s):
            dormite.append(s)
            tempo[0] += s

        sc = Scaricatore(apri=apri, orologio=lambda: tempo[0], dormi=dormi)
        self.assertEqual(sc.scarica(fonti.URL_LISTONE), b"corpo")
        self.assertEqual(dormite, [])
        tempo[0] += 1.0
        sc.scarica(fonti.URL_PROBABILI)
        self.assertEqual(len(dormite), 1)
        self.assertAlmostEqual(dormite[0], 2.0)
        req, timeout = richieste[1]
        self.assertEqual(req.get_header("User-agent"), "ConsiglioFormazione/1")
        self.assertEqual(timeout, 30)

    def test_errore_http(self):
        def apri(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
        with self.assertRaises(FonteNonAccessibile) as c:
            Scaricatore(apri=apri, dormi=lambda s: None).scarica(fonti.URL_LISTONE)
        self.assertIn("403", str(c.exception))
        self.assertIn("browser", str(c.exception))

    def test_errore_di_rete_e_timeout(self):
        for exc in (urllib.error.URLError("giù"), TimeoutError("lento")):
            def apri(req, timeout=None, exc=exc):
                raise exc
            with self.assertRaises(FonteNonAccessibile):
                Scaricatore(apri=apri, dormi=lambda s: None).scarica(fonti.URL_LISTONE)

    def test_stato_non_200(self):
        sc = Scaricatore(apri=lambda r, timeout=None: _Risposta(b"x", 204), dormi=lambda s: None)
        with self.assertRaises(FonteNonAccessibile):
            sc.scarica(fonti.URL_LISTONE)


class TestArchivio(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.base = Path(self._t.name)
        self.addCleanup(self._t.cleanup)

    def test_archivia_sha_e_nessuna_sovrascrittura(self):
        a = fonti.archivia(self.base, "voti", "2026-27-11", b"uno", "u", "scaricata", {"giocatori": 1})
        with mock.patch.object(fonti, "_marca", return_value="20261109-100000"):
            b = fonti.archivia(self.base, "voti", "2026-27-11", b"due", "u", "caricata_a_mano", {})
            c = fonti.archivia(self.base, "voti", "2026-27-11", b"tre", "u", "caricata_a_mano", {})
        self.assertEqual(a["sha256"], hashlib.sha256(b"uno").hexdigest())
        self.assertEqual(len({a["file"], b["file"], c["file"]}), 3)
        self.assertTrue(c["file"].endswith("-2.html") or b["file"].endswith("-2.html"))
        cartella = self.base / "fonti" / "voti" / "2026-27-11"
        self.assertEqual((cartella / a["file"]).read_bytes(), b"uno")
        self.assertEqual(len(list(cartella.glob("*.html"))), 3)
        meta = json.loads((cartella / a["file"].replace(".html", ".json")).read_text("utf-8"))
        self.assertEqual(meta, a)
        self.assertEqual(meta["versione_lettore"], "1")
        self.assertEqual(meta["origine"], "scaricata")

    def test_collisione_stesso_secondo(self):
        with mock.patch.object(fonti, "_marca", return_value="20261109-100000"):
            a = fonti.archivia(self.base, "listone", "listone", b"1", "u", "scaricata", {})
            b = fonti.archivia(self.base, "listone", "listone", b"2", "u", "scaricata", {})
            c = fonti.archivia(self.base, "listone", "listone", b"3", "u", "scaricata", {})
        self.assertEqual([a["file"], b["file"], c["file"]],
                         ["20261109-100000.html", "20261109-100000-2.html", "20261109-100000-3.html"])

    def test_ultima_e_copie(self):
        self.assertIsNone(fonti.ultima(self.base, "voti", "x"))
        self.assertEqual(fonti.copie(self.base, "voti", "x"), [])
        with mock.patch.object(fonti, "_marca", side_effect=["20261109-100000", "20261109-110000"]):
            fonti.archivia(self.base, "voti", "x", b"vecchia", "u", "scaricata", {})
            fonti.archivia(self.base, "voti", "x", "nuova è".encode(), "u", "scaricata", {})
        meta, html = fonti.ultima(self.base, "voti", "x")
        self.assertEqual(html, "nuova è")
        self.assertEqual(meta["file"], "20261109-110000.html")
        self.assertEqual([m["file"] for m in fonti.copie(self.base, "voti", "x")],
                         ["20261109-110000.html", "20261109-100000.html"])


class TestAcquisizione(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.base = Path(self._t.name)
        self.addCleanup(self._t.cleanup)
        self.html = (DATI / "voti_ridotta.html").read_bytes()

    def test_acquisisci_manuale_ok(self):
        r = fonti.acquisisci_voti(self.base, "2026-27", 11, self.html, None)
        self.assertEqual(r["meta"]["origine"], "caricata_a_mano")
        self.assertEqual(r["meta"]["riepilogo"]["giocatori"], len(r["voti"]["giocatori"]))
        self.assertEqual(r["differenze"], [])

    def test_acquisisci_scaricando(self):
        sc = Scaricatore(apri=lambda r, timeout=None: _Risposta(self.html), dormi=lambda s: None)
        r = fonti.acquisisci_voti(self.base, "2026-27", 11, None, sc)
        self.assertEqual(r["meta"]["origine"], "scaricata")
        self.assertEqual(r["meta"]["url"], url_voti("2026-27", 11))

    def test_acquisisci_manuale_giornata_sbagliata(self):
        with self.assertRaises(PaginaNonValida):
            fonti.acquisisci_voti(self.base, "2026-27", 10, self.html, None)
        self.assertFalse((self.base / "fonti").exists() and any((self.base / "fonti").rglob("*.html")))

    def test_acquisisci_non_utf8(self):
        with self.assertRaises(PaginaNonValida) as c:
            fonti.acquisisci_voti(self.base, "2026-27", 11, b"\xff\xfe\x00abc", None)
        self.assertIn("non è una pagina salvata in UTF-8", str(c.exception))
        self.assertFalse((self.base / "fonti").exists() and any((self.base / "fonti").rglob("*")))

    def test_seconda_copia_con_differenze(self):
        fonti.acquisisci_voti(self.base, "2026-27", 11, self.html, None)
        modificata = self.html.replace(b"</body>", b"</body>")
        r = fonti.acquisisci_voti(self.base, "2026-27", 11, modificata, None)
        self.assertEqual(r["differenze"], [])
        self.assertEqual(len(fonti.copie(self.base, "voti", "2026-27-11")), 2)

    def test_acquisisci_listone(self):
        html = (DATI / "quotazioni_ridotta.html").read_bytes()
        r = fonti.acquisisci_listone(self.base, html, None)
        self.assertTrue(r["giocatori"])
        self.assertEqual(r["meta"]["riepilogo"]["giocatori"], len(r["giocatori"]))
        self.assertEqual(fonti.ultima(self.base, "listone", "listone")[0]["file"], r["meta"]["file"])


class TestDifferenze(unittest.TestCase):
    def test_differenze(self):
        prima = {"giocatori": [
            {"id": "1", "nome": "A", "voto": 6.0, "fv_pubblicato": 6.0, "gol": 0},
            {"id": "2", "nome": "B", "voto": 7.0, "fv_pubblicato": 7.0, "gol": 0}]}
        dopo = copy.deepcopy(prima)
        dopo["giocatori"][0]["voto"] = 6.5
        dopo["giocatori"].append({"id": "3", "nome": "C", "voto": 5.0, "fv_pubblicato": 5.0, "gol": 0})
        d = fonti.differenze_voti(prima, dopo)
        self.assertEqual(len(d), 2)
        self.assertIn({"id": "1", "nome": "A", "campo": "voto", "prima": 6.0, "dopo": 6.5}, d)
        self.assertIn({"id": "3", "nome": "C", "campo": "presenza", "prima": "assente", "dopo": "presente"}, d)

    def test_scomparso(self):
        prima = {"giocatori": [{"id": "1", "nome": "A", "voto": 6.0}]}
        d = fonti.differenze_voti(prima, {"giocatori": []})
        self.assertEqual(d, [{"id": "1", "nome": "A", "campo": "presenza", "prima": "presente", "dopo": "assente"}])


if __name__ == "__main__":
    unittest.main()
