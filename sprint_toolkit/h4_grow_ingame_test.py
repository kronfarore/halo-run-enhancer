"""The easy-to-read version of the same test: grow a vitality block.

The Knight Commander was an awkward subject because it OWNS its Vitality Properties --
a vitality edit there would be a plain write and would not have exercised the grow at
all. Melee was the only block it lacks, which is why the test read as animation timing.

`storm_knight_ranger` is the better subject on Shutdown:
  * fielded 12 times on m70,
  * owns NO Vitality Properties (it inherits storm_knight's 70 body / 80 shield), so
    reaching it REQUIRES the grow,
  * and vitality is unmistakable in play.

Set to 1 body / 0 shield, a Knight Ranger dies to a single hit. The reader does not
even have to tell a Ranger from an ordinary Knight: if ANY Knight on Shutdown pops
instantly, the grow reached it, and if none do, it did not. Ordinary Knights and the
Commander keep 70/80 and 90/110, which is the control.
"""
import os
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
KR = ('objects' + SEP + 'characters' + SEP + 'storm_knight' + SEP + 'ai' + SEP
      + 'storm_knight_ranger')
CONTROLS = [('storm_knight', 'objects' + SEP + 'characters' + SEP + 'storm_knight'
             + SEP + 'ai' + SEP + 'storm_knight'),
            ('storm_knight_commander', 'objects' + SEP + 'characters' + SEP
             + 'storm_knight' + SEP + 'ai' + SEP + 'storm_knight_commander')]
SET = {'Normal Body Vitality': 1.0, 'Legendary Body Vitality': 1.0,
       'Normal Shield Vitality': 0.0, 'Legendary Shield Vitality': 0.0}
APPLY = '--apply' in sys.argv
live = os.path.join(hc.MAPS, 'm70_liftoff.map')
base = V.baseline_for('Halo 4', live)
print('baseline present: %s  (%s)' % (os.path.exists(base), base))
if not os.path.exists(base):
    raise SystemExit('refusing to patch with no baseline to restore from')

reg = hp.PluginRegistry(P, ['Halo4MCC', 'Halo4'])
pc = reg.get('char')
r = ET.parse(os.path.join(P, 'Halo4', 'char.xml')).getroot()
VIT = next(int(c.get('offset'), 16) for c in r
           if c.tag.lower() == 'tagblock' and c.get('name') == 'Vitality Properties')
m = hp.open_map(live, 'Halo 4')
off = m.find_tags('char', KR)[0][1]
print()
print('=== before')
print('   knight_ranger Vitality Properties elements: %d' % m.i32(off + VIT))
for f in SET:
    print('   %-28s %s' % (f, m.read_tag_field(off, f, pc, 'Vitality Properties', 0)))
for nm, path in CONTROLS:
    o = m.find_tags('char', path)[0][1]
    print('   control %-24s body %s / shield %s'
          % (nm, m.read_tag_field(o, 'Normal Body Vitality', pc, 'Vitality Properties', 0),
             m.read_tag_field(o, 'Normal Shield Vitality', pc, 'Vitality Properties', 0)))
if not APPLY:
    print('\n(report only -- pass --apply)')
    raise SystemExit
res = hp._apply_init_defaults(m, {'tag': 'char ' + KR, 'block': 'Vitality Properties',
                                 'grow': True}, reg)
bad = [x.get('reason') for x in (res or []) if not x.get('ok')]
print()
print('=== seed: %d ok %s' % (len([x for x in (res or []) if x.get('ok')]),
                              bad or ''))
print('   elements now: %d at file offset 0x%X'
      % (m.i32(off + VIT), m.data2off(m.u32(off + VIT + 4))))
for f, v in SET.items():
    m.write_tag_field(off, f, v, pc, 'Vitality Properties', 0)
m.save()
del m
m2 = hp.open_map(live, 'Halo 4')
o2 = m2.find_tags('char', KR)[0][1]
print()
print('=== after (reopened)')
print('   tags: %d ; checksum reproduces: %s'
      % (len(m2.tags), m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))
for f in SET:
    print('   %-28s %s' % (f, m2.read_tag_field(o2, f, pc, 'Vitality Properties', 0)))
for nm, path in CONTROLS:
    o = m2.find_tags('char', path)[0][1]
    print('   control %-24s body %s / shield %s  (must be unchanged)'
          % (nm, m2.read_tag_field(o, 'Normal Body Vitality', pc,
                                   'Vitality Properties', 0),
             m2.read_tag_field(o, 'Normal Shield Vitality', pc,
                               'Vitality Properties', 0)))
kc = m2.find_tags('char', CONTROLS[1][1])[0][1]
CH = next(int(c.get('offset'), 16) for c in r
          if c.tag.lower() == 'tagblock' and c.get('name') == 'Charge Properties')
print('   the earlier melee grow still stands: Charge elements=%d, melee chance %s'
      % (m2.i32(kc + CH),
         m2.read_tag_field(kc, 'Melee Chance', pc, 'Charge Properties', 0)))
