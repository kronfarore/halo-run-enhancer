"""Which cards target an hlmt vitality field, and does root disagree with the block?

Halo 4 and Reach both declare `Maximum Vitality` TWICE on hlmt: once inside
`Old Damage Info` (the legacy block) and once at the tag ROOT, the newer model where
the root pool is split by each Damage Sections entry's `Vitality Percentage`.
`plugin.find` returns the Old Damage Info one, so every existing card reads that
unless it carries `nth: 1`.

The question this answers is not "which is right" in the abstract -- it is, per tag a
card actually names, whether the two disagree, and whether the block a card writes is
even populated.
"""
import io
import json
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
ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
GAMES = [
    ('Halo 4', ['Halo4MCC', 'Halo4'], hc.MAPS, [m for m, _t in hc.CAMPAIGN]),
    ('Halo Reach', ['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
     ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']),
]
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
FIELDS = ('Maximum Vitality', 'Maximum Shield Vitality')


def offsets(sub):
    r = ET.parse(os.path.join(P, sub, 'hlmt.xml')).getroot()
    root_mv = [int(c.get('offset'), 16) for c in r
               if c.get('name') == 'Maximum Vitality' and c.tag.lower() != 'tagblock']
    odi = [c for c in r if c.tag.lower() == 'tagblock'
           and c.get('name') == 'Old Damage Info'][0]
    blk = dict((c.get('name'), int(c.get('offset'), 16)) for c in odi
               if c.get('name') and c.tag.lower() == 'float32')
    return (root_mv[0] if root_mv else None), int(odi.get('offset'), 16), blk


def walk(node, path, out):
    if isinstance(node, dict):
        if 'tag' in node and ('targets' in node or 'field' in node):
            out.append((path, node))
            return
        for k, v in node.items():
            walk(v, path + [k], out)


cards = []
walk(doc, [], cards)

for game, subs, mapdir, maps in GAMES:
    ROOT_MV, ODI_OFF, BF = offsets(subs[0])
    print('=== %s   root Maximum Vitality @0x%X, Old Damage Info @0x%X'
          % (game, ROOT_MV, ODI_OFF))
    # which cards name an hlmt tag and one of the vitality fields
    want = []
    for path, c in cards:
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if game in (c.get('skip_games') or []) or (gl and game not in gl):
            continue
        tag = W.resolve(c.get('tag'), game, order)
        if not isinstance(tag, str) or not tag.startswith('hlmt '):
            continue
        for t in W.resolve(c.get('targets'), game, order) or []:
            if not isinstance(t, dict):
                continue
            f = W.resolve(t.get('field'), game, order)
            if f in FIELDS:
                want.append((' / '.join(path[-3:]), tag, f, t.get('nth', 0) or 0))
    if not want:
        print('   no card targets an hlmt vitality field in this game\n')
        continue
    caches = {}
    for label, tag, f, nth in want:
        paths = [p.strip() for p in tag.split(' ', 1)[1].split('&')]
        shown = 0
        for mid in maps:
            if mid not in caches:
                fp = os.path.join(mapdir, mid + '.map')
                if not os.path.exists(fp):
                    caches[mid] = None
                    continue
                caches[mid] = hp.open_map(fp, game)
            m = caches[mid]
            if m is None:
                continue
            for t in m.tags:
                n = t['name'] or ''
                if t['class'] != 'hlmt' or t['base'] is None:
                    continue
                if not any((('*' in p and hp.hm._wildcard_matcher(p)(n)) or p == n)
                           for p in paths):
                    continue
                root = struct.unpack_from('<f', m.data, t['base'] + ROOT_MV)[0]
                cnt = m.i32(t['base'] + ODI_OFF)
                blk = None
                if cnt > 0:
                    e = m.data2off(m.u32(t['base'] + ODI_OFF + 4))
                    blk = struct.unpack_from('<f', m.data, e + BF[f])[0]
                state = ('block EMPTY -- card writes nothing' if blk is None else
                         'agree' if abs(root - blk) < 1e-6 else 'DISAGREE')
                if state != 'agree' or shown == 0:
                    print('   %-42s %-30s %-24s root=%-9s block=%-9s %s'
                          % (label[:42], n.rsplit(SEP, 1)[-1][:30], f,
                             round(root, 2), '--' if blk is None else round(blk, 2),
                             state + ('  [nth=1]' if nth else '')))
                shown += 1
            if shown:
                break
    print()
