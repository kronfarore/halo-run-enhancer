r"""Enemy count cards: more enemies spawn, as a percentage of the level's enemies.

HALO 2 (confirmed in game on 03a, 2026-10-04: squads doubled by raising both difficulty
counts and copying starting locations were clearly bigger). The engine places
min(difficulty count, len(Starting Locations)) actors per squad, so a squad grows by its
counts plus -- where the new count outruns them -- copies of its ON-FOOT locations:

  scnr Squads  +0x160 elem 0x74   Team enum16 +0x24 (0 = the character's), Normal / Insane
                                  Difficulty Count +0x2C / +0x2E, Vehicle Type Index +0x34,
                                  Character Type Index +0x36
    Starting Locations +0x48 elem 0x64   xyz +0x0, Character Type Index +0x20 (-1 = the
                                         squad's), Vehicle Type Index +0x28 (a location
                                         that mans a turret/vehicle is never copied)
  Character Palette +0x178 elem 0x8 (ident +0x4); char Unit tagRef +0xC (Parent +0x4);
  bipd Default Team +0xC0

THE PERCENTAGE IS OF EVERY ENEMY THE LEVEL SPAWNS, script waves included (the user's
rule): a script call with a literal count, `(ai_place sq 3)`, overrides the squad count,
so those actors count toward the base but their squads take no extras -- the extras go
to the squads that spawn by their own count. A card's extras are spread over its squads
in proportion to their size: each squad gets the whole part of its share, and the
leftover actors go to squads drawn by their fractional share with a random generator
seeded from the map and the card, so every machine (co-op) builds the same level and a
small percentage does not land on the first squads of the level.

WHO IS AN ENEMY. Allegiance in Halo 2 is set by script, `(ai_allegiance player covenant)`
on the Arbiter levels, so it is read from the compiled scripts (opcode 0x137, two team
arguments): the player's friends are Player plus every team paired with it. A squad's team
is its own Team, or its characters' biped Default Team. Enemy = not a friend and not a
human character. Squads that ARE vehicles (squad-level Vehicle Type Index), bosses and
count-0 squads are left alone (the user's call: infantry only).

Compiled ai_place: opcode 0x123 = `(ai_place ai)`, 0x124 = `(ai_place ai count)`; the
`ai` argument (value type 19) holds the squad index when its high 16 bits are 0
(0x4000xxxx is a squad group, 0xC0SSxxxx one starting location of squad SS).
"""
import math
import random
import struct

H2_SQUADS, H2_SQ_SZ = 0x160, 0x74
H2_TEAM, H2_NORMAL, H2_INSANE, H2_VEH, H2_CHAR = 0x24, 0x2C, 0x2E, 0x34, 0x36
H2_LOCS, H2_LOC_SZ, H2_LOC_CHAR, H2_LOC_VEH = 0x48, 0x64, 0x20, 0x28
H2_PALETTE, H2_PAL_SZ, H2_PAL_ID = 0x178, 0x8, 0x4
H2_CHAR_UNIT, H2_CHAR_PARENT, H2_BIPD_TEAM = 0xC, 0x4, 0xC0
H2_OP_PLACE_N, H2_OP_ALLEGIANCE = 0x124, 0x137
T_SHORT, F_PRIMITIVE = 7, 9
TEAM_PLAYER = 1

#: Characters never multiplied, and squads holding one are left alone: the bosses and the
#: story characters (a second Tartarus or Regret would break the fight scripts).
BOSS_WORDS = ('tartarus', 'heretic_leader', 'prophet', 'monitor', 'johnson', 'miranda',
              'cortana', 'dervish', 'masterchief')
#: Human species (by the character's folder under objects\characters): never enemies.
HUMAN_SPECIES = ('marine', 'masterchief', 'dervish', 'miranda', 'johnson', 'cortana',
                 'odst', 'civilian', 'crewman')
SPREAD = 0.6       # world units between a copied location and its source


def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def species(name):
    parts = (name or '').lower().split('\\')
    if 'characters' in parts and parts.index('characters') + 1 < len(parts):
        return parts[parts.index('characters') + 1]
    return parts[-1]


def _is_boss(name):
    low = (name or '').lower().rsplit('\\', 1)[-1]
    return any(w in low for w in BOSS_WORDS)


def _is_human(name):
    sp = species(name)
    return any(sp.startswith(h) for h in HUMAN_SPECIES)


def _tree(m):
    import halo_patch
    import hud_titles
    return hud_titles.Tree(m, 'Halo 2', halo_patch._block_base, m.scenario_tag()['base'])


