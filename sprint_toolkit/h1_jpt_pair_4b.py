r"""Step 4b BY HAND for a damage effect port_field_audit does not read (the Railgun, C7 close-out 2026-10-16: the
slug's ATTACHED hit tag -- the audit's field_audit config names one damage effect a port), read-only: the source
pair (the port's Halo 4 damage effect vs its yardstick's) field by field where they DIFFER, beside the Halo 1 port
tag and its donor. Then the usual rule per line: no card -> the ratio outright; a zero on one side -> the source
value; an enum / flags -> decide by name.

    python h1_jpt_pair_4b.py <H4 port .damage_effect> <H4 yardstick .damage_effect> <H1 port tag> <H1 donor tag>
    python h1_jpt_pair_4b.py ^
        objects\weapons\rifle\storm_rail_gun\projectiles\damage_effects\storm_rail_gun_bolt_impact_pve.damage_effect ^
        objects\weapons\support_high\storm_rocket_launcher\projectiles\damage_effects\storm_rocket_launcher_rocket_impact.damage_effect ^
        "weapons\railgun\slug impact.damage_effect" "weapons\rocket launcher\explosion.damage_effect"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402
import port_field_audit as A  # noqa: E402

TYPES = '(?:real|real bounds|real fraction|angle|long integer|short integer|short enum|string id|long flags)'


def h4_fields(rel):
    s = open(h4_tags.export_xml('h4:' + rel), encoding='utf-8', errors='replace').read()
    return {m.group(1): m.group(2)
            for m in re.finditer(r'<field name="([^"]+)" value="([^"]*)" type="%s"' % TYPES, s)}


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    fa, fb = h4_fields(argv[0]), h4_fields(argv[1])
    h1, h1d = A.flatten('HCEEK', argv[2]), A.flatten('HCEEK', argv[3])
    print('%-38s %-16s %-16s | %-26s %s' % ('field (H4 name)', 'H4 port', 'H4 yardstick', 'H1 port', 'H1 donor'))
    for k in sorted(set(fa) | set(fb)):
        if fa.get(k) == fb.get(k):
            continue
        hk = [x for x in h1 if x.split('/')[-1].replace('_', ' ') == k.lower()]
        port = h1[hk[0]][1] if hk else '- (no Halo 1 field)'
        donor = h1d.get(hk[0], ('', '-'))[1] if hk else ''
        print('%-38s %-16s %-16s | %-26s %s' % (k, fa.get(k), fb.get(k), port, donor))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1:])
