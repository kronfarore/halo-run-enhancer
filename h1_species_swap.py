r"""Halo 1: species replacement cards -- the patch-time pass (2026-10-06).

Every enemy actor variant (and the 13 Marine variants, as kit COPIES on a chain) is
resident in all ten levels since 2026-10-06 (sprint_toolkit/h1_all_enemies.py; memory
h1-all-enemies-every-map). These cards SPAWN them: each pick turns 10% of a level's
enemies into the card's species, for the rest of the run.

What the a10 tests proved, and what therefore decides the design:
  * the team is per ENCOUNTER (scnr encounter +0x24): Flood squads inside a Covenant
    encounter fight beside the Covenant. So a card converts WHOLE encounters and sets
    their team (Covenant 3, Flood 4, Sentinel 5, Human 2) -- the new species then fights
    the level's own enemies as well as the player (confirmed on a10 v2);
  * every species spawns and behaves on any level (a10 v1).

THE SHARE is counted on the HIGHEST difficulty (squad Insane count +0x7E): the level's
enemies are the placed enemy squads; encounters are drawn in a seeded order (scenario
tag name + card name, so co-op machines agree) and taken while that brings the total
closer to the share. An encounter is left alone when any of its squads is not a plain
enemy (an ally, a vehicle or turret driver, a boss), rides a vehicle by script
(vehicle_load_magic), or is a scripted SET PIECE (command lists, seats, attachments,
teleports, custom animations on it: a10's cryo_bane Elite). Squads already of the
card's species keep what they are.

TIERS (user, 2026-10-06). Each actor is ranked 1-4 by its own variant and becomes the
same tier of the card's species; where the tier offers several weapons the replaced
actor's weapon is carried over if one carries it, else one is drawn (seeded):
    Grunt     minor | major | spec-ops needler | spec-ops fuel rod
    Jackal    minor | major | major | major
    Elite     minor | major | spec-ops, stealth | commander, stealth major sword
    Hunter    hunter | hunter | hunter major | hunter major
    Sentinel  sentinel/defensive | major | shielded | shielded major
    Flood Infection  infection x5 | infection x10 | carrier | carrier x2   (squad counts)
    Flood Combat     Human (AR, pistol, plasma pistol, needler, plasma rifle) |
                     Elite (any armed form) | heavy Human (rocket, sniper, shotgun) |
                     heavy Elite or Stealth (Flak Cannon = fuel rod, Energy Sword)
    Human (ally)     Marine | armoured Marine | armoured sniper / shotgun | armoured majors
Ranking a replaced actor: Grunt minor 1, major 2, spec-ops 3, spec-ops fuel rod 4;
Jackal minor 1, major 2; Elite minor 1, major 2, spec-ops / stealth 3, commander /
stealth major 4; Hunter 3, major 4; Sentinel 1, major 2, shielded 3, shielded major 4;
Flood (user): infection 1, carrier 2, combat Human 3, combat Elite / stealth 4.
Variants no level ships (Flood Elite with fuel rod or sword, Flood Human with a sniper
rifle) are built in a SLOT by the Armed pass's machinery (h1_enemy_weapons.Level.clone).

ACTOR PALETTE ENTRIES, in this order: an entry already naming the variant; an entry no
squad or starting location uses any more (a species Thunderstorm / Downpour moved away
frees its entries); a new entry while the palette is under 64; a free slot filled with
the variant; else the actor keeps its old variant (reported).

The Marine variants exist on most levels only as chain COPIES whose Major Variant is
the residency chain, not a promotion: before a copy spawns, its Major Variant is set to
its real major (the plan file's chain_major).

ORDER in halo_patch.apply_run: Thunderstorm / Downpour -> THIS -> Betrayal / Schism
(they then turn the new Marines / allied Sentinels like any others) -> Assassins ->
Armed cards (they reuse this pass's Level, so slots and aliases are shared) -> Spawn
Count and the other cards.
"""
import json
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.join(HERE, 'sprint_toolkit')
if TOOLKIT not in sys.path:
    sys.path.insert(0, TOOLKIT)

import h1_variants as hv          # noqa: E402
import h1_variant_slots as vs     # noqa: E402

