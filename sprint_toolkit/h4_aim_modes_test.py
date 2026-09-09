r"""h4_aim_modes_test.py -- do the new `Aim Assist Modes` rows actually write?

Halo 4 declares its aim assist twice: the root fields every earlier game uses, and a
new `Aim Assist Modes` block that repeats them -- one element on a player weapon, two on
a vehicle gun -- and on 20 of the 37 weapon tags the cards name, the two DISAGREE. The
Autoaim / Magnetism / Error Angle cards were only ever writing the root, so each card
now carries a mirrored Halo 4 row for the block as well.

This writes every one of those rows onto a copy of each map with a x2 multiply and
reads the result back out of EVERY element of the block, which is the part `index:
"all"` exists for: a vehicle gun's second mode is invisible to any check that only
looks at element 0.

    python sprint_toolkit/h4_aim_modes_test.py
"""
import collections
import io
import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                                           # noqa: E402
import halo_enhancer as he                                        # noqa: E402
import halo_patch as hp                                           # noqa: E402
import h4_census as hc                                            # noqa: E402

S = chr(92)
BLOCK = 'Aim Assist Modes'
MAPS = ['m10_crash', 'm40_invasion', 'm70_liftoff', 'm90_sacrifice']


def rows():
    """Every (weapon, card, tag, field) the mirrored Halo 4 rows declare."""
    doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
    order = list(doc['Missions'])
    out = []
    for weapon, cards in doc['Player Modifiers']['Specific Weapon Modifier'].items():
        for cname, c in cards.items():
            g = c.get('game')
            gl = [g] if isinstance(g, str) else (g or order)
            if 'Halo 4' not in gl or c.get('ignore'):
                continue
            tag = he.resolve_gamed(c.get('tag'), 'Halo 4', order) \
                if isinstance(c.get('tag'), dict) else c.get('tag')
            ts = c.get('targets')
            ts = he.resolve_gamed(ts, 'Halo 4', order) if isinstance(ts, dict) else ts
            for t in ts or []:
                if not isinstance(t, dict) or t.get('block') != BLOCK:
                    continue
                if not he.target_applies(t, 'Halo 4'):
                    continue
                if isinstance(tag, str) and tag.startswith('weap '):
                    out.append((weapon, cname, tag.split(' ', 1)[-1], t['field']))
    return out


def main():
    jobs = rows()
    print('%d mirrored row(s) over %d card(s), %d weapon(s)'
          % (len(jobs), len({(w, c) for w, c, _t, _f in jobs}),
             len({w for w, _c, _t, _f in jobs})))
    reg = hp.PluginRegistry(assembly_plugins.plugins_dir(), ['Halo4MCC', 'Halo4'])
    plug = reg.get('weap')
    wrote = set()
    resident = set()          # rows whose tag was found on at least one sampled map
    elems = collections.Counter()
    missed_tags = set()
    for mid in MAPS:
        src = os.path.join(hc.MAPS, mid + '.map')
        if not os.path.exists(src):
            continue
        dst = os.path.join(tempfile.gettempdir(), mid + '.aim.map')
        shutil.copyfile(src, dst)
        m = hp.open_map(dst, 'Halo 4')
        for weapon, cname, pat, field in jobs:
            if (weapon, cname, field) in wrote:
                continue
            for path in [x.strip() for x in pat.split('&')]:
                hits = m.find_tags('weap', path)
                if not hits:
                    missed_tags.add((weapon, path))
                    continue
                resident.add((weapon, cname, field))
                before = {}
                for tp, base in hits:
                    n = m.i32(base + 0x3F0)
                    before[tp] = [m.read_tag_field(base, field, plug, BLOCK, i)
                                  for i in range(n)]
                res = m.apply_field('weap', path, field, 'mul', 2.0, plug, BLOCK,
                                    'all', nth=0) or []
                if not any(r.get('ok') and not r.get('skip') for r in res):
                    continue
                # every element must have moved, not just the first
                good = True
                for tp, base in hits:
                    n = m.i32(base + 0x3F0)
                    after = [m.read_tag_field(base, field, plug, BLOCK, i)
                             for i in range(n)]
                    elems[n] += 1
                    for b, a in zip(before[tp], after):
                        if b in (None, 0) or a is None:
                            continue
                        if abs(a - b * 2.0) > max(1e-3, abs(b) * 1e-3):
                            good = False
                if good:
                    wrote.add((weapon, cname, field))
        del m
        os.remove(dst)
    total = {(w, c, f) for w, c, _t, f in jobs}
    print('wrote and verified: %d/%d row(s) whose tag is on a sampled map (%d rows '
          'total; the rest name a weapon these four maps do not carry)'
          % (len(wrote), len(resident), len(total)))
    print('block sizes seen: %s' % dict(elems))
    for w, c, f in sorted(resident - wrote):
        print('   NO WRITE  %-20s %-12s %s' % (w, c, f))
    if missed_tags:
        print('tags not resident on the sampled maps (not a failure):')
        for w, p in sorted(missed_tags):
            print('   %-20s %s' % (w, p.rsplit(S, 1)[-1]))


if __name__ == '__main__':
    main()
