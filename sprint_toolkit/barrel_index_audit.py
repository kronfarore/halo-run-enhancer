"""Give every Barrels row on a multi-barrel Halo 4 weapon `index: "all"`.

Line scan rather than text anchoring: track the current weapon and card while walking
halo.json, and rewrite any `"block": "Barrels"` row that carries no index, inside a card
whose weapon actually has more than one barrel. The earlier text-anchored attempt
silently caught only 30 of 45 rows, which is exactly the failure mode a scan avoids.
"""
import collections
import io
import json
import os
import sys
import xml.etree.ElementTree as ET

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
HALO_JSON = os.path.join(TOOL, 'halo.json')
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
APPLY = '--apply' in sys.argv

r = ET.parse(os.path.join(P, 'Halo4MCC', 'weap.xml')).getroot()
BOFF = int([c for c in r if c.tag.lower() == 'tagblock'
            and c.get('name') == 'Barrels'][0].get('offset'), 16)
multi = {}
for mid, _t in hc.CAMPAIGN:
    m = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), 'Halo 4')
    for tp, off in m.find_tags('weap', '*'):
        if tp not in multi and m.i32(off + BOFF) > 1:
            multi[tp] = m.i32(off + BOFF)

doc = json.load(io.open(HALO_JSON, encoding='utf-8'))
order = list(doc['Missions'])
target_cards = set()


def walk(n, p):
    if isinstance(n, dict):
        if 'tag' in n and 'targets' in n:
            g = n.get('game')
            gl = [g] if isinstance(g, str) else list(g or [])
            if 'Halo 4' in (n.get('skip_games') or []) or (gl and 'Halo 4' not in gl):
                return
            tag = W.resolve(n.get('tag'), 'Halo 4', order)
            if not isinstance(tag, str) or not tag.startswith('weap '):
                return
            paths = [x.strip() for x in tag.split(' ', 1)[1].split('&')]
            if any(any((('*' in q and hp.hm._wildcard_matcher(q)(mp)) or q == mp)
                       for q in paths) for mp in multi):
                target_cards.add((p[-2] if len(p) >= 2 else '?', p[-1]))
            return
        for k, v in n.items():
            walk(v, p + [k])


walk(doc, [])
lines = io.open(HALO_JSON, encoding='utf-8').read().split(chr(10))
weapon = card = None
changed = collections.Counter()
for i, l in enumerate(lines):
    s = l.strip()
    ind = len(l) - len(l.lstrip(chr(9)))
    if s.endswith('{') and s.startswith('"'):
        name = s[1:s.index('"', 1)]
        if ind == 3:
            weapon, card = name, None
        elif ind == 4:
            card = name
    if '"block": "Barrels"' in l and '"index"' not in l:
        if (weapon, card) in target_cards:
            lines[i] = l.replace('"block": "Barrels"',
                                 '"block": "Barrels", "index": "all"')
            changed[(weapon, card)] += 1
out = chr(10).join(lines)
json.loads(out)
tot = sum(changed.values())
for (w, c), n in sorted(changed.items()):
    print('   %-18s %-24s %d row(s)' % (w, c, n))
print('   %d rows across %d cards' % (tot, len(changed)))
if not APPLY:
    print('(report only -- pass --apply)')
    raise SystemExit
io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
print('written')
