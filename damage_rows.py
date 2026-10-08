r"""damage_rows.py -- the "Effective" (player) and "Hardened" (enemy) cards: scale how much
one DAMAGE TYPE does to one ARMOUR CLASS.

From Halo 2 on a jpt! names a row of the matg Damage Table (Damage Groups -> Armor
Modifiers -> Damage Multiplier) by its General / Specific Damage string ids, and a material
names the armour column by its General / Specific Armor. The engine BINARY-SEARCHES the
group and the row by stringid and MULTIPLIES every row it finds (jpt general x specific
group, material general x specific armour; a missing row counts 1) -- see player_armour.py.
So a card scales the GENERAL rows only: (any group of the damage type) x (any armour row of
the class), in every Damage Table element ([0] normal play, [1] the native Tilt-skull table
from Halo 3 on). Specific groups ('sniper', 'anti_flood', 'kill_flood', ...) are never
touched: the engine multiplies them on top, scaling both would double-apply.

    apply_op(m, game, registry, spec, op_str) -> list of result rows
    describe(m, game, spec) -> short text of the rows a card acts on (patcher display)
    plan(m, game, spec) -> the rows/columns a card would touch (self-test, display)

`spec` = the target's `damage_row` key: {"damage": <DAMAGE key or 'anything'>,
"armour": <ARMOUR key>}.

THE PLAYER. From Halo 2 on the player wears the same armour names as Elites (H2/H3
Arbiter, ODST body = Brute hide, Reach/H4 Spartans = Elite rows), so a card moves the damage
the player takes as well -- intended (user, 2026-10-08) -- unless the Patching option
'Give the player its own armour rows' ran player_armour.apply first: the player then has
rows of its own (keys = its materials' own Name stringids) that never match an armour name
here -- asserted per op. Halo 1's player columns (Cyborg, Cyborg Energy Shield) are its own
and never in a class below.

STEPS. halo.json gives each card a multiplying `step` and an `add_step`; the enhancer makes
two cards of it ('(x)' and '(+)'/'(-)', halo_enhancer._step_variants) that stack on the
same rows. A target's `row_floor` keeps a non-zero row from being pushed below it (a
subtraction would otherwise turn a 0.25 row into an immunity); a row already under the
floor is never raised.

HALO 1 has no table: every jpt! carries 33 per-material floats (0x200 Dirt .. 0x280 Hunter
Shield). A card scales the class's COLUMNS on every jpt! of the damage type; the jpt!s are
classified by H1_JPT below (the Halo 2 group of the same weapon, from
sprint_toolkit/damage_categories_h1_odst.json), plus any weapons\...\melee.

RULES: values only change (no row is added -- a (group, armour) pair without a row stays at
the engine's x1 and is COUNTED, so we know later whether row creation is needed); rows at 0
(immunities) stay 0; results are clamped >= 0, or >= `floor` (see STEPS). The arrays' key order is untouched, so the
binary search still finds every row (asserted).
"""
import struct

import halo_map as hm

EFFECT = 'Damage rows'

#: damage type -> (player-facing label, GENERAL damage groups). Vehicle/turret groups
#: (bullet_vehicle, plasma_vehicle, bullet_turret, plasma_turret, ...) are not player weapon
#: types and are never included. (The Halo 2 SAW port shipped with bullet_vehicle; every
#: Halo 2 patch now points it at bullet_slow -- halo_patch._fix_h2_saw_group.)
DAMAGE = {
    'bullets': ('Bullets', ('bullet_slow',)),
    'precision': ('Precision rounds', ('bullet_fast', 'bullet_fast_h3')),     # _h3 = ODST BR
    'plasma': ('Plasma', ('plasma_slow', 'plasma_fast')),
    'needles': ('Needles', ('needle',)),                                    # Reach / Halo 4
    'explosives': ('Explosives', ('explosion_small', 'explosion_large', 'explosion_attached')),
    'blades': ('Blades and melee', ('cutting', 'melee')),
    'fire': ('Fire', ('burning',)),
    'lasers': ('Lasers', ('laser',)),
}
ANYTHING = 'anything'           # every type above ("Anything vs Flood")

