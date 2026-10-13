r"""Difficulty baselines that bring every game's LEGENDARY time-to-kill as close together
as possible (user, 2026-10-13), from the measured rows in reports/ttk/*.json.

The enhancer's Options -> Run rules -> Difficulty baseline sets four matg dials per game
(Enemy Vitality, Enemy Shield, Enemy Damage, Rate Of Fire; absolute values, 0 = vanilla).
Here:
  * Enemy Vitality / Enemy Shield scale the enemies' body / shield pools -> YOUR time to
    kill them. Fitted as two factors per game.
  * Enemy Damage scales what the AI hits you for -> THEIR time to kill you. One factor.
  * Rate Of Fire stays vanilla: the AI trigger rate is capped at the weapon's top rate
    (every collector), so the dial acts unevenly between games and weapons.
TARGETS: per category the cross-game GEOMETRIC MEAN of today's times, so the overall
Legendary difficulty stays where it is on average and only the spread shrinks.
  player -> enemy  categories = (Elite | Brute-or-Knight) x weapon role (automatic,
                   plasma, precision);
  enemy -> player  categories = Elite | Brute-or-Knight, PACED times (default weapons).
FIT: per game, grid search minimising the squared log error to the targets. A factor
changes the shot COUNT exactly (ttk_common.shots_to_kill on the row's own pools and
hits); the time follows: player rows scale their time by (n'-1)/(n-1) (keeps each gun's
reloads / heat roughly in proportion), enemy rows are re-simulated with ai_times.
VALIDATION: at factor 1 every row must reproduce its stored shot count (printed).

ASSUMPTION (stated): from Halo 2 on the Legendary pools are the CHARACTER's legendary
vitality and the matg vitality / shield dials read 1.0; the dial is assumed to multiply
them as it does in Halo 1. The Knight shares the Brute column (the user's 'Brute / Knight').

    python ttk_calibrate.py            -> reports/ttk_calibration.md
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_common as tc     # noqa: E402

SRC = os.path.join(HERE, 'reports', 'ttk')
OUT = os.path.join(HERE, 'reports', 'ttk_calibration.md')
ORDER = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
#: today's Legendary dials (matg Difficulty, 'Impossible' / 'imposs.'), as re-read by the
#: collectors: vitality, shield, damage, rate of fire
CURRENT = {'Halo 1': (1.4, 1.4, 1.8, 1.5), 'Halo 2': (1.0, 1.0, 1.5, 1.5),
           'Halo 3': (1.0, 1.0, 1.6, 1.0), 'Halo 3: ODST': (1.0, 1.0, 1.6, 1.0),
           'Halo Reach': (1.0, 1.0, 1.6, 1.0), 'Halo 4': (1.0, 1.0, 1.3, 1.0)}
ROLE = {'automatic': ('assault rifle', 'smg'),
        'plasma': ('plasma rifle', 'plasma repeater', 'storm rifle'),
        'precision': ('pistol', 'battle rifle', 'magnum', 'dmr')}
#: enemy -> player rows used (the default weapon; ODST's 2nd-most-common BPR row is not)
SKIP_WEAPON = ('2nd most common',)
GRID = [round(0.30 + 0.01 * i, 2) for i in range(271)]          # 0.30 .. 3.00
SPLIT = '--split' in sys.argv


def v(x):
    if isinstance(x, dict) and 'value' in x:
        return float(x['value'])
    if isinstance(x, (list, tuple)):
        return float(x[0])
    return float(x)


def first(inp, *keys):
    for k in keys:
        if k in inp:
            return v(inp[k])
    raise KeyError(keys)


def role(weapon):
    w = weapon.lower()
    for r, keys in ROLE.items():
        if any(k in w for k in keys):
            return r
    return None


def enemy_class(name):
    return 'Elite' if 'elite' in name.lower() else 'Brute / Knight'


def extract(game, r):
    inp = r['inputs']
    t = inp.get('target') if isinstance(inp.get('target'), dict) else {}
    hs = first(inp, 'shield hit', 'hit on shield', 'hit vs shield')
    hb = first(inp, 'body hit', 'hit on body', 'hit vs body')
    if r['direction'] == 'player->enemy':
        if game == 'Halo 1':
            dv = next(val for k, val in t.items() if 'Impossible Enemy Vitality' in k)
            ds = next(val for k, val in t.items() if 'Impossible Enemy Shield' in k)
            S = t['actv Shield Vitality (+0x204)'] * ds
            B = t['actv Body Vitality (+0x200)'] * dv
        elif 'shield pool' in t:
            S, B = t['shield pool'], t['body pool']
        elif 'enemy shield (legendary)' in inp:
            S = v(inp['enemy shield (legendary)']) * v(inp.get('difficulty enemy shield', 1.0))
            B = v(inp['enemy body (legendary)']) * v(inp.get('difficulty enemy vitality', 1.0))
        else:
            S = v(inp['target legendary shield vitality']) * v(inp['legendary enemy shield'])
            B = v(inp['target legendary body vitality']) * v(inp['legendary enemy vitality'])
        return {'S': S, 'B': B, 'hs': hs, 'hb': hb}
    if game == 'Halo 1':
        S = t['coll Maximum Shield Vitality (+0xCC)']
        B = t['coll Maximum Body Vitality (+0x8)']
    elif 'shield pool' in t:
        S, B = t['shield pool'], t['body pool']
    elif 'player shield' in inp:
        S, B = v(inp['player shield']), v(inp['player body'])
    else:
        S, B = v(inp['player shield vitality']), v(inp['player body vitality'])
    sps = first(inp, 'shots per second used (capped, 30 Hz quantised)',
                'shots per second used (capped)', 'shots per second (end pattern)',
                'ai shots per second')
    bd = first(inp, 'burst duration used (mean)', 'burst duration (end)',
               *[k for k in inp if 'really accurate burst duration' in k])
    bs = first(inp, 'burst separation used (x Impossible Burst Separation)',
               'burst separation used', 'burst separation used (mean x dial)',
               'burst separation (end, x difficulty)', 'ai burst separation s')
    return {'S': S, 'B': B, 'hs': hs, 'hb': hb, 'sps': sps, 'bd': bd, 'bs': bs}


def load():
    rows = []
    for p in glob.glob(os.path.join(SRC, 'ttk_*.json')):
        d = json.load(open(p, encoding='utf-8'))
        for r in d['rows']:
            if r.get('seconds') is None or any(s in r['weapon'] for s in SKIP_WEAPON):
                continue
            if r['direction'] == 'player->enemy':
                rl = role(r['weapon'])
                if rl is None:
                    continue
                cat = ('you kill', enemy_class(r['target']), rl)
            else:
                cat = ('kills you', enemy_class(r['attacker']), 'paced')
            import ttk_report
            r['weapon'] = ttk_report.NAMES.get(r['weapon'], r['weapon'])
            x = extract(d['game'], r)
            rows.append({'game': d['game'], 'row': r, 'cat': cat, 'x': x})
    return rows


def player_time(item, kv, ks):
    x, r = item['x'], item['row']
    n0 = r['shots']
    n, _ = tc.shots_to_kill(x['S'] * ks, x['B'] * kv, x['hs'], x['hb'])
    if n is None:
        return None, None
    t0 = r['seconds']
    return n, (t0 * (n - 1) / (n0 - 1) if n0 > 1 else t0)


def enemy_time(item, f):
    x = item['x']
    n, _ = tc.shots_to_kill(x['S'], x['B'], x['hs'] * f, x['hb'] * f)
    held, paced = tc.ai_times(n, x['sps'], x['bd'], x['bs'])
    # rows that were quantised / ramped by their collector keep that ratio
    r = item['row']
    base = tc.ai_times(r['shots'], x['sps'], x['bd'], x['bs'])[1]
    stored = r.get('seconds_paced') or r['seconds']
    scale = stored / base if base else 1.0
    return n, paced * scale if paced is not None else None


def main():
    rows = load()
    # validation
    bad = []
    for it in rows:
        if it['cat'][0] == 'you kill':
            n, _t = player_time(it, 1.0, 1.0)
        else:
            n, _t = enemy_time(it, 1.0)
        if n != it['row']['shots']:
            bad.append('%s %s %s: stored %s, recomputed %s' % (
                it['game'], it['row']['weapon'], it['cat'][1], it['row']['shots'], n))
    # targets: geometric mean per category over the games that have it
    cats = {}
    for it in rows:
        cats.setdefault(it['cat'], []).append(it['row']['seconds_paced'] if it['cat'][0] ==
                                              'kills you' else it['row']['seconds'])
    target = {c: math.exp(sum(math.log(t) for t in ts) / len(ts)) for c, ts in cats.items()}

    def err(items, fn):
        e = 0.0
        for it in items:
            _n, t = fn(it)
            if t is None or t <= 0:
                return float('inf')
            e += (math.log(t) - math.log(target[it['cat']])) ** 2
        return e

    fits = {}
    for g in ORDER:
        mine = [it for it in rows if it['game'] == g]
        if not mine:
            continue
        pl = [it for it in mine if it['cat'][0] == 'you kill']
        en = [it for it in mine if it['cat'][0] == 'kills you']
        best = (float('inf'), 1.0, 1.0)
        # shield factor only matters where the enemy has a shield
        for kv in GRID:
            # ONE factor for vitality and shield (default): each game keeps its own
            # shield / body balance. --split fits them separately (lopsided results:
            # the totals alone barely tell shield from body toughness).
            for ks in ((GRID if any(it['x']['S'] > 0 for it in pl) else [1.0]) if SPLIT
                       else [kv]):
                e = err(pl, lambda it: player_time(it, kv, ks))
                if e < best[0]:
                    best = (e, kv, ks)
        bf = min(GRID, key=lambda f: err(en, lambda it: enemy_time(it, f))) if en else 1.0
        cv, cs, cd, cr = CURRENT[g]
        new = (round(cv * best[1], 2), round(cs * best[2], 2), round(cd * bf, 2), cr)
        # evaluate with the ROUNDED dials
        kv, ks, f = new[0] / cv, new[1] / cs, new[2] / cd
        res = []
        for it in mine:
            if it['cat'][0] == 'you kill':
                n, t = player_time(it, kv, ks)
                t0 = it['row']['seconds']
            else:
                n, t = enemy_time(it, f)
                t0 = it['row'].get('seconds_paced') or it['row']['seconds']
            res.append((it, t0, t, n))
        fits[g] = (new, res)

    lines = ['# Difficulty baselines for equal Legendary time-to-kill', '',
             'Fitted from `reports/ttk_legendary.md` (method there; this script: '
             '`sprint_toolkit/ttk_calibrate.py`). Targets = the cross-game geometric mean '
             'per category, so Legendary overall stays as hard as today on average; only the '
             'differences between games shrink. Rate of Fire stays vanilla (the AI trigger '
             'rate is capped at the weapon rate, so that dial acts unevenly).', '',
             '## Options -> Run rules -> Difficulty baseline (Legendary)', '',
             '| game | Vitality | Shield | Damage | Rate of Fire |', '|---|---|---|---|---|']
    for g in ORDER:
        if g in fits:
            (nv, ns, nd, nr), _res = fits[g]
            cv, cs, cd, cr = CURRENT[g]
            lines.append('| %s | %.2f (now %.2f) | %.2f (now %.2f) | %.2f (now %.2f) | '
                         'vanilla (%.2f) |' % (g, nv, cv, ns, cs, nd, cd, cr))
    lines += ['', '## Targets', '', '| category | target | games |', '|---|---|---|']
    for c in sorted(target):
        lines.append('| %s %s (%s) | %.2f s | %d |' % (c[0], c[1], c[2], target[c], len(cats[c])))
    lines += ['', '## Before -> after, per row', '',
              '| game | direction | enemy | weapon | before | after | target | hits after |',
              '|---|---|---|---|---|---|---|---|']
    spread_before, spread_after = [], []
    for g in ORDER:
        if g not in fits:
            continue
        for it, t0, t, n in fits[g][1]:
            tg = target[it['cat']]
            spread_before.append(abs(math.log(t0 / tg)))
            spread_after.append(abs(math.log(t / tg)) if t else 0)
            lines.append('| %s | %s | %s | %s | %.2f s | %s | %.2f s | %s |' % (
                g, it['cat'][0], it['cat'][1], it['row']['weapon'], t0,
                '%.2f s' % t if t else '-', tg, n))
    mb = math.exp(sum(spread_before) / len(spread_before))
    ma = math.exp(sum(spread_after) / len(spread_after))
    lines += ['', 'Average distance from the target: before x%.2f, after x%.2f '
              '(geometric; 1.00 = every row exactly on target).' % (mb, ma)]
    if bad:
        lines += ['', '## Validation FAILED for these rows (extraction differs from the '
                  'collector)', ''] + ['- ' + b for b in bad]
    lines.insert(4, ('Enemy Vitality and Enemy Shield were fitted SEPARATELY (--split).' if SPLIT else
                     'Enemy Vitality and Enemy Shield move by ONE factor per game, so every game '
                     'keeps its own shield / body balance (--split fits them separately; the '
                     'totals alone barely tell the two apart, so that gives lopsided dials).'))
    lines.insert(5, '')
    with open(OUT if not SPLIT else OUT.replace('.md', '_split.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:20]))
    print('validation: %d row(s) differ' % len(bad))
    for b in bad:
        print('  ' + b)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
