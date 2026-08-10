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
}

# Bosses need class+type precision: Tartarus is not "every brute", he is the
# hero/brute entry. `None` means the boss has no scoredb entry at all.
BOSS_TO_BUCKET = {
    'Prophet Regret': ('leader', 'elite'),
    'Heretic Leader': ('leader', 'elite'),
    'Brute Chieftain': ('hero', 'brute'),
    'Tartarus': ('hero', 'brute'),
    'Sentinel Enforcer': ('*', 'sentinel'),
    # 343 Guilty Spark is not a scored kill in scoredb.xml.
    '343 Guilty Spark': None,
}

GENERIC_TAG_HINT = 'generic'

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

# Effect name -> category. Every one of halo.json's 103 enemy-effect names is here
# exactly once; `test_scoredb` fails if halo.json grows a name this map lacks, so a
# new effect cannot silently score zero.
CATEGORIES = {
    'durability': [
        'Body Vitality', 'Shield Vitality', 'Shield Recharge', 'Body Recharge',
        'Enemy Vitality', 'Enemy Shield', 'Enemy Recharge', 'Enforcer Chassis',
        'Hologram Body Vitality', 'Hologram Shield Vitality',
    ],
    'damage': [
        'Weapon Damage Modifier', 'Melee Damage', 'Beam Damage', 'Enemy damage',
        'Pop Damage', 'Explosion Damage', 'Hunter Fuel Rod Damage',
        'Gravity Cannon', 'Gravity Cannon Projectile',
        'Beam', 'Beam Projectile', 'Needler', 'Needler Damage',
        'Needler Projectile', 'Rocket', 'Rocket Damage', 'Rocket Projectile',
        'Chieftain Hammer Damage', 'Gravity Hammer Damage',
    ],
    'accuracy': [
        'Accuracy', 'Target Tracking & Leading', 'Projectile Error', 'Burst Error',
        'Guidance Vs Player', 'Hologram Accuracy',
        'Hologram Target Tracking & Leading', 'AI Projectile Speed',
    ],
    'rate_of_fire': [
        'Rate of Fire', 'Firing Patterns', 'Burst Seperation', 'Special Fire Delay',
        'New Target Delay', 'Special-Case Firing', 'Overcharge Chance',
        'Hologram Rate of Fire', 'Beam Rate of Fire',
        'Hunter Fuel Rod Rounds per Second', 'Hunter Fuel Rod Charging Time',
        'Hunter Fuel Rod Projectiles Per Shot',
    ],
    'senses': [
        'Vision', 'Hearing Distance', 'Perception', 'Suicide Sensing Distance',
    ],
    'range': [
        'Maximum Firing Distance', 'Maximum Firing Distance Hunter Fuel Rod',
        'Projectile Range Hunter Fuel Rod', 'Pop Radius', 'Explosion Radius',
        'Beam Range', 'Chieftain Hammer Radius', 'Gravity Hammer Radius',
    ],
    'aggression': [
        'Melee Behavior', 'Melee Leap', 'Melee Delay Scale', 'Berserk',
        'Elite Berserk', 'Hunter Berserk', 'Combatform Berserk',
        'Shield down Berserk', 'More Berserking', 'Kamikaze', 'Leader Charge',
        'Gravity Throne', 'Grapple Melee',
    ],
    'positioning': [
        'Cover Properties', 'Cover Chance', 'Firing Positions',
        'Dive From Grenade Chance', 'Retreat', 'Leader Leash',
        'Placement Properties', 'Movement Switching', 'Panic', 'Stun Behavior',
        'Player Stun Time', 'Player Vehicle Ram Chance',
    ],
    'grenades': [
        'Grenades', 'Grenades Chance', 'Grenade Scales', 'Grenade Properties',
    ],
    'ranks': [
        'Upgrade Chance', 'Major Upgrades (Normal)', 'Major Upgrades (Few)',
        'Major Upgrades (Many)',
    ],
    'equipment': [
        'Deployable Shield Use', 'Equipment Use Chance',
    ],
    'flood_forms': [
        'Infection Forms', 'Infestation Speed', 'Stealth Morphs', 'Tank Form',
        'Stalker Form', 'Ranged Form', 'Group Morph',
    ],
}

NAME_TO_CATEGORY = {n: c for c, names in CATEGORIES.items() for n in names}


def weight_of(effect_name, weights=None):
    """The score weight of an effect, or 0 if its name is not categorised."""
    cat = NAME_TO_CATEGORY.get(effect_name)
    if not cat:
        return 0
    return (weights or CATEGORY_WEIGHTS).get(cat, 0)


