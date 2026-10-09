r"""Self-test for damage_rows.py (the Effective / Hardened cards).

One baseline map per game is COPIED into a scratch folder (the baselines and the live MCC
maps are never written). Per map:

  census  every combo of damage_rows.COMBOS: rows hit (non-zero), immunity rows kept at 0,
          (group, armour) pairs with no row (engine x1), groups / armour rows absent.
  ops     player_armour.apply first (Halo 2 on), then a few cards' ops on the same image
          (*1.4 each, then a Hardened *0.8 on one of them). After each op the WHOLE image is
          compared with the image before it: exactly the planned value offsets changed, each
          by the factor (float32), and nothing else -- so zeros, the player's own rows, the
          Cyborg columns (Halo 1) and every other row are untouched by construction; the
          player's key rows and the Cyborg columns are checked explicitly as well. Every
          Armor Modifiers array's keys are unchanged and still sorted.
  run     a full halo_patch.apply_run on the scratch copy with one Effective card in the plan:
          no failed row, player_armour ran (Halo 2 on), and after reopening the saved map
          every planned row reads baseline x the factor while the player's own rows read
          what the shared rows read before.

    python sprint_toolkit/damage_rows_selftest.py [--scratch DIR] [--only "Halo 3"] [--census]
"""
import argparse
import gc
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
import halo_patch as hp          # noqa: E402
import damage_rows as dr         # noqa: E402
import player_armour as pa       # noqa: E402

BASE = r'E:\HaloBaselines'
PLUGINS = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
SUB = {'Halo 1': 'Halo1MCC', 'Halo 2': 'Halo2MCC', 'Halo 3': 'Halo3MCC', 'Halo 3: ODST': 'ODSTMCC',
       'Halo Reach': 'ReachMCC', 'Halo 4': 'Halo4MCC'}
MAPS = [
    ('Halo 1', r'halo1\maps\b30.map'),
    ('Halo 2', r'halo2\h2_maps_win64_dx11\03a_oldmombasa.map'),
    ('Halo 3', r'halo3\maps\010_jungle.map'),
    ('Halo 3: ODST', r'halo3odst\maps\sc100.map'),
    ('Halo Reach', r'haloreach\maps\m10.map'),
    ('Halo 4', r'halo4\maps\m10_crash.map'),
]
#: the cards whose ops are tested per game (damage, armour)
OPS = {
    'Halo 1': [('plasma', 'shields'), ('bullets', 'flesh'), ('anything', 'flood'), ('explosives', 'vehicles')],
    'Halo 2': [('plasma', 'shields'), ('bullets', 'brute_hide'), ('anything', 'flood'), ('precision', 'hunters')],
    'Halo 3': [('plasma', 'shields'), ('bullets', 'flesh'), ('anything', 'flood'), ('lasers', 'vehicles'),
               ('turrets', 'vehicles')],
    'Halo 3: ODST': [('plasma', 'shields'), ('bullets', 'brute_hide'), ('precision', 'shields'),
                     ('explosives', 'vehicles')],
    'Halo Reach': [('plasma', 'shields'), ('needles', 'shields'), ('bullets', 'flesh'), ('blades', 'armour')],
    'Halo 4': [('plasma', 'armour'), ('needles', 'shields'), ('explosives', 'vehicles'), ('lasers', 'shields'),
               ('turrets', 'flesh')],
}
FACTOR = 1.4
HARD = 0.8
ADD, SUBTRACT, FLOOR = 0.3, 0.9, 0.1      # the (+) / (-) cards' ops, with the row floor


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def census(m, game):
    rows = []
    for d, a, games in dr.COMBOS:
        p = dr.plan(m, game, {'damage': d, 'armour': a})
        rows.append(dict(d=d, a=a, asked=game in games, hits=len(p['hits']), zeros=p['zeros'],
                         missing=len(p['missing']), missing_list=p['missing'],
                         absent_groups=p['absent_groups'], absent_armour=p['absent_armour'],
                         jpts=len(set(h[0] for h in p['hits'])) if p['kind'] == 'jpt' else None,
                         t0=sum(1 for h in p['hits'] if p['kind'] == 'table' and h[0] == 0)))
    return rows


def diff_offsets(a, b):
    import numpy as np
    n = min(len(a), len(b))
    x = np.frombuffer(a, dtype=np.uint8, count=n)
    y = np.frombuffer(b, dtype=np.uint8, count=n)
    d = np.nonzero(x != y)[0]
    return set(int(i) for i in d), len(a) != len(b)


def player_rows(m, game):
    """{(table, group name, key): value} of the player's own key rows."""
    keys = {k for k, _o in getattr(m, '_player_armour_keys', ())}
    out = {}
    c = pa._Ctx(m, game)
    for t, groups in c.tables():
        for _ge, g, _rn, _rb, rows in groups:
            for k, v in rows:
                if k in keys:
                    out[(t, pa.sid_name(m, game, g), k)] = v
    return out