#: armour class -> (label, armour row names). Per-game overrides in ARMOUR_GAME.
#:  shields  energy_shield_thin only: energy_shield_thick is the Jackal hand shield and
#:           turret shields, _solid / _invincible are vehicles and scripted immunities.
#:  flesh    soft_organic (Grunt/Jackal/Drone/Marine flesh) + soft_inorganic (the Grunt's
#:           methane-pack body armour, hard_metal_thin_cov_grunt; also Warthog/Mongoose
#:           seats -- harmless). Reach adds tough_organic: there it is the Drone and Mule,
#:           not Brutes (Reach Brutes are soft_organic).
#:  vehicles hard_metal_thick + hard_metal_solid (Hunter plates are hard_metal_solid from
#:           H2 on, shared with Scorpion/Wraith/Pelican/Phantom) + the vehicles' breakable
#:           parts brittle_mech (engines), brittle_elec (Covenant anti-grav pods, Phantom),
#:           brittle_glass (windscreens). brittle / brittle_explosive (props, fusion coils)
#:           and Halo 4's brittle_elec_hum_env (scenery) are not vehicles. ODST's `hunter`
#:           specific row (only plasma_vehicle has one) is included for completeness.
#:  flood    the floodflesh rows; Halo 3's brittle_flood too (no material wears it today).
ARMOUR = {
    'shields': ('Shields', ('energy_shield_thin',)),
    'armour': ('Armour', ('hard_metal_thin',)),
    'flesh': ('Flesh', ('soft_organic', 'soft_inorganic')),
    'brute_hide': ('Brute hide', ('tough_organic',)),
    'flood': ('Flood', ('soft_floodflesh', 'tough_floodflesh', 'hard_floodflesh', 'brittle_flood')),
    'hunters': ('Hunters', ('soft_organic_flesh_hunter',)),
    'vehicles': ('Vehicles and Hunter plates', ('hard_metal_thick', 'hard_metal_solid', 'brittle_mech',
                                                'brittle_elec', 'brittle_glass', 'hunter')),
}
ARMOUR_GAME = {
    ('Halo Reach', 'flesh'): ('soft_organic', 'soft_inorganic', 'tough_organic'),
}

# --- Halo 1 -------------------------------------------------------------------------------
H1_COLUMNS_AT = 0x200
H1_COLUMNS = ('Dirt', 'Sand', 'Stone', 'Snow', 'Wood', 'Metal (Hollow)', 'Metal (Thin)',
              'Metal (Thick)', 'Rubber', 'Glass', 'Force Field', 'Grunt', 'Hunter Armor',
              'Hunter Skin', 'Elite', 'Jackal', 'Jackal Energy Shield', 'Engineer',
              'Engineer Force Field', 'Flood Combat Form', 'Flood Carrier Form', 'Cyborg',
              'Cyborg Energy Shield', 'Armored Human', 'Human', 'Sentinel', 'Monitor', 'Plastic',
              'Water', 'Leaves', 'Elite Energy Shield', 'Ice', 'Hunter Shield')
H1_PLAYER_COLUMNS = ('Cyborg', 'Cyborg Energy Shield')
#: armour class -> Halo 1 jpt! columns. Shields = Elite Energy Shield (Sentinels wear it
#: too); never the Jackal hand shield. Flesh includes Human (Marines) and Engineer (no
#: campaign Engineers; the column is flesh). Hunters = the Hunter Skin column (Precision vs
#: Hunters: the Sniper Rifle, the Battle Rifle port).
H1_ARMOUR = {
    'shields': ('Elite Energy Shield',),
    'armour': ('Elite',),
    'flesh': ('Grunt', 'Jackal', 'Human', 'Engineer'),
    'flood': ('Flood Combat Form', 'Flood Carrier Form'),
    'hunters': ('Hunter Skin',),
    'vehicles': ('Metal (Hollow)', 'Metal (Thin)', 'Metal (Thick)', 'Hunter Armor', 'Hunter Shield'),
}
_B = chr(92)


