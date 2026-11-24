r"""Do the ports' Balanced numbers still hold under the MEASURED 30 Hz fire rule? (READ-ONLY)

    python rof_balance_check.py            -> reports/rof_balance_check.md + .json

Every game fires by the reset rule (reports/rof_test.jsonl, 2026-11-23): a shot every
ceil(30 / rate) ticks, a fire recovery rounded up to ticks (assumed), no cap. A port's Balanced
rate came from the RATIO rule, field by field on TAG values: port = source x yardstick(target) /
yardstick(source), leg by leg. The ratio rule's intent, in what the guns FIRE (shots a second from
rate, fire recovery and shots per fire, by the reset rule):

    intended = fired(source) x PRODUCT over legs fired(yard, to) / fired(yard, from)
    actual   = fired(port, its Balanced numbers in the target game)

and the damage that restores the intended damage per second is   Balanced damage x k,
k = intended / actual. (The SAW: Halo 4's 20/s is held to 15 by its 0.067 s recovery, the AR / SMG
yardsticks fire their tags, the Halo 2 SAW's 20 fires 15 -> k = 1. Comparing TAG cadences instead
would wrongly say x4/3: the ratio rule scaled the rate and the recovery separately.)
FIRE RECOVERY paces only a one-shot-a-pull weapon (shots per fire >= 1, or a rate of 0); a held
automatic (shots per fire 0) ignores it -- INFERRED (Reach's Needler, 12/s with 0.2 recovery, would
fire 5/s), not measured. A chain with no gun leg (a grenade yardstick) keeps the port's tag cadence
as the intent, scaled by the source's own fired / tag loss.

Chains: the balance_*.json files (Halo 2 ports, the SAW, the Focus Rifle: every leg's own values);
Halo 1 ports without one: their config's yardstick pick, source -> Halo 1, rates read from the kits
(HCEEK / H3EK / HREK / H4EK through port_field_audit.flatten). A pick that is not a gun (a grenade)
contributes no leg. Charge-paced weapons and heat-driven rates are listed, not corrected.
"""
import glob
import importlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(1, ROOT)
import port_env  # noqa: E402,F401
import ttk_common as tc  # noqa: E402
import port_field_audit as fa  # noqa: E402
import port_role_compare as rc  # noqa: E402
from reclaimer.hek.defs.weap import weap_def  # noqa: E402

OUT = os.path.join(HERE, 'reports', 'rof_balance_check')
KITS = {'Halo 2': 'H2EK', 'Halo 3': 'H3EK', 'Halo 3: ODST': 'H3ODSTEK', 'Halo Reach': 'HREK',
        'Halo 4': 'H4EK'}
H1_TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
THRESHOLD = 0.05
#: weapons whose charge is a separate CHARGED mode (its own card): the tap fire is rate-paced
TAP_CHARGE = {'Boltshot'}
#: rates FITTED IN GAME (a heat-driven ramp measured by probe / battery count): not ratio-derived
FITTED = {('Halo 1', 'Plasma Repeater'): 'heat-driven 20 -> 3.4 ramp fitted by h1_weapon_state_probe',
          ('Halo 2', 'Plasma Repeater'): 'heat-driven 20 -> 3.05 ramp fitted to the measured round 44'}


def cadence(rate, rec=0.0, spf=0):
    """(tag shots/s, fired shots/s) at a flat rate: rate 0 = the recovery placeholder (every
    tick, paced by the recovery); spf > 1 = bursts of spf at the rate, then the recovery."""
    rate, rec, spf = float(rate or 0.0), float(rec or 0.0), int(spf or 0)
    if rate <= 0 and rec <= 0:
        return None
    r = rate if rate > 0 else 30.0
    rt = int(round(30.0 / tc.tick_rate(r)))
    if spf == 0 and rate > 0:
        rec = 0.0                       # a held automatic: the recovery does not pace it
    rct = int(math.ceil(rec * 30.0 - 1e-6)) if rec > 0 else 0
    if spf > 1:
        cont = spf / ((spf - 1) / r + max(1.0 / r, rec))
        fired = spf * 30.0 / ((spf - 1) * rt + max(rt, rct))
    else:
        cont = 1.0 / max(1.0 / r, rec)
        fired = 30.0 / max(rt, rct)
    return cont, fired


