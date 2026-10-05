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

H3_PALETTE, H3_PAL_SZ, H3_PAL_ID = 0x3A8, 0x10, 0xC
H3_GROUPS, H3_GROUP_SZ = 0x378, 0x28            # Squad Groups: name, Parent Index +0x20
H3_SQUADS, H3_SQ_SZ = 0x384, 0x40
H3_SQ_FLAGS, H3_TEAM, H3_SQ_GROUP = 0x20, 0x24, 0x26
H3_INITIALLY_PLACED = 1 << 4
H3_FIRETEAMS, H3_FT_SZ = 0x30, 0x60
H3_FT_PLACE_ON, H3_FT_COUNT, H3_FT_CHAR, H3_FT_VEH = 0x0, 0x4, 0x8, 0x12
H3_LOCS, H3_LOC_SZ, H3_LOC_POS, H3_LOC_CHAR, H3_LOC_VEH = 0x54, 0x88, 0x8, 0x28, 0x30
H3_CHAR_UNIT, H3_CHAR_PARENT, H3_BIPD_TEAM = 0x14, 0x4, 0xFC
H3_SCRIPTS, H3_SCRIPT_SZ, H3_SCRIPT_ROOT = 0x3EC, 0x34, 0x24
H3_SCRIPT_PARAMS, H3_PARAM_SZ = 0x28, 0x24
#: Halo Reach's Team enum differs from Halo 3's from 4 on.
REACH_TEAMS = ('default', 'player', 'human', 'covenant', 'brute', 'mule', 'spare',
               'covenant_player')
#: The CELL family (ODST, Reach): squads hold Spawn Points / Single Locations and Designer /
#: Templated Cells; a cell has a count, a difficulty mask and weighted Character Types.
#: scripts = (block, element, root datum, parameters block, name kind).
CELL_LAYOUT = {
    'Halo 3: ODST': dict(palette=0x3E8, groups=0x3AC, squads=(0x3B8, 0x6C),
                         locs=(0x3C, 0x90, 0x10, 0x32), cells=(0x54, 0x60), cell_sz=0x84,
                         diff=0x4, count=0x10, veh=0x46, chars=(0x14, 0x10, 0xC),
                         team=0x10C, scripts=(0x42C, 0x34, 0x24, 0x28, 'ascii'),
                         teams=None),
    'Halo Reach': dict(palette=0x3EC, groups=0x38C, squads=(0x398, 0x6C),
                       locs=(0x3C, 0x7C, 0x10, 0x32), cells=(0x54, 0x60), cell_sz=0x6C,
                       diff=0x4, count=0x10, veh=0x46, chars=(0x14, 0x10, 0xC),
                       team=0x16C, scripts=(0x430, 0x18, 0x8, 0xC, 'sid'),
                       teams=REACH_TEAMS),
    'Halo 4': dict(palette=0x444, groups=0x3E4, squads=(0x3F0, 0x6C),
                   locs=(0x3C, 0x7C, 0x8, 0x2E), cells=(0x54, 0x60), cell_sz=0x64,
                   diff=0x4, count=0x8, veh=0x3E, chars=(0xC, 0x8, 0x4),
                   team=0x1DC, scripts=None, teams=REACH_TEAMS + ('forerunner',),
                   twins=True),
}        # expression flags of a call group (built-in / script)
TEAM_NAMES = ('default', 'player', 'human', 'covenant', 'flood', 'sentinel', 'heretic',
              'prophet', 'guilty')

#: Characters never multiplied, and squads holding one are left alone: the bosses and the
#: story characters (a second Tartarus or Regret would break the fight scripts).
BOSS_WORDS = ('tartarus', 'heretic_leader', 'prophet', 'monitor', 'johnson', 'miranda',
              'cortana', 'dervish', 'masterchief', 'arbiter', 'truth', 'gravemind', 'guilty',
              '_buck', '_dare', 'oni_op', '_dutch', '_romeo', '_mickey', 'sgt_hero', 'scarab',
              'engineer_freeform',     # the freed Engineer of Data Hive / Coastal Highway
              'mule', 'halsey',        # Reach's Mule (a boss card of its own) and Halsey
              # Reach's Noble Team by name (Halo 4's Infinity Spartans are ordinary allies)
              'spartan_carter', 'spartan_emile', 'spartan_jorge', 'spartan_jun', 'spartan_kat',
              'lasky', 'palmer', 'del_rio', 'didact', 'librarian')     # Halo 4's story cast