def _p(*parts):
    return _B.join(parts)


#: Halo 1 jpt! -> damage type, from damage_categories_h1_odst.json (weapons +
#: ai_and_vehicles; the type of the Halo 2 group of the same weapon). Not listed, on
#: purpose: the Plasma Pistol charged bolt (emp), the vehicle guns (bullet_vehicle /
#: plasma_vehicle: Warthog, Scorpion MG, Ghost, Banshee bolts, Shade, the plasma cannon
#: impact). The SAW port bullet is Bullets, as every other SAW (bullet_slow).
H1_JPT = {
    _p('weapons', 'assault rifle', 'bullet'): 'bullets',
    _p('weapons', 'pistol', 'bullet'): 'bullets',
    _p('weapons', 'shotgun', 'pellet'): 'bullets',
    _p('weapons', 'smg', 'bullet'): 'bullets',                           # port
    _p('weapons', 'saw', 'bullet'): 'bullets',                           # port
    _p('weapons', 'sniper rifle', 'sniper bullet'): 'precision',
    _p('weapons', 'battle rifle', 'bullet'): 'precision',                # port
    _p('weapons', 'plasma pistol', 'bolt'): 'plasma',
    _p('weapons', 'plasma rifle', 'bolt'): 'plasma',
    _p('weapons', 'needler', 'detonation damage'): 'plasma',
    _p('weapons', 'needler', 'impact damage'): 'plasma',
    _p('weapons', 'sentinel beam', 'beam'): 'plasma',                    # port
    _p('weapons', 'covenant carbine', 'slug'): 'plasma',                 # port (plasma_fast in H2/H3)
    _p('characters', 'sentinel', 'beam'): 'plasma',
    _p('weapons', 'needler', 'explosion'): 'explosives',
    _p('weapons', 'rocket launcher', 'explosion'): 'explosives',
    _p('weapons', 'fuel rod gun', 'explosion'): 'explosives',
    _p('weapons', 'fuel rod gun', 'grunt explosion'): 'explosives',
    _p('weapons', 'frag grenade', 'explosion'): 'explosives',
    _p('weapons', 'plasma grenade', 'explosion'): 'explosives',
    _p('weapons', 'plasma grenade', 'attached'): 'explosives',
    _p('vehicles', 'banshee', 'fuel rod explosion'): 'explosives',
    _p('vehicles', 'wraith', 'explosion'): 'explosives',
    _p('vehicles', 'scorpion', 'shell explosion'): 'explosives',
    _p('weapons', 'plasma_cannon', 'effects', 'plasma_cannon_explosion'): 'explosives',
    _p('weapons', 'energy sword', 'melee'): 'blades',
    _p('weapons', 'energy sword', 'lunge strike'): 'blades',
    _p('weapons', 'plasma_cannon', 'effects', 'plasma_cannon_melee'): 'blades',
    _p('weapons', 'flamethrower', 'explosion'): 'fire',
    _p('weapons', 'flamethrower', 'impact damage'): 'fire',
}

GAMES_TABLE = ('Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4')
ALL_GAMES = ('Halo 1',) + GAMES_TABLE