BS = chr(92)
PLAN_FILE = os.path.join(TOOLKIT, 'h1_all_enemies_plan.json')
PALETTE_MAX = 64
ENC_TEAM, SQ_NORMAL, SQ_INSANE = 0x24, 0x7C, 0x7E
TEAM = {'covenant': 3, 'flood': 4, 'sentinel': 5, 'human': 2}


def C(*parts):
    return BS.join(('characters',) + parts)


GRUNT, JACKAL, ELITE = 'grunt', 'jackal', 'elite'
FCE, FCH = 'floodcombat elite', 'floodcombat_human'

# card key -> (faction, species folders it counts as, {tier: [entry]}).
# entry: variant path | ('clone', base variant, weapon key) | ('count', variant, mult)
CARDS = {
    'grunt': ('covenant', ('grunt',), {
        1: [C(GRUNT, 'grunt minor plasma pistol'), C(GRUNT, 'grunt minor needler')],
        2: [C(GRUNT, 'grunt major plasma pistol'), C(GRUNT, 'grunt major needler')],
        3: [C(GRUNT, 'grunt specops needler')],
        4: [C(GRUNT, 'grunt specops fuel rod')]}),
    'jackal': ('covenant', ('jackal',), {
        1: [C(JACKAL, 'jackal minor plasma pistol')],
        2: [C(JACKAL, 'jackal major plasma pistol')],
        3: [C(JACKAL, 'jackal major plasma pistol')],
        4: [C(JACKAL, 'jackal major plasma pistol')]}),
    'elite': ('covenant', ('elite',), {
        1: [C(ELITE, 'elite minor', 'elite minor plasma rifle'),
            C(ELITE, 'elite minor', 'elite minor needler')],
        2: [C(ELITE, 'elite major', 'elite major plasma rifle'),
            C(ELITE, 'elite major', 'elite major needler')],
        3: [C(ELITE, 'elite specops', 'elite specops plasma rifle'),
            C(ELITE, 'elite specops', 'elite specops needler'),
            C(ELITE, 'elite stealth', 'stealth elite plasma rifle')],
        4: [C(ELITE, 'elite commander', 'elite commander plasma rifle'),
            C(ELITE, 'elite commander', 'elite commander energy sword'),
            C(ELITE, 'elite stealth', 'stealth elite major energy sword')]}),
    'hunter': ('covenant', ('hunter',), {
        1: [C('hunter', 'hunter')], 2: [C('hunter', 'hunter')],
        3: [C('hunter', 'hunter major')], 4: [C('hunter', 'hunter major')]}),
    'sentinel': ('sentinel', ('sentinel',), {
        1: [C('sentinel', 'sentinel'), C('sentinel', 'sentinel_defensive')],
        2: [C('sentinel', 'sentinel major')],
        3: [C('sentinel', 'sentinel_shielded')],
        4: [C('sentinel', 'sentinel_shielded major')]}),
    'flood infection': ('flood', ('flood_infection', 'floodcarrier'), {
        1: [('count', C('flood_infection', 'flood_infection'), 5)],
        2: [('count', C('flood_infection', 'flood_infection'), 10)],
        3: [('count', C('floodcarrier', 'floodcarrier'), 1)],
        4: [('count', C('floodcarrier', 'floodcarrier'), 2)]}),
    'flood combat': ('flood', ('floodcombat',), {
        1: [C(FCH, FCH + ' ' + w) for w in
            ('assault rifle', 'pistol', 'plasma pistol', 'needler', 'plasma rifle')],
        2: [C(FCE, FCE + ' ' + w) for w in
            ('assault rifle', 'needler', 'pistol', 'plasma pistol', 'plasma rifle',
             'rocket launcher', 'shotgun', 'sniper rifle')],
        3: [C(FCH, FCH + ' rocket launcher'), C(FCH, FCH + ' shotgun'),
            ('clone', C(FCH, FCH + ' rocket launcher'), 'sniper')],
        4: [('clone', C(FCE, FCE + ' rocket launcher'), 'fuel rod'),
            ('clone', C(FCE, FCE + ' rocket launcher'), 'sword'),
            ('clone', C(FCE, FCE + ' stealth unarmed'), 'fuel rod'),
            ('clone', C(FCE, FCE + ' stealth unarmed'), 'sword')]}),
    'human': ('human', ('marine',), {
        1: [C('marine', 'marine ' + w) for w in
            ('assault rifle', 'needler', 'plasma rifle', 'shotgun')],
        2: [C('marine_armored', 'marine_armored ' + w) for w in
            ('assault rifle', 'needler', 'plasma rifle')],
        3: [C('marine_armored', 'marine_armored sniper rifle'),
            C('marine_armored', 'marine_armored shotgun major')],
        4: [C('marine_armored', 'marine_armored ' + w + ' major') for w in
            ('assault rifle', 'plasma rifle', 'sniper rifle', 'shotgun')]}),
}
# the weapon a clone carries, read off the stock variant that already carries it
CLONE_WEAPON_FROM = {
    'fuel rod': C(GRUNT, 'grunt specops fuel rod'),
    'sword': C(ELITE, 'elite commander', 'elite commander energy sword'),
    'sniper': C(FCE, FCE + ' sniper rifle'),
}
# cards drawn in this order when several are active (fixed, so co-op machines agree)
ORDER = ('hunter', 'elite', 'jackal', 'grunt', 'sentinel', 'flood combat',
         'flood infection', 'human')