#: ...and by the character's species folder: Halo 1's Keyes is `characters\captain\...`, a
#: word that must not catch `brute_captain`.
BOSS_SPECIES = ('captain', 'keyes', 'johnson', 'miranda', 'cortana', 'monitor', 'dervish',
                'masterchief',
                'null')                                # vehicle-pilot placeholders
#: Species on the player's side whatever their team says: Reach's Moas (ambient_life) --
#: the user's call, they belong with the ally cards.
ALLY_SPECIES = ('ambient_life',)
#: Human species (by the character's folder under objects\characters): never enemies.
HUMAN_SPECIES = ('marine', 'masterchief', 'dervish', 'miranda', 'johnson', 'cortana',
                 'odst', 'civilian', 'crewman', 'captain', 'keyes', 'pilot', 'spartan')
SPREAD = 0.6       # world units between a copied location and its source
GAMES = ('Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4')


def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def species(name):
    """The character's folder under characters\\ -- Halo 4's `storm_` prefix dropped, so
    storm_marine is a marine and storm_grunt a grunt."""
    parts = (name or '').lower().split('\\')
    if 'characters' in parts and parts.index('characters') + 1 < len(parts):
        sp = parts[parts.index('characters') + 1]
    else:
        sp = parts[-1]
    return sp[6:] if sp.startswith('storm_') else sp


def _is_boss(name):
    low = (name or '').lower().rsplit('\\', 1)[-1]
    return any(w in low for w in BOSS_WORDS) or species(name) in BOSS_SPECIES


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
        enemy = bool(chars) and not human and not (sides & friends) and \
            not any(species(x) in ALLY_SPECIES for x in chars)
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


# ---- Halo 3 --------------------------------------------------------------------------

def _h3_flags(m, t, i):
    """Expression flags: +0x6 in the third-generation record, +0x14 in Halo 4's (0x1C)."""
    return struct.unpack_from('<H', m.data, t.base + i * t.size + (0x14 if t.size == 0x1C else 6))[0]


def _is_call(t, node):
    """Is `node` a call group? Decided by structure -- its value is the datum of a function
    name node -- because the flag values differ by game (Halo 3: 8 / 10, Halo 4: 32 / 34)."""
    if not node or node['value'] == 0xFFFFFFFF or node['vtype'] == 2:
        return False
    ch = t.at(node['value'] & 0xFFFF)
    return bool(ch) and ch['vtype'] == 2 and (node['value'] >> 16) == ch['salt'] and \
        ch['i'] != node['i']


#: expression flags of a literal (primitive) argument
LITERAL_FLAGS = {'Halo 4': (0x21,)}


def _h3_name(node):
    """The squad an ai argument's text names: 'squad', 'squad/location' -> 'squad'."""
    s = (node or {}).get('string') or ''
    return s.split('/')[0].strip().lower()


def _h3_ai_arg(t, node):
    """The ai text a loading call's object argument carries: `(ai_actors X)` -> X."""
    if not _is_call(t, node):
        return None
    g = t.at(node['value'] & 0xFFFF)
    if g and g['string'] == 'ai_actors':
        a = _args(t, g, 1)
        return a[0] if a else None
    return None


def _h3_effects(t, fn, a, placers, loaders):
    """(placed nodes, bound nodes) of one call `fn` with argument nodes `a`."""
    placed, bound = [], []
    if fn == 'ai_place' and a:
        placed.append(a[0])
    elif fn == 'vehicle_load_magic' and len(a) >= 3:
        x = _h3_ai_arg(t, a[2])
        if x:
            bound.append(x)
    elif fn in ('ai_vehicle_enter_immediate', 'ai_place_in_vehicle') and a:
        bound.append(a[0])
        if fn == 'ai_place_in_vehicle':
            placed.append(a[0])
    for k in placers.get(fn, ()):
        if k < len(a):
            placed.append(a[k])
    for k in loaders.get(fn, ()):
        if k < len(a):
            bound.append(a[k])
            placed.append(a[k])
    return placed, bound


