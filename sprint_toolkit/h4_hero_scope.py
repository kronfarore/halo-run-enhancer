"""Per-hero block ownership and the ancestor a `grow` would seed from.

A hero card needs `init_defaults: {tag, block, grow: true}` only where the hero does NOT
define that block itself -- a source-less grow then seeds it from the tag's nearest
populated ANCESTOR, which is what halo_patch.seed_ancestor picks. So this reports, per
family: every variant, its declared metagame tier, which of the card-relevant blocks it
owns, and its Parent Character.

Card -> block:  Body/Shield Vitality, Body/Shield Recharge -> Vitality Properties
                Melee Behavior -> Charge Properties
                Grenade Chance -> Grenades Properties
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
import tagrefs

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
r = ET.parse(os.path.join(P, 'Halo4', 'char.xml')).getroot()
BLK = {}
for c in r:
    if c.tag.lower() == 'tagblock' and c.get('name') in (
            'Vitality Properties', 'Charge Properties', 'Grenades Properties'):
        BLK[c.get('name')] = int(c.get('offset'), 16)
MB = [c for c in r if c.tag.lower() == 'tagblock'
      and c.get('name') == 'Campaign Metagame Bucket'][0]
MBO = int(MB.get('offset'), 16)
MBF = {}
for x in MB:
    if x.get('name'):
        MBF.setdefault(x.get('name'), int(x.get('offset'), 16))
CLASSES = []
for x in MB:
    if x.get('name') == 'Class':
        CLASSES = [o.get('name') or (o.text or '').strip() for o in x
                   if (o.get('name') or (o.text or '').strip())]
SPEC = tagrefs._spec(P, 'Halo4', 'char')
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)
pc = reg.get('char')
FAMILIES = ('storm_knight', 'storm_jackal', 'storm_elite', 'storm_grunt')
info = {}
for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    idx = {t['index']: t for t in m.tags}
    for t in m.tags:
        n = t['name'] or ''
        if t['class'] != 'char' or t['base'] is None or n in info:
            continue
        leaf = n.rsplit(SEP, 1)[-1]
        if not any(leaf.startswith(f) for f in FAMILIES):
            continue
        own = [b for b, o in BLK.items() if m.i32(t['base'] + o) > 0]
        cl = None
        if m.i32(t['base'] + MBO) > 0:
            e = m.data2off(m.u32(t['base'] + MBO + 4))
            ci = struct.unpack_from('<B', m.data, e + MBF['Class'])[0]
            cl = CLASSES[ci] if ci < len(CLASSES) else str(ci)
        parent = None
        for fp, d in tagrefs.refs_of(m, t['base'], SPEC):
            if fp == 'Parent Character':
                tt = idx.get(d & 0xFFFF)
                if tt and tt['name']:
                    parent = tt['name'].rsplit(SEP, 1)[-1]
        nb = m.read_tag_field(t['base'], 'Normal Body Vitality', pc,
                              'Vitality Properties', 0)
        ns = m.read_tag_field(t['base'], 'Normal Shield Vitality', pc,
                              'Vitality Properties', 0)
        info[n] = (leaf, cl, own, parent, nb, ns, mid)
for fam in FAMILIES:
    rows = sorted(v for k, v in info.items() if v[0].startswith(fam))
    if not rows:
        continue
    print('=== %s' % fam)
    for leaf, cl, own, parent, nb, ns, mid in rows:
        star = ' <<< HERO' if cl == 'Hero' else ''
        print('   %-34s %-11s parent=%-22s owns: %-46s %s%s'
              % (leaf, cl or '-', parent or '-', ', '.join(own) or 'NOTHING',
                 ('vit %s/%s' % (nb, ns)) if nb is not None else '', star))
    print()
