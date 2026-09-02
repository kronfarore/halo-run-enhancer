r"""generic_census.py -- who actually inherits from `ai\generic`, per field, per game.

A card on a specific enemy sometimes has to aim at the SHARED base instead of the
enemy, because the enemy does not define the field. That is only acceptable while the
enemy is in the majority -- if most characters inherit the field, editing the base is
close enough to editing "the AI". Once an enemy defines the field itself, the same card
silently stops being about that enemy, and once MOST enemies define it, the base edit
is a card about almost nobody.

Which side of that line a field falls on CHANGES BETWEEN GAMES: Reach moved a dozen
fields from inherited to defined (see coverage_audit's Reach section). This tool makes
that measurable rather than assumed, and gives the numbers a per-game card description
should be written from -- "in Halo 2 this edits the shared AI base, so it also moves
the Flood" is only true while the census says so.

For each field `ai\generic` actively uses (non-zero there), per game:
  * TYPES   how many enemy families inherit it vs define their own;
  * VARIANTS  the same count over every tag of every family, since a family often
    splits -- `grunt` inherits while `grunt_ultra` does not;
  * VALUES  whether a definer merely repeats generic's number (harmless to inherit)
    or genuinely differs (where the base edit really misses).

    python sprint_toolkit/generic_census.py
    python sprint_toolkit/generic_census.py --game "Halo Reach" --min-definers 1
    python sprint_toolkit/generic_census.py --field "Rate Of Fire" --verbose
"""
import argparse
import collections
import contextlib
import io
import json
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_enhancer as he                                        # noqa: E402
import halo_patch as hp                                           # noqa: E402
import coverage_audit as ca                                       # noqa: E402

S = chr(92)
GENERIC = 'ai' + S + 'generic'
# The families worth reporting: one row per enemy the game actually fields, not per
# tag. `coverage_audit` already knows how a card's tag maps to an enemy.
CASES = ca.CASES