def _script_units(m, game, tree=None):
    """[(Tree, [(script name, [parameter names], root index)])] -- one per script container:
    the scenario (Halo 3 / ODST / Reach) or every hsdt tag (Halo 4, whose compiled scripts
    live in hs_script_data tags: Scripts +0xC elem 0x20, name string id +0x0, root +0xC,
    Parameters +0x14 elem 0x24)."""
    import halo_patch
    import hud_titles
    g = str(game).strip()
    out = []
    if g == 'Halo 4':
        for tag in (m.tags.values() if isinstance(m.tags, dict) else m.tags):
            if not isinstance(tag, dict) or tag.get('class') != 'hsdt' or not tag.get('base'):
                continue
            t = hud_titles.Tree(m, g, halo_patch._block_base, None, container=tag['base'])
            if not t.ok():
                continue
            scripts = []
            for el in m.follow_all(tag['base'], [0xC], [0x20], 'all'):
                params = [m.data[q:q + 0x20].split(b'\0')[0].decode('latin-1').lower()
                          for q in m.follow_all(el, [0x14], [H3_PARAM_SZ], 'all')]
                if params:
                    scripts.append(((m.resolve_stringid(m.u32(el)) or '').lower(), params,
                                    m.u32(el + 0xC) & 0xFFFF))
            out.append((t, scripts))
        return out
    t = tree or _tree(m, g)
    s = halo_patch._scnr_base(m)
    lay = CELL_LAYOUT.get(g)
    soff, ssz, sroot, spar, kind = (lay['scripts'] if lay else
                                    (H3_SCRIPTS, H3_SCRIPT_SZ, H3_SCRIPT_ROOT, H3_SCRIPT_PARAMS,
                                     'ascii'))
    scripts = []
    for el in m.follow_all(s, [soff], [ssz], 'all'):
        params = [m.data[q:q + 0x20].split(b'\0')[0].decode('latin-1').lower()
                  for q in m.follow_all(el, [spar], [H3_PARAM_SZ], 'all')]
        if params:
            sname = (m.resolve_stringid(m.u32(el)) or '' if kind == 'sid' else
                     m.data[el:el + 0x20].split(b'\0')[0].decode('latin-1'))
            scripts.append((sname.lower(), params, m.u32(el + sroot) & 0xFFFF))
    return [(t, scripts)]


def h3_script_refs(m, tree=None, game='Halo 3'):
    """What the compiled scripts do with squads, by NAME: {'place': {name: calls},
    'literal': {name: actors}, 'bound': {names}, 'allied': set, 'removed': set}.

    Level helper scripts take a squad as a parameter (`(ai_gc_jackal sq_gc_jackal_03)`,
    the global `ai_trickle_via_phantom pilot squad`), so each script with parameters is
    walked first: a parameter that reaches ai_place makes the script a PLACER of that
    argument, one that reaches a loading call (vehicle_load_magic ... (ai_actors p),
    ai_vehicle_enter_immediate, ai_place_in_vehicle) a LOADER -- to a fixed point, since
    helpers call helpers (in Halo 4 across hsdt tags: the global script container's
    helpers are called from the scenario's)."""
    units = _script_units(m, game, tree)
    lit_flags = LITERAL_FLAGS.get(str(game).strip(), (F_PRIMITIVE,))

    def body(t, root):
        seen, stack, out = set(), [root], []
        while stack:
            i = stack.pop()
            if i in seen or i >= t.n:
                continue
            seen.add(i)
            r = t.at(i)
            if not r:
                continue
            out.append(r)
            if r['next'] != 0xFFFFFFFF:
                stack.append(r['next'] & 0xFFFF)
            if _is_call(t, r):
                stack.append(r['value'] & 0xFFFF)
        return out

    bodies = [(t, name, params, [r for r in body(t, root) if r['vtype'] == 2])
              for t, scripts in units for name, params, root in scripts]
    placers, loaders = {}, {}
    for _round in range(6):
        changed = False
        for t, name, params, calls in bodies:
            for r in calls:
                p, b = _h3_effects(t, (r['string'] or '').lower(), _args(t, r), placers, loaders)
                for nodes, table in ((p, placers), (b, loaders)):
                    for x in nodes:
                        nm = ((x or {}).get('string') or '').lower()
                        if nm in params:
                            k = params.index(nm)
                            if k not in table.setdefault(name, set()):
                                table[name].add(k)
                                changed = True
        if not changed:
            break
    out = {'place': {}, 'literal': {}, 'bound': set(), 'allied': set(), 'removed': set()}
    for t, _scripts in units:
        for i in range(t.n):
            r = t.at(i)
            if not r or r['vtype'] != 2 or r['next'] == 0xFFFFFFFF:
                continue
            fn = (r['string'] or '').lower()
            a = _args(t, r)
            if fn in ('ai_allegiance', 'ai_allegiance_remove'):
                if len(a) >= 2:
                    pr = ((a[0]['string'] or '').lower(), (a[1]['string'] or '').lower())
                    out['allied' if fn == 'ai_allegiance' else 'removed'].add(pr)
                continue
            p, b = _h3_effects(t, fn, a, placers, loaders)
            for x in p:
                n = _h3_name(x)
                if n:
                    out['place'][n] = out['place'].get(n, 0) + 1
            for x in b:
                if _h3_name(x):
                    out['bound'].add(_h3_name(x))
            if fn == 'ai_place' and len(a) >= 2 and _h3_name(a[0]) and not _is_call(t, a[1]) \
                    and _h3_flags(m, t, a[1]['i']) in lit_flags:
                n = int(t.number(a[1]) or 0)
                if n > 0:
                    k = _h3_name(a[0])
                    out['literal'][k] = out['literal'].get(k, 0) + n
    return out


