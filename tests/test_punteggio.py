import json
import unittest
from pathlib import Path

from consigliere import pagine, punteggio

RADICE = Path(__file__).resolve().parent.parent
VOTI_VERI = RADICE / "tests" / "dati" / "voti_vero_2026-27_11.html"


def lega(nome):
    return json.loads((RADICE / "consigliere" / "modelli" / f"{nome}.json").read_text(encoding="utf-8"))


def gioc(**k):
    g = {"id": 1, "nome": "X", "squadra": "Y", "ruolo": "C", "voto": 6.0, "fv_pubblicato": None,
         "ammonito": False, "espulso": False, "gol": 0, "gol_subiti": 0, "autogol": 0,
         "rigori_segnati": 0, "rigori_sbagliati": 0, "rigori_parati": 0, "assist": 0,
         "player_of_the_match": 0}
    g.update(k)
    return g


class TestFv(unittest.TestCase):
    def test_fv_gol_assist_cartellino(self):
        g = gioc(voto=6.5, gol=1, assist=1, ammonito=True)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 10.0)

    def test_fv_porta_inviolata(self):
        L = lega("libera")
        self.assertAlmostEqual(punteggio.fv_lega(gioc(ruolo="P", voto=6.0), L), 7.0)
        self.assertAlmostEqual(punteggio.fv_lega(gioc(ruolo="P", voto=6.0, gol_subiti=2), L), 4.0)
        self.assertIsNone(punteggio.fv_lega(gioc(ruolo="P", voto=None), L))

    def test_fv_player_of_the_match(self):
        g = gioc(voto=7.0, player_of_the_match=1)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("pensionati")), 7.5)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("f1")), 8.0)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 7.0)

    def test_sv_ammonito(self):
        g = gioc(voto=None, ammonito=True)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("pensionati")), 5.0)
        self.assertIsNone(punteggio.fv_lega(g, lega("libera")))
        self.assertIsNone(punteggio.fv_lega(None, lega("pensionati")))

    def test_porta_inviolata_solo_portiere(self):
        for ruolo in "DCA":
            g = gioc(ruolo=ruolo, voto=6.0, gol_subiti=0)
            self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 6.0, msg=ruolo)

    def test_rigore_segnato_non_doppio(self):
        g = gioc(voto=7.0, gol=0, rigori_segnati=1)
        self.assertAlmostEqual(punteggio.fv_lega(g, lega("libera")), 10.0)

    def test_fv_coerente(self):
        ok = gioc(voto=6.0, assist=1, fv_pubblicato=7.0)
        self.assertTrue(punteggio.fv_coerente(ok))
        self.assertFalse(punteggio.fv_coerente(gioc(voto=6.0, assist=1, fv_pubblicato=6.5)))
        self.assertTrue(punteggio.fv_coerente(gioc(voto=None)))


class TestCapitano(unittest.TestCase):
    def test_capitano_confini(self):
        c = lega("libera")["capitano"]
        for v, atteso in [(5.5, 0), (6, 0.5), (6.5, 1), (7, 1.5), (7.5, 2), (8.5, 2), (5, 0), (6.25, 0.5)]:
            self.assertEqual(punteggio.bonus_capitano(v, c), atteso, v)
        self.assertFalse(punteggio.voto_mezzo(6.25))
        self.assertTrue(punteggio.voto_mezzo(6.5))

    def test_capitano_disattivo(self):
        self.assertEqual(punteggio.bonus_capitano(8, {"attivo": False}), 0)
        self.assertEqual(punteggio.bonus_capitano(8, None), 0)


class TestModificatore(unittest.TestCase):
    def test_modificatore_confini(self):
        f = [1, 2, 3, 4, 5, 6, 6]
        for media, atteso in [(5.99, 1), (6, 2), (6.24, 2), (6.25, 3), (6.5, 4), (6.75, 5), (7, 6), (7.25, 6)]:
            # portiere e difensori tutti uguali alla media: la media restituita coincide
            m, b = punteggio.modificatore(media, [media] * 4, f)
            self.assertAlmostEqual(m, media)
            self.assertEqual(b, atteso, media)
        self.assertEqual(punteggio.modificatore(6.75, [6.75] * 4, [0, 1, 1, 3, 3, 6, 6])[1], 3)

    def test_modificatore_tre_migliori(self):
        m, b = punteggio.modificatore(7, [7, 6.5, 6.5, 4], [1, 2, 3, 4, 5, 6, 6])
        self.assertAlmostEqual(m, 6.75)
        self.assertEqual(b, 5)

    def test_modificatore_pochi_difensori(self):
        f = [1, 2, 3, 4, 5, 6, 6]
        self.assertEqual(punteggio.modificatore(7, [7, 7, 7], f), (None, 0))
        self.assertEqual(punteggio.modificatore(None, [7, 7, 7, 7], f), (None, 0))

    def test_fasce_lunghezza_errata(self):
        with self.assertRaisesRegex(ValueError, "devono essere 7, trovate 5"):
            punteggio.modificatore(7, [7] * 4, [1, 2, 3, 4, 5])
        self.assertFalse(punteggio.fasce_monotone([1, 2, 3, 4, 5]))
        self.assertFalse(punteggio.fasce_monotone([0, 1, 2, 3, 4, 5, 6, 7]))

    def test_fasce_monotone(self):
        self.assertTrue(punteggio.fasce_monotone([0, 1, 1, 3, 3, 6, 6]))
        self.assertFalse(punteggio.fasce_monotone([0, 2, 1, 3, 3, 6, 6]))


