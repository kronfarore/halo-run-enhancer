"""Every Halo 4 equipment card, every target, read across the WHOLE campaign.

deadcards samples one map per game, which is exactly the shape of miss that hides an
ability only two missions carry. This asks all eight.
"""
import io
import json
import os
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)
maps = {}


def openm(mid):
    if mid not in maps:
        maps[mid] = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    return maps[mid]


def read_any(tag, field, block, index):
    """(value, map, tagpath) for the first campaign map where this target reads."""
    cls, _, rest = tag.partition(' ')
    pl = reg.get(cls)
    if pl is None:
        return None, None, 'no plugin for %s' % cls
    paths = [p.strip() for p in rest.split('&')]
    for mid, _t in hc.CAMPAIGN:
        m = openm(mid)
        for t in m.tags:
            if t['class'] != cls or t['base'] is None or not t['name']:
                continue
            n = t['name']
            hit = any((('*' in p and hp.hm._wildcard_matcher(p)(n)) or p == n)
                      for p in paths)
            if not hit:
                continue
            v = m.read_tag_field(t['base'], field, pl, block,
                                 0 if index is None else index)
            if v is not None:
                return v, mid, n.rsplit(SEP, 1)[-1]
    return None, None, None


bad = 0
total = 0
for entry, cards in doc['Equipment'].items():
    rows = []
    for cname, c in cards.items():
        if not isinstance(c, dict):
            continue
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if 'Halo 4' in (c.get('skip_games') or []):
            continue
        if gl and 'Halo 4' not in gl:
            continue
        tag = W.resolve(c.get('tag'), 'Halo 4', order)
        targets = W.resolve(c.get('targets'), 'Halo 4', order) or []
        for t in targets:
            if not isinstance(t, dict):
                continue
            gs = t.get('games')
            if gs and 'Halo 4' not in gs:
                continue
            f = W.resolve(t.get('field'), 'Halo 4', order)
            if not isinstance(f, str):
                continue
            total += 1
            v, mid, where = read_any(tag, f, t.get('block'), t.get('index'))
            if v is None:
                bad += 1
                rows.append(('DEAD', cname, f, t.get('block'), '', ''))
            else:
                rows.append(('ok  ', cname, f, t.get('block'),
                             round(v, 4) if isinstance(v, float) else v,
                             '%s %s' % (mid, where)))
    if rows:
        print('=== %s' % entry)
        for st, cname, f, b, v, w in rows:
            print('   %s %-20s %-42s %-14s %-10s %s'
                  % (st, cname, f, b or '', v, w))
print('\n%d targets, %d dead' % (total, bad))
