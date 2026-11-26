"""halo.json validator — run it after editing the effect database.

    python validate_halo_json.py

Two kinds of check:

  STRUCTURE  — read from halo.json alone, no maps or plugins needed. Catches the
               traps that are invisible until a specific game is played.
  RESOLUTION — for every effect, for each game it declares, resolve the tag on the
               real maps and confirm each target field exists in the plugin AND
               reads on at least one matching tag. The maps are the pristine
               BASELINES of every mission in halo.json (what a patch rebuilds from),
               and the run prints which ones it read.

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

# The game's map folder under the MCC root (CONFIG map_game_folder). WHICH maps are read
# is not listed here any more: it is every mission of halo.json's own Missions list (see
# MAPS below), each from its pristine BASELINE.
FOLDERS = {'Halo 1': 'halo1/maps', 'Halo 2': 'halo2/h2_maps_win64_dx11',
           'Halo 3': 'halo3/maps', 'Halo 3: ODST': 'halo3odst/maps',
           'Halo Reach': 'haloreach/maps', 'Halo 4': 'halo4/maps'}
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
# game -> (map folder, the missions to read). Every mission the run can play, in halo.json's
# order. These used to be hand-kept samples: they named two maps no mission plays (Halo 2
# 01a_tutorial, Halo 3 005_intro -- a tag resident only there would have counted as
# resolving) and left out nine that are played (Halo 2 01b / 03b / 04a / 06b / 07a / 08a,
# ODST sc100 / sc150, Reach m70_bonus): ODST's SAW port lives on sc150 alone.
MAPS = {g: (FOLDERS[g], list(DB['Missions'][g])) for g in GAMES if g in FOLDERS}


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

    # 5. Every enemy / hero / boss card names its colour-drift group (enemy_colors: an
    #    active card shifts that enemy's colours toward red, blue or green). A new card
    #    without one would silently never shift anything.
    em = DB.get('Enemy modifiers', {})
    cards = [(f'EnemyGen/{n}', e) for n, e in (em.get('General modifiers') or {}).items()]
    for sec in ('Specific Enemy modifier', 'Hero enemy modifier', 'Boss enemy modifier'):
        for who, effs in (em.get(sec) or {}).items():
            cards += [(f'{who}/{n}', e) for n, e in effs.items()]
    for label, e in cards:
        c = e.get('color') if isinstance(e, dict) else None
        if c not in COLOR_GROUPS:
            report(f'{label}: "color" must be one of {", ".join(COLOR_GROUPS)} '
                   f'(aggressive = more damage, defensive = survives longer, '
                   f'utility = everything else), got {c!r}')

    # 6. harder_when / easier_when follow the step, on the right side
    check_directions(False)

    # 7. Zoom coverage (user, 2026-10-09): every weapon gets the Zoom card -- it improves
    #    a 1-stage zoom to 2 stages, amplifies a 2-stage one, and GIVES one to a weapon
    #    without (from_zero) -- so a port must never skip it because its donor or it has
    #    no zoom. Every Zoom card has a Zoom Time twin where the field exists (Halo 3 on;
    #    Halo 1/2 weapons have no zoom time). Melee weapons are the only exceptions.
    check_zoom_coverage(per_game)

    # 8. Game names and per-game keys, and 9. a card offered in a game where it has no
    #    tag or no row (review U5 V5).
    check_games()
    check_offered()


# Keys whose value is either a plain value or a dict keyed BY GAME (the app resolves
# them with resolve_gamed): on a card, on a target row, and in a `constraints` entry.
# In such a dict only game names and 'default' are read. Any other key is lost in
# silence: `"block": {"Halo 3": "Barrels", "index": 1}` resolved to 'Barrels' and the
# row wrote barrel 0 (Spartan Laser / Projectiles Per Shot, from 2026-07-20 until the
# review found it by script) while this validator printed 0 problems.
GAMED_CARD_KEYS = ('tag', 'targets', 'debug_desc', 'desc_inverted', 'harder_when',
                   'easier_when', 'requires_config', 'invertible')
GAMED_ROW_KEYS = ('field', 'block', 'negate', 'nth', 'index', 'offset', 'zero_is', 'tag',
                  'inverse_steps')
GAMED_CONSTRAINT_KEYS = ('field', 'of', 'block', 'index')

# Rows that are not a plugin field write: apply_run has a dedicated op for each
# (animation lengths, placement shares, the Brute equipment drop, ability tuning ...).
PSEUDO_ROWS = ('reload_anim', 'swap_anim', 'berserk_anim', 'sword_drain', 'morph_anim',
               'infect_anim', 'move_speed', 'squad_count', 'species_swap', 'camo',
               'damage_row', 'map_swap', 'map_equip', 'equip_drop', 'sprint')


def card_ignored(eff):
    """halo_enhancer.is_ignored: the card is held out of every pool. Only a real yes
    counts ('yes' / 'true' / '1' / true), so a typo cannot delete a card."""
    v = eff.get('ignore')
    if isinstance(v, bool):
        return v
    return isinstance(v, str) and v.strip().lower() in ('yes', 'true', '1')


def row_applies(t, game):
    """halo_enhancer.target_applies: the row's own ignore / games / skip_games gates."""
    if t.get('ignore'):
        return False
    if game in (t.get('skip_games') or []):
        return False
    return not t.get('games') or game in t['games']


