#!/usr/bin/env python3
"""Piccolo test d'integrazione delle due strategie (dati sintetici, NON reali)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ottimizza import Player
from confronta_strategie import compare


def fake_player(pid, role, fv, vote=6.0):
    return Player(pid, pid, 'TestFC', role, vote, fv, True)


class DualForecastTests(unittest.TestCase):
    def setUp(self):
        self.players = [fake_player(f'p{i}', 'P', 6+i) for i in range(2)]
        for role, count in [('D', 6), ('C', 5), ('A', 5)]:
            self.players += [fake_player(f'{role.lower()}{i}', role, 6+i) for i in range(count)]
        self.a = {
            'stagione': 'test', 'giornata': 1, 'strategia': 'MASSIMA_MEDIA', 'stato': 'CONGELATO',
            'capitano': 'a0', 'vicecapitano': 'c0',
            'titolari': {'P': ['p0'], 'D': ['d0', 'd1', 'd2', 'd3'],
                        'C': ['c0', 'c1', 'c2'], 'A': ['a0', 'a1', 'a2']},
            'panchina': {'P': ['p1'], 'D': ['d4', 'd5'], 'C': ['c3', 'c4'], 'A': ['a3', 'a4']}
        }
        self.b = {
            **self.a, 'strategia': 'PRIMO_POSTO',
            'titolari': {'P': ['p1'], 'D': ['d2', 'd3', 'd4', 'd5'],
                        'C': ['c2', 'c3', 'c4'], 'A': ['a2', 'a3', 'a4']},
            'panchina': {'P': ['p0'], 'D': ['d0', 'd1'], 'C': ['c0', 'c1'], 'A': ['a0', 'a1']},
            'capitano': 'a4', 'vicecapitano': 'c4'
        }

    def test_compare_two_lineups(self):
        res = compare(self.players, self.a, self.b, winner=70.0)
        self.assertEqual(res['stato_ottimo'], 'SUBSET_ONLY_NON_CERTIFICATO')
        aa = res['strategia_A_massima_media']['totale']
        bb = res['strategia_B_primo_posto']['totale']
        self.assertGreater(bb, aa)
        self.assertAlmostEqual(res['confronto']['delta_B_meno_A'], bb-aa)
        self.assertLessEqual(bb, res['ottimo_ex_post']['totale'])
        self.assertIn('superamento_ipotetico_A', res['confronto'])

    def test_identical_lineups_allowed(self):
        b = {**self.a, 'strategia': 'PRIMO_POSTO'}
        res = compare(self.players, self.a, b)
        self.assertEqual(res['confronto']['delta_B_meno_A'], 0)

    def test_mismatched_giornata_rejected(self):
        b = {**self.b, 'giornata': 2}
        with self.assertRaises(ValueError):
            compare(self.players, self.a, b)


if __name__ == '__main__':
    unittest.main()
