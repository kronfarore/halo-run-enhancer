"""card-stacking: split (or group) overloaded cards, per the user's pass over
overloaded_cards.txt (2026-09-27). One spec entry per card family; every card of that
name anywhere in halo.json is rewritten.

Spec forms (rows are matched by their `group` if they have one, else their field --
per-game field dicts match on any game's name):
  split:   [(new card name, [row names]), ...]   rows not named fall into NO card and
           abort the family (reported), so nothing is dropped silently
  group:   {group name: [row names]}           keep the card, give rows one input
  merge:   ('New Card', [other card names], {group: [rows]})   (Run/Sneak Speed)
Options on a split: 'exclusive' -> each new card gets "exclusive": <family>, so drawing
one blacklists its siblings for that source; 'carry' -> rows copied into EVERY new card
(Special-Case Firing's Mode set). {name} in a new card name is the original card name.
Cards the user still has to check are simply not listed. Re-running is safe: a family
already split no longer exists under its old name.

usage: split_cards.py [--write]
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import json_spans

HALO_JSON = os.path.join(os.path.dirname(HERE), 'halo.json')

MELEE = [('Melee Timing', ['Melee Attack Delay Timer', 'Melee Attack Timeout',
                           'Melee Attack Delay', 'Melee Charge Time']),
         ('Melee Chance', ['Melee Chance']),
         ('Melee Leap Range', ['Melee Leap Range'])]
PER_ROUND = [('Heat Per Round', ['Heat Generated Per Round']),
             ('Age Per Round', ['Age Generated Per Round'])]
HOMING = [('Homing Leading', ['Targeted Leading Fraction']),
          ('Homing Turn Rate', ['Guided Angular Velocity']),
          ('Homing Accuracy', ['Guided Projectile (Outer Range) Error Radius',
                               'Guided Projectile Outer Range Error Radius'])]
GRENADES = [('Grenade Velocity', ['Grenade Velocity', 'Grenade Ideal Velocity']),
            ('Grenade Range', ['Grenade Ranges', 'Grenade Ranges Max']),
            ('Grenade Collateral', ['Collateral Damage Radius'])]
RANGE_VEL = [('{name} Range', ['Range', 'Maximum Range']), ('{name} Velocity', ['Velocity'])]
RANGE_VEL_GRAV = RANGE_VEL + [('{name} Gravity', ['Gravity Scale'])]
CHASSIS = [('{name} Speed', ['Maximum Forward Speed', 'Maximum Reverse Speed']),
           ('{name} Acceleration', ['Speed Acceleration', 'Speed Deceleration']),
           ('{name} Turn', ['Maximum Left Turn', 'Maximum Right Turn (Negative)', 'Turn Rate'])]
UPGRADES = [('Few Upgrade Chance', ['Few Upgrade Chance']),
            ('Normal Upgrade Chance', ['Normal Upgrade Chance']),
            ('Many Upgrade Chance', ['Many Upgrade Chance'])]
ACCURACY = [('Accuracy Bounds', ['Accuracy Bounds']), ('Accuracy Time', ['Accuracy Time']),
            ('Projectile Error', ['Projectile Error'])]

SPEC = {
    # 3 / 46
    'Projectile': {'split': [('Projectile Range', ['Range']), ('Projectile Velocity', ['Velocity']),
                             ('Projectile Lead Time', ['Autoaim Leading Maximum Lead Time']),
                             ('Projectile Gravity', ['Gravity Scale'])]},
    'Charged Projectile': {'split': [('Charged Projectile Range', ['Maximum Range']),
                                     ('Charged Projectile Velocity', ['Velocity'])]},
    # 7
    'Accuracy Penalties': {'group': {'Accuracy Penalties': ['Reload Penalty', 'Switch Penalty']}},
    # 10 / 71
    'Melee Behavior': {'split': MELEE},
    'AI Base Melee Behavior': {'split': [('AI Base ' + n, r) for n, r in MELEE]},
    # 11 / 47
    'Per Round': {'split': PER_ROUND},
    'Per Round (Charged)': {'split': [(n + ' (Charged)', r) for n, r in PER_ROUND]
                            + [('Charged Drain Rate', ['Charged Drain Rate'])]},
    # 12
    'Heat Recovery': {'split': [('Heat Threshold', ['Heat Recovery Threshold']),
                                ('Heat Loss', ['Heat Loss', 'Heat Loss Per Second'])]},
    # 13 / 14
    'Search Tactics': {'exclusive': True, 'split': [
        ('Search: Suppressing Fire', ['Suppressing Fire Weight']),
        ('Search: Uncover', ['Uncover Weight']),
        ('Search: Leap On Cover', ['Leap On Cover Weight']),
        ('Search: Destroy Cover', ['Destroy Cover Weight']),
        ('Search: Guard', ['Guard Weight']),
        ('Search: Investigate', ['Investigate Weight'])]},
    # 17
    'Vision': {'split': [('Vision', ['Vision']), ('Peripheral Vision', ['Peripheral Vision'])]},
    # 19
    'Cover Properties': {'split': [('Hide Behind Cover', ['Hide Behind Cover Time']),
                                   ('Cover Threshold', ['Cover Vitality Threshold', 'Shield Fractions'])]},
    # 21 / 74
    'Grenades': {'split': GRENADES},
    'Grenade Properties': {'split': GRENADES},
    # 22 / 45
    'Homing': {'split': HOMING},
    'Homing (Charged)': {'split': [(n + ' (Charged)', r) for n, r in HOMING]},
    # 24 / 105
    'Target Tracking & Leading': {'split': [('Target Tracking', ['Target Tracking']),
                                            ('Target Leading', ['Target Leading'])]},
    'Hologram Target Tracking & Leading': {'split': [('Hologram Target Tracking', ['Target Tracking']),
                                                     ('Hologram Target Leading', ['Target Leading'])]},
    # 26 / 70
    'Accuracy': {'split': ACCURACY},
    'AI Base Accuracy': {'split': [('AI Base ' + n, r) for n, r in ACCURACY]},
    # 27
    'Firing Positions': {'split': [('Guard Position Time', ['Guard Position Time']),
                                   ('Combat Position Time', ['Combat Position Time']),
                                   ('Position Avoid Distance', ['Old Position Avoid Distance'])]},
    # 30
    'Body Recharge': {'split': [('Body Recharge Amount', ['Body Recharge Fraction']),
                                ('Body Recharge Delay', ['Body Recharge Delay Time']),
                                ('Body Recharge Time', ['Body Recharge Time'])]},
    # 32
    'Armor Lock': {'split': [('Armor Lock Chance', ['Armor Lock Chance', 'Grenade Stuck Armor Lock Chance']),
                             ('Armor Lock Duration', ['Armor Lock Safety Duration', 'Armor Lock Maximum Duration',
                                                      'Armor Lock Cooldown'])]},
    # 33
    'Grenades Chance': {'split': [('Grenade Chance', ['Grenade Chance']),
                                  ('Anti-Vehicle Grenade Chance', ['Anti-Vehicle Grenade Chance']),
                                  ('Grenade Check Time', ['Grenade Check Time']),
                                  ('Encounter Grenade Timeout', ['Encounter Grenade Timeout']),
                                  ('Grenade Throw Delay', ['Grenade Throw Delay'])]},
    # 35
    'Needle Timer': {'split': [('Needle Timer', ['Timer', 'Timer Max']),
                               ('Supercombine Timer', ['Super Detonation Time']),
                               ('Supercombine Needle Count', ['Super Detonation Projectile Count']),
                               ('Needle Fuse', ['Fuse'])]},
    # 36
    'Pellet Spread': {'split': [('Pellet Count', ['Yaw Count', 'Pitch Count']),
                                ('Pellet Spread', ['Spread', 'Distribution Exponent'])]},
    # 38 / 64
    'Equipment Explosion': {'split': [('Explosion Radius', ['Radius']), ('Explosion Damage', ['Damage'])]},
    'Powerdrain': {'split': [('Powerdrain Radius', ['Radius']), ('Powerdrain Damage', ['Damage'])]},
    # 39 / 73
    'Upgrade Chance': {'split': UPGRADES},
    'Placement Properties': {'split': UPGRADES},
    # 40
    'Hunter Berserk': {'split': [('Berserk Damage', ['Berserk Damage Amount', 'Berserk Damage Threshold']),
                                 ('Berserk Grenade', ['Berserk Grenade Chance'])]},
    # 41
    'Berserk': {'split': [('Berserk Cooldown', ['Beserk Cooldown']),
                          ('Berserk Perimeter Range', ['Perimeter Range', 'Perimeter Range Close']),
                          ('Berserk Count', ['Maximum Berserk Count', 'Minimum Berserk Count']),
                          ('Berserk Special Chances', ['Shield-Down Berserk Chance', 'Shield-Down Berserk Range',
                                                      'Play Berserk Animation Chance When Stuck'])]},
    # 42
    'Special-Case Firing': {'carry': ['Special-Fire Mode'], 'split': [
        ('Special Damage', ['Special Damage Modifier']),
        ('Special-Fire Chance', ['Special-Fire Chance']),
        ('Special-Fire Delay', ['Special-Fire Delay'])]},
    # 44
    'Run Speed': {'merge': ('Speed and Acceleration', ['Sneak Speed'],
                            {'Speed': ['Run Speed', 'Sneak Speed'],
                             'Acceleration': ['Run Acceleration', 'Sneak Acceleration']})},
    # 51
    'Airstrike': {'split': [('Airstrike Charges', ['Charges']),
                            ('Airstrike Shots', ['Shots Per Strike']),
                            ('Airstrike Cooldown', ['Cooldown']),
                            ('Airstrike Timing', ['Warmup', 'Duration', 'Marker Time']),
                            ('Airstrike Radius', ['Launch Radius']),
                            ('Airstrike Pattern', ['Strike Pattern x', 'Strike Pattern y'])]},
    # 54 / 55 / 57
    'Charged Shot Range': {'split': [('Charged Shot Range', ['Range']), ('Charged Shot Velocity', ['Velocity'])]},
    'Sprint Wind-Up': {'split': [('Sprint Wind-Up', ['Seconds to Full Speed']), ('Sprint Decay', ['Decay Rate'])]},
    'Camo Break': {'split': [('Camo Break Speed', ['Movement Speed Domain']),
                             ('Camo Break Awareness', ['Awareness Time'])]},
    # 72
    'Grenade Scales': {'split': [('Grenade Chance Scale', ['Grenade Chance Scale']),
                                 ('Grenade Timer Scale', ['Grenade Timer Scale'])]},
    # 76 / 101
    'Projectile Range Hunter Fuel Rod': {'split': [('Fuel Rod Range', ['Range']), ('Fuel Rod Velocity', ['Velocity']),
                                                   ('Fuel Rod Gravity', ['Gravity Scale'])]},
    'Projectile Range': {'split': RANGE_VEL_GRAV},
    # 77
    'Kamikaze': {'exclusive': True, 'split': [('Kamikaze Chance', ['Broken Kamikaze Chance']),
                                              ('Kamikaze Count', ['Maximum Kamikaze Count'])]},
    # 78 / 79 / 80
    'Panic': {'split': [('Panic Chance', ['Friend Killed Panic Chance', 'Leader Killed Panic Chance']),
                        ('Flee Time', ['Flee Time'])]},
    'Movement Switching': {'split': [('Crouch Chance', ['Initial Crouch Chance', 'Crouch Time']),
                                     ('Run Time', ['Run Time'])]},
    'Combatform Berserk': {'split': [('Berserk Chance', ['Berserk Chance']),
                                     ('Berserk Distance', ['Berserk Distance']),
                                     ('Berserk Count', ['Maximum Berserk Count', 'Minimum Berserk Count'])]},
    # 81
    'Infestation Speed': {'group': {'Infection Time': ['Infection Time', 'Infection Time Max']}},
    # 82
    'Stealth Morphs': {'split': [('Morph Distance', ['Stealth Morph Distance Threshold']),
                                 ('Morph Damage', ['Stealth Morph Damage Threshold'])]},
    # 83 (the card is named "Tank Form")
    'Tank Form': {'split': [('Distance Damage Radius', ['Distance Damage Outer Radius', 'Distance Damage Inner Radius']),
                            ('Distance Damage Time', ['Distance Damage Time', 'Distance Damage Reset Time']),
                            ('Throttle Distance', ['Throttle Distance', 'Throttle Distance Max']),
                            ('Protect Damage Amount', ['Protect Damage Amount']),
                            ('Protect Time', ['Protect Time']),
                            ('Spew Chance', ['Spew Chance']),
                            ('Spew Frequency', ['Spew Frequency', 'Spew Frequency Max'])]},
    # 84
    'Stalker Form': {'split': [('Morph Distance', ['Stealth Morph Distance Threshold']),
                               ('Morph Damage', ['Stealth Morph Damage Threshold']),
                               ('Stalk Range', ['Stalk Range', 'Stalk Range Max', 'Stalk Range Hard Maximum']),
                               ('Stalk Charge', ['Stalk Charge Chance'])]},
    # 85 -- Turtle Abort Distance rides with Turtle Distance until the user has checked it
    'Ranged Form': {'split': [('Ranged Distance', ['Ranged Proximity Distance']),
                              ('Turtle Threshold', ['Turtle Damage Threshold']),
                              ('Turtle Time', ['Turtle Time', 'Turtle Time Max']),
                              ('Turtle Distance', ['Turtle Distance', 'Turtle Abort Distance'])]},
    # 87 / 88 / 89 / 90
    'Shield down Berserk': {'split': [('Shield-Down Berserk Chance', ['Shield-Down Berserk Chance',
                                                                      'Shield-Down Berserk Chance Max']),
                                      ('Shield-Down Berserk Range', ['Shield-Down Berserk Ranges',
                                                                     'Shield-Down Berserk Ranges Max'])]},
    'More Berserking': {'split': [('Berserk Cooldown', ['Beserk Cooldown']), ('Berserk Count', ['Berserk Count'])]},
    'Leader Charge': {'split': [('Leader Charge Chance', ['Leader Abandoned Berserk Chance']),
                                ('Leader Charge Range', ['Perimeter Range'])]},
    'Deployable Shield Use': {'split': [('Shield Use Vitality', ['Vitality Fraction Shield Equipment',
                                                                'Vitality Fraction Bubbleshield']),
                                        ('Shield Use Recent Damage', ['Recent Damage Shield Equipment'])]},
    # 92 / 93 / 94
    'Hologram': {'split': [('Hologram Wait Time', ['Hologram Cover Wait Time', 'Hologram Cover Wait Time Max']),
                           ('Hologram Cooldown', ['Hologram Cooldown Delay'])]},
    'Death': {'split': [('Death Height', ['Death Height', 'Death Rise Time']),
                        ('Death Detonation Time', ['Death Detonation Time']),
                        ('Detonation Body Vitality', ['Detonation Body Vitality'])]},
    'Shield Boost': {'split': [('Shield Boost Radius', ['Shield Boost Radius Maximum']),
                               ('Shield Boost Period', ['Shield Boost Period']),
                               ('Shield Boost Strength', ['Shield Boost Strength'])]},
    # 95 / 96 / 100 / 106
    'Head Gun Rate of Fire': {'group': {'Rate of Fire': ['Rounds Per Second', 'Rounds Per Second Max']}},
    'Head Gun Accuracy': {'group': {'Error Angle': ['Error Angle', 'Error Angle Max', 'Minimum Error']}},
    'Turret Rate of Fire': {'group': {'Rate of Fire': ['Rounds Per Second', 'Rounds Per Second Max']}},
    'Beam Rate of Fire': {'group': {'Rate of Fire': ['Rounds Per Second', 'Rounds Per Second Max']}},
    # 97
    'Fight Circle': {'split': [('Fight Circle Strafe Time', ['Strafe Time']),
                               ('Fight Circle Firing Time', ['Extra Firing Time']),
                               ('Fight Circle Angles', ['Maximum Angle From Threat Axis', 'Nearby Inner Angle',
                                                        'Nearby Outer Angle'])]},
    # 99
    'Grenade Catch': {'split': [('Grenade Catch Chance', ['Chance To Collect']),
                                ('Grenade Catch Range', ['Maximum Collect Range']),
                                ('Grenade Catch Attack Speed', ['Attack Speed']),
                                ('Grenade Catch Strength', ['Strength'])]},
    # 103 / 107 / 109 / 111
    'Gravity Cannon Projectile': {'split': RANGE_VEL},
    'Beam Range': {'split': [('Beam Range', ['Range']), ('Beam Velocity', ['Velocity'])]},
    'Beam Projectile': {'split': RANGE_VEL},
    'Rocket Projectile': {'split': RANGE_VEL},
    # 112
    'Rocket Damage': {'split': [('Rocket Damage', ['Damage']), ('Rocket Radius', ['Radius'])]},
    # 104 / 113
    'Gravity Throne': {'split': CHASSIS},
    'Enforcer Chassis': {'split': CHASSIS},
    # 114
    'Gravity Jump': {'split': [('Gravity Jump Cooldown', ['Cooldown']),
                               ('Gravity Jump Trigger Distance', ['Trigger Distance']),
                               ('Gravity Jump Height', ['Jump Target Height']),
                               ('Gravity Jump Float Time', ['Float Time']),
                               ('Gravity Jump Descend Gravity', ['Descend Gravity']),
                               ('Gravity Jump Target Attractor', ['Target Attractor']),
                               ('Gravity Jump Retreat Radius', ['Retreat Radius'])]},
}


def row_names(t):
    names = set()
    for v in (t.get('group'), t.get('field'), t.get('label')):
        if isinstance(v, str):
            names.add(v)
        elif isinstance(v, dict):
            names |= {x for x in v.values() if isinstance(x, str)}
    return names


def desc_for(rows):
    out = []
    for t in rows:
        f = t.get('field')
        f = f if isinstance(f, str) else next((x for x in (f or {}).values() if isinstance(x, str)), '?')
        if f not in out:
            out.append(f)
    return ', '.join(out)


def dump_card(card, ind):
    lines = ['{']
    keys = list(card)
    for i, k in enumerate(keys):
        comma = ',' if i < len(keys) - 1 else ''
        if k == 'targets':
            lines.append('%s\t"targets": [' % ind)
            for j, t in enumerate(card[k]):
                tc = ',' if j < len(card[k]) - 1 else ''
                lines.append('%s\t\t%s%s' % (ind, json.dumps(t, ensure_ascii=False)
                                             .replace('{"', '{ "').replace('}', ' }'), tc))
            lines.append('%s\t]%s' % (ind, comma))
        else:
            lines.append('%s\t%s: %s%s' % (ind, json.dumps(k), json.dumps(card[k], ensure_ascii=False), comma))
    lines.append(ind + '}')
    return '\n'.join(lines)


def rewrite(card, name, spec, siblings, nested=False):
    """[(card name, card dict)] replacing `card`, or a reason string."""
    tg = card.get('targets') or []
    if isinstance(tg, dict):
        # per-game target lists: split each game's list the same way, then regroup
        per = {}
        for g, lst in tg.items():
            if not isinstance(lst, list):
                return 'per-game target entry %r is not a list' % g
            r = rewrite(dict(card, targets=lst), name, spec, siblings, nested=True)
            if isinstance(r, str) and not r.startswith('nothing to split'):
                return '%s: %s' % (g, r)
            per[g] = r if not isinstance(r, str) else [(None, dict(card, targets=lst))]
        names = []
        for g, parts in per.items():
            for n, _c in parts:
                if n is not None and n not in names:
                    names.append(n)
        if 'group' in spec:
            return [(name, dict(card, targets={g: parts[0][1]['targets'] for g, parts in per.items()}))]
        if len(names) < 2:
            return 'nothing to split (%d part)' % len(names)
        out = []
        for n in names:
            lists = {}
            for g, parts in per.items():
                hit = [c for pn, c in parts if pn == n]
                if hit:
                    lists[g] = hit[0]['targets']
            c = dict(next(c for g, parts in per.items() for pn, c in parts if pn == n))
            c['targets'] = lists
            c['split_from'] = name
            out.append((n, c))
        return out
    if not all(isinstance(t, dict) for t in tg):
        return 'a target that is not an object -- split by hand'
    if 'group' in spec:
        out = []
        for t in tg:
            t = dict(t)
            for gname, rows in spec['group'].items():
                if row_names(t) & set(rows):
                    t['group'] = gname
            out.append(t)
        return [(name, dict(card, targets=out))]
    carry = [t for t in tg if row_names(t) & set(spec.get('carry') or ())]
    rest = [t for t in tg if t not in carry]
    parts, used = [], set()
    for new, rows in spec['split']:
        new = new.replace('{name}', name)
        mine = [t for t in rest if row_names(t) & set(rows)]
        for t in mine:
            used.add(id(t))
        if mine:
            parts.append((new, mine))
    left = [t for t in rest if id(t) not in used and 'field' in t]
    if left:
        return 'rows not placed: %s' % sorted({x for t in left for x in row_names(t)})
    if len(parts) < 2:
        return 'nothing to split (%d part)' % len(parts)
    out = []
    for new, rows in parts:
        if new != name and new in siblings and not nested:
            new = '%s (%s)' % (new, name)
        c = {}
        for k, v in card.items():
            if k == 'targets':
                continue
            c[k] = v
        c['desc'] = desc_for(rows)
        # the family it came from: a run drafted before the split still names the
        # family, and HaloGUI._rebuild_split_card rebuilds it from these cards
        c['split_from'] = name
        if spec.get('exclusive'):
            c['exclusive'] = name
        c['targets'] = [dict(t) for t in rows] + [dict(t) for t in carry]
        out.append((new, c))
    return out


def main():
    text = io.open(HALO_JSON, encoding='utf-8').read()
    doc = json.loads(text)
    spans = json_spans.card_spans(text)
    report = collections.defaultdict(list)
    edits = []
    produced = {}                      # parent path -> {new card name: card}

    def parent_of(path):
        n = doc
        for k in path[:-1]:
            n = n[k]
        return n

    for path, s, e in spans:
        if not path or path[0] == 'Missions':
            continue
        name = path[-1]
        spec = SPEC.get(name)
        if spec is None or not isinstance(name, str):
            continue
        card = json.loads(text[s:e])
        if 'targets' not in card or 'tag' not in card:
            continue
        parent = parent_of(path)
        where = ' / '.join(str(p) for p in path[1:-1])
        if 'merge' in spec:
            new, others, groups = spec['merge']
            other = [o for o in others if o in parent]
            rows = list(card['targets'])
            for o in other:
                rows += parent[o]['targets']
            out = []
            for t in rows:
                t = dict(t)
                for gname, members in groups.items():
                    if row_names(t) & set(members):
                        t['group'] = gname
                out.append(t)
            c = dict(card, targets=out, desc='Run and sneak speed, and their acceleration')
            edits.append((s, e, [(new, c)], 'merge', other, path))
            report[name].append('%s: merged with %s into "%s"' % (where, other, new))
            continue
        res = rewrite(card, name, spec, set(parent))
        if isinstance(res, str):
            report[name].append('%s: SKIPPED -- %s' % (where, res))
            continue
        made = produced.setdefault(tuple(path[:-1]), {})
        kept = []
        for new, c in res:
            prev = made.get(new)
            if prev is not None:
                same = ({k: v for k, v in prev.items() if k not in ('split_from', 'desc')}
                        == {k: v for k, v in c.items() if k not in ('split_from', 'desc')})
                if same:
                    report[name].append('%s: "%s" already made by %s -- identical, dropped'
                                        % (where, new, prev['split_from']))
                    continue
                new = '%s (%s)' % (new, name)
            made[new] = c
            kept.append((new, c))
        res = kept
        edits.append((s, e, res, 'split', [], path))
        report[name].append('%s: -> %s' % (where, ', '.join('"%s"' % n for n, _ in res)))

    # removals of merged-away siblings: find their spans
    removals = []
    for s, e, res, kind, others, path in edits:
        for o in others:
            for p2, s2, e2 in spans:
                if p2 == tuple(path[:-1]) + (o,):
                    removals.append((s2, e2))
    lines = []
    for k in sorted(report):
        lines.append(k)
        lines += ['    ' + x for x in report[k]]
    out = os.path.join(HERE, 'split_cards_report.txt')
    io.open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('%d cards rewritten, %d families; report -> %s' % (len(edits), len(report), out))
    if '--write' not in sys.argv:
        return
    ops = [(s, e, 'rw', res, path) for s, e, res, kind, others, path in edits] + \
          [(s, e, 'rm', None, None) for s, e in removals]
    for s, e, kind, res, path in sorted(ops, key=lambda x: -x[0]):
        if kind == 'rm':
            # the key, its value and one separating comma
            ks = text.rfind('\n', 0, s)
            ke = e
            nxt = text[ke:].lstrip()
            if nxt.startswith(','):
                ke = text.index(',', ke) + 1
            else:
                ks = text.rfind(',', 0, ks)
            text = text[:ks] + text[ke:]
            continue
        line_start = text.rfind('\n', 0, s) + 1
        ind = text[line_start:s].split('"')[0]
        pieces = []
        for i, (new, c) in enumerate(res):
            body = dump_card(c, ind)
            pieces.append(body if i == 0 else ind + json.dumps(new) + ': ' + body)
        # the first piece replaces the value; its key must be renamed too
        key_start = text.rfind('"', 0, text.rfind(':', 0, s))
        key_start = text.rfind('"', 0, key_start)
        key_end = text.index(':', key_start)
        text = (text[:key_start] + json.dumps(res[0][0]) + text[key_end:s]
                + (',\n').join(pieces) + text[e:])
    json.loads(text)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(text)
    print('written')


if __name__ == '__main__':
    main()
