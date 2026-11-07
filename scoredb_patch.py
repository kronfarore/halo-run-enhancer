r"""Patch MCC's campaign metagame point values -- `<MCC>\Data\UI\scoredb.xml`.

The metagame score is NOT tag data and NOT hardcoded in a binary. MCC parses this
plain-text XML at startup and builds float records from it; the disassembly of the
scoring path (MCC-Win64-Shipping.exe+446E54 / +447704 / +44B594) reads `class` and
`type` as two u16 keys and `score` / `score_skull` as the two floats it picks the
larger of. So changing the file changes scoring, with no .map rebuild and no dll edit.

**A FULL MCC RESTART IS REQUIRED.** The file is read once at startup, not per level.
A patch applied while the game runs silently does nothing.

The idea: a run that makes enemies nastier should pay more per kill. Each enemy
effect in halo.json carries a `score` weight (1-5); the weights of the effects a run
actually applied are summed per enemy and turned into a multiplier on that enemy's
base score.

The subtle part is WHO an effect really targets:

  * a Specific Enemy effect on its own character tag hits exactly that enemy;
  * `matg globals\globals` effects are difficulty-wide and hit everyone;
  * `char ai\generic` is a FALLBACK -- an enemy that defines the same field on its
    own character tag overrides it and is NOT affected. halo.json already records
    which fields each enemy defines, so the exclusion set is derivable from it.
    See `generic_targets()`.
"""
import copy
import os
import re
import shutil

import mcc_textfile          # atomic writes, line endings kept (review U4 B9 / N7)

SCOREDB_REL = os.path.join('Data', 'UI', 'scoredb.xml')

# halo.json enemy name -> scoredb `type` bucket. NOTE `jackel`: that spelling is
# MCC's own typo in scoredb.xml and must be matched exactly.
ENEMY_TO_BUCKET = {
    'Elite': 'elite',
    'Grunt': 'grunt',
    'Jackal': 'jackel',
    'Hunter': 'hunter',
    'Brute': 'brute',
    'Bugger': 'bugger',
    'Sentinel': 'sentinel',
    'Flood Combat Form': 'flood_combat',
    'Flood Carrier Form': 'flood_carrier',
    'Flood Pure Form': 'flood_pure',
    # 'Flood Infection Form' has NO scoredb bucket -- MCC does not score infection
    # forms at all. Effects on it therefore cannot move any score; that is a real
    # gap in the data, not a bug here. Kept explicit so it is not "fixed" by
    # guessing a bucket.
    'Flood Infection Form': None,
    # ODST only. Engineers are not enemies in Halo 3, but they are in Mombasa
    # Streets, Kikowani Station and Data Hive, and scoredb.xml already scores them.
    'Engineer': 'engineer',
    # Reach / Halo 4 rows scoredb.xml already has (pawn = Crawler, bishop = Watcher)
    'Skirmisher': 'skirmisher',
    'Knight': 'knight',
    'Crawler': 'pawn',
    'Watcher': 'bishop',
    # the Human family is only drawn under Betrayal, when Marines score as enemies.
    # Outside Betrayal the Marine rows are a PENALTY (negative), so this bucket is
    # reached by a card only while the run holds the Betrayal skull, and only by a card
    # drafted from the Human family -- never by an enemy-general card (review U4 A1:
    # 'General Enemy Vitality' alone had scaled the penalty -50 -> -62).
    'Human': 'marine',
}

# Bosses need class+type precision: Tartarus is not "every brute", he is the
# hero/brute entry. `None` means the boss has no scoredb entry at all. Every key of
# halo.json's Boss and Hero groups must be here (validate_halo_json checks); a group
# that is missing is reported by multipliers_for as 'unscored boss' rather than
# dropped in silence (review U4 B7: nine of fifteen groups were missing).
BOSS_TO_BUCKET = {
    'Prophet Regret': ('leader', 'elite'),        # the 'Prophet' row (150) shares the Zealot's bucket
    'Heretic Leader': ('leader', 'elite'),
    'Brute Chieftain': ('hero', 'brute'),
    'Tartarus': ('hero', 'brute'),
    'Sentinel Enforcer': ('*', 'sentinel'),
    # 343 Guilty Spark is not a scored kill in scoredb.xml.
    '343 Guilty Spark': None,
    # the stock scoredb.xml.bak has a row for each of these five (2026-11-07)
    'Mule': ('infantry', 'mule'),                 # Mule 200
    'Elite Honor Guard': ('hero', 'elite'),       # Elite Honor Guard 150
    'Elite Zealot': ('leader', 'elite'),          # Elite Zealot 75
    'Knight Commander': ('leader', 'knight'),     # Knight Commander 150
    'Jackal Sniper': ('specialist', 'jackel'),    # Jackal Sniper 20
    # no row of their own: the tier row their card describes
    'Elite Specops Commander': ('leader', 'elite'),
    'Elite General': ('leader', 'elite'),
    'Jackal Ranger': ('specialist', 'jackel'),    # the Sniper's row
    'Grunt Ultra': ('specialist', 'grunt'),       # Grunt Ranger 15 (the Hero row is 'Grunt Hero' 25)
}