def q_of(c):
    return c[1] / c[0] if c else 1.0


# ----------------------------------------------------------------------------- reading
_CARDS = json.load(open(os.path.join(ROOT, 'halo.json'), encoding='utf-8'))
SW = _CARDS['Player Modifiers']['Specific Weapon Modifier']
ALIAS = {'Energy Sword': 'Energy Blade', 'Flak Cannon (H1 fuel rod)': 'Flak Cannon', 'Pistol (bolt)': 'Pistol'}


def tag_for(name, game):
    name = ALIAS.get(name, name)
    for card in (SW.get(name) or {}).values():
        t = card.get('tag') if isinstance(card, dict) else None
        if isinstance(t, dict) and t.get(game):
            return t[game].split(' ', 1)[1].split(' & ')[0]
    return None


def read_rates(game, tag):
    """(rate max, fire recovery, shots per fire, charging time) of a weapon tag in a game."""
    if game == 'Halo 1':
        p = os.path.join(H1_TAGS, tag + '.weapon')
        if not os.path.exists(p):
            return None
        tr = weap_def.build(filepath=p).data.tagdata.weap_attrs.triggers.STEPTREE[0]
        return max(tr.firing.rounds_per_second), 0.0, 0, tr.charging.charging_time
    w = fa.flatten(KITS[game], tag + '.weapon')
    return (rc.num(w, 'rounds per second max', 'rounds per second'), rc.num(w, 'fire recovery time'),
            int(rc.num(w, 'shots per fire') or 0), rc.num(w, 'charging time'))


def q_weapon(game, tag, tap=False):
    """tap: the weapon's charge is a separate charged mode (its own card); the tap fire is rate-paced."""
    try:
        r = read_rates(game, tag) if tag else None
    except (Exception, SystemExit):          # not a weapon tag (a grenade's equipment) / not in the kit
        r = None
    if r is None:
        return None, 'no tag'
    rate, rec, spf, charge = r
    c = cadence(rate, rec, spf)
    if not c:
        return None, 'no rate'
    note = 'charge %.2f s' % charge if charge and charge > 0 else ''
    if note and not tap:
        return None, '%s: %s -- CHARGE-paced, not a rate leg' % (game, note)
    return c, '%s: rate %g, recovery %g, shots/fire %d%s -> fires %.3g/s (tag cadence %.3g)' % (
        game, rate, rec, spf, (', ' + note) if note else '', c[1], c[0])


# ----------------------------------------------------------------------------- the ports
def catalog():
    return json.load(open(os.path.join(ROOT, 'weapon_ports_catalog.json'), encoding='utf-8'))


def port_side(entry):
    """The Balanced rate fields of a catalog entry (weap rows) + its damage rows."""
    f, dmg, wtag = {}, [], None
    for r in entry.get('balance') or ():
        if r.get('class') == 'weap' and r.get('field') in ('Rounds Per Second', 'Rounds Per Second Max',
                                                           'Fire Recovery Time', 'Shots Per Fire'):
            f[r['field']] = r.get('value')
            wtag = wtag or r.get('tag')
        if r.get('class') == 'jpt!' and r.get('field', '').startswith('Damage') and \
                r.get('field') != 'Damage Lower Bound':
            dmg.append(r)
    return f, dmg, wtag