def _h3_char_team(m, name, depth=0, team_at=H3_BIPD_TEAM):
    if not name or depth > 6:
        return None
    f = m.find_tags('char', name)
    if not f:
        return None
    u = m.u32(f[0][1] + H3_CHAR_UNIT + 0xC)
    if u != 0xFFFFFFFF:
        import halo_patch
        un = halo_patch._tag_name_by_id(m, u)
        fb = m.find_tags('bipd', un) if un else []
        return _i16(m, fb[0][1] + team_at) if fb else None
    p = m.u32(f[0][1] + H3_CHAR_PARENT + 0xC)
    if p != 0xFFFFFFFF:
        import halo_patch
        return _h3_char_team(m, halo_patch._tag_name_by_id(m, p), depth + 1, team_at)
    return None


def h3_squads(m, tree=None):
    """Every FIRE-TEAM (Halo 3's unit of count, character and locations) in the shape of
    h2_squads; squad-level facts (team, placement, script use) are copied onto each.
    `normal` = the count when the team plays on Normal, `insane` = the count of a team that
    plays on Legendary but not Normal (difficulty variants are separate fire-teams)."""
    import halo_patch
    t = tree or _tree(m, 'Halo 3')
    s = halo_patch._scnr_base(m)
    pal, teams = [], []
    for el in m.follow_all(s, [H3_PALETTE], [H3_PAL_SZ], 'all'):
        ident = m.u32(el + H3_PAL_ID)
        nm = halo_patch._tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None
        pal.append(nm)
        teams.append(_h3_char_team(m, nm))
    refs = h3_script_refs(m, t)
    names_of = {TEAM_NAMES[k]: k for k in range(len(TEAM_NAMES))}
    removed = {b for a, b in refs['removed'] if a == 'player'} | \
              {a for a, b in refs['removed'] if b == 'player'}
    friends = {TEAM_PLAYER} | {names_of[n] for n in (
        ({b for a, b in refs['allied'] if a == 'player'} |
         {a for a, b in refs['allied'] if b == 'player'}) - removed) if n in names_of}
    groups = [(m.data[g:g + 0x20].split(b'\0')[0].decode('latin-1').lower(), _i16(m, g + 0x20))
              for g in m.follow_all(s, [H3_GROUPS], [H3_GROUP_SZ], 'all')]
    out = []
    idx = 0
    for sq in m.follow_all(s, [H3_SQUADS], [H3_SQ_SZ], 'all'):
        name = m.data[sq:sq + 0x20].split(b'\0')[0].decode('latin-1').lower()
        names, gi, hops = {name}, _i16(m, sq + H3_SQ_GROUP), 0
        while 0 <= gi < len(groups) and hops < 12:
            names.add(groups[gi][0])
            gi, hops = groups[gi][1], hops + 1
        steam = _i16(m, sq + H3_TEAM)
        initial = bool(m.u32(sq + H3_SQ_FLAGS) & H3_INITIALLY_PLACED)
        placed = initial or any(n in refs['place'] for n in names)
        bound = any(n in refs['bound'] for n in names)
        literal = refs['literal'].get(name, 0)
        fts = m.follow_all(sq, [H3_FIRETEAMS], [H3_FT_SZ], 'all')
        for k, ft in enumerate(fts):
            c = _i16(m, ft + H3_FT_CHAR)
            locs = m.follow_all(ft, [H3_LOCS], [H3_LOC_SZ], 'all')
            ci = {c} if not locs else set()
            foot = 0
            for loc in locs:
                o = _i16(m, loc + H3_LOC_CHAR)
                ci.add(o if o >= 0 else c)
                foot += _i16(m, loc + H3_LOC_VEH) < 0
            ci = {x for x in ci if 0 <= x < len(pal) and pal[x]}
            chars = {pal[x] for x in ci}
            sides = {steam} if steam else {teams[x] for x in ci}
            human = any(_is_human(x) for x in chars)
            enemy = bool(chars) and not human and not (sides & friends) and \
            not any(species(x) in ALLY_SPECIES for x in chars)
            count = _i16(m, ft + H3_FT_COUNT)
            on = struct.unpack_from('<H', m.data, ft + H3_FT_PLACE_ON)[0]
            on_normal = on == 0 or bool(on & 2)
            on_legend = on == 0 or bool(on & 8)
            out.append({'index': idx, 'off': ft, 'name': '%s[%d]' % (name, k),
                        'count': count,
                        'normal': count if on_normal else 0,
                        'insane': count if (on_legend and not on_normal) else 0,
                        'locs': len(locs), 'foot': foot, 'chars': chars, 'enemy': enemy,
                        'ally': bool(chars) and not enemy,
                        'vehicle': _i16(m, ft + H3_FT_VEH) >= 0,
                        'boss': any(_is_boss(x) for x in chars),
                        'script': literal if k == 0 else 0, 'fixed': bool(literal),
                        'bound': bound, 'placed': placed})
            idx += 1
    return out