def all_arrays_sorted(m, game):
    c = pa._Ctx(m, game)
    bad = 0
    for _t, groups in c.tables():
        for _ge, _g, rn, rb, _rows in groups:
            ks = [struct.unpack_from('<i', m.data, rb + i * 8)[0] for i in range(rn)]
            if any(x > y for x, y in zip(ks, ks[1:])):
                bad += 1
    return bad


def keyed_values(m, game, spec):
    """{(table, group, armour) or (jpt, column): value} of a card's non-zero rows."""
    p = dr.plan(m, game, spec)
    if p['kind'] == 'jpt':
        return {(h[0], h[1]): h[3] for h in p['hits']}
    return {(h[0], h[1], h[2]): h[4] for h in p['hits']}


def test_lift(m, game, S):
    """No immunities: exactly the planned values change, each to the floor; afterwards
    nothing in scope is below it, the left-alone rows are the same, arrays stay sorted."""
    hits, skipped = dr.lift_plan(m, game)
    before = bytes(m.data)
    res = dr.lift_immunities(m, game)
    if not res or not res[0]['ok']:
        S['fail'].append('lift: %s' % res)
        return
    changed, grew = diff_offsets(before, m.data)
    allowed = set()
    for off, _v, _l in hits:
        allowed.update(range(off, off + 4))
        if struct.unpack_from('<f', m.data, off)[0] != f32(dr.LIFT_FLOOR):
            S['fail'].append('lift: %#x not at the floor' % off)
    if grew or changed - allowed:
        S['fail'].append('lift: %d byte(s) changed outside the planned rows' % len(changed - allowed))
    again, skipped2 = dr.lift_plan(m, game)
    if again or skipped2 != skipped:
        S['fail'].append('lift: %d row(s) still below the floor, skipped %d -> %d'
                         % (len(again), skipped, skipped2))
    if game != 'Halo 1' and all_arrays_sorted(m, game):
        S['fail'].append('lift: unsorted array(s)')
    S['lift'] = '%d value(s) -> %g (%d zeros), %d left alone; %s' % (
        len(hits), dr.LIFT_FLOOR, sum(1 for h in hits if h[1] == 0), skipped, res[0].get('new'))


def test_ops(m, game, S):
    fails = S['fail']
    specs = [{'damage': d, 'armour': a} for d, a in OPS[game]]
    # the Hardened op runs on the first card again, after the others; then the adding
    # cards: +ADD on the second, -SUBTRACT (floored) on the first
    seq = ([(s, '*%g' % FACTOR, None) for s in specs] + [(specs[0], '*%g' % HARD, None)]
           + [(specs[1], '+%g' % ADD, FLOOR), (specs[0], '-%g' % SUBTRACT, FLOOR)])
    want_of = {'*%g' % FACTOR: lambda v: v * FACTOR, '*%g' % HARD: lambda v: v * HARD,
               '+%g' % ADD: lambda v: v + ADD,
               '-%g' % SUBTRACT: lambda v: max(min(v, FLOOR), v - SUBTRACT)}
    for spec, op, floor in seq:
        lab = dr.label(spec) + ' ' + op
        p = dr.plan(m, game, spec)
        if not p['hits']:
            fails.append('%s: no rows to scale' % lab)
            continue
        pr_before = player_rows(m, game) if game != 'Halo 1' else None
        before = bytes(m.data)
        res = dr.apply_op(m, game, None, spec, op, floor=floor)
        if not res or not res[0]['ok'] or res[0].get('skip'):
            fails.append('%s: %s' % (lab, res))
            continue
        changed, grew = diff_offsets(before, m.data)
        if grew:
            fails.append('%s: the image changed size' % lab)
        want = want_of[op]
        allowed = set()
        bad_vals = 0
        for h in p['hits']:
            off, v = h[-2], h[-1]
            allowed.update(range(off, off + 4))
            nv = struct.unpack_from('<f', m.data, off)[0]
            if abs(nv - f32(want(v))) > 1e-6 * max(1.0, abs(v)):
                bad_vals += 1
        outside = changed - allowed
        if outside:
            fails.append('%s: %d byte(s) changed outside the planned rows (first %#x)'
                         % (lab, len(outside), min(outside)))
        if bad_vals:
            fails.append('%s: %d row(s) not changed by %s' % (lab, bad_vals, op))
        zeros_ok = all(struct.unpack_from('<f', m.data, h[-2])[0] != 0.0 for h in p['hits'])
        if not zeros_ok:
            fails.append('%s: a scaled row reads 0' % lab)
        if game == 'Halo 1':
            cy = [dr.H1_COLUMNS.index(c) for c in dr.H1_PLAYER_COLUMNS]
            for name, base in m.find_tags('jpt!', '*'):
                for i in cy:
                    o = dr.H1_COLUMNS_AT + 4 * i + base
                    if before[o:o + 4] != bytes(m.data[o:o + 4]):
                        fails.append('%s: Cyborg column changed on %s' % (lab, name))
        else:
            if player_rows(m, game) != pr_before:
                fails.append('%s: a player key row changed' % lab)
            if not pr_before:
                fails.append('%s: no player key rows found' % lab)
            nb = all_arrays_sorted(m, game)
            if nb:
                fails.append('%s: %d unsorted Armor Modifiers array(s)' % (lab, nb))
        floored = sum(1 for h in p['hits'] if floor is not None
                      and abs(struct.unpack_from('<f', m.data, h[-2])[0] - f32(min(h[-1], floor))) < 1e-6)
        S['ops'].append('%-38s %3d value(s) %s, %d zero(s) kept, %d missing pair(s), %d at the floor; '
                        '%d byte(s) changed' % (lab, len(p['hits']), op, p['zeros'], len(p['missing']),
                                                floored, len(changed)))
        del before


