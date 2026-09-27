"""card-stacking, second pass (user, 2026-09-27): field-level rework after the splits.

Runs AFTER split_cards.py. Every change is a handler keyed by card name; a handler gets
(path, card, parent) from the ORIGINAL document and returns the card(s) that replace it
([(name, card), ...]; [] removes it) or None to leave it. Rewritten textually through
json_spans, like the other tools, so halo.json's hand formatting survives.

  More Shooting (+ Charged / Scoped)  -> "Salvo Shooting": Rounds Per Second (+Max) *1.2,
      Shots Per Fire (+Max) +1. Rounds Per Shot moves to the weapon's Projectiles Per
      Shot card (created if missing), grouped with Projectiles Per Shot, step +1.
  Gravity Cannon / Beam / Rocket / Needler (boss weapons) -> "<X> Salvo" + "<X>
      Projectiles Per Shot", the same way.
  Step changes: Grenade Range (Grenade Ranges only) and Grenade Collateral *0.8 (*0.9 on
      ai\\generic), Homing Leading, Projectile Lead Time, Needle Timer, Supercombine Timer
      *1.2, Leap's Leap Proximity Fraction *0.8.
  Grenade Throw Delay + Encounter Grenade Timeout -> one "Grenade Throw Delay" card (the
      same setting, renamed after Halo 1).
  Charged Projectile Range / Velocity take the rows of the weapon's normal cards.
  Target Locator Arming Timer, Sentinel Beam Velocity -> ignore.
  Threshold Energy Burned / Energy Adjustment: all four Threshold Effects; threshold
      max 1; adjustment step *0.8.
  Danger Radius: ask_direction (the run picks the direction on first use).
  Orbit / Chase Speed: also switch on Auto Turret "Turret Follows Player".
  Watcher: new "Grenade Catch Cooldown" (Collect Cooldown, Attack Delay; step *0.8).

usage: rework_cards.py [--write]
"""
import copy
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import json_spans
from split_cards import dump_card, HALO_JSON

report = []


def each_list(card):
    tg = card.get('targets')
    return list(tg.values()) if isinstance(tg, dict) else [tg or []]


def map_rows(card, fn):
    """Apply fn(row) -> row / None (drop) to every row, per-game lists included."""
    c = copy.deepcopy(card)
    tg = c.get('targets')
    if isinstance(tg, dict):
        c['targets'] = {g: [r for r in (fn(t) for t in (lst or [])) if r is not None]
                        for g, lst in tg.items()}
    else:
        c['targets'] = [r for r in (fn(t) for t in (tg or [])) if r is not None]
    return c


def fname(t):
    f = t.get('field')
    return f if isinstance(f, str) else json.dumps(f)


def with_step(t, step):
    t = {k: v for k, v in t.items() if k != 'step'}
    return dict({'step': step}, **t)


def is_generic(path, card):
    return 'General' in str(path) or 'ai\\generic' in json.dumps(card.get('tag'))


RPS = ('Rounds Per Second', 'Rounds Per Second Max')
SPF = ('Shots Per Fire', 'Shots Per Fire Max')


def salvo_rows(t):
    if t.get('field') in RPS:
        return with_step(t, '*1.2')
    if t.get('field') in SPF:
        return with_step(t, '+1')
    if t.get('field') in ('Rounds Per Shot', 'Projectiles Per Shot'):
        return None
    return t


def pps_rows(t):
    if t.get('field') in ('Rounds Per Shot', 'Projectiles Per Shot'):
        t = with_step(t, '+1')
        t['group'] = 'Projectiles Per Shot'
        return t
    return None


def rows_of(card, fields):
    out = []
    for lst in each_list(card):
        out += [t for t in lst if t.get('field') in fields]
    return out


