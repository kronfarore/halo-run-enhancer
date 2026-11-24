r"""Stage the RATE OF FIRE rule test: does a game fire its tag rate, or a 30 Hz reset rate?

    python sprint_toolkit\rof_test_stage.py              # stage all five games
    python sprint_toolkit\rof_test_stage.py "Halo 4"     # only the named game(s)
    python sprint_toolkit\rof_test_stage.py --expect     # print the expected readings only

Halo 1 and Halo 2 fire by the 30 Hz RESET rule (Halo 2 measured on the Plasma Repeater port,
reports/h2_fire_rule.jsonl): rate / 30 added a tick, a shot at 1, the sum reset -> only 30/n
rounds a second. Halo 3, ODST, Reach and Halo 4 are not measured. This test tells the rules
apart with ONE boot per game, read off the battery HUD the way the Plasma Repeater was:

  the game's plasma weapon (placed at the player's start): a FLAT 24/s (acceleration 0, fire
  recovery 0), battery 1% a round, heat H = 0.1167 a round, heat loss L = 2.0/s (drains while
  firing, as every game does), overheat at 1.0. Heat climbs by H - L / r a round, so
      fires 24/s (the tag; any carry rule)        overheats on round ~30  -> battery ~70
      60 Hz reset (24 -> every 3 ticks = 20/s)    overheats on round ~60  -> battery ~40
      30 Hz reset (24 -> every 2 ticks = 15/s)    NEVER overheats: the battery runs out
  Halo 2 (Cairo Station) answers the open Halo 2 question instead -- does it fire 30/s or cap
  at 15/s like Halo 1? -- with a flat 30/s, H = 0.0833, L = 1.5:
      fires 30/s -> overheats on round ~30 (battery ~70);  15/s cap -> never overheats.

The user's test: pick the weapon up, hold the trigger from cold until it overheats or the
battery is empty, and read the battery number at the overheat (or "empty, no overheat").

Levels and test aids are stable_grenades_stage's (E: baselines through halo_patch.apply_run,
god shield, run x2, the cheat weapon); rof_test.cmd swaps the copies in and back.
"""
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stable_grenades_stage as SG   # noqa: E402  (chdir to the tool folder, CONFIG, buffs)

hp, C = SG.hp, SG.C
OUT = r'E:\HaloBackups\rof_test'
B = chr(92)
WEAPON = {
    'Halo 2': B.join(('objects', 'weapons', 'rifle', 'plasma_rifle', 'plasma_rifle')),
    'Halo 3': B.join(('objects', 'weapons', 'rifle', 'plasma_rifle', 'plasma_rifle')),
    'Halo 3: ODST': B.join(('objects', 'weapons', 'rifle', 'plasma_rifle', 'plasma_rifle')),
    'Halo Reach': B.join(('objects', 'weapons', 'rifle', 'plasma_rifle', 'plasma_rifle')),
    'Halo 4': B.join(('objects', 'weapons', 'rifle', 'storm_assault_carbine', 'storm_assault_carbine')),
}
RATE = {'Halo 2': 30.0}            # every other game: 24
DEFAULT_RATE = 24.0
LOSS = {'Halo 2': 1.5}             # every other game: 2.0
DEFAULT_LOSS = 2.0
BATTERY = 0.01                     # a round: the HUD battery counts rounds down from 100


def fit(game):
    """(rate, heat a round, loss): overheat on round 30 if the tag rate fires."""
    r, L = RATE.get(game, DEFAULT_RATE), LOSS.get(game, DEFAULT_LOSS)
    return r, round(1.0 / 30.0 + L / r, 6), L


def ops(game):
    r, h, L = fit(game)
    rows = [('Rounds Per Second', 'Barrels', r), ('Rounds Per Second Max', 'Barrels', r),
            ('Acceleration Time', 'Barrels', 0.0), ('Fire Recovery Time', 'Barrels', 0.0),
            ('Heat Generated Per Round', 'Barrels', h), ('Overheated Threshold', None, 1.0),
            ('Heat Recovery Threshold', None, 0.1), ('Heat Loss Per Second', None, L),
            ('Overheated Heat Loss Per Second', None, 0.35),
            ('Age Generated Per Round', 'Barrels', BATTERY)]
    if game in ('Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4'):
        rows.append(('Campaign Age Generated Per Round', 'Barrels', BATTERY))
    return [{'field': f, 'block': b, 'index': 0, 'nth': 0, 'set': v} for f, b, v in rows]


def overheat_round(rate, heat, loss, hz, carry, shots=200):
    """Round on which the gun overheats (None = never in `shots` rounds) under a tick rule:
    `hz` ticks a second (None = continuous time), sum reset (carry False) or carried."""
    h, n = 0.0, 0
    if hz is None:
        for n in range(1, shots + 1):
            h += heat
            if h >= 1.0:
                return n
            h = max(0.0, h - loss / rate)
        return None
    s, t = 0.0, 0
    while n < shots and t < 60 * hz:
        s += rate / hz
        if s >= 1.0 - 1e-6:
            s = s - 1.0 if carry else 0.0
            n += 1
            h += heat
            if h >= 1.0:
                return n
        h = max(0.0, h - loss / hz)
        t += 1
    return None