def _rows(eff):
    """Every target row of a card, whichever shape `targets` has: [(where, row)]."""
    ts = eff.get('targets')
    if isinstance(ts, dict):
        return [(f'targets[{g}]', t) for g, lst in ts.items()
                for t in (lst if isinstance(lst, list) else [])]
    return [('targets', t) for t in (ts if isinstance(ts, list) else [])]


def check_games():
    """8. Every game NAME must be one of the Missions keys, and a per-game dict may hold
    only game names and 'default'. A misspelt name gates the card or the row out of the
    game it meant (`_game_ok` / `target_applies` compare strings), a stray key is never
    read -- and both used to pass here without a word."""
    known = set(GAMES)

    def names(label, where, val, need_list=False):
        if val is None:
            return
        if isinstance(val, str):
            if need_list:
                # target_applies tests `game in value`: on a string that is a SUBSTRING
                # test, and 'Halo 3' is inside 'Halo 3: ODST'
                report(f'{label}: {where} must be a list of game names, got the string '
                       f'{val!r}')
            val = [val]
        if not isinstance(val, list):
            report(f'{label}: {where} must be a game name or a list of them, got '
                   f'{type(val).__name__}')
            return
        for g in val:
            if g not in known:
                report(f'{label}: {where} names unknown game {g!r} '
                       f'(known: {", ".join(GAMES)})')

    def gamed(label, where, val, strict):
        """`strict`: the key is only ever a plain value or a per-game dict. Otherwise the
        dict may be a plain spec (init_defaults, damage_row) and is judged per-game only
        when it holds at least one game key."""
        if not isinstance(val, dict):
            return
        if not strict and not any(k in known or k == 'default' for k in val):
            return
        for k in val:
            if k not in known and k != 'default':
                report(f'{label}: {where} has the key {k!r} inside a per-game entry -- '
                       f'only game names and "default" are read there, so it is lost')

    for label, eff, _weapon in iter_effects():
        if not isinstance(eff, dict):
            report(f'{label}: a card must be an object, got {type(eff).__name__}')
            continue
        names(label, '"game"', eff.get('game'))
        names(label, '"skip_games"', eff.get('skip_games'))
        for k, v in eff.items():
            if k != 'desc_overrides':           # rule 4 reports that one
                gamed(label, f'"{k}"', v, k in GAMED_CARD_KEYS)
        for c in eff.get('constraints') or []:
            if isinstance(c, dict):
                for k, v in c.items():
                    gamed(label, f'constraints "{k}"', v, k in GAMED_CONSTRAINT_KEYS)
        if not isinstance(eff.get('targets'), (list, dict, type(None))):
            report(f'{label}: "targets" must be a list (or a per-game dict of lists), got '
                   f'{type(eff["targets"]).__name__}')
        if isinstance(eff.get('targets'), dict):
            for g, lst in eff['targets'].items():
                if not isinstance(lst, list):
                    report(f'{label}: targets[{g}] must be a list of rows, got '
                           f'{type(lst).__name__}')
        for where, t in _rows(eff):
            if not isinstance(t, dict):
                # the app drops such a row (on_patch_map); it is a typo all the same
                report(f'{label}: {where} holds {t!r} -- a row must be an object')
                continue
            row = f'{where} [{t.get("field") if isinstance(t.get("field"), str) else "row"}]'
            names(label, f'{row} "games"', t.get('games'), need_list=True)
            names(label, f'{row} "skip_games"', t.get('skip_games'), need_list=True)
            for k, v in t.items():
                gamed(label, f'{row} "{k}"', v, k in GAMED_ROW_KEYS)