def _fields(target_list):
    """Field names in a targets list; a `field` may be a per-game dict of names."""
    out = set()
    groups = target_list.values() if isinstance(target_list, dict) else [target_list]
    for grp in groups:
        for t in (grp or []):
            if not isinstance(t, dict):
                continue
            fld = t.get('field')
            if isinstance(fld, dict):
                out.update(v for v in fld.values() if isinstance(v, str) and v)
            elif isinstance(fld, str) and fld:
                out.add(fld)
    return out


def _tag_text(data):
    tag = data.get('tag')
    if isinstance(tag, dict):
        return ' '.join(str(v) for v in tag.values())
    return str(tag or '')


def is_generic_effect(data):
    return GENERIC_TAG_HINT in _tag_text(data)


def own_tag_fields(specific_group):
    """Per enemy, the fields it defines on its OWN (non-generic) character tag.

    That is exactly the set of fields for which the enemy overrides the generic
    fallback, so it is what decides who a generic effect misses.
    """
    own = {}
    for enemy, effects in specific_group.items():
        acc = set()
        for data in effects.values():
            if isinstance(data, dict) and not is_generic_effect(data):
                acc |= _fields(data.get('targets'))
        own[enemy] = acc
    return own


def generic_targets(effect_data, specific_group):
    """Which enemies a generic-tag effect actually reaches.

    An enemy that defines ANY of the effect's fields on its own tag has overridden
    the generic value and is excluded. An effect with no identifiable fields is
    treated as reaching everyone, since we cannot prove an override.
    """
    fields = _fields(effect_data.get('targets'))
    own = own_tag_fields(specific_group)
    if not fields:
        return sorted(own)
    return sorted(e for e, f in own.items() if not (fields & f))


def effect_targets(effect_data, enemy, specific_group):
    """The enemies one effect should raise the score of.

    `enemy` is the halo.json group it was drafted from, or None for a General
    modifier. Returns a sorted list of halo.json enemy names.
    """
    if is_generic_effect(effect_data):
        return generic_targets(effect_data, specific_group)
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


def multipliers_for(effects, specific_group, weights=None, step=0.05,
                    cap_mult=None):
    """Turn a run's applied effects into a per-bucket score multiplier.

    `effects` is halo_patch.collect_effects output. Each enemy effect adds its
    category weight to every enemy it actually reaches -- which for a generic-tag
    effect means only the enemies that have NOT overridden its fields. The summed
    weight becomes `1 + step * total`, so a run that stacks nasty effects on Elites
    pays more for Elites specifically.
    """
    totals = {}
    for eff in effects or []:
        if eff.get('cat') not in (2, 3, 5):      # enemy-specific / enemy-general / boss
            continue
        w = weight_of(eff.get('name'), weights)
        if not w:
            continue
        w *= max(1, int(eff.get('count') or 1))
        if eff.get('cat') == 5:
            bucket = BOSS_TO_BUCKET.get(eff.get('enemy') or eff.get('boss'))
            if bucket:
                totals[bucket] = totals.get(bucket, 0) + w
            continue
        if eff.get('cat') == 2 and not eff.get('_generic_target'):
            names = [eff.get('enemy')]
        else:
            names = effect_targets(eff, eff.get('enemy'), specific_group)
        for nm in names:
            b = ENEMY_TO_BUCKET.get(nm)
            if not b:
                continue                          # e.g. Flood Infection Form
            totals[('*', b)] = totals.get(('*', b), 0) + w

    # A boss bucket is a SUBSET of its type, not an alternative to it: effects that
    # buffed every Brute also buffed Tartarus, so his (hero, brute) weight has to
    # include the type-wide total. Without this the exact key shadows the wider one
    # in _lookup and a boss can end up worth LESS than a rank-and-file enemy.
    for (cls, typ) in list(totals):
        if cls != '*':
            totals[(cls, typ)] += totals.get(('*', typ), 0)

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


def read_baseline(scoredb):
    """Always scale from the PRISTINE file, never from an already-patched one --
    the same .bak baseline model the map patcher uses, so repatching does not
    compound and toggling the option off restores the original values."""
    bak = backup_path(scoredb)
    if not os.path.exists(bak):
        shutil.copy2(scoredb, bak)
    with open(bak, encoding='utf-8') as f:
        return f.read()


def apply(scoredb, multipliers, cap=None, dry_run=False):
    base = read_baseline(scoredb)
    patched, changed = scale_xml(base, multipliers, cap)
    if not dry_run:
        with open(scoredb, 'w', encoding='utf-8', newline='') as f:
            f.write(patched)
    return changed, patched


def restore(scoredb):
    bak = backup_path(scoredb)
    if os.path.exists(bak):
        shutil.copy2(bak, scoredb)
        return True
    return False
