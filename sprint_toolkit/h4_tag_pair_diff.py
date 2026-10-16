r"""Two H4EK tags side by side, read-only (the Railgun, C7 2026-10-16: MP vs _pve -- C8 found they differ in the
projectile + damage only; the Railgun's also differ in the charge HOLD, the error, the magazine and attachments):
a unified diff of their XML exports (h4_tags, cached in out\h4_export), the tag id line left out. Run it on each
pair the weapon names: weapon, projectile, impact / detonation damage effects.

    python h4_tag_pair_diff.py <tag A> <tag B> [<tag A2> <tag B2> ...]
    python h4_tag_pair_diff.py objects\weapons\rifle\storm_rail_gun\storm_rail_gun.weapon ^
                               objects\weapons\rifle\storm_rail_gun\storm_rail_gun_pve.weapon
Paths under H4EK\tags WITH their extension.
"""
import difflib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402


def lines(rel):
    return open(h4_tags.export_xml('h4:' + rel), encoding='utf-8', errors='replace').read().splitlines()


def main(argv):
    if len(argv) < 2 or len(argv) % 2:
        raise SystemExit(__doc__)
    for a, b in zip(argv[::2], argv[1::2]):
        la, lb = lines(a), lines(b)
        print('===== %s  vs  %s' % (a, b))
        n = 0
        for l in difflib.unified_diff(la[2:], lb[2:], n=0, lineterm=''):
            if l.startswith(('---', '+++')):
                continue
            print('   ', l.strip()[:220])
            n += 1
        print('    (%s)' % ('identical' if not n else '%d diff line(s)' % n))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1:])