def h_more_shooting(path, card, parent):
    name = path[-1]
    suffix = name[len('More Shooting'):]                  # '', ' (Charged)', ' (Scoped)'
    salvo = map_rows(card, salvo_rows)
    salvo['desc'] = 'How fast it fires and how many rounds one pull sends.'
    salvo['split_from'] = name
    out = [('Salvo Shooting' + suffix, salvo)]
    moved = map_rows(card, pps_rows)
    has_rps = any(lst for lst in each_list(moved))
    if not has_rps:
        return out
    pps_name = 'Projectiles Per Shot' + suffix
    existing = parent.get(pps_name)
    if existing is None:
        # a new card: this card's Rounds Per Shot rows plus a Projectiles Per Shot row
        # beside each (same block / barrel), so the group moves both
        def add_pps(t):
            if t.get('field') != 'Rounds Per Shot':
                return None
            t = pps_rows(t)
            p = dict(t, field='Projectiles Per Shot')
            return [t, p]
        c = copy.deepcopy(card)
        tg = c.get('targets')
        if isinstance(tg, dict):
            c['targets'] = {g: [x for t in (lst or []) for x in (add_pps(t) or [])]
                            for g, lst in tg.items()}
        else:
            c['targets'] = [x for t in (tg or []) for x in (add_pps(t) or [])]
        for k in ('debug_desc', 'easier_when', 'harder_when'):
            c.pop(k, None)
        c['desc'] = 'Projectiles and ammo per shot.'
        c['split_from'] = name
        out.append((pps_name, c))
        report.append('%s: new card "%s"' % (' / '.join(path[1:-1]), pps_name))
    return out


GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']


def covered(keys):
    """{per-game key: [games it resolves for]}, the way resolve_gamed resolves: the
    game itself, else 'default', else the nearest earlier game's key."""
    out = {k: [] for k in keys}
    for i, g in enumerate(GAMES):
        if g in keys:
            out[g].append(g)
        elif 'default' in keys:
            out['default'].append(g)
        else:
            prev = next((x for x in reversed(GAMES[:i]) if x in keys), None)
            if prev:
                out[prev].append(g)
    return out


def rows_by_games(card, fields):
    """[(row, [games it applies to])] -- a per-game list's rows carry the games that
    list resolves for, so they can move into a card shaped differently."""
    tg = card.get('targets')
    cg = card.get('game')
    card_games = [cg] if isinstance(cg, str) else list(cg or GAMES)
    if 'Halo 3' in card_games and 'Halo 3: ODST' not in card_games:
        card_games.append('Halo 3: ODST')          # ODST inherits Halo 3's cards
    if not isinstance(tg, dict):
        return [(t, [g for g in (t.get('games') or GAMES) if g in card_games])
                for t in (tg or []) if t.get('field') in fields]
    cov = covered(list(tg))
    out = []
    for k, lst in tg.items():
        for t in lst or []:
            if t.get('field') in fields:
                gs = [g for g in cov.get(k, []) if g in card_games]
                if t.get('games'):
                    gs = [g for g in gs if g in t['games']]
                out.append((t, gs))
    return out


def h_projectiles_per_shot(path, card, parent):
    """Existing Projectiles Per Shot card: group it, step +1, and take the Rounds Per
    Shot rows from the sibling More Shooting card of the same suffix -- each only for
    the games its source list applied to."""
    suffix = path[-1][len('Projectiles Per Shot'):]
    src = parent.get('More Shooting' + suffix)
    c = map_rows(card, pps_rows)
    if src is None:
        return [(path[-1], c)]
    moving = [(pps_rows(copy.deepcopy(t)), gs) for t, gs in rows_by_games(src, ('Rounds Per Shot',))]
    moving = [(t, gs) for t, gs in moving if gs]
    if isinstance(c['targets'], dict):
        cov = covered(list(c['targets']))
        for k, lst in c['targets'].items():
            for t, gs in moving:
                mine = [g for g in gs if g in cov.get(k, [])]
                if mine:
                    lst.append(dict(t, games=mine))
    else:
        for t, gs in moving:
            c['targets'].append(dict(t, games=gs))
    return [(path[-1], c)]


def h_boss_weapon(path, card, parent):
    name = path[-1]
    salvo = map_rows(card, salvo_rows)
    salvo['desc'] = 'Fire rate and rounds per burst.'
    salvo['split_from'] = name
    pps = map_rows(card, pps_rows)
    pps['desc'] = 'Projectiles per shot.'
    pps['split_from'] = name
    return [(name + ' Salvo', salvo), (name + ' Projectiles Per Shot', pps)]


def stepper(fields, step, generic_step=None):
    def h(path, card, parent):
        s = generic_step if (generic_step and is_generic(path, card)) else step
        return [(path[-1], map_rows(card, lambda t: with_step(t, s)
                                   if (not fields or t.get('field') in fields) else t))]
    return h


