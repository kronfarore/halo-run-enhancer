r"""Spawn Count cards: more enemies (or allies) spawn, as a percentage of the level's.

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

HALO 1 has the same squad shape one level down, under ENCOUNTERS, and the same counts:

  scnr Actor Palette +0x420 elem 0x10 (ident +0xC)
  Encounters +0x42C elem 0xB0   name +0x0, Flags +0x20 (bit 0 Not Initially Created),
                                Team Index +0x24 (0 = by unit), Platoons +0x8C elem 0xAC
    Squads +0x80 elem 0xE8      name +0x0, Actor Type +0x20, Platoon Index +0x22,
                                Normal / Insane Difficulty Count +0x7C / +0x7E
      Starting Locations +0xD0 elem 0x1C   xyz +0x0, Actor Type override +0x18

THE PERCENTAGE IS OF EVERY ENEMY THE LEVEL SPAWNS, script spawns included (the user's
rule). Squads whose actors arrive some other way count toward the base but take no
extras, which go to the squads that spawn by their own count:
  * a fixed script count, `(ai_place sq 3)` (Halo 2) -- it overrides the squad count;
  * one-at-a-time spawns, `(ai_spawn_actor enc/sq)` (Halo 1) -- one actor per call;
  * squads put into a vehicle by script -- Halo 2 `ai_place_in_vehicle` /
    `ai_vehicle_enter_immediate`, Halo 1 `vehicle_load_magic ... (ai_actors X)`. Halo 1's
    dropship troops wait in a hidden staging area (a30: ~100 units from the drop) and the
    dropship's 8 passenger seats are already 6-8 full, so extras would be stranded there
    and a "wait until the wave is dead" could never finish.
A card's extras are spread over its squads in proportion to their size: each squad gets
the whole part of its share, and the leftover actors go to squads drawn by their
fractional share with a generator seeded from the scenario and the card, so every machine
(co-op) builds the same level and a small percentage does not land on the first squads.

WHO IS AN ENEMY. Halo 2 sets allegiance by script, `(ai_allegiance player covenant)` on the
Arbiter levels, so it is read from the compiled scripts: the player's friends are Player
plus every team paired with it. A squad's team is its own Team, or its characters' biped
Default Team; enemy = not a friend and not a human character. Halo 1's allegiance calls
are NOT trustworthy -- c10 allies the player with the Flood at startup and the removal is
commented out -- so Halo 1 goes by species: Covenant and Flood are enemies, Sentinels too
unless the level allies them with the player (c10, c20). An ALLY card (side='ally') takes
the other side: human characters and squads on a friendly team. Squads that ARE vehicles
(Halo 2 squad-level Vehicle Type Index), bosses and story characters are never grown.

Compiled scripts. Halo 2 (names are opcodes, ai arguments are indices: value type 19,
high 16 bits 0 = squad index, 0x4000 = squad group, 0xC0SS = a starting location of squad
SS): ai_place 0x123 / with count 0x124, ai_place_in_vehicle 0x125, ai_allegiance 0x137,
ai_vehicle_enter_immediate 0x15B. Halo 1 (an ai argument keeps its SOURCE TEXT -- encounter,
encounter/squad or encounter/platoon -- in the Script String Data at scnr+0x488): ai_place
0xC3, ai_spawn_actor 0xCA, ai_allegiance 0xDB, ai_actors 0xE2, vehicle_load_magic 0x93.
"""
import math
import random
import struct

H2_SQUADS, H2_SQ_SZ = 0x160, 0x74
H2_TEAM, H2_NORMAL, H2_INSANE, H2_VEH, H2_CHAR = 0x24, 0x2C, 0x2E, 0x34, 0x36
H2_LOCS, H2_LOC_SZ, H2_LOC_CHAR, H2_LOC_VEH = 0x48, 0x64, 0x20, 0x28
H2_PALETTE, H2_PAL_SZ, H2_PAL_ID = 0x178, 0x8, 0x4
H2_CHAR_UNIT, H2_CHAR_PARENT, H2_BIPD_TEAM = 0xC, 0x4, 0xC0
H2_OP_PLACE_N, H2_OP_PLACE_IN_VEHICLE = 0x124, 0x125
H2_OP_ALLEGIANCE, H2_OP_ENTER_IMMEDIATE = 0x137, 0x15B
T_SHORT, F_PRIMITIVE, T_AI = 7, 9, 19