def check_offered():
    """9. In every game a card is OFFERED in it needs a tag and at least one row that
    applies there. Without a tag collect_effects drops the pick (`if not tag: return`),
    without a row the patcher has nothing to write: either way the draft slot is spent
    on nothing and no report row exists anywhere. check_resolution used to `continue`
    past both. Skulls are whole-map rules with no rows of their own; an ignored card is
    offered nowhere."""
    for label, eff, _weapon in iter_effects():
        if not isinstance(eff, dict) or card_ignored(eff):
            continue
        for game in declared_games(eff):
            if game not in GAMES:
                continue                        # rule 8 names it
            quiet = is_inert(label, game)
            tag = resolve_gamed(eff.get('tag'), game)
            if not isinstance(tag, str) or not tag.strip():
                report(f'{label} [{game}]: NO TAG in a game the card is offered in -- the '
                       f'pick is dropped at patch time', quiet)
                continue
            if eff.get('skull'):
                continue
            rows = resolve_gamed(eff.get('targets'), game) or []
            live = [t for t in rows if isinstance(t, dict) and row_applies(t, game)
                    and (any(t.get(k) for k in PSEUDO_ROWS) or t.get('placed')
                         or resolve_gamed(t.get('field'), game) is not None)]
            if not live:
                report(f'{label} [{game}]: NO ROW applies in a game the card is offered '
                       f'in ({len(rows)} row(s), none for this game)', quiet)


ZOOM_EXEMPT = ('Energy Blade', 'Gravity Hammer')
ZOOM_TIME_GAMES = ('Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4')


def check_zoom_coverage(per_game):
    weapons = DB.get('Player Modifiers', {}).get('Specific Weapon Modifier') or {}
    fielded = {g: set() for g in GAMES}
    for game, missions in DB['Missions'].items():
        for md in missions.values():
            fielded[game] |= set(md.get('weapons') or [])
    try:
        import weapon_ports
        for game, ports in weapon_ports.load_catalog().items():
            fielded.setdefault(game, set()).update(p['weapon'] for p in ports or ())
    except Exception:
        pass

    def has(card, game):
        if not isinstance(card, dict):
            return False
        d = declared_games(card)
        return game in d or (game == 'Halo 3: ODST' and 'Halo 3' in d)
    for w, cards in sorted(weapons.items()):
        if w in ZOOM_EXEMPT:
            continue
        for game in GAMES:
            # a weapon whose cards are deferred in a game (Halo 1 Flamethrower) has none
            if w not in fielded.get(game, ()) or not any(has(c, game) for c in cards.values()):
                continue
            if not has(cards.get('Zoom'), game):
                report(f'{w}/Zoom: missing in {game} -- every weapon gets the Zoom card '
                       f'(it gives a zoom to one without)')
            elif game in ZOOM_TIME_GAMES and not has(cards.get('Zoom Time'), game):
                report(f'{w}/Zoom Time: missing in {game} -- every Zoom card has its '
                       f'Zoom Time twin from Halo 3 on')


COLOR_GROUPS = ('aggressive', 'defensive', 'utility')


def _step_direction(step):
    """'increased' / 'decreased' for a per-pick op, None for a set or nothing."""
    import halo_map as _hm
    parsed = _hm.parse_operator(step) if isinstance(step, str) else None
    if not parsed:
        return None
    kind, val = parsed
    if kind == 'mul':
        return 'increased' if val > 1 else ('decreased' if val < 1 else None)
    if kind in ('add', 'sub'):
        up = (val > 0) == (kind == 'add')
        return None if val == 0 else ('increased' if up else 'decreased')
    return None


