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

NOT YET (first boot decides): teaching missing classes (Weapon List rows), Grunt half rate.
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


def enemy_of(char_path):
    """The enemy type a character tag belongs to, or None (objects / characters / <folder> / ai)."""
    if not char_path:
        return None
    parts = char_path.lower().split(BS)
    if len(parts) < 3 or parts[-1] in NEVER:
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
        modes = {}
        for md in m.follow_all(b, [JM_MODES], [JM_MODE_ES], 'all'):
            ml = m.u32(md)
            self._learn(ml)
            cls = modes.setdefault(ml, {})
            for c in m.follow_all(md, [JM_SUB], [JM_CLASS_ES], 'all'):
                cl = m.u32(c)
                self._learn(cl)
                tys = cls.setdefault(cl, {})
                for t in m.follow_all(c, [JM_SUB], [JM_TYPE_ES], 'all'):
                    tl = m.u32(t)
                    self._learn(tl)
                    acts = set(m.u32(a) for a in m.follow_all(t, [JM_SUB], [JM_ACT_ES], 'all'))
                    if self.idle is None:
                        for a in acts:
                            self._learn(a)
                    tys[tl] = acts
        wl = {m.u32(e): m.u32(e + 4) for e in m.follow_all(b, [JM_WL], [JM_WL_ES], 'all')}
        return {'modes': modes, 'wl': wl, 'base': b}

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


def teach(m, hp, graphs, wanted):
    """TEACHING (user 2026-11-03): `wanted` = {enemy: [weapon path]} the gate refused. Each weapon
    gets a Weapon List row (its NAME -> a donor weapon's class, TEACH_DONORS by kind) in every
    graph of the species, where that class has an 'any' type with an 'idle' action -- the same
    lookup the gate replays, so the unit holds it with the donor's animations. NOT_TAUGHT are
    never taught. Rows go in once per graph (block relocated into partition slack). Returns
    (taught {enemy: set(weapon)}, rows)."""
    adds, taught, rows = {}, {}, []
    tags = {p.lower(): p for p, _b in m.find_tags('weap', '*')}
    by_base = {p.rsplit(BS, 1)[-1]: p for p in tags}
    for enemy, ws in wanted.items():
        gs = [g for f in ENEMY_CHARS.get(enemy, ()) for _p, g in graphs.by_folder.get(f, ())]
        if not gs:
            continue
        for w in ws:
            base = w.lower().rsplit(BS, 1)[-1]
            info = weapon_info(m, tags.get(w.lower(), w))
            if base in NOT_TAUGHT or not info:
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
                    cl = ov if ov is not None and ov != graphs.any and di['class'] != DUAL_CLASS                         else di['class']
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
                    break
    # SORTED (boot 3, 2026-11-04): every stock Weapon List is sorted by the weapon-name string
    # id and the game binary-searches it -- rows appended at the end were found only where the
    # search happened to land on them (Brute Shot yes, Rocket Launcher / turrets no). The whole
    # list is rewritten sorted.
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
        for ft in m.follow_all(sq, [FT], [FT_ES], 'all'):
            for loc in m.follow_all(ft, [LOCS], [LOC_ES], 'all'):
                v = m.u32(loc + LOC_VARIANT)
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
    taught, trows = teach(m, hp, graphs, {e: sorted(ws) for e, ws in refused.items()})
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

    def jackal_shield(loc, w):
        if two_handed(m, hp, info.get(w)):
            if sid is None:
                stats['no_variant'] += 1
            elif m.u32(loc + LOC_VARIANT) != sid:
                struct.pack_into('<I', m.data, loc + LOC_VARIANT, sid)
                stats['shieldless'] += 1
        elif sid is not None and m.u32(loc + LOC_VARIANT) == sid:
            struct.pack_into('<I', m.data, loc + LOC_VARIANT, 0)
            stats['reshielded'] += 1

    def type_of(c):
        return enemy_of(cnames[c]) if c is not None and 0 <= c < len(cnames) else None

    def draw(enemy, team, addr):
        if enemy not in usable:
            return None
        if enemy in ALLY_TYPES and team not in friends:
            return None
        return _pick(usable[enemy], _draw(salt, addr))

    def count(enemy, w):
        by = done.setdefault(enemy, {})
        by[w] = by.get(w, 0) + 1

    for sq in m.follow_all(base, [SQUADS], [SQ_ES], 'all'):
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


def apply(m, hp, spec, registry=None, salt=None):
    rows, _done = arm(m, hp, (spec or {}).get('cards') or {}, salt=salt)
    for r in rows:
        r.setdefault('effect', 'enemy weapons')
    return rows
