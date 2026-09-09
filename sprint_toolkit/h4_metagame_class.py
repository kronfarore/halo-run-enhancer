"""Who Halo 4 itself calls a Hero: char `Campaign Metagame Bucket / Class`.

The authoritative test, on the user's rule -- not a guess from the name. The block is
at 0x270 (esz 8) in the Halo4 char plugin; `Type` is the species enum at +0x1, `Class`
the tier enum at +0x2, and `Point Count` the metagame score at +0x4.

    Class: 0 Infantry, 1 Leader, 2 HERO, 3 Specialist,
           4 Light Vehicle, 5 Heavy Vehicle, 6 Giant Vehicle, 7 Standard Vehicle
"""
import collections
import os
import struct
import sys
import xml.etree.ElementTree as ET

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
r = ET.parse(os.path.join(P, 'Halo4', 'char.xml')).getroot()
MB = [c for c in r if c.tag.lower() == 'tagblock'
      and c.get('name') == 'Campaign Metagame Bucket'][0]
OFF = int(MB.get('offset'), 16)
SZ = int(MB.get('elementSize'), 16)
F = {}
for x in MB:
    if x.get('name'):
        F.setdefault(x.get('name'), int(x.get('offset'), 16))


def opts(name):
    for x in MB:
        if x.get('name') == name:
            out = []
            for o in x:
                v = o.get('name') or (o.text or '').strip()
                if v:
                    out.append(v)
            return out
    return []


TYPES = opts('Type')
CLASSES = opts('Class')
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)
pc = reg.get('char')
seen = {}
for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    for t in m.tags:
        n = t['name'] or ''
        if t['class'] != 'char' or t['base'] is None or n in seen:
            continue
        cnt = m.i32(t['base'] + OFF)
        if cnt <= 0:
            seen[n] = None
            continue
        e = m.data2off(m.u32(t['base'] + OFF + 4))
        ty = struct.unpack_from('<B', m.data, e + F['Type'])[0]
        cl = struct.unpack_from('<B', m.data, e + F['Class'])[0]
        pts = struct.unpack_from('<h', m.data, e + F['Point Count'])[0]
        # vitality, difficulty-prefixed in Halo 4
        nb = m.read_tag_field(t['base'], 'Normal Body Vitality', pc,
                              'Vitality Properties', 0)
        ns = m.read_tag_field(t['base'], 'Normal Shield Vitality', pc,
                              'Vitality Properties', 0)
        seen[n] = (ty, cl, pts, nb, ns, mid)

by = collections.defaultdict(list)
noblock = []
for n, v in seen.items():
    if v is None:
        noblock.append(n)
        continue
    by[v[1]].append((n, v))
for cl in sorted(by):
    label = CLASSES[cl] if cl < len(CLASSES) else '?%d' % cl
    print('=== Class %d = %s   (%d tag(s))' % (cl, label, len(by[cl])))
    for n, (ty, _c, pts, nb, ns, mid) in sorted(by[cl]):
        tname = TYPES[ty] if ty < len(TYPES) else '?%d' % ty
        vit = ('body %s / shield %s' % (nb, ns)) if nb is not None else 'no vitality block'
        print('   %-56s %-12s pts=%-4d %s' % (n.rsplit(SEP, 1)[-1][:56], tname, pts, vit))
    print()
print('char tags with NO Campaign Metagame Bucket at all: %d' % len(noblock))
for n in sorted(noblock)[:12]:
    print('   %s' % n.rsplit(SEP, 1)[-1])