#: The 28 combos the user approved (2026-10-08): (damage, armour, games asked for). Each
#: is an "Effective: <damage> vs <armour>" player card and a "Hardened: <armour> vs
#: <damage>" enemy card. halo.json carries the games where the rows also EXIST and are
#: not all 0 (sprint_toolkit/damage_rows_selftest.py --census measures that).
_H1_H3 = ('Halo 1', 'Halo 2', 'Halo 3')
COMBOS = [
    # core
    ('bullets', 'shields', ALL_GAMES), ('bullets', 'flesh', ALL_GAMES),
    ('precision', 'shields', ALL_GAMES), ('plasma', 'shields', ALL_GAMES),
    ('plasma', 'armour', ALL_GAMES), ('explosives', 'shields', ALL_GAMES),
    ('explosives', 'vehicles', ALL_GAMES), ('blades', 'shields', ALL_GAMES),
    ('bullets', 'brute_hide', ('Halo 2', 'Halo 3', 'Halo 3: ODST')),
    (ANYTHING, 'flood', _H1_H3),
    # extras
    ('bullets', 'armour', ALL_GAMES), ('bullets', 'flood', _H1_H3),
    ('precision', 'flesh', ALL_GAMES), ('precision', 'armour', ALL_GAMES),
    ('precision', 'hunters', ('Halo 1', 'Halo 2', 'Halo 3')),
    ('plasma', 'flesh', ALL_GAMES), ('plasma', 'brute_hide', ('Halo 2', 'Halo 3', 'Halo 3: ODST')),
    ('plasma', 'vehicles', ALL_GAMES),
    ('needles', 'shields', ('Halo Reach', 'Halo 4')), ('needles', 'armour', ('Halo Reach', 'Halo 4')),
    ('explosives', 'flesh', ALL_GAMES), ('explosives', 'flood', _H1_H3),
    ('blades', 'flesh', ALL_GAMES), ('blades', 'flood', _H1_H3),
    # Halo 2: rows exist, nothing in the campaign burns yet (the cut gravity rifle) --
    # kept for the Flamethrower port (user, 2026-10-08)
    ('fire', 'flesh', ('Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST')),
    ('fire', 'flood', ('Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST')),
    ('lasers', 'vehicles', ('Halo 3', 'Halo Reach', 'Halo 4')),
    ('lasers', 'shields', ('Halo 3', 'Halo Reach', 'Halo 4')),
]


def h1_type(name):
    """Halo 1 jpt! path -> damage type key or None. Every weapons\\...\\melee is melee."""
    n = str(name or '').lower()
    t = H1_JPT.get(n)
    if t:
        return t
    if n.startswith('weapons' + _B) and n.endswith(_B + 'melee'):
        return 'blades'
    return None


def damage_groups(damage):
    if damage == ANYTHING:
        out = []
        for _l, gs in DAMAGE.values():
            out += list(gs)
        return tuple(out)
    return DAMAGE[damage][1]


def damage_types(damage):
    return tuple(DAMAGE) if damage == ANYTHING else (damage,)


def armour_rows(game, armour):
    return ARMOUR_GAME.get((str(game).strip(), armour)) or ARMOUR[armour][1]


def label(spec):
    d = spec.get('damage')
    a = spec.get('armour')
    dl = 'Anything' if d == ANYTHING else DAMAGE.get(d, (d,))[0]
    return '%s vs %s' % (dl, ARMOUR.get(a, (a,))[0])


def _row(field, ok, old=None, new=None, reason=None, **kw):
    r = {'effect': EFFECT, 'field': field, 'ok': ok}
    if old is not None:
        r['old'] = old
    if new is not None:
        r['new'] = new
    if reason:
        r['reason'] = reason
    r.update(kw)
    return r


def _check_spec(spec):
    if not isinstance(spec, dict):
        return 'damage_row must be a dict'
    d, a = spec.get('damage'), spec.get('armour')
    if d != ANYTHING and d not in DAMAGE:
        return 'unknown damage type %r' % (d,)
    if a not in ARMOUR:
        return 'unknown armour class %r' % (a,)
    return None


