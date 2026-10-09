r"""Every field of any Halo 3 (H3EK) tag, by name, from `tool export-tag-to-xml` (cached by path in
out\h3_export, h3_weapon_values.export) -- for the values h3_weapon_values does not print.

Written for the Brute Shot (2026-10-09): its damage is the grenade's DETONATION damage effect
(h3_weapon_values prints None), its detonation timer / minimum velocity / material responses
decide how it bursts. A projectile gets a short summary (damage refs, detonation, flight,
responses); any other tag lists every `<field name value>` (filter with --grep).

    python h3_tag_fields.py objects\weapons\support_low\brute_shot\projectiles\grenade\grenade.projectile
    python h3_tag_fields.py objects\weapons\support_low\brute_shot\damage_effects\shot_grenade_explosion.damage_effect
    python h3_tag_fields.py objects\weapons\support_high\spartan_laser\spartan_laser.weapon --grep charg
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from h3_weapon_values import export, field  # noqa: E402

PROJECTILE = ('detonation damage', 'impact damage', 'attached detonation damage',
              'super detonation damage', 'detonation effect (airborne)', 'detonation effect (ground)',
              'detonation timer starts', 'timer', 'arming time', 'minimum velocity', 'maximum range',
              'bounce maximum range', 'initial velocity', 'final velocity', 'acceleration range',
              'air gravity scale', 'water gravity scale', 'air damage range', 'danger radius')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tags', nargs='+', help='H3EK tag paths WITH extension')
    ap.add_argument('--grep', help='only fields whose name holds this text (case-insensitive)')
    ap.add_argument('--all', action='store_true', help='a projectile: every field, not the summary')
    a = ap.parse_args()
    for p in a.tags:
        t = export(p)
        print(p)
        if t is None:
            print('  ABSENT')
            continue
        if p.endswith('.projectile') and not a.all and not a.grep:
            for n in PROJECTILE:
                print('  %-30s %s' % (n, field(t, n)))
            print('  default responses   ', re.findall(r'<field name="default response" value="([^"]*)"', t))
            print('  potential responses ', re.findall(r'<field name="potential response" value="([^"]*)"', t))
            print('  chance fractions    ', re.findall(r'<field name="chance fraction" value="([^"]*)"', t))
            continue
        for m in re.finditer(r'<field name="([^"]*)" value="([^"]*)"', t):
            if a.grep and a.grep.lower() not in m.group(1).lower():
                continue
            print('  %-40s %s' % m.groups())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
