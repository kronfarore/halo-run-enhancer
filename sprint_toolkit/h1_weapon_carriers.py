r"""Step 11's first question: which Halo 1 characters CARRY a weapon, and with what Weapon
Damage Modifier (the ARMED WDM RULE's base, actv +0xC4)?

Lists every actor variant in HCEEK whose ranged-combat weapon names the given tag, with
its unit, major variant and WDM. The Mauler (2026-10-09) found Halo 1's shotgun carriers
split -- Flood combat (0.15) vs Marines (0.6) -- so it pinned one donor (`donor_variant`).
The WDM is read from the tag file directly (big-endian, after the 64-byte header); the AR
carriers read 0.4, as the Spike Rifle recorded.

    python h1_weapon_carriers.py "weapons\shotgun\shotgun"
"""
import glob
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.actv import actv_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
WDM = 0xC4                                    # actor_variant Weapon Damage Modifier


def wdm(path):
    b = open(path, 'rb').read()
    return struct.unpack('>f', b[64 + WDM:64 + WDM + 4])[0]


def main(weapon):
    want = weapon.lower()
    found = 0
    for p in sorted(glob.glob(os.path.join(TAGS, 'characters', '**', '*.actor_variant'), recursive=True)):
        d = actv_def.build(filepath=p).data.tagdata
        if d.ranged_combat.weapon.filepath.lower() != want:
            continue
        found += 1
        rel = os.path.relpath(p, TAGS)[:-len('.actor_variant')]
        print('%-58s WDM %-5g unit %s  major %s' % (rel, round(wdm(p), 3), d.unit.filepath,
                                                   d.major_variant.filepath or '-'))
    print('%d carrier(s) of %s' % (found, weapon))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
