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


def walk(db, state, games, via='next_level', start=None):
    """Enter each game in turn, as Next level does; {game: (p1 items, p2 items, entries)}."""
    out, prev = {}, start
    for g in games:
        added = he.apply_line_transitions(db, state, g, from_game=prev, via=via)
        out[g] = (list(state.player1_weapons), list(state.player2_weapons), added)
        prev = g
    return out


def phase2(db):
    """Transitions, the offer rule, display (plan section 10, Phase 2)."""
    S, C = he.SPRINT_ITEM, he.CAMO_ITEM
    he.CONFIG.update({'equipment_lines_enabled': True, 'equipment_lines': None,
                      'remove_superflare_jammer': False,
                      'remove_invincibility_invisibility': False,
                      'sprint_feature': True, 'h4_sprint_mode': 'restore'})

    print('\n9. walk Halo 1 -> Halo 4 (Next level)')
    st = he.RunState()
    st.player1_weapons, st.player1_weapon = ['Assault Rifle', C], 'Assault Rifle'
    st.player2_weapons, st.player2_weapon = [S, 'Pistol'], S
    w = walk(db, st, ['Halo 1', 'Halo 2', 'Halo 3'])
    check(w['Halo 1'][:2] == (['Assault Rifle', C], [S, 'Pistol']) and not w['Halo 1'][2]
          and not w['Halo 2'][2], 'Halo 1 / 2: nothing changes, nothing logged')
    check(w['Halo 3'][0] == ['Assault Rifle', 'Invisibility'], 'H3: 👁 Camo -> Invisibility')
    check(w['Halo 3'][1] == [S, 'Pistol']
          and sorted((e['player'], str(e['to'])) for e in w['Halo 3'][2])
          == [('player1', 'Invisibility'), ('player2', 'None')],
          'H3: ⚡ Sprint stays, dormant (one gap entry)')
    # Halo 3 drafts: Decoy x2 (P1), Turret + Mobility (P2), Power Drain (no line)
    st.player1_weapons += ['Jammer', 'Superflare', 'Power Drain']
    st.player2_weapons += ['Auto Turret', 'Grav Lift']
    st.rounds.append({'player1': {'weapon': 'Jammer', 'mod': None, 'gained_weapon': None},
                      'player2': {'weapon': 'Grav Lift', 'mod': None, 'gained_weapon': None},
                      'enemy1': None, 'enemy2': None, 'wildcard': None,
                      'boss1': None, 'boss2': None})
    w = walk(db, st, ['Halo 3: ODST', 'Halo Reach', 'Halo 4'], start='Halo 3')
    check(not w['Halo 3: ODST'][2] and w['Halo 3: ODST'][0][-3:] == ['Jammer', 'Superflare',
                                                                     'Power Drain'],
          'ODST: nothing changes; Sprint still dormant, no second entry')
    check(w['Halo Reach'][0] == ['Assault Rifle', 'Active Camouflage', 'Hologram', 'Power Drain'],
          'Reach P1: Invisibility -> Active Camouflage; Jammer + Superflare -> ONE Hologram; '
          'Power Drain (no line) kept')
    check(w['Halo Reach'][1] == ['Sprint', 'Pistol', 'Auto Turret', 'Jet Pack']
          and st.player2_weapon == 'Sprint',
          'Reach P2: ⚡ Sprint -> Sprint (primary follows), Grav Lift -> Jet Pack, '
          'Auto Turret dormant')
    r = {(e['player'], e['line']): e for e in w['Halo Reach'][2]}
    check(r[('player1', 'Decoy')]['from'] == ['Jammer', 'Superflare']
          and r[('player2', 'Turret')]['to'] is None and r[('player1', 'Decoy')]['after_round'] == 1
          and all(e['via'] == 'next_level' and e['from_game'] == 'Halo 3: ODST'
                  for e in w['Halo Reach'][2]),
          'Reach log: merge, gap, after_round, via and from_game recorded')
    check(not w['Halo 4'][2] and w['Halo 4'][1] == ['Sprint', 'Pistol', 'Auto Turret', 'Jet Pack'],
          'H4: nothing renamed (Auto Turret active again, Sprint stays Sprint)')
    for e in st.line_log:
        print('       ' + he.line_entry_text(e))

    print('\n10. display')
    t1, tip1 = he.arsenal_text(db, st, 'player1', 'Halo 4')
    check(t1 == 'Assault Rifle, Active Camouflage, Hologram, Power Drain'
          and 'Camo line: 👁 Camo (Halo 2) -> Invisibility (Halo 3) -> Active Camouflage '
              '(Halo Reach)' in tip1,
          'H4 P1 tooltip traces the Camo line: %r' % tip1.split('\n')[0])
    t2, tip2 = he.arsenal_text(db, st, 'player2', 'Halo Reach')
    check('Auto Turret (inactive in Halo Reach)' in t2
          and 'Turret line: Auto Turret; inactive in Halo Reach; becomes Auto Turret in Halo 4'
          in tip2, 'Reach P2: Auto Turret marked inactive, tooltip names Halo 4')
    st3 = he.RunState()
    st3.player2_weapons = [S]
    t3, tip3 = he.arsenal_text(db, st3, 'player2', 'Halo 3')
    check(t3 == '⚡ Sprint (inactive in Halo 3)' and 'becomes Sprint in Halo Reach' in tip3,
          'H3: ⚡ Sprint inactive, becomes Sprint in Reach')

    print('\n11. offers: a held line is taken for both players')
    pool = ['Active Camouflage', 'Drop Shield', 'Jet Pack', 'Armor Lock', 'Hologram', 'DMR']
    st4 = he.RunState()
    st4.player1_weapons = ['Invisibility']            # carried, not renamed yet
    st4.player2_weapons = ['Grav Lift']
    check(he.drop_weapons_taken(db, pool, st4) == ['Drop Shield', 'Armor Lock', 'Hologram', 'DMR'],
          'Invisibility held -> Active Camouflage taken; Grav Lift -> Jet Pack taken')
    he.CONFIG['equipment_lines_enabled'] = False
    check(he.drop_weapons_taken(db, pool, st4) == ['Drop Shield', 'Jet Pack', 'Armor Lock',
                                                   'Hologram', 'DMR'],
          'table off: only the built-in Camo line counts')
    he.CONFIG['equipment_lines_enabled'] = True
    he.CONFIG.update({'sprint_as_card': True, 'sprint_start_with': False,
                      'sprint_need_weapon': False,
                      'abilities_offered': ['sprint', 'overshield', 'regeneration', 'camo']})
    st5 = he.RunState()
    st5.player1_weapons = ['Assault Rifle', 'Invisibility']
    st5.player2_weapons = ['Pistol']
    got = he.ability_offer_pool(db, 'Halo 1', st5, 'player2')
    check(C not in got and S in got, 'H1: Invisibility held -> 👁 Camo not offered (%s)' % got)

    print('\n12. Halo 4 holder, gaps and denied items, backwards, table off')
    he.CONFIG['h4_sprint_mode'] = 'holder'
    pm = db.get_player_modifiers_filtered([S], set(), 'Halo 4')
    check(any(m.get('equipment') == 'Sprint' for m in pm), 'holder: ⚡ Sprint holder gets Sprint cards')
    he.CONFIG['h4_sprint_mode'] = 'off'
    st6 = he.RunState()
    st6.player1_weapons = ['Sprint']
    w = walk(db, st6, ['Halo 4'], start='Halo Reach')
    check(w['Halo 4'][0] == ['Sprint'] and w['Halo 4'][2][0]['to'] is None,
          'h4_sprint_mode off: Sprint dormant in Halo 4')
    he.CONFIG['h4_sprint_mode'] = 'restore'
    he.CONFIG['remove_superflare_jammer'] = True
    st7 = he.RunState()
    st7.player1_weapons = ['Hologram', 'Active Camouflage', 'Jet Pack', 'Sprint']
    w = walk(db, st7, ['Halo 3'], via='manual', start='Halo Reach')
    check(w['Halo 3'][0] == ['Hologram', 'Invisibility', 'Grav Lift', 'Sprint'],
          'backwards to H3, Jammer/Superflare denied: Hologram + Sprint dormant, '
          'Camo and Mobility follow')
    check(all(e['via'] == 'manual' for e in w['Halo 3'][2]), 'manual change logged as manual')
    he.CONFIG['remove_superflare_jammer'] = False
    w = walk(db, st7, ['Halo 1'], via='manual', start='Halo 3')
    check(w['Halo 1'][0] == ['Hologram', C, 'Grav Lift', S],
          'on to H1: Camo -> 👁 Camo, Sprint -> ⚡ Sprint, the rest dormant')
    he.CONFIG['equipment_lines_enabled'] = False
    st8 = he.RunState()
    st8.player1_weapons = ['Grav Lift', 'Invisibility']
    w = walk(db, st8, ['Halo Reach'], start='Halo 3: ODST')
    check(w['Halo Reach'][0] == ['Grav Lift', 'Active Camouflage'],
          'table off: Grav Lift stays, the built-in Camo line still renames')
    he.CONFIG['equipment_lines_enabled'] = True

    print('\n13. line_log is saved with the run')
    with contextlib.redirect_stdout(io.StringIO()):
        back = he.RunState.from_dict(st.to_dict())
    check(back.line_log == st.line_log and back.player2_weapons == st.player2_weapons,
          '.run round trip keeps line_log (%d entries) and the renamed arsenal' % len(st.line_log))
    with contextlib.redirect_stdout(io.StringIO()):
        old = he.RunState.from_dict({'phase': 'player1_turn', 'rounds': []})
    check(old.line_log == [], 'an old run loads with an empty line_log')


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

    phase2(db)

    he.CONFIG.clear()
    he.CONFIG.update(saved)
    print('\n%s' % ('ALL PASSED' if not FAILS else '%d FAILED' % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