def check_directions(quiet):
    """6. The STEP is the ground truth for direction (user, 2026-10-06): enemy cards
    (Enemy / Skull) say it with harder_when, player cards (Player / Equipment / Friend)
    with easier_when, and a key must point where the step points."""
    sides = {'Player Modifiers': ('easier_when', 'harder_when'),
             'Equipment': ('easier_when', 'harder_when'),
             'Friend modifiers': ('easier_when', 'harder_when'),
             'Enemy modifiers': ('harder_when', 'easier_when'),
             'Skull modifiers': ('harder_when', 'easier_when')}

    def walk(o, path, own, other):
        if isinstance(o, dict):
            if 'targets' in o or 'tag' in o:
                ts = o.get('targets')
                tl = ts if isinstance(ts, list) else (
                    [x for v in ts.values() for x in v] if isinstance(ts, dict) else [])
                for key in (other,):
                    if key in o:
                        report(f'{path}: "{key}" on a {own.split("_")[0]}-side card -- use "{own}"', quiet)
                for t in tl:
                    if not isinstance(t, dict):
                        continue
                    if other in t:
                        report(f'{path} [{t.get("field")}]: "{other}" on a '
                               f'{own.split("_")[0]}-side card -- use "{own}"', quiet)
                    st = t.get('step')
                    if st is None and isinstance(t.get('steps'), list) and t['steps']:
                        st = t['steps'][0]
                    want = _step_direction(st) if isinstance(st, str) else None
                    have = t.get(own)
                    if want and isinstance(have, str) and have != want and not t.get('ask_direction'):
                        report(f'{path} [{t.get("field")}]: {own} "{have}" but the step '
                               f'{st} points {want}', quiet)
                    # the adding twin of a step (halo_enhancer._step_variants)
                    ast_ = t.get('add_step')
                    awant = _step_direction(ast_) if isinstance(ast_, str) else None
                    if ast_ is not None and (not awant or str(ast_).strip()[:1] not in '+-'):
                        report(f'{path} [{t.get("field")}]: add_step {ast_!r} is not +n / -n', quiet)
                    elif awant and want and awant != want:
                        report(f'{path} [{t.get("field")}]: add_step {ast_} points {awant}, '
                               f'step {st} points {want}', quiet)
                return
            for k, v in o.items():
                walk(v, f'{path}/{k}' if path else k, own, other)

    for sec, (own, other) in sides.items():
        walk(DB.get(sec) or {}, sec, own, other)


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
# Ported weapons (weapon_ports_catalog.json) are fielded by every game they were
# ported into: the SAW's Halo 1-Reach cards are real cards, not inert ones.
_PORTS = {}
try:
    import weapon_ports as _wp
    for _g, _ps in (_wp.load_catalog() or {}).items():
        for _p in _ps or ():
            if _p.get('weapon'):
                _FIELDED.setdefault(_g, set()).add(_p['weapon'])
                _PORTS.setdefault(_g, {})[_p['weapon']] = _p
except Exception:
    pass
_ANY_FIELDED = set().union(*_FIELDED.values()) if _FIELDED else set()

# A port's tag that the deployed maps lack but the EDITING KIT has is not a fault: the
# levels were built before that tag was wired in (Halo 1's SAW bullet and melee until
# a10/b30 are rebuilt). Those are listed apart, as 'awaiting a rebuild'.
# the kits and their extensions are port_cards' (Halo 1 HCEEK, Halo 2 H2EK), so a port whose
# cards were derived from the kit is checked against the same kit
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
from port_cards import KIT_TAGS, KIT_EXT          # noqa: E402
import map_vault                                  # noqa: E402  (the Baselines folder)
pending = []


