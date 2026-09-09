"""Would Halo 4 hero cards actually land, or write into inherited empty blocks?

Reach's hero tier (Elite General, Elite Zealot, Grunt Ultra, Jackal Sniper) has direct
Halo 4 counterparts, and Halo 4 adds its own (Knight Commander, Crawler Prime). But a
hero card is only worth writing if that char tag DEFINES the block it edits -- the
empty-block class from Halo 3 on is what made Brute Grenades a silent no-op.

For each candidate this reports, per property block, whether the tag has its own
elements and what the headline values are against the ordinary variant of the species.
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
import h4_wire_weapons as W

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
BLOCKS = ['Vitality Properties', 'Weapons Properties', 'Grenades Properties',
          'Charge Properties', 'Perception Properties', 'Firing Pattern Properties',
          'Engage Properties', 'Cover Properties', 'Retreat Properties']
CANDIDATES = [
    ('Elite Zealot', 'storm_elite_zealot', 'storm_elite'),
    ('Elite General', 'storm_elite_general', 'storm_elite'),
    ('Elite Officer', 'storm_elite_officer', 'storm_elite'),
    ('Grunt Ultra', 'storm_grunt_ultra', 'storm_grunt'),
    ('Jackal Sniper', 'storm_jackal_sniper', 'storm_jackal'),
    ('Jackal Major', 'storm_jackal_major', 'storm_jackal'),
    ('Knight Commander', 'storm_knight_commander', 'storm_knight'),
    ('Knight Ranger', 'storm_knight_ranger', 'storm_knight'),
    ('Crawler Prime', 'storm_pawn_prime', 'storm_pawn'),
    ('Didact (boss)', 'storm_didact', None),
]
r = ET.parse(os.path.join(P, 'Halo4', 'char.xml')).getroot()
OFF = {}
for c in r:
    if c.tag.lower() == 'tagblock' and c.get('name') in BLOCKS:
        OFF[c.get('name')] = int(c.get('offset'), 16)
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)
pc = reg.get('char')
found = {}
for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    for t in m.tags:
        n = t['name'] or ''
        if t['class'] != 'char' or t['base'] is None:
            continue
        leaf = n.rsplit(SEP, 1)[-1]
        if leaf in found:
            continue
        found[leaf] = (m, t['base'], mid)
print('%-18s %-28s %s' % ('candidate', 'tag', 'blocks it DEFINES'))
for label, leaf, base in CANDIDATES:
    if leaf not in found:
        print('   %-16s %-28s NOT PRESENT on any campaign map' % (label, leaf))
        continue
    m, off, mid = found[leaf]
    own = [b for b in BLOCKS if OFF.get(b) is not None and m.i32(off + OFF[b]) > 0]
    print('   %-16s %-28s [%s] %s' % (label, leaf, mid, ', '.join(own) or 'NONE -- inherits everything'))
    if 'Vitality Properties' in own:
        v = m.read_tag_field(off, 'Body Vitality', pc, 'Vitality Properties', 0)
        s = m.read_tag_field(off, 'Shield Vitality', pc, 'Vitality Properties', 0)
        line = '        Body %s / Shield %s' % (v, s)
        if base and base in found:
            mb, ob, _mid = found[base]
            bv = mb.read_tag_field(ob, 'Body Vitality', pc, 'Vitality Properties', 0)
            bs = mb.read_tag_field(ob, 'Shield Vitality', pc, 'Vitality Properties', 0)
            line += '   (ordinary %s: Body %s / Shield %s)' % (base, bv, bs)
        print(line)
