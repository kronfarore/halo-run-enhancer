r"""Halo 3 'Armed: <weapon>' -- what weapons the AI carries, at patch time (2026-11-02,
sprint_toolkit/ARMED_ALL_GAMES.md; scoping in sprint_toolkit/armed_scope/h3_odst/).
The Halo 3 counterpart of h2_enemy_weapons.py, same shape:

    apply(m, hp, spec) -> [result rows]        (halo_patch calls it after the skulls; Halo 3)
    spec = {'cards': {'Grunt': {<weapon tag>: share, ...}, 'Marine': {...}, ...}}

USER DECISIONS (2026-11-02): every weapon is assumed loaded and every species present on every
map (no residency gate here; species residency is its own work item, the Halo 1 chain trick).

ARMING. A squad's FIRE-TEAMS (scnr squads +0x384/0x40 > fire-teams +0x30/0x60: character +0x8,
weapon / secondary +0xA / +0xC) and their STARTING LOCATIONS (+0x54/0x88: character +0x28, -1 =
the fire-team's; weapon +0x2A / +0x2C, -1 = the fire-team's) index the scnr Weapon Palette
(+0x120/0x10). Every fire-team and every location with its own weapon whose character is of a
carded type draws a deterministic number (level name + the field's address: co-op partners and
re-patches agree); below the sum of the shares it takes the weapon whose interval holds it (above
100% the shares count by weight), secondary -1. EVERY unit of a carded type is armed (vehicle /
script-loaded squads too, the Halo 2 rule); enemy-type cards arm allied units of the type too,
the Ally card (Marine) only friendly ones. Halo 3 shares no squad arrays (checked 2026-10-04).

THE GATE (H3EK sapien unit_can_use_weapon, scoping 2026-11-02): a unit holds a weapon only if
its animation graph has an 'idle' action for (mode, class, type) with 'any' fallbacks for each,
mode 'combat'; the graph's Weapon List (jmad +0x8C) can re-class a weapon by its NAME. A refused
weapon = the unit spawns UNARMED. So a unit only draws among the weapons its species' graphs
allow, and a location of ANOTHER species that inherits its fire-team's new weapon but cannot
hold it keeps the fire-team's ORIGINAL weapon (written explicitly). Graphs: every jmad under
objects\characters\<species folder>\ (not fp / lipsync / cinematics); all of a species' graphs
must allow the weapon. Labels are compared as RAW string ids; only 'any', 'combat' and 'idle'
are looked up by name (static ids).

JACKALS. A Jackal location handed a two-handed weapon (not class pistol, not dual-wieldable)
spawns without its arm shield: Actor Variant Name (+0x38, string id) = 'shieldless', the jackal
model's own variant; one handed a one-handed weapon gets the shield back (variant cleared). A
fire-team has no variant field: its extras past the locations keep the shield (reported).

FIRING DATA (user 2026-11-02): the ODST Magnum, the Silenced SMG and the Brute Plasma Rifle have
no ai\generic rows; they borrow the Magnum's, the SMG's and the Plasma Rifle's (FIRING_DONORS,
borrow_firing). The SAW is kept out (EXCLUDED) until Halo 3's weapon ports.

HALO 3: ODST (2026-11-06) runs the same pass after bind('Halo 3: ODST'): its tags sit at other
offsets (LAYOUTS) and its squads are CELLS: a squad's Single Locations (spawn points +0x3C/0x90:
cell +0x10, character +0x32, weapon +0x34, Actor Variant Name +0x44) spawn the units its Designer /
Templated Cells (+0x54 / +0x60, 0x84) describe -- a Character Type and an Initial Weapon array per
cell (0x10 elements: index +0xC, Chance +0xE), the weapon arrays often SHARED between cells (Grunts
and Jackals on one Needler / Plasma Pistol array) or EMPTY. A cell of a carded type draws once
(deterministic by its address); a shared array is copied first, an empty one gets one element,
then every element names the drawn weapon. A spawn point with its own weapon draws for itself.
Jackal spawn points whose cell is all Jackals take 'shieldless' with a two-handed weapon; a cell's
units past its spawn points keep the shield.
"""
import hashlib
import struct

GAME = 'Halo 3'
BS = chr(92)
ENEMY_CHARS = {
    'Grunt': ('grunt',),
    'Jackal': ('jackal',),
    'Elite': ('elite',),
    'Brute': ('brute',),
    'Bugger': ('bugger',),
    'Flood Combat Form': ('floodcombat_elite', 'floodcombat_human', 'floodcombat_brute'),
    'Skirmisher': (),                               # Reach: NAME_TYPES / GRAPH_FOLDERS
    'Marine': ('marine', 'marine_female'),          # the Ally (Friend) twin
}
#: story characters / bosses never armed (their scripts and weapons are their own)
NEVER = ('brute_chieftain', 'brute_chieftain_armor', 'brute_chieftain_weapon', 'truth',
         'dervish', 'marine_johnson', 'johnson', 'miranda', 'guilty_spark')
ALLY_TYPES = ('Marine',)
SQUADS, SQ_ES, SQ_TEAM = 0x384, 0x40, 0x24
FT, FT_ES, FT_CHAR, FT_WEAP = 0x30, 0x60, 0x8, 0xA
LOCS, LOC_ES, LOC_CHAR, LOC_WEAP, LOC_VARIANT = 0x54, 0x88, 0x28, 0x2A, 0x38
CPAL, CPAL_ES, CPAL_ID = 0x3A8, 0x10, 0xC
WPAL, WPAL_ES, WPAL_ID = 0x120, 0x10, 0xC
# weap: class / name string ids +0x3DC / +0x3E0, flags +0x18C (bit 16 can / 17 only dual wield)
WEAP_CLASS, WEAP_NAME, WEAP_FLAGS, DUAL_BITS = 0x3DC, 0x3E0, 0x18C, 3 << 16
# jmad: Modes +0x5C (0x28) > Classes +0x4 (0x1C) > Types +0x4 (0x34) > Actions +0x4 (0x8);
# Weapon List +0x8C (0x8: weapon name, class)
JM_MODES, JM_MODE_ES, JM_SUB, JM_CLASS_ES, JM_TYPE_ES, JM_ACT_ES = 0x5C, 0x28, 0x4, 0x1C, 0x34, 0x8
# the sub-block offsets per level (Halo 3 / ODST: all +0x4); Reach puts its actions in SETS
JM_CLASS_SUB, JM_TYPE_SUB, JM_SET_SUB, JM_SET_ES, JM_ACT_SUB = 0x4, 0x4, None, 0, 0x4
#: weap -> its hlmt (Model tagRef), hlmt -> render model; hlmt model Variants (name +0, Objects +0x20)
WEAP_MODEL, HLMT_VARIANTS, HLMT_VARIANT_ES, HLMT_VARIANT_OBJECTS = 0x34, 0x64, 0x48, None
#: firing block element sizes (Weapons Properties, Firing Pattern Properties)
GEN_PROPS_ES = 0xE0
JM_WL, JM_WL_ES = 0x8C, 0x8
DUAL_CLASS = 0x1F4                 # the 'dual' class id: the Weapon List never re-classes it
PISTOL_NAMES = ('pistol',)
# ai\generic: Weapons Properties / Firing Pattern Properties (ai_firing_profile SOURCES['Halo 3'])
GEN_PROPS, GEN_FPP = 0x174, 0x180
#: (block, element size, weapon datum offset) of a character's two firing blocks
FIRING_BLOCKS = ((GEN_PROPS, GEN_PROPS_ES, 0x10), (GEN_FPP, 0x1C, 0xC))
#: never handed out (tag basenames): the SAW has no ai\generic data and waits for Halo 3's
#: weapon ports (user 2026-11-02)
EXCLUDED = ('saw', 'machinegun_turret_jorge')    # Reach: Jorge's own chaingun, a story weapon
#: weapons without ai\generic rows borrow a donor's rows (user 2026-11-02), tag basenames
#: never TAUGHT (user 2026-11-03: every enemy wields every weapon, the two melee weapons excepted
#: for now): a species that already holds them keeps getting them
NOT_TAUGHT = ('energy_blade', 'energy_sword', 'gravity_hammer')      # Reach's sword: energy_sword
#: donor weapons whose class a refused weapon borrows, by the refused weapon's kind (tag basenames)
TEACH_DONORS = {
    'heavy': ('rocket_launcher', 'flak_cannon', 'spartan_laser', 'brute_shot', 'battle_rifle', 'dmr',
              'assault_rifle', 'covenant_carbine', 'plasma_rifle'),
    'rifle': ('assault_rifle', 'battle_rifle', 'dmr', 'covenant_carbine', 'needle_rifle', 'plasma_rifle', 'smg',
              'rocket_launcher'),
    'pistol': ('plasma_pistol', 'magnum', 'needler', 'assault_rifle', 'plasma_rifle'),
}
FIRING_DONORS = {'automag': 'magnum', 'smg_silenced': 'smg', 'plasma_rifle_red': 'plasma_rifle'}
# ODST squads (scnr +0x3B8 / 0x6C): spawn points and cells (see the module text)
SP, SP_ES, SP_CELL, SP_CHAR, SP_WEAP, SP_VARIANT = 0x3C, 0x90, 0x10, 0x32, 0x34, 0x44
CELL_BLOCKS, CELL_ES, CELL_COUNT = (0x54, 0x60), 0x84, 0x10
CELL_CHARS, CELL_WEAPS, CELL_ARR_ES, CELL_IDX, CELL_CHANCE = 0x14, 0x20, 0x10, 0xC, 0xE
#: per game: what bind() sets (Halo 3 is the module default)
LAYOUTS = {
    'Halo 3': dict(SQUADS=0x384, SQ_ES=0x40, CPAL=0x3A8, WPAL=0x120, WEAP_CLASS=0x3DC,
                   WEAP_NAME=0x3E0, WEAP_FLAGS=0x18C, GEN_PROPS=0x174, GEN_FPP=0x180,
                   BIPD_PREFERRED=0x1A4),
    'Halo 3: ODST': dict(SQUADS=0x3B8, SQ_ES=0x6C, CPAL=0x3E8, WPAL=0x13C, WEAP_CLASS=0x3EC,
                         WEAP_NAME=0x3F0, WEAP_FLAGS=0x19C, GEN_PROPS=0x198, GEN_FPP=0x1A4,
                         BIPD_PREFERRED=0x1B4),
    # Reach (2026-11-09; scoping armed_scope/reach/NOTES.md + the Reach / ReachMCC plugins): the
    # graph walk Modes +0x104/0x30 > class +0xC/0x38 > type +0x8/0x14 > sets +0x8/0x48 > actions
    # +0xC/0xC, Weapon List +0x140; cells 0x6C, spawn points 0x7C; char root 0x270, Variants
    # elements 0x18; weap / biped Model +0x64; hlmt Variants +0x84/0x38 (Objects +0x20: the
    # Jackal shield is a CHILD OBJECT of the jackal_minor / jackal_major variants)
    'Halo Reach': dict(SQUADS=0x398, SQ_ES=0x6C, CPAL=0x3EC, WPAL=0x168, WEAP_CLASS=0x3AC,
                       WEAP_NAME=0x3B0, WEAP_FLAGS=0x204, GEN_PROPS=0x1EC, GEN_PROPS_ES=0xC4,
                       GEN_FPP=0x1F8, BIPD_PREFERRED=0x348, WEAP_MODEL=0x64,
                       JM_MODES=0x104, JM_MODE_ES=0x30, JM_CLASS_SUB=0xC, JM_CLASS_ES=0x38,
                       JM_TYPE_SUB=0x8, JM_TYPE_ES=0x14, JM_SET_SUB=0x8, JM_SET_ES=0x48,
                       JM_ACT_SUB=0xC, JM_ACT_ES=0xC, JM_WL=0x140, SP_ES=0x7C, CELL_ES=0x6C,
                       CHAR_ROOT=0x270, CHAR_VARIANT_ES=0x18, HLMT_VARIANTS=0x84,
                       HLMT_VARIANT_ES=0x38, HLMT_VARIANT_OBJECTS=0x20),
}
# what bind() resets when it switches back to a game whose LAYOUTS entry leaves a key out
_DEFAULTS = dict(WEAP_MODEL=0x34, GEN_PROPS_ES=0xE0, JM_MODES=0x5C, JM_MODE_ES=0x28,
                 JM_CLASS_SUB=0x4, JM_CLASS_ES=0x1C, JM_TYPE_SUB=0x4, JM_TYPE_ES=0x34,
                 JM_SET_SUB=None, JM_SET_ES=0, JM_ACT_SUB=0x4, JM_ACT_ES=0x8, JM_WL=0x8C,
                 SP_ES=0x90, CELL_ES=0x84, CHAR_ROOT=0x1F8, CHAR_VARIANT_ES=0x14,
                 HLMT_VARIANTS=0x64, HLMT_VARIANT_ES=0x48, HLMT_VARIANT_OBJECTS=None)