H1_PALETTE, H1_PAL_SZ, H1_PAL_ID = 0x420, 0x10, 0xC
H1_ENCOUNTERS, H1_ENC_SZ, H1_ENC_FLAGS, H1_ENC_TEAM = 0x42C, 0xB0, 0x20, 0x24
H1_PLATOONS, H1_PLATOON_SZ = 0x8C, 0xAC
H1_SQUADS, H1_SQ_SZ, H1_ACTOR, H1_PLATOON = 0x80, 0xE8, 0x20, 0x22
H1_NORMAL, H1_INSANE = 0x7C, 0x7E
H1_LOCS, H1_LOC_SZ, H1_LOC_ACTOR = 0xD0, 0x1C, 0x18
H1_ACTV_UNIT = 0x14          # actv Unit tagRef (ident at +0xC)
H1_STRINGS = 0x488
H1_OP_PLACE, H1_OP_SPAWN_ACTOR, H1_OP_ALLEGIANCE = 0xC3, 0xCA, 0xDB
H1_OP_AI_ACTORS, H1_OP_LOAD_MAGIC = 0xE2, 0x93
H1_ENEMY_SPECIES = ('elite', 'grunt', 'jackal', 'hunter', 'flood', 'sentinel')

TEAM_PLAYER, TEAM_HUMAN, TEAM_SENTINEL = 1, 2, 5

#: Characters never multiplied, and squads holding one are left alone: the bosses and the
#: story characters (a second Tartarus or Regret would break the fight scripts).
BOSS_WORDS = ('tartarus', 'heretic_leader', 'prophet', 'monitor', 'johnson', 'miranda',
              'cortana', 'dervish', 'masterchief', 'captain', 'keyes')
#: Human species (by the character's folder under objects\characters): never enemies.
HUMAN_SPECIES = ('marine', 'masterchief', 'dervish', 'miranda', 'johnson', 'cortana',
                 'odst', 'civilian', 'crewman', 'captain', 'keyes', 'pilot')
SPREAD = 0.6       # world units between a copied location and its source
GAMES = ('Halo 1', 'Halo 2')


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


def _tree(m, game):
    import halo_patch
    import hud_titles
    return hud_titles.Tree(m, game, halo_patch._block_base, halo_patch._scnr_base(m))


def _args(t, r, limit=6):
    """The argument nodes of call-name node `r`."""
    out, a = [], r['next']
    while a != 0xFFFFFFFF and len(out) < limit:
        x = t.at(a & 0xFFFF)
        if not x or (t.game == 'Halo 1' and x['salt'] == 0):
            break
        out.append(x)
        a = x['next']
    return out


def _calls(t, opcodes):
    """(opcode, args) for every call to one of `opcodes`."""
    for i in range(t.n):
        r = t.at(i)
        if r and r['vtype'] == 2 and r['opcode'] in opcodes and r['next'] != 0xFFFFFFFF:
            if t.game == 'Halo 1' and r['salt'] == 0:
                continue
            yield r['opcode'], _args(t, r)


# ---- Halo 2 --------------------------------------------------------------------------

def _h2_squad_of(value):
    """Squad index an ai argument names (a squad, or one starting location of it)."""
    hi = value >> 16
    if hi == 0:
        return value & 0xFFFF
    if hi & 0xC000 == 0xC000:
        return hi & 0xFF
    return None


def h2_friend_teams(m, tree=None):
    """Player plus every team the level's scripts ally with it (either order)."""
    t = tree or _tree(m, 'Halo 2')
    friends = {TEAM_PLAYER}
    for _op, a in _calls(t, (H2_OP_ALLEGIANCE,)):
        if len(a) >= 2:
            x, y = a[0]['value'] & 0xFFFF, a[1]['value'] & 0xFFFF
            if x == TEAM_PLAYER:
                friends.add(y)
            elif y == TEAM_PLAYER:
                friends.add(x)
    return friends


def h2_script_counts(m, tree=None):
    """{squad index: actors} placed by `(ai_place <squad> <literal count>)` calls. Counts
    written as expressions are not evaluated (and not counted)."""
    t = tree or _tree(m, 'Halo 2')
    out = {}
    for _op, a in _calls(t, (H2_OP_PLACE_N,)):
        if len(a) < 2 or (a[0]['value'] >> 16) != 0:
            continue
        flags = struct.unpack_from('<H', m.data, t.base + a[1]['i'] * t.size + 6)[0]
        if a[1]['vtype'] == T_SHORT and flags == F_PRIMITIVE:
            n = int(t.number(a[1]))
            if n > 0:
                out[a[0]['value']] = out.get(a[0]['value'], 0) + n
    return out


