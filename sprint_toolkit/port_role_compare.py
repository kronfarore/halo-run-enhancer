r"""Where does a ported weapon sit among the weapons whose ROLE it shares? (2026-10-05)

The field audit (port_field_audit.py) asks "does every number come from the right
place"; this asks "does the result PLAY like it belongs between its neighbours". It
reads each weapon's weapon / projectile / damage effect tags and derives role metrics:

    hit        damage per projectile (upper bound; x projectiles per shot)
    interval   seconds between shots: 1 / rounds per second, or the fire recovery time
               when that is longer (a semi-automatic beam rifle)
    burst      shots and damage from cold until OVERHEATED, and the seconds it takes
    recover    seconds from overheated until it fires again:
               (overheated threshold - recovery threshold) / overheated heat loss
    cycle dps  burst damage / (burst seconds + recover seconds) -- holding the trigger
    battery    shots per battery (1 / age per round) and the damage in one battery
    + headshots (damage flag or specific damage 'sniper'), range, zoom, aim assist

ASSUMPTION, stated rather than hidden: heat is lost only while NOT firing (no decay is
counted inside a burst). Measured in game it may be otherwise -- the burst numbers are
then upper bounds on heat, lower bounds on time.

    python port_role_compare.py focus_rifle [--balanced]

`--balanced` applies the port's catalog balance rows (weapon_ports_catalog.json) over
its built values, as the patcher does with the balance option on.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_field_audit as fa                                       # noqa: E402

R, P = r'objects\weapons\rifle', r'objects\weapons\pistol'
#: comparison sets: label -> (kit, weapon tag, projectile tag stem). The stem names both
#: the .projectile and the .damage_effect beside it (the beams keep them together).
SETS = {
    'focus_rifle': {
        'game': 'Halo 4', 'port': 'Focus Rifle', 'port_label': 'H4 Focus (port)',
        'weapons': [
            ('Reach Focus (source)', 'HREK', R + r'\focus_rifle\focus_rifle.weapon',
             R + r'\focus_rifle\projectiles\focus_rifle_beam'),
            ('Reach Sniper (bridge)', 'HREK', R + r'\sniper_rifle\sniper_rifle.weapon',
             R + r'\sniper_rifle\projectiles\sniper_rifle_bullet'),
            ('H4 Focus (port)', 'H4EK', R + r'\focus_rifle\focus_rifle.weapon',
             R + r'\focus_rifle\projectiles\focus_rifle_beam'),
            ('H4 Beam Rifle', 'H4EK', R + r'\storm_beam_rifle\storm_beam_rifle.weapon',
             R + r'\storm_beam_rifle\projectiles\storm_beam_rifle_beam'),
            # the player-side "friendly" beam deals 0 in Halo 4 (the port's copy of it was
            # silent until it had its own damage); the ENEMY beam carries the real numbers
            ('H4 Sentinel Beam', 'H4EK', P + r'\storm_sentinel_beam\storm_sentinel_beam.weapon',
             P + r'\storm_sentinel_beam\projectiles\storm_sentinel_beam_beam_enemy'),
            ('H4 Sniper (bridge)', 'H4EK', R + r'\storm_sniper_rifle\storm_sniper_rifle.weapon',
             R + r'\storm_sniper_rifle\projectiles\storm_sniper_rifle_bullet'),
        ]},
}


def first(v, *names, default=None):
    """The first field (by leaf name, barrel 0 / root preferred) that exists."""
    for n in names:
        for k, (_t, x) in v.items():
            if k.rsplit('/', 1)[-1].rstrip("'") == n and '[1]' not in k and 'aim assist modes' not in k:
                nums = fa.nums(x)
                if nums:
                    return nums
                return x
    return default


def num(v, *names, i=-1, default=0.0):
    x = first(v, *names)
    if isinstance(x, list) and x:
        return x[i] if len(x) > abs(i) - (1 if i < 0 else 0) else x[0]
    return default


def metrics(kit, wtag, stem, overrides=None):
    w = fa.flatten(kit, wtag)
    p = fa.flatten(kit, stem + '.projectile')
    d = fa.flatten(kit, stem + '.damage_effect')
    ov = {k.lower(): v for k, v in (overrides or {}).items()}

    def o(name, value):
        return float(ov[name]) if name in ov and isinstance(ov[name], (int, float)) else value
    hit = o('damage upper bound max', o('damage upper bound', num(d, 'damage upper bound')))
    pps = o('projectiles per shot', num(w, 'projectiles per shot', default=1.0)) or 1.0
    rps = o('rounds per second max', o('rounds per second', num(w, 'rounds per second')))
    recovery = o('fire recovery time', num(w, 'fire recovery time'))
    interval = max(1.0 / rps if rps else 0.0, recovery if hit >= 20 else 0.0)
    heat = o('heat generated per round', num(w, 'heat generated per round'))
    over = num(w, 'overheated threshold', default=0.0) or 1.0
    rec_thr = o('heat recovery threshold', num(w, 'heat recovery threshold'))
    over_loss = o('overheated heat loss per second', num(w, 'overheated heat loss per second'))
    loss = o('heat loss per second', num(w, 'heat loss per second'))
    age = o('age generated per round', num(w, 'age generated per round'))
    flags = first(d, 'flags', default='')
    flags = '%d' % flags[0] if isinstance(flags, list) and flags else str(flags)
    specific = str(first(d, 'specific_damage', default=''))
    m = {'hit': hit * pps, 'interval': interval, 'rps': 1.0 / interval if interval else 0.0,
         'dps_raw': hit * pps / interval if interval else 0.0,
         'range': o('maximum range', num(p, 'maximum range')),
         'zoom': first(w, 'magnification range', default='-'),
         'autoaim': (num(w, 'autoaim angle'), num(w, 'autoaim range')),
         'magnet': (num(w, 'magnetism angle'), num(w, 'magnetism range')),
         # Reach prints flag NAMES; Halo 4 prints the number, and bit 1 (2) is "can cause
         # headshots" -- set on the H4 Sniper, Beam Rifle, Magnum, DMR, clear on the AR
         'headshot': 'yes' if ('headshot' in flags or specific == 'sniper'
                               or (kit == 'H4EK' and flags.split()[0].isdigit()
                                   and int(flags.split()[0]) & 2)) else 'no',
         'damage type': str(first(d, 'general_damage', default='-'))}
    if heat > 0:
        shots = math.ceil(over / heat)
        m['burst shots'] = shots
        m['burst dmg'] = shots * m['hit']
        m['burst s'] = shots * interval
        m['recover s'] = (over - rec_thr) / over_loss if over_loss else float('inf')
        m['cycle dps'] = m['burst dmg'] / (m['burst s'] + m['recover s'])
        m['cool 1 shot s'] = heat / loss if loss else float('inf')
    if age > 0:
        m['battery shots'] = int(round(1.0 / age))
        m['battery dmg'] = m['battery shots'] * m['hit']
    else:
        mag = first(w, 'rounds loaded maximum', default=None)
        tot = first(w, 'rounds total maximum', default=None)
        if isinstance(mag, list):
            m['magazine'] = '%d / %d' % (mag[0], tot[0] if isinstance(tot, list) else 0)
    return m


def catalog_rows(game, weapon):
    cat = json.load(open(os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json'),
                         encoding='utf-8')).get(game) or []
    for e in (cat if isinstance(cat, list) else [cat]):
        if e.get('weapon') == weapon:
            return {r['field']: r['value'] for r in e.get('balance') or ()}
    return {}


ROWS = [('hit', 'damage per shot', '%.1f'), ('interval', 'seconds per shot', '%.3f'),
        ('dps_raw', 'dps while firing', '%.0f'), ('burst shots', 'shots to overheat', '%d'),
        ('burst dmg', 'damage to overheat', '%.0f'), ('burst s', 'seconds to overheat', '%.2f'),
        ('recover s', 'overheat recovery s', '%.2f'), ('cycle dps', 'dps holding trigger', '%.0f'),
        ('cool 1 shot s', 'cool-off per shot s', '%.2f'),
        ('battery shots', 'shots per battery', '%d'), ('battery dmg', 'damage per battery', '%.0f'),
        ('magazine', 'magazine / reserve', '%s'), ('headshot', 'headshots', '%s'),
        ('damage type', 'damage type', '%s'), ('range', 'max range', '%.0f'),
        ('zoom', 'zoom', '%s'), ('autoaim', 'autoaim deg / range', '%s'),
        ('magnet', 'magnetism deg / range', '%s')]


def fmt(fmtstr, v):
    if v is None:
        return '-'
    if isinstance(v, (list, tuple)):
        return '/'.join('%g' % x for x in v)
    try:
        return fmtstr % v
    except TypeError:
        return str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('set', choices=sorted(SETS))
    ap.add_argument('--balanced', action='store_true')
    a = ap.parse_args()
    S = SETS[a.set]
    cols = []
    for label, kit, w, stem in S['weapons']:
        cols.append((label, metrics(kit, w, stem)))
        if label == S['port_label'] and a.balanced:
            cols.append((label + ' balanced',
                         metrics(kit, w, stem, catalog_rows(S['game'], S['port']))))
    width = 20
    print('%-24s' % '' + ''.join('%-*s' % (width, c[0][:width - 1]) for c in cols))
    for key, title, f in ROWS:
        if not any(key in m for _l, m in cols):
            continue
        print('%-24s' % title + ''.join('%-*s' % (width, fmt(f, m.get(key))[:width - 1])
                                        for _l, m in cols))
    print('\n(heat is assumed to decay only while NOT firing; see the docstring)')


if __name__ == '__main__':
    main()
