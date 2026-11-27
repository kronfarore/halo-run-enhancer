"""Equipment upgrade lines: the scripted checks of EQUIPMENT_LINES_PLAN.md section 10.

    python sprint_toolkit/equipment_lines_check.py

Phase 1 (data + lookups). In memory, halo.json only: no map is read, nothing is
written. Exits 1 on the first failed assertion group, printing what failed.
"""
import contextlib
import io
import os
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
import halo_enhancer as he  # noqa: E402

FAILS = []


def check(cond, what):
    print(('  ok   ' if cond else '  FAIL ') + what)
    if not cond:
        FAILS.append(what)


def names(mods):
    return sorted(m.get('name') for m in mods)


def keys(mods):
    return {he.line_card_key(m) for m in mods}


def main():
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    saved = dict(he.CONFIG)
    # A fixed option set, so the answers do not depend on this machine's settings.
    he.CONFIG.update({'equipment_lines_enabled': True, 'equipment_lines': None,
                      'remove_superflare_jammer': False,
                      'remove_invincibility_invisibility': False,
                      'sprint_feature': True, 'h4_sprint_mode': 'restore'})
    G = he.LINE_GAMES
    check(tuple(db.get_games()) == G, 'LINE_GAMES is halo.json\'s game order %s' % (G,))

    print('\n1. every default item exists in its game')
    for line in list(he.BUILTIN_LINES) + list(he.DEFAULT_EQUIPMENT_LINES):
        for g in G:
            items = set(he.line_game_items(db, g))
            for it in he._line_cell(line, g):
                check(it in items, '%s / %s: %s' % (line['name'], g, it))

    print('\n2. the defaults validate clean; no item is in two lines')
    clean, warn = he.validate_lines(db, he.default_equipment_lines())
    check(not warn, 'no warnings %s' % warn)
    check(clean == he.default_equipment_lines(), 'validated defaults == defaults')
    seen = {}
    for line in he.active_lines(db):
        for g in G:
            for it in he._line_cell(line, g):
                if seen.setdefault(it, line['name']) != line['name']:
                    check(False, '%s is in %s and %s' % (it, seen[it], line['name']))
    check(len(he.active_lines(db)) == 9, '9 lines active (2 built in + 7 table)')
    he.CONFIG['equipment_lines_enabled'] = False
    check([l['name'] for l in he.active_lines(db)] == ['Sprint', 'Camo'],
          'table off: only Sprint and Camo')
    he.CONFIG['equipment_lines_enabled'] = True

    print('\n3. the table, per game (stage | cards that apply)')
    table = {}
    for line in he.active_lines(db):
        row = table[line['name']] = {}
        for g in G:
            st = he.line_stage(db, line, g)
            cards = he.line_cards(db, line, g)
            row[g] = (st, cards)
            print('  %-12s %-13s %-34s %s' % (line['name'], g, ' + '.join(st) or '-',
                                                ', '.join(names(cards))))

    def stage(line, g):
        return table[line][g][0]

    def cards(line, g):
        return table[line][g][1]

    check(stage('Sprint', 'Halo 1') == [he.SPRINT_ITEM] and stage('Sprint', 'Halo 3') == []
          and stage('Sprint', 'Halo 3: ODST') == [] and stage('Sprint', 'Halo Reach') == ['Sprint'],
          'Sprint: ability in H1/H2, gap in H3/ODST, Sprint from Reach')
    check(stage('Camo', 'Halo 3: ODST') == ['Invisibility'], 'ODST follows Halo 3 (Camo)')
    check(stage('Decoy', 'Halo 3') == ['Jammer', 'Superflare'], 'Decoy H3 holds two items')
    check(names(cards('Sprint', 'Halo 1')) == names(cards('Sprint', 'Halo 2'))
          == ['Sprint', 'Sprint Cooldown', 'Sprint Duration', 'Sprint Speed'],
          'Sprint H1 == H2: the four ability cards (Phase 0 #5)')
    for ln, it in (('Camo', 'camo'), ('Overshield', 'overshield'), ('Regeneration', 'regeneration')):
        check(cards(ln, 'Halo 1') and keys(cards(ln, 'Halo 1')) == keys(cards(ln, 'Halo 2')),
              '%s: Halo 1 cards == Halo 2 cards, none stranded' % ln)
    for ln in ('Camo', 'Overshield', 'Regeneration', 'Shield', 'Cover', 'Mobility', 'Decoy',
               'Turret'):
        check(keys(cards(ln, 'Halo 3')) == keys(cards(ln, 'Halo 3: ODST')),
              '%s: Halo 3 cards == ODST cards (inherited)' % ln)
    for ln in ('Camo', 'Mobility', 'Decoy'):
        a, b = keys(cards(ln, 'Halo Reach')), keys(cards(ln, 'Halo 4'))
        check(a and a <= b, '%s: every Reach card continues in Halo 4 (nothing stranded)%s'
              % (ln, '' if a <= b else ' -- Reach only: %s' % sorted(a - b)))
    a, b = keys(cards('Sprint', 'Halo Reach')), keys(cards('Sprint', 'Halo 4'))
    print('  info Sprint Reach -> Halo 4 (restore): stranded %s' % sorted(x[2] for x in a - b))
    check(all(any(m.get('name') == 'Map Presence' for m in cards(ln, g))
              for ln in ('Camo', 'Mobility', 'Decoy', 'Shield', 'Cover', 'Turret')
              for g in ('Halo 3', 'Halo Reach', 'Halo 4') if stage(ln, g)),
          'every equipment stage has a Map Presence card')
    check(keys(cards('Camo', 'Halo 2')).isdisjoint(keys(cards('Camo', 'Halo 3'))),
          'Camo H2 -> H3: the ability cards are all stranded')

    print('\n4. Options switches make a cell a gap')
    he.CONFIG['remove_superflare_jammer'] = True
    dec = next(l for l in he.active_lines(db) if l['name'] == 'Decoy')
    check(he.line_stage(db, dec, 'Halo 3') == [] and he.line_cards(db, dec, 'Halo 3') == [],
          'remove_superflare_jammer: Decoy H3/ODST is a gap')
    he.CONFIG['remove_superflare_jammer'] = False
    he.CONFIG['remove_invincibility_invisibility'] = True
    camo = he.BUILTIN_LINES[1]
    check(he.line_stage(db, camo, 'Halo 3') == [], 'remove_invincibility_invisibility: Camo H3 gap')
    he.CONFIG['remove_invincibility_invisibility'] = False
    sprint = he.BUILTIN_LINES[0]
    for mode, want in (('off', []), ('holder', ['Sprint']), ('all', ['Sprint']),
                       ('restore', ['Sprint'])):
        he.CONFIG['h4_sprint_mode'] = mode
        check(he.line_stage(db, sprint, 'Halo 4') == want
              and he.line_stage(db, sprint, 'Halo Reach') == ['Sprint'],
              'h4_sprint_mode %s: Sprint H4 stage %s, Reach unaffected' % (mode, want))
    he.CONFIG['h4_sprint_mode'] = 'restore'
    he.CONFIG['sprint_feature'] = False
    check(he.line_stage(db, sprint, 'Halo 1') == [], 'abilities off: Sprint H1 is a gap')
    he.CONFIG['sprint_feature'] = True

    print('\n5. line_of')
    for item, want, games in ((he.CAMO_ITEM, 'Camo', ['Halo 1', 'Halo 2']),
                              ('Invisibility', 'Camo', ['Halo 3', 'Halo 3: ODST']),
                              ('Jet Pack', 'Mobility', ['Halo Reach', 'Halo 4']),
                              ('Superflare', 'Decoy', ['Halo 3', 'Halo 3: ODST']),
                              ('Hardlight Shield', 'Cover', ['Halo 4']),
                              ('Power Drain', None, []), ('Plasma Pistol', None, [])):
        line, gs = he.line_of(db, item)
        check(((line or {}).get('name'), gs) == (want, games),
              '%s -> %s %s' % (item, want, games))
    he.CONFIG['equipment_lines_enabled'] = False
    check(he.line_of(db, 'Jet Pack') == (None, []) and he.line_of(db, 'Invisibility')[0],
          'table off: Jet Pack in no line, Invisibility still Camo')
    he.CONFIG['equipment_lines_enabled'] = True

    print('\n6. validation')
    bad = [{'name': 'Mobility', 'stages': {'Halo 3': ['Grav Lift', 'Plasma Pistol'],
                                           'Halo Reach': ['Jet Pack'], 'Halo 9': ['x']}},
           {'name': 'mobility', 'stages': {'Halo 4': ['Jet Pack', 'Thruster Pack']}},
           {'name': 'Camo', 'stages': {'Halo 4': ['Promethean Vision']}},
           {'name': 'Empty', 'stages': {'Halo 3': ['Invisibility']}},
           {'name': 'Spaced', 'stages': {'Halo 3': ['power drain'], 'Halo 3: ODST': []}},
           'not a row']
    clean, warn = he.validate_lines(db, bad)
    for w in warn:
        print('       warning: %s' % w)
    got = {l['name']: l['stages'] for l in clean}
    check(got.get('Mobility') == {'Halo 3': ['Grav Lift'], 'Halo Reach': ['Jet Pack']},
          'unknown item and unknown game dropped')
    check(got.get('mobility (2)') == {'Halo 4': ['Thruster Pack']},
          'name taken (any case) -> renamed; Jet Pack (earlier line) dropped')
    check(got.get('Camo (2)') == {'Halo 4': ['Promethean Vision']}, 'built-in name taken')
    check('Empty' not in got, 'Invisibility (built-in Camo) dropped, empty line removed')
    check(got.get('Spaced') == {'Halo 3': ['Power Drain'], 'Halo 3: ODST': []},
          'names canonicalised; an explicit empty ODST cell is kept')
    sp = next(l for l in clean if l['name'] == 'Spaced')
    check(he.line_stage(db, sp, 'Halo 3: ODST') == [], 'explicit [] ODST: a gap, not Halo 3')
    check(len(warn) == 8, '8 warnings, one per drop (%d)' % len(warn))

    print('\n7. refund rounding (nearest, halves up)')
    check([he.refund_picks(n, 50) for n in range(6)] == [0, 1, 1, 2, 2, 3], '50 %: 0..5')
    check(he.refund_picks(4, 30) == 1 and he.refund_picks(5, 30) == 2
          and he.refund_picks(3, 100) == 3 and he.refund_picks(1, 10) == 0, '30 / 100 / 10 %')

    print('\n8. settings and runs')
    for k in ('equipment_lines_enabled', 'equipment_lines', 'equipment_refund_enabled',
              'equipment_refund_percent'):
        check(k in he.OPTION_KEYS and k in he.SETTINGS_KEYS, '%s travels (run + settings)' % k)
    check(saved.get('equipment_lines') is not None, 'CONFIG holds a concrete table')
    with contextlib.redirect_stdout(io.StringIO()):
        old = he.RunState.from_dict({'phase': 'weapon_selection', 'rounds': [],
                                     'options': {'two_player_coop': True}})
    check(old.options.get('equipment_lines_enabled') is False
          and old.options.get('equipment_refund_enabled') is False,
          'a run saved before the keys loads with lines and refunds off')
    he.CONFIG.update({'equipment_lines_enabled': True, 'equipment_refund_enabled': True})
    snap = he.RunState().to_dict()
    with contextlib.redirect_stdout(io.StringIO()):
        new = he.RunState.from_dict(snap)
    check(new.options.get('equipment_lines_enabled') is True
          and new.options.get('equipment_lines') == he.CONFIG.get('equipment_lines'),
          'a new run round-trips its lines options')

    he.CONFIG.clear()
    he.CONFIG.update(saved)
    print('\n%s' % ('ALL PASSED' if not FAILS else '%d FAILED' % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
