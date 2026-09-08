"""Halo 4 matg and scnr audit -- the last two tag classes of the first pass.

matg is one tag per game holding the global tuning; scnr is one per MAP. Both are
therefore audited differently from weap/char: there is no question of "which tags are
live", only which FIELDS carry a real value and which of those no card reaches.

Reports, per class:
  1. plugin diff Reach -> Halo 4 (what arrived, what left)
  2. every field a Halo 4 card targets
  3. every numeric field that carries a NON-DEFAULT value and no card touches
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
NUMERIC = ('float32', 'int32', 'int16', 'int8', 'rangef', 'angle', 'uint16', 'uint32',
           'enum8', 'enum16', 'enum32')
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)


def plugin_path(sub, cls):
    f = os.path.join(P, sub, cls + '.xml')
    return f if os.path.exists(f) else None


def fields_of(cls, sub):
    """{name: set(block path)} and [(name, block, type)] for numeric leaves."""
    f = plugin_path(sub, cls)
    if f is None:
        return None, None
    names = collections.defaultdict(set)
    leaves = []

    def walk(n, path):
        for c in n:
            nm = c.get('name')
            if not nm:
                continue
            if c.tag.lower() == 'tagblock':
                walk(c, (path + '/' + nm).strip('/'))
            else:
                names[nm].add(path or '(root)')
                if c.tag.lower() in NUMERIC:
                    leaves.append((nm, path or None, c.tag.lower()))
    walk(ET.parse(f).getroot(), '')
    return names, leaves


def carded(cls):
    used = collections.defaultdict(set)
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
        if GAME in (c.get('skip_games') or []) or (gl and GAME not in gl):
            continue
        if c.get('ignore'):
            continue
        ctag = W.resolve(c.get('tag'), GAME, order)
        for t in W.resolve(c.get('targets'), GAME, order) or []:
            if not isinstance(t, dict) or not he.target_applies(t, GAME):
                continue
            tag = W.resolve(t.get('tag'), GAME, order) or ctag
            if not isinstance(tag, str) or not tag.startswith(cls + ' '):
                continue
            f = W.resolve(t.get('field'), GAME, order)
            f = hp.apply_difficulty(f, t, 'Legendary') if isinstance(f, str) else f
            if isinstance(f, str):
                used[f].add(' / '.join(p[-3:]))
                base = W.resolve(t.get('field'), GAME, order)
                if isinstance(base, str):
                    used[base].add(' / '.join(p[-3:]))
    return used


for cls, sub_h4, sub_reach, tagpath, maps in [
        ('matg', 'Halo4MCC', 'ReachMCC', 'globals' + SEP + 'globals',
         [m for m, _t in hc.CAMPAIGN][:1]),
        ('scnr', 'Halo4MCC', 'ReachMCC', None, [m for m, _t in hc.CAMPAIGN])]:
    h4n, h4l = fields_of(cls, sub_h4)
    if h4n is None:
        h4n, h4l = fields_of(cls, 'Halo4')
    rn, _rl = fields_of(cls, sub_reach)
    if rn is None:
        rn, _rl = fields_of(cls, 'Reach')
    print('=' * 78)
    print('%s -- Halo 4 declares %d field names (%d numeric leaves)'
          % (cls, len(h4n), len(h4l)))
    new = sorted(set(h4n) - set(rn))
    gone = sorted(set(rn) - set(h4n))
    print('   NEW since Reach (%d): %s' % (len(new), ', '.join(new[:24])
                                           + (' ...' if len(new) > 24 else '')))
    print('   GONE after Reach (%d): %s' % (len(gone), ', '.join(gone[:24])
                                            + (' ...' if len(gone) > 24 else '')))
    used = carded(cls)
    print('   fields a Halo 4 card targets: %d' % len(used))
    for f in sorted(used):
        print('        %-44s %s' % (f, '; '.join(sorted(used[f]))[:60]))
    # values
    pl = reg.get(cls)
    hits = collections.OrderedDict()
    names = sorted({n for n, _b, _t in h4l})
    untouched = [n for n in names if n not in used]
    ms = {}
    for mid in maps:
        ms[mid] = hp.open_map(os.path.join(hc.MAPS, mid + '.map'), GAME)
    for n in untouched:
        blks = sorted({b for nm, b, _t in h4l if nm == n},
                      key=lambda x: (x is None, x))
        for mid in maps:
            m = ms[mid]
            paths = [tagpath] if tagpath else [p for p, _o in m.find_tags(cls, '*')]
            done = False
            for path in paths[:3]:
                got = m.find_tags(cls, path)
                if not got:
                    continue
                base = got[0][1]
                for b in blks:
                    v = m.read_tag_field(base, n, pl, b, 0)
                    if v not in (None, 0, 0.0, -1, -1.0):
                        hits[n] = (b, v, mid)
                        done = True
                        break
                if done:
                    break
            if done:
                break
    print('   UNTOUCHED with a real value (%d of %d untouched):'
          % (len(hits), len(untouched)))
    for n, (b, v, mid) in hits.items():
        print('        %-46s %-30s %s' % (n, b or '(root)',
                                          round(v, 4) if isinstance(v, float) else v))