GENERIC_TAG_HINT = 'generic'      # the last path component of `char ai\generic` (see _is_generic_tag)

# One weight per category instead of 245 per-effect lines. Set by the user
# 2026-08-10 after reviewing the category overview; the scale is RELATIVE (it only
# ranks enemies against each other), with overall payout controlled separately by
# `step` and the Options multiplier.
CATEGORY_WEIGHTS = {
    'durability': 5,
    'rate_of_fire': 5,
    'damage': 4,
    'ranks': 4,
    'accuracy': 3,
    'range': 3,
    'grenades': 3,
    'flood_forms': 3,
    'positioning': 2,
    'senses': 1,
    'aggression': 1,
    'equipment': 1,
}

# Effect name -> category. Every offered enemy-effect name of halo.json's four enemy
# groups (General, Specific Enemy, Boss, Hero) is here exactly once -- 'General <x>'
# scores as <x>, 'Armed: <weapon>' as equipment, 'Hardened: ...' as durability --
# and validate_halo_json.check_scores fails when halo.json grows a name this table
# lacks. Until 2026-11-07 the table stopped at the 103 names of 2026-08-10 while the
# groups grew to 319, so 185 names scored zero in silence and the test this comment
# promised never existed (review U4 B8); a card without a category is now also noted
# at patch time (multipliers_for `notes`). The per-name table: reports/score_categories.md.
CATEGORIES = {
    'durability': [
        'Body Vitality', 'Shield Vitality', 'Shield Recharge', 'Body Recharge',
        'Enemy Vitality', 'Enemy Shield', 'Enemy Recharge', 'Enforcer Chassis',
        'Hologram Body Vitality', 'Hologram Shield Vitality',
        # ODST Engineer: shields every ally around it, so it is durability -- and
        # for the whole squad, not just itself.
        'Shield Boost',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Armor Lock Chance', 'Armor Lock Duration', 'Body Recharge Amount',
        'Body Recharge Delay', 'Body Recharge Time', 'Detonation Body Vitality',
        'Protect Damage Amount', 'Protect Time', 'Recharge Delay', 'Resurrection',
        'Shield Boost Period', 'Shield Boost Radius', 'Shield Boost Strength',
        'Shield Recharge Delay', 'Shield Recharge Time', 'Turret Vitality', 'Turtle Distance',
        'Turtle Threshold', 'Turtle Time',
    ],
    'damage': [
        'Weapon Damage Modifier', 'Melee Damage', 'Beam Damage', 'Enemy damage',
        'Pop Damage', 'Explosion Damage', 'Hunter Fuel Rod Damage',
        'Gravity Cannon', 'Gravity Cannon Projectile',
        'Beam', 'Beam Projectile', 'Needler', 'Needler Damage',
        'Needler Projectile', 'Rocket', 'Rocket Damage', 'Rocket Projectile',
        'Chieftain Hammer Damage', 'Gravity Hammer Damage',
        # ODST Engineer: its corpse rises and detonates, so this is what killing
        # one does TO you rather than a durability trait.
        'Death',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Berserk Damage', 'Death Detonation Time', 'Death Height', 'Ground Smash Damage',
        'Grunt Damage', 'Head Gun Damage', 'Morph Damage', 'Roar Damage', 'Special Damage',
        'Turret Damage',
    ],
    'accuracy': [
        'Accuracy', 'Target Tracking & Leading', 'Projectile Error', 'Burst Error',
        'Guidance Vs Player', 'Hologram Accuracy',
        'Hologram Target Tracking & Leading', 'AI Projectile Speed',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Accuracy Bounds', 'Accuracy Time', 'Distribution Function', 'Head Gun Accuracy',
        'Hologram Target Leading', 'Hologram Target Tracking', 'Target Leading',
        'Target Tracking', 'Tracking & Leading',
    ],
    'rate_of_fire': [
        'Rate of Fire', 'Firing Patterns', 'Burst Seperation', 'Special Fire Delay',
        'New Target Delay', 'Special-Case Firing', 'Overcharge Chance',
        'Hologram Rate of Fire', 'Beam Rate of Fire',
        'Hunter Fuel Rod Rounds per Second', 'Hunter Fuel Rod Charging Time',
        'Hunter Fuel Rod Projectiles Per Shot',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Beam Projectiles Per Shot', 'Beam Salvo', 'Bursting', 'Distance Damage Time',
        'Fight Circle Firing Time', 'Gravity Cannon Projectiles Per Shot',
        'Gravity Cannon Salvo', 'Head Gun Rate of Fire', 'Needler Projectiles Per Shot',
        'Needler Salvo', 'Projectiles Per Shot', 'Rocket Projectiles Per Shot', 'Rocket Salvo',
        'Run Time', 'Special-Fire Chance', 'Special-Fire Delay', 'Spew Chance',
        'Spew Frequency', 'Turret Rate of Fire',
    ],
    'senses': [
        'Vision', 'Hearing Distance', 'Perception', 'Suicide Sensing Distance',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Peripheral Vision', 'Search',
    ],
    'range': [
        'Maximum Firing Distance', 'Maximum Firing Distance Hunter Fuel Rod',
        'Projectile Range Hunter Fuel Rod', 'Pop Radius', 'Explosion Radius',
        'Beam Range', 'Chieftain Hammer Radius', 'Gravity Hammer Radius',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Advance Range', 'Beam Projectile Range', 'Beam Projectile Velocity', 'Beam Velocity',
        'Distance Damage Radius', 'Firing Range', 'Fuel Rod Gravity', 'Fuel Rod Range',
        'Fuel Rod Velocity', 'Gravity Cannon Projectile Range',
        'Gravity Cannon Projectile Velocity', 'Grunt Radius', 'Hunter Radius',
        'Needler Projectile Range', 'Needler Projectile Velocity', 'Rocket Projectile Range',
        'Rocket Projectile Velocity', 'Rocket Radius', 'Sentinel Beam Gravity',
        'Sentinel Beam Range',
    ],
    'aggression': [
        'Melee Behavior', 'Melee Leap', 'Melee Delay Scale', 'Berserk',
        'Elite Berserk', 'Hunter Berserk', 'Combatform Berserk',
        'Shield down Berserk', 'More Berserking', 'Kamikaze', 'Leader Charge',
        'Gravity Throne', 'Grapple Melee',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Berserk Animation', 'Berserk Chance', 'Berserk Cooldown', 'Berserk Count',
        'Berserk Distance', 'Berserk Grenade', 'Berserk Perimeter Range',
        'Berserk Special Chances', 'Cower Time', 'Flee Time', 'Flee Timeout', 'Hamstring',
        'Hamstring Angle', 'Hamstring Distance', 'Hamstring Time', 'I am not scared',
        'Leader Charge Chance', 'Leader Charge Range', 'Melee Chance', 'Melee Delay',
        'Melee Leap Chance', 'Melee Leap Range', 'Melee Leap Velocity', 'Melee Radius',
        'Melee Reach', 'Melee Timing', 'Panic Chance', 'Player Preference', 'Retreat Chance',
        'Shield-Down Berserk Chance', 'Shield-Down Berserk Range', 'Suppress',
        'Surprise Behavior', 'Vengeful Berserk', 'Wildfire',
    ],
    'positioning': [
        'Cover Properties', 'Cover Chance', 'Firing Positions',
        'Dive From Grenade Chance', 'Retreat', 'Leader Leash',
        'Placement Properties', 'Movement Switching', 'Panic', 'Stun Behavior',
        'Player Stun Time', 'Player Vehicle Ram Chance',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Advance', 'Boarding', 'Combat Position Time', 'Cover Threshold', 'Crouch Chance',
        'Defensive Cover', 'Enforcer Chassis Acceleration', 'Enforcer Chassis Speed',
        'Enforcer Chassis Turn', 'Evasion', 'Evasion Properties', 'Fight Circle Angles',
        'Fight Circle Strafe Time', 'Fight Flank Chance', 'Flanking', 'Flight Acceleration',
        'Flight Speed', 'Gravity Jump Cooldown', 'Gravity Jump Descend Gravity',
        'Gravity Jump Float Time', 'Gravity Jump Height', 'Gravity Jump Retreat Radius',
        'Gravity Jump Target Attractor', 'Gravity Jump Trigger Distance',
        'Gravity Throne Acceleration', 'Gravity Throne Speed', 'Gravity Throne Turn',
        'Guard Position Time', 'Hide Behind Cover', 'Hologram Cooldown', 'Hologram Wait Time',
        'Hopping', 'Leap', 'Movement Speed', 'Position Avoid Distance', 'Search: Destroy Cover',
        'Search: Guard', 'Search: Investigate', 'Search: Leap On Cover',
        'Search: Suppressing Fire', 'Search: Uncover', 'Teleport', 'Thrust',
    ],
    'grenades': [
        'Grenades', 'Grenades Chance', 'Grenade Scales', 'Grenade Properties',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Anti-Vehicle Grenade Chance', 'Encounter Grenade Timeout',
        'Grenade Catch Attack Speed', 'Grenade Catch Chance', 'Grenade Catch Cooldown',
        'Grenade Catch Range', 'Grenade Catch Strength', 'Grenade Chance',
        'Grenade Chance Scale', 'Grenade Check Time', 'Grenade Collateral', 'Grenade Range',
        'Grenade Throw Delay', 'Grenade Timer Scale', 'Grenade Velocity', 'Kamikaze Chance',
        'Kamikaze Count',
    ],
    'ranks': [
        'Upgrade Chance', 'Major Upgrades (Normal)', 'Major Upgrades (Few)',
        'Major Upgrades (Many)',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Elite Incursion', 'Few Upgrade Chance', 'Flood Combat Incursion',
        'Flood Infection Incursion', 'Grunt Incursion', 'Hunter Incursion',
        'Infection Conversion', 'Jackal Incursion', 'Many Upgrade Chance',
        'Normal Upgrade Chance', 'Sentinel Incursion', 'Shard Spawning', 'Spawn Count',
        'Transformation Time',
    ],
    'equipment': [
        'Deployable Shield Use', 'Equipment Use Chance',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Arm Shield', 'Shield Projection', 'Shield Projector Duration',
        'Shield Projector Recharge', 'Shield Use Recent Damage', 'Shield Use Vitality',
    ],
    'flood_forms': [
        'Infection Forms', 'Infestation Speed', 'Stealth Morphs', 'Tank Form',
        'Stalker Form', 'Ranged Form', 'Group Morph',
        # review U4 B8 (2026-11-07): names that scored zero, placed by the fix plan's keyword
        # rules -- the table and the choices are in reports/score_categories.md
        'Morph Distance', 'Ranged Distance', 'Stalk Charge', 'Stalk Range', 'Throttle Distance',
    ],
}