def h_throw_delay(path, card, parent):
    other = parent.get('Encounter Grenade Timeout')
    if other is None or other.get('split_from') != card.get('split_from'):
        return None
    c = copy.deepcopy(card)
    rows = rows_of(card, ('Grenade Throw Delay',)) + rows_of(other, ('Encounter Grenade Timeout',))
    for t in rows:
        t['group'] = 'Grenade Throw Delay'
    if isinstance(card.get('targets'), dict) or isinstance(other.get('targets'), dict):
        report.append('%s: throw delay has per-game lists -- merged by hand needed'
                      % ' / '.join(path[1:-1]))
        return None
    c['targets'] = [t for t in rows]
    games = set(card.get('game') or []) | set(other.get('game') or [])
    if isinstance(card.get('game'), str) or isinstance(other.get('game'), str):
        games = {g for x in (card.get('game'), other.get('game'))
                 for g in ([x] if isinstance(x, str) else (x or []))}
    if card.get('game') or other.get('game'):
        c['game'] = sorted(games)
    tags = {}
    for x in (other, card):
        t = x.get('tag')
        tags.update(t if isinstance(t, dict) else ({'default': t} if t else {}))
    c['tag'] = tags
    c['desc'] = 'Grenade Throw Delay (Encounter Grenade Timeout in Halo 1)'
    report.append('%s: Encounter Grenade Timeout merged into Grenade Throw Delay'
                  % ' / '.join(path[1:-1]))
    return [(path[-1], c)]


def h_drop_encounter(path, card, parent):
    other = parent.get('Grenade Throw Delay')
    if other is None or other.get('split_from') != card.get('split_from'):
        return None
    if isinstance(card.get('targets'), dict) or isinstance(other.get('targets'), dict):
        return None
    return []


def h_charged(normal):
    def h(path, card, parent):
        src = parent.get(normal)
        if src is None:
            report.append('%s: no "%s" card to copy rows from' % (' / '.join(path[1:-1]), normal))
            return None
        c = copy.deepcopy(card)
        c['targets'] = copy.deepcopy(src['targets'])
        c = map_rows(c, lambda t: {k: v for k, v in t.items() if k != 'tag'})
        c['desc'] = src.get('desc', c.get('desc'))
        return [(path[-1], c)]
    return h


def h_ignore(path, card, parent):
    c = dict(card)
    c['ignore'] = True
    return [(path[-1], c)]


def h_threshold(path, card, parent):
    def f(t):
        t = dict(t, index='all')
        if t.get('field') == 'Threshold Energy Burned':
            t['max'] = 1
        if t.get('field') == 'Energy Adjustment':
            t = with_step(t, '*0.8')
        return t
    return [(path[-1], map_rows(card, f))]


def h_danger(path, card, parent):
    return [(path[-1], map_rows(card, lambda t: dict(t, ask_direction=True)
                                if t.get('field') == 'Danger Radius' else t))]


def h_follow(path, card, parent):
    c = copy.deepcopy(card)
    flag = {'field': 'Flags', 'block': 'Auto Turret', 'set': 'Turret Follows Player',
            'set_bit': 'Turret Follows Player'}
    if isinstance(c['targets'], dict):
        for lst in c['targets'].values():
            if not any(t.get('set_bit') for t in lst):
                lst.append(dict(flag))
    elif not any(t.get('set_bit') for t in c['targets']):
        c['targets'].append(flag)
    return [(path[-1], c)]


def h_catch(path, card, parent):
    """After the Watcher's Grenade Catch Chance card, add a Grenade Catch Cooldown."""
    if 'Grenade Catch Cooldown' in parent:
        return None
    block = next((t.get('block') for lst in each_list(card) for t in lst), None)
    cd = {k: v for k, v in card.items() if k not in ('targets', 'desc', 'harder_when')}
    cd['desc'] = 'Seconds between grenade catches, and before it throws one back.'
    cd['harder_when'] = 'decreased'
    cd['targets'] = [{'step': '*0.8', 'field': f, 'block': block, 'min': 0, 'group': g}
                     for f, g in (('Collect Cooldown', 'Collect Cooldown'),
                                  ('Collect Cooldown Max', 'Collect Cooldown'),
                                  ('Attack Delay', 'Attack Delay'),
                                  ('Attack Delay Max', 'Attack Delay'))]
    cd['split_from'] = 'Grenade Catch'
    report.append('Watcher: new card "Grenade Catch Cooldown"')
    return [(path[-1], card), ('Grenade Catch Cooldown', cd)]


