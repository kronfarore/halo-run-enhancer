"""Trace globals\\damage_effects the way the user asks for: from the CHARACTER back.

A jpt! existing proves nothing. What makes one worth carding is that some object
references it, so this walks every bipd/vehi/weap header, collects the jpt! refs, and
reports each globals\\damage_effects tag with the list of things that point at it.
Anything with no referrer is unused and should not be carded.

Also reports Target Tracking / Target Leading ranges, to settle whether that field is
genuinely 0..1 and should clamp.
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
ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
GAMES = [
    ('Halo 3', ['Halo3MCC', 'Halo3'], os.path.join(ROOT, 'halo3', 'maps'),
     ['010_jungle', '030_outskirts', '070_waste', '120_halo']),
    ('Halo Reach', ['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
     ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']),
    ('Halo 4', ['Halo4MCC', 'Halo4'], hc.MAPS, [m for m, _t in hc.CAMPAIGN]),
]
SLOT = {0x3FC: 'primary melee', 0x41C: 'boarding', 0x42C: 'boarding response',
        0x43C: 'ejection', 0x44C: 'ejection response', 0x47C: 'obstacle smash',
        0x48C: 'shield pop', 0x49C: 'assassination'}

for game, subs, mapdir, maps in GAMES:
    refs = collections.defaultdict(set)          # jpt path -> {(referrer, slot)}
    allglob = set()
    track = []
    reg = hp.PluginRegistry(P, subs)
    pc = reg.get('char')
    for mid in maps:
        fp = os.path.join(mapdir, mid + '.map')
        if not os.path.exists(fp):
            continue
        m = hp.open_map(fp, game)
        idx = {t['index']: t for t in m.tags}
        for t in m.tags:
            n = t['name'] or ''
            if t['base'] is None:
                continue
            if t['class'] == 'jpt!' and n.startswith('globals' + SEP + 'damage_effects'):
                allglob.add(n)
            if t['class'] == 'char' and pc is not None:
                for f in ('Target Tracking', 'Target Leading'):
                    v = m.read_tag_field(t['base'], f,  pc,
                                         'Firing Pattern Properties/Firing Patterns',
                                         'all')
                    if v is not None:
                        track.append(v)
            if t['class'] not in ('bipd', 'vehi', 'weap', 'char'):
                continue
            for off in range(0, 0x900, 4):
                try:
                    d = struct.unpack_from('<I', m.data, t['base'] + off)[0]
                except Exception:
                    break
                tt = idx.get(d & 0xFFFF)
                if (tt and (d >> 16) != 0 and tt['class'] == 'jpt!' and tt['name']
                        and tt['name'].startswith('globals' + SEP + 'damage_effects')):
                    refs[tt['name']].add((n.rsplit(SEP, 1)[-1], SLOT.get(off, hex(off))))
    print('=== %s   %d globals%sdamage_effects jpt! in these maps' % (game, len(allglob), SEP))
    for path in sorted(allglob):
        who = refs.get(path)
        leaf = path.rsplit(SEP, 1)[-1]
        if not who:
            print('   %-34s  UNUSED -- nothing references it' % leaf)
        else:
            slots = sorted({s for _r, s in who})
            names = sorted({r for r, _s in who})
            print('   %-34s  %2d referrer(s) as %-22s %s'
                  % (leaf, len(names), '/'.join(slots)[:22],
                     ', '.join(names[:5]) + (' ...' if len(names) > 5 else '')))
    if track:
        print('   Target Tracking/Leading across %d reads: min=%s max=%s'
              % (len(track), round(min(track), 3), round(max(track), 3)))
    print()
