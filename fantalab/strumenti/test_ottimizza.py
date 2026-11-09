#!/usr/bin/env python3
"""Brute-force cross-checks for the exact hindsight optimizer (synthetic data)."""
from __future__ import annotations

import itertools
import random
import unittest
from ottimizza import Player, captain_bonus, defence_bonus, score_forecast, solve_best_xi


class TestOttimo(unittest.TestCase):
    def test_bonus_thresholds(self):
        self.assertEqual([defence_bonus(x) for x in (5.9, 6, 6.24, 6.25, 6.5, 6.75, 7, 7.25)],
                         [1, 2, 2, 3, 4, 5, 6, 6])
        self.assertEqual([captain_bonus(x) for x in (5.5, 6, 6.5, 7, 7.5)],
                         [0, .5, 1, 1.5, 2])

    def test_exact_vs_bruteforce(self):
        rng = random.Random(12345)
        for iteration in range(12):
            players = []
            for role, n in [('P', 2), ('D', 6), ('C', 4), ('A', 4)]:
                for idx in range(n):
                    vote = rng.choice([5, 5.5, 6, 6.5, 7, 7.5, 8])
                    fv = vote + rng.choice([-2, -1, 0, 0, 1, 3, 4, 6])
                    players.append(Player(f'{role}{idx}', f'{role}{idx}', 'Test', role, vote, fv, True))
            predicted = solve_best_xi(players)['totale']
            by_r = {r: [p for p in players if p.role == r] for r in ['P', 'D', 'C', 'A']}
            true_best = float('-inf')
            for g in by_r['P']:
                for ds in itertools.combinations(by_r['D'], 4):
                    mod = defence_bonus((g.vote + sum(sorted((d.vote for d in ds), reverse=True)[:3])) / 4)
                    for cs in itertools.combinations(by_r['C'], 3):
                        for aa in itertools.combinations(by_r['A'], 3):
                            chosen = (g, *ds, *cs, *aa)
                            value = sum(p.fv for p in chosen) + mod + max(captain_bonus(p.vote) for p in chosen)
                            true_best = max(true_best, value)
            self.assertAlmostEqual(predicted, true_best, msg=f'iteration {iteration}')

    def test_forecast_substitution(self):
        all_players = []
        for role, n in [('P', 2), ('D', 6), ('C', 5), ('A', 5)]:
            for i in range(n):
                valid = not (role == 'D' and i == 0)
                all_players.append(Player(f'{role}{i}', f'{role}{i}', 'Test', role,
                                          6 if valid else None, 6 if valid else None, valid))
        f = {'titolari': {'P':['P0'], 'D':['D0','D1','D2','D3'], 'C':['C0','C1','C2'], 'A':['A0','A1','A2']},
             'panchina': {'P':['P1'], 'D':['D4','D5'], 'C':['C3','C4'], 'A':['A3','A4']},
             'capitano':'A0', 'vicecapitano':'C0'}
        actual = score_forecast(all_players, f)
        self.assertEqual(actual['sostituzioni'], [{'out':'D0','in':'D4','ruolo':'D'}])
        self.assertEqual(actual['totale'], 68.5)  # 11 * 6 + defence 2 + captain 0.5


if __name__ == '__main__':
    unittest.main()
