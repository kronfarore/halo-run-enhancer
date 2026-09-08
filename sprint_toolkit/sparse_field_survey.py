"""Targeted Leading Fraction per weapon per game, plus the sparse-field outlier report.

Two jobs:
  1. What the Homing cards need: which games declare the field, and what each homing
     weapon's projectile holds, so the allow-lists and the note are measured.
  2. The rare fields the user asked about -- for each, every projectile that sets it
     and what makes one differ from the rest.
"""
import collections
import os
import sys
import xml.etree.ElementTree as ET

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
GAMES = [
    ('Halo 1', ['Halo1MCC', 'Halo1'], os.path.join(ROOT, 'halo1', 'maps'),
     ['b30', 'c10', 'c20', 'd20', 'a30']),
    ('Halo 2', ['Halo2MCC', 'Halo2'],
     os.path.join(ROOT, 'halo2', 'h2_maps_win64_dx11'),
     ['01a_tutorial', '03a_oldmombasa', '05a_deltaapproach', '08b_deltacontrol']),
    ('Halo 3', ['Halo3MCC', 'Halo3'], os.path.join(ROOT, 'halo3', 'maps'),
     ['010_jungle', '020_base', '030_outskirts', '070_waste', '100_citadel', '120_halo']),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'], os.path.join(ROOT, 'halo3odst', 'maps'),
     ['l200', 'l300']),
    ('Halo Reach', ['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
     ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']),
    ('Halo 4', ['Halo4MCC', 'Halo4'], hc.MAPS, [m for m, _t in hc.CAMPAIGN]),
]
SPARSE = [('Targeted Leading Fraction', None), ('Minimum Velocity', None),
          ('Arming Time', None), ('And Velocity', 'Material Response'),
          ('Chance Fraction', 'Material Response'),
          ('Super Detonation Time', None), ('Autoaim Leading Maximum Lead Time', None)]


def declares(sub, field):
    f = os.path.join(P, sub, 'proj.xml')
    if not os.path.exists(f):
        return None
    found = [False]

    def walk(n):
        for c in n:
            if c.get('name') == field and c.tag.lower() != 'tagblock':
                found[0] = True
            if c.tag.lower() == 'tagblock':
                walk(c)
    walk(ET.parse(f).getroot())
    return found[0]


print('=== which games DECLARE each field')
for f, _b in SPARSE:
    row = []
    for game, subs, _md, _mp in GAMES:
        d = declares(subs[0], f)
        row.append('%s:%s' % (game.replace('Halo ', 'H').replace(': ODST', 'ODST'),
                              '-' if d is None else ('yes' if d else 'no')))
    print('   %-38s %s' % (f, '  '.join(row)))
print()

for game, subs, mapdir, maps in GAMES:
    pl = hp.PluginRegistry(P, subs).get('proj')
    if pl is None:
        print('=== %s -- no proj plugin' % game)
        continue
    vals = collections.defaultdict(dict)     # field -> {proj leaf: value}
    missing = []
    for mid in maps:
        fp = os.path.join(mapdir, mid + '.map')
        if not os.path.exists(fp):
            missing.append(mid)
            continue
        m = hp.open_map(fp, game)
        for tp, off in m.find_tags('proj', '*'):
            for f, b in SPARSE:
                leaf = tp.rsplit(SEP, 1)[-1]
                if leaf in vals[f]:
                    continue
                v = m.read_tag_field(off, f, pl, b, 0)
                if v not in (None, 0, 0.0):
                    vals[f][leaf] = v
    print('=' * 78)
    print('%s%s' % (game, '   (missing maps: %s)' % ', '.join(missing) if missing else ''))
    for f, b in SPARSE:
        d = vals[f]
        if not d:
            print('   %-38s --' % f)
            continue
        byval = collections.defaultdict(list)
        for k, v in d.items():
            byval[round(v, 4) if isinstance(v, float) else v].append(k)
        common = max(byval.items(), key=lambda kv: len(kv[1]))
        print('   %-38s %d projectile(s)' % (f, len(d)))
        for val in sorted(byval, key=lambda x: (-len(byval[x]), x)):
            names = sorted(byval[val])
            tag = '  <-- most common' if val == common[0] and len(byval) > 1 else ''
            print('        %-10s x%-3d %s%s'
                  % (val, len(names), ', '.join(n[:34] for n in names[:6])
                     + (' ...' if len(names) > 6 else ''), tag))