#: games whose squads are cells (_arm_cells)
CELL_GAMES = ('Halo 3: ODST', 'Halo Reach')
#: ODST's own story characters (squad mates, Dare, the Superintendent's avatars) are never armed
NEVER_WORDS = {'Halo 3: ODST': ('odst', 'dare', 'vergil', 'buck', 'dutch', 'mickey', 'romeo'),
               # Noble Team, Halsey, Keyes and the scripted heroes keep their own weapons
               'Halo Reach': ('spartan', 'noble', 'jorge', 'kat', 'carter', 'emile', 'jun',
                              'halsey', 'keyes', 'holland', 'hero', 'story', 'bob')}
#: Reach's Skirmishers are Jackals by folder and graph but their own enemy type in halo.json
NAME_TYPES = {'Halo Reach': (('skirmisher', 'Skirmisher'),)}
#: graph folders per species where they differ from ENEMY_CHARS (Reach's AI Elites animate
#: through objects/characters/elite_ai, the 'elite' graph is the players')
GRAPH_FOLDERS = {'Halo Reach': {'Elite': ('elite_ai',), 'Skirmisher': ('jackal',)}}


def bind(game, m=None, hp=None):
    """Point the module at `game`'s layout (Halo 3 or ODST). With the map: the 'dual' class id."""
    global GAME, FIRING_BLOCKS, DUAL_CLASS
    GAME = game
    globals().update(_DEFAULTS)
    globals().update(LAYOUTS[game])
    globals()['REPOSE'] = REPOSE_BY_GAME.get(game, {})
    FIRING_BLOCKS = ((GEN_PROPS, GEN_PROPS_ES, 0x10), (GEN_FPP, 0x1C, 0xC))
    if m is not None:
        DUAL_CLASS = find_sid(m, hp, 'dual') or (0x1F4 if game == 'Halo 3' else DUAL_CLASS)


def enemy_of(char_path):
    """The enemy type a character tag belongs to, or None (objects / characters / <folder> / ai)."""
    if not char_path:
        return None
    parts = char_path.lower().split(BS)
    if len(parts) < 3 or parts[-1] in NEVER \
            or any(w in parts[-1] for w in NEVER_WORDS.get(GAME, ())):
        return None
    for word, kind in NAME_TYPES.get(GAME, ()):
        if parts[-1].startswith(word):
            return kind
    return next((e for e, fs in ENEMY_CHARS.items() if parts[2] in fs), None)


def graph_folders(enemy):
    return GRAPH_FOLDERS.get(GAME, {}).get(enemy) or ENEMY_CHARS.get(enemy, ())


def _draw(salt, addr):
    return int(hashlib.sha256(('%s|%d' % (salt, addr)).encode()).hexdigest()[:8], 16) / 2.0 ** 32


def _pick(shares, x):
    total = sum(shares.values())
    if total <= 0:
        return None
    scale = 1.0 / total if total > 1.0 else 1.0
    acc = 0.0
    for w, s in sorted(shares.items()):
        acc += s * scale
        if x < acc:
            return w
    return None


def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def _name(m, hp, sid):
    try:
        return (m.resolve_stringid(sid) or '').lower()
    except Exception:
        return ''


# ----------------------------------------------------------------------------- the gate
class Graphs:
    """Every species graph of the map as {mode id: {class id: {type id: set(action ids)}}} plus
    its Weapon List, and the raw ids of 'any', 'combat', 'idle' -- the gate's names."""

    def __init__(self, m, hp):
        self.m, self.hp = m, hp
        self.by_folder = {}
        self.any = self.combat = self.idle = None
        for p, b in m.find_tags('jmad', '*'):
            lo = p.lower()
            parts = lo.split(BS)
            if len(parts) < 3 or parts[0] != 'objects' or parts[1] != 'characters':
                continue
            if any(x in lo for x in ('cinematics', 'lipsync', BS + 'fp')):
                continue
            g = self._read(b)
            if g['modes']:
                self.by_folder.setdefault(parts[2], []).append((p, g))

    def _read(self, b):
        m = self.m
        modes, where = {}, {}
        for md in m.follow_all(b, [JM_MODES], [JM_MODE_ES], 'all'):
            ml = m.u32(md)
            self._learn(ml)
            cls = modes.setdefault(ml, {})
            for c in m.follow_all(md, [JM_CLASS_SUB], [JM_CLASS_ES], 'all'):
                cl = m.u32(c)
                self._learn(cl)
                tys = cls.setdefault(cl, {})
                where[(ml, cl)] = c
                for t in m.follow_all(c, [JM_TYPE_SUB], [JM_TYPE_ES], 'all'):
                    tl = m.u32(t)
                    where[(ml, cl, tl)] = t
                    self._learn(tl)
                    holders = [t] if JM_SET_SUB is None else \
                        m.follow_all(t, [JM_SET_SUB], [JM_SET_ES], 'all')    # Reach: every set
                    acts = set(m.u32(a) for h in holders
                               for a in m.follow_all(h, [JM_ACT_SUB], [JM_ACT_ES], 'all'))
                    if self.idle is None:
                        for a in acts:
                            self._learn(a)
                    tys[tl] = acts
        wl = {m.u32(e): m.u32(e + 4) for e in m.follow_all(b, [JM_WL], [JM_WL_ES], 'all')}
        return {'modes': modes, 'wl': wl, 'base': b, 'where': where}

    def _learn(self, sid):
        if None not in (self.any, self.combat, self.idle):
            return
        n = _name(self.m, self.hp, sid)
        if n == 'any' and self.any is None:
            self.any = sid
        elif n == 'combat' and self.combat is None:
            self.combat = sid
        elif n == 'idle' and self.idle is None:
            self.idle = sid

    def holds(self, g, wclass, wname):
        """sapien's lookup: mode 'combat' then 'any', class (Weapon List re-class by name) then
        'any', type = the weapon's name then 'any'; an 'idle' action in any of them."""
        cl = wclass
        ov = g['wl'].get(wname)
        if ov is not None and ov != self.any and wclass != DUAL_CLASS:
            cl = ov
        for mo in (self.combat, self.any):
            M = g['modes'].get(mo)
            if not M:
                continue
            for c in (cl, self.any):
                C = M.get(c)
                if not C:
                    continue
                for t in (wname, self.any):
                    T = C.get(t)
                    if T and self.idle in T:
                        return True
        return False

    def allows(self, enemy, wclass, wname):
        """Every graph of the enemy type's folders holds the weapon (no graph = refuse)."""
        found = False
        for folder in graph_folders(enemy):
            for _p, g in self.by_folder.get(folder, ()):
                found = True
                if not self.holds(g, wclass, wname):
                    return False
        return found


def weapon_info(m, weapon):
    t = dict(m.find_tags('weap', weapon)).get(weapon)
    if t is None:
        return None
    return {'class': m.u32(t + WEAP_CLASS), 'name': m.u32(t + WEAP_NAME),
            'dual': bool(m.u32(t + WEAP_FLAGS) & DUAL_BITS)}


def two_handed(m, hp, info):
    return bool(info) and not info['dual'] and _name(m, hp, info['class']) not in PISTOL_NAMES


def has_firing(m, hp, weapon):
    """ai / generic carries Weapons Properties AND a Firing Pattern Properties entry for it."""
    g = dict(m.find_tags('char', 'ai' + BS + 'generic')).get('ai' + BS + 'generic')
    if g is None:
        return None
    want = weapon.lower()

    def any_entry(off, es, at):
        for e in m.follow_all(g, [off], [es], 'all'):
            if (hp._tag_name_by_id(m, m.u32(e + at)) or '').lower() == want:
                return True
        return False
    # element sizes / weapon datum offsets as ai_firing_profile reads them (Halo 3)
    return any_entry(GEN_PROPS, GEN_PROPS_ES, 0x10) and any_entry(GEN_FPP, 0x1C, 0xC)


