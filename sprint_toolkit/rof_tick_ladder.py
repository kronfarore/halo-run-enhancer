r"""Rate-of-fire card ladders for Halo 1 and Halo 2 under their 30 Hz fire rule (READ-ONLY).

    python rof_tick_ladder.py            -> reports/rof_tick_ladder.md + .json

Both games fire by the RESET rule (measured: Halo 1 h1_weapon_state_probe / the SMG magazine
dumps; Halo 2 the Plasma Repeater port, reports/h2_fire_rule.jsonl): every tick rate / 30 is
added in float32, a shot at 1, the sum reset -> a shot every ceil(30 / rate) ticks. A gun can
only FIRE 30 / n rounds a second (30, 15, 10, 7.5, 6, 5, 4.29, 3.75 ...). Halo 1 also CAPS at
15/s (2 ticks: 22.5 and 30 tags fired 15/s). Halo 2 fires 30/s (1 tick): MEASURED 2026-11-23
(rof_test_stage, reports/rof_test.jsonl), as do Halo 3 / ODST / Reach / Halo 4 by the same reset rule.

SUPERSEDED (user, 2026-11-23): the per-pick ladders are NOT wanted. Salvo Shooting raises Shots Per
Fire as well as Rounds Per Second, so a pick changes the output even where the rate cannot move.
And Fire Recovery Time does not exist in Halo 1 / 2 (it is implemented from Halo 3 on): the Halo 2
'paced by Fire Recovery Time' notes below are WRONG -- in Halo 1 and 2 the rate gives the pace.
Kept only as a record of which rate picks fire the same.

So the Salvo Shooting card's linear *1.2 a pick often changes nothing: an SMG at 15 needs x2
before it fires faster. This tool reads every Salvo Shooting card's Halo 1 / Halo 2 weapon tag
(halo.json), shows what the current steps fire, and SUGGESTS per-pick ladders (`steps` and
`inverse_steps`, the patcher's existing irregular ladders, applied to vanilla) in which EVERY
pick moves the fired rate at least one rung, aiming at the rate the linear +-20% a pick would
give. A ladder entry is a multiplier on both rate fields (the ramp keeps its shape), chosen a
hair above the rung so float32 lands on it. Inverted ladders stop at x0.2 of the fired rate
(the 4th pick) and hold: the linear x0.8 reaches x0 on the 5th pick, and Halo 2 reads a rate
of 0 as 30 (zero_is) -- the inverted card would then fire at the top rate.

Halo 2 weapons paced by Fire Recovery Time (pistol, sniper, rocket, shotgun, beam rifle,
Brute Shot, Mauler, DMR port) or by a charge (Spartan Laser, charged plasma pistol) gain
nothing from the rate card: listed as such (the Fire Recovery Time card is their rate card).
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import ttk_halo2 as t2  # noqa: E402
from reclaimer.hek.defs.weap import weap_def  # noqa: E402

H1_TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
OUT = os.path.join(HERE, 'reports', 'rof_tick_ladder')
PICKS = 5
STEP = 0.2                 # the card's linear step (halo.json *1.2)
INV_FLOOR = 0.2            # the inverted ladder's last rung: x0.2 of the fired rate
MARGIN = 1.002             # a ladder rate sits this far above its rung (float32 safety)
TOP = {'Halo 1': 2, 'Halo 2': 1}   # fastest interval in ticks (H1 measured cap 15/s)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def ticks(rate, game):
    """Ticks between shots for a flat rate (float32 sum from 0 to 1, reset)."""
    if rate <= 0:
        return None
    step, s, n = f32(rate / 30.0), 0.0, 0
    while s < 1.0:
        s = f32(s + step)
        n += 1
    return max(n, TOP[game])


def fired(rate, game):
    n = ticks(rate, game)
    return 30.0 / n if n else 0.0


def h1_weapon(rel):
    p = os.path.join(H1_TAGS, rel + '.weapon')
    if not os.path.exists(p):
        return None
    w = weap_def.build(filepath=p).data.tagdata.weap_attrs
    tr = w.triggers.STEPTREE[0]
    lo, hi = tr.firing.rounds_per_second
    return {'rps': [lo, hi], 'recovery': 0.0, 'spf': 1, 'charge': tr.charging.charging_time,
            'tag': rel}


def h2_weapon(rel):
    try:
        w = t2.read_weapon(rel, {})
    except (Exception, SystemExit):   # not in H2EK, or no projectile damage to read
        return None
    beh = w['trigger behavior'] or ''
    return {'rps': [w['rps'][0] or 30.0, w['rps'][1] or 30.0],   # zero_is 30
            'recovery': w['fire recovery'], 'spf': int(w['shots per fire'][1] or 1),
            'charge': 1.0 if 'charge' in beh else 0.0, 'tag': rel}


def fmt(x):
    return ('%.3f' % x).rstrip('0').rstrip('.')


def ladder(w, game, up):
    """[(op, fired hi, fired lo)] per pick, or [] when the card cannot move the rate."""
    lo, hi = w['rps']
    t0 = ticks(hi, game)
    f0 = 30.0 / t0
    out, t_prev = [], t0
    for k in range(1, PICKS + 1):
        if up:
            want = f0 * (1 + STEP * k)
            t = min(t_prev - 1, max(TOP[game], int(round(30.0 / want))))
            if t < TOP[game]:
                break
        else:
            want = f0 * max(INV_FLOOR, 1 - STEP * k)
            t = max(t_prev + 1, int(round(30.0 / want)))
            if k > 1 and 1 - STEP * k < INV_FLOOR - 1e-9:
                break       # past x0.2: the last entry holds (stack_op)
        m = (30.0 / t) * MARGIN / hi
        m = float('%.4g' % m)
        assert ticks(hi * m, game) == t, (w['tag'], hi, m, t)
        out.append(('*' + fmt(m), fired(hi * m, game), fired(lo * m, game)))
        t_prev = t
    return out


def linear(w, game, up):
    lo, hi = w['rps']
    res = []
    for k in range(1, PICKS + 1):
        m = max(0.0, 1 + (STEP if up else -STEP) * k)
        if m == 0.0:
            # Halo 2 zero_is 30: a rate of 0 reads as 30; Halo 1: the gun never fires
            res.append(30.0 / TOP[game] if game == 'Halo 2' else 0.0)
        else:
            res.append(fired(hi * m, game))
    return res


def main():
    cards = json.load(open(os.path.join(ROOT, 'halo.json'), encoding='utf-8'))
    found = []          # (owner, card name, card): every card writing Rounds Per Second

    def rps_card(c):
        ts = c.get('targets')
        flat = [t for l in ts.values() for t in l] if isinstance(ts, dict) else (ts or [])
        return any(isinstance(t, dict) and str(t.get('field', '')).startswith('Rounds Per Second')
                   for t in flat)
    for section in ('Player Modifiers', 'Enemy modifiers'):
        for group in cards[section].values():
            if not isinstance(group, dict):
                continue
            for owner, cs in group.items():
                if not isinstance(cs, dict):
                    continue
                for cname, c in cs.items():
                    if isinstance(c, dict) and rps_card(c):
                        found.append((owner, cname, c))
    rows = []
    for wname, cname, c in found:
        if True:
            tags = c.get('tag') if isinstance(c.get('tag'), dict) else {}
            if isinstance(c.get('tag'), str):
                # one path for the card: only usable when it names ONE of Halo 1 / 2
                gl = c.get('game') or []
                gl = [gl] if isinstance(gl, str) else gl
                mine = [g for g in gl if g in ('Halo 1', 'Halo 2')]
                if len(mine) == 1:
                    tags = {mine[0]: c['tag']}
            for game in ('Halo 1', 'Halo 2'):
                rel = tags.get(game)
                if not rel:
                    continue
                rel = rel.split(' ', 1)[1].split(' & ')[0]
                w = h1_weapon(rel) if game == 'Halo 1' else h2_weapon(rel)
                r = {'weapon': wname, 'card': cname, 'game': game, 'tag': rel}
                if w is None:
                    r['note'] = 'tag not found in the kit'
                    rows.append(r)
                    continue
                lo, hi = w['rps']
                r.update(rate=[lo, hi], fires=[fired(lo, game), fired(hi, game)],
                         recovery=w['recovery'], spf=w['spf'])
                rec_t = int(math.ceil(w['recovery'] * 30 - 1e-6)) if w['recovery'] else 0
                if game == 'Halo 2' and w['charge'] and 'Charged' not in cname and not w['recovery']:
                    r['note'] = 'charge weapon: paced by the charge, the rate card does nothing'
                elif game == 'Halo 2' and w['charge'] and 'Charged' in cname:
                    r['note'] = 'charged shot: paced by the charge, the rate card does nothing'
                elif game == 'Halo 2' and rec_t and w['spf'] <= 1 and rec_t >= ticks(hi, game):
                    r['note'] = ('paced by Fire Recovery Time %.3g s (%d ticks): the rate card '
                                 'does nothing (its Fire Recovery Time card is the rate card)'
                                 % (w['recovery'], rec_t))
                if 'note' not in r:
                    r['linear_up'] = linear(w, game, True)
                    r['linear_inv'] = linear(w, game, False)
                    r['steps'] = ladder(w, game, True)
                    r['inverse_steps'] = ladder(w, game, False)
                    if w['spf'] > 1:
                        r['note'] = ('%d-round burst: the rate is the cadence INSIDE a burst; the '
                                     'gap between bursts is Fire Recovery Time' % w['spf'])
                rows.append(r)
    json.dump(rows, open(OUT + '.json', 'w', encoding='utf-8'), indent=1)

    def rates(v):
        return '-'.join(fmt(x) for x in v) if v[0] != v[1] else fmt(v[0])

    L = ['# Salvo Shooting under the 30 Hz fire rule: Halo 1 and Halo 2', '',
         '**SUPERSEDED (user, 2026-11-23): the suggested ladders are not wanted** -- Salvo Shooting '
         'adds Shots Per Fire too, so a pick still changes the output where the rate cannot move. '
         'Fire Recovery Time does not exist in Halo 1 / 2 (Halo 3 on), so the Halo 2 "paced by Fire '
         'Recovery Time" rows are wrong. Halo 2 fires 30/s at a 30 tag (measured 2026-11-23, '
         'reports/rof_test.jsonl). Kept as a record only.', '',
         'Generated by `sprint_toolkit/rof_tick_ladder.py` (read-only). A gun fires only 30/n '
         'rounds a second (n whole ticks): 30, 15, 10, 7.5, 6, 5, 4.29, 3.75, 3.33, 3, 2.73, 2.5 ... '
         'Halo 1 caps at 15/s (measured); Halo 2 fires 30/s (measured 2026-11-23).', '',
         '* **now**: what picks 1-5 of today\'s linear step (x1.2 a pick; inverted x0.8) FIRE. A '
         'repeated number = a pick that changes nothing.',
         '* **suggested**: a `steps` / `inverse_steps` entry per pick (a multiplier on BOTH rate '
         'fields, applied to vanilla; past the last entry it holds = saturated), each pick at '
         'least one rung, aiming at the linear +-20% a pick. Fired rate after the arrow (the low '
         'end of a ramp in brackets).',
         '* The inverted ladder stops at x0.2 of the fired rate. TODAY the 5th inverted pick is '
         'x0 -- in Halo 2 a rate of 0 reads as 30 (zero_is), so it would fire FASTER; in Halo 1 '
         'the gun would stop firing.', '']
    for game in ('Halo 1', 'Halo 2'):
        L += ['## ' + game, '',
              '| weapon (card) | tag rate | fires | now up 1-5 | suggested up | now inverted 1-5 | '
              'suggested inverted |', '|---|---|---|---|---|---|---|']
        notes = []
        for r in rows:
            if r['game'] != game:
                continue
            name = r['weapon'] + ('' if r['card'] == 'Salvo Shooting' else
                                  ' (%s)' % r['card'].replace('Salvo Shooting ', '').strip('()'))
            if 'rate' not in r:
                notes.append('* %s: %s (%s)' % (name, r['note'], r['tag']))
                continue
            if 'steps' not in r:
                L.append('| %s | %s | %s | %s | | | |' % (name, rates(r['rate']), rates(r['fires']),
                                                          r['note']))
                continue

            def lad(l):
                return ', '.join('%s -> %s%s' % (op, fmt(fh), '' if abs(fl - fh) < 1e-9 else
                                                 ' (%s)' % fmt(fl)) for op, fh, fl in l) or 'top rung: none'
            L.append('| %s | %s | %s | %s | %s | %s | %s |' % (
                name, rates(r['rate']), rates(r['fires']), ', '.join(fmt(x) for x in r['linear_up']),
                lad(r['steps']), ', '.join(fmt(x) for x in r['linear_inv']), lad(r['inverse_steps'])))
            if r.get('note'):
                notes.append('* %s: %s' % (name, r['note']))
        L += [''] + notes + ['']
    open(OUT + '.md', 'w', encoding='utf-8').write('\n'.join(L))
    print('wrote %s.md / .json (%d rows)' % (OUT, len(rows)))


if __name__ == '__main__':
    main()
