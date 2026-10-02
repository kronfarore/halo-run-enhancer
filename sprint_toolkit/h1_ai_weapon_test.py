r"""Build a Halo 1 test map for "teaching" enemies another weapon (2026-10-02).

Halo 1's AI weapon is decided by the actor variant (actv) alone: its Weapon tagref at
+0x64. Squads and start locations only choose WHICH actv spawns, and the biped's own
Weapons block is a default the actv overrides. Each actv also links a Major Variant
(+0x24) it promotes into, which carries its own weapon -- so minor and major change
together. See memory halo1-enemy-weapon-teaching.

The test (b30, Grunts appear at once):
  grunt minor/major plasma pistol -> plasma rifle    the Grunt antr HAS 'pr' animations
  grunt minor/major needler       -> assault rifle   the Grunt antr has NO 'ar' animations
Only the weapon tagref changes; burst/range fields stay the old weapon's on purpose, so
the first boot isolates "does the weapon change at all" and "what does a missing
animation set do".

The tagref is copied whole (16 bytes) from an actv on the same map that already carries
the target weapon, so it is a reference the map provably resolves.

Writes a COPY; never touches the live map:
    python h1_ai_weapon_test.py                 -> halo1\maps\b30_aiweapon_test.map
    python h1_ai_weapon_test.py --check <map>   -> print what each grunt actv carries
Deploy / restore with h1_ai_weapon_test.cmd.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch as hp  # noqa: E402

MAPS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'halo1', 'maps')
WEAPON_REF, MAJOR_REF = 0x64, 0x24

G = 'characters\\grunt\\'
EDITS = [
    # (actv to edit, actv whose weapon ref is copied)
    (G + 'grunt minor plasma pistol', 'characters\\elite\\elite minor\\elite minor plasma rifle'),
    (G + 'grunt major plasma pistol', 'characters\\elite\\elite minor\\elite minor plasma rifle'),
    (G + 'grunt minor needler', 'characters\\marine_armored\\marine_armored assault rifle'),
    (G + 'grunt major needler', 'characters\\marine_armored\\marine_armored assault rifle'),
]


def weapon_of(m, base):
    return hp._tag_name_by_id(m, m.u32(base + WEAPON_REF + 0xC))


def report(m):
    tags = dict(m.find_tags('actv', '*'))
    for name, _src in EDITS:
        b = tags.get(name)
        if b is None:
            print('  %-28s MISSING' % name.split('\\')[-1])
            continue
        major = hp._tag_name_by_id(m, m.u32(b + MAJOR_REF + 0xC))
        print('  %-28s weapon=%-45s major=%s' % (name.split('\\')[-1], weapon_of(m, b),
                                                  (major or '-').split('\\')[-1]))


def build(src, dst):
    shutil.copyfile(src, dst)
    m = hp.open_map(dst, 'Halo 1')
    tags = dict(m.find_tags('actv', '*'))
    print('before:')
    report(m)
    for name, donor in EDITS:
        b, d = tags[name], tags[donor]
        m.data[b + WEAPON_REF:b + WEAPON_REF + 16] = m.data[d + WEAPON_REF:d + WEAPON_REF + 16]
    m.save(dst)
    m = hp.open_map(dst, 'Halo 1')
    print('after (re-read from the saved copy):')
    report(m)
    print('written:', dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', metavar='MAP')
    ap.add_argument('--src', default=os.path.join(MAPS, 'b30.map'))
    ap.add_argument('--dst', default=os.path.join(MAPS, 'b30_aiweapon_test.map'))
    a = ap.parse_args()
    if a.check:
        report(hp.open_map(a.check, 'Halo 1'))
    else:
        build(a.src, a.dst)


if __name__ == '__main__':
    main()