# ---- Halo 3: ODST ---------------------------------------------------------------------

def cell_squads(m, game, tree=None):
    """Every distinct CELL BLOCK, in the shape of h2_squads plus `mult`.

    ODST squads are built to spawn a cell's count with few or no starting locations --
    6,079 of 6,823 campaign cells count past their single locations and 1,678 squads have
    none -- so a cell grows by its COUNT alone, like a Halo 3 fire-team.

    The ODST tool STORED IDENTICAL CELL ARRAYS ONCE: sc100's 449 cell blocks are 40
    distinct ones, one of them used by 12 squads, and a squad's designer and templated
    cells are nearly always the same block. So the unit here is the cell ELEMENT, and
    `mult` is the number of campaign squads that use it: +1 on its count puts `mult` more
    actors on the level. A cell any of whose squads spawns by script or into a vehicle
    never grows (the shared write would reach that squad too). Firefight's `sq_sur_*`
    squads share some blocks; they are not counted, but a shared cell they use grows for
    them as well. A squad whose designer and templated cells are DIFFERENT blocks (1-6 per
    level) is counted from its templated cells and never grows."""
    import halo_patch
    g = str(game).strip()
    L = CELL_LAYOUT[g]
    t = tree if (tree or g == 'Halo 4') else _tree(m, g)     # Halo 4: scripts in hsdt tags
    s = halo_patch._scnr_base(m)
    pal, teams = [], []
    for el in m.follow_all(s, [L['palette']], [H3_PAL_SZ], 'all'):
        ident = m.u32(el + H3_PAL_ID)
        nm = halo_patch._tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None
        pal.append(nm)
        teams.append(_h3_char_team(m, nm, team_at=L['team']))
    refs = h3_script_refs(m, t, g)
    tn = L['teams'] or TEAM_NAMES
    names_of = {tn[k]: k for k in range(len(tn))}
    removed = {b for a, b in refs['removed'] if a == 'player'} | \
              {a for a, b in refs['removed'] if b == 'player'}
    friends = {TEAM_PLAYER} | {names_of[n] for n in (
        ({b for a, b in refs['allied'] if a == 'player'} |
         {a for a, b in refs['allied'] if b == 'player'}) - removed) if n in names_of}
    groups = [(_cstr(m, x), _i16(m, x + 0x20))
              for x in m.follow_all(s, [L['groups']], [H3_GROUP_SZ], 'all')]
    units, order = {}, []
    for sq in m.follow_all(s, [L['squads'][0]], [L['squads'][1]], 'all'):
        name = _cstr(m, sq)
        names, gi, hops = {name}, _i16(m, sq + H3_SQ_GROUP), 0
        while 0 <= gi < len(groups) and hops < 12:
            names.add(groups[gi][0])
            gi, hops = groups[gi][1], hops + 1
        # FIREFIGHT shares these maps: its `sq_sur_*` squads are spawned by the survival
        # system (and a few by name from the survival scripts compiled in beside the
        # campaign's) -- never campaign squads, so never counted.
        placed = not name.startswith('sq_sur') and (
            bool(m.u32(sq + H3_SQ_FLAGS) & H3_INITIALLY_PLACED) or
            any(n in refs['place'] for n in names))
        bound = any(n in refs['bound'] for n in names)
        literal = refs['literal'].get(name, 0)
        d_off, t_off = L['cells']
        dptr, tptr = m.u32(sq + d_off + 4), m.u32(sq + t_off + 4)
        split = bool(m.u32(sq + d_off) and m.u32(sq + t_off) and dptr != tptr)
        use = t_off if m.u32(sq + t_off) else d_off
        cells = m.follow_all(sq, [use], [L['cell_sz']], 'all')
        # Halo 4 keeps no shared blocks, and a squad's designer and templated cells are
        # separate copies with the same counts: grow the designer twin with its templated
        # cell, whichever of the two the engine reads.
        twins = (m.follow_all(sq, [d_off], [L['cell_sz']], 'all')
                 if split and L.get('twins') else [])
        if twins and len(twins) == len(cells) and all(
                _i16(m, a + L['count']) == _i16(m, b + L['count']) for a, b in zip(cells, twins)):
            split = False
        else:
            twins = []
        locs = m.follow_all(sq, [L['locs'][0]], [L['locs'][1]], 'all')
        steam = _i16(m, sq + H3_TEAM)
        for n, cell in enumerate(cells):
            u = units.get(cell)
            if u is None:
                u = units[cell] = {'off': cell, 'users': 0, 'chars': set(), 'steam': set(),
                                   'bound': False, 'fixed': False, 'split': False, 'script': 0,
                                   'names': [], 'twins': []}
                order.append(cell)
            u['chars'] |= {_i16(m, loc + L['locs'][3]) for loc in locs
                           if _i16(m, loc + L['locs'][2]) == n}
            u['steam'].add(steam)
            if twins:
                u['twins'].append(twins[n])
                co, ce, cx = L['chars']
                u['chars'] |= {_i16(m, e + cx) for e in m.follow_all(twins[n], [co], [ce], 'all')}
            if placed:
                u['users'] += 1
                u['names'].append(name)
                u['bound'] |= bound
                u['fixed'] |= bool(literal)
                u['split'] |= split
                if n == 0:
                    u['script'] += literal
    out = []
    for idx, cell in enumerate(order):
        u = units[cell]
        co, ce, cx = L['chars']
        ci = {_i16(m, e + cx) for e in m.follow_all(cell, [co], [ce], 'all')} | u['chars']
        ci = {x for x in ci if 0 <= x < len(pal) and pal[x]}
        chars = {pal[x] for x in ci}
        sides = {x for x in u['steam'] if x} or {teams[x] for x in ci}
        human = any(_is_human(x) for x in chars)
        enemy = bool(chars) and not human and not (sides & friends) and \
            not any(species(x) in ALLY_SPECIES for x in chars)
        count = _i16(m, cell + L['count'])
        on = struct.unpack_from('<H', m.data, cell + L['diff'])[0]
        on_normal = on == 0 or bool(on & 2)
        on_legend = on == 0 or bool(on & 8)
        out.append({'index': idx, 'off': cell,
                    'name': '%s (+%d)' % (u['names'][0], u['users'] - 1) if u['users'] > 1
                    else (u['names'][0] if u['names'] else 'cell@%x' % cell),
                    'count': count, 'mult': max(u['users'], 1),
                    'normal': count if on_normal else 0,
                    'insane': count if (on_legend and not on_normal) else 0,
                    'locs': 0, 'foot': 1, 'chars': chars, 'enemy': enemy,
                    'ally': bool(chars) and not enemy,
                    'vehicle': _i16(m, cell + L['veh']) >= 0, 'twins': u['twins'],
                    'boss': any(_is_boss(x) for x in chars),
                    'script': u['script'], 'fixed': u['fixed'] or u['split'],
                    'bound': u['bound'], 'placed': u['users'] > 0})
    return out