HANDLERS = {
    'More Shooting': h_more_shooting,
    'More Shooting (Charged)': h_more_shooting,
    'More Shooting (Scoped)': h_more_shooting,
    'Projectiles Per Shot': h_projectiles_per_shot,
    'Projectiles Per Shot (Charged)': h_projectiles_per_shot,
    'Projectiles Per Shot (Scoped)': h_projectiles_per_shot,
    'Gravity Cannon': h_boss_weapon, 'Beam': h_boss_weapon,
    'Rocket': h_boss_weapon, 'Needler': h_boss_weapon,
    'Grenade Range': stepper(('Grenade Ranges',), '*0.8', '*0.9'),
    'Grenade Collateral': stepper(None, '*0.8', '*0.9'),
    'Homing Leading': stepper(None, '*1.2'),
    'Homing Leading (Charged)': stepper(None, '*1.2'),
    'Projectile Lead Time': stepper(None, '*1.2'),
    'Needle Timer': stepper(None, '*1.2'),
    'Supercombine Timer': stepper(None, '*1.2'),
    'Leap': stepper(('Leap Proximity Fraction',), '*0.8'),
    'Grenade Throw Delay': h_throw_delay,
    'Encounter Grenade Timeout': h_drop_encounter,
    'Charged Projectile Range': h_charged('Projectile Range'),
    'Charged Projectile Velocity': h_charged('Projectile Velocity'),
    'Sentinel Beam Velocity': h_ignore,
    'Threshold Energy Burned': h_threshold,
    'Energy Adjustment': h_threshold,
    'Danger Radius': h_danger,
    'Orbit': h_follow, 'Chase Speed': h_follow,
    'Grenade Catch Chance': h_catch,
}
# only on these sources (a card name alone would also catch other things)
ONLY = {
    'Arming Timer': ('Target Locator',),
    'Needler': ('Sentinel Enforcer',),
    'Beam': ('Sentinel Enforcer',),
    'Rocket': ('Sentinel Enforcer',),
    'Gravity Cannon': ('Prophet Regret',),
    'Orbit': ('Auto Turret',), 'Chase Speed': ('Auto Turret',),
    'Grenade Catch Chance': ('Watcher',),
}
HANDLERS['Arming Timer'] = h_ignore


def main():
    text = io.open(HALO_JSON, encoding='utf-8').read()
    doc = json.loads(text)

    def node(path):
        n = doc
        for k in path:
            n = n[k]
        return n

    edits = []
    for path, s, e in json_spans.card_spans(text):
        if not path or path[0] == 'Missions' or not isinstance(path[-1], str):
            continue
        h = HANDLERS.get(path[-1])
        if h is None:
            continue
        only = ONLY.get(path[-1])
        if only and path[-2] not in only:
            continue
        card = node(path)
        if 'targets' not in card or 'tag' not in card:
            continue
        res = h(path, card, node(path[:-1]))
        if res is None:
            continue
        edits.append((s, e, res, path))
        report.append('%s / %s -> %s' % (' / '.join(map(str, path[1:-1])), path[-1],
                                        [n for n, _ in res] or 'removed'))
    out = os.path.join(HERE, 'rework_cards_report.txt')
    io.open(out, 'w', encoding='utf-8').write('\n'.join(report) + '\n')
    print('%d cards changed; report -> %s' % (len(edits), out))
    if '--write' not in sys.argv:
        return
    for s, e, res, path in sorted(edits, key=lambda x: -x[0]):
        key_end = text.rfind(':', 0, s)
        key_start = text.rfind('"', 0, text.rfind('"', 0, key_end))
        line_start = text.rfind('\n', 0, key_start) + 1
        ind = text[line_start:key_start]
        if not res:
            # remove the key, its value and one separating comma
            after = text[e:].lstrip()
            if after.startswith(','):
                text = text[:line_start] + text[text.index(',', e) + 1:].lstrip('\r').lstrip('\n')
                continue
            prev = text.rfind(',', 0, line_start)
            text = text[:prev] + text[e:]
            continue
        body = (',\n').join((ind + json.dumps(n) + ': ' + dump_card(c, ind)) for n, c in res)
        text = text[:line_start] + body + text[e:]
    doc2 = json.loads(text)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(text)
    print('written')


if __name__ == '__main__':
    main()
