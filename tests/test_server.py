import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from consigliere import fonti
from consigliere.archivio import Archivio
from consigliere.server import crea_server
from tests.aiuti import COMPOSIZIONE, crea_xlsx, listone_prova, risultato_valido

DATI = Path(__file__).resolve().parent / "dati"
Q_VOTI = "stagione=2026-27&giornata=11"
V11 = "/api/verifica/prova/2026-27/11"


class _Risposta:
    def __init__(self, corpo, url):
        self.corpo, self.url = corpo, url

    def read(self, n=-1):
        return self.corpo

    def getcode(self):
        return 200

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


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
        self.html = (DATI / "voti_ridotta.html").read_bytes()
        self.rete = lambda r, timeout=None: _Risposta(self.html, r.full_url)
        finto = fonti.Scaricatore(apri=lambda r, timeout=None: self.rete(r, timeout), dormi=lambda s: None)
        self.srv = crea_server(self.base, porta=0, avvia=avvia, scaricatore=finto)
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

    def test_ricerca_con_riassunto_condiviso_irraggiungibile_parte_senza(self):
        self.prepara()
        r = self.chiama("PUT", "/api/riassunto", {"condiviso": "https://127.0.0.1:1/ultimo.json"})
        self.assertEqual(r.status, 200)
        id_ = self.json(self.post_ricerca())["id"]
        richiesta = json.loads((self.base / "ricerche" / "prova" / id_ / "richiesta.json").read_text("utf-8"))
        self.assertFalse(richiesta["riassunto"])
        self.assertFalse(self.json(self.chiama("GET", f"/api/ricerche/prova/{id_}"))["con_riassunto"])

    def test_indirizzo_del_riassunto_non_http_rifiutato(self):
        self.assertEqual(self.chiama("PUT", "/api/riassunto", {"condiviso": "javascript:alert(1)"}).status, 400)
        self.assertEqual(self.chiama("PUT", "/api/riassunto", {"condiviso": ""}).status, 200)
        self.assertIsNone(self.json(self.chiama("GET", "/api/stato"))["riassunto"]["config"]["condiviso"])

    def test_chiudi_sblocca_una_nuova_ricerca(self):
        self.prepara()
        id_ = self.json(self.post_ricerca())["id"]
        s = self.json(self.chiama("POST", f"/api/ricerche/prova/{id_}/chiudi"))
        self.assertEqual(s["stato"], "errore")
        self.assertEqual(self.post_ricerca().status, 200)

    def copie_voti(self):
        return list((self.base / "fonti" / "voti").rglob("*.html"))

    def accetta(self):
        self.assertEqual(self.chiama("POST", "/api/avviso").status, 200)

    def test_download_richiede_avviso_v2(self):
        chiamate = []
        self.rete = lambda r, timeout=None: chiamate.append(r) or _Risposta(self.html, r.full_url)
        voti = ("POST", "/api/fonti/voti", {"stagione": "2026-27", "giornata": 11})
        for stato in ("assente", "v1"):
            if stato == "v1":
                (self.base / "avviso.json").write_text('{"accettato_il": "2026-01-01T10:00:00+01:00"}')
            for metodo, p, c in (voti, ("POST", "/api/fonti/listone", None)):
                r = self.chiama(metodo, p, c)
                self.assertEqual(r.status, 409, (stato, p))
                self.assertIn("accetta l'avviso", self.json(r)["errore"])
        self.assertEqual(chiamate, [])
        self.accetta()
        self.assertEqual(self.chiama(*voti).status, 200)
        self.assertEqual(len(chiamate), 1)

    def test_caricamento_a_mano_senza_avviso(self):
        self.assertEqual(self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", self.html).status, 200)

    def test_voti_html_senza_query(self):
        r = self.chiama("POST", "/api/fonti/voti", self.html)
        self.assertEqual(r.status, 400)
        self.assertIn("?stagione=", self.json(r)["errore"])

    def test_content_length_non_valido(self):
        for valore in ("-5", "abc"):
            c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=5)
            c.putrequest("POST", "/api/leghe")
            c.putheader("Content-Length", valore)
            c.endheaders()
            r = c.getresponse()
            self.assertEqual(r.status, 400, valore)
            c.close()

    def test_ultima_versione_illeggibile_segnalata(self):
        self.prepara()
        self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", self.html)
        self.chiama("POST", V11)
        self.chiama("POST", V11)
        (self.base / "verifiche/prova/2026-27/G11/v2/verifica.json").write_text("{rotto")
        g = self.json(self.chiama("GET", V11))
        self.assertIsNone(g["ultima"])
        self.assertEqual(g["versione_illeggibile"], 2)
        self.assertEqual(len(g["versioni"]), 2)

    def test_voti_scaricati(self):
        self.accetta()
        r = self.chiama("POST", "/api/fonti/voti", {"stagione": "2026-27", "giornata": 11})
        self.assertEqual(r.status, 200, r.dati)
        d = self.json(r)
        self.assertEqual(d["meta"]["origine"], "scaricata")
        self.assertGreater(d["giocatori"], 0)
        self.assertEqual(d["differenze"], [])
        self.assertIn("mancanze", d)
        self.assertEqual(len(self.copie_voti()), 1)

    def test_voti_caricati_a_mano(self):
        r = self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", self.html)
        self.assertEqual(r.status, 200, r.dati)
        self.assertEqual(self.json(r)["meta"]["origine"], "caricata_a_mano")
        self.assertEqual(len(self.copie_voti()), 1)

    def test_voti_giornata_diversa_dalla_pagina(self):
        r = self.chiama("POST", "/api/fonti/voti?stagione=2026-27&giornata=10", self.html)
        self.assertEqual(r.status, 400)
        self.assertEqual(self.copie_voti(), [])

    def test_voti_stagione_o_giornata_non_valide(self):
        self.accetta()
        for q in ("stagione=../x&giornata=11", "stagione=2026-27&giornata=39", "stagione=2026-27&giornata=a"):
            self.assertEqual(self.chiama("POST", f"/api/fonti/voti?{q}", self.html).status, 400, q)
        self.assertEqual(self.chiama("POST", "/api/fonti/voti", {"stagione": "2026-27"}).status, 400)

    def test_voti_fonte_non_accessibile(self):
        self.accetta()
        def giu(r, timeout=None):
            raise OSError("rete assente")
        self.rete = giu
        r = self.chiama("POST", "/api/fonti/voti", {"stagione": "2026-27", "giornata": 11})
        self.assertEqual(r.status, 502)
        self.assertIn("Salva la pagina", self.json(r)["errore"])

    def test_voti_pagina_troppo_grande(self):
        with mock.patch("consigliere.server.MAX_PAGINA", 1000):
            r = self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", b"x" * 2000)
        self.assertEqual(r.status, 413)

    def test_voti_non_utf8(self):
        r = self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", b"<html>\xff\xfe</html>")
        self.assertEqual(r.status, 400)

    def test_listone_dal_sito_e_a_mano(self):
        self.accetta()
        self.html = (DATI / "quotazioni_ridotta.html").read_bytes()
        r = self.chiama("POST", "/api/fonti/listone")
        self.assertEqual(r.status, 200, r.dati)
        n = self.json(r)["numero"]
        self.assertGreater(n, 0)
        self.assertEqual(self.json(self.chiama("GET", "/api/stato"))["listone"]["numero"], n)
        self.assertEqual(Archivio(self.base).listone()["origine"], "scaricata")
        r = self.chiama("POST", "/api/fonti/listone", self.html)
        self.assertEqual(self.json(r)["meta"]["origine"], "caricata_a_mano")
        self.assertEqual(Archivio(self.base).listone()["origine"], "caricata_a_mano")

    def test_verifica_senza_voti(self):
        self.prepara()
        r = self.chiama("POST", V11)
        self.assertEqual(r.status, 409)
        self.assertIn("Scarica prima i voti", self.json(r)["errore"])
        g = self.json(self.chiama("GET", V11))
        self.assertEqual((g["versioni"], g["ultima"], g["schierata"], g["voti"]), ([], None, None, None))

    def test_verifica_crea_versioni(self):
        self.prepara()
        self.assertEqual(self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", self.html).status, 200)
        for k in (1, 2):
            r = self.chiama("POST", V11)
            self.assertEqual(r.status, 200, r.dati)
            self.assertEqual(self.json(r)["versione"], k)
        g = self.json(self.chiama("GET", V11))
        self.assertEqual(len(g["versioni"]), 2)
        self.assertEqual(g["ultima"]["versione_verifica"], 2)
        self.assertEqual(g["voti"]["origine"], "caricata_a_mano")

    def test_verifica_errore_di_calcolo_500(self):
        self.prepara()
        percorso = self.base / "leghe" / "prova.json"
        lega = json.loads(percorso.read_text(encoding="utf-8"))
        lega["modificatore_difesa"] = {"attivo": True, "fasce": [1, 2, 3]}  # lunghezza sbagliata
        percorso.write_text(json.dumps(lega), encoding="utf-8")
        self.assertEqual(self.chiama("POST", f"/api/fonti/voti?{Q_VOTI}", self.html).status, 200)
        # la pagina ridotta non basta per un modulo completo: il calcolo vero usa una pagina sintetica completa
        from consigliere import verifica
        from tests.test_verifica import voti_prova
        originale = verifica.calcola
        with mock.patch.object(verifica, "calcola", lambda lega, voti, *a, **k: originale(lega, voti_prova(), *a, **k)):
            r = self.chiama("POST", V11)
        self.assertEqual(r.status, 500, r.dati)
        self.assertTrue(self.json(r)["errore"].startswith("Non riesco a calcolare la verifica: "), r.dati)
        self.assertFalse((self.base / "verifiche" / "prova" / "2026-27" / "G11" / "v1").exists())

    def test_verifica_percorso_non_valido(self):
        self.prepara()
        self.assertEqual(self.chiama("GET", "/api/verifica/prova/2026-27/99").status, 400)
        self.assertEqual(self.chiama("GET", "/api/verifica/prova/xx/11").status, 400)
        self.assertEqual(self.chiama("GET", "/api/verifica/inesistente/2026-27/11").status, 404)
        self.assertEqual(self.chiama("GET", "/api/verifica/..%2Fx/2026-27/11").status, 404)

    def corpo_schierata(self, lega, modulo="3-4-3"):
        per = {r: [g for g in lega["rosa"] if g["ruolo"] == r] for r in "PDCA"}
        d, c, a = (int(x) for x in modulo.split("-"))
        tit = per["P"][:1] + per["D"][:d] + per["C"][:c] + per["A"][:a]
        pan = lega["panchina"]
        resto = [g for r in "PDCA" for g in [x for x in per[r] if x not in tit][:pan[r]]]
        nomi = lambda gg: [f"{g['nome']} {g['squadra']}" for g in gg]
        return {"testo": "\n".join(nomi(tit)), "modulo": modulo, "panchina": nomi(resto),
                "capitano": tit[-1]["nome"], "vice": tit[-2]["nome"]}

    def test_schierata_salvata_e_usata(self):
        lega = self.prepara()
        r = self.chiama("POST", V11 + "/schierata", self.corpo_schierata(lega))
        self.assertEqual(r.status, 200, r.dati)
        self.assertEqual(self.json(r), {"versione": 1})
        self.assertEqual(len(self.json(self.chiama("GET", V11))["schierata"]["titolari"]), 11)

    def test_schierata_capitano_e_vice_abbinati_come_i_titolari(self):
        lega = self.prepara()
        corpo = self.corpo_schierata(lega)
        corpo |= {"capitano": corpo["capitano"].upper(), "vice": "  " + corpo["vice"].lower() + " "}
        r = self.chiama("POST", V11 + "/schierata", corpo)
        self.assertEqual(r.status, 200, r.dati)
        r = self.chiama("POST", V11 + "/schierata", corpo | {"vice": "Sconosciuto Zzz"})
        self.assertEqual(r.status, 409)
        self.assertIn("non è tra i titolari", self.json(r)["errore"])
        r = self.chiama("POST", V11 + "/schierata", corpo | {"vice": "uno\ndue"})
        self.assertEqual((r.status, self.json(r)["errore"]), (409, "Per il vice scrivi un solo nome."))

    def test_schierata_con_errori_di_regole(self):
        lega = self.prepara()
        corpo = self.corpo_schierata(lega) | {"modulo": "9-9-9"}
        r = self.chiama("POST", V11 + "/schierata", corpo)
        self.assertEqual(r.status, 409)
        self.assertTrue(self.json(r)["errori"])

    def test_schierata_ambigua(self):
        lega = self.prepara()
        a = self.chiama("POST", "/api/listone", xlsx_prova(listone_prova() + [
            {"nome": "D01 Rossi", "squadra": "ZZZ", "ruolo": "D"}]))
        self.assertEqual(a.status, 200)
        corpo = self.corpo_schierata(lega) | {"testo": "D01 Rossi"}
        r = self.chiama("POST", V11 + "/schierata", corpo)
        self.assertEqual(r.status, 409, r.dati)
        d = self.json(r)
        self.assertEqual(d["ambigui"][0]["testo"], "D01 Rossi")
        self.assertGreaterEqual(len(d["ambigui"][0]["opzioni"]), 2)

    def test_schierata_nome_non_trovato(self):
        lega = self.prepara()
        r = self.chiama("POST", V11 + "/schierata", self.corpo_schierata(lega) | {"testo": "Nessuno Qui"})
        self.assertEqual(r.status, 409)
        self.assertEqual(self.json(r)["non_trovati"], ["Nessuno Qui"])

    def test_host_estraneo_verifica(self):
        self.prepara()
        for metodo, p, c in (("POST", "/api/fonti/voti", {"stagione": "2026-27", "giornata": 11}),
                             ("POST", "/api/fonti/listone", None), ("GET", V11, None), ("POST", V11, None),
                             ("POST", V11 + "/schierata", {})):
            self.assertEqual(self.chiama(metodo, p, c, headers={"Host": "evil.example"}).status, 403, p)
            self.assertEqual(self.chiama(metodo, p, c, headers={"Origin": "http://evil.example"}).status, 403, p)
        self.assertEqual(self.copie_voti(), [])

    def test_pagina_servita(self):
        r = self.chiama("GET", "/")
        self.assertEqual(r.status, 200)
        self.assertIn("text/html", r.getheader("Content-Type"))


if __name__ == "__main__":
    unittest.main()
