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
JM_WL, JM_WL_ES = 0x8C, 0x8
DUAL_CLASS = 0x1F4                 # the 'dual' class id: the Weapon List never re-classes it
PISTOL_NAMES = ('pistol',)
# ai\generic: Weapons Properties / Firing Pattern Properties (ai_firing_profile SOURCES['Halo 3'])
GEN_PROPS, GEN_FPP = 0x174, 0x180
#: (block, element size, weapon datum offset) of a character's two firing blocks
FIRING_BLOCKS = ((GEN_PROPS, 0xE0, 0x10), (GEN_FPP, 0x1C, 0xC))
#: never handed out (tag basenames): the SAW has no ai\generic data and waits for Halo 3's
#: weapon ports (user 2026-11-02)
EXCLUDED = ('saw',)
#: weapons without ai\generic rows borrow a donor's rows (user 2026-11-02), tag basenames
#: never TAUGHT (user 2026-11-03: every enemy wields every weapon, the two melee weapons excepted
#: for now): a species that already holds them keeps getting them
NOT_TAUGHT = ('energy_blade', 'gravity_hammer')
#: donor weapons whose class a refused weapon borrows, by the refused weapon's kind (tag basenames)
TEACH_DONORS = {
    'heavy': ('rocket_launcher', 'flak_cannon', 'spartan_laser', 'brute_shot', 'battle_rifle',
              'assault_rifle', 'covenant_carbine', 'plasma_rifle'),
    'rifle': ('assault_rifle', 'battle_rifle', 'covenant_carbine', 'plasma_rifle', 'smg',
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
}
#: ODST's own story characters (squad mates, Dare, the Superintendent's avatars) are never armed
NEVER_WORDS = {'Halo 3: ODST': ('odst', 'dare', 'vergil', 'buck', 'dutch', 'mickey', 'romeo')}


def bind(game, m=None, hp=None):
    """Point the module at `game`'s layout (Halo 3 or ODST). With the map: the 'dual' class id."""
    global GAME, FIRING_BLOCKS, DUAL_CLASS
    GAME = game
    globals().update(LAYOUTS[game])
    FIRING_BLOCKS = ((GEN_PROPS, 0xE0, 0x10), (GEN_FPP, 0x1C, 0xC))
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
    return next((e for e, fs in ENEMY_CHARS.items() if parts[2] in fs), None)


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
            for c in m.follow_all(md, [JM_SUB], [JM_CLASS_ES], 'all'):
                cl = m.u32(c)
                self._learn(cl)
                tys = cls.setdefault(cl, {})
                where[(ml, cl)] = c
                for t in m.follow_all(c, [JM_SUB], [JM_TYPE_ES], 'all'):
                    tl = m.u32(t)
                    where[(ml, cl, tl)] = t
                    self._learn(tl)
                    acts = set(m.u32(a) for a in m.follow_all(t, [JM_SUB], [JM_ACT_ES], 'all'))
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
        for folder in ENEMY_CHARS.get(enemy, ()):
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
    return any_entry(GEN_PROPS, 0xE0, 0x10) and any_entry(GEN_FPP, 0x1C, 0xC)


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
GRIP_FIX = ('brute_shot', 'missile_pod', 'machinegun_turret', 'plasma_cannon', 'flamethrower')
#: the species whose own turret pose holds GRIP_FIX weapons fine (boot 5: Marine turrets in the
#: Marine flamethrower pose): they keep the pose step
POSE_OK = ('Marine',)
#: NATIVE pairs taught anyway (boot 7: the Grunt's own turret pose holds the Machine Gun Turret
#: pointing up): rocket pose + body-frame grip like the taught turrets
REPOSE = {'Grunt': ('machinegun_turret', 'plasma_cannon')}
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
    hl = hp._tag_name_by_id(m, m.u32(w + 0x34 + 0xC))
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


def _donor_frame(m, hp, md):
    """Where the DONOR's rifle-like frame sits in the hand (the donor is held at its origin): its
    root then its body frame -- identity for every rifle and the Rocket Launcher's rotation, so
    for those the grip is the weapon's body frame alone (the confirmed Grunt / Jackal grips);
    a turret donor (the Marine flamethrower pose) adds its ~50 deg pitch and offset."""
    root = _root(m, md)
    if _angle(root[1], (0.0, 0.0, 0.0, 1.0)) < 1.0:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    return _compose(root, _body_frame(m, hp, md))


def find_sid(m, hp, text):
    for i in range(1, 0x10000):
        if _name(m, hp, i) == text:
            return i
    return None


def grip(m, hp, enemy, weapon, donor, style=None):
    """The grip marker GRIP_NAME[enemy] on `weapon`'s render model, placed so the weapon's
    off-hand marker lands where the `donor`'s does in the hand (the donor is held at its origin):
    M = L_weapon * inverse(L_donor). The species' biped is pointed at that marker name (only
    weapons carrying it are affected). Returns a result row."""
    name = GRIP_NAME.get(enemy)
    row = {'tag': 'mode ' + enemy, 'field': 'grip: ' + weapon.rsplit(BS, 1)[-1], 'ok': False}
    sid = find_sid(m, hp, name) if name else None
    mt, md = _render_model(m, hp, weapon), _render_model(m, hp, donor)
    if sid is None or mt is None or md is None:
        return dict(row, reason='no %s id / render model in this map' % name)
    lt, ld = _marker(m, hp, mt, OFFHAND[enemy]), _marker(m, hp, md, OFFHAND[enemy])
    if lt is None or ld is None:
        return dict(row, reason='no off-hand marker on the weapon or the donor')
    style = style or GRIP_STYLE.get(GAME, {}).get(enemy, 'body')
    if style == 'offhand':
        t, q = _compose(lt[0], _inverse(ld[0]))
        how = 'aligned to the %s off-hand' % donor.rsplit(BS, 1)[-1]
    else:
        # the weapon's body frame where the donor's sits in the hand: M = B_w * inverse(F_donor)
        t, q = _compose(_body_frame(m, hp, mt), _inverse(_donor_frame(m, hp, md)))
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
        gs = [g for f in ENEMY_CHARS.get(enemy, ()) for _p, g in graphs.by_folder.get(f, ())]
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
                if dp in {t.lower() for t in taught.get(enemy, ())}:
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
        if not _grow_sorted(m, hp, cls_el + JM_SUB, JM_TYPE_ES, new):
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
        if GAME == 'Halo 3: ODST':
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
    nofire = set(w for w in handed if has_firing(m, hp, w) is False)
    sid = find_variant(m, hp, 'shieldless')
    stats = {'shieldless': 0, 'reshielded': 0, 'no_variant': 0, 'kept_original': 0,
             'ft_jackals': 0}
    done = {}

    def jackal_shield(loc, w, at=LOC_VARIANT):
        if two_handed(m, hp, info.get(w)):
            if sid is None:
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

    if GAME == 'Halo 3: ODST':
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
                     'an element' % (stats['cells'], stats['unshared'], stats['filled'])})
    if stats['shieldless'] or stats['reshielded'] or stats['no_variant'] or stats['ft_jackals']:
        rows.append({'tag': tag + 'Jackal', 'field': 'Jackal shields', 'ok': not stats['no_variant'],
                     'new': '%d locations shieldless (two-handed), %d given the shield back; %d '
                     'fire-teams armed (their extras keep the shield)%s' % (
                         stats['shieldless'], stats['reshielded'], stats['ft_jackals'],
                         '; %d KEPT the shield: no shieldless variant id in this map'
                         % stats['no_variant'] if stats['no_variant'] else '')})
    if stats['kept_original']:
        rows.append({'tag': tag.rstrip(BS), 'field': 'mixed fire-teams', 'ok': True,
                     'new': '%d locations of another species keep the fire-team\'s original '
                     'weapon (they cannot hold the new one)' % stats['kept_original']})
    return rows, done