def h2_vehicle_bound(m, tree=None):
    """Squad indices the scripts put into a vehicle (ai_place_in_vehicle, the squad being
    placed; ai_vehicle_enter_immediate, the squad or location entering)."""
    t = tree or _tree(m, 'Halo 2')
    out = set()
    for _op, a in _calls(t, (H2_OP_PLACE_IN_VEHICLE, H2_OP_ENTER_IMMEDIATE)):
        if a and a[0]['vtype'] == T_AI:
            si = _h2_squad_of(a[0]['value'])
            if si is not None:
                out.add(si)
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
    """Every squad: {index, name, off, normal, insane, locs, foot, chars, enemy, ally,
    vehicle, boss, script, bound, placed}."""
    t = tree or _tree(m, 'Halo 2')
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
    bound = h2_vehicle_bound(m, t)
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
        human = any(_is_human(c) for c in chars)
        # a character with no biped team (the infection form is a creature) is not a friend
        enemy = bool(chars) and not human and not (sides & friends)
        out.append({'index': idx, 'off': sq,
                    'name': m.data[sq:sq + 0x20].split(b'\0')[0].decode('ascii', 'replace'),
                    'normal': _i16(m, sq + H2_NORMAL), 'insane': _i16(m, sq + H2_INSANE),
                    'locs': len(locs), 'foot': foot, 'chars': chars, 'enemy': enemy,
                    'ally': bool(chars) and not enemy,
                    'vehicle': _i16(m, sq + H2_VEH) >= 0,
                    'boss': any(_is_boss(c) for c in chars),
                    'script': script.get(idx, 0), 'bound': idx in bound, 'placed': True})
    return out


# ---- Halo 1 --------------------------------------------------------------------------

def _h1_strings(m):
    import halo_patch
    s = halo_patch._scnr_base(m)
    ptr, size = m.u32(s + H1_STRINGS + 0xC), max(0, m.i32(s + H1_STRINGS))
    if not ptr or not size:
        return b''
    o = (ptr - m.magic) & 0xFFFFFFFF
    return bytes(m.data[o:o + size])


def h1_script_refs(m, tree=None):
    """{'place': {name: calls}, 'spawn_actor': {...}, 'loaded': {...}, 'allegiance': {(a, b)}}
    -- names are the script's own text: encounter, encounter/squad or encounter/platoon."""
    t = tree or _tree(m, 'Halo 1')
    blob = _h1_strings(m)

    def text(node):
        o = struct.unpack_from('<I', m.data, t.base + node['i'] * t.size + 0xC)[0]
        if not (0 <= o < len(blob)):
            return None
        e = blob.find(b'\0', o)
        return blob[o:e if e >= 0 else len(blob)].decode('latin-1').strip().lower()

    out = {'place': {}, 'spawn_actor': {}, 'loaded': {}, 'allegiance': set()}
    for op, a in _calls(t, (H1_OP_PLACE, H1_OP_SPAWN_ACTOR, H1_OP_ALLEGIANCE, H1_OP_LOAD_MAGIC)):
        if not a:
            continue
        if op == H1_OP_ALLEGIANCE:
            if len(a) >= 2:
                out['allegiance'].add((text(a[0]), text(a[1])))
            continue
        if op == H1_OP_LOAD_MAGIC:
            # vehicle seat (ai_actors X): the third argument is a call group whose value
            # points at the ai_actors name node
            if len(a) >= 3:
                g = t.at(a[2]['value'] & 0xFFFF)
                if g and g['opcode'] == H1_OP_AI_ACTORS:
                    aa = _args(t, g, 1)
                    if aa and text(aa[0]):
                        k = text(aa[0])
                        out['loaded'][k] = out['loaded'].get(k, 0) + 1
            continue
        k = text(a[0])
        if k:
            key = 'place' if op == H1_OP_PLACE else 'spawn_actor'
            out[key][k] = out[key].get(k, 0) + 1
    return out