def odst_squads(m, tree=None):
    return cell_squads(m, 'Halo 3: ODST', tree)


def reach_squads(m, tree=None):
    return cell_squads(m, 'Halo Reach', tree)


def _cstr(m, off):
    return m.data[off:off + 0x20].split(bytes(1))[0].decode('latin-1').strip().lower()


# ---- shared ------------------------------------------------------------------------

def squads(m, game):
    g = str(game).strip()
    return (h1_squads(m) if g == 'Halo 1' else h2_squads(m) if g == 'Halo 2' else
            h3_squads(m) if g == 'Halo 3' else cell_squads(m, g) if g in CELL_LAYOUT else None)


def _matching(m, game, all_squads, pattern, side='enemy', include_boss=False):
    """Infantry squads on `side` fielding a character the card's pattern names (a mixed
    squad counts for each species in it). Halo 1 patterns name actor variants (actv)."""
    cls = 'actv' if str(game).strip() == 'Halo 1' else 'char'
    names = {p.lower() for p, _b in m.find_tags(cls, pattern)} if pattern else None
    out = []
    for sq in all_squads:
        # a boss is grown only by a card that names it (include_boss), never a general one
        if not sq[side] or sq['vehicle'] or (sq['boss'] and not include_boss):
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
    if sq.get('fixed'):        # another fire-team of a squad placed with a fixed count
        return 0
    # an ODST cell block shared by several squads spawns its count for each of them
    return max(sq[key], 0) * sq.get('mult', 1) if sq['placed'] else 0


