r"""What does a SHIPPED Halo 4 tag reference, and which H4EK tag is it really? Read-only.

The C2 Suppressor (2026-10-15): H4EK's _default_metal.material names a colour map that ships nowhere;
the material the game draws (m020.map) named the SHATTER control map instead, and its parameter floats
matched H4EK's _shatter_metal.material exactly. The H4EK .material can differ from the shipped one --
read the cache.

Tag references: every tag-reference struct in the tag's data window (group magic @0, datum @0xC whose
low 16 bits index the tag table, the class matching that tag's). `--match <H4EK .material>`: the
material's real / colour parameter values found as floats in the same window (a parameter set matching
it is the material the cache holds). The window runs past the tag's own data into its neighbours'
(the cache packs tags back to back) -- read the first block of references.

    python h4_cache_refs.py m020 "mat " *storm_forerunner_smg_default_metal
    python h4_cache_refs.py m020 "mat " *storm_forerunner_smg_default_metal --window 0x370 ^
        --match objects\weapons\rifle\storm_forerunner_smg\shaders\storm_forerunner_smg_shatter\storm_forerunner_smg_shatter_metal.material
"""
import argparse
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map', help='a halo4\\maps name without .map (m020, m10_crash, ...)')
    ap.add_argument('group', help='tag group, 4 chars ("mat ", bitm, weap ...)')
    ap.add_argument('pattern', help='tag path pattern (find_tags)')
    ap.add_argument('--window', type=lambda s: int(s, 0), default=0x1000)
    ap.add_argument('--match', help='an H4EK .material: find its parameter values in the window')
    a = ap.parse_args()
    import halo4_map
    m = halo4_map.Halo4Map(os.path.join(TOOL, '..', 'halo4', 'maps', a.map + '.map'))
    for name, base in m.find_tags(a.group, a.pattern):
        print('==', name, hex(base))
        with open(m.path, 'rb') as f:
            f.seek(base)
            d = f.read(a.window)
        for o in range(0, len(d) - 16, 4):
            g = d[o:o + 4]
            if not all(32 <= c < 127 for c in g):
                continue
            datum = struct.unpack_from('<I', d, o + 12)[0]
            t = m.tag(datum & 0xFFFF)
            if t is None or t.get('class') not in (g[::-1].decode('latin-1'), g.decode('latin-1')):
                continue
            print('  +0x%04x %s %s' % (o, t.get('class'), t.get('name')))
        if a.match:
            import h4_tags
            s = open(h4_tags.export_xml(a.match), encoding='utf-8', errors='replace').read()
            vals = {}
            for blk in re.findall(r'<field name="parameter name".*?(?=<field name="parameter name"|\Z)', s, re.S):
                gd = dict(re.findall(r'<field name="([^"]*)" value="([^"]*)"', blk))
                if gd.get('parameter type') == 'real':
                    vals[gd['parameter name']] = [float(gd.get('real', 0))]
                elif gd.get('parameter type') in ('color', 'argb color'):
                    vals[gd['parameter name']] = [float(x) for x in gd.get('color', '').split(',') if x]
            hit = 0
            for pname, vs in vals.items():
                for v in vs:
                    if v in (0.0, 1.0):
                        continue           # too common to tell anything
                    for o in range(0, len(d) - 4, 4):
                        if abs(struct.unpack_from('<f', d, o)[0] - v) < 2e-5:
                            print('  match +0x%04x %-28s %g' % (o, pname, v))
                            hit += 1
                            break
            print('  %d parameter value(s) of %s found' % (hit, a.match.rsplit('\\', 1)[-1]))


if __name__ == '__main__':
    main()