def h1_squads(m, tree=None):
    """Every squad, in the same shape as h2_squads (index runs over all encounters)."""
    import halo_patch
    t = tree or _tree(m, 'Halo 1')
    s = halo_patch._scnr_base(m)
    pal, unit = [], {}
    for el in m.follow_all(s, [H1_PALETTE], [H1_PAL_SZ], 'all'):
        ident = m.u32(el + H1_PAL_ID)
        name = halo_patch._tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None
        pal.append(name)
        # the species comes from the variant's biped: the enemy-weapons pass moves spawns
        # onto generic `characters\enhancer\slot NN` variants before the cards run
        found = m.find_tags('actv', name) if name else []
        u = m.u32(found[0][1] + H1_ACTV_UNIT + 0xC) if found else 0xFFFFFFFF
        unit[name] = (halo_patch._tag_name_by_id(m, u) if u != 0xFFFFFFFF else None) or name
    refs = h1_script_refs(m, t)
    allied = {b for a, b in refs['allegiance'] if a == 'player'} | \
             {a for a, b in refs['allegiance'] if b == 'player'}
    sentinels_friendly = 'sentinel' in allied
    out = []
    idx = 0
    for e in m.follow_all(s, [H1_ENCOUNTERS], [H1_ENC_SZ], 'all'):
        en = m.data[e:e + 0x20].split(b'\0')[0].decode('latin-1').strip().lower()
        initial = not (m.u32(e + H1_ENC_FLAGS) & 1)
        team = _i16(m, e + H1_ENC_TEAM)
        toons = [m.data[p:p + 0x20].split(b'\0')[0].decode('latin-1').strip().lower()
                 for p in m.follow_all(e, [H1_PLATOONS], [H1_PLATOON_SZ], 'all')]
        for sq in m.follow_all(e, [H1_SQUADS], [H1_SQ_SZ], 'all'):
            sn = m.data[sq:sq + 0x20].split(b'\0')[0].decode('latin-1').strip().lower()
            pi = _i16(m, sq + H1_PLATOON)
            names = {en, en + '/' + sn}
            if 0 <= pi < len(toons):
                names.add(en + '/' + toons[pi])
            a = _i16(m, sq + H1_ACTOR)
            locs = m.follow_all(sq, [H1_LOCS], [H1_LOC_SZ], 'all')
            ci = {a} if not locs else set()
            for loc in locs:
                o = _i16(m, loc + H1_LOC_ACTOR)
                ci.add(o if o >= 0 else a)
            chars = {pal[c] for c in ci if 0 <= c < len(pal) and pal[c]}
            sps = {species(unit.get(c, c)) for c in chars}
            human = any(_is_human(unit.get(c, c)) for c in chars) or bool(sps) and not any(
                sp.startswith(h) for sp in sps for h in H1_ENEMY_SPECIES)
            sentinel = any(sp.startswith('sentinel') for sp in sps)
            if team in (TEAM_PLAYER, TEAM_HUMAN):
                enemy = False
            elif team > TEAM_HUMAN:
                enemy = not (team == TEAM_SENTINEL and sentinels_friendly)
            else:
                enemy = bool(chars) and not human and not (sentinel and sentinels_friendly)
            out.append({'index': idx, 'off': sq, 'name': en + '/' + sn,
                        'normal': _i16(m, sq + H1_NORMAL), 'insane': _i16(m, sq + H1_INSANE),
                        'locs': len(locs), 'foot': len(locs), 'chars': chars,
                        'enemy': enemy, 'ally': bool(chars) and not enemy, 'vehicle': False,
                        'boss': any(_is_boss(c) or _is_boss(unit.get(c)) for c in chars),
                        'script': sum(refs['spawn_actor'].get(n, 0) for n in names),
                        'bound': any(n in refs['loaded'] for n in names),
                        'placed': initial or any(n in refs['place'] for n in names)})
            idx += 1
    return out


# ---- shared ------------------------------------------------------------------------

def squads(m, game):
    g = str(game).strip()
    return h1_squads(m) if g == 'Halo 1' else h2_squads(m) if g == 'Halo 2' else None


def _matching(m, game, all_squads, pattern, side='enemy'):
    """Infantry squads on `side` fielding a character the card's pattern names (a mixed
    squad counts for each species in it). Halo 1 patterns name actor variants (actv)."""
    cls = 'actv' if str(game).strip() == 'Halo 1' else 'char'
    names = {p.lower() for p, _b in m.find_tags(cls, pattern)} if pattern else None
    out = []
    for sq in all_squads:
        if not sq[side] or sq['vehicle'] or sq['boss']:
            continue
        if names is not None and not any(c.lower() in names for c in sq['chars']):
            continue
        out.append(sq)
    return out


def _spawns(sq, key):
    """Actors this squad puts on the level at `key` difficulty: a fixed script count (or
    one-at-a-time spawns) replaces the squad count; an unplaced squad puts none."""
    if sq['script']:
        return sq['script']
    return max(sq[key], 0) if sq['placed'] else 0


