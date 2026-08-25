r"""plugin_diff.py -- what a tag gained or lost between two games.

Scoping tool for new cards: point it at a tag group and two games and it reports the
blocks and fields one has that the other does not, grouped by block so a whole new
subsystem reads as one thing rather than forty loose fields.

It also cross-references halo.json: a field the LATER game dropped is only a problem
if a card actually names it, and a card is only broken if that card is offered in the
later game at all. Both are reported, because "24 fields removed" and "one card
affected" are very different headlines.

    python sprint_toolkit/plugin_diff.py --group weap
    python sprint_toolkit/plugin_diff.py --group char --from "Halo 2" --to "Halo 3"
    python sprint_toolkit/plugin_diff.py --group weap --removed-only
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import assembly_plugins                              # noqa: E402

PLUGINS = assembly_plugins.plugins_dir()
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')

SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST'],
           'Halo Reach': ['ReachMCC', 'Reach']}
# Structural noise, not fields anyone would build a card on.
SKIP_TAGS = {'comment', 'undefined', 'unused'}


def load(game, group):
    """({block path: elementSize}, {field path: kind}, baseSize) for a tag group."""
    path = None
    for sub in SUBDIRS[game]:
        p = os.path.join(PLUGINS, sub, group + '.xml')
        if os.path.isfile(p):
            path = p
            break
    if path is None:
        raise SystemExit('no %s plugin for %s under %s' % (group, game, PLUGINS))
    blocks, fields = {}, {}

    def walk(node, prefix):
        for ch in node:
            name, tag = ch.get('name'), ch.tag.lower()
            if not name or tag in SKIP_TAGS:
                continue
            if tag == 'tagblock':
                blocks[prefix + '/' + name] = ch.get('elementSize')
                walk(ch, prefix + '/' + name)
            elif ch.get('offset') is not None and not name.lower().startswith('unknown'):
                fields[prefix + '/' + name] = tag

    root = ET.parse(path).getroot()
    walk(root, '')
    return blocks, fields, root.get('baseSize'), os.path.basename(os.path.dirname(path))


def cards_using(group, field_names, game):
    """{field: [card names]} for halo.json cards that target this tag group.

    `game` filters to cards actually offered there, so a field only Halo 1 uses is not
    reported as broken in Reach."""
    data = json.load(open(HALO_JSON, encoding='utf-8'))
    out = {}

    def games_of(node):
        g = node.get('games') or node.get('game')
        if g is None:
            return None
        return [g] if isinstance(g, str) else list(g)

    def visit(node, owner):
        if isinstance(node, dict):
            tag = node.get('tag')
            tags = [tag] if isinstance(tag, str) else (
                list(tag.values()) if isinstance(tag, dict) else [])
            if tags and any(str(t).startswith(group + ' ') for t in tags):
                gs = games_of(node)
                if gs is None or game in gs:
                    for t in node.get('targets') or []:
                        if not isinstance(t, dict):
                            continue
                        f = t.get('field')
                        names = [f] if isinstance(f, str) else (
                            list(f.values()) if isinstance(f, dict) else [])
                        for n in names:
                            if n in field_names:
                                out.setdefault(n, set()).add(owner)
            for k, v in node.items():
                visit(v, owner or str(k))
        elif isinstance(node, list):
            for v in node:
                visit(v, owner)

    for section in ('Player Modifiers', 'Enemy modifiers', 'Equipment'):
        for grp, entries in (data.get(section) or {}).items():
            if isinstance(entries, dict):
                for name, mods in entries.items():
                    visit(mods, name)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--group', default='weap')
    ap.add_argument('--from', dest='a', default='Halo 3', choices=sorted(SUBDIRS))
    ap.add_argument('--to', dest='b', default='Halo Reach', choices=sorted(SUBDIRS))
    ap.add_argument('--removed-only', action='store_true')
    ap.add_argument('--added-only', action='store_true')
    o = ap.parse_args()

    ab, af, asz, asub = load(o.a, o.group)
    bb, bf, bsz, bsub = load(o.b, o.group)
    print("%s %s (%s, baseSize %s, %d blocks, %d fields)"
          % (o.a, o.group, asub, asz, len(ab), len(af)))
    print("%s %s (%s, baseSize %s, %d blocks, %d fields)"
          % (o.b, o.group, bsub, bsz, len(bb), len(bf)))

    new_blocks = [b for b in bb if b not in ab]
    gone_blocks = [b for b in ab if b not in bb]

    if not o.removed_only:
        print("\n=== BLOCKS new in %s (%d) ===" % (o.b, len(new_blocks)))
        for b in sorted(new_blocks):
            kids = [f for f in bf if f.startswith(b + '/')]
            print("   %-56s esz=%-8s %d field(s)" % (b, bb[b], len(kids)))

        added = {f: t for f, t in bf.items() if f not in af}
        # A field inside a wholly-new block is already covered by the block line.
        loose = {f: t for f, t in added.items()
                 if not any(f.startswith(b + '/') for b in new_blocks)}
        print("\n=== FIELDS new in %s, inside blocks %s already had (%d) ==="
              % (o.b, o.a, len(loose)))
        bygrp = {}
        for f, t in loose.items():
            grp, _, leaf = f.rpartition('/')
            bygrp.setdefault(grp or '(root)', []).append((leaf, t))
        for grp in sorted(bygrp):
            print("\n   %s" % (grp or '(root)'))
            for leaf, t in sorted(bygrp[grp]):
                print("        %-10s %s" % (t, leaf))

    if not o.added_only:
        gone = [f for f in af if f not in bf
                and not any(f.startswith(b + '/') for b in gone_blocks)]
        print("\n=== BLOCKS gone since %s (%d) ===" % (o.a, len(gone_blocks)))
        for b in sorted(gone_blocks):
            print("   %s" % b)
        print("\n=== FIELDS gone since %s (%d) ===" % (o.a, len(gone)))
        leaves = {f.rpartition('/')[2] for f in gone}
        used = cards_using(o.group, leaves, o.b)
        for f in sorted(gone):
            leaf = f.rpartition('/')[2]
            who = used.get(leaf)
            print("   %-58s %s" % (f, ('USED BY: ' + ', '.join(sorted(who))) if who else ''))
        hurt = sorted({c for s in used.values() for c in s})
        print("\n   cards offered in %s that name a removed field: %s"
              % (o.b, ', '.join(hurt) if hurt else 'none'))


if __name__ == '__main__':
    main()