def h2_friend_teams(m, tree=None):
    """Player plus every team the level's scripts ally with it (either order)."""
    t = tree or _tree(m)
    friends = {TEAM_PLAYER}
    for i in range(t.n):
        r = t.at(i)
        if not r or r['vtype'] != 2 or r['opcode'] != H2_OP_ALLEGIANCE or r['next'] == 0xFFFFFFFF:
            continue
        a = t.at(r['next'] & 0xFFFF)
        b = t.at(a['next'] & 0xFFFF) if a and a['next'] != 0xFFFFFFFF else None
        if not b:
            continue
        x, y = a['value'] & 0xFFFF, b['value'] & 0xFFFF
        if x == TEAM_PLAYER:
            friends.add(y)
        elif y == TEAM_PLAYER:
            friends.add(x)
    return friends


def h2_script_counts(m, tree=None):
    """{squad index: actors} placed by `(ai_place <squad> <literal count>)` calls. Counts
    written as expressions are not evaluated (and not counted)."""
    t = tree or _tree(m)
    out = {}
    for i in range(t.n):
        r = t.at(i)
        if not r or r['vtype'] != 2 or r['opcode'] != H2_OP_PLACE_N or r['next'] == 0xFFFFFFFF:
            continue
        a = t.at(r['next'] & 0xFFFF)
        if not a or a['next'] == 0xFFFFFFFF or (a['value'] >> 16) != 0:
            continue
        bi = a['next'] & 0xFFFF
        b = t.at(bi)
        flags = struct.unpack_from('<H', m.data, t.base + bi * t.size + 6)[0]
        if b and b['vtype'] == T_SHORT and flags == F_PRIMITIVE:
            n = int(t.number(b))
            if n > 0:
                out[a['value']] = out.get(a['value'], 0) + n
    return out


def _char_team(m, byidx, tag, depth=0):
    """A character's biped Default Team, following Parent Character when Unit is unset."""
    if not tag or tag.get('base') is None or depth > 6:
        return None
    b = tag['base']
    u = m.u32(b + H2_CHAR_UNIT + 4)
    if u != 0xFFFFFFFF and byidx.get(u & 0xFFFF) and byidx[u & 0xFFFF].get('base') is not None:
        return _i16(m, byidx[u & 0xFFFF]['base'] + H2_BIPD_TEAM)
    p = m.u32(b + H2_CHAR_PARENT + 4)
    if p != 0xFFFFFFFF and byidx.get(p & 0xFFFF):
        return _char_team(m, byidx, byidx[p & 0xFFFF], depth + 1)
    return None


def h2_squads(m, tree=None):
    """Every squad: {index, name, off, normal, insane, locs, foot, chars, enemy, vehicle,
    boss, script}."""
    t = tree or _tree(m)
    s = m.scenario_tag()['base']
    byidx = {x['index']: x for x in m.tags}
    pal, teams = [], []
    for el in m.follow_all(s, [H2_PALETTE], [H2_PAL_SZ], 'all'):
        ident = m.u32(el + H2_PAL_ID)
        tag = byidx.get(ident & 0xFFFF) if ident != 0xFFFFFFFF else None
        pal.append(tag['name'] if tag else None)
        teams.append(_char_team(m, byidx, tag))
    friends = h2_friend_teams(m, t)
    script = h2_script_counts(m, t)
    out = []
    for idx, sq in enumerate(m.follow_all(s, [H2_SQUADS], [H2_SQ_SZ], 'all')):
        base = _i16(m, sq + H2_CHAR)
        locs = m.follow_all(sq, [H2_LOCS], [H2_LOC_SZ], 'all')
        ci = {base} if not locs else set()
        foot = 0
        for loc in locs:
            c = _i16(m, loc + H2_LOC_CHAR)
            ci.add(c if c >= 0 else base)
            foot += _i16(m, loc + H2_LOC_VEH) < 0
        ci = {c for c in ci if 0 <= c < len(pal) and pal[c]}
        chars = {pal[c] for c in ci}
        steam = _i16(m, sq + H2_TEAM)
        sides = {steam} if steam else {teams[c] for c in ci}
        # a character with no biped team (the infection form is a creature) is not a friend
        enemy = bool(chars) and not any(_is_human(c) for c in chars) and not (sides & friends)
        out.append({'index': idx, 'off': sq,
                    'name': m.data[sq:sq + 0x20].split(b'\0')[0].decode('ascii', 'replace'),
                    'normal': _i16(m, sq + H2_NORMAL), 'insane': _i16(m, sq + H2_INSANE),
                    'locs': len(locs), 'foot': foot, 'chars': chars, 'enemy': enemy,
                    'vehicle': _i16(m, sq + H2_VEH) >= 0,
                    'boss': any(_is_boss(c) for c in chars),
                    'script': script.get(idx, 0)})
    return out


