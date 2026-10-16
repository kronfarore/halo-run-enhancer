r"""A Halo 4 projectile at a glance, read-only (the Sticky Detonator, C8, 2026-10-16: step 4a for an
explosive whose damage lives in its DETONATION, which h3_weapon_values --kit h4 does not print -- the A7
lesson): the fuse (timer start, timer, arming, minimum velocity, max latch times), flight (range, velocity,
gravity) and each damage effect it names -- impact, detonation, attached -- with radius, AOE core, lower /
upper damage, group, category and acceleration. Exports through h4_tags (out\h4_export).

    python h4_projectile_summary.py objects\weapons\pistol\storm_sticky_detonator\projectiles\storm_sticky_detonator_grenade_pve.projectile
    python h4_projectile_summary.py objects\weapons\grenade\storm_plasma_grenade\storm_plasma_grenade.projectile ^
        objects\weapons\support_high\storm_rocket_launcher\projectiles\storm_rocket_launcher_rocket.projectile
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402

PROJ = ['detonation timer starts', 'timer', 'arming time', 'minimum velocity', 'maximum range',
        'max latch time to detonate', 'max latch time to arm', 'initial velocity', 'final velocity',
        'air gravity scale']
DAMAGE = ['radius', 'AOE core radius', 'damage lower bound', 'damage upper bound', 'general_damage',
          'category', 'instantaneous acceleration']
REFS = ['impact damage', 'detonation damage', 'attached detonation damage']


def fields(path, keys):
    t = open(path, encoding='utf-8', errors='replace').read()
    out = {}
    for k in keys:
        m = re.search(r'<field name="%s" value="([^"]*)"' % re.escape(k), t)
        if m:
            out[k] = m.group(1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('projectiles', nargs='+', help='H4EK tag paths (with .projectile)')
    a = ap.parse_args()
    for rel in a.projectiles:
        f = fields(h4_tags.export_xml(rel), PROJ + REFS)
        print('==', rel)
        for k in PROJ:
            if k in f:
                print('   %-28s %s' % (k, f[k]))
        for k in REFS:
            ref = f.get(k, '')
            if not ref or ref.startswith(','):
                print('   %-28s -' % k)
                continue
            d = fields(h4_tags.export_xml(ref.split(',')[0] + '.damage_effect'), DAMAGE)
            print('   %-28s %s' % (k, ref.split(',')[0].rsplit('\\', 1)[-1]))
            print('       ' + '  '.join('%s %s' % (x, d[x]) for x in DAMAGE if x in d))


if __name__ == '__main__':
    main()
