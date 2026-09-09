"""Rebuild Shutdown's test from the baseline, using CRAWLERS instead of Knights.

Knights are the rarest Promethean class -- 19 spawns -- so converting them made a test
you have to hunt for. Crawlers are the most numerous at 76.

`storm_pawn_sniper` is the right subject for the same reason the Knight Ranger was: it
owns NO Vitality Properties and inherits storm_pawn's, so reaching it REQUIRES the grow.
And it is a Crawler, so putting it where a Crawler already spawns carries none of the
body-size risk that made me refuse Crawler -> Knight.

Starts from the baseline so the map carries only what this test needs:
  1. grow storm_pawn_sniper's Vitality Properties, set 1 body / 0 shield;
  2. repoint all 76 storm_pawn spawns to storm_pawn_sniper;
  3. re-apply the Knight Commander melee grow, kept as a second, independent data point.

Every Crawler on the level then dies to a single hit. Controls that must NOT change:
storm_pawn_prime (owns its vitality, 80), storm_knight 70/80, storm_knight_commander
90/110, and every Covenant character.
"""
import os
import shutil
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
CH_DIR = 'objects' + SEP + 'characters' + SEP
SUBJECT = CH_DIR + 'storm_pawn' + SEP + 'ai' + SEP + 'storm_pawn_sniper'
KC = CH_DIR + 'storm_knight' + SEP + 'ai' + SEP + 'storm_knight_commander'
FROM_LEAF, TO_LEAF = 'storm_pawn', 'storm_pawn_sniper'
VIT_SET = {'Normal Body Vitality': 1.0, 'Legendary Body Vitality': 1.0,
           'Normal Shield Vitality': 0.0, 'Legendary Shield Vitality': 0.0}
MELEE_SET = {'Melee Chance': 1.0, 'Melee Attack Delay Timer': 0.0,
             'Melee Attack Timeout': 0.0, 'Melee Leap Range': 12.0}
CONTROLS = [('storm_pawn', CH_DIR + 'storm_pawn' + SEP + 'ai' + SEP + 'storm_pawn'),
            ('storm_pawn_prime', CH_DIR + 'storm_pawn' + SEP + 'ai' + SEP
             + 'storm_pawn_prime'),
            ('storm_knight', CH_DIR + 'storm_knight' + SEP + 'ai' + SEP
             + 'storm_knight')]
APPLY = '--apply' in sys.argv
live = os.path.join(hc.MAPS, 'm70_liftoff.map')
base = V.baseline_for('Halo 4', live)
if not os.path.exists(base):
    raise SystemExit('no baseline; refusing')
print('=== restore from baseline first')
if APPLY:
    shutil.copyfile(base, live)
    print('   restored %d bytes' % os.path.getsize(live))
else:
    print('   would restore')

reg = hp.PluginRegistry(P, ['Halo4MCC', 'Halo4'])
pc = reg.get('char')
r = ET.parse(os.path.join(P, 'Halo4', 'char.xml')).getroot()
VIT = next(int(c.get('offset'), 16) for c in r
           if c.tag.lower() == 'tagblock' and c.get('name') == 'Vitality Properties')
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
so = m.find_tags('char', SUBJECT)[0][1]
print()
print('=== subject before: %s' % TO_LEAF)
print('   Vitality Properties elements: %d (0 means it inherits -- the grow is needed)'
      % m.i32(so + VIT))
idx = {t['index']: t for t in m.tags}
b2 = m.find_tags('scnr', '*')[0][1]
pe, npal = at(m, b2, CPO)
slot = {}
for i in range(npal):
    d = struct.unpack_from('<I', m.data, pe + i * CPS + 0xC)[0]
    tt = idx.get(d & 0xFFFF)
    slot[(tt['name'] or '').rsplit(SEP, 1)[-1] if tt else '?'] = i
src, dst = slot.get(FROM_LEAF), slot.get(TO_LEAF)
se, nsq = at(m, b2, SQO)
hits = []
for s in range(nsq):
    sb = se + s * SQS
    sp, spn = at(m, sb, hc.SPAWN_POINTS[0])
    for j in range(spn):
        e = sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character']
        if m.i16(e) == src:
            hits.append(e)
    for co, csize in hc.CELL_BLOCKS:
        ca, cn = at(m, sb, co)
        for j in range(cn):
            bo, bsize = hc.CELL_SUB['character']
            ba, bn = at(m, ca + j * csize, bo)
            for k in range(bn):
                e = ba + k * bsize + hc.CELL_SUB_INDEX
                if m.i16(e) == src:
                    hits.append(e)
print('   %s = slot %s -> %s = slot %s ; %d spawn/cell entries to convert'
      % (FROM_LEAF, src, TO_LEAF, dst, len(hits)))
if not APPLY:
    print('\n(report only -- pass --apply)')
    raise SystemExit
res = hp._apply_init_defaults(m, {'tag': 'char ' + SUBJECT,
                                  'block': 'Vitality Properties', 'grow': True}, reg)
print()
print('=== grow %s vitality: ok=%d %s'
      % (TO_LEAF, len([x for x in (res or []) if x.get('ok')]),
         [x.get('reason') for x in (res or []) if not x.get('ok')] or ''))
for f, v in VIT_SET.items():
    m.write_tag_field(so, f, v, pc, 'Vitality Properties', 0)
ko = m.find_tags('char', KC)[0][1]
hp._apply_init_defaults(m, {'tag': 'char ' + KC, 'block': 'Charge Properties',
                            'grow': True}, reg)
for f, v in MELEE_SET.items():
    m.write_tag_field(ko, f, v, pc, 'Charge Properties', 0)
for e in hits:
    struct.pack_into('<h', m.data, e, dst)
m.save()
del m

m2 = hp.open_map(live, 'Halo 4')
so2 = m2.find_tags('char', SUBJECT)[0][1]
print()
print('=== after (reopened)')
print('   %-24s vitality block=%d body %s shield %s'
      % (TO_LEAF, m2.i32(so2 + VIT),
         m2.read_tag_field(so2, 'Normal Body Vitality', pc, 'Vitality Properties', 0),
         m2.read_tag_field(so2, 'Normal Shield Vitality', pc, 'Vitality Properties', 0)))
for nm, path in CONTROLS:
    o = m2.find_tags('char', path)[0][1]
    print('   %-24s body %-6s shield %-6s  (control, must be unchanged)'
          % (nm, m2.read_tag_field(o, 'Normal Body Vitality', pc,
                                   'Vitality Properties', 0),
             m2.read_tag_field(o, 'Normal Shield Vitality', pc,
                               'Vitality Properties', 0)))
b3 = m2.find_tags('scnr', '*')[0][1]
se3, nsq3 = at(m2, b3, SQO)
left = conv = 0
for s in range(nsq3):
    sb = se3 + s * SQS
    sp, spn = at(m2, sb, hc.SPAWN_POINTS[0])
    for j in range(spn):
        v = m2.i16(sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character'])
        left += v == src
        conv += v == dst
print('   spawns: %d ordinary Crawler left, %d Crawler Sniper' % (left, conv))
print('   tags: %d ; checksum reproduces: %s'
      % (len(m2.tags), m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))