def run(game, rel, scratch, do_census):
    src = os.path.join(BASE, rel)
    if not os.path.isfile(src):
        raise SystemExit('MISSING baseline %s' % src)
    dst = os.path.join(scratch, 'dr_' + os.path.basename(rel))
    shutil.copyfile(src, dst)
    reg = hp.PluginRegistry(PLUGINS, [SUB[game]])
    S = {'map': os.path.basename(rel), 'game': game, 'fail': [], 'ops': []}
    try:
        m = hp.open_map(dst, game)
        if do_census:
            S['census_vanilla'] = census(m, game)
        run_spec = {'damage': OPS[game][0][0], 'armour': OPS[game][0][1]}
        base_vals = keyed_values(m, game, run_spec)
        if game != 'Halo 1':
            res = pa.apply(m, game, reg)
            bad = [r for r in res if not r['ok']]
            S['pa'] = '%d row(s), %d failed%s' % (len(res), len(bad), (': ' + '; '.join(
                '%s %s' % (r['field'], r.get('reason')) for r in bad)) if bad else '')
            if not getattr(m, '_player_armour_keys', None):
                S['fail'].append('player_armour gave no keys')
            # the shared rows' values the player's rows must still copy after the run
            pr0 = player_rows(m, game)
        if do_census:
            S['census'] = census(m, game)
        test_ops(m, game, S)
        test_lift(m, game, S)
        del m
        gc.collect()
        # --- full apply_run on the (untouched) scratch file
        plan = [{'tag': 'jpt! *' if game == 'Halo 1' else 'matg globals' + chr(92) + 'globals',
                 'name': 'Effective: ' + dr.label(run_spec), 'absent_is_skip': False,
                 'ops': [{'field': dr.label(run_spec), 'op_str': '*1.2', 'damage_row': run_spec}]}]
        results, _bak = hp.apply_run(dst, plan, reg, 'Normal', backup=False, game=game,
                                     player_armour=True)
        bad = [r for r in results if not r.get('ok')]
        S['run'] = ['%s | %s | %s -> %s %s' % (r.get('effect'), r.get('field'), r.get('old'), r.get('new'),
                                             r.get('reason') or '') for r in results
                    if r.get('effect') != pa.EFFECT or r.get('field') in ('rows', 'materials block')]
        for r in bad:
            S['fail'].append('apply_run: %s %s %s' % (r.get('effect'), r.get('field'), r.get('reason')))
        if game != 'Halo 1' and not any(r.get('effect') == pa.EFFECT for r in results):
            S['fail'].append('apply_run: player_armour did not run')
        if not any(r.get('effect') == plan[0]['name'] and r.get('ok') for r in results):
            S['fail'].append('apply_run: the card row is missing')
        gc.collect()
        m2 = hp.open_map(dst, game)
        after = keyed_values(m2, game, run_spec)
        wrong = [k for k, v in base_vals.items() if abs(after.get(k, -1) - f32(v * 1.2)) > 1e-6 * max(1, v)]
        if wrong or set(after) != set(base_vals):
            S['fail'].append('apply_run: %d of %d row(s) not x1.2 after reopening (%s)'
                             % (len(wrong), len(base_vals), wrong[:3]))
        S['run_rows'] = len(base_vals)
        if game != 'Halo 1':
            m2._player_armour_keys = []
            pa.apply(m2, game, reg)          # idempotent: only re-reads the keys
            pr2 = player_rows(m2, game)
            if pr2 != pr0:
                diffs = [k for k in pr0 if pr2.get(k) != pr0[k]]
                S['fail'].append('apply_run: player rows differ after the run (%d)' % len(diffs))
            nb = all_arrays_sorted(m2, game)
            if nb:
                S['fail'].append('apply_run: %d unsorted array(s)' % nb)
        del m2
        gc.collect()
        # --- without the option: no player rows, the card still applies (the player
        # shares the change -- intended)
        shutil.copyfile(src, dst)
        # a second card that crushes its rows to 1%: the lift runs LAST, so they end at 0.1
        crush = {'damage': OPS[game][1][0], 'armour': OPS[game][1][1]}
        plan2 = plan + [{'tag': plan[0]['tag'], 'name': 'Hardened: ' + dr.label(crush),
                         'absent_is_skip': False,
                         'ops': [{'field': dr.label(crush), 'op_str': '*0.01', 'damage_row': crush}]}]
        results, _bak = hp.apply_run(dst, plan2, reg, 'Normal', backup=False, game=game,
                                     no_immunities=True)
        if not any(r.get('field') == 'No immunities' and r.get('ok') for r in results):
            S['fail'].append('apply_run: No immunities did not run')
        if any(r.get('effect') == pa.EFFECT for r in results):
            S['fail'].append('apply_run without the option: player_armour ran')
        if not any(r.get('effect') == plan[0]['name'] and r.get('ok') and not r.get('skip')
                   for r in results):
            S['fail'].append('apply_run without the option: the card did not apply')
        gc.collect()
        m3 = hp.open_map(dst, game)
        after = keyed_values(m3, game, run_spec)
        # x1.2, then lifted to the floor last
        wrong = [k for k, v in base_vals.items()
                 if abs(after.get(k, -1) - max(f32(v * 1.2), f32(dr.LIFT_FLOOR))) > 1e-6 * max(1, v)]
        left = dr.lift_plan(m3, game)[0]       # incl. the crushed card's rows
        crushed = keyed_values(m3, game, crush)
        if not crushed or any(abs(v - f32(dr.LIFT_FLOOR)) > 1e-6 for v in crushed.values()
                              if v < 0.5):
            S['fail'].append('apply_run: the crushed card rows are not at the floor')
        if left:
            S['fail'].append('apply_run: %d row(s) below the floor after the run' % len(left))
        if wrong or not set(base_vals) <= set(after):      # lifted zeros join the card's rows
            S['fail'].append('apply_run without the option: %d row(s) not x1.2' % len(wrong))
        S['run_plain'] = ('without the player-rows option, with No immunities: %d row(s) x1.2, '
                          'player_armour not run, nothing below the floor, a *0.01 card ends at %g' % (
                              len(base_vals), dr.LIFT_FLOOR))
        del m3
        gc.collect()
    finally:
        gc.collect()
        try:
            os.remove(dst)
        except OSError as ex:
            S['fail'].append('could not delete scratch copy: %s' % ex)
    return S


