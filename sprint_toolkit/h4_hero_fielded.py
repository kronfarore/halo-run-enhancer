"""Which Halo 4 heroes are FIELDED -- using h4_census's own squad constants.

The first attempt hand-rolled the offsets and read the character index at +0x4 of every
sub-block. That is wrong twice over: a Spawn Point carries it at +0x2E, and a Cell
reaches it through a nested 8-byte sub-block at +0x0C. Those constants already exist in
h4_census (SPAWN_FIELDS, CELL_SUB, CELL_SUB_INDEX) and are what produced the shipped
mission lists, so they are the ones to trust.
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

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
HEROES = ['storm_elite_general', 'storm_grunt_ultra', 'storm_jackal_sniper',
          'storm_jackal_ranger', 'storm_jackal_ranger_shield',
          'storm_knight_commander',
          # controls: an ordinary variant that certainly IS fielded, and a Leader
          'storm_elite', 'storm_knight', 'storm_elite_zealot']
r = ET.parse(os.path.join(P, 'Halo4MCC', 'scnr.xml')).getroot()
SQ = next(c for c in r if c.tag.lower() == 'tagblock' and c.get('name') == 'Squads')
CP = next(c for c in r if c.tag.lower() == 'tagblock'
          and c.get('name') == 'Character Palette')
SQO, SQS = int(SQ.get('offset'), 16), int(SQ.get('elementSize'), 16)
CPO, CPS = int(CP.get('offset'), 16), int(CP.get('elementSize'), 16)
fielded = collections.defaultdict(collections.Counter)
palette = collections.defaultdict(set)


def at(m, base, off):
    """(array file offset, count) for a reflexive at base+off."""
    cnt = m.i32(base + off)
    if cnt <= 0:
        return 0, 0
    return m.data2off(m.u32(base + off + 4)), cnt


for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    idx = {t['index']: t for t in m.tags}
    got = m.find_tags('scnr', '*')
    if not got:
        continue
    base = got[0][1]
    pe, npal = at(m, base, CPO)
    slot = {}
    for i in range(npal):
        d = struct.unpack_from('<I', m.data, pe + i * CPS + 0xC)[0]
        tt = idx.get(d & 0xFFFF)
        leaf = (tt['name'] or '').rsplit(SEP, 1)[-1] if tt else ''
        if leaf in HEROES:
            slot[i] = leaf
            palette[leaf].add(mid)
    if not slot:
        continue
    se, nsq = at(m, base, SQO)
    for s in range(nsq):
        sb = se + s * SQS
        sp, spn = at(m, sb, hc.SPAWN_POINTS[0])
        for j in range(spn):
            v = m.i16(sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character'])
            if v in slot:
                fielded[slot[v]][mid] += 1
        for co, csize in hc.CELL_BLOCKS:
            ca, cn = at(m, sb, co)
            for j in range(cn):
                bo, bsize = hc.CELL_SUB['character']
                ba, bn = at(m, ca + j * csize, bo)
                for k in range(bn):
                    v = m.i16(ba + k * bsize + hc.CELL_SUB_INDEX)
                    if v in slot:
                        fielded[slot[v]][mid] += 1
print('%-30s %-30s %s' % ('character', 'in palette on', 'FIELDED by squads on'))
for h in HEROES:
    pal = sorted(palette.get(h, ()))
    f = fielded.get(h)
    fl = ', '.join('%s x%d' % (k, v) for k, v in sorted(f.items())) if f else 'NOWHERE'
    print('   %-27s %-30s %s' % (h, ('%d map(s)' % len(pal)) if pal else '-', fl))