# --- plan -----------------------------------------------------------------------------------
def plan(m, game, spec):
    """What a card touches. Halo 2 on:
      {'kind': 'table', 'hits': [(table, group name, armour name, value offset, value)],
       'zeros': n, 'missing': [(table, group, armour)], 'absent_groups': [...],
       'absent_armour': [...], 'arrays': [(rows base, rows count)], 'player_keys': set}
    Halo 1:
      {'kind': 'jpt', 'hits': [(jpt name, column, value offset, value)], 'zeros': n,
       'jpts': [names], 'columns': [...]}"""
    game = str(game).strip()
    bad = _check_spec(spec)
    if bad:
        raise ValueError(bad)
    if game == 'Halo 1':
        return _plan_h1(m, spec)
    if game not in GAMES_TABLE:
        raise ValueError('no damage table in %s' % game)
    import player_armour as pa
    c = pa._Ctx(m, game)
    if c.matg is None:
        raise ValueError('no globals tag')
    nm = {}

    def name(v):
        if v not in nm:
            nm[v] = pa.sid_name(m, game, v)
        return nm[v]

    want_g = set(damage_groups(spec['damage']))
    want_a = set(armour_rows(game, spec['armour']))
    player_keys = {k for k, _o in getattr(m, '_player_armour_keys', ())}
    hits, missing, zeros, arrays = [], [], 0, []
    seen_g, seen_a = set(), set()
    tables = c.tables()
    all_armour = set()
    for _t, groups in tables:
        for _ge, _g, _rn, _rb, rows in groups:
            all_armour.update(name(k) for k, _v in rows)
    for t, groups in tables:
        for ge, g, rn, rb, rows in groups:
            gname = name(g)
            if gname not in want_g:
                continue
            seen_g.add(gname)
            arrays.append((rb, rn))
            have = set()
            for r, (k, v) in enumerate(rows):
                an = name(k)
                if an not in want_a:
                    continue
                if k in player_keys:
                    raise AssertionError('player armour key %s matches armour class %s'
                                         % (an, spec['armour']))
                have.add(an)
                seen_a.add(an)
                if v == 0.0:
                    zeros += 1
                    continue
                hits.append((t, gname, an, rb + r * 8 + 4, v))
            for an in sorted(want_a & all_armour - have):
                missing.append((t, gname, an))
    return {'kind': 'table', 'hits': hits, 'zeros': zeros, 'missing': missing,
            'absent_groups': sorted(want_g - seen_g), 'absent_armour': sorted(want_a - all_armour),
            'arrays': arrays, 'player_keys': player_keys, 'tables': len(tables)}


def _plan_h1(m, spec):
    cols = []
    for a in (spec['armour'],):
        cols += list(H1_ARMOUR.get(a, ()))
    assert not set(cols) & set(H1_PLAYER_COLUMNS), 'a class maps to a player column'
    types = set(damage_types(spec['damage']))
    hits, zeros, jpts = [], 0, []
    for name, base in m.find_tags('jpt!', '*'):
        if h1_type(name) not in types:
            continue
        jpts.append(name)
        for col in cols:
            off = base + H1_COLUMNS_AT + 4 * H1_COLUMNS.index(col)
            v = struct.unpack_from('<f', m.data, off)[0]
            if v == 0.0:
                zeros += 1
                continue
            hits.append((name, col, off, v))
    return {'kind': 'jpt', 'hits': hits, 'zeros': zeros, 'jpts': jpts, 'columns': cols,
            'missing': [], 'absent_groups': [], 'absent_armour': []}


def _keys(m, arrays):
    return [bytes(m.data[rb + i * 8:rb + i * 8 + 4]) for rb, rn in arrays for i in range(rn)]


def _sorted(m, rb, rn):
    ks = [struct.unpack_from('<i', m.data, rb + i * 8)[0] for i in range(rn)]
    return all(a <= b for a, b in zip(ks, ks[1:]))