def _takes_extras(sq):
    return (not sq['script'] and not sq.get('fixed') and not sq['bound'] and sq['placed']
            and sq['foot'] > 0
            and (sq['normal'] > 0 or sq['insane'] > 0))


def _allocate(squads, key, extra, rng):
    """{squad index: count increase} -- `extra` ACTORS spread over `squads` in proportion to
    the actors each spawns (`key` count x `mult`): the whole part of each share, then the
    leftovers drawn by fractional share without replacement. A unit with `mult` > 1 (an
    ODST cell block shared by several squads) moves in steps of `mult` actors."""
    total = sum(sq[key] * sq.get('mult', 1) for sq in squads)
    if extra <= 0 or total <= 0:
        return {}
    got, frac, mult = {}, [], {}
    for sq in squads:
        mu = sq.get('mult', 1)
        mult[sq['index']] = mu
        share = sq[key] * mu * extra / float(total) / mu      # in count steps
        whole = int(math.floor(share))
        if whole:
            got[sq['index']] = whole
        if share > whole:
            frac.append([sq['index'], share - whole])
    left = extra - sum(n * mult[i] for i, n in got.items())
    while left > 0 and frac:
        r = rng.random() * sum(w for _i, w in frac)
        for k, (i, w) in enumerate(frac):
            r -= w
            if r <= 0 or k == len(frac) - 1:
                got[i] = got.get(i, 0) + 1
                left -= mult[i]
                frac.pop(k)
                break
    return got


def _copies(m, foot, loc_sz, pos_at, need, spread):
    """`need` copies of the on-foot locations `foot`, cycling, nudged around their source."""
    out = []
    for k in range(need):
        e = bytearray(m.data[foot[k % len(foot)]:foot[k % len(foot)] + loc_sz])
        x, y, z = struct.unpack_from('<fff', e, pos_at)
        ring = k // len(foot) + 1
        ang = 2.0 * math.pi * (k % len(foot)) / len(foot) + ring
        struct.pack_into('<fff', e, pos_at, x + spread * ring * math.cos(ang),
                         y + spread * ring * math.sin(ang), z)
        out.append(bytes(e))
    return out


