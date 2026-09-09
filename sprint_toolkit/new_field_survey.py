r"""new_field_survey.py -- what the fields a new game ADDED are actually worth.

The other half of the cross-game audit. `plugin_diff` says which fields one game has
that another does not; that is a plugin question and it over-reports badly, because a
plugin lists every field the engine can store and a cache fills almost none of them in.
This reads the real tags and answers the question a card needs answered: does anything
in the shipped game SET this field, and do the values vary between tags or is it one
constant nobody tuned?

Verdicts, which are the triage:
  DEAD      no tag sets it -- authoring surface, not gameplay
  CONSTANT  every tag that sets it agrees; there is one number, so a card would move
            the whole game at once rather than one weapon
  VARIES    tags disagree -- the shape a per-weapon / per-enemy card wants
and each row says whether halo.json already names the field, so an existing card is not
proposed twice.

    python sprint_toolkit/new_field_survey.py --group weap
    python sprint_toolkit/new_field_survey.py --group char --from "Halo 3" --to "Halo Reach"
    python sprint_toolkit/new_field_survey.py --group proj --verbose
"""
import argparse
import collections
import json
import os
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_patch as hp                                           # noqa: E402
import plugin_diff as pd                                          # noqa: E402

S = chr(92)
_R = os.path.dirname(TOOL)
# Enough maps to see the spread without reading the whole game. A map can only
# UNDER-report (a tag it does not carry is invisible), so the verdicts are a floor:
# DEAD means "not on these maps", never "not in the game".
MAPS = {
    'Halo 2': (os.path.join(_R, 'halo2', 'h2_maps_win64_dx11'),
               ['03a_oldmombasa', '05a_deltaapproach', '07a_highcharity']),
    'Halo 3': (os.path.join(_R, 'halo3', 'maps'),
               ['030_outskirts', '070_waste', '120_halo']),
    'Halo 3: ODST': (os.path.join(_R, 'halo3odst', 'maps'), ['l200', 'l300']),
    'Halo Reach': (os.path.join(_R, 'haloreach', 'maps'),
                   ['m10', 'm30', 'm50', 'm70']),
    'Halo 4': (os.path.join(_R, 'halo4', 'maps'),
               ['m10_crash', 'm40_invasion', 'm70_liftoff', 'm90_sacrifice']),
}
# Types worth reading a number out of. A tagref or stringid is a reference, not a dial,
# and a card cannot multiply it.
NUMERIC = {'float32', 'int8', 'int16', 'int32', 'uint8', 'uint16', 'uint32',
           'degree', 'rangef', 'enum8', 'enum16', 'enum32'}


def cards_naming(fields):
    """{field name: [card paths]} for every halo.json card that already names one."""
    d = json.load(open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
    out = collections.defaultdict(list)

    def walk(node, path):
        if isinstance(node, dict):
            ts = node.get('targets')
            if ts is not None:
                rows = []
                for v in ([ts] if isinstance(ts, list) else list(ts.values())):
                    rows.extend(v if isinstance(v, list) else [])
                for t in rows:
                    f = t.get('field') if isinstance(t, dict) else None
                    for f in ([f] if isinstance(f, str)
                              else list(f.values()) if isinstance(f, dict) else []):
                        if f in fields:
                            out[f].append(' / '.join(path[-2:]))
                return
            for k, v in node.items():
                walk(v, path + [k])
        elif isinstance(node, list):
            for v in node:
                walk(v, path)
    walk(d, [])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--group', required=True)
    ap.add_argument('--from', dest='older', default='Halo Reach')
    ap.add_argument('--to', dest='newer', default='Halo 4')
    ap.add_argument('--verbose', action='store_true',
                    help='name the tags behind each value')
    ap.add_argument('--min-setters', type=int, default=1)
    a = ap.parse_args()

    _ob, ofields, _obs, _od = pd.load(a.older, a.group)
    _nb, nfields, _nbs, _nd = pd.load(a.newer, a.group)
    added = {p: t for p, t in nfields.items() if p not in ofields}
    folder, names = MAPS[a.newer]
    plug = hp.PluginRegistry(pd.PLUGINS, pd.SUBDIRS[a.newer]).get(a.group)
    if plug is None:
        raise SystemExit('no %s plugin for %s' % (a.group, a.newer))
    print('%s -> %s, %s: %d field(s) added by the plugin, %d readable as a number'
          % (a.older, a.newer, a.group, len(added),
             sum(1 for t in added.values() if t in NUMERIC)))
    known = cards_naming({p.rsplit('/', 1)[-1] for p in added})

    vals = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(dict)
    seen_tags = set()
    for n in names:
        path = os.path.join(folder, n + '.map')
        if not os.path.exists(path):
            continue
        m = hp.open_map(path, a.newer)
        for tp, base in m.find_tags(a.group, '*'):
            if tp in seen_tags:
                continue
            seen_tags.add(tp)
            for fp, ftype in added.items():
                if ftype not in NUMERIC:
                    continue
                name = fp.rsplit('/', 1)[-1]
                parts = fp.strip('/').split('/')
                blk = parts[-2] if len(parts) > 1 else None
                try:
                    v = m.read_tag_field(base, name, plug, blk, 0)
                except Exception:
                    v = None
                if v is None or v == 0:
                    continue
                key = round(v, 4) if isinstance(v, float) else v
                vals[fp][key] += 1
                examples[fp].setdefault(key, tp.rsplit(S, 1)[-1])
    print('read %d %s tag(s) over %d map(s)' % (len(seen_tags), a.group, len(names)))
    print()
    print('%-9s %-52s %-7s %s' % ('verdict', 'field', 'setters', 'values'))
    print('-' * 110)
    rows = []
    for fp, ftype in sorted(added.items()):
        if ftype not in NUMERIC:
            continue
        c = vals.get(fp)
        setters = sum(c.values()) if c else 0
        if setters < a.min_setters and setters:
            continue
        verdict = 'DEAD' if not c else ('CONSTANT' if len(c) == 1 else 'VARIES')
        rows.append((0 if verdict == 'VARIES' else 1 if verdict == 'CONSTANT' else 2,
                     fp, verdict, c, setters))
    for _o, fp, verdict, c, setters in sorted(rows):
        show = ''
        if c:
            top = c.most_common(5)
            show = ', '.join('%s x%d' % (v, n) for v, n in top)
            if len(c) > 5:
                show += ', ... %d distinct' % len(c)
        name = fp.rsplit('/', 1)[-1]
        print('%-9s %-52s %-7s %s' % (verdict, fp[1:], setters or '-', show))
        if known.get(name):
            print('%-9s %-52s   already carded: %s'
                  % ('', '', ', '.join(sorted(set(known[name])))[:80]))
        if a.verbose and c:
            for v, _n in c.most_common(5):
                print('%-9s %-52s   %-12s e.g. %s' % ('', '', v, examples[fp][v]))


if __name__ == '__main__':
    main()
