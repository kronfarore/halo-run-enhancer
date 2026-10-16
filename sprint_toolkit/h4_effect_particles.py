r"""Every PARTICLE SYSTEM of Halo 4 effects (H4EK, read-only) -- the SOURCE half of closing check 10, THE
MUZZLE-FLASH RULE, for a Halo 4 port (h1_effect_particles.py is the Halo 1 half). Per particle system: its
location's MARKER, the particle tag, the camera mode (first / third person) and every emitter's `bounding
radius estimate` (wu) -- what a port's flash is sized and placed against; then the effect's other parts.
Written for the Scattershot (C5, 2026-10-15): sg_firing's first-person flashes are two muzzle_flash_large
(0.092 / 0.110 wu) + muzzle bits at primary_trigger, rings / glow / streak at the muzzle rim, sparkles on
the rails -- the C2 / C3 ports read the same numbers by hand.
    python h4_effect_particles.py "objects\weapons\rifle\storm_spread_gun\fx\firing\sg_firing.effect"
(paths under H4EK\tags, with the extension; several at once)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402


def systems(rel):
    s = io.open(h4_tags.export_xml('h4:' + rel), encoding='latin-1').read()
    loc_blk = s[s.find('<block name="locations"'):]
    loc_blk = loc_blk[:loc_blk.find('\n    </block>')]
    locs = re.findall(r'name="marker name" value="([^"]*)"', loc_blk)
    out = []
    for el in re.split(r'<block name="particle systems"', s)[1:]:
        for ps in re.split(r'\n                <element index="\d+" name="', el)[1:]:
            d, radii = {}, []
            for k, v in re.findall(r'name="([^"]*)" value="([^"]*)"', ps):
                if k == 'bounding radius estimate':
                    radii.append(float(v))
                d.setdefault(k, v)
            li = d.get('location', ',-1').split(',')[-1]
            loc = locs[int(li)] if li.lstrip('-').isdigit() and 0 <= int(li) < len(locs) else li
            out.append((loc, d.get('particle', '?').split('\\')[-1], d.get('camera mode', '?'), radii))
    parts = [v for v in re.findall(r'<field name="type" value="([^"]*)" type="tag reference"/>', s)
             if v and not v.startswith(',')]
    return locs, out, parts


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    for rel in argv:
        locs, sy, parts = systems(rel)
        print('== %s   locations %s' % (rel, locs))
        for loc, part, cam, radii in sy:
            print('  %-18s %-40s %-22s r=%s' % (loc, part, cam, [round(r, 3) for r in radii]))
        for p in parts:
            print('  part', p.split('\\')[-1])


if __name__ == '__main__':
    main(sys.argv[1:])
