"""Give the player the SAW at the start of a Halo 1 kit scenario, for the build.
The scenario tag is backed up to the scratchpad first; --restore puts it back.

WHICH PROFILES, and why this refuses to guess. a10 has six starting profiles and only
three of them are spawns: the others drive MECHANISMS -- the sprint mod's invisible
weapon, the bridge pistol, a weapon insert -- and handing one of those the SAW breaks
the level rather than arming the player. That list cannot be derived from the tag, so it
is recorded per map here, and a map with no entry is refused with its profiles printed
rather than being given a plausible default.

    python saw_scenario.py                        # a10
    python saw_scenario.py --map b30
    python saw_scenario.py --map b30 --profiles player0_starting_profile
    python saw_scenario.py --map a10 --restore
"""
import argparse, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.scnr import scnr_def

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
SAW = 'weapons' + os.sep + 'saw' + os.sep + 'saw'
MAGAZINE, TOTAL = 72, 216

#: map -> the profiles that are actually player spawns. See the note above.
PROFILES = {
    'a10': ('player0_starting_profile', 'a10_coop_profile', 'player1_starting_profile'),
}


def scenario(name):
    return os.path.join(HCEEK, 'tags', 'levels', name, name + '.scenario')


def backup(name):
    return os.path.join(HERE, name + '.scenario.before_saw')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='a10')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--profiles', help='comma separated, for a map not in PROFILES')
    ap.add_argument('--all-profiles', action='store_true',
                    help='every profile -- only safe on a map whose profiles are all spawns')
    a = ap.parse_args()

    scn, bak = scenario(a.map), backup(a.map)
    if a.restore:
        if not os.path.exists(bak):
            raise SystemExit('nothing to restore: %s does not exist' % bak)
        shutil.copy2(bak, scn)
        print('restored', scn)
        return
    if not os.path.exists(scn):
        raise SystemExit('no such scenario: %s' % scn)

    t = scnr_def.build(filepath=scn)
    profs = t.data.tagdata.player_starting_profiles.STEPTREE
    names = [p.name for p in profs]

    if a.profiles:
        want = tuple(s.strip() for s in a.profiles.split(',') if s.strip())
        missing = [w for w in want if w not in names]
        if missing:
            raise SystemExit('%s has no profile called %s.\nIts profiles are:\n    %s'
                             % (a.map, ', '.join(missing), '\n    '.join(names)))
    elif a.all_profiles:
        want = tuple(names)
    elif a.map in PROFILES:
        want = PROFILES[a.map]
    else:
        raise SystemExit(
            'which of %s profiles are player spawns is not recorded, and guessing breaks\n'
            'levels -- a10 has three that drive mechanisms rather than arming anyone.\n\n'
            '%s has:\n    %s\n\n'
            'Name them with --profiles a,b or take all of them with --all-profiles, and\n'
            'add the answer to PROFILES in this file so it is only decided once.'
            % (a.map, a.map, '\n    '.join(names)))

    # AFTER the refusal above, so a map this cannot act on does not leave a backup
    # behind -- one that would later look like a saved state and is only a copy.
    if not os.path.exists(bak):
        shutil.copy2(scn, bak)
        print('backed up to', bak)

    for i, p in enumerate(profs):
        mark = '  <-- SAW' if p.name in want else ''
        print('profile %d: %r primary %s secondary %s%s'
              % (i, p.name, p.primary_weapon.filepath, p.secondary_weapon.filepath, mark))
        if p.name not in want:
            continue
        p.primary_weapon.filepath = SAW
        p.primary_rounds_loaded = MAGAZINE
        p.primary_rounds_total = TOTAL
    t.serialize(temp=False, backup=False)
    print('set %d profile(s) of %s to %s' % (len(want), a.map, SAW))


if __name__ == '__main__':
    main()
