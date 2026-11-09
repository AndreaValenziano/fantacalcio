import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from consigliere.archivio import Archivio
from consigliere.server import crea_server
from tests.aiuti import COMPOSIZIONE, crea_xlsx, listone_prova, risultato_valido

IA_FINTE = [{"id": "claude", "nome": "Claude", "comando": "claude", "argomenti": ["{prompt}"], "avviso": None,
             "garantita": True, "disponibile": True},
            {"id": "gemini", "nome": "Gemini", "comando": "gemini", "argomenti": ["{prompt}"], "avviso": "x",
             "garantita": True, "disponibile": False}]


def xlsx_prova(giocatori=None):
    righe = [["R", "Nome", "Squadra"]] + [[g["ruolo"], g["nome"], g["squadra"]] for g in giocatori or listone_prova()]
    return crea_xlsx({"Tutti": righe})


class TestServer(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.avvii = 0

        def avvia(script, sistema):
            self.avvii += 1

        p = mock.patch("consigliere.server.carica_ia", return_value=[dict(x) for x in IA_FINTE])
        p.start()
        self.addCleanup(p.stop)
        self.srv = crea_server(self.base, porta=0, avvia=avvia)
        self.porta = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self._tmp.cleanup()

    def chiama(self, metodo, percorso, corpo=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=5)
        h = dict(headers or {})
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo).encode()
            h.setdefault("Content-Type", "application/json")
        c.request(metodo, percorso, body=corpo, headers=h)
        r = c.getresponse()
        r.dati = r.read()
        c.close()
        return r

    def json(self, r):
        return json.loads(r.dati)

    def prepara(self, modello="grossa", avviso=True, listone=True, rosa=True):
        if avviso:
            self.assertEqual(self.chiama("POST", "/api/avviso").status, 200)
        if listone:
            self.assertEqual(self.chiama("POST", "/api/listone", xlsx_prova()).status, 200)
        lega = self.json(self.chiama("POST", "/api/leghe", {"modello": modello, "nome": "Prova"}))
        if rosa:
            per = {r: [g for g in listone_prova() if g["ruolo"] == r] for r in "PDCA"}
            lega["rosa"] = [g for r, n in COMPOSIZIONE.items() for g in per[r][:n]]
            self.assertEqual(self.chiama("PUT", f"/api/leghe/{lega['id']}", lega).status, 200)
        return lega

    def post_ricerca(self, lega_id="prova", ia="claude"):
        return self.chiama("POST", "/api/ricerche", {"lega": lega_id, "ia": ia, "stile": "sicuri"})

    def test_ascolta_solo_in_locale(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_stato_iniziale(self):
        s = self.json(self.chiama("GET", "/api/stato"))
        self.assertFalse(s["avviso_accettato"])
        self.assertIsNone(s["listone"])
        self.assertEqual(s["leghe"], [])
        self.assertEqual({m["id"] for m in s["modelli"]}, {"pensionati", "grossa", "f1", "libera"})
        self.assertEqual([i["id"] for i in s["ia"]], ["claude", "gemini"])

    def test_ricerca_bloccata_senza_avviso(self):
        self.prepara(avviso=False)
        r = self.post_ricerca()
        self.assertEqual(r.status, 409)
        self.assertIn("avviso", self.json(r)["errore"])

    def test_ricerca_bloccata_senza_listone(self):
        self.prepara(listone=False, rosa=False)
        r = self.post_ricerca()
        self.assertEqual(r.status, 409)
        self.assertIn("listone", self.json(r)["errore"])

    def test_ricerca_bloccata_se_mancano_regole(self):
        self.prepara("f1")
        r = self.post_ricerca()
        self.assertEqual(r.status, 409)
        self.assertIn("capitano", self.json(r)["errore"])

    def test_ricerca_bloccata_con_rosa_vuota(self):
        self.prepara(rosa=False)
        r = self.post_ricerca()
        self.assertEqual(r.status, 409)
        self.assertIn("rosa", self.json(r)["errore"])

    def test_ia_non_installata_spiega_cosa_manca(self):
        self.prepara()
        r = self.post_ricerca(ia="gemini")
        self.assertEqual(r.status, 409)
        self.assertIn("Gemini", self.json(r)["errore"])

    def test_doppio_clic_non_avvia_due_ricerche(self):
        self.prepara()
        self.assertEqual(self.post_ricerca().status, 200)
        self.assertEqual(self.post_ricerca().status, 409)
        self.assertEqual(self.avvii, 1)

    def test_richiesta_da_altro_sito_rifiutata(self):
        r = self.chiama("POST", "/api/avviso", headers={"Origin": "https://cattivo.example"})
        self.assertEqual(r.status, 403)
        self.assertFalse(Archivio(self.base).avviso_accettato())

    def test_origin_locale_accettata(self):
        r = self.chiama("POST", "/api/avviso", headers={"Origin": f"http://127.0.0.1:{self.porta}"})
        self.assertEqual(r.status, 200)

    def test_host_diverso_rifiutato(self):
        r = self.chiama("GET", "/api/stato", headers={"Host": "cattivo.example"})
        self.assertEqual(r.status, 403)

    def test_id_con_percorso_rifiutato(self):
        self.assertEqual(self.chiama("GET", "/api/ricerche/..%2F..%2Fx/1").status, 404)
        self.assertEqual(self.chiama("GET", "/api/leghe/..%2Fx").status, 404)

    def test_file_statico_fuori_cartella_rifiutato(self):
        self.assertEqual(self.chiama("GET", "/../server.py").status, 404)
        self.assertEqual(self.chiama("GET", "/server.py").status, 404)

    def test_listone_non_valido_400(self):
        r = self.chiama("POST", "/api/listone", b"ciao")
        self.assertEqual(r.status, 400)
        self.assertIn("Excel", self.json(r)["errore"])

    def test_listone_troppo_grande_413(self):
        r = self.chiama("POST", "/api/listone", b"x" * (10 * 1024 * 1024 + 1))
        self.assertEqual(r.status, 413)

    def test_nuovo_listone_segnala_giocatore_uscito(self):
        lega = self.prepara()
        uscito = lega["rosa"][0]["nome"]
        self.chiama("POST", "/api/listone", xlsx_prova([g for g in listone_prova() if g["nome"] != uscito]))
        s = self.json(self.chiama("GET", "/api/stato"))
        avvisi = s["leghe"][0]["avvisi_rosa"]
        self.assertEqual([(a["nome"], a["problema"]) for a in avvisi], [(uscito, "non_trovato")])
        self.assertEqual(len(s["leghe"][0]["rosa"]), 25)

    def test_file_lega_danneggiato_risponde_con_il_nome_del_file(self):
        self.prepara()
        (self.base / "leghe" / "prova.json").write_text("{rotto")
        r = self.chiama("GET", "/api/stato")
        self.assertEqual(r.status, 500)
        self.assertIn("prova.json", self.json(r)["errore"])

    def test_abbina_rosa(self):
        self.prepara(rosa=False)
        r = self.json(self.chiama("POST", "/api/leghe/prova/abbina", {"testo": "P01 Rossi\nNessuno"}))
        self.assertEqual([g["nome"] for g in r["trovati"]], ["P01 Rossi"])
        self.assertEqual(r["non_trovati"], ["Nessuno"])

    def test_put_con_id_diverso_rifiutato(self):
        lega = self.prepara(rosa=False)
        lega["id"] = "altra"
        self.assertEqual(self.chiama("PUT", "/api/leghe/prova", lega).status, 400)

    def test_tutto_il_giro_fino_al_risultato_pronto(self):
        self.prepara()
        id_ = self.json(self.post_ricerca())["id"]
        self.assertEqual(self.json(self.chiama("GET", f"/api/ricerche/prova/{id_}"))["stato"], "in_corso")
        c = self.base / "ricerche" / "prova" / id_
        (c / "risultato.json").write_text(json.dumps(risultato_valido("grossa")), encoding="utf-8")
        (c / "FATTO").write_text("x")
        s = self.json(self.chiama("GET", f"/api/ricerche/prova/{id_}"))
        self.assertEqual(s["stato"], "pronto", s["errori"])
        self.assertEqual(self.json(self.chiama("GET", "/api/ricerche/prova"))[0]["id"], id_)
        self.assertEqual(self.post_ricerca().status, 200)

    def test_chiudi_sblocca_una_nuova_ricerca(self):
        self.prepara()
        id_ = self.json(self.post_ricerca())["id"]
        s = self.json(self.chiama("POST", f"/api/ricerche/prova/{id_}/chiudi"))
        self.assertEqual(s["stato"], "errore")
        self.assertEqual(self.post_ricerca().status, 200)

    def test_pagina_servita(self):
        r = self.chiama("GET", "/")
        self.assertEqual(r.status, 200)
        self.assertIn("text/html", r.getheader("Content-Type"))


if __name__ == "__main__":
    unittest.main()
