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

AUDIT MODE (--chain): walk every consecutive pair of games that has the group and print
only what needs a decision -- fields a later game ADDED that no card offered in that game
names, and fields it REMOVED that a card offered there still names. This is the
between-games card audit; it is what would have raised Brace Grenade Chance and the
defensive-cover trio (ODST -> Reach) and Search Distance (Halo 2 -> Halo 3) long before
they were noticed by hand. Halo 1 keeps characters in actr/actv, so `char` starts at
Halo 2.

    python sprint_toolkit/plugin_diff.py --chain --group char --group weap --group proj
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import assembly_plugins                              # noqa: E402

# Groups whose NEW-field side the user has decided not to build from, so a sweep does
# not keep re-proposing the same work. `matg` is the standing one: the ODST -> Reach
# diff surfaces big new blocks (Co-Op Difficulty 33 fields, Damage 15, Active Camo 11,
# Default Player Traits 35 with sub-blocks) and the answer has been "ignore" every time
# it has come up, most recently 2026-09-03.
#
# This suppresses the ADDED side only. The REMOVED side still reports, because that is
# breakage rather than a proposal -- a card naming a field the later game dropped is a
# bug whatever anyone decided about new work.
ADDED_SIDE_IGNORED = {
    'matg': 'user has repeatedly said to ignore the new matg fields',
}

PLUGINS = assembly_plugins.plugins_dir()
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')

SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST'],
           'Halo Reach': ['ReachMCC', 'Reach'],
           'Halo 4': ['Halo4MCC', 'Halo4']}
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


def _field_names_for(f, game):
    """The field name(s) a target resolves to in `game`, by the enhancer's own rules:
    exact game, ODST falls back to Halo 3, then `default`, then the nearest EARLIER game."""
    if isinstance(f, str):
        return [f]
    if not isinstance(f, dict):
        return []
    for g in [game] + (['Halo 3'] if game == 'Halo 3: ODST' else []):
        if g in f:
            return [f[g]] if f[g] else []
    if 'default' in f:
        return [f['default']] if f['default'] else []
    order = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
    if game in order:
        for g in reversed(order[:order.index(game)]):
            if g in f:
                return [f[g]] if f[g] else []
    return []


def cards_using(group, field_names, game):
    """{field: [card names]} for halo.json cards that target this tag group.

    `game` filters to cards actually offered there, so a field only Halo 1 uses is not
    reported as broken in Reach."""
    data = json.load(open(HALO_JSON, encoding='utf-8'))
    out = {}

    def offered_in(node, literal=False):
        """Is this card offered in `game`? Mirrors halo_enhancer's own gating: an
        explicit game list, MINUS skip_games, with ODST inheriting Halo 3.

        skip_games was ignored here at first, which reported `Stun Time` and
        `Stun Penalty` as broken in Reach when both already carry
        skip_games: ["Halo Reach"] -- i.e. the exact gating this check exists to
        recommend was read as its absence."""
        g = node.get('games') or node.get('game')
        skip = node.get('skip_games')
        skip = [skip] if isinstance(skip, str) else list(skip or [])
        want = {game}
        if game == 'Halo 3: ODST' and not literal:
            # ODST inherits Halo 3 CARDS -- but a TARGET's games list is matched
            # literally by the enhancer (target_applies), which is exactly how the ODST
            # fixes are pinned; inheriting there reported them as still broken.
            want.add('Halo 3')
        if any(s in want for s in skip):
            return False
        if g is None:
            return True
        gs = [g] if isinstance(g, str) else list(g)
        return any(x in want for x in gs)

    def visit(node, owner):
        if isinstance(node, dict):
            tag = node.get('tag')
            tags = [tag] if isinstance(tag, str) else (
                list(tag.values()) if isinstance(tag, dict) else [])
            if tags and any(str(t).startswith(group + ' ') for t in tags):
                if offered_in(node):
                    # `targets` is a list, or a dict keyed by game -- the game-keyed
                    # form was skipped entirely before, so cards written that way
                    # (Stun Time on hlmt) contributed nothing to this check.
                    tg = node.get('targets')
                    rows = []
                    if isinstance(tg, list):
                        rows = tg
                    elif isinstance(tg, dict):
                        for gk, v in tg.items():
                            if gk == game or (game == 'Halo 3: ODST' and gk == 'Halo 3'):
                                rows += v if isinstance(v, list) else [v]
                    for t in rows:
                        if not isinstance(t, dict):
                            continue
                        # A TARGET carries its own games/skip_games, and that is where
                        # this kind of breakage is normally fixed -- Brute's
                        # `Vitality Fraction Bubbleshield` and Engineer's
                        # `Shield Boost Strength` are both already pinned to ODST while
                        # the card itself stays offered in Reach. Reading only the card
                        # reported all three as broken when none were.
                        if not offered_in(t, literal=True):
                            continue
                        # A per-game field dict names DIFFERENT fields in different
                        # games; only the one this game resolves to counts. Taking every
                        # value reported renamed fields (ODST's homing error radius,
                        # Invisible Time -> Cooldown Time) as still in use.
                        names = _field_names_for(t.get('field'), game)
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


NUMERIC_KINDS = ('float', 'int', 'uint', 'range', 'degree', 'real', 'short')
ORDER = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']


def _has(game, group):
    return any(os.path.isfile(os.path.join(PLUGINS, sub, group + '.xml'))
               for sub in SUBDIRS[game])


