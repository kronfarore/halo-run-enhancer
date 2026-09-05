r"""Settle how ODST hands starting weapons to co-op players. Needs two players, one
start, no checkpoint.

THE QUESTION
------------
Two models are consistent with everything the map files say, and they disagree about
what the patcher should write:

  SHARED   the two co-op players read the SAME profile; player 1's pick goes in its
           Primary slot and player 2's in its Secondary. Both players then spawn
           holding both weapons. This is what the tool does today, and it is the
           likeliest explanation for "every profile had both weapons".

  PER-PLAYER  each player reads their OWN profile -- player i gets profile
           (insertion ordinal * 4 + i) -- and each profile's Primary is that player's
           pick. This is what odst_profile_for() implements, behind
           `odst_profiles_by_insertion`, and what the profile NAMES imply: ONI Alpha
           Site calls its first four Player / odst02 / odst03 / odst04.

THE PROBE
---------
Writes an unmistakable pair into the two profiles of insertion point 0:

    profile 0   Primary = weapon A     Secondary = (emptied)
    profile 1   Primary = weapon B     Secondary = (emptied)

Then start the level in two-player co-op and look at what each player is HOLDING at
the very first frame, before touching anything.

    player 1 has A and player 2 has B      -> PER-PLAYER. The stride's player axis is
                                              real; turn odst_profiles_by_insertion on
                                              and it can replace both old switches.
    both players have A                    -> SHARED. Profiles are not per-player;
                                              odst_profile_for is wrong and should be
                                              dropped, and the today-behaviour stands.
    both players have A and B (two guns)   -> SHARED, and the secondary emptying did
                                              not take -- rerun with --keep-secondary
                                              to see which slot each weapon came from.
    player 1 has A, player 2 has nothing   -> PER-PLAYER, but profile 1's weapon did
                                              not resolve on this map; try --a/--b with
                                              two weapons this level definitely stocks.

Nothing here tests the INSERTION axis (whether the second insertion point uses
profiles 4-7). That needs playing to a checkpoint and reverting, and it only matters
once the player axis is settled -- if this probe says SHARED, the insertion axis is
moot.

SAFETY
------
Patches a copy by default and tells you where it is. `--in-place` writes the real map,
making the usual `.bak` first if there isn't one, so the Enhancer's own restore still
works. Never run it against a map while MCC is open.

Usage:
    python sprint_toolkit/odst_profile_probe.py sc100
    python sprint_toolkit/odst_profile_probe.py sc100 --in-place
    python sprint_toolkit/odst_profile_probe.py l300 --a rocket_launcher --b sniper_rifle
    python sprint_toolkit/odst_profile_probe.py sc100 --show      # read, write nothing
"""
import argparse
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.dirname(_HERE)
os.chdir(_TOOL)
sys.path.insert(0, _TOOL)

import halo_patch as hp                                          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_vault as V                                            # noqa: E402

GAME = 'Halo 3: ODST'
SUBDIRS = ['ODSTMCC', 'ODST']
CFG = json.load(open('settings.json', encoding='utf-8'))
ROOT = CFG.get('mcc_root') or (
    r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection')
MAPS = os.path.join(ROOT, 'halo3odst', 'maps')

# Two weapons that look nothing alike in the HUD or in the hands, so the answer is
# readable from a screenshot rather than from a weapon name in a menu.
DEFAULT_A = 'rocket_launcher'
DEFAULT_B = 'sniper_rifle'

WEAP_DIRS = ('rifle', 'pistol', 'support_high', 'support_low', 'melee', 'multiplayer')


def find_weapon(m, short):
    """The full weap tag path for a weapon basename on this map, or None."""
    for p, _ in m.find_tags('weap', '*'):
        if p.rsplit(chr(92), 1)[-1] == short:
            return 'weap ' + p
    return None


def profile_slots(m, registry):
    """(scnr_base, block offset, element size, count) for Player Starting Profile."""
    plug = registry.get('scnr')
    base = hp._scnr_base(m)
    if plug is None or base is None:
        return None
    f = None
    for fn in ('Starting Health Damage', 'Starting Health Modifier'):
        f = plug.find(fn, 'Player Starting Profile')
        if f:
            break
    if not f:
        return None
    boff = f['block_offsets'][-1]
    esize = f['block_sizes'][-1]
    return base, boff, esize, m.i32(base + boff)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mission', help='ODST mission id, e.g. sc100')
    ap.add_argument('--a', default=DEFAULT_A, help='weapon basename for profile 0')
    ap.add_argument('--b', default=DEFAULT_B, help='weapon basename for profile 1')
    ap.add_argument('--in-place', action='store_true',
                    help='patch the real map (makes a .bak first if none exists)')
    ap.add_argument('--keep-secondary', action='store_true',
                    help='leave the secondary slots alone instead of emptying them')
    ap.add_argument('--show', action='store_true', help='report only, write nothing')
    args = ap.parse_args()

    real = os.path.join(MAPS, args.mission + '.map')
    src = V.pristine_source('Halo 3: ODST', real)
    if not os.path.exists(src):
        print('no such map: %s' % real); return 1

    if args.show:
        target = src
    elif args.in_place:
        if not os.path.exists(bak):
            shutil.copy(real, bak)
            print('made baseline %s' % os.path.basename(bak))
        shutil.copy(bak, real)                  # always start from pristine
        target = real
    else:
        target = os.path.join(_TOOL, 'patches', args.mission + '.probe.map')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(src, target)

    reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], SUBDIRS)
    m = hp.open_map(target, GAME)
    slots = profile_slots(m, reg)
    if not slots:
        print('could not locate Player Starting Profile'); return 1
    base, boff, esize, count = slots

    starts = hp.odst_player_starts(m, GAME)
    n0 = len(starts.get(hp.ODST_START_INSERTION, []))
    print('%s: %d profiles, %d location(s) at insertion point 0'
          % (args.mission, count, n0))
    for i in range(min(count, 8)):
        poff = m.follow(base, [boff], [esize], i)
        nm = hp._profile_name(m, poff) if poff is not None else '?'
        print('    profile %-2d %s' % (i, nm))
    if args.show:
        return 0

    tag_a, tag_b = find_weapon(m, args.a), find_weapon(m, args.b)
    for lbl, short, tag in (('A', args.a, tag_a), ('B', args.b, tag_b)):
        if not tag:
            print('weapon %s (%s) is not in this map — pick another with --%s'
                  % (lbl, short, lbl.lower()))
            return 1

    for idx, tag, lbl in ((0, tag_a, 'A ' + args.a), (1, tag_b, 'B ' + args.b)):
        spec = {'primary': tag, 'profiles': [idx],
                'null_empty_slots': not args.keep_secondary}
        res = hp._apply_starting_equipment(m, GAME, reg, spec)
        ok = [r for r in res if r.get('ok') and not r.get('skip')]
        print('  profile %d <- %-28s %s' % (idx, lbl, 'written' if ok else 'FAILED'))
        for r in res:
            if not r.get('ok'):
                print('      %s' % r.get('reason'))
    m.save()

    print()
    print('wrote %s' % target)
    if not args.in_place:
        print('copy it over %s when you want to play it' % os.path.basename(real))
    print()
    print('Start two-player co-op and read what each player HOLDS on the first frame:')
    print('  P1 %-22s P2 %-22s -> PER-PLAYER profiles' % (args.a, args.b))
    print('  P1 %-22s P2 %-22s -> SHARED profile' % (args.a, args.a))
    return 0


if __name__ == '__main__':
    sys.exit(main())