def print_census(S):
    print('  census (after player_armour; vanilla equal unless noted):')
    van = {(r['d'], r['a']): r for r in S.get('census_vanilla', [])}
    for r in S['census']:
        v = van.get((r['d'], r['a']))
        note = '' if not v or v['hits'] == r['hits'] else '  (vanilla %d)' % v['hits']
        print('    %s %-11s vs %-10s hits %3d (t0 %3d) zeros %3d missing %3d%s%s%s%s' % (
            '*' if r['asked'] else ' ', r['d'], r['a'], r['hits'], r['t0'], r['zeros'], r['missing'],
            (' jpts %d' % r['jpts']) if r['jpts'] is not None else '',
            (' absent groups %s' % ','.join(r['absent_groups'])) if r['absent_groups'] else '',
            (' absent armour %s' % ','.join(r['absent_armour'])) if r['absent_armour'] else '', note))
        if r['missing'] and r['asked']:
            print('        no row: %s' % ', '.join('[%d] %s/%s' % x for x in r['missing_list'][:12]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch', default=os.path.join(
        os.environ.get('TEMP', '.'), 'damage_rows_selftest'))
    ap.add_argument('--only')
    ap.add_argument('--census', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.scratch, exist_ok=True)
    allok = True
    for game, rel in MAPS:
        if a.only and game != a.only:
            continue
        S = run(game, rel, a.scratch, a.census)
        print('=== %s %s: %s' % (game, S['map'], 'PASS' if not S['fail'] else 'FAIL'))
        if S.get('pa'):
            print('  player_armour: %s' % S['pa'])
        for o in S['ops']:
            print('  op  ' + o)
        for r in S.get('run', []):
            print('  run ' + r)
        print('  run: %d row(s) re-read x1.2' % S.get('run_rows', 0))
        if S.get('lift'):
            print('  lift: ' + S['lift'])
        if S.get('run_plain'):
            print('  run: ' + S['run_plain'])
        if a.census:
            print_census(S)
        for f in S['fail']:
            print('  FAIL ' + f)
        allok = allok and not S['fail']
        sys.stdout.flush()
    print('ALL PASS' if allok else 'FAILURES')
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