# script functions that make an encounter a set piece (never converted)
SETPIECE_WORDS = ('command_list', 'vehicle', 'attach', 'detach', 'teleport', 'animation',
                  'set_team')
# Only calls that depend on WHO the unit is: scripted paths (command lists), seats
# (vehicle_load_magic, ai_go_to_vehicle, ai_vehicle_encounter), attachments, teleports,
# custom animations. NOT ai_erase (area cleanup), ai_braindead, damage / vitality /
# drop-item calls: any species takes those (a10 v2: a Hunter squad in crossfire_anti,
# which the script makes invulnerable and erases, worked). NOT 'magic' either:
# ai_magically_see_encounter names nearly every encounter.


def species(name):
    p = (name or '').lower().split(BS)
    return p[1] if len(p) > 2 and p[0] == 'characters' else ''


def tier_of(name):
    """Rank 1-4 of a replaced actor's variant (module docstring)."""
    n = (name or '').lower()
    sp = species(n)
    leaf = n.rsplit(BS, 1)[-1]
    if sp == 'grunt':
        return 4 if 'fuel rod' in leaf else 3 if 'specops' in leaf else \
            2 if 'major' in leaf else 1
    if sp == 'jackal':
        return 2 if 'major' in leaf else 1
    if sp == 'elite':
        if 'commander' in leaf or ('stealth' in leaf and 'major' in leaf):
            return 4
        return 3 if ('specops' in leaf or 'stealth' in leaf) else 2 if 'major' in leaf else 1
    if sp == 'hunter':
        return 4 if 'major' in leaf else 3
    if sp == 'sentinel':
        if 'shielded' in leaf:
            return 4 if 'major' in leaf else 3
        return 2 if 'major' in leaf else 1
    if sp.startswith('flood_infection'):
        return 1
    if sp.startswith('floodcarrier'):
        return 2
    if sp == FCH:
        return 3
    if sp.startswith('floodcombat'):
        return 4
    if sp.startswith('marine'):
        return 4 if 'major' in leaf else 2 if sp == 'marine_armored' else 1
    return 1


