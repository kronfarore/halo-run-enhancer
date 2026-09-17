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

EVERY campaign map is read (2026-09-17). The old fixed 3-5 map subsets missed variants
-- Halo 3's skipped Sierra 117, where the Brutes define their grenades. A variant that
appears on fewer than --min-maps maps is left out of the verdict as a one-off, unless
that enemy has no other variant in the game.

A row is matched across games by (enemy, card, target position), not by field name, so
a renamed field (Halo 1 `Melee Attack Delay` -> Halo 2 `Melee Attack Delay Timer`) is
still followed.

HALO 1 is different: there is no character inheritance. Cards aim at `actr` (the actor,
shared by all its variants) or `actv` (one variant), and both are flat structs that
always carry every field, so an H1 enemy DEFINES every field its tags have. Halo 1 ->
Halo 2 therefore only ever reports TO GENERIC: a value the H1 card set on the species
that Halo 2 leaves to `ai\generic`.

    python sprint_toolkit/generic_drift.py
    python sprint_toolkit/generic_drift.py --pair "Halo Reach" "Halo 4"
    python sprint_toolkit/generic_drift.py --all            # include unaffected drifts
    python sprint_toolkit/generic_drift.py --min-maps 1     # count one-off variants too
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
H1_GROUPS = ('actr', 'actv')
CASES = ([('Halo 1', ['Halo1MCC', 'Halo1'], os.path.join(_R, 'halo1', 'maps'))]
         + [(c[0], c[1], c[2]) for c in ca.CASES])


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
    ini = mod.get('init_defaults')
    # init_defaults is itself a dict ({tag, block, grow}); it is only per-game when its
    # keys are games. Resolving the plain form as a game map returned None, so every
    # boss seeder (Honor Guard, Specops Commander, Knight Commander) read as unseeded.
    if isinstance(ini, dict) and any(k in games or k == 'default' for k in ini):
        ini = gamed(ini, game, games)
    if not isinstance(ini, dict):
        return False
    b = ini.get('block')
    return bool(ini.get('grow') or b) and (b is None or block is None or b == block)


def gamed(v, game, games):
    return he.resolve_gamed(v, game, games) if isinstance(v, dict) else v


Row = collections.namedtuple('Row', 'key enemy card field block aim seed group pats')


def card_rows(db, game):
    """Every Row a card declares for this game.

    `aim` is 'generic' when the row lands on the shared AI base and 'species' when it
    lands on the enemy's own tags -- the distinction the whole audit turns on. A row's
    own `tag` wins over the card's, exactly as the patcher resolves it. `key` is what
    matches the row in the neighbouring game: the target's position when the card's
    target list is shared by every game, its field name when the list itself is per game.
    """
    games = db.get_games()
    groups = H1_GROUPS if game == 'Halo 1' else ('char',)
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
                raw = mod.get('targets')
                per_game_list = isinstance(raw, dict)
                ts = gamed(raw, game, games) or []
                for i, t in enumerate(ts):
                    if not isinstance(t, dict) or not he.target_applies(t, game):
                        continue
                    tag = gamed(t.get('tag'), game, games) or ctag
                    f = gamed(t.get('field'), game, games)
                    if not isinstance(f, str) or not isinstance(tag, str):
                        continue
                    group, _sp, pats = tag.partition(' ')
                    if group not in groups:
                        continue
                    pats = [p.strip() for p in pats.split(' & ') if p.strip()]
                    aim = ('generic' if group == 'char' and pats == [GENERIC]
                           else 'species')
                    blk = gamed(t.get('block'), game, games)
                    key = (enemy, mod.get('name'), ('field', f) if per_game_list else i)
                    out.append(Row(key, enemy, mod.get('name'), f, blk, aim,
                                   seeds(mod, game, games, blk), group, pats))
    return out