def families(db, game, maps, plug):
    """{enemy: [(tag path, base, map)]} for every enemy with tags in this game."""
    out = collections.defaultdict(list)
    seen = collections.defaultdict(set)
    for mp, m in maps:
        for enemy in sorted(db.enemy_mods):
            for pat in ca.enemy_tag_patterns(db, enemy):
                for tp, base in m.find_tags('char', pat):
                    if tp in seen[enemy] or tp.endswith(GENERIC):
                        continue
                    seen[enemy].add(tp)
                    out[enemy].append((tp, base, m))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', action='append',
                    help='only this game (repeatable)')
    ap.add_argument('--field', help='only this field')
    ap.add_argument('--min-definers', type=int, default=1,
                    help='only fields at least this many enemy families define '
                         '(default 1; 0 shows everything generic sets)')
    ap.add_argument('--verbose', action='store_true',
                    help='name every variant, not just the counts')
    ap.add_argument('--all-fields', action='store_true',
                    help='the raw census over every field generic sets (264 rows in '
                         'Reach, most of them vehicle steering nobody cards). The '
                         'default is the card-shaped view: only the fields a card '
                         'aims at the shared base, which is where the minority rule '
                         'is actually decided')
    args = ap.parse_args()

    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    cfg = json.load(io.open(os.path.join(TOOL, 'settings.json'), encoding='utf-8'))

    for game, subs, folder in CASES:
        if args.game and game not in args.game:
            continue
        paths = ca.game_maps(folder)
        if not paths:
            print('%s: no maps under %s' % (game, folder))
            continue
        plug = hp.PluginRegistry(cfg['assembly_plugins_dir'], subs).get('char')
        if plug is None:
            continue
        print('\n%s: reading %d level(s)…' % (game, len(paths)), flush=True)
        maps = []
        for mp in paths:
            try:
                maps.append((mp, hp.open_map(mp, game)))
            except Exception:
                pass
        fam = families(db, game, maps, plug)

        # what generic itself sets
        gen = {}
        for _mp, m in maps:
            for tp, base in m.find_tags('char', GENERIC):
                for f, b in ca._plugin_fields(plug):
                    if f in gen or not ca._interesting(f):
                        continue
                    try:
                        v = m.read_tag_field(base, f, plug, b, 'all', 0)
                    except Exception:
                        continue
                    if v:
                        gen[f] = (round(v, 4) if isinstance(v, float) else v, b)
        if args.field:
            gen = {k: v for k, v in gen.items() if k.lower() == args.field.lower()}
        print('   ai%sgeneric actively sets %d field(s)' % (S, len(gen)))

        # --- the card-shaped view: every card that aims at the shared base ----------
        if not args.all_fields:
            print('   %-11s %-24s %-30s %s'
                  % ('enemy', 'card', 'field', 'this enemy in this game'))
            print('   ' + '-' * 100)
            shown = 0
            for enemy in sorted(fam):
                for mod in (db.enemy_mods.get(enemy) or []):
                    if not db._game_ok(mod, game):
                        continue
                    tag = mod.get('tag')
                    tag = he.resolve_gamed(tag, game, db.get_games()) \
                        if isinstance(tag, dict) else tag
                    base_aimed = (isinstance(tag, str)
                                  and tag.split(' ', 1)[-1].strip() == GENERIC)
                    ts = mod.get('targets')
                    ts = he.resolve_gamed(ts, game, db.get_games()) \
                        if isinstance(ts, dict) else ts
                    for t in ts or []:
                        if not isinstance(t, dict) or not he.target_applies(t, game):
                            continue
                        own = t.get('tag')
                        own = he.resolve_gamed(own, game, db.get_games()) \
                            if isinstance(own, dict) else own
                        aimed = (base_aimed if not isinstance(own, str)
                                 else own.split(' ', 1)[-1].strip() == GENERIC)
                        if not aimed:
                            continue
                        f = t.get('field')
                        f = he.resolve_gamed(f, game, db.get_games()) \
                            if isinstance(f, dict) else f
                        if not isinstance(f, str):
                            continue
                        if args.field and f.lower() != args.field.lower():
                            continue
                        blk = t.get('block')
                        blk = he.resolve_gamed(blk, game, db.get_games()) \
                            if isinstance(blk, dict) else blk
                        fld = plug.find(f, blk)
                        if not fld:
                            continue
                        inh = dfn = 0
                        for tp, tbase, m in fam[enemy]:
                            try:
                                ok = bool(m.follow_all(tbase, fld['block_offsets'],
                                                       fld.get('block_sizes'), 'all'))
                            except Exception:
                                ok = False
                            dfn += 1 if ok else 0
                            inh += 0 if ok else 1
                        # A card may pair the base edit with a second target aimed at
                        # the enemy's own tags, precisely to cover the variants that
                        # define the field. That is the fix, not the problem, so do
                        # not report it as a miss.
                        redirected = False
                        for t2 in ts or []:
                            if not isinstance(t2, dict) or t2 is t:
                                continue
                            f2 = he.resolve_gamed(t2.get('field'), game,
                                                  db.get_games()) \
                                if isinstance(t2.get('field'), dict) else t2.get('field')
                            o2 = t2.get('tag')
                            o2 = he.resolve_gamed(o2, game, db.get_games()) \
                                if isinstance(o2, dict) else o2
                            if (f2 == f and isinstance(o2, str)
                                    and o2.split(' ', 1)[-1].strip() != GENERIC
                                    and he.target_applies(t2, game)):
                                redirected = True
                                break
                        verdict = ('reaches all %d' % inh if not dfn else
                                   ('misses %d of %d, but the card redirects those'
                                    % (dfn, dfn + inh) if redirected else
                                    ('REACHES NONE (%d define it)' % dfn if not inh
                                     else 'MISSES %d of %d' % (dfn, dfn + inh))))
                        print('   %-11s %-24s %-30s %s'
                              % (enemy, mod.get('name'), f, verdict))
                        shown += 1
            if not shown:
                print('   (no card aims at the shared base in this game)')
            continue

        rows = []
        for field, (gval, block) in sorted(gen.items()):
            inherit_t, define_t, same_v, diff_v = [], [], 0, 0
            variants_i = variants_d = 0
            detail = []
            for enemy, tags in sorted(fam.items()):
                defs = []
                for tp, base, m in tags:
                    try:
                        got = m.read_tag_field(base, field, plug, block, 'all', 0)
                    except Exception:
                        got = None
                    # a populated block is a DEFINITION even when the value is 0 --
                    # defining overrides the inheritance, so 0 means "none of this
                    # behaviour", not "unset"
                    populated = False
                    fld = plug.find(field, block)
                    if fld:
                        try:
                            populated = bool(m.follow_all(base, fld['block_offsets'],
                                                          fld.get('block_sizes'),
                                                          'all'))
                        except Exception:
                            populated = False
                    if populated:
                        defs.append((tp.rsplit(S, 1)[-1], got))
                if defs:
                    define_t.append(enemy)
                    variants_d += len(defs)
                    variants_i += len(tags) - len(defs)
                    for _leaf, v in defs:
                        if v == gval:
                            same_v += 1
                        else:
                            diff_v += 1
                    if args.verbose:
                        detail.append('      %-12s %s' % (enemy, defs[:6]))
                else:
                    inherit_t.append(enemy)
                    variants_i += len(tags)
            if len(define_t) < args.min_definers:
                continue
            rows.append((field, gval, inherit_t, define_t, variants_i, variants_d,
                         same_v, diff_v, detail))

        print('   %-34s %-8s %-9s %-11s %s'
              % ('field', 'generic', 'families', 'variants', 'definers repeat/differ'))
        print('   ' + '-' * 96)
        for (field, gval, inh, dfn, vi, vd, same, diff, detail) in rows:
            verdict = ('BASE EDIT OK' if len(dfn) <= len(inh) / 2
                       else ('MIXED' if dfn and inh else 'BASE EDIT REACHES NOBODY'))
            print('   %-34s %-8s %d inh/%d def  %3d inh/%3d def  %d repeat / %d differ'
                  '   %s'
                  % (field, gval, len(inh), len(dfn), vi, vd, same, diff, verdict))
            if args.verbose:
                print('      inherits: %s' % (', '.join(inh) or '-'))
                for d in detail:
                    print(d)
    return 0


if __name__ == '__main__':
    sys.exit(main())