def chain_audit(groups):
    """Consecutive-game diff per group: uncarded ADDED fields, carded REMOVED fields."""
    total_added = total_broken = 0
    for group in groups:
        games = [g for g in ORDER if _has(g, group)]
        print()
        print('##### %s: %s' % (group, ' -> '.join(games)))
        for a, b in zip(games, games[1:]):
            _ab, af, _asz, _ = load(a, group)
            _bb, bf, _bsz, _ = load(b, group)
            # Only values a card can drive: a new tagRef, stringid or flags word is a
            # rename or a hookup, not a field to author a card for.
            added_leaves = {f.rpartition('/')[2]: f for f, kind in bf.items()
                            if f not in af and kind.startswith(NUMERIC_KINDS)}
            gone = [f for f in af if f not in bf]
            b_leaves = {f.rpartition('/')[2] for f in bf}
            really_gone = {f.rpartition('/')[2]: f for f in gone
                           if f.rpartition('/')[2] not in b_leaves}
            carded_new = cards_using(group, set(added_leaves), b)
            uncarded = {leaf: f for leaf, f in added_leaves.items()
                        if leaf not in carded_new and leaf not in _a_leaves(af)}
            broken = cards_using(group, set(really_gone), b)
            if group in ADDED_SIDE_IGNORED:
                uncarded = {}
            print()
            print('  %s -> %s: %d field(s) added, %d uncarded; %d removed, %d still carded'
                  % (a, b, len(added_leaves), len(uncarded), len(really_gone), len(broken)))
            byblk = {}
            for leaf, f in uncarded.items():
                byblk.setdefault(f.rpartition('/')[0] or '(root)', []).append(leaf)
            for blk in sorted(byblk):
                print('     + %-44s %s' % (blk[:44], ', '.join(sorted(byblk[blk]))))
            for leaf, who in sorted(broken.items()):
                print('     - %-44s USED BY: %s' % (really_gone[leaf][:44], ', '.join(sorted(who))))
            total_added += len(uncarded)
            total_broken += len(broken)
    print()
    print('%d uncarded added field(s), %d removed field(s) still named by a card'
          % (total_added, total_broken))


def _a_leaves(af):
    """Leaf names the earlier game already had anywhere -- a MOVED field is not new."""
    return {f.rpartition('/')[2] for f in af}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--group', default='weap')
    ap.add_argument('--from', dest='a', default='Halo 3', choices=sorted(SUBDIRS))
    ap.add_argument('--to', dest='b', default='Halo Reach', choices=sorted(SUBDIRS))
    ap.add_argument('--removed-only', action='store_true')
    ap.add_argument('--added-only', action='store_true')
    ap.add_argument('--chain', action='store_true',
                    help='audit every consecutive game pair (see the module docstring)')
    ap.add_argument('--groups', nargs='*',
                    help='with --chain: the tag groups to walk (default: char weap proj eqip)')
    o = ap.parse_args()
    if o.chain:
        chain_audit(o.groups or ['char', 'weap', 'proj', 'eqip'])
        return

    ab, af, asz, asub = load(o.a, o.group)
    bb, bf, bsz, bsub = load(o.b, o.group)
    print("%s %s (%s, baseSize %s, %d blocks, %d fields)"
          % (o.a, o.group, asub, asz, len(ab), len(af)))
    print("%s %s (%s, baseSize %s, %d blocks, %d fields)"
          % (o.b, o.group, bsub, bsz, len(bb), len(bf)))

    new_blocks = [b for b in bb if b not in ab]
    gone_blocks = [b for b in ab if b not in bb]

    skip_added = ADDED_SIDE_IGNORED.get(o.group) and not o.added_only
    if skip_added:
        # Named explicitly rather than silently dropped: the reader should know the
        # added side exists and was a decision, not that the diff found nothing.
        print("\n=== %d block(s) and %d field(s) new in %s: NOT LISTED ==="
              % (len(new_blocks),
                 len([f for f in bf if f not in af]), o.b))
        print("   %s" % ADDED_SIDE_IGNORED[o.group])
        print("   --added-only overrides this.")

    if not o.removed_only and not skip_added:
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
        # MOVED is not REMOVED. Reach relocated `Full Speed Multiplier` from
        # Player Control to Player Information; keyed by full path that reads as a
        # deletion, and the Reach Sprint Speed card -- which already names the new
        # block and works -- was reported as broken. A leaf name that still exists
        # somewhere in the later tag is a move, and cards are matched by leaf name,
        # so counting moves as breakage is a guaranteed false positive.
        # ...but only for leaf names distinctive enough to mean something. `Name` sits
        # in 37 blocks of Reach's scnr and `Flags` in 50, so a bare name match there is
        # noise, not a move. Anything above this many homes is treated as a common
        # label and left in the removed list.
        COMMON_LEAF = 6
        b_leaves = {}
        for f in bf:
            b_leaves.setdefault(f.rpartition('/')[2], []).append(f)
        moved = {}
        for f in gone:
            where = b_leaves.get(f.rpartition('/')[2]) or []
            if 0 < len(where) <= COMMON_LEAF:
                moved[f] = where
        really_gone = [f for f in gone if f not in moved]

        if moved:
            print("\n=== FIELDS moved to another block in %s (%d) ==="
                  % (o.b, len(moved)))
            for f in sorted(moved):
                print("   %-52s -> %s" % (f, ', '.join(sorted(moved[f]))))

        print("\n=== FIELDS gone since %s (%d) ===" % (o.a, len(really_gone)))
        leaves = {f.rpartition('/')[2] for f in really_gone}
        used = cards_using(o.group, leaves, o.b)
        for f in sorted(really_gone):
            leaf = f.rpartition('/')[2]
            who = used.get(leaf)
            print("   %-58s %s" % (f, ('USED BY: ' + ', '.join(sorted(who))) if who else ''))
        hurt = sorted({c for s in used.values() for c in s})
        print("\n   cards offered in %s that name a removed field: %s"
              % (o.b, ', '.join(hurt) if hurt else 'none'))


if __name__ == '__main__':
    main()
