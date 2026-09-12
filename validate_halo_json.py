"""halo.json validator — run it after editing the effect database.

    python validate_halo_json.py

Two kinds of check:

  STRUCTURE  — read from halo.json alone, no maps or plugins needed. Catches the
               traps that are invisible until a specific game is played.
  RESOLUTION — for every effect, for each game it declares, resolve the tag on the
               real maps and confirm each target field exists in the plugin AND
               reads on at least one matching tag.

Exit code is 0 only when nothing is reported.
"""
import json
import os
import sys

TOOL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOL)
import halo_map as hm                                    # noqa: E402
import halo_patch as hp                                  # noqa: E402

BS = chr(92)
MCC = os.path.abspath(os.path.join(TOOL, '..'))
# Resolved rather than hardcoded: Assembly moved off the Steam drive and every
# CLI tool that had the old path baked in stopped finding it.
import assembly_plugins

PLUGINS = assembly_plugins.plugins_dir()

MAPS = {
    'Halo 1': ('halo1/maps', ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']),
    'Halo 2': ('halo2/h2_maps_win64_dx11',
               ['01a_tutorial', '03a_oldmombasa', '04b_floodlab', '05a_deltaapproach',
                '05b_deltatowers', '06a_sentinelwalls', '07b_forerunnership', '08b_deltacontrol']),
    'Halo 3': ('halo3/maps',
               ['005_intro', '010_jungle', '020_base', '030_outskirts', '040_voi',
                '050_floodvoi', '070_waste', '100_citadel', '110_hc', '120_halo']),
    # ODST, Reach and Halo 4 were never resolution-checked -- the dict simply stopped
    # at Halo 3, so `0 problems` said nothing about half the games in the database and
    # a Halo 4 card naming a field the engine renamed could not be caught here. Fewer
    # maps each than the older games get: these caches are an order of magnitude larger
    # and every one is held open at once.
    'Halo 3: ODST': ('halo3odst/maps',
                     ['l200', 'l300', 'sc110', 'sc120', 'sc130', 'sc140', 'h100']),
    'Halo Reach': ('haloreach/maps',
                   ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']),
    # Shutdown, Composer and Infinity between them field every Halo 4 species and
    # nearly every weapon; Dawn carries the sprint equipment the other three lack.
    'Halo 4': ('halo4/maps',
               ['m10_crash', 'm020', 'm30_cryptum', 'm40_invasion', 'm60_rescue',
                'm70_liftoff', 'm80_delta', 'm90_sacrifice']),
}
SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST'],
           'Halo Reach': ['ReachMCC', 'Reach'], 'Halo 4': ['Halo4MCC', 'Halo4']}

problems = []



# Findings that have been LOOKED AT and accepted, keyed (game, label, field). Every one
# is the empty-block class: the tag resolves and the field is in the plugin, but the
# block has no elements because the tag inherits it. Suppressed by default so a clean
# run means "nothing new broke"; --all lists them with the reason.
#
# ADD TO THIS ONLY after establishing WHY, and prefer fixing: a card whose block is
# empty can often be made live with `init_defaults` + `grow`, which is how the hero
# cards reach blocks their tags do not own -- or GATED OUT of that game, which is what
# happened to the nine Halo 4 Hunter and Sentinel rows that used to sit here. Accepting
# a finding only keeps it quiet; the card goes on being offered and patched, and the
# write goes on landing nowhere. Prefer the gate.
ACCEPTED = {
    ('Halo Reach', 'Gravity Hammer/Accuracy Penalties', 'Reload Penalty'):
        'the Gravity Hammer has no Barrels values in Reach -- only seven Reach weapons '
        'carry Reload/Switch Penalty and it is not one of them',
    ('Halo Reach', 'Gravity Hammer/Accuracy Penalties', 'Switch Penalty'):
        'same',
}
_seen_accepted = []

inert = []


def report(msg, quiet=False):
    (inert if quiet else problems).append(msg)


# ---------------------------------------------------------------- load
with open(os.path.join(TOOL, 'halo.json'), encoding='utf-8') as f:
    DB = json.load(f)
GAMES = list(DB['Missions'].keys())


def resolve_gamed(v, game):
    """Mirror of the app's per-game resolution: exact match, else 'default', else
    the nearest EARLIER game (a later game's value must never leak backwards)."""
    if not isinstance(v, dict):
        return v
    if game in v:
        return v[game]
    if 'default' in v:
        return v['default']
    order = [g for g in GAMES if g in v]
    if not order:
        return None
    idx = GAMES.index(game) if game in GAMES else len(GAMES)
    earlier = [g for g in order if GAMES.index(g) <= idx]
    return v[earlier[-1]] if earlier else None


def declared_games(eff):
    """Which games an effect is OFFERED in — matching ModifierDatabase._game_ok,
    which is the code that actually gates a card.

    Note it does NOT infer anything from the tag dict: `_game_ok` returns True
    whenever there is no explicit `game` key, so a per-game tag dict alone does not
    restrict an effect. An effect with tag keys {H1, H2} and no `game` key is still
    offered in H3, where `resolve_gamed` silently falls back to the H2 tag."""
    skip = eff.get('skip_games')
    skip = [skip] if isinstance(skip, str) else list(skip or [])
    g = eff.get('game')
    if isinstance(g, str):
        return [g] if g not in skip else []
    if isinstance(g, list):
        return [x for x in g if x not in skip]
    return [x for x in GAMES if x not in skip]


def iter_effects():
    """(label, effect, weapon_or_None) for every effect in the database."""
    pm = DB.get('Player Modifiers', {})
    for n, e in (pm.get('General Modifiers') or {}).items():
        yield f'Player/{n}', e, None
    for w, effs in (pm.get('Specific Weapon Modifier') or {}).items():
        for n, e in effs.items():
            yield f'{w}/{n}', e, w
    # Equipment is a sibling top-level section, keyed like weapons.
    for q, effs in (DB.get('Equipment') or {}).items():
        for n, e in effs.items():
            yield f'{q}/{n}', e, None
    em = DB.get('Enemy modifiers', {})
    for n, e in (em.get('General modifiers') or {}).items():
        yield f'EnemyGen/{n}', e, None
    for enemy, effs in (em.get('Specific Enemy modifier') or {}).items():
        for n, e in effs.items():
            yield f'{enemy}/{n}', e, None
    for boss, effs in (em.get('Boss enemy modifier') or {}).items():
        for n, e in effs.items():
            yield f'Boss {boss}/{n}', e, None
    # Heroes are a separate section and were missed entirely -- every Brute Chieftain,
    # Elite General, Knight Commander card went unchecked.
    for hero, effs in (em.get('Hero enemy modifier') or {}).items():
        for n, e in effs.items():
            yield f'{hero}/{n}', e, None
    for n, e in (DB.get('Friend modifiers') or {}).items():
        yield f'Friend/{n}', e, None
    for n, e in (DB.get('Skull modifiers') or {}).items():
        yield f'Skull/{n}', e, None


# ------------------------------------------------------- structure checks
def check_structure():
    # Which weapons/equipment each game actually has, from the Missions lists.
    per_game = {}
    for game, missions in DB['Missions'].items():
        s = set()
        for md in missions.values():
            for key in ('weapons', 'grenades', 'equipment'):
                s |= set(md.get(key) or [])
        per_game[game] = s

    skulls = set((DB.get('Skull modifiers') or {}).keys())

    for label, eff, weapon in iter_effects():
        tag = eff.get('tag')

        # 1. The shape-dependent trap: an effect is only IMPLICITLY restricted to a
        #    game when its tag is a per-game DICT. With a plain-string tag and no
        #    "game" key nothing limits it, so a weapon that exists in only one game
        #    gets offered in the others, where its tag cannot resolve.
        if weapon and 'game' not in eff and isinstance(tag, str):
            homes = [g for g in GAMES if weapon in per_game.get(g, ())]
            if homes and len(homes) < len(GAMES):
                report(f'{label}: no "game" key and a plain-string tag, but '
                       f'{weapon} only exists in {", ".join(homes)} — add '
                       f'"game": {json.dumps(homes[0] if len(homes) == 1 else homes)}')

        # 2. affected_by_skull must name a skull that exists.
        abs_ = eff.get('affected_by_skull')
        if abs_:
            for nm in ([abs_] if isinstance(abs_, str) else list(abs_)):
                if nm not in skulls:
                    report(f'{label}: affected_by_skull names unknown skull {nm!r} '
                           f'(known: {", ".join(sorted(skulls)) or "none"})')

        # 3. A skull entry needs its "skull" key (that's what the patcher dispatches on).
        if label.startswith('Skull/') and not eff.get('skull'):
            report(f'{label}: skull entry is missing its "skull" key')

        # 4. desc_overrides must be a per-game DICT. A list of single-key dicts looks
        #    plausible but silently renders as raw Python in the card text.
        ov = eff.get('desc_overrides')
        if ov is not None and not isinstance(ov, dict):
            report(f'{label}: desc_overrides must be a dict keyed by game, got '
                   f'{type(ov).__name__} — e.g. {{"Halo 3": "..."}}')
        elif isinstance(ov, dict):
            for k in ov:
                if k not in GAMES and k != 'default':
                    report(f'{label}: desc_overrides has unknown game key {k!r}')


# Who each game actually fields, from its own Missions lists. A card about a weapon or
# an enemy the game does not have CANNOT be drafted there, so its tag failing to resolve
# is the expected result rather than a fault -- the Flood from ODST on, Reach's
# Sentinels, Halo 4's Plasma Rifle, Brutes and Buggers. Reporting those as problems
# buried the real findings 3 to 1. They are still listed under --all, because "inert
# here" is worth being able to see on purpose.
_FIELDED = {}
for _g, _ms in DB['Missions'].items():
    _s = set()
    for _md in _ms.values():
        for _k in ('weapons', 'grenades', 'equipment', 'enemies', 'bosses', 'turrets'):
            _s |= set(_md.get(_k) or [])
    _FIELDED[_g] = _s
_ANY_FIELDED = set().union(*_FIELDED.values()) if _FIELDED else set()


def is_inert(label, game):
    """True when this card's subject is something `game` does not field."""
    owner = label.split('/')[0]
    if owner.startswith('Boss '):
        owner = owner[5:]
    if owner not in _ANY_FIELDED:
        return False                  # Player/EnemyGen/Friend/Skull have no owner
    return owner not in _FIELDED.get(game, ())


# ------------------------------------------------------ resolution checks
_plugins, _maps = {}, {}


def plugin(game, cls):
    key = (game, cls)
    if key not in _plugins:
        found = None
        for sub in SUBDIRS[game]:
            fn = os.path.join(PLUGINS, sub, cls + '.xml')
            if os.path.exists(fn):
                found = hm.Plugin(fn)
                break
        _plugins[key] = found
    return _plugins[key]


def map_paths(game):
    """The sampled map FILES for a game, opened one at a time by the caller."""
    subdir, names = MAPS[game]
    out = []
    for mn in names:
        fn = os.path.join(MCC, *subdir.split('/'), mn + '.map')
        if os.path.exists(fn):
            out.append((mn, fn))
    return out


def flavors(field, t):
    if t.get('diff_prefix_nl'):
        return ['Normal ' + field, 'Legendary ' + field]
    if t.get('diff_prefix'):
        return ['Legendary ' + field, 'Heroic ' + field, 'Normal ' + field]
    if t.get('diff_suffix'):
        return [f'{field} ({x})' for x in ('Legendary', 'Heroic', 'Normal', 'Easy')]
    if t.get('difficulty'):
        return [f'{x} {field}' for x in ('Impossible', 'Legendary', 'Normal', 'Easy')]
    return [field]


def _targets_of(eff, game, cls, tpath):
    """The resolvable targets of one card in one game: (field, block, nth, class, path).

    Pseudo-field targets are skipped -- reload/swap animation lengths, map placement
    percentages, the Brute equipment drop weight and the ability tuning rows are all
    handled by dedicated ops in apply_run, not by a plugin field write, so there is no
    field name to look up. A target may also redirect to a tag of its own class, which
    is resolved against THAT class or every redirect reads as a missing field.
    """
    out = []
    for t in resolve_gamed(eff.get('targets'), game) or []:
        if not isinstance(t, dict) or any(
                t.get(k) for k in ('reload_anim', 'swap_anim', 'map_swap',
                                   'map_equip', 'equip_drop', 'sprint')):
            continue
        if t.get('games') and game not in t['games']:
            continue
        if t.get('skip_games') and game in t['skip_games']:
            continue
        field = resolve_gamed(t.get('field'), game)
        if field is None:
            continue
        use_cls, use_path = cls, tpath
        own = resolve_gamed(t.get('tag'), game)
        if isinstance(own, str) and own.strip():
            use_cls, use_path = hm.split_tag(own)
        out.append((field, resolve_gamed(t.get('block'), game),
                    resolve_gamed(t.get('nth'), game) or 0, use_cls, use_path, t))
    return out


def check_resolution():
    """Per game: build the work list, then walk the maps ONE AT A TIME.

    A card is only reported when every sampled map of its game agrees -- the tag is on
    none of them, or the field's block is empty on all of them. Whether a tag is
    resident and whether a character defines a block both vary by level, so a
    single-map verdict is a guaranteed false positive (the Halo 2 Elites carry their
    Grenades block on 9 of the 13 levels that field them).
    """
    work = {}                       # game -> [(label, cls, path, [targets])]
    for label, eff, _weapon in iter_effects():
        if eff.get('skull'):        # whole-map rules, applied in code; nothing to resolve
            continue
        for game in declared_games(eff):
            if game not in MAPS:
                continue
            tag = resolve_gamed(eff.get('tag'), game)
            if not isinstance(tag, str) or not tag.strip():
                continue
            cls, tpath = hm.split_tag(tag)
            if cls == 'matg':
                continue
            init = eff.get('init_defaults')
            # `init_defaults` is a PLAIN dict on most cards and a per-game one on a
            # few, and resolve_gamed treats any dict as game-keyed -- so resolving
            # unconditionally turned every plain seeder into None and the rule never
            # fired. Only resolve when the keys really are game names.
            if isinstance(init, dict) and any(k in GAMES for k in init):
                init = resolve_gamed(init, game)
            seeds = (str(init.get('block')).lower()
                     if isinstance(init, dict) and init.get('block') else None)
            work.setdefault(game, []).append(
                (label, tag, cls, tpath, _targets_of(eff, game, cls, tpath), seeds))

    for game, items in work.items():
        # The plugin half needs no map at all, so it is settled first and the field is
        # dropped from the map walk once it is known to be missing.
        live = []
        for label, tag, cls, tpath, targets, seeds in items:
            p = plugin(game, cls)
            quiet = is_inert(label, game)
            if p is None:
                report(f'{label} [{game}]: no {cls} plugin', quiet)
                continue
            keep = []
            for field, block, nth, ucls, upath, t in targets:
                tp = plugin(game, ucls)
                if tp is None:
                    report(f'{label} [{game}]: no {ucls} plugin', quiet)
                    continue
                fld = None
                for nm in flavors(field, t):
                    fld = tp.find(nm, block, nth)
                    if fld:
                        break
                if not fld:
                    report(f'{label} [{game}]: FIELD not in plugin: {field!r} '
                           f'(block {block!r})', quiet)
                    continue
                # A card that SEEDS the block it edits is not broken when that block
                # reads empty -- being empty is the whole reason it seeds, and the
                # patcher grows or copies it before writing. Same comparison
                # halo_enhancer makes at _seeded_default and deadcards at its own loop;
                # without it every hero card with init_defaults reads as a fault, which
                # is exactly what the newly-walked Hero section produced.
                keep.append((field, ucls, upath, fld,
                             bool(seeds and block and str(block).lower() == seeds)))
            live.append((label, tag, cls, tpath, keep))

        found = {}                  # label -> tag resolved on some map
        tfound = {}                 # (cls, path) -> a TARGET's own tag resolved
        filled = {}                 # (label, field, path) -> block non-empty somewhere
        for mn, fn in map_paths(game):
            try:
                m = hp.open_map(fn, game)
            except Exception as ex:
                print(f'  (could not open {mn}: {ex})')
                continue
            hits = {}

            def tags_for(cls, path):
                key = (cls, path)
                if key not in hits:
                    h = []
                    for part in path.split(' & '):
                        h += m.find_tags(cls, part.strip())
                    hits[key] = h
                return hits[key]

            for label, tag, cls, tpath, keep in live:
                if tags_for(cls, tpath):
                    found[label] = True
                for field, ucls, upath, fld, _seeded in keep:
                    key = (label, field, upath)
                    if tags_for(ucls, upath):
                        tfound[(ucls, upath)] = True
                    if filled.get(key):
                        continue
                    for _tp, b in tags_for(ucls, upath):
                        if m.follow_all(b, fld['block_offsets'],
                                        fld.get('block_sizes'), 'all'):
                            filled[key] = True
                            break
            del m                   # one map at a time: Halo 4's eight are 5.5 GB

        for label, tag, cls, tpath, keep in live:
            quiet = is_inert(label, game)
            if not found.get(label):
                report(f'{label} [{game}]: tag resolves on 0 maps  ({tag})', quiet)
                continue
            for field, ucls, upath, _fld, seeded in keep:
                if seeded or filled.get((label, field, upath)):
                    continue
                # A target may name a tag of its own -- the Firing Noise cards carry
                # the projectile's Impact and Detonation Noise alongside the weapon's.
                # When THAT tag is the thing missing, saying the field is empty points
                # at the wrong half of the card.
                if not tfound.get((ucls, upath)):
                    report(f'{label} [{game}]: TARGET tag resolves on 0 maps '
                           f'({ucls} {upath})', quiet)
                else:
                    why = ACCEPTED.get((game, label, field))
                    if why is not None:
                        _seen_accepted.append((game, label, field, why))
                        continue
                    report(f'{label} [{game}]: field EMPTY on every sampled map: '
                           f'{field!r}', quiet)


if __name__ == '__main__':
    check_structure()
    n_struct = len(problems)
    print(f'structure checks: {n_struct} problem(s)')
    skipped = not os.path.isdir(PLUGINS)
    if not skipped:
        check_resolution()
    else:
        print(f'  (skipping resolution checks — plugins not found at {PLUGINS})')
    print(f'\n===== {len(problems)} problem(s) =====')
    for pr in problems:
        print(' ', pr)
    if _seen_accepted:
        if '--all' in sys.argv:
            print(f'\n----- {len(_seen_accepted)} accepted finding(s) -----')
            for g, lab, f, why in _seen_accepted:
                print(f'  {lab} [{g}]: {f!r}')
                print(f'        accepted: {why}')
        else:
            print(f'({len(_seen_accepted)} accepted finding(s) suppressed -- known '
                  f'empty blocks; --all lists them with reasons)')
    # An entry that never fires is a card that was fixed, or a label that drifted.
    _fired = {(g, lab, f) for g, lab, f, _w in _seen_accepted}
    _stale = [k for k in ACCEPTED if k not in _fired]
    if _stale:
        print(f'{len(_stale)} accepted entr(y/ies) did NOT fire -- fixed, or the label '
              f'drifted:')
        for g, lab, f in _stale:
            print(f'   {lab} [{g}]: {f!r}')
    if inert:
        if '--all' in sys.argv:
            print(f'\n----- {len(inert)} inert card(s): the game does not field this '
                  f'weapon or enemy, so the card cannot be drafted there -----')
            for pr in inert:
                print(' ', pr)
        else:
            print(f'({len(inert)} inert card(s) suppressed -- a weapon or enemy the '
                  f'game does not field; --all lists them)')
    if skipped:
        # The notice above is enough for a person reading the output, but not for
        # anything that chains on the exit code: "0 problem(s)" with exit 0 after
        # skipping the resolution pass was exactly the silent clean bill of health
        # assembly_plugins was written to prevent. A distinct code says "not checked".
        print('RESOLUTION NOT CHECKED: plugins not found at %s -- a structure-only '
              'result, not a clean one (exit 2).' % PLUGINS)
    sys.exit(1 if problems else (2 if skipped else 0))