def chains():
    """(target game, port name, source game, source tag, legs [(yard, from, to)], source of chain)."""
    out = {}
    for p in sorted(glob.glob(os.path.join(HERE, 'balance_*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        if not isinstance(d, dict) or 'hops' not in d:
            continue
        if p.endswith('_mgvel.json'):
            continue                                    # a velocity variant of the same chain
        rows = {r.get('field'): r for r in d['rows'] if r.get('legs')}
        out[(d['target'], d['ported'])] = {'source': d['source'], 'file': os.path.basename(p),
                                            'rows': rows, 'legs': [tuple(h[1:4]) for h in d['hops']]}
    for p in sorted(glob.glob(os.path.join(HERE, 'ports_h1', '*.py'))):
        n = os.path.basename(p)[:-3]
        if n.startswith('_'):
            continue
        P = getattr(importlib.import_module('ports_h1.' + n), 'PORT', None) or {}
        key = ('Halo 1', P.get('name'))
        if not P or key in out:
            continue
        y = P.get('yardstick') or {}
        pick = str(y.get('pick') or '')
        pick = pick.split(' + ')[0].split(' (ratio')[0]
        pick = ALIAS.get(pick, pick)
        legs = [(pick, P.get('source'), 'Halo 1')] if pick else []
        out[key] = {'source': P.get('source'), 'file': 'ports_h1/%s.py' % n, 'rows': None, 'legs': legs,
                    'source tag': ((y.get('candidates') or {}).get('source_weapon'))}
    return out


def c_from_rows(rows, i_from, which):
    """(tag cadence, fired) of one side of a balance_*.json chain: which = 'ported_src' /
    legs[i] 'value_from' / 'value_to'."""
    def val(field):
        r = rows.get(field)
        if not r:
            return 0.0
        if which == 'ported_src':
            return r.get('ported_src') or 0.0
        return r['legs'][i_from].get(which) or 0.0
    return cadence(val('Rounds Per Second Max') or val('Rounds Per Second'),
                   val('Fire Recovery Time'), val('Shots Per Fire'))


def main():
    cat = catalog()
    ch = chains()
    rows_out = []
    for game, entries in cat.items():
        for e in entries if isinstance(entries, list) else ():
            f, dmg, wtag = port_side(e)
            rate = f.get('Rounds Per Second Max') or f.get('Rounds Per Second')
            if not rate and not f.get('Fire Recovery Time'):
                continue
            c = ch.get((game, e.get('weapon')))
            r = {'game': game, 'port': e.get('weapon'), 'source': e.get('source'),
                 'balanced': {k: v for k, v in f.items()}, 'damage rows': dmg, 'notes': []}
            cp = cadence(rate, f.get('Fire Recovery Time'), f.get('Shots Per Fire'))
            r['port fires'] = cp
            if c is None:
                r['notes'].append('no chain found (no balance file, no Halo 1 config pick)')
                rows_out.append(r)
                continue
            r['chain'] = c['file']
            if (game, e.get('weapon')) in FITTED:
                r['notes'].append('excluded: ' + FITTED[(game, e.get('weapon'))])
                rows_out.append(r)
                continue
            if c['rows']:
                rr = c['rows'].get('Rounds Per Second Max') or c['rows'].get('Rounds Per Second')
                rb = rr.get('balanced') if rr else None
                hand = rb is not None and rate and abs(float(rb) - float(rate)) > 0.01 * max(abs(float(rate)), 1e-6)
                rr2 = c['rows'].get('Fire Recovery Time')
                if rr2 and rr2.get('balanced') is not None and f.get('Fire Recovery Time') is not None and \
                        abs(float(rr2['balanced']) - float(f['Fire Recovery Time'])) > 0.005:
                    hand = True
                if hand:
                    r['notes'].append('rate SET BY HAND (catalog %s, ratio rule %s / recovery %s): tested as '
                                      'it fires, no correction' % (rate, rb, rr2.get('balanced') if rr2 else '-'))
                    rows_out.append(r)
                    continue
                cs = c_from_rows(c['rows'], 0, 'ported_src')
                legs = []
                for i, (yard, frm, to) in enumerate(c['legs']):
                    cf = c_from_rows(c['rows'], i, 'value_from')
                    ct = c_from_rows(c['rows'], i, 'value_to')
                    if cf and ct:
                        legs.append((yard, frm, to, cf[1], ct[1]))
            else:
                cs, why = q_weapon(c['source'], c.get('source tag'), tap=e.get('weapon') in TAP_CHARGE)
                r['notes'].append('source ' + why)
                legs = []
                for yard, frm, to in c['legs']:
                    cf, wf = q_weapon(frm, tag_for(yard, frm))
                    ct, wt = q_weapon(to, tag_for(yard, to))
                    if cf is None or ct is None:
                        r['notes'].append('yardstick %s: no rate in %s / %s (no leg)' % (yard, frm, to))
                        continue
                    r['notes'].append('yardstick %s -- %s; %s' % (yard, wf, wt))
                    legs.append((yard, frm, to, cf[1], ct[1]))
            if not cs or not cp:
                r['notes'].append('no source rate')
                rows_out.append(r)
                continue
            if legs:
                intended = cs[1]
                for _y, _f, _t, ff, ft in legs:
                    intended *= ft / ff
            else:                       # no gun leg: the port's tag cadence, at the source's loss
                intended = cp[0] * cs[1] / cs[0]
                r['notes'].append('no gun yardstick leg: intent = the port tag cadence x the source fired/tag')
            r['source fires'] = cs[1]
            r['legs'] = legs
            r['intended'] = intended
            r['k'] = intended / cp[1]
            rows_out.append(r)
    json.dump(rows_out, open(OUT + '.json', 'w', encoding='utf-8'), indent=1, default=str)

    L = ['# Balanced damage under the measured fire rule', '',
         'Generated by `sprint_toolkit/rof_balance_check.py` (read-only). intended = fired(source) x '
         'PRODUCT fired(yardstick, to) / fired(yardstick, from); k = intended / fired(port). Shots a '
         'second by the 30 Hz reset rule; fire recovery rounded up to ticks and pacing only one-shot-a-'
         'pull weapons (both ASSUMED). Damage that restores the ratio rule\'s damage per second = '
         'Balanced damage x k. |k - 1| > %d%% is flagged.' % (THRESHOLD * 100), '',
         '| game | port | Balanced rate (fires/s) | source fires | yardstick legs (fires from -> to) | intended | k | damage now -> x k |',
         '|---|---|---|---|---|---|---|---|']
    for r in rows_out:
        cp = r.get('port fires')
        rate_txt = ', '.join('%s %g' % (k.replace('Rounds Per Second', 'rps').replace('Fire Recovery Time', 'rec')
                                                .replace('Shots Per Fire', 'spf'), v)
                             for k, v in r['balanced'].items() if v) + (' (%.3g/s)' % cp[1] if cp else '')
        if 'k' not in r:
            L.append('| %s | %s | %s | | | | - | %s |' % (r['game'], r['port'], rate_txt, '; '.join(r['notes'])))
            continue
        legs = '; '.join('%s %.3g -> %.3g' % (y, ff, ft) for y, _f, _t, ff, ft in r['legs']) or '-'
        k = r['k']
        flag = abs(k - 1) > THRESHOLD
        dm = ', '.join('%s %g -> %.4g' % (d['field'].replace('Damage ', ''), d['value'], d['value'] * k)
                       for d in r['damage rows'] if isinstance(d.get('value'), (int, float))) or '(no damage row)'
        L.append('| %s | %s | %s | %.3g | %s | %.3g | %s%.3f%s | %s |' % (
            r['game'], r['port'], rate_txt, r['source fires'], legs, r['intended'],
            '**' if flag else '', k, '**' if flag else '', dm if flag else '-'))
    L += ['', '## Notes per port', '']
    for r in rows_out:
        if r['notes']:
            L.append('* %s %s: %s' % (r['game'], r['port'], ' | '.join(r['notes'])))
    open(OUT + '.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('wrote %s.md (%d ports)' % (OUT, len(rows_out)))


if __name__ == '__main__':
    main()