NAME_TO_CATEGORY = {n: c for c, names in CATEGORIES.items() for n in names}
# General cards are named "General <card>" (2026-10-01); they score as the card they
# were named after.
NAME_TO_CATEGORY.update({'General ' + n: c for n, c in list(NAME_TO_CATEGORY.items())})


def weight_of(effect_name, weights=None):
    """The score weight of an effect, or 0 if its name is not categorised."""
    cat = NAME_TO_CATEGORY.get(effect_name)
    if not cat and str(effect_name).startswith('Armed: '):
        cat = 'equipment'       # Halo 1 'Armed: <weapon>' cards: what the enemy carries
    if not cat and str(effect_name).startswith('Hardened: '):
        # 'Hardened: <armour> vs <damage>' (damage_rows.py): an enemy-general card that
        # makes one armour class take less from one damage type -- durability
        cat = 'durability'
    if not cat:
        return 0
    return (weights or CATEGORY_WEIGHTS).get(cat, 0)


def _resolve(value, game, games=None):
    """The GUI's resolve_gamed rule, without the GUI: a per-game dict gives this game's
    entry, else its 'default', else the nearest EARLIER game's in `games` order (ODST takes
    Halo 3's), else None; anything else is returned as it is. With no `game` the dict is
    returned whole (the callers then take every game's value, as before 2026-11-07)."""
    if not isinstance(value, dict) or game is None:
        return value
    if game in value:
        return value[game]
    if 'default' in value:
        return value['default']
    if games and game in games:
        for g in reversed(games[:games.index(game)]):
            if g in value:
                return value[g]
    return None