def _arm_cells(m, hp, base, widx, info, graphs, type_of, draw, count, jackal_shield, char_team,
               stats):
    """ODST: arm the cells (and spawn points with their own weapon) of every squad."""
    stats.update(cells=0, unshared=0, filled=0)
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

    for sq in squads:
        squad_team = _i16(m, sq + SQ_TEAM)
        designer = m.follow_all(sq, [CELL_BLOCKS[0]], [CELL_ES], 'all')
        armed, kinds = {}, {}
        for off in CELL_BLOCKS:
            for cell in m.follow_all(sq, [off], [CELL_ES], 'all'):
                chars = [_i16(m, e + CELL_IDX)
                         for e in m.follow_all(cell, [CELL_CHARS], [CELL_ARR_ES], 'all')]
                types = set(type_of(c) for c in chars)
                kinds[cell] = types
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
        for cell, w in armed.items():
            if kinds.get(cell) == {'Jackal'} and two_handed(m, hp, info.get(w)) \
                    and _i16(m, cell + CELL_COUNT) > placed.get(cell, 0):
                stats['ft_jackals'] += 1


def apply(m, hp, spec, registry=None, salt=None, game='Halo 3'):
    bind(game if game in LAYOUTS else 'Halo 3', m, hp)
    rows, _done = arm(m, hp, (spec or {}).get('cards') or {}, salt=salt)
    for r in rows:
        r.setdefault('effect', 'enemy weapons')
    return rows
