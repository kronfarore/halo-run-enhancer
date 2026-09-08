"""Halo 4 proj audit: which projectiles are LIVE, which are carded, which fields nothing touches.

Three questions, each answered against the maps rather than the tag listing:

  1. Which proj tags does a weapon (or a character's own gun) actually fire? A proj
     existing proves nothing -- the same trap as the globals\\damage_effects sweep.
  2. Which live proj tags has no card, and does the weapon that fires them have one?
  3. Which proj FIELDS does no card anywhere target, and of those, which carry a
     non-default value worth offering?

Cards reach proj two ways and both must be honoured: a card-level `tag` starting
"proj ", and a TARGET-level `tag` redirect (Impact Noise / Detonation Noise sit on a
weap card but redirect to the proj), which also carries its own `games` allow-list.
"""
import collections
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
import halo_enhancer as he
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
GAME = 'Halo 4'
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)
pp = reg.get('proj')

# ---------------------------------------------------------------- what is carded
carded = collections.defaultdict(set)       # proj path -> {card label}
fields_used = collections.defaultdict(set)  # field -> {card label}
cards = []


def walk(node, path):
    if isinstance(node, dict):
        if 'tag' in node and 'targets' in node:
            cards.append((path, node))
            return
        for k, v in node.items():
            walk(v, path + [k])


walk(doc, [])
for path, c in cards:
    g = c.get('game')
    gl = [g] if isinstance(g, str) else list(g or [])
    if GAME in (c.get('skip_games') or []) or (gl and GAME not in gl):
        continue
    label = ' / '.join(path[-3:])
    ctag = W.resolve(c.get('tag'), GAME, order)
    for t in W.resolve(c.get('targets'), GAME, order) or []:
        if not isinstance(t, dict) or not he.target_applies(t, GAME):
            continue
        tag = W.resolve(t.get('tag'), GAME, order) or ctag
        if not isinstance(tag, str) or not tag.startswith('proj '):
            continue
        f = W.resolve(t.get('field'), GAME, order)
        if isinstance(f, str):
            fields_used[f].add(label)
        for p in tag.split(' ', 1)[1].split('&'):
            carded[p.strip()].add(label)

# ------------------------------------------------- which proj tags are LIVE, and whose
live = {}                                   # proj path -> {referrer}
allproj = set()
import tagrefs
SPECS = {}
for cls in ('weap', 'vehi', 'eqip', 'char', 'bipd', 'proj'):
    SPECS[cls] = tagrefs._spec(P, 'Halo4MCC', cls) or tagrefs._spec(P, 'Halo4', cls)
for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), GAME)
    idx = {t['index']: t for t in m.tags}
    for t in m.tags:
        if t['class'] == 'proj' and t['name']:
            allproj.add(t['name'])
        sp = SPECS.get(t['class'])
        if sp is None or t['base'] is None:
            continue
        for fieldpath, d in tagrefs.refs_of(m, t['base'], sp):
            tt = idx.get(d & 0xFFFF)
            if tt and tt['class'] == 'proj' and tt['name']:
                live.setdefault(tt['name'], set()).add(
                    '%s %s [%s]' % (t['class'], (t['name'] or '').rsplit(SEP, 1)[-1],
                                    fieldpath.rsplit('/', 1)[0] or 'root'))


def match(path, pats):
    return any((('*' in p and hp.hm._wildcard_matcher(p)(path)) or p == path)
               for p in pats)


pats = list(carded)
uncarded_live = sorted(p for p in live if not match(p, pats))
carded_dead = sorted(p for p in pats if '*' not in p and p not in live and p in allproj)
print('=== %d proj tags in the campaign, %d referenced by a weapon/char, '
      '%d card patterns' % (len(allproj), len(live), len(pats)))
print()
print('--- LIVE but no card (%d)' % len(uncarded_live))
for p in uncarded_live:
    print('   %-62s  fired by %s' % (p[-62:], ', '.join(sorted(live[p]))[:60]))
print()
print('--- carded but nothing fires it (%d)' % len(carded_dead))
for p in carded_dead:
    print('   %-62s  %s' % (p[-62:], ', '.join(sorted(carded[p]))[:50]))

# ------------------------------------------------------- which proj FIELDS go untouched
r = ET.parse(os.path.join(P, 'Halo4MCC', 'proj.xml')).getroot()
NUMERIC = ('float32', 'int32', 'int16', 'int8', 'rangef', 'angle', 'uint16', 'uint32')
decl = []


def fwalk(n, path):
    for c in n:
        nm = c.get('name')
        if not nm:
            continue
        if c.tag.lower() == 'tagblock':
            fwalk(c, (path + '/' + nm).strip('/'))
        elif c.tag.lower() in NUMERIC:
            decl.append((nm, path or None, int(c.get('offset'), 16), c.tag.lower()))


fwalk(r, '')
names = sorted({n for n, _b, _o, _t in decl})
untouched = [n for n in names if n not in fields_used]
print()
print('=== %d numeric proj field names, %d touched by a card, %d untouched'
      % (len(names), len(names) - len(untouched), len(untouched)))
print()
print('--- untouched fields that carry a NON-ZERO value on some live projectile')
maps = {}
hits = collections.OrderedDict()
for n in untouched:
    blks = sorted({b for nm, b, _o, _t in decl if nm == n}, key=lambda x: (x is None, x))
    for mid, _t in hc.CAMPAIGN:
        if mid not in maps:
            maps[mid] = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), GAME)
        m = maps[mid]
        done = False
        for t in m.tags:
            if t['class'] != 'proj' or t['base'] is None or t['name'] not in live:
                continue
            for b in blks:
                v = m.read_tag_field(t['base'], n, pp, b, 0)
                if v not in (None, 0, 0.0):
                    hits[n] = (b, v, t['name'].rsplit(SEP, 1)[-1], mid)
                    done = True
                    break
            if done:
                break
        if done:
            break
for n, (b, v, who, mid) in hits.items():
    print('   %-42s %-26s %-12s %s' % (n, b or '(root)',
                                       round(v, 4) if isinstance(v, float) else v, who))
print()
print('   (%d untouched fields read zero/absent everywhere and are not listed)'
      % (len(untouched) - len(hits)))
