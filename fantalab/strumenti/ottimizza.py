#!/usr/bin/env python3
"""Fantacalcio Classic 4-3-3: best XI ex post under the user's rules.

Usage:
    python strumenti/ottimizza.py dati/voti_completi.csv
    python strumenti/ottimizza.py dati/voti_completi.csv --previsione stagioni/2026-27/G11/previsione_macchina.json

The input must be COMPLETE and the scoring must be normalized to the league
fantavoto, including +1 goalkeeper clean sheet. Do not infer or impute missing
ratings. An optimum on incomplete data is only optimal within that subset.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROLES = ('P', 'D', 'C', 'A')
STARTERS = {'P': 1, 'D': 4, 'C': 3, 'A': 3}
BENCH = {'P': 1, 'D': 2, 'C': 2, 'A': 2}
CAP_LEVELS = (0.0, 0.5, 1.0, 1.5, 2.0)


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    team: str
    role: str
    vote: float | None
    fv: float | None
    valid: bool


def captain_bonus(vote: float) -> float:
    """Only 0.5-step pure ratings have been confirmed by league screenshot."""
    if abs(vote * 2 - round(vote * 2)) > 0.000001:
        raise ValueError(f'Voto capitano con frazione non regolata: {vote}')
    if vote <= 5.5:
        return 0.0
    if vote == 6.0:
        return 0.5
    if vote == 6.5:
        return 1.0
    if vote == 7.0:
        return 1.5
    return 2.0


def defence_bonus(mean: float) -> int:
    if mean < 6:
        return 1
    if mean < 6.25:
        return 2
    if mean < 6.5:
        return 3
    if mean < 6.75:
        return 4
    if mean < 7.0:
        return 5
    return 6


def load_csv(path: Path) -> list[Player]:
    out: list[Player] = []
    with path.open(newline='', encoding='utf-8-sig') as fh:
        rd = csv.DictReader(fh)
        needed = {'id', 'giocatore', 'squadra', 'ruolo', 'voto_puro', 'fv_lega', 'stato'}
        if not rd.fieldnames or not needed.issubset(rd.fieldnames):
            raise ValueError(f'CSV richiede le colonne: {sorted(needed)}')
        for r in rd:
            if not r['id'] or not r['giocatore']:
                raise ValueError('ID o nome giocatore vuoto')
            role = r['ruolo'].strip().upper()
            if role not in ROLES:
                raise ValueError(f'Ruolo Classic non valido: {role}')
            stato = r['stato'].strip().upper()
            if stato not in ('VALIDO', 'SV'):
                raise ValueError(f'Stato non valido per {r["id"]}: {stato}')
            valid = stato == 'VALIDO'
            vote = float(r['voto_puro'].replace(',', '.')) if valid else None
            fv = float(r['fv_lega'].replace(',', '.')) if valid else None
            if valid and (not r['voto_puro'] or not r['fv_lega']):
                raise ValueError(f'Voto o fantavoto mancante: {r["id"]}')
            if valid:
                captain_bonus(vote)
            out.append(Player(r['id'].strip(), r['giocatore'].strip(), r['squadra'].strip(), role, vote, fv, valid))
    if len({p.id for p in out}) != len(out):
        raise ValueError('ID giocatore duplicato nel CSV')
    return out


def group_best_k(players: list[Player], k: int, min_cap: float = 0.0) -> tuple[Player, ...] | None:
    players = sorted(players, key=lambda p: (-p.fv, p.id))
    if len(players) < k:
        return None
    selected = players[:k]
    if any(captain_bonus(p.vote) >= min_cap for p in selected):
        return tuple(selected)
    eligible = [p for p in players[k:] if captain_bonus(p.vote) >= min_cap]
    if not eligible:
        return None
    return tuple(selected[:k-1] + eligible[:1])


def strongest_defence_packages(keepers: list[Player], defenders: list[Player]):
    """Exact: at most 4 of any pure-vote level can enter the XI.

    Retaining the best four FVs for each pure vote cannot remove an optimum:
    replacing any lower-FV defender of the SAME pure vote keeps the modifier
    and captain potential unchanged and weakly improves the base score.
    """
    by_vote: dict[float, list[Player]] = defaultdict(list)
    for p in defenders:
        by_vote[p.vote].append(p)
    shortlist = []
    for vote in sorted(by_vote):
        shortlist.extend(sorted(by_vote[vote], key=lambda p: (-p.fv, p.id))[:4])
    best_by_cap: dict[float, tuple[float, Player, tuple[Player, ...], float, int] | None] = {
        cap: None for cap in CAP_LEVELS
    }
    for four in itertools.combinations(shortlist, 4):
        votes = sorted((d.vote for d in four), reverse=True)
        high3 = sum(votes[:3])
        def_fv = sum(d.fv for d in four)
        max_d_cap = max(captain_bonus(d.vote) for d in four)
        for gk in keepers:
            avg = (high3 + gk.vote) / 4
            mod = defence_bonus(avg)
            val = gk.fv + def_fv + mod
            cap = max(max_d_cap, captain_bonus(gk.vote))
            cur = best_by_cap[cap]
            if cur is None or val > cur[0] + 1e-9:
                best_by_cap[cap] = (val, gk, four, avg, mod)
    return best_by_cap


def solve_best_xi(players: list[Player]) -> dict:
    valid = {role: [p for p in players if p.valid and p.role == role] for role in ROLES}
    for role in ROLES:
        if len(valid[role]) < STARTERS[role]:
            raise ValueError(f'Giocatori validi {role} insufficienti per 4-3-3: {len(valid[role])}')
    best_by_cap = strongest_defence_packages(valid['P'], valid['D'])
    def_pick_any = max((x for x in best_by_cap.values() if x is not None), key=lambda x: x[0])
    midfielder_by_level = {b: group_best_k(valid['C'], 3, b) for b in CAP_LEVELS}
    forward_by_level = {b: group_best_k(valid['A'], 3, b) for b in CAP_LEVELS}
    cases = []
    for threshold in CAP_LEVELS:
        eligible_def = [x for cap, x in best_by_cap.items() if cap >= threshold and x is not None]
        if eligible_def:
            cases.append((max(eligible_def, key=lambda x: x[0]), midfielder_by_level[0], forward_by_level[0], threshold))
        if midfielder_by_level[threshold] is not None:
            cases.append((def_pick_any, midfielder_by_level[threshold], forward_by_level[0], threshold))
        if forward_by_level[threshold] is not None:
            cases.append((def_pick_any, midfielder_by_level[0], forward_by_level[threshold], threshold))
    scored = []
    for defence, mid, att, threshold in cases:
        if not mid or not att:
            continue
        total = defence[0] + sum(p.fv for p in mid) + sum(p.fv for p in att) + threshold
        scored.append((total, defence, mid, att))
    if not scored:
        raise ValueError('Nessun 4-3-3 valido disponibile')
    scored.sort(key=lambda x: x[0], reverse=True)
    total, defence, mid, att = scored[0]
    _, keeper, four, avg, mod = defence
    lineup = {'P': (keeper,), 'D': four, 'C': mid, 'A': att}
    eleven = [p for role in ROLES for p in lineup[role]]
    c = max(eleven, key=lambda p: (captain_bonus(p.vote), p.vote, p.fv))
    base = sum(p.fv for p in eleven)
    final = base + mod + captain_bonus(c.vote)
    assert abs(total - final) < 1e-8
    return {
        'status': 'OTTIMO_MATEMATICO_SUL_DATASET_FORNITO',
        'nota': 'Globale solo se i voti/ruoli/FV di TUTTI i calciatori sono completi e conformi alla lega.',
        'totale': round(final, 3), 'somma_fv': round(base, 3),
        'modificatore_difesa': mod, 'media_modificatore': round(avg, 3),
        'bonus_capitano': captain_bonus(c.vote), 'capitano': c.id,
        'titolari': {r: [p.id for p in lineup[r]] for r in ROLES},
        'dettaglio': [{'id': p.id, 'nome': p.name, 'ruolo': p.role, 'voto': p.vote, 'fv': p.fv}
                     for p in eleven],
        'giocatori_validi_valutati': len([p for p in players if p.valid]),
    }


def score_forecast(players: list[Player], forecast: dict) -> dict:
    by_id = {p.id: p for p in players}
    starters, bench = forecast['titolari'], forecast['panchina']
    flat = [id for role in ROLES for id in starters[role] + bench[role]]
    if len(flat) != 18 or len(set(flat)) != 18:
        raise ValueError('Una previsione deve contenere 18 ID distinti: 11+7')
    for role in ROLES:
        if len(starters[role]) != STARTERS[role] or len(bench[role]) != BENCH[role]:
            raise ValueError(f'Numero di giocatori scorretto in {role}')
        for id in starters[role] + bench[role]:
            if id not in by_id:
                raise ValueError(f'Giocatore non presente nel dataset: {id}')
            if by_id[id].role != role:
                raise ValueError(f'Ruolo non corrisponde: {id} è {by_id[id].role} anziché {role}')
    effective = {}
    subs = []
    missing = []
    for role in ROLES:
        pool = [by_id[id] for id in bench[role] if by_id[id].valid]
        effective[role] = []
        for id in starters[role]:
            p = by_id[id]
            if p.valid:
                effective[role].append(p)
            elif pool:
                sub = pool.pop(0)
                effective[role].append(sub)
                subs.append({'out': id, 'in': sub.id, 'ruolo': role})
            else:
                missing.append({'sv_senza_copertura': id, 'ruolo': role})
    if missing:
        return {'status': 'NON_CALCOLABILE_CON_REGOLE_NOTE', 'mancanti': missing,
                'motivo': 'Manca una copertura con voto: servono regole su giocatori di ufficio e conteggio ufficiale.'}
    eleven = [p for role in ROLES for p in effective[role]]
    captain_id = forecast['capitano']
    vice_id = forecast['vicecapitano']
    if captain_id in {p.id for p in eleven}:
        cap_id = captain_id
    elif vice_id in {p.id for p in eleven}:
        return {'status': 'VICECAPITANO_DA_VERIFICARE', 'sostituzioni': subs,
                'motivo': 'Capitano senza voto. La regola esatta di subentro del vice non è confermata.'}
    else:
        return {'status': 'CAPITANO_SENZA_VOTO', 'sostituzioni': subs}
    gk = effective['P'][0]
    d = effective['D']
    avg = (gk.vote + sum(sorted((p.vote for p in d), reverse=True)[:3])) / 4
    mod = defence_bonus(avg)
    base = sum(p.fv for p in eleven)
    cap = captain_bonus(by_id[cap_id].vote)
    return {'status': 'CALCOLATO_SE_FV_GIA_NORMALIZZATI',
            'totale': round(base + mod + cap, 3),
            'somma_fv': round(base, 3), 'modificatore_difesa': mod,
            'media_modificatore': round(avg, 3), 'bonus_capitano': cap,
            'capitano_effettivo': cap_id,
            'sostituzioni': subs, 'titolari_effettivi': {r: [p.id for p in effective[r]] for r in ROLES}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('voti_csv', type=Path)
    parser.add_argument('--previsione', type=Path, help='JSON originale con titolari/panchina/capitano/vicecapitano')
    parser.add_argument('--output', type=Path, help='Salva il rapporto JSON su file')
    args = parser.parse_args()
    try:
        players = load_csv(args.voti_csv)
        result = {'perfetta': solve_best_xi(players)}
        if args.previsione:
            forecast = json.loads(args.previsione.read_text(encoding='utf-8'))
            result['previsione'] = score_forecast(players, forecast)
            if 'totale' in result['previsione']:
                result['rimpianto_punti'] = round(result['perfetta']['totale'] - result['previsione']['totale'], 3)
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(payload + '\n', encoding='utf-8')
        print(payload)
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as e:
        print(f'ERRORE: {e}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