#: games where a species character with its OWN firing rows gets ai/generic's row for a handed
#: weapon its list lacks (Reach boot 2: Jackals -- the only species with own Weapons Properties,
#: Focus / Needle Rifle, Needler, Plasma Pistol -- held the DMR and did not attack; Grunts /
#: Troopers with no own rows fire everything)
#: Elites (own rows: grenade / rocket launcher) fire an Assault Rifle fine, so a per-weapon fallback
#: works -- an experiment, limited to the Jackal graph's species
SPECIES_FIRING = {'Halo Reach': ('Jackal', 'Skirmisher')}


def species_firing(m, hp, pairs):
    """`pairs` = [(enemy, weapon path)]: every palette character of the species whose Weapons
    Properties / Firing Pattern Properties are non-empty and lack the weapon gets ai/generic's
    row for it (blocks relocated sorted-free: appended, as borrow_firing does). Result rows."""
    rows = []
    pairs = [(e, w) for e, w in pairs if e in SPECIES_FIRING.get(GAME, ())]
    if not pairs:
        return rows
    gen = dict(m.find_tags('char', 'ai' + BS + 'generic')).get('ai' + BS + 'generic')
    if gen is None:
        return rows
    base = hp._scnr_base(m)
    pal = [hp._tag_name_by_id(m, m.u32(e + CPAL_ID)) for e in m.follow_all(base, [CPAL], [CPAL_ES], 'all')]
    want = {}
    for enemy, w in pairs:
        for c in pal:
            if c and enemy_of(c) == enemy:
                want.setdefault(c, set()).add(w.lower())
    for c, ws in sorted(want.items()):
        cb = dict(m.find_tags('char', c)).get(c)
        if cb is None:
            continue
        for off, es, at in FIRING_BLOCKS:
            els = m.follow_all(cb, [off], [es], 'all')
            if not els:
                continue                     # an empty block inherits the parent's rows whole
            have = {(hp._tag_name_by_id(m, m.u32(e + at)) or '').lower() for e in els}
            extra, added = bytearray(), []
            for g in m.follow_all(gen, [off], [es], 'all'):
                gn = (hp._tag_name_by_id(m, m.u32(g + at)) or '').lower()
                if gn in ws and gn not in have:
                    extra += m.data[g:g + es]
                    added.append(gn.rsplit(BS, 1)[-1])
                    have.add(gn)
            if not extra:
                continue
            blk = cb + off
            n = max(0, m.i32(blk))
            got = hp._h3_reserve(m, [n * es + len(extra)])
            if not got:
                continue
            old = hp._block_base(m, blk)
            m.data[got[0]:got[0] + n * es] = m.data[old:old + n * es]
            m.data[got[0] + n * es:got[0] + n * es + len(extra)] = extra
            struct.pack_into('<iI', m.data, blk, n + len(extra) // es, m.off2data(got[0]))
            rows.append({'tag': 'char ' + c.rsplit(BS, 1)[-1], 'field': 'firing rows (+0x%X)' % off,
                         'ok': True, 'new': "ai/generic's " + ', '.join(added)})
    return rows


def borrow_firing(m, hp, weapons):
    """Give each of `weapons` (tag paths) without firing data its FIRING_DONORS donor's rows:
    every character whose Weapons Properties / Firing Pattern Properties lists the donor and
    not the weapon gets a copy of the donor's row naming the weapon (sub-blocks shared, the
    block relocated into partition slack as hunter_drop grows blocks). Returns result rows."""
    rows, want = [], {}
    for w in weapons:
        base = w.lower().rsplit(BS, 1)[-1]
        donor = FIRING_DONORS.get(base)
        if not donor or has_firing(m, hp, w) is not False:
            continue
        # the donor's own path: the weapon whose basename is the donor's, from the tag list
        dtag = next((p for p, _b in m.find_tags('weap', '*') if p.lower().rsplit(BS, 1)[-1] == donor),
                    None)
        datum = hp._h3_tag_datum(m, 'weap', w)
        if dtag is None or datum is None:
            rows.append({'tag': 'char ai' + BS + 'generic', 'field': 'firing data: ' + base,
                         'ok': False, 'reason': 'donor %s or the weapon not in this map' % donor})
            continue
        want[base] = (dtag.lower(), datum, donor)
    if not want:
        return rows
    for p, b in m.find_tags('char', '*'):
        for off, es, at in FIRING_BLOCKS:
            elems = m.follow_all(b, [off], [es], 'all')
            if not elems:
                continue
            names = [(hp._tag_name_by_id(m, m.u32(e + at)) or '').lower() for e in elems]
            extra = bytearray()
            added = []
            for base, (dtag, datum, donor) in sorted(want.items()):
                if dtag not in names or any(n.rsplit(BS, 1)[-1] == base for n in names):
                    continue
                e = elems[names.index(dtag)]
                row = bytearray(m.data[e:e + es])
                struct.pack_into('<I', row, at, datum)
                extra += row
                added.append('%s <- %s' % (base, donor))
            if not extra:
                continue
            blk = b + off
            n = max(0, m.i32(blk))
            got = hp._h3_reserve(m, [n * es + len(extra)])
            if not got:
                rows.append({'tag': 'char ' + p, 'field': 'firing data', 'ok': False,
                             'reason': 'no partition slack to grow the block'})
                continue
            dst, old = got[0], hp._block_base(m, blk)
            m.data[dst:dst + n * es] = m.data[old:old + n * es]
            m.data[dst + n * es:dst + n * es + len(extra)] = extra
            struct.pack_into('<i', m.data, blk, n + len(extra) // es)
            struct.pack_into('<I', m.data, blk + 4, m.off2data(dst))
            rows.append({'tag': 'char ' + p, 'field': 'firing data (+0x%X)' % off, 'ok': True,
                         'new': ', '.join(added)})
    return rows


def _kind(m, hp, info):
    """'pistol' (Plasma Pistol's class), 'rifle' (Assault Rifle's) or 'heavy' (anything else:
    missile, support, turret classes)."""
    def cls(base):
        t = next((p for p, _b in m.find_tags('weap', '*') if p.lower().rsplit(BS, 1)[-1] == base), None)
        wi = weapon_info(m, t) if t else None
        return wi['class'] if wi else None
    c = info['class']
    if c == cls('plasma_pistol'):
        return 'pistol'
    if c == cls('assault_rifle'):
        return 'rifle'
    return 'heavy'


def _eff_class(graphs, g, info):
    ov = g['wl'].get(info['name'])
    return ov if ov is not None and ov != graphs.any and info['class'] != DUAL_CLASS else info['class']


def _pose_plan(m, graphs, gs, info, donors):
    """THE POSE (boot 4, 2026-11-04: turrets and the Brute Shot held through the Rocket Launcher's
    class pointed at the sky -- a weapon's grip is built for its OWN class's pose). A donor of the
    weapon's own native class that every graph holds lends its pose: per graph the weapon is
    re-classed to the donor's class (Weapon List, if it differs) and, where that class has no
    'any' type, gets a TYPE of its own: a copy of the donor's type entry (label = the weapon's
    name; the game's own Grunt Plasma Cannon / Machine Gun Turret entries share their animation
    pointers the same way). Returns (donor info, [(graph, class, [(mode, donor type addr)])]) or
    None."""
    for dname, di in donors:
        if di['class'] != info['class'] or di['name'] == info['name']:
            continue
        if not all(graphs.holds(g, di['class'], di['name']) for g in gs):
            continue
        plan = []
        for g in gs:
            cl = _eff_class(graphs, g, di)
            copies = []
            for mo in (graphs.combat, graphs.any):
                C = g['modes'].get(mo, {}).get(cl)
                if C and graphs.any not in C and di['name'] in C and info['name'] not in C:
                    copies.append((mo, g['where'][(mo, cl, di['name'])]))
            plan.append((g, cl, copies))
        return dname, plan
    return None


def _grow_sorted(m, hp, blk, es, new):
    """Rewrite the block at `blk` with `new` {label: element bytes} merged in, sorted by the
    leading u32 label (the game binary-searches these blocks). Returns False without slack."""
    n = max(0, m.i32(blk))
    old = hp._block_base(m, blk) if n else None
    els = {m.u32(old + i * es): bytes(m.data[old + i * es:old + (i + 1) * es]) for i in range(n)}
    els.update(new)
    data = b''.join(v for _k, v in sorted(els.items()))
    got = hp._h3_reserve(m, [len(data)])
    if not got:
        return False
    m.data[got[0]:got[0] + len(data)] = data
    struct.pack_into('<i', m.data, blk, len(els))
    struct.pack_into('<I', m.data, blk + 4, m.off2data(got[0]))
    return True


# ----------------------------------------------------------------------------- grips
#: (boot 5, 2026-11-05) weapons whose model is NOT built for the borrowed pose: held at their origin
#: they point skyward / roll (Marine Brute Shot, Grunt turrets, Jackal turrets + Brute Shot). They
#: get a GRIP MARKER for the species instead (GRIP_NAME, the name the species' biped looks for).
GRIP_FIX = ('brute_shot', 'missile_pod', 'machinegun_turret', 'plasma_cannon', 'flamethrower',
            'plasma_turret')                         # Reach's plasma cannon
#: the species whose own turret pose holds GRIP_FIX weapons fine (boot 5: Marine turrets in the
#: Marine flamethrower pose): they keep the pose step
POSE_OK = ('Marine',)
#: NATIVE pairs taught anyway (boot 7: the Grunt's own turret pose holds the Machine Gun Turret
#: pointing up): rocket pose + body-frame grip like the taught turrets
REPOSE_BY_GAME = {'Halo 3': {'Grunt': ('machinegun_turret', 'plasma_cannon')},
                  'Halo 3: ODST': {'Grunt': ('machinegun_turret', 'plasma_cannon')}}
REPOSE = REPOSE_BY_GAME['Halo 3']                   # bind() points it at the game's
GRIP_NAME = {'Grunt': 'right_hand_grunt', 'Jackal': 'left_hand_jackal', 'Marine': 'right_hand_marine',
             'Bugger': 'right_hand_jackal'}
#: the biped(s) per species whose Preferred Gun Node (+0x1A4) must name GRIP_NAME
GRIP_BIPEDS = {'Grunt': ('grunt',), 'Jackal': ('jackal',), 'Marine': ('marine', 'marine_female'),
               'Bugger': ('bugger',)}
BIPD_PREFERRED = 0x1A4
#: the off-hand (IK) markers compared, most specific first (then any 'left_hand*')
OFFHAND = {'Marine': ('left_hand_marine', 'left_hand'), 'Grunt': ('left_hand',),
           'Jackal': ('left_hand',), 'Bugger': ('left_hand',)}
MODE_NODES, MODE_NODE_ES, MODE_GROUPS, MODE_GROUP_ES, MARKER_ES = 0x30, 0x60, 0x3C, 0x10, 0x24


def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def _qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def _qrot(q, v):
    x, y, z, _w = _qmul(_qmul(q, (v[0], v[1], v[2], 0.0)), _qconj(q))
    return (x, y, z)


def _compose(a, b):
    """a after b as rigid transforms (t, q): point_parent = a(b(point))."""
    (ta, qa), (tb, qb) = a, b
    r = _qrot(qa, tb)
    return ((ta[0] + r[0], ta[1] + r[1], ta[2] + r[2]), _qmul(qa, qb))


def _inverse(a):
    t, q = a
    qi = _qconj(q)
    r = _qrot(qi, t)
    return ((-r[0], -r[1], -r[2]), qi)


def _norm(q):
    n = sum(x * x for x in q) ** 0.5 or 1.0
    return tuple(x / n for x in q)


def _render_model(m, hp, weapon):
    w = dict(m.find_tags('weap', weapon)).get(weapon)
    if w is None:
        return None
    hl = hp._tag_name_by_id(m, m.u32(w + WEAP_MODEL + 0xC))
    h = dict(m.find_tags('hlmt', hl)).get(hl) if hl else None
    mn = hp._tag_name_by_id(m, m.u32(h + 0xC)) if h is not None else None
    return dict(m.find_tags('mode', mn)).get(mn) if mn else None


def _marker(m, hp, mode, names, fallback=True):
    """(transform in node-0 space, marker element) of the first marker group in `names` (then
    any 'left_hand*'), or None."""
    groups = {_name(m, hp, m.u32(g)): g
              for g in m.follow_all(mode, [MODE_GROUPS], [MODE_GROUP_ES], 'all')}
    pick = next((groups[n] for n in names if n in groups), None)
    if pick is None and fallback:
        pick = next((g for n, g in sorted(groups.items()) if n.startswith('left_hand')), None)
    mk = m.follow_all(pick, [4], [MARKER_ES], 'all') if pick is not None else []
    if not mk:
        return None
    e = mk[0]
    tr = (struct.unpack_from('<3f', m.data, e + 4), _norm(struct.unpack_from('<4f', m.data, e + 0x10)))
    nodes = m.follow_all(mode, [MODE_NODES], [MODE_NODE_ES], 'all')
    ni, hops = m.data[e + 2], 0
    while 0 < ni < len(nodes) and hops < 32:          # up the parent chain to node 0
        nd = nodes[ni]
        tr = _compose((struct.unpack_from('<3f', m.data, nd + 0xC),
                       _norm(struct.unpack_from('<4f', m.data, nd + 0x18))), tr)
        ni = struct.unpack_from('<h', m.data, nd + 4)[0]
        hops += 1
    return tr, e


#: (boot 6, 2026-11-05) how a species' grip is computed: 'offhand' = the weapon's off-hand marker
#: where the donor's sits (Marines: confirmed); the rest 'body' -- Grunts came out diagonal and
#: Jackals sideways with 'offhand' (Jackals hold the gun in the other hand, the Rocket Launcher
#: has no plain left_hand marker for Grunts)
#: (ODST boot 1, 2026-11-07) per GAME: ODST Marines floated the Brute Shot in front of their hands
#: with 'offhand' (ODST's Rocket Launcher puts its Marine off-hand elsewhere) -> 'body' there
GRIP_STYLE = {'Halo 3': {'Marine': 'offhand'}}
#: the root-rotation difference (degrees) above which a weapon taught through a SAME-CLASS pose
#: still gets a grip (ODST boot 1: the Plasma Cannon pointed up in the Marine flamethrower pose,
#: its root is rotated ~95 deg where the flamethrower's is ~50; the Machine Gun Turret matches it)
POSE_GRIP_DEG = 10.0


def _body_frame(m, hp, mode):
    """The frame a rifle-like hold needs, in node-0 space: these weapons' ROOT nodes are rotated
    against the object origin (turrets pitched ~50 deg, Plasma Cannon ~95, Brute Shot / Missile Pod
    on two axes) while every rifle's root is unrotated. The hand takes node 0's frame, or the
    'body' child's when there is one (the Brute Shot / Missile Pod body is rolled 90 deg: Bungie's
    right_hand_brute markers are exactly that rotation)."""
    nodes = m.follow_all(mode, [MODE_NODES], [MODE_NODE_ES], 'all')
    qb = (0.0, 0.0, 0.0, 1.0)
    for nd in nodes[1:]:
        if struct.unpack_from('<h', m.data, nd + 4)[0] == 0 and _name(m, hp, m.u32(nd)) == 'body':
            qb = _norm(struct.unpack_from('<4f', m.data, nd + 0x18))
            break
    # (boot 7) then turned toward the MUZZLE with the smallest rotation: the Plasma Cannon's
    # primary_trigger sits at -X, so its body frame alone held it backwards
    trig = _marker(m, hp, mode, ('primary_trigger',), fallback=False)
    if trig is not None:
        d = _qrot(_qconj(qb), _qrot(trig[0][1], (1.0, 0.0, 0.0)))
        qb = _qmul(qb, _turn_x_to(d))
    return ((0.0, 0.0, 0.0), _norm(qb))


def _turn_x_to(d):
    """The smallest rotation taking +X to the direction d (180 deg about Z when d is -X)."""
    n = sum(x * x for x in d) ** 0.5 or 1.0
    d = tuple(x / n for x in d)
    if d[0] > 0.9999:
        return (0.0, 0.0, 0.0, 1.0)
    if d[0] < -0.9999:
        return (0.0, 0.0, 1.0, 0.0)
    ax = (0.0, -d[2], d[1])                       # (1,0,0) x d
    return _norm((ax[0], ax[1], ax[2], 1.0 + d[0]))


def _root(m, mode):
    """Node 0's default transform (t, q): where the model's root sits against the object origin."""
    nodes = m.follow_all(mode, [MODE_NODES], [MODE_NODE_ES], 'all')
    if not nodes:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    return (struct.unpack_from('<3f', m.data, nodes[0] + 0xC),
            _norm(struct.unpack_from('<4f', m.data, nodes[0] + 0x18)))


def _angle(qa, qb):
    import math
    d = abs(sum(a * b for a, b in zip(_norm(qa), _norm(qb))))
    return math.degrees(2 * math.acos(min(1.0, d)))


def _turret_donor(m, md):
    """True when the donor's root is rotated against its origin (a turret: the Marine flamethrower
    pose), False for every rifle and the Rocket Launcher (unrotated roots)."""
    return _angle(_root(m, md)[1], (0.0, 0.0, 0.0, 1.0)) >= 1.0


#: (Reach boot 1, 2026-11-09) species whose weapons need their own hand markers: a Jackal
#: handed a DMR / Rocket Launcher twisted its off-hand behind its body -- its native rifles
#: (Focus Rifle, Needle Rifle) carry right_hand_jackal + left_hand_jackal, the rest neither
MARKER_SPECIES = {'Halo Reach': ('Jackal', 'Skirmisher')}


def species_markers(m, hp, enemy, weapon):
    """Copy the species' own hand markers (its biped's Preferred Gun Node and its left twin) onto
    `weapon` where it lacks them: on a reference weapon carrying both the generic marker
    (right_hand / left_hand) and the species' one, the offset between the two (in node-0 space)
    is measured and put on the weapon's own generic marker. Returns result rows."""
    rows = []
    folders = GRIP_BIPEDS.get(enemy) or GRIP_BIPEDS.get('Jackal')
    pref = None
    for p, b in m.find_tags('bipd', '*'):
        if p.lower().rsplit(BS, 1)[-1] in folders:
            pref = _name(m, hp, m.u32(b + BIPD_PREFERRED)) or pref
    if not pref or not pref.startswith('right_hand_'):
        return rows
    mt = _render_model(m, hp, weapon)
    info = weapon_info(m, weapon)
    if mt is None or not two_handed(m, hp, info):
        return rows                         # pistols: the stock one-handed holds are fine
    refs = getattr(m, '_species_marker_refs', None)
    if refs is None:
        # Bungie's own pairs, read BEFORE this pass adds any (an added pair is no reference)
        refs = []
        for rp_, _rb in m.find_tags('weap', '*'):
            rm = _render_model(m, hp, rp_)
            if rm is not None:
                names = {_name(m, hp, m.u32(g)) for g in m.follow_all(rm, [MODE_GROUPS], [MODE_GROUP_ES], 'all')}
                refs.append((rp_, rm, names, (weapon_info(m, rp_) or {}).get('class')))
        try:
            m._species_marker_refs = refs
        except AttributeError:
            pass
    have = {_name(m, hp, m.u32(g)) for g in m.follow_all(mt, [MODE_GROUPS], [MODE_GROUP_ES], 'all')}
    for name, generic in ((pref, 'right_hand'), (pref.replace('right_hand', 'left_hand', 1), 'left_hand')):
        if name in have or generic not in have:
            continue
        sid = find_sid(m, hp, name)
        gen_t = _marker(m, hp, mt, (generic,), fallback=False)
        ref = None
        cands = [r for r in refs if r[1] != mt and name in r[2] and generic in r[2]]
        cands.sort(key=lambda r: r[3] != (info or {}).get('class'))      # same class first
        for rp_, rm, _n, _c in cands:
            a = _marker(m, hp, rm, (generic,), fallback=False)
            b2 = _marker(m, hp, rm, (name,), fallback=False)
            if a is not None and b2 is not None:
                ref = (a[0], b2[0], rp_)
                break
        if sid is None or gen_t is None or ref is None:
            continue
        t, q = _compose(gen_t[0], _compose(_inverse(ref[0]), ref[1]))
        mk = bytearray(m.data[gen_t[1]:gen_t[1] + MARKER_ES])
        mk[2] = 0
        struct.pack_into('<3f', mk, 4, *t)
        struct.pack_into('<4f', mk, 0x10, *_norm(q))
        got = hp._h3_reserve(m, [MARKER_ES])
        if not got:
            continue
        m.data[got[0]:got[0] + MARKER_ES] = mk
        grp = bytearray(MODE_GROUP_ES)
        struct.pack_into('<IiI', grp, 0, sid, 1, m.off2data(got[0]))
        if _grow_sorted(m, hp, mt + MODE_GROUPS, MODE_GROUP_ES, {sid: bytes(grp)}):
            have.add(name)
            rows.append({'tag': 'mode ' + enemy, 'field': '%s: %s' % (weapon.rsplit(BS, 1)[-1], name),
                         'ok': True, 'new': 'from its %s, offset as on the %s'
                         % (generic, ref[2].rsplit(BS, 1)[-1])})
    return rows


def find_sid(m, hp, text):
    for i in range(1, 0x10000):
        if _name(m, hp, i) == text:
            return i
    return None


#: (Reach 2026-11-09) grip names to try where the species' biped names none, per game; a name
#: another species' biped already looks for is skipped (Reach Jackals use right_hand_jackal)
GRIP_NAMES_BY_GAME = {'Halo Reach': {'Bugger': ('right_hand_bugger', 'right_hand_grunt',
                                                'right_hand_engineer', 'right_hand_skirmisher')}}


def grip_name(m, hp, enemy):
    """The grip marker name for `enemy`: its biped's own Preferred Gun Node when it names one
    (Reach Grunts: right_hand, a marker Bungie put on weapons), else GRIP_NAME / the per-game
    candidates, never a name another species' biped looks for."""
    taken, own = set(), None
    for p, b in m.find_tags('bipd', '*'):
        v = m.u32(b + BIPD_PREFERRED)
        n = _name(m, hp, v) if v else ''
        if p.lower().rsplit(BS, 1)[-1] in GRIP_BIPEDS.get(enemy, ()):
            own = own or n
        elif n:
            taken.add(n)
    if own:
        return own
    for n in GRIP_NAMES_BY_GAME.get(GAME, {}).get(enemy, ()) + (GRIP_NAME.get(enemy),):
        if n and n not in taken and find_sid(m, hp, n) is not None:
            return n
    return None


def grip(m, hp, enemy, weapon, donor, style=None):
    """The grip marker GRIP_NAME[enemy] on `weapon`'s render model, placed so the weapon's
    off-hand marker lands where the `donor`'s does in the hand (the donor is held at its origin):
    M = L_weapon * inverse(L_donor). The species' biped is pointed at that marker name (only
    weapons carrying it are affected). Returns a result row."""
    name = grip_name(m, hp, enemy)
    row = {'tag': 'mode ' + enemy, 'field': 'grip: ' + weapon.rsplit(BS, 1)[-1], 'ok': False}
    sid = find_sid(m, hp, name) if name else None
    mt, md = _render_model(m, hp, weapon), _render_model(m, hp, donor)
    if sid is None or mt is None or md is None:
        return dict(row, reason='no %s id / render model in this map' % name)
    if any(m.u32(g) == sid for g in m.follow_all(mt, [MODE_GROUPS], [MODE_GROUP_ES], 'all')):
        # Bungie's own grip for this species (Reach): keep it
        return dict(row, ok=True, new='keeps its own %s marker' % name)
    lt, ld = _marker(m, hp, mt, OFFHAND[enemy]), _marker(m, hp, md, OFFHAND[enemy])
    if lt is None or ld is None:
        return dict(row, reason='no off-hand marker on the weapon or the donor')
    style = style or GRIP_STYLE.get(GAME, {}).get(enemy, 'body')
    if style == 'offhand':
        t, q = _compose(lt[0], _inverse(ld[0]))
        how = 'aligned to the %s off-hand' % donor.rsplit(BS, 1)[-1]
    else:
        # the weapon's body frame where the donor's sits in the hand: M = B_w * inverse(F_donor)
        fd = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        if _turret_donor(m, md):
            # a turret-pose donor (the Marine flamethrower pose, ODST boots 2-4): the body frame
            # UNPITCHED -- the flamethrower's ~50 deg root pitch aimed the Plasma Cannon at the
            # sky, inverted at the ground; the hand of that pose is already level for a turret --
            # at the weapon's OWN root position (the flamethrower's floated it ~30 cm forward)
            fd = (_root(m, mt)[0], (0.0, 0.0, 0.0, 1.0))
        t, q = _compose(_body_frame(m, hp, mt), _inverse(fd))
        how = 'on the body frame, as the %s sits' % donor.rsplit(BS, 1)[-1]
    mk = bytearray(m.data[lt[1]:lt[1] + MARKER_ES])
    mk[2] = 0
    struct.pack_into('<3f', mk, 4, *t)
    struct.pack_into('<4f', mk, 0x10, *_norm(q))
    struct.pack_into('<f', mk, 0x20, 1.0)
    got = hp._h3_reserve(m, [MARKER_ES])
    if not got:
        return dict(row, reason='no partition slack')
    m.data[got[0]:got[0] + MARKER_ES] = mk
    grp = bytearray(MODE_GROUP_ES)
    struct.pack_into('<IiI', grp, 0, sid, 1, m.off2data(got[0]))
    if not _grow_sorted(m, hp, mt + MODE_GROUPS, MODE_GROUP_ES, {sid: bytes(grp)}):
        return dict(row, reason='no partition slack')
    for p, b in m.find_tags('bipd', '*'):
        if p.lower().rsplit(BS, 1)[-1] in GRIP_BIPEDS.get(enemy, ()):
            struct.pack_into('<I', m.data, b + BIPD_PREFERRED, sid)
    return dict(row, ok=True, new='%s %s' % (name, how))


def teach(m, hp, graphs, wanted):
    """TEACHING (user 2026-11-03): `wanted` = {enemy: [weapon path]} the gate refused. Each weapon
    gets a Weapon List row (its NAME -> a donor weapon's class, TEACH_DONORS by kind) in every
    graph of the species, where that class has an 'any' type with an 'idle' action -- the same
    lookup the gate replays, so the unit holds it with the donor's animations. NOT_TAUGHT are
    never taught. Rows go in once per graph (block relocated into partition slack). Returns
    (taught {enemy: set(weapon)}, rows)."""
    adds, taught, rows, types, grips = {}, {}, [], {}, []
    tags = {p.lower(): p for p, _b in m.find_tags('weap', '*')}
    by_base = {p.rsplit(BS, 1)[-1]: p for p in tags}
    for enemy, ws in wanted.items():
        gs = [g for f in graph_folders(enemy) for _p, g in graphs.by_folder.get(f, ())]
        if not gs:
            continue
        mine = {t.lower() for t in ws}
        donors = [(p.rsplit(BS, 1)[-1], weapon_info(m, tags[p])) for p in sorted(tags)
                  if p not in mine and p.rsplit(BS, 1)[-1] not in NOT_TAUGHT
                  and p.startswith('objects' + BS + 'weapons' + BS)
                  # a mounted turret's weapon is held in a SEATED gunner pose, no carry pose
                  and not any(x in p.rsplit(BS, 1)[-1] for x in ('integrated', 'undeployed'))]
        donors = [(d, i) for d, i in donors if i]
        for w in ws:
            base = w.lower().rsplit(BS, 1)[-1]
            info = weapon_info(m, tags.get(w.lower(), w))
            if base in NOT_TAUGHT or not info:
                continue
            pose = None if base in GRIP_FIX and enemy not in POSE_OK else \
                _pose_plan(m, graphs, gs, info, donors)
            if pose:
                dname, plan = pose
                for g, cl, copies in plan:
                    if cl != info['class']:
                        g['wl'][info['name']] = cl
                        adds.setdefault(id(g), (g, {}))[1][info['name']] = cl
                    for mo, src in copies:
                        el = bytearray(m.data[src:src + JM_TYPE_ES])
                        struct.pack_into('<I', el, 0, info['name'])
                        types.setdefault(g['where'][(mo, cl)], {})[info['name']] = bytes(el)
                        g['modes'][mo][cl][info['name']] = set(g['modes'][mo][cl][m.u32(src)])
                if all(graphs.holds(g, info['class'], info['name']) for g, _c, _x in plan):
                    taught.setdefault(enemy, set()).add(w)
                    rows.append({'tag': 'jmad ' + enemy, 'field': 'taught: ' + base, 'ok': True,
                                 'new': 'in the %s pose (%d graphs)' % (dname, len(gs))})
                    dp = by_base.get(dname)
                    mt = _render_model(m, hp, tags.get(w.lower(), w))
                    md = _render_model(m, hp, tags[dp]) if dp else None
                    if base in GRIP_FIX and mt is not None and md is not None and _angle(
                            _root(m, mt)[1], _root(m, md)[1]) > POSE_GRIP_DEG:
                        grips.append((enemy, tags.get(w.lower(), w), dp, 'body'))
                    continue
            for d in TEACH_DONORS[_kind(m, hp, info)]:
                dp = by_base.get(d)
                if dp == w.lower() or dp in {t.lower() for t in taught.get(enemy, ())}:
                    continue                 # a donor taught here itself: name its own donor
                di = weapon_info(m, tags[dp]) if dp else None
                if not di or not all(graphs.holds(g, di['class'], di['name']) for g in gs):
                    continue
                plan = []
                for g in gs:
                    ov = g['wl'].get(di['name'])
                    cl = ov if ov is not None and ov != graphs.any and di['class'] != DUAL_CLASS else di['class']
                    trial = dict(g, wl=dict(g['wl']))
                    trial['wl'][info['name']] = cl
                    if not graphs.holds(trial, info['class'], info['name']):
                        break
                    plan.append((g, cl))
                else:
                    for g, cl in plan:
                        g['wl'][info['name']] = cl
                        adds.setdefault(id(g), (g, {}))[1][info['name']] = cl
                    taught.setdefault(enemy, set()).add(w)
                    rows.append({'tag': 'jmad ' + enemy, 'field': 'taught: ' + base, 'ok': True,
                                 'new': 'held as the %s (%d graphs)' % (d, len(gs))})
                    if base in GRIP_FIX:
                        grips.append((enemy, tags.get(w.lower(), w), dp, None))
                    break
    # SORTED (boot 3, 2026-11-04): every stock Weapon List is sorted by the weapon-name string
    # id and the game binary-searches it -- rows appended at the end were found only where the
    # search happened to land on them (Brute Shot yes, Rocket Launcher / turrets no). The whole
    # list is rewritten sorted.
    for enemy, w, dp, style in grips:
        rows.append(grip(m, hp, enemy, w, tags[dp], style))
    for cls_el, new in types.items():
        if not _grow_sorted(m, hp, cls_el + JM_TYPE_SUB, JM_TYPE_ES, new):
            rows.append({'tag': 'jmad', 'field': 'animation types', 'ok': False,
                         'reason': 'no partition slack to grow the block'})
    for g, new in adds.values():
        blk = g['base'] + JM_WL
        n = max(0, m.i32(blk))
        old = hp._block_base(m, blk) if n else None
        allrows = {m.u32(old + i * JM_WL_ES): m.u32(old + i * JM_WL_ES + 4) for i in range(n)}
        allrows.update(new)
        data = b''.join(struct.pack('<II', k, c) for k, c in sorted(allrows.items()))
        got = hp._h3_reserve(m, [len(data)])
        if not got:
            rows.append({'tag': 'jmad', 'field': 'Weapon List', 'ok': False,
                         'reason': 'no partition slack to grow the block'})
            continue
        dst = got[0]
        m.data[dst:dst + len(data)] = data
        struct.pack_into('<i', m.data, blk, len(allrows))
        struct.pack_into('<I', m.data, blk + 4, m.off2data(dst))
    return taught, rows


def find_variant(m, hp, text):
    """The raw string id of `text` as used by a location's Actor Variant Name in THIS map (Halo 3
    string ids are read through resolve_stringid only), or None."""
    base = hp._scnr_base(m)
    for sq in m.follow_all(base, [SQUADS], [SQ_ES], 'all'):
        if GAME in CELL_GAMES:
            places = [(sp, SP_VARIANT) for sp in m.follow_all(sq, [SP], [SP_ES], 'all')]
        else:
            places = [(loc, LOC_VARIANT) for ft in m.follow_all(sq, [FT], [FT_ES], 'all')
                      for loc in m.follow_all(ft, [LOCS], [LOC_ES], 'all')]
        for loc, at in places:
            v = m.u32(loc + at)
            if v and v != 0xFFFFFFFF and _name(m, hp, v) == text:
                return v
    # no location uses it yet (010): Halo 3 string ids are plain indices (namespace 0), so
    # the first index that resolves to the text is its id
    for i in range(1, 0x10000):
        if _name(m, hp, i) == text:
            return i
    return None


# ----------------------------------------------------------------------------- arming
def arm(m, hp, cards, salt=None):
    base = hp._scnr_base(m)
    wnames = [hp._tag_name_by_id(m, m.u32(e + WPAL_ID))
              for e in m.follow_all(base, [WPAL], [WPAL_ES], 'all')]
    widx = {(n or '').lower(): i for i, n in enumerate(wnames)}
    cpal = m.follow_all(base, [CPAL], [CPAL_ES], 'all')
    ids = [m.u32(e + CPAL_ID) for e in cpal]
    cnames = [hp._tag_name_by_id(m, i) if i != 0xFFFFFFFF else None for i in ids]
    friends, char_team = hp._player_friends(m, GAME, cnames, ids)
    friends = set(friends)
    salt = salt or hp.level_salt(m)
    graphs = Graphs(m, hp)
    rows, missing, refused, excluded = [], set(), {}, set()
    info = {}
    usable = {}                                  # enemy -> {weapon: share} it can hold
    for enemy, ws in (cards or {}).items():
        ok = {}
        for w, s in ws.items():
            lw = (w or '').lower()
            if not lw or s <= 0:
                continue
            if lw.rsplit(BS, 1)[-1] in EXCLUDED:
                excluded.add(w)
                continue
            if lw not in widx:
                missing.add(w)
                continue
            if lw not in info:
                info[lw] = weapon_info(m, wnames[widx[lw]])
            wi = info[lw]
            if wi is None or not graphs.allows(enemy, wi['class'], wi['name']):
                refused.setdefault(enemy, set()).add(w)
            ok[lw] = s
        if ok:
            usable[enemy] = ok
    # TEACH what the gate refused (not the melee weapons), then drop what is still refused
    forced = {e: set(wnames[widx[w]] for w in ws if w.rsplit(BS, 1)[-1] in REPOSE.get(e, ()))
              for e, ws in usable.items()}
    taught, trows = teach(m, hp, graphs, {e: sorted(refused.get(e, set()) | forced.get(e, set()))
                                          for e in set(refused) | set(forced)
                                          if refused.get(e) or forced.get(e)})
    rows += trows
    for enemy in list(refused):
        refused[enemy] -= taught.get(enemy, set())
        for w in refused[enemy]:
            usable.get(enemy, {}).pop(w.lower(), None)
        if not refused[enemy]:
            del refused[enemy]
        if enemy in usable and not usable[enemy]:
            del usable[enemy]
    handed = sorted(set(wnames[widx[w]] for ok in usable.values() for w in ok))
    rows += borrow_firing(m, hp, handed)
    rows += species_firing(m, hp, [(e, wnames[widx[w]]) for e, ws in usable.items() for w in ws])
    for enemy in MARKER_SPECIES.get(GAME, ()):
        for w in sorted(usable.get(enemy, {})):
            rows += species_markers(m, hp, enemy, wnames[widx[w]])
    nofire = set(w for w in handed if has_firing(m, hp, w) is False)
    sid = find_variant(m, hp, 'shieldless')
    stats = {'shieldless': 0, 'reshielded': 0, 'no_variant': 0, 'kept_original': 0,
             'ft_jackals': 0}
    done = {}

    def jackal_shield(loc, w, at=LOC_VARIANT):
        if two_handed(m, hp, info.get(w)):
            if sid is None and GAME == 'Halo Reach':
                # Reach has no 'shieldless' variant: the spawn point names none, so the cell's
                # (cloned, shieldless) character's own variant applies
                if m.u32(loc + at):
                    struct.pack_into('<I', m.data, loc + at, 0)
                    stats['shieldless'] += 1
            elif sid is None:
                stats['no_variant'] += 1
            elif m.u32(loc + at) != sid:
                struct.pack_into('<I', m.data, loc + at, sid)
                stats['shieldless'] += 1
        elif sid is not None and m.u32(loc + at) == sid:
            struct.pack_into('<I', m.data, loc + at, 0)
            stats['reshielded'] += 1

    def type_of(c):
        return enemy_of(cnames[c]) if c is not None and 0 <= c < len(cnames) else None

    def draw(enemy, team, addr):
        if enemy not in usable:
            return None
        if enemy in ALLY_TYPES and team not in friends:
            return None
        return _pick(usable[enemy], _draw(salt, addr))

    def count(enemy, w, n=1):
        by = done.setdefault(enemy, {})
        by[w] = by.get(w, 0) + n

    if GAME in CELL_GAMES:
        _arm_cells(m, hp, base, widx, info, graphs, type_of, draw, count, jackal_shield, char_team,
                   stats)
    for sq in m.follow_all(base, [SQUADS], [SQ_ES], 'all') if GAME == 'Halo 3' else ():
        squad_team = _i16(m, sq + SQ_TEAM)
        for ft in m.follow_all(sq, [FT], [FT_ES], 'all'):
            fc = _i16(m, ft + FT_CHAR)
            fenemy = type_of(fc)
            fteam = squad_team if squad_team > 0 else (char_team[fc] if 0 <= fc < len(char_team) else None)
            orig = _i16(m, ft + FT_WEAP)
            fw = draw(fenemy, fteam, ft + FT_WEAP)
            if fw is not None:
                struct.pack_into('<h', m.data, ft + FT_WEAP, widx[fw])
                struct.pack_into('<h', m.data, ft + FT_WEAP + 2, -1)
                count(fenemy, fw)
                if fenemy == 'Jackal':
                    stats['ft_jackals'] += 1
            for loc in m.follow_all(ft, [LOCS], [LOC_ES], 'all'):
                lc = _i16(m, loc + LOC_CHAR)
                c = lc if lc >= 0 else fc
                enemy = type_of(c)
                team = squad_team if squad_team > 0 else (char_team[c] if 0 <= c < len(char_team) else None)
                own = _i16(m, loc + LOC_WEAP)
                if own < 0:
                    # inherits the fire-team's weapon: fine for the fire-team's own species;
                    # another species that cannot hold the new one keeps the ORIGINAL weapon
                    if fw is None:
                        continue
                    wi = info.get(fw)
                    if enemy == fenemy:
                        if enemy == 'Jackal':
                            jackal_shield(loc, fw)
                        continue
                    if enemy and wi and graphs.allows(enemy, wi['class'], wi['name']):
                        count(enemy, fw)
                        if enemy == 'Jackal':
                            jackal_shield(loc, fw)
                        continue
                    if orig >= 0:
                        struct.pack_into('<h', m.data, loc + LOC_WEAP, orig)
                        stats['kept_original'] += 1
                    continue
                w = draw(enemy, team, loc + LOC_WEAP)
                if w is None:
                    continue
                struct.pack_into('<h', m.data, loc + LOC_WEAP, widx[w])
                struct.pack_into('<h', m.data, loc + LOC_WEAP + 2, -1)
                count(enemy, w)
                if enemy == 'Jackal':
                    jackal_shield(loc, w)
    tag = 'scnr enemy weapons' + BS
    for enemy, ws in sorted(done.items()):
        for w, n in sorted(ws.items()):
            rows.append({'tag': tag + enemy, 'field': 'Armed: ' + w.split(BS)[-1], 'ok': True,
                         'new': '%d fire-teams / locations' % n})
    for enemy, ws in sorted(refused.items()):
        for w in sorted(ws):
            rows.append({'tag': tag + enemy, 'field': 'Armed: ' + w.split(BS)[-1], 'ok': True,
                         'skip': True, 'reason': ('melee weapons are not taught'
                                                  if w.lower().rsplit(BS, 1)[-1] in NOT_TAUGHT
                                                  else 'no donor class fits its graphs')
                         + ' (it would spawn unarmed); not handed out'})
    for w in sorted(nofire):
        rows.append({'tag': tag.rstrip(BS), 'field': 'Armed: ' + w.split(BS)[-1], 'ok': True,
                     'reason': 'handed out, but ai\\generic has no firing data for it: the AI '
                     'may hold it without firing (first boot decides)'})
    for w in sorted(excluded):
        rows.append({'tag': tag.rstrip(BS), 'field': 'Armed: ' + w.split(BS)[-1], 'ok': True,
                     'skip': True, 'reason': 'kept out of Halo 3 Armed cards until its weapon port'})
    for w in sorted(missing):
        rows.append({'tag': tag.rstrip(BS), 'field': 'Armed: ' + w.split(BS)[-1], 'ok': True,
                     'skip': True, 'reason': "not in this level's weapon palette"})
    if stats.get('cells'):
        rows.append({'tag': tag.rstrip(BS), 'field': 'cells', 'ok': True,
                     'new': '%d cells armed: %d shared weapon arrays copied, %d empty ones given '
                     'an element; %d two-handed Jackal cells on shieldless clones'
                     % (stats['cells'], stats['unshared'], stats['filled'], stats.get('cloned', 0))})
        rows.extend(stats.get('clone_rows') or [])
    if stats['shieldless'] or stats['reshielded'] or stats['no_variant'] or stats['ft_jackals']:
        rows.append({'tag': tag + 'Jackal', 'field': 'Jackal shields', 'ok': not stats['no_variant'],
                     'new': '%d locations shieldless (two-handed), %d given the shield back; %d '
                     'fire-teams / cells armed whose extras keep the shield%s' % (
                         stats['shieldless'], stats['reshielded'], stats['ft_jackals'],
                         '; %d KEPT the shield: no shieldless variant id in this map'
                         % stats['no_variant'] if stats['no_variant'] else '')})
    if stats['kept_original']:
        rows.append({'tag': tag.rstrip(BS), 'field': 'mixed fire-teams', 'ok': True,
                     'new': '%d locations of another species keep the fire-team\'s original '
                     'weapon (they cannot hold the new one)' % stats['kept_original']})
    return rows, done


#: ODST char root size; the Variants block (+0x54, 0x14: variant name, model variant index)
CHAR_ROOT, CHAR_VARIANTS, CHAR_VARIANT_ES, CHAR_MAJOR = 0x1F8, 0x54, 0x14, 0x44
#: a spare palette character (no squad uses it, no character names it as parent / major) taken
#: for a shieldless Jackal clone -- these first, then any other spare (Firefight's survival
#: characters and the unused Flood leftovers sit in every ODST campaign palette)
#: names a Reach shieldless Jackal variant may take (must exist as a string id in the map)
SHIELDLESS_NAMES = ('shieldless', 'no_shield', 'unshielded', 'jackal_shieldless', 'jackal_noshield',
                    # Reach has none of those: global object-function strings in every map, named
                    # by no model variant and no graph alias (the name only has to be unique)
                    'shield_depleted', 'recent_shield_damage', 'current_shield_damage')
SPARE_PREFER = ('civilian_police_survival', 'civilain_police_sarge_survival', 'flood_combat_civilian',
                'flood_combat_odst', 'floodcombat_brute_stealth', 'brute_phantom', 'brute_tracker')


class _Shieldless:
    """(ODST boot 2, 2026-11-07) Jackals spawned in formations or past a cell's spawn points kept
    their shields: only spawn points carry a variant. The CHARACTER decides the model variant too
    (jackal 'minor', jackal_major 'major', jackal_sniper 'sniper': the sniper has no shield), so a
    two-handed Jackal cell is pointed at a CLONE of its character -- the root copied over a spare
    palette character, its Variants block one element naming 'shieldless' (the jackal model's own
    variant, looked up by name)."""

    def __init__(self, m, hp, base, cnames, used):
        self.m, self.hp, self.made, self.rows = m, hp, {}, []
        pal = m.follow_all(base, [CPAL], [CPAL_ES], 'all')
        refd = set()
        for p, b in m.find_tags('char', '*'):
            for off in (0x4, 0x44):
                refd.add((hp._tag_name_by_id(m, m.u32(b + off + 0xC)) or '').lower())
        spares = [i for i, n in enumerate(cnames) if n and i not in used and n.lower() not in refd
                  and i < len(pal)]
        leaf = lambda i: cnames[i].lower().rsplit(BS, 1)[-1]
        if GAME == 'Halo Reach':
            # (Reach boot 2 rig) an unused palette character can still be placed by a script
            # (spartan_carter, elite_pilot on m20): Reach takes only another mission's characters
            spares = []
        self.spares = sorted(spares, key=lambda i: (SPARE_PREFER.index(leaf(i))
                                                    if leaf(i) in SPARE_PREFER else 99, i))
        self.cnames = list(cnames)
        self.base = base
        # Reach (m35, 2026-11-09): every palette character is in use -- then a character tag the
        # palette does not hold and nothing names, one made for ANOTHER mission first
        # (generic_m20_flak on m35), joins the palette as a new entry
        # the level's own id ('m20'): find_tags names a Reach scnr '*'; level_salt reads it
        scnr = str(hp.level_salt(m) or '').lower()
        import re
        pal_names = set((n or '').lower() for n in cnames)
        loose = [p for p, _b in m.find_tags('char', '*') if p.lower() not in pal_names
                 and p.lower() not in refd]

        def other_mission(p):
            ids = re.findall(r'm\d\d', p.lower().rsplit(BS, 1)[-1])
            return bool(ids) and not any(i in scnr for i in ids)
        self.loose = [p for p in loose if other_mission(p)] +             [p for p in loose if 'firefight' in p.lower() and not other_mission(p)]
        self.sid = find_sid(m, hp, 'shieldless')
        self.vidx = None
        self.hlmt = None
        self.twins = {}
        for p, b in m.find_tags('hlmt', '*'):
            if p.lower().endswith(BS + 'jackal'):
                self.hlmt = b
                for k, e in enumerate(m.follow_all(b, [HLMT_VARIANTS], [HLMT_VARIANT_ES], 'all')):
                    if _name(m, hp, m.u32(e)) == 'shieldless':
                        self.vidx = k

    def _palette_add(self, path, spare=True):
        """Append `path` to the Character Palette; it becomes a spare (or just an entry)."""
        m, hp = self.m, self.hp
        blk = self.base + CPAL
        n = max(0, m.i32(blk))
        datum = hp._h3_tag_datum(m, 'char', path)
        got = hp._h3_reserve(m, [(n + 1) * CPAL_ES]) if datum is not None and n else None
        if not got:
            return
        old = hp._block_base(m, blk)
        m.data[got[0]:got[0] + n * CPAL_ES] = m.data[old:old + n * CPAL_ES]
        e = got[0] + n * CPAL_ES
        m.data[e:e + CPAL_ES] = m.data[old:old + CPAL_ES]           # the tagRef's group word
        struct.pack_into('<I', m.data, e + CPAL_ID, datum)
        struct.pack_into('<iI', m.data, blk, n + 1, m.off2data(got[0]))
        self.cnames.append(path)
        if spare:
            self.spares.append(n)
        self.rows.append({'tag': 'scnr character palette', 'field': 'spare', 'ok': True,
                          'new': '%s appended (no squad and no character uses it)'
                          % path.rsplit(BS, 1)[-1]})

    def variant(self, src_char):
        """(name id, model variant index) a shieldless clone of `src_char` names. Halo 3 / ODST:
        the jackal model's own 'shieldless'. Reach has none -- the shield is a CHILD OBJECT of the
        jackal_minor / jackal_major variants, and a graph variant alias puts those into the
        pistol-only 'shield' mode -- so the source's variant is copied with no child objects
        under a name no variant and no graph alias uses (appended: characters name model
        variants by index). Falls back to jackal_sniper (no shield, no alias)."""
        m, hp = self.m, self.hp
        if HLMT_VARIANT_OBJECTS is None:
            return (self.sid, self.vidx) if self.sid is not None and self.vidx is not None else None
        v = m.follow_all(src_char, [CHAR_VARIANTS], [CHAR_VARIANT_ES], 'all')
        want = m.u32(v[0]) if v else None
        if want in self.twins:
            return self.twins[want]
        if self.hlmt is None:
            return None
        blk = self.hlmt + HLMT_VARIANTS
        els = m.follow_all(self.hlmt, [HLMT_VARIANTS], [HLMT_VARIANT_ES], 'all')
        names = [m.u32(e) for e in els]
        src = next((e for e in els if m.u32(e) == want), None)
        if src is not None and m.i32(src + HLMT_VARIANT_OBJECTS) <= 0:
            return 'bare'                       # jackal_sniper, the Skirmishers: no shield object
        free = [n for n in SHIELDLESS_NAMES if find_sid(m, hp, n) is not None
                and find_sid(m, hp, n) not in names and find_sid(m, hp, n) not in self.twins.values()]
        got = hp._h3_reserve(m, [(len(els) + 1) * HLMT_VARIANT_ES]) if src is not None and free else None
        if got:
            sid = find_sid(m, hp, free[0])
            old = hp._block_base(m, blk)
            m.data[got[0]:got[0] + len(els) * HLMT_VARIANT_ES] = m.data[old:old + len(els) * HLMT_VARIANT_ES]
            new = got[0] + len(els) * HLMT_VARIANT_ES
            m.data[new:new + HLMT_VARIANT_ES] = m.data[src:src + HLMT_VARIANT_ES]
            struct.pack_into('<I', m.data, new, sid)
            struct.pack_into('<i', m.data, new + HLMT_VARIANT_OBJECTS, 0)          # no shield
            struct.pack_into('<iI', m.data, blk, len(els) + 1, m.off2data(got[0]))
            self.twins[want] = (sid, len(els))
            self.rows.append({'tag': 'hlmt jackal', 'field': 'shieldless variant', 'ok': True,
                              'new': '%s: a copy of %s without its shield object'
                              % (free[0], _name(m, hp, want))})
        else:
            snip = next((k for k, n in enumerate(names) if _name(m, hp, n) == 'jackal_sniper'), None)
            self.twins[want] = (names[snip], snip) if snip is not None else None
        return self.twins[want]

    def of(self, ci):
        """The palette index of the shieldless clone of palette character `ci`, or None."""
        if ci in self.made:
            return self.made[ci]
        if ci in self.made.values():
            return ci                                   # already a clone (a shared array)
        m, hp = self.m, self.hp
        self.made[ci] = None
        src = dict(m.find_tags('char', self.cnames[ci])).get(self.cnames[ci])
        var = self.variant(src) if src is not None else None
        if var == 'bare':
            self.made[ci] = ci                  # its model variant carries no shield already
            return ci
        if var is None:
            return None
        if not self.spares and self.loose:
            self._palette_add(self.loose.pop(0))
        if not self.spares:
            return None
        si = self.spares.pop(0)
        dst = dict(m.find_tags('char', self.cnames[si])).get(self.cnames[si])
        if src is None or dst is None:
            return None
        got = hp._h3_reserve(m, [CHAR_VARIANT_ES])
        if not got:
            return None
        m.data[dst:dst + CHAR_ROOT] = m.data[src:src + CHAR_ROOT]
        el = bytearray(CHAR_VARIANT_ES)
        v = m.follow_all(src, [CHAR_VARIANTS], [CHAR_VARIANT_ES], 'all')
        if v:
            el[:] = m.data[v[0]:v[0] + CHAR_VARIANT_ES]          # keeps its voices
        struct.pack_into('<Ih', el, 0, var[0], var[1])
        m.data[got[0]:got[0] + CHAR_VARIANT_ES] = el
        struct.pack_into('<iI', m.data, dst + CHAR_VARIANTS, 1, m.off2data(got[0]))
        self.made[ci] = si
        # (ODST boot 3) the cell's Major Upgrade turns some units into the character's MAJOR
        # CHARACTER (jackal -> jackal_major, shielded): the clone's major is the major's clone,
        # or none when that cannot be made (the upgrade is lost, the shield stays off)
        major = hp._tag_name_by_id(m, m.u32(dst + CHAR_MAJOR + 0xC))
        if major and major.lower() != self.cnames[ci].lower():
            mi = next((i for i, n in enumerate(self.cnames) if (n or '').lower() == major.lower()), None)
            if mi is None:
                # (Reach m35) the major is not in the palette: it joins it, so it can be cloned
                n0 = len(self.cnames)
                self._palette_add(major, spare=False)
                mi = n0 if len(self.cnames) > n0 else None
            mc = self.of(mi) if mi is not None else None
            datum = hp._h3_tag_datum(m, 'char', self.cnames[mc]) if mc is not None else None
            struct.pack_into('<I', m.data, dst + CHAR_MAJOR + 0xC,
                             datum if datum is not None else 0xFFFFFFFF)
        self.rows.append({'tag': 'char ' + self.cnames[si], 'field': 'shieldless Jackal', 'ok': True,
                          'new': 'a clone of %s naming the shieldless variant (major: %s)'
                          % (self.cnames[ci].rsplit(BS, 1)[-1], (major or 'none').rsplit(BS, 1)[-1])})
        return si


def _arm_cells(m, hp, base, widx, info, graphs, type_of, draw, count, jackal_shield, char_team,
               stats):
    """ODST: arm the cells (and spawn points with their own weapon) of every squad."""

    def shield_names():
        return [hp._tag_name_by_id(m, m.u32(e + CPAL_ID))
                for e in m.follow_all(base, [CPAL], [CPAL_ES], 'all')]
    stats.update(cells=0, unshared=0, filled=0, cloned=0)
    squads = m.follow_all(base, [SQUADS], [SQ_ES], 'all')
    refs = {}
    for sq in squads:
        for off in CELL_BLOCKS:
            for cell in m.follow_all(sq, [off], [CELL_ES], 'all'):
                if m.i32(cell + CELL_WEAPS) > 0:
                    p = m.u32(cell + CELL_WEAPS + 4)
                    refs[p] = refs.get(p, 0) + 1

    def holdable(types, w):
        wi = info.get(w)
        return wi is not None and all(graphs.allows(t, wi['class'], wi['name']) for t in types)

    def write_cell(cell, w):
        blk = cell + CELL_WEAPS
        n, p = m.i32(blk), m.u32(blk + 4)
        if n <= 0:
            got = hp._h3_reserve(m, [CELL_ARR_ES])
            if not got:
                return False
            el = bytearray(CELL_ARR_ES)
            struct.pack_into('<h', el, CELL_CHANCE, 1)
            m.data[got[0]:got[0] + CELL_ARR_ES] = el
            struct.pack_into('<iI', m.data, blk, 1, m.off2data(got[0]))
            n = 1
            stats['filled'] += 1
        elif refs.get(p, 0) > 1:
            got = hp._h3_reserve(m, [n * CELL_ARR_ES])
            if not got:
                return False
            src = hp._block_base(m, blk)
            m.data[got[0]:got[0] + n * CELL_ARR_ES] = m.data[src:src + n * CELL_ARR_ES]
            struct.pack_into('<I', m.data, blk + 4, m.off2data(got[0]))
            refs[p] -= 1
            stats['unshared'] += 1
        el0 = hp._block_base(m, blk)
        for i in range(n):
            struct.pack_into('<h', m.data, el0 + i * CELL_ARR_ES + CELL_IDX, widx[w])
        return True

    jackal_cells, seen, jackal_sps = [], {}, []
    for sq in squads:
        squad_team = _i16(m, sq + SQ_TEAM)
        designer = m.follow_all(sq, [CELL_BLOCKS[0]], [CELL_ES], 'all')
        armed, kinds = {}, {}
        for off in CELL_BLOCKS:
            for cell in m.follow_all(sq, [off], [CELL_ES], 'all'):
                if cell in seen:
                    # squads can share a cell block: one draw per cell, not one per squad
                    kinds[cell], armed_w = seen[cell]
                    if armed_w is not None:
                        armed[cell] = armed_w
                    continue
                seen[cell] = (set(), None)
                chars = [_i16(m, e + CELL_IDX)
                         for e in m.follow_all(cell, [CELL_CHARS], [CELL_ARR_ES], 'all')]
                types = set(type_of(c) for c in chars)
                kinds[cell] = types
                seen[cell] = (types, None)
                if not chars or None in types:
                    continue
                enemy = type_of(chars[0])
                c0 = chars[0]
                team = squad_team if squad_team > 0 else (char_team[c0] if 0 <= c0 < len(char_team) else None)
                w = draw(enemy, team, cell + CELL_WEAPS)
                if w is None or (len(types) > 1 and not holdable(types, w)):
                    continue
                if write_cell(cell, w):
                    armed[cell] = w
                    seen[cell] = (types, w)
                    stats['cells'] += 1
                    count(enemy, w, max(1, _i16(m, cell + CELL_COUNT)))
        placed = {}
        for sp in m.follow_all(sq, [SP], [SP_ES], 'all'):
            ci = _i16(m, sp + SP_CELL)
            cell = designer[ci] if 0 <= ci < len(designer) else None
            if cell is not None:
                placed[cell] = placed.get(cell, 0) + 1
            own_c, own_w = _i16(m, sp + SP_CHAR), _i16(m, sp + SP_WEAP)
            types = {type_of(own_c)} if own_c >= 0 else kinds.get(cell, {None})
            w = armed.get(cell)
            if own_w >= 0 and None not in types:
                enemy = next(iter(types))
                c0 = own_c if own_c >= 0 else -1
                team = squad_team if squad_team > 0 else (char_team[c0] if 0 <= c0 < len(char_team) else None)
                w2 = draw(enemy, team, sp + SP_WEAP)
                if w2 is not None and holdable(types, w2):
                    struct.pack_into('<hh', m.data, sp + SP_WEAP, widx[w2], -1)
                    count(enemy, w2)
                    w = w2
                else:
                    w = None                 # keeps its own weapon
            if w is not None and types == {'Jackal'}:
                jackal_shield(sp, w, SP_VARIANT)
                if own_c >= 0 and two_handed(m, hp, info.get(w)):
                    jackal_sps.append(sp)
        for cell, w in armed.items():
            if kinds.get(cell) == {'Jackal'} and two_handed(m, hp, info.get(w)):
                jackal_cells.append(cell)
    # every two-handed Jackal cell onto a shieldless clone of its character (its own array)
    if jackal_cells or jackal_sps:
        used = set()
        for sq in squads:
            for sp in m.follow_all(sq, [SP], [SP_ES], 'all'):
                used.add(_i16(m, sp + SP_CHAR))
            for off in CELL_BLOCKS:
                for cell in m.follow_all(sq, [off], [CELL_ES], 'all'):
                    for e in m.follow_all(cell, [CELL_CHARS], [CELL_ARR_ES], 'all'):
                        used.add(_i16(m, e + CELL_IDX))
        cnames = shield_names()
        sl = _Shieldless(m, hp, base, cnames, used)
        crefs = {}
        for sq in squads:
            for off in CELL_BLOCKS:
                for cell in m.follow_all(sq, [off], [CELL_ES], 'all'):
                    p = m.u32(cell + CELL_CHARS + 4)
                    crefs[p] = crefs.get(p, 0) + 1
        for cell in dict.fromkeys(jackal_cells):
            blk = cell + CELL_CHARS
            n, p = m.i32(blk), m.u32(blk + 4)
            els = m.follow_all(cell, [CELL_CHARS], [CELL_ARR_ES], 'all')
            new = [sl.of(_i16(m, e + CELL_IDX)) for e in els]
            if not els or None in new:
                stats['ft_jackals'] += 1
                continue
            if crefs.get(p, 0) > 1:
                got = hp._h3_reserve(m, [n * CELL_ARR_ES])
                if not got:
                    stats['ft_jackals'] += 1
                    continue
                src = hp._block_base(m, blk)
                m.data[got[0]:got[0] + n * CELL_ARR_ES] = m.data[src:src + n * CELL_ARR_ES]
                struct.pack_into('<I', m.data, blk + 4, m.off2data(got[0]))
                crefs[p] -= 1
            el0 = hp._block_base(m, blk)
            for i, ci in enumerate(new):
                struct.pack_into('<h', m.data, el0 + i * CELL_ARR_ES + CELL_IDX, ci)
            stats['cloned'] += 1
        for sp in jackal_sps:                   # a spawn point naming its own Jackal character
            ci = sl.of(_i16(m, sp + SP_CHAR))
            if ci is not None:
                struct.pack_into('<h', m.data, sp + SP_CHAR, ci)
        stats['clone_rows'] = sl.rows


def apply(m, hp, spec, registry=None, salt=None, game='Halo 3'):
    bind(game if game in LAYOUTS else 'Halo 3', m, hp)
    rows, _done = arm(m, hp, (spec or {}).get('cards') or {}, salt=salt)
    for r in rows:
        r.setdefault('effect', 'enemy weapons')
    return rows