def _fields(target_list, game=None, games=None):
    """Field names in a targets list, as `game` sees them: a per-game `targets` dict and a
    per-game `field` dict resolve for the game (every game's value when `game` is None);
    a target carrying a `games` allow-list that leaves the game out is a field this tag
    does not have there. `skip_games` and `ignore` rows are kept: the field exists on the
    tag whether or not the card is offered."""
    out = set()
    targets = _resolve(target_list, game, games)
    groups = targets.values() if isinstance(targets, dict) else [targets]
    for grp in groups:
        for t in (grp or []):
            if not isinstance(t, dict):
                continue
            if game is not None and t.get('games') and game not in t['games']:
                continue
            fld = _resolve(t.get('field'), game, games)
            if isinstance(fld, dict):
                out.update(v for v in fld.values() if isinstance(v, str) and v)
            elif isinstance(fld, str) and fld:
                out.add(fld)
    return out


def _tag_values(data, game=None, games=None):
    tag = _resolve(data.get('tag'), game, games)
    if isinstance(tag, dict):
        return [str(v) for v in tag.values()]
    return [str(tag or '')]


def _is_generic_tag(tag):
    """`char ai\\generic` (or Halo 4's / Reach's `char ai\\generic*`), also as a member of a
    '&'-joined list: the LAST path component is `generic`. Reach's
    objects\\characters\\spartans_ai\\ai\\spartan_generic merely CONTAINS the word -- the old
    substring test took every card naming it for a generic one, in every game."""
    for one in str(tag).split('&'):
        one = one.strip()
        if ' ' in one:
            one = one.split(' ', 1)[1]                     # the class word
        last = one.replace('/', '\\').rstrip('\\*').rsplit('\\', 1)[-1].strip().lower()
        if last == GENERIC_TAG_HINT:
            return True
    return False


