r"""Halo 2 SAW port: point the built maps' saw_bullet at 'bullet_slow' (the AR's group).

The port's loose tag (H2EK tags\objects\weapons\rifle\saw\damage_effects\saw_bullet) was
corrected to bullet_slow on 2026-10-05 09:31 -- after the twelve campaign maps had been
built (07:07-08:03 that morning), so they still carry the gpmg donor's 'bullet_vehicle'.
A rebuild picks the tag up; until then this writes the same 4-byte string id into the
built maps, exactly what every Halo 2 patch already does (halo_patch._fix_h2_saw_group,
which stays as the safety net). Idempotent.

01b_spacestation is never touched (reserved for another test).

    python h2_saw_group_fix.py [--dry] <maps folder> [<maps folder> ...]
"""
import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import halo_patch as hp      # noqa: E402

SKIP = ('01b_spacestation',)


def fix(path, dry=False):
    m = hp.open_map(path, 'Halo 2')
    res = hp._fix_h2_saw_group(m, 'Halo 2')
    if not res:
        return 'no SAW port'
    r = res[0]
    if not r.get('ok'):
        return 'FAILED: %s' % r.get('reason')
    if r.get('skip'):
        return r.get('reason')
    if not dry:
        m.save(path)
    return '%s -> bullet_slow%s' % (r.get('old'), ' (dry run)' if dry else '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folders', nargs='+')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    for folder in a.folders:
        for path in sorted(glob.glob(os.path.join(folder, '*.map'))):
            name = os.path.splitext(os.path.basename(path))[0]
            if name in SKIP or not name[:2].isdigit():
                continue
            print('%-60s %s' % (path, fix(path, a.dry)), flush=True)


if __name__ == '__main__':
    main()
