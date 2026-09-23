"""Give the player the SAW at the start of a10 (Halo 1 kit scenario tag), for the build.
The scenario tag is backed up to the scratchpad first; --restore puts it back.

    python saw_scenario.py            # back up, then set every starting profile's primary
    python saw_scenario.py --restore
"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.scnr import scnr_def

SCN = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags',
                   'levels', 'a10', 'a10.scenario')
BAK = os.path.join(HERE, 'a10.scenario.before_saw')
SAW = 'weapons' + os.sep + 'saw' + os.sep + 'saw'
SPAWN_PROFILES = ('player0_starting_profile', 'a10_coop_profile', 'player1_starting_profile')


def main():
    if '--restore' in sys.argv:
        shutil.copy2(BAK, SCN)
        print('restored', SCN)
        return
    if not os.path.exists(BAK):
        shutil.copy2(SCN, BAK)
        print('backed up to', BAK)
    t = scnr_def.build(filepath=SCN)
    profs = t.data.tagdata.player_starting_profiles.STEPTREE
    for i, p in enumerate(profs):
        print('profile %d: %r primary %s secondary %s' % (
            i, p.name, p.primary_weapon.filepath, p.secondary_weapon.filepath))
        # Only the spawn profiles: a10's others drive mechanisms (the sprint mod's
        # invisible weapon, the bridge pistol, a weapon insert) and must stay as they are.
        if p.name not in SPAWN_PROFILES:
            continue
        p.primary_weapon.filepath = SAW
        p.primary_rounds_loaded = 72
        p.primary_rounds_total = 216
    t.serialize(temp=False, backup=False)
    print('set the spawn profiles', SPAWN_PROFILES, 'to', SAW)


if __name__ == '__main__':
    main()
