r"""Stage the Stable Grenades in-game test: one level per game, built from the E: baseline.

    python sprint_toolkit\stable_grenades_stage.py            # build both sets
    python sprint_toolkit\stable_grenades_stage.py --check    # only re-read the staged maps
    python sprint_toolkit\stable_grenades_stage.py "Halo 1"   # only the named game(s)

Two sets under E:\HaloBackups\stable_grenades_test\, each laid out like the MCC folder:
  vanilla\  the baseline through halo_patch.apply_run with an EMPTY plan
  stable\   the same, plus the Stable Grenades card of every grenade of that game
  itemonly\ Halo 2 only: the card's item-flag write alone (no hlmt write). Tells whether
            the eqip flag by itself stops a pickup chaining -- the H2 plasma pickup shares
            its hlmt TAG with the thrown plasma grenade, so the hlmt write reaches both.
Both go through the same apply_run with the same options, so the ONLY difference between
the two is this card. stable_grenades_test.cmd swaps them into the game (and back).

Levels (placed grenade pickups, scnr Equipment block, 2026-11-05):
  Halo 1  a30 Halo                  17 frag (plasma only from Covenant drops)
  Halo 2  01b Cairo Station         13 frag, 26 plasma
  Halo 3  100 The Covenant          18 frag, 22 plasma, 26 spike, 1 firebomb
  ODST    h100 Mombasa Streets      28 frag, 13 plasma, 7 spike, 17 firebomb
  Reach   m60 The Package           18 frag, 12 plasma
  Halo 4  m40_invasion Infinity     8 frag, 61 plasma, 4 pulse
"""
import json
import os
import shutil
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
import halo_enhancer as he    # noqa: E402
import halo_patch as hp       # noqa: E402

C = dict(he.CONFIG)
C.update(json.load(open(os.path.join(TOOL, 'settings.json'), encoding='utf-8')))
OUT = r'E:\HaloBackups\stable_grenades_test'
LEVELS = {'Halo 1': 'a30', 'Halo 2': '01b', 'Halo 3': '100', 'Halo 3: ODST': 'h100',
          'Halo Reach': 'm60', 'Halo 4': 'm40_invasion'}
GRENADES = ('Frag Grenade', 'Plasma Grenade', 'Claymore Grenade', 'Firebomb Grenade',
            'Pulse Grenade')
DB = json.load(open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
GAMES = list(DB['Missions'])
SW = DB['Player Modifiers']['Specific Weapon Modifier']


def plan_for(game, item_only=False):
    """The plan PatchDialog builds for one positive pick of each grenade's card
    (item_only: keep only the eqip item-flag ops)."""
    plan = []
    for w in GRENADES:
        eff = SW[w].get('Stable Grenades')
        if not eff or game not in eff['game']:
            continue
        ops = [{'field': t['field'], 'block': t.get('block'), 'index': 0,
                'nth': t.get('nth', 0) or 0, 'tag': t.get('tag'),
                'unshare': bool(t.get('unshare')),
                ('set_bit' if t.get('flag_on') else 'clear_bit'): t['flag']}
               for t in he.resolve_gamed(eff['targets'], game, GAMES)
               if not item_only or (t.get('tag') or '').startswith('eqip ')]
        plan.append({'tag': he.resolve_gamed(eff['tag'], game, GAMES),
                     'name': 'Stable Grenades', 'ops': ops, 'weapon': w})
    return plan


def flag_rows(path, game, reg):
    """(tag, flags) of the grenade pickups' item flags and models' damage flags."""
    m = hp.open_map(path, game)
    out = []
    eq = reg.get('eqip')
    allf = [f for f in eq.fields if f['name'].lower() == 'flags']
    item = [i for i, f in enumerate(allf) if 'always maintains z up' in (f.get('bits') or {})]
    for tp, tb in m.find_tags('eqip', '*grenade*'):
        out.append(('eqip ' + tp, m.read_tag_field(tb, 'Flags', eq, None, 0, item[0])))
    if game != 'Halo 1':
        pl = reg.get('hlmt')
        blk = 'Old Damage Info' if game in ('Halo Reach', 'Halo 4') else 'New Damage Info'
        for tp, tb in m.find_tags('hlmt', '*grenade*'):
            v = m.read_tag_field(tb, 'Flags', pl, blk)
            if v is not None:
                out.append(('hlmt ' + tp, v))
    return out


def main(check_only=False, only=()):
    for g, mid in LEVELS.items():
        if only and g not in only:
            continue
        reg = hp.PluginRegistry(C['assembly_plugins_dir'], C['plugin_subdirs_by_game'][g])
        sub = C['map_game_folder'][g]
        live = hp.default_map_path(C['mcc_root'], sub, mid)
        src = hp.existing_baseline(live, C.get('baseline_root'), sub)
        name = os.path.basename(live)
        print('##', g, name, '<-', src, flush=True)
        staged = {}
        for kind in ('vanilla', 'stable') + (('itemonly',) if g == 'Halo 2' else ()):
            dst = os.path.join(OUT, kind, sub.replace('/', os.sep), name)
            staged[kind] = dst
            if check_only:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            plan = plan_for(g, kind == 'itemonly') if kind != 'vanilla' else []
            res, _ = hp.apply_run(dst, plan, reg, 'Normal', backup=False, game=g,
                                  from_baseline=False)
            mine = [r for r in res if r.get('effect') == 'Stable Grenades']
            print('  %-8s %d rows (%d card: %d applied, %d skipped, %d failed)  sig %s' % (
                kind, len(res), len(mine),
                sum(1 for r in mine if r.get('ok') and not r.get('skip')),
                sum(1 for r in mine if r.get('skip')),
                sum(1 for r in mine if not r.get('ok') and not r.get('skip')),
                hp.patch_signature(res)), flush=True)
            for r in res:
                if not r.get('ok') and not r.get('skip'):
                    print('     FAIL', r.get('effect'), r.get('tag'), r.get('reason'))
        rows = {k: dict(flag_rows(v, g, reg)) for k, v in staged.items()}
        a = rows['vanilla']
        for k in sorted(set().union(*rows.values())):
            print('     %-80s %s%s' % (k, '  '.join('%s %-5s' % (kind, r.get(k))
                                                for kind, r in rows.items()),
                  '   <- card' if any(r.get(k) != a.get(k) for r in rows.values()) else ''))


if __name__ == '__main__':
    main('--check' in sys.argv, [a for a in sys.argv[1:] if not a.startswith('--')])