def _load_plan():
    try:
        with open(PLAN_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def anchor_copy(path):
    p = path.split(BS)
    return BS.join(p[:2] + ['anchor'] + p[2:])


# ----------------------------------------------------------------------------- scripts
def setpiece_names(m, why=None):
    """Lower-case encounter names some script treats as a set piece (SETPIECE_WORDS):
    an ai name argument of such a call, directly or through (ai_actors X)."""
    import enemy_count as ec
    t = ec._tree(m, 'Halo 1')
    blob = ec._h1_strings(m)

    def text(node):
        o = struct.unpack_from('<I', m.data, t.base + node['i'] * t.size + 0xC)[0]
        if not (0 <= o < len(blob)):
            return None
        e = blob.find(b'\0', o)
        return blob[o:e if e >= 0 else len(blob)].decode('latin-1').strip().lower()

    def subtree(node, depth=0):
        """Every node text under argument `node`, through nested calls
        ((list_get (ai_actors X) 0), (unit (...)))."""
        yield text(node)
        v = node.get('value')
        if depth > 6 or v in (None, 0xFFFFFFFF):
            return
        g = t.at(v & 0xFFFF)
        if g and g['vtype'] == 2 and g['i'] != node['i'] and (v >> 16) == g['salt']:
            for a in ec._args(t, g):
                yield from subtree(a, depth + 1)

    out = set()
    for i in range(t.n):
        r = t.at(i)
        if not r or r['vtype'] != 2 or r['next'] == 0xFFFFFFFF or r['salt'] == 0:
            continue
        fname = text(r) or ''
        if not any(w in fname for w in SETPIECE_WORDS):
            continue
        for a in ec._args(t, r):
            for n in subtree(a):
                if n:
                    out.add(n.split('/')[0])
                    if why is not None:
                        why.setdefault(n.split('/')[0], set()).add(fname)
    return out


# ----------------------------------------------------------------------------- palette
def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def _used_entries(lv):
    used = set()
    for enc in hv._elems(lv.m, lv.s + hv.S_ENC, hv.S_ENC_SZ):
        for sq in hv._elems(lv.m, enc + hv.SQ, hv.SQ_SZ):
            used.add(_i16(lv.m, sq + hv.SQ_TYPE))
            for sl in hv._elems(lv.m, sq + hv.SL, hv.SL_SZ):
                used.add(_i16(lv.m, sl + hv.SL_TYPE))
    return used


def _set_entry(lv, i, name):
    m = lv.m
    struct.pack_into('<I', m.data, lv.pal[i] + 4, m.tag_name_ptr(('actv', name)))
    struct.pack_into('<I', m.data, lv.pal[i] + 0xC, m.tag_id(('actv', name)))
    lv.pal_names[i] = name


def _ref_to(m, name):
    ref = bytearray(16)
    ref[0:4] = b'vtca'
    if name and m.tag_id(('actv', name)) is not None:
        struct.pack_into('<I', ref, 4, m.tag_name_ptr(('actv', name)))
        struct.pack_into('<I', ref, 0xC, m.tag_id(('actv', name)))
    else:
        struct.pack_into('<I', ref, 0xC, 0xFFFFFFFF)
    return bytes(ref)


class Swapper:
    def __init__(self, m, lv, index_fn):
        self.m, self.lv, self.index_fn = m, lv, index_fn
        self.plan = _load_plan()
        self.cache = {}                # entry key -> palette index (or None)
        self.claimed = set()           # palette entries this pass gave a variant
        self.notes = []
        self.recycled = self.appended = self.slotted = 0

    def resolve(self, name):
        """The resident variant to use for `name` (a Marine chain copy where the stock
        variant is not in this map), its chain major fixed."""
        if name in self.lv.tags:
            return name
        copy = anchor_copy(name)
        if copy in self.lv.tags:
            real = (self.plan.get('chain_major') or {}).get(copy)     # a copy path
            if real:
                stock = real.replace(BS + 'anchor', '', 1)
                real = self.resolve(stock)     # the stock major, else its copy (fixed)
            b = self.lv.tags[copy]
            self.m.data[b + hv.REF_MAJOR:b + hv.REF_MAJOR + 16] = _ref_to(self.m, real)
            return copy
        return None

    def entry(self, name):
        """Palette index for resident variant `name` (module docstring order)."""
        lv = self.lv
        if name in lv.pal_names:
            return lv.pal_names.index(name)
        used = _used_entries(lv) | self.claimed
        for i, n in enumerate(lv.pal_names):
            if i not in used and n and not n.lower().startswith(
                    'characters' + BS + 'enhancer' + BS):
                self.notes.append('palette %d %s -> %s (unused)' % (
                    i, n.rsplit(BS, 1)[-1], name.rsplit(BS, 1)[-1]))
                _set_entry(lv, i, name)
                self.claimed.add(i)
                self.recycled += 1
                return i
        if len(lv.pal_names) < PALETTE_MAX:
            self.appended += 1
            return lv.palette_index(name)
        if lv.free_slots:
            sl = lv.free_slots.pop(0)
            src = lv.tags[name]
            vs.fill_slot(self.m, sl, src,
                         bytes(self.m.data[src + hv.REF_WEAPON:src + hv.REF_WEAPON + 16]),
                         None, bytes(self.m.data[src + hv.REF_MAJOR:src + hv.REF_MAJOR + 16]))
            lv.alias[vs.slot_path(sl)] = name
            self.slotted += 1
            return lv.palette_index(vs.slot_path(sl))
        return None

    def target(self, e):
        """(palette index, count multiplier, label) for one tier entry, or None."""
        key = e if isinstance(e, str) else tuple(e)
        if key in self.cache:
            return self.cache[key]
        out = None
        if isinstance(e, str) or e[0] == 'count':
            name, mult = (e, 1) if isinstance(e, str) else (e[1], e[2])
            res = self.resolve(name)
            idx = self.entry(res) if res else None
            out = (idx, mult, name.rsplit(BS, 1)[-1] + ('' if mult == 1 else ' x%d' % mult)) \
                if idx is not None else None
        else:
            _k, base, wkey = e
            carrier = self.lv.tags.get(CLONE_WEAPON_FROM[wkey])
            weapon = hv._ref_name(self.m, carrier, hv.REF_WEAPON) if carrier is not None else None
            if weapon and base in self.lv.tags:
                idx, note = self.lv.clone(base, weapon, self.index_fn())
                if idx is not None:
                    out = (idx, 1, '%s with %s' % (base.rsplit(BS, 1)[-1], wkey))
                    if note:
                        self.notes.append('%s with %s: %s' % (base.rsplit(BS, 1)[-1], wkey, note))
                else:
                    self.notes.append('%s with %s: %s' % (base.rsplit(BS, 1)[-1], wkey, note))
        self.cache[key] = out
        return out

    def weapon_of(self, e):
        name = e if isinstance(e, str) else e[1]
        if not isinstance(e, str) and e[0] == 'clone':
            carrier = self.lv.tags.get(CLONE_WEAPON_FROM[e[2]])
            return hv._ref_name(self.m, carrier, hv.REF_WEAPON) if carrier is not None else None
        res = self.resolve(name) if name not in self.lv.tags else name
        b = self.lv.tags.get(res) if res else None
        return hv._ref_name(self.m, b, hv.REF_WEAPON) if b is not None else None


# ----------------------------------------------------------------------------- pass
def _encounters(m, lv, squads):
    """[{off, name, squads: [h1_squads rows]}] in scenario order."""
    by_off = {s['off']: s for s in squads}
    out = []
    for enc in hv._elems(m, lv.s + hv.S_ENC, hv.S_ENC_SZ):
        name = m.data[enc:enc + 0x20].split(b'\0')[0].decode('latin-1').strip().lower()
        out.append({'off': enc, 'name': name,
                    'squads': [by_off[sq] for sq in hv._elems(m, enc + hv.SQ, hv.SQ_SZ)
                               if sq in by_off]})
    return out


def _of_species(name, folders):
    sp = species(name)
    return any(sp.startswith(f) for f in folders)


def apply(m, hp, cards, levels=None):
    """`cards` = [{'name': card name, 'species': CARDS key, 'share': 0.1 per pick}].
    Returns patch-log rows. Leaves the shared Level on m._h1_level."""
    import enemy_count as ec
    import h1_enemy_weapons as ew
    lv = getattr(m, '_h1_level', None) or ew.Level(m, hp)
    m._h1_level = lv
    index_cache = []

    def index_fn():
        if not index_cache:
            index_cache.append(ew.build_index(levels or [], hp.open_map))
        return index_cache[0]

    sw = Swapper(m, lv, index_fn)
    squads = ec.h1_squads(m)
    encs = _encounters(m, lv, squads)
    sets = setpiece_names(m)
    scen = next((n for c, n in m.tags if c == 'scnr'), '')
    taken = set()
    rows = []
    cards = sorted(cards, key=lambda c: (ORDER.index(c['species']) if c['species'] in ORDER
                                         else len(ORDER), c['name']))
    for card in cards:
        key, share = card['species'], max(0.0, float(card.get('share') or 0))
        base = {'effect': card['name'], 'tag': 'actv characters\\*', 'field': 'Incursion'}
        if key not in CARDS:
            rows.append({**base, 'ok': False, 'reason': 'unknown species %r' % key})
            continue
        faction, folders, tiers = CARDS[key]
        enemy_total, eligible = 0, []
        for e in encs:
            live = [s for s in e['squads'] if s['chars'] and s['placed']]
            foes = [s for s in live if s['enemy'] and not s['boss']]
            enemy_total += sum(max(0, s['insane']) for s in foes)
            if not live or len(foes) != len(live) or e['off'] in taken:
                continue
            if any(s['bound'] for s in e['squads']) or e['name'] in sets:
                continue
            w = sum(max(0, s['insane']) for s in foes
                    if not all(_of_species(c, folders) for c in s['chars']))
            if w > 0:
                eligible.append((e, w))
        want = share * enemy_total
        rng = random.Random('%s|%s' % (scen, card['name']))
        order = list(eligible)
        rng.shuffle(order)
        picked, got = [], 0
        for e, w in order:
            if abs(got + w - want) < abs(got - want):
                picked.append(e)
                got += w
        if not picked:
            rows.append({**base, 'ok': True, 'skip': True,
                         'reason': 'nothing to convert (%d enemies on Insane, %d eligible '
                                   'encounters)' % (enemy_total, len(eligible))})
            continue
        moved = 0
        for e in picked:
            taken.add(e['off'])
            struct.pack_into('<h', m.data, e['off'] + ENC_TEAM, TEAM[faction])
            for s in e['squads']:
                moved += _convert_squad(
                    m, lv, sw, rng, s,
                    lambda src: None if _of_species(src, folders) else tiers.get(tier_of(src)))
        names = ', '.join(e['name'] for e in picked)
        rows.append({**base, 'ok': True,
                     'old': '%d enemies on Insane (%d eligible encounters)' % (
                         enemy_total, len(eligible)),
                     'new': '%d -> %s in %d encounter(s), team %s: %s' % (
                         got, key, len(picked), faction, names)})
    if sw.recycled or sw.appended or sw.slotted:
        rows.append({'effect': 'species swap', 'tag': 'scnr', 'field': 'Actor Palette',
                     'ok': True, 'old': '%d entries' % len(lv.pal_names),
                     'new': '%d unused entries reused, %d appended, %d slot(s)%s' % (
                         sw.recycled, sw.appended, sw.slotted,
                         '; OVER 64' if len(lv.pal_names) > PALETTE_MAX else '')})
    for n in sw.notes:
        rows.append({'effect': 'species swap', 'tag': 'scnr', 'field': 'variant',
                     'ok': True, 'new': n})
    lv.rescan()
    m.actv_alias = dict(lv.alias)
    return rows


def _convert_squad(m, lv, sw, rng, s, choose):
    """Repoint one squad: its actor type, and each starting-location override on its own
    (an infection squad can carry combat-form overrides). `choose(variant)` gives the
    tier entries to draw from, or None to keep that actor. A count multiplier (infection
    forms x5 / x10, two carriers) applies when the squad's own type changes. Returns 1
    when anything changed."""
    sq = s['off']
    changed = 0

    def name_at(i):
        n = lv.pal_names[i] if 0 <= i < len(lv.pal_names) else None
        return lv.alias.get(n, n)

    def convert(src):
        entries = choose(src)
        if entries is None:
            return None
        pick = _pick(m, lv, sw, rng, src, entries)
        if pick is None:
            sw.notes.append('%s: no resident variant for tier %d of %s -- kept' % (
                s['name'], tier_of(src), src.rsplit(BS, 1)[-1]))
        return pick

    src = name_at(_i16(m, sq + hv.SQ_TYPE))
    if src:
        pick = convert(src)
        if pick:
            idx, mult, _label = pick
            struct.pack_into('<h', m.data, sq + hv.SQ_TYPE, idx)
            if mult != 1:
                for off in (SQ_NORMAL, SQ_INSANE):
                    n = _i16(m, sq + off)
                    struct.pack_into('<h', m.data, sq + off, max(0, min(0x7FFF, n * mult)))
            changed = 1
    for sl in hv._elems(m, sq + hv.SL, hv.SL_SZ):
        o = _i16(m, sl + hv.SL_TYPE)
        osrc = name_at(o) if o >= 0 else None
        if not osrc:
            continue
        op = convert(osrc)
        if op:
            struct.pack_into('<h', m.data, sl + hv.SL_TYPE, op[0])
            changed = 1
    return changed


def _pick(m, lv, sw, rng, src, entries):
    """One of `entries` for replaced variant `src`: its weapon carried over when an entry
    carries it, else a seeded draw; entries that cannot be resolved are skipped."""
    entries = list(entries or [])
    b = lv.tags.get(src)
    weapon = hv._ref_name(m, b, hv.REF_WEAPON) if b is not None else None
    same = [e for e in entries if weapon and sw.weapon_of(e) == weapon]
    for pool in (same, entries):
        pool = list(pool)
        while pool:
            e = pool.pop(rng.randrange(len(pool)))
            got = sw.target(e)
            if got is not None:
                return got
    return None


# ----------------------------------------------------------------------------- faction skulls
# The Flood / Guardians of the Galaxy / The Great Journey / Insurrection (user, 2026-10-07):
# EVERY enemy encounter becomes the skull's faction, and allied encounters too (they stay
# on the player's side). Several faction skulls SPLIT the encounters between them (each
# encounter goes to the faction with the fewest actors so far, in a seeded order), so
# they fight each other. Runs BEFORE Thunderstorm / Downpour and the Incursion cards.
#
# A replaced species takes the same POSITION in the target faction's ladder (the
# Thunderstorm ladders): Covenant Grunt 1, Jackal 2, Elite 3, Hunter 4; Flood infection
# 1, carrier 2, combat Human 3, combat Elite / stealth 4 (the user's Flood ranking);
# Sentinels and Humans have one species, so their position is their rank. Within the
# target species the actor keeps its RANK (tier_of) on that species' Incursion ladder.
FACTION_SKULLS = {'faction_covenant': 'covenant', 'faction_flood': 'flood',
                  'faction_sentinel': 'sentinel', 'faction_human': 'human'}
FACTION_NAMES = {'covenant': 'The Great Journey', 'flood': 'The Flood',
                 'sentinel': 'Guardians of the Galaxy', 'human': 'Insurrection'}
ALLY_TEAM = TEAM['human']
_INF = C('flood_infection', 'flood_infection')
_CAR = C('floodcarrier', 'floodcarrier')
LADDER = {
    'covenant': {1: 'grunt', 2: 'jackal', 3: 'elite', 4: 'hunter'},
    'flood': {1: {1: [('count', _INF, 5)], 2: [('count', _INF, 10)],
                  3: [('count', _INF, 10)], 4: [('count', _INF, 10)]},
              2: {t: [('count', _CAR, 1)] for t in (1, 2, 3, 4)},
              3: 'flood combat', 4: 'flood combat'},
    'sentinel': {p: 'sentinel' for p in (1, 2, 3, 4)},
    'human': {p: 'human' for p in (1, 2, 3, 4)},
}
# never converted as allies: story-bound or scripted humans
ALLY_SKIP_WORDS = ('wounded', 'sitting', 'suicidal', 'cinematic')


def faction_of(name):
    sp = species(name)
    if sp in ('grunt', 'jackal', 'elite', 'hunter'):
        return 'covenant'
    if sp.startswith('flood'):
        return 'flood'
    if sp.startswith('sentinel'):
        return 'sentinel'
    if sp.startswith('marine') or sp.startswith('crewman'):
        return 'human'
    return None


def position(name):
    sp = species(name)
    cov = {'grunt': 1, 'jackal': 2, 'elite': 3, 'hunter': 4}
    if sp in cov:
        return cov[sp]
    if sp.startswith('flood_infection'):
        return 1
    if sp.startswith('floodcarrier'):
        return 2
    if sp == FCH:
        return 3
    if sp.startswith('floodcombat'):
        return 4
    return max(1, min(4, tier_of(name)))


def faction_entries(faction, src):
    """Tier entries for variant `src` under a faction skull, or None to keep it (already
    of the faction, or not a character species: turret / vehicle drivers)."""
    have = faction_of(src)
    if have is None or have == faction:
        return None
    lad = LADDER[faction][position(src)]
    tiers = CARDS[lad][2] if isinstance(lad, str) else lad
    return tiers.get(tier_of(src))


def _hostile_team(faction, factions):
    """The team an enemy encounter of `faction` fights on. Insurrection's humans take
    Betrayal's team (Flood) -- unless The Flood is active too, then the first faction
    team no other active skull uses, so the two still fight each other."""
    if faction != 'human':
        return TEAM[faction]
    used = {TEAM[f] for f in factions if f != 'human'}
    return next((t for t in (TEAM['flood'], TEAM['covenant'], TEAM['sentinel'])
                 if t not in used), 6)


def apply_factions(m, hp, factions, levels=None):
    """`factions` = faction keys of the active faction skulls. Patch-log rows."""
    import enemy_count as ec
    import h1_enemy_weapons as ew
    factions = sorted(set(f for f in factions if f in LADDER))
    if not factions:
        return []
    lv = getattr(m, '_h1_level', None) or ew.Level(m, hp)
    m._h1_level = lv
    index_cache = []

    def index_fn():
        if not index_cache:
            index_cache.append(ew.build_index(levels or [], hp.open_map))
        return index_cache[0]

    sw = Swapper(m, lv, index_fn)
    encs = _encounters(m, lv, ec.h1_squads(m))
    sets = setpiece_names(m)
    scen = next((n for c, n in m.tags if c == 'scnr'), '')
    rng = random.Random('%s|%s' % (scen, '+'.join(factions)))
    sides = {'enemy': [], 'ally': []}
    left = {'set piece': 0, 'seated by script': 0, 'mixed / boss': 0}
    for e in encs:
        live = [s for s in e['squads'] if s['chars'] and s['placed']]
        if not live:
            continue
        foes = [s for s in live if s['enemy'] and not s['boss']]
        friends = [s for s in live if s['ally'] and not s['boss'] and all(
            faction_of(c) and not any(w in c.lower() for w in ALLY_SKIP_WORDS)
            for c in s['chars'])]
        side = 'enemy' if len(foes) == len(live) else \
            'ally' if len(friends) == len(live) else None
        if side is None:
            left['mixed / boss'] += 1
            continue
        if any(s['bound'] for s in e['squads']):
            left['seated by script'] += 1
            continue
        if e['name'] in sets:
            left['set piece'] += 1
            continue
        sides[side].append((e, sum(max(0, s['insane']) for s in live)))
    rows = []
    for side in ('enemy', 'ally'):
        order = list(sides[side])
        rng.shuffle(order)
        load = {f: 0 for f in factions}
        got = {f: [] for f in factions}
        for e, w in order:
            f = min(factions, key=lambda x: (load[x], factions.index(x)))
            load[f] += w
            got[f].append(e)
        for f in factions:
            if not got[f]:
                continue
            team = _hostile_team(f, factions) if side == 'enemy' else ALLY_TEAM
            changed = 0
            for e in got[f]:
                struct.pack_into('<h', m.data, e['off'] + ENC_TEAM, team)
                for s in e['squads']:
                    changed += _convert_squad(m, lv, sw, rng, s,
                                              lambda src, f=f: faction_entries(f, src))
            rows.append({'effect': FACTION_NAMES[f], 'tag': 'scnr', 'field': 'Faction',
                         'ok': True, 'old': '%d %s encounter(s), %d on Insane' % (
                             len(got[f]), 'enemy' if side == 'enemy' else 'allied',
                             load[f]),
                         'new': '-> %s, team %d (%d squads changed)%s' % (
                             f, team, changed, '' if side == 'enemy' else ', still allied')})
    if any(left.values()):
        rows.append({'effect': 'faction skulls', 'tag': 'scnr', 'field': 'left alone',
                     'ok': True,
                     'new': ', '.join('%d %s' % (n, k) for k, n in left.items() if n)})
    if sw.recycled or sw.appended or sw.slotted:
        rows.append({'effect': 'faction skulls', 'tag': 'scnr', 'field': 'Actor Palette',
                     'ok': True, 'old': '%d entries' % len(lv.pal_names),
                     'new': '%d unused entries reused, %d appended, %d slot(s)%s' % (
                         sw.recycled, sw.appended, sw.slotted,
                         '; OVER 64' if len(lv.pal_names) > PALETTE_MAX else '')})
    for n in sw.notes:
        rows.append({'effect': 'faction skulls', 'tag': 'scnr', 'field': 'variant',
                     'ok': True, 'new': n})
    lv.rescan()
    m.actv_alias = dict(lv.alias)
    return rows