@unittest.skipUnless(VOTI_VERI.exists(), "pagina vera G11 assente")
class TestPaginaVera(unittest.TestCase):
    def test_fv_pagina_vera(self):
        voti = pagine.leggi_voti(VOTI_VERI.read_text(encoding="utf-8"))
        con_voto = [g for g in voti["giocatori"] if g["voto"] is not None]
        falsi = [g for g in con_voto if not punteggio.fv_coerente(g)]
        perc = 100 * (len(con_voto) - len(falsi)) / len(con_voto)
        print(f"\nfv_coerente: {perc:.1f}% ({len(falsi)} incoerenti su {len(con_voto)})")
        for g in falsi:
            print("  ", g["nome"], g["ruolo"], g["voto"], "pubb.", g["fv_pubblicato"],
                  "ricalc.", punteggio.fv_lega(g, {"bonus": punteggio.BONUS_STANDARD, "ammonito_senza_voto": False}))
        self.assertGreaterEqual(perc, 95)


if __name__ == "__main__":
    unittest.main()


def p(i, ruolo="C", voto=6.0, **k):
    """Giocatore di prova con id i."""
    k.setdefault("fv_pubblicato", voto)
    k.setdefault("nome", f"G{i}")
    return gioc(id=i, ruolo=ruolo, **{"voto": voto, **k})


def giocatore_f(i, ruolo):
    return {"id": i, "ruolo": ruolo}


def formazione(ruoli_titolari, ruoli_panchina, **extra):
    """Titolari id 1..11 e panchina id 21.. con i ruoli indicati (stringhe tipo 'PDDDCCCAAA')."""
    f = {"modulo": "4-3-3",
         "titolari": [giocatore_f(i + 1, r) for i, r in enumerate(ruoli_titolari)],
         "panchina": [giocatore_f(21 + i, r) for i, r in enumerate(ruoli_panchina)],
         "capitano": None, "vice": None, "switch": None}
    f.update(extra)
    return f


T433 = "PDDDDCCCAAA"  # P + 4D + 3C + 3A
B = "PDDCCAA"


def voti_di(*gg):
    return {g["id"]: g for g in gg}


def tutti(ruoli, voto=6.0, base=1):
    return [p(base + i, r, voto) for i, r in enumerate(ruoli)]