# --- apply -----------------------------------------------------------------------------------
def apply_op(m, game, registry, spec, op_str, floor=None):
    """Scale one card's rows by `op_str` (the stacked op, e.g. '*1.4' or '+0.4'). See the
    module docstring. `floor`: no non-zero row ends below it (one already below stays).
    Returns result rows (one summary row; ok False with a reason on failure)."""
    game = str(game).strip()
    lab = label(spec) if not _check_spec(spec) else str(spec)
    parsed = hm.parse_operator(op_str)
    if not parsed:
        return [_row(lab, False, reason='blank/invalid operator')]
    oper, val = parsed
    try:
        p = plan(m, game, spec)
    except (ValueError, AssertionError) as ex:
        return [_row(lab, False, reason=str(ex))]
    if not p['hits']:
        return [_row(lab, True, skip=True,
                     reason='no non-zero row for %s in this map' % lab)]
    keys_before = _keys(m, p.get('arrays', ()))
    sorted_before = [_sorted(m, rb, rn) for rb, rn in p.get('arrays', ())]
    f = hm.OP_FUNCS[oper]
    olds = []
    for h in p['hits']:
        off, v = h[-2], h[-1]
        nv = max(0.0 if floor is None else min(v, float(floor)), f(v, val))
        struct.pack_into('<f', m.data, off, nv)
        olds.append(v)
    if game != 'Halo 1':
        if _keys(m, p['arrays']) != keys_before or \
                [_sorted(m, rb, rn) for rb, rn in p['arrays']] != sorted_before:
            raise AssertionError('damage-row keys moved')        # never: values only
    typ = sorted(olds)[len(olds) // 2]
    if p['kind'] == 'jpt':
        where = '%d value(s) on %d damage effect(s), columns %s' % (
            len(p['hits']), len({h[0] for h in p['hits']}), ', '.join(p['columns']))
        tag = 'jpt! *'
    else:
        tbls = sorted({h[0] for h in p['hits']})
        where = '%d row(s) in table%s %s (%s vs %s)' % (
            len(p['hits']), 's' if len(tbls) > 1 else '', '/'.join('[%d]' % t for t in tbls),
            '/'.join(sorted({h[1] for h in p['hits']})), '/'.join(sorted({h[2] for h in p['hits']})))
        tag = 'matg globals' + _B + 'globals'
    extra = []
    if p['zeros']:
        extra.append('%d immunity row(s) at 0 kept' % p['zeros'])
    if p['missing']:
        extra.append('%d pair(s) without a row (engine x1, not added)' % len(p['missing']))
    return [_row(lab, True, tag=tag, old='%d value(s), typical %g' % (len(olds), typ),
                 new='%s%g: %s%s' % ({'mul': 'x', 'add': '+', 'sub': '-', 'set': '='}[oper], val, where,
                                     ('; ' + '; '.join(extra)) if extra else ''))]


def describe(m, game, spec):
    """Patcher display: how many rows the card acts on and their typical value."""
    try:
        p = plan(m, game, spec)
    except (ValueError, AssertionError) as ex:
        return '? (%s)' % ex
    if not p['hits']:
        return '— no non-zero row in this map'
    vals = sorted(h[-1] for h in p['hits'])
    typ = vals[len(vals) // 2]
    if p['kind'] == 'jpt':
        return '%d value(s) on %d damage effect(s), typical %g (range %g-%g)' % (
            len(vals), len({h[0] for h in p['hits']}), typ, vals[0], vals[-1])
    t0 = [h for h in p['hits'] if h[0] == 0]
    show = ', '.join('%s/%s %g' % (h[1], h[2], h[4]) for h in t0[:6])
    return '%d row(s), typical %g%s%s' % (
        len(vals), typ, ('  [0]: ' + show + (' ...' if len(t0) > 6 else '')) if t0 else '',
        ('  (%d pair(s) have no row: x1)' % len(p['missing'])) if p['missing'] else '')


# --- no immunities (Options -> Patching) ----------------------------------------------------
#: the option's minimum: every in-scope row (0 included) ends at least here
LIFT_FLOOR = 0.1
#: damage groups left alone: they are MEANT to do nothing (screen-shake effects, triggers)
LIFT_SKIP_GROUPS = ('no_damage',)
#: armour rows left alone (substrings): scripted invulnerability (Guilty Spark, set pieces,
#: Reach / Halo 4 invulnerable objects) and what is not armour at all (water, terrain)
LIFT_SKIP_ARMOUR = ('invincible', 'invulnerable', 'liquid', 'terrain')
#: Halo 1 columns left alone: the environment, and the Monitor (Guilty Spark)
H1_LIFT_SKIP = ('Dirt', 'Sand', 'Stone', 'Snow', 'Wood', 'Plastic', 'Water', 'Leaves', 'Ice',
                'Monitor')


def lift_plan(m, game):
    """The rows the no-immunities option raises: [(offset, old value, label)] plus the
    skipped zero count. From Halo 2 on: every Damage Table element, every group but
    LIFT_SKIP_GROUPS, every armour row but LIFT_SKIP_ARMOUR (the player's own rows
    included). Halo 1: the armour columns of every jpt! that does damage to something
    (an all-zero profile is a no-damage effect and stays)."""
    game = str(game).strip()
    out, skipped = [], 0
    if game == 'Halo 1':
        cols = [i for i, c in enumerate(H1_COLUMNS) if c not in H1_LIFT_SKIP]
        for name, base in m.find_tags('jpt!', '*'):
            vals = [(i, struct.unpack_from('<f', m.data, base + H1_COLUMNS_AT + 4 * i)[0])
                    for i in cols]
            if not any(v > 0 for _i, v in vals):
                skipped += sum(1 for _i, v in vals if v < LIFT_FLOOR)
                continue
            for i, v in vals:
                if v < LIFT_FLOOR:
                    out.append((base + H1_COLUMNS_AT + 4 * i, v,
                                '%s / %s' % (str(name).rsplit(_B, 1)[-1], H1_COLUMNS[i])))
        return out, skipped
    import player_armour as pa
    c = pa._Ctx(m, game)
    if c.matg is None:
        raise ValueError('no globals tag')
    nm = {}

    def name(v):
        if v not in nm:
            nm[v] = pa.sid_name(m, game, v) or ''
        return nm[v]
    for t, groups in c.tables():
        for _ge, g, _rn, rb, rows in groups:
            gname = name(g)
            for r, (k, v) in enumerate(rows):
                if v >= LIFT_FLOOR:
                    continue
                an = name(k)
                if gname in LIFT_SKIP_GROUPS or any(s in an for s in LIFT_SKIP_ARMOUR):
                    skipped += 1
                    continue
                out.append((rb + r * 8 + 4, v, '[%d] %s / %s' % (t, gname, an)))
    return out, skipped


def lift_immunities(m, game):
    """Options -> Patching 'No immunities': every in-scope damage row below LIFT_FLOOR
    (immunities at 0 and near-immunities like EMP vs vehicles at 0.001) is set to it.
    Values only -- no key moves, the arrays stay sorted. Returns result rows."""
    lab = 'No immunities'
    try:
        hits, skipped = lift_plan(m, game)
    except ValueError as ex:
        return [_row(lab, False, reason=str(ex))]
    if not hits:
        return [_row(lab, True, skip=True, reason='no row below %g' % LIFT_FLOOR)]
    zeros = sum(1 for _o, v, _l in hits if v == 0.0)
    for off, _v, _l in hits:
        struct.pack_into('<f', m.data, off, LIFT_FLOOR)
    return [_row(lab, True, tag='jpt! *' if str(game).strip() == 'Halo 1' else 'matg globals',
                 old='%d immunit%s at 0, %d row(s) below %g' % (
                     zeros, 'y' if zeros == 1 else 'ies', len(hits) - zeros, LIFT_FLOOR),
                 new='%g (%d left alone: no-damage group, invincible / water / terrain%s)' % (
                     LIFT_FLOOR, skipped, ', no-damage effects' if str(game).strip() == 'Halo 1' else ''))]
