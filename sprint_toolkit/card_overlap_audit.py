"""Two cards writing the same field of the same tag -- the `index: "all"` overlap risk.

Adding `index: "all"` to a card is only safe when no OTHER card reaches the same
(tag, field) on a narrower index, or the two multiply the same bytes twice. This
reports every (game, tag path, block, field) that more than one card targets, and
flags the pairs where the index specs differ, which is the dangerous shape.
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
for game in GAMES:
    hits = collections.defaultdict(list)
    for p, c in cards:
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if game in (c.get('skip_games') or []) or (gl and game not in gl) or c.get('ignore'):
            continue
        ctag = W.resolve(c.get('tag'), game, order)
        for t in W.resolve(c.get('targets'), game, order) or []:
            if not isinstance(t, dict) or not he.target_applies(t, game):
                continue
            tag = W.resolve(t.get('tag'), game, order) or ctag
            f = W.resolve(t.get('field'), game, order)
            if not isinstance(tag, str) or not isinstance(f, str):
                continue
            blk = W.resolve(t.get('block'), game, order)
            idx = t.get('index', 0)
            nth = t.get('nth', 0) or 0
            for path in [x.strip() for x in tag.split(' ', 1)[1].split('&')]:
                key = (tag.split(' ')[0], path, repr(blk), f, repr(nth))
                hits[key].append((' / '.join(p[-2:]), repr(idx)))
    bad = []
    for key, lst in hits.items():
        if len(lst) < 2:
            continue
        idxs = {i for _c, i in lst}
        cardnames = {c for c, _i in lst}
        if len(cardnames) < 2:
            continue                      # same card naming the tag twice: harmless
        # The dangerous shape is ONE card claiming every element while another
        # claims a specific one -- then the "all" card writes bytes the narrow card
        # already owns. Two cards on DIFFERENT specific indices is the correct
        # per-mode pattern (base on 0, "(Charged)" on 1) and is not a conflict.
        has_all = any(i == repr('all') for i in idxs)
        has_specific = any(i != repr('all') for i in idxs)
        if not (has_all and has_specific):
            continue
        bad.append((key, sorted(lst), True))
    if not bad:
        continue
    print('=== %s -- %d field(s) where "all" overlaps a specific index' % (game, len(bad)))
    for (cls, path, blk, f, nth), lst, differing in sorted(bad):
        mark = '   <-- "all" OVERLAPS A SPECIFIC INDEX'
        print('   %-5s %-46s %-22s %-30s%s'
              % (cls, path.rsplit(SEP, 1)[-1][:46], (blk or '')[:22], f[:30], mark))
        for c, i in lst:
            print('        %-46s index=%s' % (c[:46], i))