def awaiting_rebuild(label, game, tag):
    """True when `label` is a ported weapon's card and every part of `tag` exists in
    that game's editing kit (the maps just predate it)."""
    owner = label.split('/')[0]
    if owner not in _PORTS.get(game, {}) or game not in KIT_TAGS or not tag:
        return False
    cls, _s, rest = tag.partition(' ')
    ext = KIT_EXT.get(cls)
    if not ext:
        return False
    import glob
    # a '*' path (Halo 2's per-character first-person graphs) counts when any match exists
    return all(glob.glob(os.path.join(KIT_TAGS[game], p.strip() + '.' + ext)) if '*' in p
               else os.path.exists(os.path.join(KIT_TAGS[game], p.strip() + '.' + ext))
               for p in rest.split(' & ') if p.strip())


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
    """The maps to read for a game, opened one at a time by the caller: [(mission, file)].

    Each mission's pristine BASELINE -- the bytes every patch rebuilds from
    (halo_patch.existing_baseline with the Baselines folder of settings.json, as
    apply_run and the sibling audits read it). This used to build
    `<MCC>/<game folder>/<name>.map`, the LIVE file the patcher writes: "the tag
    resolves" and "the block is not empty" were answered by whatever the last patch
    left there, or by an older build than the baseline (after 2026-11-13 every Halo 3
    and ODST live map was the previous build), and a map that was not there was dropped
    without a word (review U5 V7). What was read is printed; a mission with no baseline
    is read from its live map and SAID so; a mission with no file at all is named."""
    subdir, missions = MAPS[game]
    root = map_vault.baseline_root()
    out, notes = [], []
    for mid in missions:
        live = hp.default_map_path(MCC, subdir, mid)
        try:
            base = hp.existing_baseline(live, root, subdir)
        except hp.BaselineUnreachable as ex:
            report(f'{game}: {ex} -- its maps were NOT read')
            return []
        if base:
            out.append((mid, base))
        elif live and os.path.isfile(live):
            out.append((mid, live))
            notes.append(f'{mid}: no baseline, the LIVE (patched) map was read')
        else:
            notes.append(f'{mid}: MISSING (no baseline, no live map) -- not read')
    where = os.path.join(root, *subdir.split('/')) if root else 'the .bak beside each map'
    print(f'  {game}: {len(out)} of {len(missions)} map(s) to read ({where}): '
          f'{", ".join(m for m, _f in out) or "none"}')
    for n in notes:
        print(f'      {n}')
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
        if not isinstance(t, dict) or any(t.get(k) for k in PSEUDO_ROWS):
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


def _check_placed(label, game, field, t, quiet):
    """A `placed` target (the inverted Stable Grenades, Halo 1 / 2) is a bit on the
    pickup's scnr Equipment PLACEMENTS, written by halo_patch._apply_placed_flag from
    its own offset table -- not a field of the target's eqip tag. So it is looked up in
    the scnr plugin's Equipment block, and the plugin's offset, element and bit must
    agree with the patcher's table (_PLACED_EQUIP_FLAGS / _MAP_EQUIPMENT)."""
    spec, E = hp._PLACED_EQUIP_FLAGS.get(game), hp._MAP_EQUIPMENT.get(game)
    if spec is None or E is None:
        report(f'{label} [{game}]: placed target, but the patcher has no placement '
               f'flags for {game}', quiet)
        return
    sp = plugin(game, 'scnr')
    fld = sp.find(field, 'Equipment', 0) if sp else None
    if not fld:
        report(f'{label} [{game}]: FIELD not in scnr plugin: {field!r} '
               f'(block Equipment)', quiet)
        return
    want = str(t.get('flag') or '').strip().lower()
    pbit = next((b for nm, b in (fld.get('bits') or {}).items()
                 if nm == want or nm.startswith(want + ' (')), None)
    if (fld['offset'] != spec[0] or fld.get('block_offsets') != [E['items'][0]]
            or fld.get('block_sizes') != [E['items'][1]]
            or pbit is None or pbit != spec[2].get(want)):
        report(f'{label} [{game}]: placed {field!r} / {t.get("flag")!r}: plugin '
               f'@{fld["offset"]} bit {pbit} in block {fld.get("block_offsets")} x '
               f'{fld.get("block_sizes")}, patcher @{spec[0]} bit {spec[2].get(want)} '
               f'in {E["items"]}', quiet)


STEP_KEYS = ('step', 'steps', 'add_step', 'inverse_step', 'inverse_steps', 'from_zero')