def is_generic_effect(data, game=None, games=None):
    """Does this effect edit the shared `char ai\\generic` tag -- in `game`, when given
    (a per-game tag dict resolves for it); with no game, in any game it names."""
    return any(_is_generic_tag(t) for t in _tag_values(data, game, games))


def own_tag_fields(specific_group, game=None, games=None):
    """Per enemy, the fields it defines on its OWN (non-generic) character tag -- in `game`.

    That is exactly the set of fields for which the enemy overrides the generic
    fallback, so it is what decides who a generic effect misses. Per game, because the
    same card can sit on the enemy's own tag in one game and on ai\\generic in the next
    (Flood Carrier's Accuracy: Halo 1 own, Halo 2 generic), and a field one game has
    (a Halo 1-only Elite Vision card) must not exclude the Elite from another game's
    generic card (review U4 B5).
    """
    own = {}
    for enemy, effects in specific_group.items():
        acc = set()
        for data in effects.values():
            if isinstance(data, dict) and not is_generic_effect(data, game, games):
                acc |= _fields(data.get('targets'), game, games)
        own[enemy] = acc
    return own


def generic_targets(effect_data, specific_group, game=None, games=None):
    """Which enemies a generic-tag effect actually reaches.

    An enemy that defines ANY of the effect's fields on its own tag has overridden
    the generic value and is excluded. An effect with no identifiable fields is
    treated as reaching everyone, since we cannot prove an override.
    """
    fields = _fields(effect_data.get('targets'), game, games)
    own = own_tag_fields(specific_group, game, games)
    if not fields:
        return sorted(own)
    return sorted(e for e, f in own.items() if not (fields & f))


def effect_targets(effect_data, enemy, specific_group, game=None, games=None):
    """The enemies one effect should raise the score of.

    `enemy` is the halo.json group it was drafted from, or None for a General
    modifier. Returns a sorted list of halo.json enemy names.
    """
    if is_generic_effect(effect_data, game, games):
        return generic_targets(effect_data, specific_group, game, games)
    if enemy is None:
        return sorted(specific_group)          # matg globals: difficulty-wide
    return [enemy]


# --------------------------------------------------------------------------
# the XML side
# --------------------------------------------------------------------------

_ENEMY_RE = re.compile(r'<Enemy\b[^>]*/>')
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def parse_entries(xml_text):
    """Every <Enemy .../> element as (span, attrs). Regex rather than an XML parser
    on purpose: the file is rewritten in place so comments, indentation and the
    original attribute order all survive, which keeps a diff reviewable."""
    out = []
    for m in _ENEMY_RE.finditer(xml_text):
        attrs = dict(_ATTR_RE.findall(m.group(0)))
        out.append(((m.start(), m.end()), attrs))
    return out


def bucket_of(attrs):
    """(class, type) for an entry, e.g. ('hero', 'brute')."""
    t = attrs.get('type', '')
    c = attrs.get('class', '')
    return (c.rsplit('_class_', 1)[-1] if '_class_' in c else None,
            t.rsplit('_type_', 1)[-1] if '_type_' in t else None)


def _lookup(multipliers, bucket):
    """Exact (class, type) wins; ('*', type) applies to every class of that type."""
    cls, typ = bucket
    if (cls, typ) in multipliers:
        return multipliers[(cls, typ)]
    return multipliers.get(('*', typ))


def _skull_buckets(eff):
    """('*', type) rows a per-enemy skull's points go to; None for a general skull.
    Thunderstorm: <enemy> also pays on the tier above (kills of the promoted units score
    as that species), Downpour: <enemy> on the tier below, by halo_patch's ladder."""
    enemy = eff.get('skull_enemy')
    if not enemy:
        return None
    kind = str(eff.get('skull') or '').lower()
    names = [enemy]
    if kind in ('thunderstorm', 'downpour'):
        try:
            import halo_patch
            fams = {f: (fac, t) for f, fac, t, _w in halo_patch._TS_FAMILIES}
        except Exception:
            fams = {}
        if enemy in fams:
            fac, tier = fams[enemy]
            want = tier + (1 if kind == 'thunderstorm' else -1)
            names += [f for f, (fc, t) in fams.items() if fc == fac and t == want]
    return [('*', ENEMY_TO_BUCKET[n]) for n in names if ENEMY_TO_BUCKET.get(n)]