def _takes_extras(sq):
    return (not sq['script'] and not sq['bound'] and sq['placed'] and sq['foot'] > 0
            and (sq['normal'] > 0 or sq['insane'] > 0))


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


def grow(m, game, sq, normal, insane, spread=SPREAD):
    """Write the new counts and copy on-foot locations up to the larger of them."""
    h1 = str(game).strip() == 'Halo 1'
    locs_off, loc_sz, cnt_off = ((H1_LOCS, H1_LOC_SZ, H1_NORMAL) if h1 else
                                 (H2_LOCS, H2_LOC_SZ, H2_NORMAL))
    off = sq['off']
    need = max(normal, insane) - sq['locs']
    added = 0
    if need > 0 and sq['foot'] > 0:
        foot = [loc for loc in m.follow_all(off, [locs_off], [loc_sz], 'all')
                if h1 or _i16(m, loc + H2_LOC_VEH) < 0]
        copies = []
        for k in range(need):
            e = bytearray(m.data[foot[k % len(foot)]:foot[k % len(foot)] + loc_sz])
            x, y, z = struct.unpack_from('<fff', e, 0)
            ring = k // len(foot) + 1
            ang = 2.0 * math.pi * (k % len(foot)) / len(foot) + ring
            struct.pack_into('<fff', e, 0, x + spread * ring * math.cos(ang),
                             y + spread * ring * math.sin(ang), z)
            copies.append(bytes(e))
        m.grow_block(off, locs_off, loc_sz, copies)
        added = need
    struct.pack_into('<hh', m.data, off + cnt_off, normal, insane)
    return added


def _scnr_name(m, game):
    if str(game).strip() == 'Halo 2':
        return (m.scenario_tag() or {}).get('name') or ''
    found = m.find_tags('scnr', '*')
    return found[0][0] if found else ''


def enemy_total(m, game, pattern=None, side='enemy'):
    """(squad actors, script actors, squads) the card would count -- Normal difficulty."""
    if str(game).strip() not in GAMES:
        return None
    sq = _matching(m, game, squads(m, game), pattern, side)
    return (sum(_spawns(s, 'normal') for s in sq if not s['script']),
            sum(s['script'] for s in sq), sum(1 for s in sq if _spawns(s, 'normal')))


def scale_enemy_count(m, game, pattern, pct, seed, side='enemy'):
    """Add round(pct x the level's matching actors) actors to the matching squads.

    Returns {'ok', 'skip', 'reason' | 'base', 'script', 'extra', 'squads', 'locations'}."""
    if str(game).strip() not in GAMES:
        return {'ok': True, 'skip': True, 'reason': 'spawn count is Halo 1 / Halo 2 only so far'}
    if pct <= 0:
        return {'ok': True, 'skip': True, 'reason': 'no increase'}
    matched = [sq for sq in _matching(m, game, squads(m, game), pattern, side)
               if _spawns(sq, 'normal') or _spawns(sq, 'insane')]
    if not matched:
        return {'ok': True, 'skip': True, 'reason': 'not present in this map'}
    script = sum(sq['script'] for sq in matched)
    takers = [sq for sq in matched if _takes_extras(sq)]
    if not takers:
        return {'ok': True, 'skip': True,
                'reason': 'every matching squad spawns by script or into a vehicle'}
    # the scenario's own tag name, not the file name: every machine (co-op) and every
    # re-patch of this run draws the same squads, whatever the map file is called
    seed = '%s|%s|%s' % (_scnr_name(m, game), side, seed)
    plan = {}
    for key in ('normal', 'insane'):
        base = sum(_spawns(sq, key) for sq in matched)
        extra = int(round(pct * base))
        rng = random.Random('%s|%s' % (seed, key))
        plan[key] = (base, extra, _allocate(takers, key, extra, rng))
    locs, changed = 0, 0
    for sq in takers:
        dn = plan['normal'][2].get(sq['index'], 0)
        di = plan['insane'][2].get(sq['index'], 0)
        if not dn and not di:
            continue
        locs += grow(m, game, sq, sq['normal'] + dn if sq['normal'] > 0 else 0,
                     sq['insane'] + di if sq['insane'] > 0 else 0)
        changed += 1
    return {'ok': True, 'skip': False, 'base': plan['normal'][0], 'script': script,
            'extra': plan['normal'][1], 'extra_insane': plan['insane'][1],
            'squads': changed, 'of': len(takers), 'locations': locs}
