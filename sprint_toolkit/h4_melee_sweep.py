"""Every melee damage effect every Halo 4 enemy biped actually references, vs the cards.

The biped carries a fixed melee layout, established by reading storm_elite_ai,
storm_knight, storm_hunter and storm_pawn:

    +0x3FC primary melee          +0x41C boarding      +0x42C boarding response
    +0x43C ejection               +0x44C ejection response
    +0x47C obstacle smash         +0x49C assassination

Rather than trust those offsets, this scans the whole biped header for jpt! refs and
reports the offset alongside, so a species with an extra slot shows up rather than
being silently skipped.
"""
import collections
import io
import json
import os
import struct
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
SLOT = {0x3FC: 'primary melee', 0x41C: 'boarding', 0x42C: 'boarding response',
        0x43C: 'ejection', 0x44C: 'ejection response', 0x47C: 'obstacle smash',
        0x49C: 'assassination'}
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
se = doc['Enemy modifiers']['Specific Enemy modifier']

# every jpt! path any Halo 4 enemy card names
carded = {}
for sp, cards in se.items():
    for cn, c in cards.items():
        if not isinstance(c, dict):
            continue
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if gl and 'Halo 4' not in gl:
            continue
        tag = W.resolve(c.get('tag'), 'Halo 4', order)
        if not isinstance(tag, str) or not tag.startswith('jpt!'):
            continue
        for p in tag.split(' ', 1)[1].split('&'):
            carded.setdefault(p.strip(), []).append('%s / %s' % (sp, cn))

# every jpt! every enemy biped references
found = collections.OrderedDict()
for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    idx = {t['index']: t for t in m.tags}
    for t in m.tags:
        n = t['name'] or ''
        if t['class'] != 'bipd' or t['base'] is None or n in found:
            continue
        rows = []
        for off in range(0, 0x900, 4):
            try:
                d = struct.unpack_from('<I', m.data, t['base'] + off)[0]
            except Exception:
                break
            tt = idx.get(d & 0xFFFF)
            if tt and (d >> 16) != 0 and tt['class'] == 'jpt!' and tt['name']:
                rows.append((off, tt['name']))
        if rows:
            found[n] = rows

print('=== every jpt! referenced by a Halo 4 biped, and whether a card names it\n')
uncarded = collections.OrderedDict()
for n, rows in found.items():
    leaf = n.rsplit(SEP, 1)[-1]
    print('%s' % n)
    for off, path in rows:
        who = carded.get(path)
        mark = 'CARDED: ' + '; '.join(sorted(set(who))) if who else '<< NO CARD'
        print('   +0x%03X %-22s %-56s %s'
              % (off, SLOT.get(off, '?'), path[-56:], mark))
        if not who and not path.startswith('globals' + SEP):
            uncarded.setdefault(leaf, []).append((off, path))
    print()

print('=== species-owned melee effects with NO card')
if not uncarded:
    print('   none')
for leaf, rows in uncarded.items():
    print('   %s' % leaf)
    for off, path in rows:
        print('      +0x%03X %-22s %s' % (off, SLOT.get(off, '?'), path))
