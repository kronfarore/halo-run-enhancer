"""Which tag CLASSES does each game's card set reach, and what does Halo 4 still miss?

The first pass for a game is "every tag class we normally card". This compares Halo 4
against every earlier game so a whole class that was simply never wired shows up, rather
than being invisible because no card names it.
"""
import collections
import io
import json
import os
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_enhancer as he
import h4_wire_weapons as W

SEP = chr(92)
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
GAMES = list(doc['Missions'])
cards = []


def walk(n, p):
    if isinstance(n, dict):
        if 'tag' in n and 'targets' in n:
            cards.append((p, n))
            return
        for k, v in n.items():
            walk(v, p + [k])


walk(doc, [])
per = {}
detail = collections.defaultdict(lambda: collections.defaultdict(set))
for game in GAMES:
    seen = collections.Counter()
    for p, c in cards:
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if game in (c.get('skip_games') or []) or (gl and game not in gl) or c.get('ignore'):
            continue
        ctag = W.resolve(c.get('tag'), game, order)
        tags = set()
        if isinstance(ctag, str) and ' ' in ctag:
            tags.add(ctag.split(' ')[0])
        for t in W.resolve(c.get('targets'), game, order) or []:
            if not isinstance(t, dict) or not he.target_applies(t, game):
                continue
            tt = W.resolve(t.get('tag'), game, order)
            if isinstance(tt, str) and ' ' in tt:
                tags.add(tt.split(' ')[0])
        for cl in tags:
            seen[cl] += 1
            detail[game][cl].add(' / '.join(p[-3:]))
    per[game] = seen

allcls = sorted({c for s in per.values() for c in s})
print('%-8s %s' % ('class', ''.join('%-9s' % g.replace('Halo ', 'H').replace(': ODST', 'ODST')
                                    for g in GAMES)))
for cl in allcls:
    row = ''.join('%-9s' % (per[g].get(cl) or '-') for g in GAMES)
    mark = ''
    if not per['Halo 4'].get(cl) and any(per[g].get(cl) for g in GAMES if g != 'Halo 4'):
        mark = '   <-- NOT REACHED IN HALO 4'
    print('%-8s %s%s' % (cl, row, mark))

print()
print('=== classes some game cards but Halo 4 does not')
for cl in allcls:
    if per['Halo 4'].get(cl):
        continue
    who = [g for g in GAMES if per[g].get(cl)]
    print('   %-6s carded in: %s' % (cl, ', '.join(who)))
    for g in who[:1]:
        for x in sorted(detail[g][cl])[:6]:
            print('        e.g. %s' % x)