def multipliers_for(effects, specific_group, weights=None, step=0.05,
                    cap_mult=None, game=None, games=None, notes=None):
    """Turn a run's applied effects into a per-bucket score multiplier.

    `effects` is halo_patch.collect_effects output. Each enemy effect adds its
    category weight to every enemy it actually reaches -- which for a generic-tag
    effect means only the enemies that have NOT overridden its fields. The summed
    weight becomes `1 + step * total`, so a run that stacks nasty effects on Elites
    pays more for Elites specifically.

    `specific_group` is halo.json's Specific Enemy group AS THIS GAME SEES IT (the
    enhancer drops the effects -- and the enemies -- the game does not field), and
    `game` / `games` (the game and the ordered game list) resolve its per-game tags and
    fields, so generic targets are decided for one game (review U4 B5). Without them
    every game's values are taken together, as before. `notes` (a list) receives one
    line per card that could not score -- a boss group with no bucket -- so the caller
    can show it instead of a silent zero.
    """
    totals = {}
    general = 0     # skull points every enemy row takes ('*', '*'; see scale_xml)
    # The marine bucket exists only under Betrayal: a saved run may still carry a Human
    # card after the skull expired, and every General card lists 'Human' among its
    # targets (matg: the whole group; ai\generic: every family that does not override).
    betrayal = any(str(e.get('skull') or '').lower() == 'betrayal' for e in effects or [])
    for eff in effects or []:
        if eff.get('skull'):
            # Skull cards: their halo.json `score_points` -- the real skull's MCC
            # multiplier (careerdb.xml) in weight points -- on every enemy (a general
            # skull) or on the enemy a per-enemy skull names. Not times `count`: a skull
            # is drawn once.
            pts = int(eff.get('score_points') or 0)
            if not pts:
                continue
            rows = _skull_buckets(eff)
            if rows is not None and not rows and notes is not None:
                # a per-enemy skull on an enemy with no scoredb bucket (Flood Infection Form):
                # its points cannot move any row (review U4 N9)
                notes.append('%s: %s has no scoredb bucket (%d skull points not scored)'
                             % (eff.get('name'), eff.get('skull_enemy'), pts))
            if rows is None:
                general += pts
                if str(eff.get('skull')).lower() == 'betrayal':
                    # Only CREATE the bucket: the general loop below gives it `general`
                    # (Betrayal's own points included) exactly once, like every other
                    # '*' row. It has to exist because scale_xml's ('*', '*') fallback
                    # skips negative rows on purpose. Adding pts here as well paid
                    # Betrayal twice on the Marines (x1.4 against everyone's x1.2).
                    totals.setdefault(('*', 'marine'), 0)
            else:
                for b in rows:
                    totals[b] = totals.get(b, 0) + pts
            continue
        if eff.get('cat') not in (2, 3, 5):      # enemy-specific / enemy-general / boss
            continue
        w = weight_of(eff.get('name'), weights)
        if not w:
            if notes is not None:
                notes.append('%s: not scored (no score category -- see validate_halo_json)'
                             % eff.get('name'))
            continue
        w *= max(1, int(eff.get('count') or 1))
        if eff.get('cat') == 5:
            who = eff.get('enemy') or eff.get('boss')
            bucket = BOSS_TO_BUCKET.get(who)
            if bucket:
                totals[bucket] = totals.get(bucket, 0) + w
            elif who not in BOSS_TO_BUCKET and notes is not None:
                # None = known to be unscored (343 Guilty Spark); a missing KEY is a gap
                notes.append('unscored boss: %s has no scoredb bucket (%s not scored)'
                             % (who, eff.get('name')))
            continue
        if eff.get('cat') == 2 and not eff.get('_generic_target'):
            names = [eff.get('enemy')]
        else:
            names = effect_targets(eff, eff.get('enemy'), specific_group, game, games)
        for nm in names:
            b = ENEMY_TO_BUCKET.get(nm)
            if not b:
                continue                          # e.g. Flood Infection Form
            if b == 'marine' and not (betrayal and eff.get('enemy') == 'Human'):
                continue                          # the betrayal penalty is not a card's to scale
            totals[('*', b)] = totals.get(('*', b), 0) + w

    # A boss bucket is a SUBSET of its type, not an alternative to it: effects that
    # buffed every Brute also buffed Tartarus, so his (hero, brute) weight has to
    # include the type-wide total. Without this the exact key shadows the wider one
    # in _lookup and a boss can end up worth LESS than a rank-and-file enemy.
    # The type total is added as it stands (before the skull points), and the general
    # skull points then go to EVERY bucket, boss ones included -- `+= type or general`
    # used to drop the skull points whenever a type total existed (Iron + a Brute card
    # + a Tartarus card: hero/brute 6 -> x1.30 against every Brute's x1.55).
    for (cls, typ) in list(totals):
        if cls != '*':
            totals[(cls, typ)] += totals.get(('*', typ), 0)
    if general:
        for b in list(totals):
            totals[b] += general
        totals[('*', '*')] = general        # every other enemy row (scale_xml)

    out = {}
    for bucket, total in totals.items():
        m = 1.0 + step * total
        if cap_mult:
            m = min(m, cap_mult)
        out[bucket] = m
    return out


