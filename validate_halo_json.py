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
PLUGINS = (r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
           r"\Assembly-1-2023-11-29-1702446457\Plugins")

MAPS = {
    'Halo 1': ('halo1/maps', ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']),
    'Halo 2': ('halo2/h2_maps_win64_dx11',
               ['01a_tutorial', '03a_oldmombasa', '04b_floodlab', '05a_deltaapproach',
                '05b_deltatowers', '06a_sentinelwalls', '07b_forerunnership', '08b_deltacontrol']),
    'Halo 3': ('halo3/maps',
               ['005_intro', '010_jungle', '020_base', '030_outskirts', '040_voi',
                '050_floodvoi', '070_waste', '100_citadel', '110_hc', '120_halo']),
}
SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3']}

problems = []


def report(msg):
    problems.append(msg)


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
    g = eff.get('game')
    if isinstance(g, str):
        return [g]
    if isinstance(g, list):
        return list(g)
    return list(GAMES)


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


def maps_for(game):
    if game not in _maps:
        out = []
        subdir, names = MAPS[game]
        for mn in names:
            fn = os.path.join(MCC, *subdir.split('/'), mn + '.map')
            if os.path.exists(fn):
                try:
                    out.append((mn, hp.open_map(fn, game)))
                except Exception as ex:
                    print(f'  (could not open {mn}: {ex})')
        _maps[game] = out
    return _maps[game]


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


def check_resolution():
    for label, eff, weapon in iter_effects():
        # Skulls are whole-map rules applied in code, not per-field tag edits. Their
        # "tag" is nominal (just a group name, no path) and has nothing to resolve.
        if eff.get('skull'):
            continue
        for game in declared_games(eff):
            if game not in MAPS:
                continue
            tag = resolve_gamed(eff.get('tag'), game)
            if not isinstance(tag, str) or not tag.strip():
                continue                       # skulls and the like carry no real tag
            cls = tag.split(' ', 1)[0]
            if cls == 'matg':
                continue
            p = plugin(game, cls)
            if p is None:
                report(f'{label} [{game}]: no {cls} plugin')
                continue
            _, tpath = hm.split_tag(tag)
            found_map, hits = None, []
            for mn, m in maps_for(game):
                h = []
                for part in tpath.split(' & '):
                    h += m.find_tags(cls, part.strip())
                if h:
                    found_map, hits = m, h
                    break
            if found_map is None:
                report(f'{label} [{game}]: tag resolves on 0 maps  ({tag})')
                continue
            targets = resolve_gamed(eff.get('targets'), game) or []
            # Pseudo-field targets are handled by dedicated ops in apply_run, not by
            # a plugin field write, so there is no field name to resolve: reload
            # animation length, map placement percentages, and the Brute equipment
            # drop weight (whose element is picked by tagRef, not by index).
            for t in targets:
                if not isinstance(t, dict) or any(
                        t.get(k) for k in ('reload_anim', 'map_swap', 'map_equip',
                                           'equip_drop')):
                    continue
                if t.get('games') and game not in t['games']:
                    continue
                field = resolve_gamed(t.get('field'), game)
                if field is None:
                    continue
                block = resolve_gamed(t.get('block'), game)
                nth = resolve_gamed(t.get('nth'), game) or 0
                fld = None
                for nm in flavors(field, t):
                    fld = p.find(nm, block, nth)
                    if fld:
                        break
                if not fld:
                    report(f'{label} [{game}]: FIELD not in plugin: {field!r} '
                           f'(block {block!r})')
                    continue
                got = any(found_map.follow_all(b, fld['block_offsets'],
                                               fld.get('block_sizes'), 'all')
                          for _, b in hits)
                if not got:
                    report(f'{label} [{game}]: field EMPTY on all matched tags: {field!r}')


if __name__ == '__main__':
    check_structure()
    n_struct = len(problems)
    print(f'structure checks: {n_struct} problem(s)')
    if os.path.isdir(PLUGINS):
        check_resolution()
    else:
        print(f'  (skipping resolution checks — plugins not found at {PLUGINS})')
    print(f'\n===== {len(problems)} problem(s) =====')
    for pr in problems:
        print(' ', pr)
    sys.exit(1 if problems else 0)