def expect(game):
    r, h, L = fit(game)
    out = []
    for name, hz, carry in (('fires the tag rate (continuous)', None, False),
                            ('30 Hz, remainder carried', 30, True),
                            ('60 Hz reset', 60, False),
                            ('30 Hz reset (Halo 1 / 2)', 30, False)):
        k = overheat_round(r, h, L, hz, carry)
        out.append('%-34s %s' % (name, 'overheat on round %d -> battery %d' % (k, 100 - k)
                                 if k else 'never overheats: battery runs out'))
    if game == 'Halo 2':
        out.append('%-34s %s' % ('a 15/s cap (2 ticks)', 'never overheats: battery runs out'))
    k = int(math.ceil(1.0 / h - 1e-9))
    out.append('%-34s %s' % ('(heat does NOT drain while firing)', 'overheat on round %d -> battery %d: '
                             'the rate cannot be read, the heat model is wrong' % (k, 100 - k)))
    return out


def stage(game):
    mid = SG.LEVELS[game]
    reg = hp.PluginRegistry(C['assembly_plugins_dir'], C['plugin_subdirs_by_game'][game])
    sub = C['map_game_folder'][game]
    live = hp.default_map_path(C['mcc_root'], sub, mid)
    src = hp.existing_baseline(live, C.get('baseline_root'), sub)
    name = os.path.basename(live)
    dst = os.path.join(OUT, 'rof', sub.replace('/', os.sep), name)
    print('##', game, name, '<-', src, flush=True)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    plan = [{'tag': 'weap ' + WEAPON[game], 'name': 'Rate of fire test', 'ops': ops(game),
             'weapon': 'rof test'}]
    res, _ = hp.apply_run(dst, plan, reg, 'Normal', backup=False, game=game,
                          from_baseline=False, spawn_weapons={'groups': [[WEAPON[game]]]})
    for r in res:
        if r.get('effect') == 'Rate of fire test' or 'spawn' in str(r.get('effect') or ''):
            print('   %s %s %s: %s -> %s' % ('ok  ' if r.get('ok') else 'FAIL', r.get('tag'),
                                           r.get('field'), r.get('old'),
                                           r.get('new') or r.get('reason')), flush=True)
        elif not r.get('ok') and not r.get('skip'):
            print('   FAIL', r.get('effect'), r.get('tag'), r.get('reason'))
    buffs = {'Halo 2': SG.h2_test_buffs, 'Halo 3': SG.h3_test_buffs,
             'Halo 3: ODST': SG.odst_test_buffs, 'Halo Reach': SG.reach_test_buffs,
             'Halo 4': SG.h4_test_buffs}[game]
    print('   buffs:', '; '.join(buffs(dst)), flush=True)
    if game == 'Halo 3: ODST':
        # ODST takes no placed starting weapons (not a marker game): the plasma rifle goes in
        # as the SECONDARY of every non-empty starting profile (odst_armed_test's cheat write;
        # h100's profiles do reach the player -- the Silenced SMG primary stays)
        import contextlib
        import io
        import odst_armed_test as T
        with contextlib.redirect_stdout(io.StringIO()):
            m = hp.open_map(dst, game)
        ref = hp._h3_tag_datum(m, 'weap', WEAPON[game])
        n = 0
        for pr in m.follow_all(hp._scnr_base(m), [T.PROFILES], [T.PROFILE_ES], 'all'):
            if ref is not None and not hp._profile_is_empty(m, pr, game):
                hp._write_starting_weapon(m, pr, 'secondary', ref, -1, -1, game)
                n += 1
        m.save(dst)
        print('   plasma rifle as the secondary of %d profiles' % n, flush=True)
    for line in expect(game):
        print('   expect:', line)
    return dst


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    games = args or list(WEAPON)
    if '--expect' in sys.argv:
        for g in games:
            print('##', g, 'rate %g, heat %g a round, loss %g' % fit(g))
            for line in expect(g):
                print('  ', line)
        return
    path = os.path.join(OUT, 'staged.json')
    try:
        log = {r['game']: r for r in json.load(open(path, encoding='utf-8'))}
    except (OSError, ValueError):
        log = {}
    for g in games:
        log[g] = {'game': g, 'level': SG.LEVELS[g], 'weapon': WEAPON[g], 'map': stage(g),
                  'rate/heat/loss': fit(g), 'expect': expect(g)}
    os.makedirs(OUT, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump([log[g] for g in WEAPON if g in log], f, indent=1)


if __name__ == '__main__':
    main()