def scale_xml(xml_text, multipliers, cap=None):
    """Rewrite each entry's score/score_skull by multipliers[bucket].

    Values stay integers because that is how the file ships; MCC reads them as
    floats either way. Anything with no multiplier is left byte-for-byte alone.
    """
    entries = parse_entries(xml_text)
    out = []
    last = 0
    changed = 0
    for (start, end), attrs in entries:
        mult = _lookup(multipliers, bucket_of(attrs))
        if mult is not None and bucket_of(attrs)[1] != 'marine':
            # A negative row is a PENALTY (Marines, Spartans, the human vehicles): no bucket
            # a card reaches may scale it. Only the Marine rows take one, from their own
            # key, which multipliers_for hands out under Betrayal alone -- and the
            # Betrayal step then flips them positive.
            try:
                if float(attrs.get('score', 0)) < 0:
                    mult = None
            except ValueError:
                pass
        if mult is None and ('*', '*') in multipliers:
            # a general skull's points reach every ENEMY row (positive score) the run's
            # cards did not name -- never a betrayal row (negative) or a 0
            try:
                if float(attrs.get('score', 0)) > 0:
                    mult = multipliers[('*', '*')]
            except ValueError:
                pass
        if not mult or mult == 1:
            continue
        chunk = xml_text[start:end]
        new = chunk
        for key in ('score', 'score_skull'):
            if key not in attrs:
                continue
            try:
                base = float(attrs[key])
            except ValueError:
                continue
            val = int(round(base * mult))
            if cap is not None:
                val = min(val, cap)
            new = re.sub(r'(\b%s\s*=\s*")[^"]*(")' % key,
                         lambda m: m.group(1) + str(val) + m.group(2), new, count=1)
        if new != chunk:
            out.append(xml_text[last:start])
            out.append(new)
            last = end
            changed += 1
    out.append(xml_text[last:])
    return ''.join(out), changed


def backup_path(scoredb):
    return scoredb + '.bak'


StockError = mcc_textfile.StockError      # a replaced live file that is not stock either


class BaselineError(StockError):
    """No usable pristine copy: the live file is already modified and no .bak exists."""


_SCORE_VAL = re.compile(r'(\bscore(?:_skull)?\s*=\s*")[^"]*(")')


def _skeleton(text):
    """The file with every score value blanked and whitespace folded: what this tool's own
    writes never change. A live file with another skeleton than the .bak was replaced from
    outside (mcc_textfile.guard)."""
    return re.sub(r'\s+', ' ', _SCORE_VAL.sub(r'\1\2', text)).strip()


def is_pristine(text):
    """The shipped file's SIGNS: every Marine row and every human-vehicle row negative, and
    at least one Marine row present. Magnitudes are not checked -- the only writer that
    touches the file without a baseline is a sign flip, so signs are what a .bak seeded
    from a modified file could carry (a scaled file is always written from a .bak)."""
    marines = [float(m.group(2)) for m in MARINE_ROW.finditer(text)]
    vehicles = [float(m.group(2)) for m in VEHICLE_ROW.finditer(text)]
    return bool(marines) and all(v < 0 for v in marines + vehicles)


def ensure_baseline(scoredb, notes=None):
    """The .bak path, creating the .bak from the live file when there is none -- and only
    when the live file passes is_pristine(). Every writer calls this BEFORE it writes,
    so a .bak is never seeded from a file an earlier sign flip (Betrayal scoring, the
    Halo 2 vehicle fix, the metagame test) had already changed and then regenerated as
    'restored from .bak' forever after (review U4 B3). Raises BaselineError otherwise.

    With a .bak present, mcc_textfile.guard() checks that the live file is still the stock
    copy or this tool's own write: a file replaced underneath (an MCC update) that passes
    is_pristine() becomes the new stock copy, with a line in `notes`; one that does not
    raises StockError and nothing is written (review U4 C1)."""
    bak = backup_path(scoredb)
    if os.path.exists(bak):
        mcc_textfile.guard(scoredb, bak, _skeleton, is_pristine, 'scoredb.xml', notes)
        return bak
    text = mcc_textfile.read_text(scoredb)
    if not is_pristine(text):
        raise BaselineError('scoredb.xml is already modified and no .bak exists -- '
                            'Steam verify, then patch again')
    shutil.copy2(scoredb, bak)
    mcc_textfile.record_bak(bak)
    return bak


