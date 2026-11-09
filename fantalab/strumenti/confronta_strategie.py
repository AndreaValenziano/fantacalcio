#!/usr/bin/env python3
"""Confronta due previsioni A/B FantaLab sullo stesso CSV di voti.

Uso:
  python strumenti/confronta_strategie.py dati/voti_G12_completi.csv \
    --media stagioni/2026-27/G12/previsione_A.json \
    --primo stagioni/2026-27/G12/previsione_B.json \
    --output stagioni/2026-27/G12/confronto_A_B.json

Il calcolo dell'ottimo è globale SOLO su un universo interamente verificato:
la CLI NON può dedurre la completezza dalla presenza di molte righe.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ottimizza import load_csv, score_forecast, solve_best_xi


def read_strategy(path: Path, expected: str) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError(f'{path}: oggetto JSON richiesto')
    if obj.get('strategia') != expected:
        raise ValueError(f'{path}: strategia attesa {expected}, trovata {obj.get("strategia")!r}')
    for key in ('titolari', 'panchina', 'capitano', 'vicecapitano'):
        if key not in obj:
            raise ValueError(f'{path}: campo {key} mancante')
    if obj.get('stato') not in ('CONGELATO', 'CONGELATO_STORICO', 'CONGELATO_PRE_DEADLINE'):
        raise ValueError(f'{path}: solo snapshot CONGELATI si confrontano, stato={obj.get("stato")!r}')
    return obj


def compare(players, forecast_a: dict, forecast_b: dict, winner: float | None = None,
            universe_verified: bool = False) -> dict:
    if forecast_a.get('strategia') != 'MASSIMA_MEDIA' or forecast_b.get('strategia') != 'PRIMO_POSTO':
        raise ValueError('Passare una previsione MASSIMA_MEDIA e una PRIMO_POSTO')
    if forecast_a.get('stagione') != forecast_b.get('stagione') or forecast_a.get('giornata') != forecast_b.get('giornata'):
        raise ValueError('Stagione/giornata di A e B non coincidono')
    perfect = solve_best_xi(players)
    a = score_forecast(players, forecast_a)
    b = score_forecast(players, forecast_b)
    result = {
        'stagione': forecast_a.get('stagione'), 'giornata': forecast_a.get('giornata'),
        'stato_ottimo': 'VERIFICA_UNIVERSO_DICHIARATA' if universe_verified else 'SUBSET_ONLY_NON_CERTIFICATO',
        'nota_completezza': ('Flag manuale dell’analista: conservare prove e metadati del censimento completo.'
                             if universe_verified else 'Senza censimento e verifica di tutti i voti/listone, massimo solo nel subset del CSV.'),
        'ottimo_ex_post': perfect,
        'strategia_A_massima_media': a,
        'strategia_B_primo_posto': b,
        'nota_probabilita': 'Questa CLI calcola fantapunti EX POST, non P(primo) ex ante. Servono dati sugli avversari per stimare tale probabilità.',
        'punteggio_vincitore_lega': winner,
    }
    if 'totale' in a and 'totale' in b:
        sa, sb = a['totale'], b['totale']
        result['confronto'] = {
            'delta_B_meno_A': round(sb - sa, 3),
            'gap_A_da_ottimo': round(perfect['totale'] - sa, 3),
            'gap_B_da_ottimo': round(perfect['totale'] - sb, 3),
            'punteggio_maggiore': 'A' if sa > sb else ('B' if sb > sa else 'PARI'),
        }
        if winner is not None:
            result['confronto']['delta_A_su_vincitore'] = round(sa - winner, 3)
            result['confronto']['delta_B_su_vincitore'] = round(sb - winner, 3)
            result['confronto']['superamento_ipotetico_A'] = sa > winner
            result['confronto']['superamento_ipotetico_B'] = sb > winner
            result['confronto']['nota'] = 'Superare ipoteticamente la formazione vincente non significa aver partecipato o vinto realmente.'
    else:
        result['confronto'] = {
            'stato': 'NON_CALCOLABILE_PER_ALMENO_UNA_PREVISIONE',
            'note': 'Controllare SV senza copertura, vicecapitano e campi di voto mancanti.'
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('voti_csv', type=Path, help='CSV voti redazionali Fantacalcio.it normalizzati per la lega')
    parser.add_argument('--media', type=Path, required=True, help='JSON congelato con strategia MASSIMA_MEDIA')
    parser.add_argument('--primo', type=Path, required=True, help='JSON congelato con strategia PRIMO_POSTO')
    parser.add_argument('--punteggio-vincitore', type=float, help='Punteggio dichiarato vincitore reale lega, se noto')
    parser.add_argument('--universo-verificato', action='store_true', help='Flag MANUALE, solo con prove di completa copertura listone/voti')
    parser.add_argument('--output', type=Path, help='Salva JSON risultato')
    args = parser.parse_args()
    try:
        players = load_csv(args.voti_csv)
        a = read_strategy(args.media, 'MASSIMA_MEDIA')
        b = read_strategy(args.primo, 'PRIMO_POSTO')
        report = compare(players, a, b, args.punteggio_vincitore, args.universo_verificato)
        output = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding='utf-8')
        print(output)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
