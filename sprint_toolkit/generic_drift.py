r"""generic_drift.py -- which enemy cards changed meaning between two games.

`generic_census.py` answers "does this card still reach this enemy?" one game at a time.
That is the right question but the wrong axis: a card is written once, for the game it
was authored in, and then INHERITED forward. What breaks it is the engine moving a field
between the shared `ai\generic` base and the species' own tag, and nothing in a
single-game view says that a value moved.

So this walks CONSECUTIVE games and reports the two drifts:

  TO SPECIES  the enemy inherited the field in the older game and DEFINES it in the
              newer one. A card aimed at `ai\generic` was about that enemy and quietly
              stopped being -- it now edits a base the enemy no longer reads.
  TO GENERIC  the enemy defined it in the older game and INHERITS it in the newer one.
              A card aimed at the enemy's own tags now writes into a block with no
              elements, which is the silent no-op class: the patch reports success and
              the value never existed.

Only fields some card actually names are considered, and each drift is scored by
whether a card is really affected -- "12 fields moved" and "one card is now wrong" are
very different headlines, the same distinction plugin_diff draws.

    python sprint_toolkit/generic_drift.py
    python sprint_toolkit/generic_drift.py --pair "Halo Reach" "Halo 4"
    python sprint_toolkit/generic_drift.py --all        # include unaffected drifts
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
_R = os.path.dirname(TOOL)
# The same map subsets inherit_audit uses, and for the same reason: one map can only
# UNDER-report, since an enemy it does not field is invisible, and a species counts as
# defining a block if it defines it on ANY of these. Reading every map instead would
# multiply the runtime for a handful of extra variants.
CASES = [
    ('Halo 2', ['Halo2MCC', 'Halo2'],
     [os.path.join(_R, 'halo2', 'h2_maps_win64_dx11', n + '.map')
      for n in ('07a_highcharity', '03a_oldmombasa', '05a_deltaapproach')]),
    ('Halo 3', ['Halo3MCC', 'Halo3'],
     [os.path.join(_R, 'halo3', 'maps', n + '.map')
      for n in ('030_outskirts', '050_floodvoice', '120_halo')]),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'],
     [os.path.join(_R, 'halo3odst', 'maps', n + '.map')
      for n in ('l300', 'sc110', 'sc140')]),
    ('Halo Reach', ['ReachMCC', 'Reach'],
     [os.path.join(_R, 'haloreach', 'maps', n + '.map')
      for n in ('m10', 'm30', 'm35', 'm50', 'm70')]),
    ('Halo 4', ['Halo4MCC', 'Halo4'],
     [os.path.join(_R, 'halo4', 'maps', n + '.map')
      for n in ('m60_rescue', 'm70_liftoff', 'm80_delta')]),
]


#: (game, enemy, card) already recorded as dead in deadcards' VERIFIED table. A drift
#: that lands on one of these is not news -- it is the finding that PUT it there.
def _verified():
    # deadcards runs its whole sweep at import time, so it is imported here and muted
    # -- all this needs is its table, not another audit's output in the middle of ours.
    with contextlib.redirect_stdout(io.StringIO()):
        import deadcards
    out = set()
    for (game, path, _tag) in deadcards.VERIFIED:
        parts = [p.strip() for p in path.split('/')]
        if len(parts) >= 3:
            out.add((game, parts[-2], parts[-1]))
    return out


VERIFIED = _verified()


def seeds(mod, game, games, block):
    """True if the card SEEDS this block for this game (init_defaults). An empty block
    is then the expected state, not a miss -- the patcher grows or copies it before
    writing, which is the whole point of the seeder."""
    ini = gamed(mod.get('init_defaults'), game, games)
    if not isinstance(ini, dict):
        return False
    b = ini.get('block')
    return bool(ini.get('grow') or b) and (b is None or block is None or b == block)


def gamed(v, game, games):
    return he.resolve_gamed(v, game, games) if isinstance(v, dict) else v


def card_rows(db, game):
    """Every (enemy, card name, field, block, aim) a card declares for this game.

    `aim` is 'generic' when the row lands on the shared AI base and 'species' when it
    lands on the enemy's own tags -- the distinction the whole audit turns on. A row's
    own `tag` wins over the card's, exactly as the patcher resolves it.
    """
    games = db.get_games()
    out = []
    pools = [db.enemy_mods, getattr(db, 'boss_mods', {})]
    for pool in pools:
        for enemy, mods in (pool or {}).items():
            for mod in mods or []:
                if not db._game_ok(mod, game) or he.mod_ignored(mod):
                    continue
                # The two enemies the enhancer already refuses to patch in a game
                # where they are not enemies. Without this the audit reports the
                # Flood all through ODST and the allied Elites all through Halo 3,
                # neither of which any run can offer.
                if he._is_absent_flood_mod(mod, game):
                    continue
                if (he.CONFIG.get('ignore_elite_in_h3')
                        and he._is_allied_elite_mod(mod, game)):
                    continue
                ctag = gamed(mod.get('tag'), game, games)
                ts = gamed(mod.get('targets'), game, games) or []
                for t in ts:
                    if not isinstance(t, dict) or not he.target_applies(t, game):
                        continue
                    tag = gamed(t.get('tag'), game, games) or ctag
                    f = gamed(t.get('field'), game, games)
                    if not isinstance(f, str) or not isinstance(tag, str):
                        continue
                    if not tag.startswith('char '):
                        continue
                    aim = ('generic' if tag.split(' ', 1)[-1].strip() == GENERIC
                           else 'species')
                    blk = gamed(t.get('block'), game, games)
                    out.append((enemy, mod.get('name'), f, blk, aim,
                                seeds(mod, game, games, blk)))
    return out


def defines(db, game, subs, paths, rows):
    """{(enemy, field, block): (definers, inheritors)} over this game's maps.

    A tag DEFINES a field when the block chain leading to it actually has elements --
    the same test the patcher's write does, so "defines" here means "a write lands".
    """
    plug = hp.PluginRegistry(json.load(io.open(os.path.join(TOOL, 'settings.json'),
                                               encoding='utf-8'))
                             ['assembly_plugins_dir'], subs).get('char')
    if plug is None:
        return {}, None
    maps = []
    for p in paths:
        try:
            maps.append(hp.open_map(p, game))
        except Exception:
            pass
    tags = collections.defaultdict(dict)          # enemy -> {tag path: base}
    for m in maps:
        for enemy in {r[0] for r in rows}:
            for pat in ca.enemy_tag_patterns(db, enemy):
                for tp, base in m.find_tags('char', pat):
                    if tp.endswith(GENERIC) or tp in tags[enemy]:
                        continue
                    tags[enemy][tp] = (base, m)
    out = {}
    for enemy, _card, f, blk, _aim, _seed in rows:
        key = (enemy, f, blk)
        if key in out:
            continue
        fld = plug.find(f, blk)
        if not fld:
            continue
        dfn = inh = 0
        for _tp, (base, m) in tags[enemy].items():
            try:
                ok = bool(m.follow_all(base, fld['block_offsets'],
                                       fld.get('block_sizes'), 'all'))
            except Exception:
                ok = False
            dfn += 1 if ok else 0
            inh += 0 if ok else 1
        if dfn or inh:
            out[key] = (dfn, inh)
    return out, plug


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pair', nargs=2, metavar=('OLDER', 'NEWER'),
                    help='only this pair of games')
    ap.add_argument('--all', action='store_true',
                    help='also list drifts no card is aimed at')
    args = ap.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    order = [c[0] for c in CASES]
    state = {}
    for game, subs, paths in CASES:
        if args.pair and game not in args.pair:
            continue
        rows = card_rows(db, game)
        d, _plug = defines(db, game, subs, paths, rows)
        state[game] = (rows, d)
        print('%-13s %4d card row(s) on char, %4d (enemy, field) pair(s) measured'
              % (game, len(rows), len(d)))

    for older, newer in zip(order, order[1:]):
        if older not in state or newer not in state:
            continue
        print()
        print('=' * 78)
        print('%s  ->  %s' % (older, newer))
        (orows, od), (nrows, nd) = state[older], state[newer]
        aim_new = {}
        for enemy, card, f, blk, aim, seed in nrows:
            aim_new.setdefault((enemy, f, blk), set()).add((card, aim, seed))
        found = 0
        for key, (odfn, oinh) in sorted(od.items()):
            if key not in nd:
                continue
            ndfn, ninh = nd[key]
            o_defines, n_defines = odfn > 0, ndfn > 0
            if o_defines == n_defines:
                continue
            enemy, f, blk = key
            cards = sorted(aim_new.get(key, ()))
            drift = 'TO SPECIES' if n_defines else 'TO GENERIC'
            # A drift only BREAKS a card when the card aims the way the newer game no
            # longer supports: generic-aimed after the value moved onto the species,
            # or species-aimed after it moved onto the base.
            # ...and a species-aimed card that SEEDS the block is doing the fix, not
            # suffering the drift.
            broken = [c for c, aim, seed in cards
                      if (aim == 'generic') == n_defines and not seed]
            known = [c for c in broken if (newer, enemy, c) in VERIFIED]
            broken = [c for c in broken if c not in known]
            if not broken and not (args.all or known):
                continue
            found += 1
            print('   %-10s %-11s %-28s %s'
                  % (drift, enemy, f, '%d def/%d inh -> %d def/%d inh'
                     % (odfn, oinh, ndfn, ninh)))
            for c, aim, seed in sorted(cards):
                mark = ''
                if (aim == 'generic') == n_defines and not seed:
                    mark = ('  <-- already recorded as dead'
                            if (newer, enemy, c) in VERIFIED else '  <-- now wrong')
                elif seed:
                    mark = '  (seeds the block itself)'
                print('        card %-30s aims at %-8s%s' % (c, aim, mark))
        if not found:
            print('   nothing%s' % ('' if args.all else ' a card is aimed at'))


if __name__ == '__main__':
    main()