def type_problems(t, fld, ladder=()):
    """What is wrong between a row's OPERATOR and the plugin field's TYPE, as sentences
    (review U5 V2). The plugin lookup only ever asked whether the field exists, so a
    multiplier on an enum passed: ten Halo 4 'Distribution Function' cards carried
    `"step": "*1.2"` on enum16 {point, horizontal fan, ...}; 0 x 1.2 is 0, the row
    reported ok and the fan the card promises never engaged.

      flag / set_bit   a flags field, and a bit the plugin names
      choice           an enum, and every `ladder` name one of its options; a
                       `follows_choice` row takes the chosen NAME, so it needs them too
      set              a name needs an enum that has it; a number on an enum must be
                       one of its values
      step ...         never on an enum or a flags field
    """
    out = []
    ftype = str(fld.get('type') or '?')
    enum, flags = ftype.startswith('enum'), ftype.startswith('flags')
    opts, bits = fld.get('options') or {}, fld.get('bits') or {}

    def low(x):
        return str(x).strip().lower()

    bit = next((t[k] for k in ('flag', 'set_bit', 'clear_bit') if t.get(k) is not None), None)
    if bit is not None:
        if not flags:
            out.append(f'the flag {bit!r} is set on a {ftype} field, not a flags field')
        elif low(bit) not in bits:
            out.append(f'the flags field has no bit {bit!r} (it has: '
                       f'{", ".join(sorted(bits)) or "none named"})')
        return out                      # such a row's `set` is its display text
    if t.get('choice') or t.get('follows_choice'):
        if not enum:
            out.append(f'a choice needs an enum, the field is {ftype}')
        else:
            names = (t.get('ladder') or []) if t.get('choice') else ladder
            miss = [n for n in names if low(n) not in opts]
            if miss:
                out.append(f'the enum has no option {", ".join(map(repr, miss))} (it has: '
                           f'{", ".join(sorted(opts))})')
    sv = t.get('set')
    if isinstance(sv, str):
        if not enum:
            out.append(f'"set": {sv!r} names an option, the field is {ftype}')
        elif low(sv) not in opts:
            out.append(f'"set": {sv!r} is not an option of the enum (it has: '
                       f'{", ".join(sorted(opts))})')
    elif isinstance(sv, (int, float)) and not isinstance(sv, bool) and enum and opts \
            and sv not in opts.values():
        out.append(f'"set": {sv!r} is not a value of the enum {sorted(opts.values())}')
    if (enum or flags) and sv is None and not t.get('choice') and not t.get('follows_choice'):
        stepped = [k for k in STEP_KEYS if t.get(k) is not None]
        if stepped:
            out.append(f'"{stepped[0]}": {t[stepped[0]]!r} is an operator, the field is '
                       f'{ftype} -- a multiplier or an addition does not select an '
                       f'option; use "set" (or "choice" / "flag")')
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
    for game in GAMES:
        if game not in MAPS:        # a game added to Missions without a sample list
            report(f'{game}: no sampled maps (MAPS) -- none of its cards is '
                   f'resolution-checked')
    for label, eff, _weapon in iter_effects():
        for game in declared_games(eff):
            if game not in MAPS:
                continue            # an unknown name: structure rule 8 reports it
            if eff.get('skull') and not _targets_of(eff, game, None, None):
                # A whole-map rule applied in code: its `tag` is a class or 'MCC
                # process', not a path, and there is nothing to resolve. The eight
                # Downpour skulls are different -- they carry field rows the patcher
                # applies as ordinary ops, so those go through like any card. (Every
                # skull used to be skipped here, and every matg card below: 153 cards
                # with 311 field rows nobody looked up; Stun Penalty and Stun Time were
                # offered in Halo 4, whose matg has none of their fields. Review U5 V3.)
                continue
            tag = resolve_gamed(eff.get('tag'), game)
            if not isinstance(tag, str) or not tag.strip():
                continue            # no tag in an offered game: structure rule 9
            cls, tpath = hm.split_tag(tag)
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
            ladder = [x for _f, _b, _n, _c, _p, tt in targets if tt.get('choice')
                      for x in (tt.get('ladder') or [])]
            for field, block, nth, ucls, upath, t in targets:
                if t.get('placed'):
                    _check_placed(label, game, field, t, quiet)
                    continue
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
                # the operator against the field's type (an enum is not multiplied)
                for why in type_problems(t, fld, ladder):
                    report(f'{label} [{game}]: {field!r} (block {block!r}): {why}', quiet)
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
        n_read = 0
        for mn, fn in map_paths(game):
            try:
                # read-only: mapped, not loaded -- the baselines are 41 GB
                m = hp.open_map(fn, game, readonly=True)
            except Exception as ex:
                print(f'  (could not open {mn}: {ex})')
                continue
            n_read += 1
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

        if not n_read:
            # Not one map of this game could be read. Every card would come out "tag
            # resolves on 0 maps": loud, but blaming the cards for a missing folder.
            report(f'{game}: NO MAP could be read -- the {len(live)} card(s) offered '
                   f'there were not resolution-checked on a map')
            continue
        for label, tag, cls, tpath, keep in live:
            quiet = is_inert(label, game)
            if not found.get(label):
                if awaiting_rebuild(label, game, tag):
                    pending.append(f'{label} [{game}]: {tag}')
                else:
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