def _matching(m, squads, pattern):
    """Enemy infantry squads fielding a character the card's char pattern names (a mixed
    squad counts for each species in it)."""
    names = {p.lower() for p, _b in m.find_tags('char', pattern)} if pattern else None
    out = []
    for sq in squads:
        if not sq['enemy'] or sq['vehicle'] or sq['boss']:
            continue
        if names is not None and not any(c.lower() in names for c in sq['chars']):
            continue
        out.append(sq)
    return out


def _allocate(squads, key, extra, rng):
    """{squad index: extra actors} -- `extra` spread over `squads` in proportion to their
    `key` count: the whole part of each share, then the leftovers drawn by fractional
    share without replacement."""
    total = sum(sq[key] for sq in squads)
    if extra <= 0 or total <= 0:
        return {}
    got, frac = {}, []
    for sq in squads:
        share = sq[key] * extra / float(total)
        whole = int(math.floor(share))
        if whole:
            got[sq['index']] = whole
        if share > whole:
            frac.append([sq['index'], share - whole])
    left = extra - sum(got.values())
    while left > 0 and frac:
        r = rng.random() * sum(w for _i, w in frac)
        for k, (i, w) in enumerate(frac):
            r -= w
            if r <= 0 or k == len(frac) - 1:
                got[i] = got.get(i, 0) + 1
                frac.pop(k)
                break
        left -= 1
    return got


def _grow(m, sq, normal, insane, spread=SPREAD):
    """Write the new counts and copy on-foot locations up to the larger of them."""
    off = sq['off']
    need = max(normal, insane) - sq['locs']
    added = 0
    if need > 0 and sq['foot'] > 0:
        foot = [loc for loc in m.follow_all(off, [H2_LOCS], [H2_LOC_SZ], 'all')
                if _i16(m, loc + H2_LOC_VEH) < 0]
        copies = []
        for k in range(need):
            e = bytearray(m.data[foot[k % len(foot)]:foot[k % len(foot)] + H2_LOC_SZ])
            x, y, z = struct.unpack_from('<fff', e, 0)
            ring = k // len(foot) + 1
            ang = 2.0 * math.pi * (k % len(foot)) / len(foot) + ring
            struct.pack_into('<fff', e, 0, x + spread * ring * math.cos(ang),
                             y + spread * ring * math.sin(ang), z)
            copies.append(bytes(e))
        m.grow_block(off, H2_LOCS, H2_LOC_SZ, copies)
        added = need
    struct.pack_into('<hh', m.data, off + H2_NORMAL, normal, insane)
    return added


def enemy_total(m, game, pattern=None):
    """(squad actors, script actors, squads) the card would count -- Normal difficulty."""
    if str(game).strip() != 'Halo 2':
        return None
    sq = _matching(m, h2_squads(m), pattern)
    return (sum(s['normal'] for s in sq if not s['script'] and s['normal'] > 0),
            sum(s['script'] for s in sq), len(sq))


def scale_enemy_count(m, game, pattern, pct, seed):
    """Add round(pct x the level's matching enemies) actors to the matching squads.

    Returns {'ok', 'skip', 'reason' | 'base', 'script', 'extra', 'squads', 'locations'}."""
    if str(game).strip() != 'Halo 2':
        return {'ok': True, 'skip': True, 'reason': 'enemy count is Halo 2 only so far'}
    if pct <= 0:
        return {'ok': True, 'skip': True, 'reason': 'no increase'}
    squads = _matching(m, h2_squads(m), pattern)
    if not squads:
        return {'ok': True, 'skip': True, 'reason': 'not present in this map'}
    script = sum(sq['script'] for sq in squads)
    takers = [sq for sq in squads if not sq['script'] and (sq['normal'] > 0 or sq['insane'] > 0)]
    if not takers:
        return {'ok': True, 'skip': True,
                'reason': 'every matching squad is placed by script with a fixed count'}
    # the scenario's own tag name, not the file name: every machine (co-op) and every
    # re-patch of this run draws the same squads, whatever the map file is called
    seed = '%s|%s' % ((m.scenario_tag() or {}).get('name') or '', seed)
    plan = {}
    for key in ('normal', 'insane'):
        base = sum(sq[key] for sq in takers) + script
        extra = int(round(pct * base))
        rng = random.Random('%s|%s' % (seed, key))
        plan[key] = (base, extra, _allocate(takers, key, extra, rng))
    locs, changed = 0, 0
    for sq in takers:
        dn = plan['normal'][2].get(sq['index'], 0)
        di = plan['insane'][2].get(sq['index'], 0)
        if not dn and not di:
            continue
        locs += _grow(m, sq, sq['normal'] + dn if sq['normal'] > 0 else 0,
                      sq['insane'] + di if sq['insane'] > 0 else 0)
        changed += 1
    return {'ok': True, 'skip': False, 'base': plan['normal'][0], 'script': script,
            'extra': plan['normal'][1], 'extra_insane': plan['insane'][1],
            'squads': changed, 'of': len(takers), 'locations': locs}