def grow_all(m, game, plan, spread=SPREAD):
    """Apply [(squad, new normal, new insane)] and return the number of locations added.

    Halo 1 / Halo 2: write the counts and copy on-foot locations up to the new count
    (the grown block is appended at the end of the tag data).

    Halo 3: the COUNT alone. Its engine spawns a fire-team's whole count even past its
    starting locations and the extras line up next to each other -- confirmed in game on
    010 (two Chieftains from one location) and on 020 at x3 for enemies and allies alike
    (2026-10-04). So Halo 3 needs no copied locations and no map space at all; copying them
    would have to relocate the block into scarce zero slack (Halo 3 cannot append)."""
    g = str(game).strip()
    if g == 'Halo 3' or g in CELL_LAYOUT:
        at = H3_FT_COUNT if g == 'Halo 3' else CELL_LAYOUT[g]['count']
        for sq, normal, insane in plan:
            n = sq['count'] + (normal - sq['normal']) + (insane - sq['insane'])
            for off in [sq['off']] + list(sq.get('twins') or ()):
                struct.pack_into('<h', m.data, off + at, n)
        return 0
    h1 = g == 'Halo 1'
    locs_off, loc_sz, cnt_off = ((H1_LOCS, H1_LOC_SZ, H1_NORMAL) if h1 else
                                 (H2_LOCS, H2_LOC_SZ, H2_NORMAL))
    added, jobs = 0, []
    for sq, normal, insane in plan:
        need = max(normal, insane) - sq['locs']
        if need > 0 and sq['foot'] > 0:
            foot = [loc for loc in m.follow_all(sq['off'], [locs_off], [loc_sz], 'all')
                    if h1 or _i16(m, loc + H2_LOC_VEH) < 0]
            jobs.append((sq['off'], locs_off, loc_sz, _copies(m, foot, loc_sz, 0, need, spread)))
            added += need
        struct.pack_into('<hh', m.data, sq['off'] + cnt_off, normal, insane)
    if h1:
        for job in jobs:
            m.grow_block(*job)          # Halo 1 appends 4-aligned: no pad to save
    else:
        m.grow_blocks(jobs)             # Halo 2: one region, one 4 KB pad for them all
    return added


def grow(m, game, sq, normal, insane, spread=SPREAD):
    """One squad (see grow_all)."""
    return grow_all(m, game, [(sq, normal, insane)], spread)


def _scnr_name(m, game):
    if str(game).strip() == 'Halo 2':
        return (m.scenario_tag() or {}).get('name') or ''
    found = m.find_tags('scnr', '*')
    return found[0][0] if found else ''


def enemy_total(m, game, pattern=None, side='enemy', include_boss=False):
    """(squad actors, script actors, squads) the card would count -- Normal difficulty."""
    if str(game).strip() not in GAMES:
        return None
    sq = _matching(m, game, squads(m, game), pattern, side, include_boss)
    return (sum(_spawns(s, 'normal') for s in sq if not s['script']),
            sum(s['script'] for s in sq), sum(1 for s in sq if _spawns(s, 'normal')))


def scale_enemy_count(m, game, pattern, pct, seed, side='enemy', include_boss=False):
    """Add round(pct x the level's matching actors) actors to the matching squads.

    Returns {'ok', 'skip', 'reason' | 'base', 'script', 'extra', 'squads', 'locations'}."""
    if str(game).strip() not in GAMES:
        return {'ok': True, 'skip': True, 'reason': 'spawn count is not available in this game yet'}
    if pct <= 0:
        return {'ok': True, 'skip': True, 'reason': 'no increase'}
    matched = [sq for sq in _matching(m, game, squads(m, game), pattern, side, include_boss)
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
    work = []
    for sq in takers:
        dn = plan['normal'][2].get(sq['index'], 0)
        di = plan['insane'][2].get(sq['index'], 0)
        if dn or di:
            work.append((sq, sq['normal'] + dn if sq['normal'] > 0 else 0,
                         sq['insane'] + di if sq['insane'] > 0 else 0))
    locs = grow_all(m, game, work)
    changed = len(work)
    return {'ok': True, 'skip': False, 'base': plan['normal'][0], 'script': script,
            'extra': plan['normal'][1], 'extra_insane': plan['insane'][1],
            'squads': changed, 'of': len(takers), 'locations': locs}