def check_glyphs():
    """GLYPHS -- the ported weapons' pictograms in MCC's live icon font packages (Halo 3,
    ODST, Reach, Halo 4): missing on this machine, or a new port glyph that
    `port_glyphs.py --capture` was not run for. Logic in port_glyphs.problems()."""
    try:
        import port_glyphs
    except Exception as e:                       # the module or its json is missing
        report(f'GLYPHS: port_glyphs could not be loaded ({e})')
        return
    for pr in port_glyphs.problems(MCC):
        report('GLYPHS: ' + pr)
    # the ports' own Halo 4 sound banks in the live sfxbank.pck (port_sounds.py)
    try:
        import port_sounds
    except Exception as e:
        report(f'SOUNDS: port_sounds could not be loaded ({e})')
        return
    # the volume knob (settings.json weapon_port_volume): a bank turned on purpose is
    # not stale. Per game -- the Focus Rifle is a port in Halo 1 AND Halo 4, so the
    # flat merge this used to do let one game's knob shadow the other's (review U4 B2)
    for pr in port_sounds.problems(MCC, volume=port_sounds.volume_knobs()):
        report('SOUNDS: ' + pr)


def check_scores():
    """SCORES -- the metagame score rescale (scoredb_patch): every offered enemy-effect name
    of the four enemy groups must fall in a score category (weight > 0), and every Boss /
    Hero group must have a scoredb bucket. A name this misses scores ZERO in silence at
    patch time -- 185 did until 2026-11-07 (review U4 B8), under a comment promising this
    very test. The per-name table is reports/score_categories.md."""
    try:
        import scoredb_patch
    except Exception as e:
        report(f'SCORES: scoredb_patch could not be loaded ({e})')
        return
    em = DB.get('Enemy modifiers') or {}
    for grp in ('General modifiers', 'Specific Enemy modifier', 'Boss enemy modifier',
                'Hero enemy modifier'):
        g = em.get(grp) or {}
        items = ([(n, x, None) for n, x in g.items()] if grp == 'General modifiers'
                 else [(n, x, e) for e, effs in g.items() for n, x in (effs or {}).items()])
        for n, x, e in items:
            if isinstance(x, dict) and not x.get('ignore') and not scoredb_patch.weight_of(n):
                report(f'SCORES: {grp}{" / " + e if e else ""}: {n!r} has no score category '
                       f'(scoredb_patch.CATEGORIES) -- it scores zero')
    for grp in ('Boss enemy modifier', 'Hero enemy modifier'):
        for who in (em.get(grp) or {}):
            if who not in scoredb_patch.BOSS_TO_BUCKET:
                report(f'SCORES: {grp}: {who!r} has no scoredb bucket (scoredb_patch.BOSS_TO_BUCKET)')


if __name__ == '__main__':
    check_structure()
    n_struct = len(problems)
    print(f'structure checks: {n_struct} problem(s)')
    check_glyphs()
    print(f'port glyph/sound checks: {len(problems) - n_struct} problem(s)')
    n_before = len(problems)
    check_scores()
    print(f'score category checks: {len(problems) - n_before} problem(s)')
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
    if pending:
        print(f'({len(pending)} ported-weapon card(s) awaiting a rebuild -- the tag is in '
              f'the editing kit but not yet in the deployed maps; --all lists them)')
        if '--all' in sys.argv:
            for pr in pending:
                print(' ', pr)
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
