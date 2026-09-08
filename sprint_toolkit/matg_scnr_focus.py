"""The matg/scnr audit again, filtered to blocks that could plausibly carry a card.

The raw audit reports 319 untouched matg fields and 118 untouched scnr fields, but the
overwhelming majority are engine and authoring internals -- garbage collection, soft
ceilings, camera damping, BSP cluster data, decal culling, cutscene titles. Those are
noise for this question. This keeps only the blocks that hold tuning a player would
feel, and drops the difficulty-prefixed ladder, which the existing cards DO reach
through `difficulty: true` and only looks untouched because the audit resolves one
prefix at a time.
"""
import collections
import io
import json
import os
import sys
import xml.etree.ElementTree as ET

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import halo_enhancer as he
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
GAME = 'Halo 4'
NUMERIC = ('float32', 'int32', 'int16', 'int8', 'rangef', 'angle', 'uint16', 'uint32')
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)
DIFF_PREFIX = ('Easy ', 'Normal ', 'Heroic ', 'Legendary ')
KEEP_MATG = ('Player Information', 'Player Control', 'Default Player Traits',
             'Campaign Metagame Globals', 'Active Camo', 'Damage', 'Player Traits')
KEEP_SCNR = ('Structure BSP', '(root)', 'Player Starting Profile', 'Starting Profile')


def leaves(cls, subs):
    for sub in subs:
        f = os.path.join(P, sub, cls + '.xml')
        if os.path.exists(f):
            break
    else:
        return []
    out = []

    def walk(n, path):
        for c in n:
            nm = c.get('name')
            if not nm:
                continue
            if c.tag.lower() == 'tagblock':
                walk(c, (path + '/' + nm).strip('/'))
            elif c.tag.lower() in NUMERIC:
                out.append((nm, path or None))
    walk(ET.parse(f).getroot(), '')
    return out


def carded(cls):
    used = set()
    cards = []

    def walk(n, p):
        if isinstance(n, dict):
            if 'tag' in n and 'targets' in n:
                cards.append((p, n))
                return
            for k, v in n.items():
                walk(v, p + [k])
    walk(doc, [])
    for p, c in cards:
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if GAME in (c.get('skip_games') or []) or (gl and GAME not in gl) or c.get('ignore'):
            continue
        ctag = W.resolve(c.get('tag'), GAME, order)
        for t in W.resolve(c.get('targets'), GAME, order) or []:
            if not isinstance(t, dict) or not he.target_applies(t, GAME):
                continue
            tag = W.resolve(t.get('tag'), GAME, order) or ctag
            if not isinstance(tag, str) or not tag.startswith(cls + ' '):
                continue
            f = W.resolve(t.get('field'), GAME, order)
            if isinstance(f, str):
                used.add(f)
                for d in ('Easy', 'Normal', 'Heroic', 'Legendary'):
                    used.add(d + ' ' + f)
    return used


for cls, keep, tagpath, maps in [
        ('matg', KEEP_MATG, 'globals' + SEP + 'globals', ['m40_invasion']),
        ('scnr', KEEP_SCNR, None, ['m40_invasion', 'm30_cryptum'])]:
    used = carded(cls)
    pl = reg.get(cls)
    ls = leaves(cls, ['Halo4MCC', 'Halo4'])
    ms = {mid: hp.open_map(os.path.join(hc.MAPS, mid + '.map'), GAME) for mid in maps}
    rows = []
    seen = set()
    for name, blk in ls:
        if name in used or name in seen:
            continue
        if any(name.startswith(d) for d in DIFF_PREFIX):
            continue
        if not any(k in (blk or '(root)') for k in keep):
            continue
        seen.add(name)
        for mid in maps:
            m = ms[mid]
            paths = [tagpath] if tagpath else [p for p, _o in m.find_tags(cls, '*')]
            got = m.find_tags(cls, paths[0]) if paths else []
            if not got:
                continue
            v = m.read_tag_field(got[0][1], name, pl, blk, 0)
            if v not in (None, 0, 0.0, -1, -1.0):
                rows.append((blk or '(root)', name, v))
                break
    print('=== %s -- untouched, in a block that could carry a card (%d)'
          % (cls, len(rows)))
    for blk, name, v in sorted(rows):
        print('   %-42s %-46s %s' % (blk[:42], name,
                                     round(v, 4) if isinstance(v, float) else v))
    print()
