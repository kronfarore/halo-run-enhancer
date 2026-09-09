"""Make the grow test easy to find: turn Shutdown's ordinary Knights into Knight Rangers.

The Knight Ranger is the subject because it owns no Vitality Properties -- reaching it
needs the grow -- and it is already at 1 body / 0 shield. The problem was only that its
12 spawns are hard to stumble on.

So repoint the CHARACTER index of every ordinary-Knight spawn (palette slot 1) to the
Ranger (slot 5). 19 entries. Every regular Knight on the level then dies to one hit.

Only Knight -> Knight becomes a swap. Crawlers and Watchers are left alone deliberately:
they are much smaller and spawn in vents and wall niches, so dropping a Knight-sized
biped into one of those risks it spawning inside geometry, which would look like a
failure of the grow when it is really a placement problem.

Controls that stay untouched, both fielded on this map and both owning their own
vitality: storm_knight_commander (5 spawns, 90/110) and storm_knight_battlewagon
(10 spawns, 90/110). If converted Knights pop and those two do not, the grow works.
"""
import os
import struct
import sys
import xml.etree.ElementTree as ET

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import map_vault as V
import h4_census as hc

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
FROM_LEAF, TO_LEAF = 'storm_knight', 'storm_knight_ranger'
APPLY = '--apply' in sys.argv
live = os.path.join(hc.MAPS, 'm70_liftoff.map')
if not os.path.exists(V.baseline_for('Halo 4', live)):
    raise SystemExit('refusing to edit placements with no baseline')
rs = ET.parse(os.path.join(P, 'Halo4MCC', 'scnr.xml')).getroot()
SQ = next(c for c in rs if c.tag.lower() == 'tagblock' and c.get('name') == 'Squads')
CP = next(c for c in rs if c.tag.lower() == 'tagblock'
          and c.get('name') == 'Character Palette')
SQO, SQS = int(SQ.get('offset'), 16), int(SQ.get('elementSize'), 16)
CPO, CPS = int(CP.get('offset'), 16), int(CP.get('elementSize'), 16)


def at(m, b, o):
    c = m.i32(b + o)
    return (m.data2off(m.u32(b + o + 4)), c) if c > 0 else (0, 0)


m = hp.open_map(live, 'Halo 4')
idx = {t['index']: t for t in m.tags}
base = m.find_tags('scnr', '*')[0][1]
pe, npal = at(m, base, CPO)
slot = {}
for i in range(npal):
    d = struct.unpack_from('<I', m.data, pe + i * CPS + 0xC)[0]
    tt = idx.get(d & 0xFFFF)
    slot[(tt['name'] or '').rsplit(SEP, 1)[-1] if tt else '?'] = i
src, dst = slot.get(FROM_LEAF), slot.get(TO_LEAF)
print('palette: %s = slot %s ; %s = slot %s' % (FROM_LEAF, src, TO_LEAF, dst))
if src is None or dst is None:
    raise SystemExit('both characters must already be in the palette')
se, nsq = at(m, base, SQO)
hits = []
for s in range(nsq):
    sb = se + s * SQS
    sp, spn = at(m, sb, hc.SPAWN_POINTS[0])
    for j in range(spn):
        e = sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character']
        if m.i16(e) == src:
            hits.append((s, e))
print('ordinary-Knight spawn entries to convert: %d (squads %s)'
      % (len(hits), sorted({s for s, _e in hits})))
if not APPLY:
    print('(report only -- pass --apply)')
    raise SystemExit
for _s, e in hits:
    struct.pack_into('<h', m.data, e, dst)
m.save()
del m
m2 = hp.open_map(live, 'Halo 4')
base2 = m2.find_tags('scnr', '*')[0][1]
se2, nsq2 = at(m2, base2, SQO)
left = conv = 0
for s in range(nsq2):
    sb = se2 + s * SQS
    sp, spn = at(m2, sb, hc.SPAWN_POINTS[0])
    for j in range(spn):
        v = m2.i16(sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character'])
        if v == src:
            left += 1
        elif v == dst:
            conv += 1
print('after save: %d ordinary Knight spawns left, %d Knight Ranger spawns'
      % (left, conv))
print('tags: %d ; checksum reproduces: %s'
      % (len(m2.tags), m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))