def measure(db, game, subs, folder, wants, min_maps):
    """{(enemy, group, field, block): (definers, inheritors, one_offs_used)} over EVERY
    map of the game.

    A tag DEFINES a field when the block chain leading to it actually has elements --
    the same test the patcher's write does, so "defines" here means "a write lands". In
    Halo 1 a found actr/actv tag always defines (flat structs, no inheritance).
    `wants` maps (enemy, group) to the tag patterns to look under.
    """
    reg = hp.PluginRegistry(json.load(io.open(os.path.join(TOOL, 'settings.json'),
                                             encoding='utf-8'))
                            ['assembly_plugins_dir'], subs)
    plugs = {g: reg.get(g) for g in {g for (_e, g) in wants}}
    fields = collections.defaultdict(set)          # (enemy, group) -> {(field, block)}
    for (enemy, group), (_pats, fb) in wants.items():
        fields[(enemy, group)].update(fb)
    # tag path -> [maps it appears on, {(field, block): defines}]
    seen = {}
    owner = collections.defaultdict(set)           # (enemy, group) -> {tag path}
    for mp in ca.game_maps(folder, game):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = hp.open_map(mp, game)
        except Exception:
            continue
        for (enemy, group), (pats, _fb) in wants.items():
            plug = plugs.get(group)
            if plug is None:
                continue
            for pat in pats:
                if pat == GENERIC:
                    continue
                for tp, base in m.find_tags(group, pat):
                    if tp.endswith(GENERIC):
                        continue
                    ident = (group, tp)
                    rec = seen.get(ident)
                    if rec is None:
                        rec = seen[ident] = [set(), {}]
                    rec[0].add(mp)
                    owner[(enemy, group)].add(ident)
                    for f, blk in fields[(enemy, group)]:
                        if (f, blk) in rec[1]:
                            continue
                        fld = plug.find(f, blk)
                        if not fld:
                            continue
                        if game == 'Halo 1':
                            ok = True
                        else:
                            try:
                                ok = bool(m.follow_all(base, fld['block_offsets'],
                                                       fld.get('block_sizes'), 'all'))
                            except Exception:
                                ok = False
                        rec[1][(f, blk)] = ok
        del m
    out = {}
    for (enemy, group), idents in owner.items():
        regular = {i for i in idents if len(seen[i][0]) >= min_maps}
        used = regular or idents
        for f, blk in fields[(enemy, group)]:
            vals = [seen[i][1][(f, blk)] for i in used if (f, blk) in seen[i][1]]
            if vals:
                out[(enemy, group, f, blk)] = (sum(vals), len(vals) - sum(vals),
                                               not regular)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pair', nargs=2, metavar=('OLDER', 'NEWER'),
                    help='only this pair of games')
    ap.add_argument('--all', action='store_true',
                    help='also list drifts no card is aimed at')
    ap.add_argument('--min-maps', type=int, default=2,
                    help='a variant must appear on at least this many maps to count '
                         '(default 2; an enemy with no such variant uses all of them)')
    args = ap.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    order = [c[0] for c in CASES]
    active = [c for c in CASES if not args.pair or c[0] in args.pair]
    rows = {c[0]: card_rows(db, c[0]) for c in active}

    # What each game has to measure: its own rows, plus -- for a row the OLDER game has
    # no card for -- the newer row's field, so an enemy that only gained a card later
    # still shows which side of the base it sat on before.
    wants = {g: {} for g in rows}

    def want(game, enemy, group, pats, f, blk):
        pp, fb = wants[game].setdefault((enemy, group), ([], set()))
        for p in pats:
            if p not in pp:
                pp.append(p)
        fb.add((f, blk))

    species_pats = collections.defaultdict(list)   # (game, enemy) -> species patterns
    for g, rs in rows.items():
        for r in rs:
            if r.aim == 'species':
                for p in r.pats:
                    if p not in species_pats[(g, r.enemy)]:
                        species_pats[(g, r.enemy)].append(p)

    def pats_for(game, r):
        if game == 'Halo 1':
            return r.pats if r.group in H1_GROUPS else []
        # Every game's patterns for the species (as generic_census does), or -- for a
        # boss, which enemy_tag_patterns does not know -- this game's own card tags.
        return (ca.enemy_tag_patterns(db, r.enemy)
                or species_pats.get((game, r.enemy)) or [])

    for g, rs in rows.items():
        for r in rs:
            want(g, r.enemy, r.group, pats_for(g, r), r.field, r.block)
    for older, newer in zip(order, order[1:]):
        if older not in rows or newer not in rows or older == 'Halo 1':
            continue
        okeys = {r.key for r in rows[older]}
        for r in rows[newer]:
            if r.key not in okeys:
                want(older, r.enemy, 'char', pats_for(newer, r), r.field, r.block)

    state = {}
    for game, subs, folder in active:
        d = measure(db, game, subs, folder, wants[game], args.min_maps)
        state[game] = d
        print('%-13s %4d card row(s), %4d (enemy, field) pair(s) measured on every map'
              % (game, len(rows[game]), len(d)), flush=True)

    for older, newer in zip(order, order[1:]):
        if older not in state or newer not in state:
            continue
        print()
        print('=' * 78)
        print('%s  ->  %s' % (older, newer))
        od, nd = state[older], state[newer]
        orows = {}
        for r in rows[older]:
            orows.setdefault(r.key, r)
        found = 0
        done = set()
        for r in sorted(rows[newer], key=lambda r: (r.enemy, r.card, r.field)):
            nkey = (r.enemy, 'char', r.field, r.block)
            o = orows.get(r.key)
            okey = ((o.enemy, o.group, o.field, o.block) if o is not None
                    else (r.enemy, 'char', r.field, r.block))
            if nkey not in nd or okey not in od or (okey, nkey) in done:
                continue
            done.add((okey, nkey))
            odfn, oinh, oone = od[okey]
            ndfn, ninh, none_ = nd[nkey]
            o_defines, n_defines = odfn > 0, ndfn > 0
            if o_defines == n_defines:
                continue
            cards = sorted({(x.card, x.aim, x.seed) for x in rows[newer]
                            if (x.enemy, x.field, x.block) == (r.enemy, r.field, r.block)})
            drift = 'TO SPECIES' if n_defines else 'TO GENERIC'
            # A drift only BREAKS a card when the card aims the way the newer game no
            # longer supports: generic-aimed after the value moved onto the species,
            # or species-aimed after it moved onto the base.
            # ...and a species-aimed card that SEEDS the block is doing the fix, not
            # suffering the drift.
            broken = [c for c, aim, seed in cards
                      if (aim == 'generic') == n_defines and not seed]
            known = [c for c in broken if (newer, r.enemy, c) in VERIFIED]
            broken = [c for c in broken if c not in known]
            if not broken and not (args.all or known):
                continue
            found += 1
            renamed = ('  (was %s)' % okey[2]) if okey[2] != r.field else ''
            oneoff = '  [one-off variants only]' if (oone or none_) else ''
            print('   %-10s %-11s %-28s %s%s%s'
                  % (drift, r.enemy, r.field, '%d def/%d inh -> %d def/%d inh'
                     % (odfn, oinh, ndfn, ninh), renamed, oneoff))
            for c, aim, seed in cards:
                mark = ''
                if (aim == 'generic') == n_defines and not seed:
                    mark = ('  <-- already recorded as dead'
                            if (newer, r.enemy, c) in VERIFIED else '  <-- now wrong')
                elif seed:
                    mark = '  (seeds the block itself)'
                print('        card %-30s aims at %-8s%s' % (c, aim, mark))
        if not found:
            print('   nothing%s' % ('' if args.all else ' a card is aimed at'))


if __name__ == '__main__':
    main()