def read_baseline(scoredb, notes=None):
    """Always scale from the PRISTINE file, never from an already-patched one --
    the same .bak baseline model the map patcher uses, so repatching does not
    compound and toggling the option off restores the original values. The .bak is
    taken by ensure_baseline(), which refuses a live file that is not stock."""
    bak = ensure_baseline(scoredb, notes)
    return mcc_textfile.read_text(bak)


def apply(scoredb, multipliers, cap=None, dry_run=False, notes=None):
    """The live file = the .bak scaled by `multipliers` ({} puts the shipped bytes back).
    Written atomically (mcc_textfile): MCC reads this file once at startup, and a file
    truncated by a crash mid-write would be what it scores with all session. `notes`
    (a list) receives a line when the stock copy had to be refreshed first."""
    if dry_run and not os.path.exists(backup_path(scoredb)):
        base = mcc_textfile.read_text(scoredb)         # a dry run seeds nothing (review U4 N6)
    else:
        base = read_baseline(scoredb, notes)
    patched, changed = scale_xml(base, multipliers, cap)
    if not dry_run:
        mcc_textfile.write_text_atomic(scoredb, patched)
        mcc_textfile.record_write(scoredb, backup_path(scoredb))
    return changed, patched


def restore(scoredb):
    """The stock copy back into place: 'restored', or 'refreshed' when the live file turned
    out to be a NEWER stock file (it then IS the stock copy; nothing to put back), or False
    with no .bak. StockError for a replaced file that is not stock either."""
    bak = backup_path(scoredb)
    if not os.path.exists(bak):
        return False
    if mcc_textfile.guard(scoredb, bak, _skeleton, is_pristine, 'scoredb.xml') == 'refreshed':
        return 'refreshed'
    mcc_textfile.copy_atomic(bak, scoredb)
    mcc_textfile.record_write(scoredb, bak)
    return 'restored'


# Marines are the one bucket whose sign is a GAMEPLAY question rather than a constant.
# Normally killing one is a betrayal and costs points; under the Betrayal skull they are
# ordinary enemies and should pay out like any other kill.
MARINE_ROW = re.compile(r'(type="_campaign_metagame_bucket_type_marine"[^/]*?)'
                        r'score="(-?[\d.]+)"')


def set_marine_sign(scoredb, positive, notes=None):
    """Force every Marine row's score positive or negative, magnitude untouched.

    Sign-only and idempotent on purpose, so it composes with `apply()` rather than
    fighting it: the scaler rewrites the whole file from the pristine baseline on every
    patch, and this runs after it and only flips what it finds. Calling it twice, or
    calling it on a file the scaler just regenerated, both land on the same result.

    Returns the number of rows changed (0 when they were already the wanted sign).
    """
    return _set_sign(scoredb, MARINE_ROW, positive, notes)


# The human vehicles: negative rows in the shipped file. MCC scores a destroyed vehicle
# by its TYPE, never by who drives it, so a Flood-driven Warthog costs the row like a
# Marine-driven one (measured on Quarantine Zone, Legendary: -400 = -100 x4,
# reports/score_vehicle_test.jsonl). An empty vehicle scores nothing either way.
HUMAN_VEHICLES = ('mongoose', 'warthog', 'scorpion', 'hornet', 'pelican', 'sabre',
                  'falcon')
VEHICLE_ROW = re.compile(r'(type="_campaign_metagame_bucket_type_(?:%s)"[^/]*?)'
                         r'score="(-?[\d.]+)"' % '|'.join(HUMAN_VEHICLES))


def set_vehicle_sign(scoredb, positive, notes=None):
    """The human vehicle rows positive or negative, magnitude untouched -- the same
    sign-only, idempotent contract as `set_marine_sign`. A vehicle kill takes the plain
    table path, so a positive row pays out without the betrayal sign guard."""
    return _set_sign(scoredb, VEHICLE_ROW, positive, notes)


def _set_sign(scoredb, row, positive, notes=None):
    try:
        ensure_baseline(scoredb, notes)     # the pristine copy BEFORE the first flip
    except BaselineError:
        if positive:
            raise          # a non-stock sign over a file with no baseline: refused, reported
        # Towards stock (a flipped file an earlier patch left, no .bak yet): the write goes
        # ahead, and the next writer seeds the .bak from the result once its signs are stock.
    text = mcc_textfile.read_text(scoredb)
    n = [0]

    def sub(m):
        cur = float(m.group(2))
        want = abs(cur) if positive else -abs(cur)
        if want != cur:
            n[0] += 1
        return '%sscore="%g"' % (m.group(1), want)

    out = row.sub(sub, text)
    if n[0]:
        mcc_textfile.write_text_atomic(scoredb, out)
        if os.path.exists(backup_path(scoredb)):
            mcc_textfile.record_write(scoredb, backup_path(scoredb))
    return n[0]