class TestValuta(unittest.TestCase):
    def test_tutti_con_voto(self):
        L = lega("libera")
        titolari = [p(1, "P", 6.5), p(2, "D", 6), p(3, "D", 6.5), p(4, "D", 7), p(5, "D", 5.5),
                    p(6, "C", 6), p(7, "C", 6.5), p(8, "C", 7), p(9, "A", 7.5), p(10, "A", 6), p(11, "A", 6)]
        panchina = tutti(B, 6.0, 21)
        voti = voti_di(*titolari, *panchina)
        f = formazione(T433, B, capitano=9)
        r = punteggio.valuta(L, voti, f)
        somma = sum(g["voto"] for g in titolari) + 1  # 70.5 piu' la porta inviolata del portiere
        # modificatore: media (6.5 + 7 + 6.5 + 6) / 4 = 6.5 -> fascia 4; capitano 7.5 -> 2
        self.assertAlmostEqual(r["totale"], somma + 4 + 2)
        self.assertEqual(r["modificatore"]["bonus"], 4)
        self.assertAlmostEqual(r["modificatore"]["media"], 6.5)
        self.assertEqual(r["capitano"], {"id": 9, "bonus": 2, "da": "capitano"})
        self.assertEqual(r["cambi"], [])
        self.assertEqual(r["stato"], "ESATTO")
        self.assertEqual(r["motivi"], [])
        self.assertIsNone(r["totale_senza_vice"])
        self.assertIsNone(r["con_switch"])
        self.assertEqual(len([g for g in r["giocatori"] if g["in_campo"]]), 11)

    def test_cambio_stesso_ruolo(self):
        L = lega("libera")
        titolari = tutti(T433, 6.0)
        titolari[1] = p(2, "D", None)
        panchina = [p(21, "P"), p(22, "D", None), p(23, "D", 7.0), p(24, "C"), p(25, "C"), p(26, "A"), p(27, "A")]
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B))
        self.assertEqual(r["cambi"], [{"esce": 2, "entra": 23, "ruolo_diverso": False}])
        per_id = {g["id"]: g for g in r["giocatori"]}
        self.assertTrue(per_id[23]["entrato"] and per_id[23]["in_campo"])
        self.assertTrue(per_id[2]["uscito"] and not per_id[2]["in_campo"])
        self.assertFalse(per_id[22]["in_campo"])

    def test_limite_cambi_grossa(self):
        L = lega("grossa")
        titolari = tutti(T433, 6.0)
        for i in range(8):
            titolari[i + 1] = p(i + 2, titolari[i + 1]["ruolo"], None)  # tutti tranne P e un A... 8 SV
        titolari[0] = p(1, "P", 6.0)
        # 8 titolari SV (D x4, C x3, A x1) e panchina con riserve per tutti: il limite 7 e' la restrizione
        panchina = [p(21, "P"), p(22, "D"), p(23, "D"), p(24, "D"), p(25, "D"), p(26, "C"), p(27, "C"),
                    p(28, "C"), p(29, "A"), p(30, "A")]
        f = formazione(T433, ["P", "D", "D", "D", "D", "C", "C", "C", "A", "A"])
        f["panchina"] = [giocatore_f(21 + i, p_["ruolo"]) for i, p_ in enumerate(panchina)]
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), f)
        self.assertEqual(len(r["cambi"]), 7)
        sv_in_campo = [g for g in r["giocatori"] if g["in_campo"] and g["voto"] is None]
        self.assertEqual(len(sv_in_campo), 1)
        self.assertAlmostEqual(r["totale"] - r["modificatore"]["bonus"] - r["capitano"]["bonus"], 61.0)  # 10 x 6 + porta inviolata

    def _due_sv(self, voto_d_panchina, voto_c_panchina):
        L = dict(lega("libera"), sostituzioni={"numero": 1, "tipo": "traditional"})
        titolari = tutti(T433, 6.0)
        titolari[1] = p(2, "D", None)
        titolari[5] = p(6, "C", None)
        panchina = [p(21, "P"), p(22, "D", voto_d_panchina), p(23, "D"), p(24, "C", voto_c_panchina),
                    p(25, "C"), p(26, "A"), p(27, "A")]
        return L, voti_di(*titolari, *panchina), formazione(T433, B)

    def test_ordine_cambi_ininfluente(self):
        L, voti, f = self._due_sv(6.0, 6.0)
        L["modificatore_difesa"] = {"attivo": False}  # con il modificatore il cambio del difensore pesa di piu'
        r = punteggio.valuta(L, voti, f)
        self.assertEqual([c["esce"] for c in r["cambi"]], [2])  # prima i difensori
        self.assertNotIn("ordine dei cambi da verificare", r["motivi"])

    def test_ordine_cambi_influente(self):
        L, voti, f = self._due_sv(6.0, 8.5)
        r = punteggio.valuta(L, voti, f)
        self.assertEqual([c["esce"] for c in r["cambi"]], [2])
        self.assertIn("ordine dei cambi da verificare", r["motivi"])
        self.assertEqual(r["stato"], "PROVVISORIO")

    def _hybrid(self, moduli):
        L = dict(lega("f1"), moduli=moduli)
        titolari = tutti("PDDDDCCCAAA", 6.0)  # 4-3-3
        titolari[10] = p(11, "A", None)
        panchina = [p(21, "P"), p(22, "D"), p(23, "C", 6.5)]
        f = formazione("PDDDDCCCAAA", "PDC")
        return L, voti_di(*titolari, *panchina), f

    def test_hybrid_ruolo_diverso(self):
        L, voti, f = self._hybrid(["4-3-3", "4-4-2"])
        r = punteggio.valuta(L, voti, f)
        self.assertEqual(r["cambi"], [{"esce": 11, "entra": 23, "ruolo_diverso": True}])
        self.assertIn("cambio di ruolo diverso (regola Hybrid da verificare)", r["motivi"])
        self.assertEqual(r["stato"], "PROVVISORIO")
        L, voti, f = self._hybrid(["4-3-3", "3-4-3"])
        r = punteggio.valuta(L, voti, f)
        self.assertEqual(r["cambi"], [])
        self.assertEqual(r["motivi"], [])

    def test_portiere_solo_portiere(self):
        L = lega("f1")
        titolari = tutti("PDDDDCCCAAA", 6.0)
        titolari[0] = p(1, "P", None)
        panchina = [p(21, "D"), p(22, "C"), p(23, "A")]
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione("PDDDDCCCAAA", "DCA"))
        self.assertEqual(r["cambi"], [])
        # e un portiere di panchina non entra per un non portiere
        titolari = tutti("PDDDDCCCAAA", 6.0)
        titolari[10] = p(11, "A", None)
        panchina = [p(21, "P")]
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione("PDDDDCCCAAA", "P"))
        self.assertEqual(r["cambi"], [])

    def test_capitano_sv_vice(self):
        L = lega("libera")
        titolari = tutti(T433, 6.0)
        titolari[8] = p(9, "A", None)
        titolari[9] = p(10, "A", 7.0)
        panchina = [p(21, "P"), p(22, "D"), p(23, "D"), p(24, "C"), p(25, "C"), p(26, "A", None), p(27, "A", None)]
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B, capitano=9, vice=10))
        self.assertEqual(r["capitano"], {"id": 10, "bonus": 1.5, "da": "vice"})
        self.assertAlmostEqual(r["totale_senza_vice"], r["totale"] - 1.5)
        self.assertIn("subentro del vice da verificare", r["motivi"])
        self.assertEqual(r["stato"], "PROVVISORIO")

    def test_capitano_voto_non_mezzo(self):
        L = lega("libera")
        titolari = tutti(T433, 6.0)
        titolari[8] = p(9, "A", 6.25)
        panchina = tutti(B, 6.0, 21)
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B, capitano=9))
        self.assertEqual(r["stato"], "PROVVISORIO")
        self.assertTrue(any("capitano" in m for m in r["motivi"]))

    def test_ammonito_senza_voto_non_sostituito(self):
        L = lega("pensionati")
        titolari = tutti(T433, 6.0)
        titolari[5] = p(6, "C", None, ammonito=True)
        panchina = tutti(B, 6.0, 21)
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B))
        self.assertEqual(r["cambi"], [])
        g = {x["id"]: x for x in r["giocatori"]}[6]
        self.assertTrue(g["in_campo"])
        self.assertAlmostEqual(g["fv"], 5.0)
        self.assertAlmostEqual(r["totale"], 10 * 6.0 + 5.0 + 1)  # +1 porta inviolata

    def test_modificatore_dopo_cambi(self):
        L = lega("libera")
        titolari = tutti(T433, 6.0)  # media 6 -> fascia 2
        titolari[1] = p(2, "D", None)
        panchina = [p(21, "P"), p(22, "D", 7.0), p(23, "D"), p(24, "C"), p(25, "C"), p(26, "A"), p(27, "A")]
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B))
        # media (6 + 7 + 6 + 6) / 4 = 6.25 -> fascia 3
        self.assertAlmostEqual(r["modificatore"]["media"], 6.25)
        self.assertEqual(r["modificatore"]["bonus"], 3)
        self.assertAlmostEqual(r["totale"], 60 + 1 + 7 + 3)

    def test_modificatore_disattivo(self):
        L = lega("pensionati")
        titolari = tutti(T433, 6.0)
        panchina = tutti(B, 6.0, 21)
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B))
        self.assertEqual(r["modificatore"], {"media": None, "bonus": 0})
        self.assertAlmostEqual(r["totale"], 67.0)

    def test_switch(self):
        L = lega("pensionati")
        titolari = tutti(T433, 6.0)
        titolari[8] = p(9, "A", 5.0)
        panchina = [p(21, "P"), p(22, "D"), p(23, "D"), p(24, "C"), p(25, "C"), p(26, "A", 8.0), p(27, "A")]
        f = formazione(T433, B, switch={"titolare": 9, "riserva": 26})
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), f)
        self.assertAlmostEqual(r["totale"], 66.0)
        self.assertAlmostEqual(r["con_switch"]["totale"], 69.0)
        self.assertIsNone(r["con_switch"]["con_switch"])
        self.assertEqual(r["stato"], "ESATTO")

    def test_fv_incoerente_provvisorio(self):
        L = lega("libera")
        titolari = tutti(T433, 6.0)
        titolari[3] = p(4, "D", 6.0, nome="Rossi", fv_pubblicato=9.0)
        panchina = tutti(B, 6.0, 21)
        r = punteggio.valuta(L, voti_di(*titolari, *panchina), formazione(T433, B))
        self.assertIn("FV di Rossi da verificare", r["motivi"])
        self.assertEqual(r["stato"], "PROVVISORIO")

    def test_id_assente_e_sv(self):
        L = lega("libera")
        titolari = tutti(T433, 6.0)
        r = punteggio.valuta(L, voti_di(*titolari[:-1]), formazione(T433, B))
        g = {x["id"]: x for x in r["giocatori"]}[11]
        self.assertIsNone(g["voto"])
        self.assertEqual(g["nome"], "11")
