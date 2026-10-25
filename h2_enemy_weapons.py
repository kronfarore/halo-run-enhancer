r"""Halo 2 'Armed: <weapon>' -- what weapons the AI carries, at patch time (H2_PORT_PLAN.md 0.5b).
The Halo 2 counterpart of h1_enemy_weapons.py, and much smaller: Halo 2 looks a character's
firing behaviour up BY WEAPON in ai\generic (parent of every species), so arming an enemy is
only a matter of the scenario's squad weapon indices. A port's ai\generic entry is in the kit
tag already (sprint_toolkit/ai_firing_profile.py --h2-port <key> -> h2_ai_firing.py) and rides
every rebuilt level; a stock infantry weapon has had one since 2004.

    apply(m, hp, spec) -> [result rows]        (halo_patch calls it; Halo 2 only)
    spec = {'cards': {'Grunt': {<weapon tag>: share, ...}, 'Marine': {...}, ...},
            'balanced': [<weapon tag>, ...]}     ports whose Balanced box is on

ARMING. Squad Initial Weapon / Initial Secondary (+0x3C / +0x3E) and each starting location's
pair (+0x22 / +0x24) index the scnr Weapon Palette (+0x98, 0x28). Every squad unit whose
character is of a carded species draws a deterministic number in [0, 1) (map name + the field's
address: both co-op machines and a re-patch agree): below the sum of its shares it takes the
weapon whose interval holds it (above 100% in total the shares count by weight, as in Halo 1),
secondary -1. Units the Thunderstorm code protects (vehicle-bound / script-loaded squads,
halo_patch._ts_units) keep theirs. A location whose own weapon is -1 inherits its squad's, so
it follows the squad's draw. A weapon not in the level's palette cannot be handed out (a port
is resident in all 13 levels -- H2_PORT_PLAN 0.1; a stock weapon may be missing): reported.

BALANCED. ai_firing_profiles.json['Halo 2'][weapon] may carry 'balanced_props' {field: value}
and 'balanced_patterns' [{field: value}, {field: value}] (Assembly Halo 2 char names); for a
weapon in spec['balanced'] they are written over the map's ai\generic entry (fixed-size field
writes: Weapons Properties +0xCC/0xCC, weapon datum +0x8; Firing Pattern Properties +0xD4/0x10,
weapon datum +0x4, patterns +0x8/0x40).
"""
import hashlib
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(HERE, 'ai_firing_profiles.json')
GAME = 'Halo 2'

#: enemy type (the enhancer's names) -> character folders it covers. Bosses, Hunters (built-in
#: gun), Sentinel enforcers / constructors and the story characters are left out.
ENEMY_CHARS = {
    'Grunt': ('grunt', 'heretic_grunt'),
    'Jackal': ('jackal',),
    'Elite': ('elite', 'heretic'),
    'Brute': ('brute',),
    'Flood Combat Form': ('floodcombat_elite', 'floodcombat_human'),
    'Bugger': ('bugger',),                       # Drones: hand-held weapons in Halo 2
    # Sentinel AGGRESSORS (+ major / eliminator): a biped with no unit weapons, its beam
    # handed by the squad; its graph is 'any' in every mode, so no teach (user 2026-10-21:
    # as Halo 1's Sentinels). The enforcer is a vehicle with mounted guns: not carded.
    'Sentinel': ('sentinel_aggressor',),
    'Marine': ('marine',),                       # the Ally (Friend) twin
}
NEVER = ('brute_tartarus', 'heretic_leader', 'heretic_leader_hologram', 'marine_johnson_boss',
         'elite_councilor')
WPAL, WPAL_ES = 0x98, 0x28
PROPS, PROPS_ES, PROPS_W = 0xCC, 0xCC, 0x8          # datum of the weapon tagref (+0x4)
FPP, FPP_ES, FPP_W, FPP_PAT, PAT_ES = 0xD4, 0x10, 0x4, 0x8, 0x40
LOC_WEAP, SQUAD_WEAP, SQUAD_TEAM = 0x22, 0x3C, 0x24
ALLY_TYPES = ('Marine',)          # the Ally card's types: they arm the player's side


def side_of(m, hp, cpal, lay):
    """(teams allied with the player, each palette character's biped team)."""
    ids = [struct.unpack_from('<I', m.data, e + lay['pal_id_at'])[0] for e in cpal]
    names = [hp._tag_name_by_id(m, i) if i != 0xFFFFFFFF else None for i in ids]
    friends, char_team = hp._player_friends(m, GAME, names, ids)
    return set(friends), list(char_team)
#: a Jackal handed a two-handed weapon loses its arm shield: its STARTING LOCATION's Actor Variant
#: Name (+0x30, a string id) = 'shieldless' -- the jackal model's own variant, exactly what Bungie
#: does for one ordinary 'jackal' location on 03a (and 21 jackal_sniper ones). The character stays
#: the ordinary Jackal: test 2 switched them to jackal_sniper, and those fired but did not visibly
#: aim (the SNIPER STYLE: suppressing fire, no cover peek / investigate / surprise).
LOC_VARIANT, SHIELDLESS_VARIANT, LOC_CHAR = 0x30, 'shieldless', 0x20
_JK = 'objects' + chr(92) + 'characters' + chr(92) + 'jackal' + chr(92) + 'ai' + chr(92)
SNIPER_JACKAL = _JK + 'jackal_sniper'
SHIELDED_JACKALS = (_JK + 'jackal', _JK + 'jackal_major')    # the inverse's target, in order
# weap (Assembly Halo2MCC): flags +0x12C (bit 22 can be / 23 only dual wielded), weapon class /
# name string ids +0x288 / +0x28C, Barrels +0x2D0 (0xEC: rounds per second +0x4 bounds,
# fire recovery time +0x20)
WEAP_FLAGS, DUAL_BITS, WEAP_CLASS, WEAP_BARRELS, WEAP_BARREL_ES = 0x12C, 3 << 22, 0x288, 0x2D0, 0xEC
# jmad: Modes +0x34 (0x14; label +0x0) > Weapon Class +0x4 (0x14; label +0x0) > Weapon Type +0x4
# (0x34); Weapon List +0x54 (0x8: weapon name, weapon class) -- all 'sort' blocks
JMAD_MODES, JMAD_MODE_ES, MODE_CLASSES, CLASS_ES, CLASS_TYPES, TYPE_ES = 0x34, 0x14, 0x4, 0x14, 0x4, 0x34
JMAD_WEAPON_LIST, WL_ES = 0x54, 0x8
#: THE TEACH: per enemy type, its graph and the classes a missing class is copied from, in order
#: (heretic Grunts use the Grunt graph). Elites and Brutes have every class an Armed weapon needs.
_G = 'objects' + chr(92) + 'characters' + chr(92)
TEACH = {'Grunt': (_G + 'grunt' + chr(92) + 'grunt', ('missile', 'pistol')),
         'Jackal': (_G + 'jackal' + chr(92) + 'jackal', ('pistol',)),
         'Bugger': (_G + 'bugger' + chr(92) + 'bugger', ('pistol',))}
#: THE TYPE TEACH (user, 2026-10-21): a BRUTE holds a two-handed weapon like the Brute Shot. The
#: Brute graph has the classes (rifle: any / pr / sg; support: any / bs) but its rifle 'any' set
#: is the one-handed carry, so every mode holding both gets, in the weapon's class, a weapon TYPE
#: labelled with the weapon's NAME (the type lookup is by weapon name: elite rifle br / csr / sg /
#: sr) = a copy of the support class's 'any' type -- the whole Brute Shot set (pose, moves, aim,
#: fire), children shared. A weapon whose name already has a type there (the shotgun's sg) keeps it.
TEACH_TYPE = {'Brute': (_G + 'brute' + chr(92) + 'brute', 'support', 'any'),
              # Grunts (2026-10-21): the kit Grunt graph now HAS 'rifle' (h2_graph_teach.py, the AR
              # pilot: pistol cloned, pr -> br -- allied Grunts hold the AR / BR like a plasma rifle),
              # so the class teach no longer fires for rifles. A two-handed weapon with no type of its
              # own there (the SAW's sr) gets the fuel rod's set as its type: Grunts keep holding it
              # two-handed, as the user approved in Armed test 3. br keeps the AR pilot's.
              'Grunt': (_G + 'grunt' + chr(92) + 'grunt', 'missile', 'any')}


def enemy_of(char_path):
    """The enemy type a character tag belongs to, or None."""
    if not char_path:
        return None
    parts = char_path.lower().split('\\')
    if parts[-1] in NEVER or len(parts) < 3:
        return None
    folder = parts[2]                               # objects\characters\<folder>\ai\<name>
    return next((e for e, fs in ENEMY_CHARS.items() if folder in fs), None)


def _draw(salt, addr):
    return int(hashlib.sha256(('%s|%d' % (salt, addr)).encode()).hexdigest()[:8], 16) / 2.0 ** 32


def _pick(shares, x):
    """The weapon `x` lands on, or None (keep the unit's own)."""
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


def palette(m, hp, base):
    pal = m.follow_all(base, [WPAL], [WPAL_ES], 'all')
    return [hp._tag_name_by_id(m, struct.unpack_from('<I', m.data, e + 0x4)[0]) for e in pal]


def weapon_info(m, hp, weapon):
    """{'class', 'name', 'dual', 'rate', 'class_sid'} of a weapon tag in the map, or None. `rate` =
    the first barrel's rounds per second (upper), else 1 / its fire recovery time."""
    t = dict(m.find_tags('weap', weapon)).get(weapon)
    if t is None:
        return None
    flags = m.u32(t + WEAP_FLAGS)
    br = m.follow_all(t, [WEAP_BARRELS], [WEAP_BARREL_ES], 'all')
    rate = None
    if br:
        rps = struct.unpack_from('<f', m.data, br[0] + 0x8)[0]
        rec = struct.unpack_from('<f', m.data, br[0] + 0x20)[0]
        rate = rps if rps > 0 else (1.0 / rec if rec > 0 else None)
    sid = m.u32(t + WEAP_CLASS)
    return {'class': m.resolve_stringid(sid), 'class_sid': sid,
            'name': m.resolve_stringid(m.u32(t + WEAP_CLASS + 4)),
            'dual': bool(flags & DUAL_BITS), 'rate': rate}


def two_handed(info):
    """THE TWO-HANDED TEST (user rule, Halo 1 2026-10-08, carried to Halo 2 2026-10-20): not a
    pistol and not dual-wieldable (Halo 2's SMG is class 'rifle' but dual-wields)."""
    return bool(info) and info['class'] != 'pistol' and not info['dual']


def grunt_half(info):
    """Grunts fire a two-handed weapon at HALF rate -- except heavy support ('missile': the fuel
    rod, the rocket launcher)."""
    return two_handed(info) and info['class'] != 'missile'


def find_stringid(m, text):
    """The map's string id for `text` (Halo 2: low 16 bits = string-table index, high byte =
    the length -- halo2_map.resolve_stringid read backwards), or None."""
    try:
        cnt, blob, idx = m.u32(0x30), m.u32(0x34), m.u32(0x3C)
    except Exception:
        return None
    key = text.encode('latin-1') + b'\0'
    at = blob - 1
    while True:
        at = m.data.find(key, at + 1)
        if at < 0:
            return None
        if at == blob or m.data[at - 1] == 0:
            break
    off = at - blob
    arr = memoryview(m.data)[idx:idx + cnt * 4].cast('i')
    for i in range(cnt):
        if arr[i] == off:
            return (len(text) << 24) | i
    return None


def arm(m, hp, cards, salt=None):
    """Rewrite squad weapons by share. A JACKAL given a two-handed weapon spawns shieldless (its
    starting location's Actor Variant Name = 'shieldless'); one given a ONE-handed weapon spawns
    WITH its shield (the inverse, user 2026-10-22: the variant cleared, a jackal_sniper location
    made the ordinary Jackal). Returns (rows, {enemy: {weapon: units}})."""
    base = hp._scnr_base(m)
    wnames = palette(m, hp, base)
    widx = {(n or '').lower(): i for i, n in enumerate(wnames)}
    lay, ts = hp._BETRAYAL[GAME], hp._TS_LAYOUT[GAME]
    cpal = m.follow_all(base, [lay['palette'][0]], [lay['palette'][1]], 'all')
    cnames = [hp._tag_name_by_id(m, struct.unpack_from('<I', m.data, e + lay['pal_id_at'])[0])
              for e in cpal]
    sid = find_stringid(m, SHIELDLESS_VARIANT)
    friends, char_team = side_of(m, hp, cpal, lay)
    # the LEVEL name, not the file name: the first patch reads '<level>.map', every later one
    # '<level>.map.bak' -- salting with the file name re-drew every squad on the 2nd patch
    # (2026-10-24 co-op logs: 04a 22 -> 24 units, 06a rocket launcher -> fuel rod, new code)
    salt = salt or os.path.basename(str(getattr(m, 'path', '') or '')).split('.')[0]
    rows, missing, done = [], set(), {}
    usable, info = {}, {}
    for enemy, ws in (cards or {}).items():
        ok = {}
        for w, s in ws.items():
            if w and w.lower() in widx and s > 0:
                ok[w.lower()] = s
                if w.lower() not in info:
                    info[w.lower()] = weapon_info(m, hp, wnames[widx[w.lower()]])
            elif w:
                missing.add(w)
        if ok:
            usable[enemy] = ok
    seen, shieldless, kept, reshielded = set(), 0, 0, 0
    squad_pick = None                   # the weapon the squad drew; its locations follow it
    lname = [(n or '').lower() for n in cnames]
    shielded = next((lname.index(x) for x in SHIELDED_JACKALS if x in lname), None)

    def unshield(loc):
        """A Jackal LOCATION spawns without the arm shield. Squads have no variant field: a
        squad's draw reaches its Jackals through its locations (the branch for inheriting ones)."""
        nonlocal shieldless, kept
        if sid is None:
            kept += 1
            return
        if m.u32(loc + LOC_VARIANT) != sid:
            struct.pack_into('<I', m.data, loc + LOC_VARIANT, sid)
            shieldless += 1

    def reshield(loc, c):
        """THE INVERSE (user, 2026-10-22, the Spike Rifle: 'a single handed weapon, so they can keep
        their shield ... both ways handled the same way'): a Jackal LOCATION handed a one-handed
        weapon spawns WITH the arm shield -- a 'shieldless' Actor Variant Name is cleared (the
        character's own variant again), and a jackal_sniper (shieldless by its character) becomes
        the ordinary Jackal at this location."""
        nonlocal reshielded
        hit = False
        if sid is not None and m.u32(loc + LOC_VARIANT) == sid:
            struct.pack_into('<I', m.data, loc + LOC_VARIANT, 0)
            hit = True
        if 0 <= c < len(lname) and lname[c] == SNIPER_JACKAL and shielded is not None:
            struct.pack_into('<h', m.data, loc + LOC_CHAR, shielded)
            struct.pack_into('<I', m.data, loc + LOC_VARIANT, 0)
            hit = True
        reshielded += hit

    def jackal_shield(loc, c, w):
        """Both directions in one place: two-handed -> shieldless, one-handed -> shielded."""
        if two_handed(info.get(w)):
            unshield(loc)
        else:
            reshield(loc, c)

    squad_team, inherited = 0, {}
    for u in hp._ts_units(m, GAME, base, lay, ts):
        c = u['char']
        enemy = enemy_of(cnames[c]) if c is not None and 0 <= c < len(cnames) else None
        if u['kind'] == 'squad':
            squad_pick = None
            squad_team = struct.unpack_from('<h', m.data, u['weap_at'][0] - SQUAD_WEAP + SQUAD_TEAM)[0]
        a0, a1 = u['weap_at']
        if u['kind'] == 'loc' and struct.unpack_from('<h', m.data, a0)[0] < 0:
            # A LOCATION WITH NO WEAPON OF ITS OWN spawns with its squad's -- whatever its own
            # character (stock mixed squads: an Elite squad's Grunt locations, 03a e1_cov_inf4_0).
            # When the squad drew a weapon, these units carry it too, so they are counted under
            # THEIR type: the teach / Grunt half rate / species skill / shieldless switch follow
            # (2026-10-21: the AR pilot's per-location test layout showed them uncounted).
            if squad_pick and enemy and a0 not in seen:
                seen.add(a0)
                if enemy == 'Jackal':
                    jackal_shield(a0 - LOC_WEAP, c, squad_pick)
                by = done.setdefault(enemy, {})
                by[squad_pick] = by.get(squad_pick, 0) + 1
                inherited[(enemy, squad_pick)] = inherited.get((enemy, squad_pick), 0) + 1
            continue
        if enemy not in usable:
            continue
        # THE SIDE (user, 2026-10-21): an enemy-type card arms EVERY unit of its type, allied ones
        # too -- the Arbiter's allied Spec Ops Elites / Grunts are covered by 'Armed: Elite' /
        # 'Armed: Grunt' -- while the Ally card stays Marines', and only friendly ones. Team = the
        # squad's, else the character's biped team; allies = halo_patch._player_friends.
        team = squad_team if squad_team > 0 else (char_team[c] if 0 <= c < len(char_team) else None)
        if enemy in ALLY_TYPES and team not in friends:
            continue
        if a0 in seen:
            continue
        seen.add(a0)
        w = _pick(usable[enemy], _draw(salt, a0))
        if u['kind'] == 'squad':
            squad_pick = w
        if w is None:
            continue
        struct.pack_into('<h', m.data, a0, widx[w])
        struct.pack_into('<h', m.data, a1, -1)
        if enemy == 'Jackal' and u['kind'] == 'loc':
            jackal_shield(a0 - LOC_WEAP, c, w)
        by = done.setdefault(enemy, {})
        by[w] = by.get(w, 0) + 1
    for enemy, ws in sorted(done.items()):
        for w, n in sorted(ws.items()):
            rows.append({'tag': 'scnr enemy weapons\\' + enemy, 'field': 'Armed: ' + w.split('\\')[-1],
                         'ok': True, 'reason': '%d squad units / locations%s' % (
                             n, ' (%d of them inherit the squad\'s)' % inherited[(enemy, w)]
                             if inherited.get((enemy, w)) else '')})
    if shieldless or kept:
        rows.append({'tag': 'scnr enemy weapons\\Jackal', 'field': 'Shieldless Jackals (two-handed)',
                     'ok': not kept, 'reason': '%d Jackal locations set to variant shieldless%s' % (
                         shieldless, '; %d KEPT the shield: no \'shieldless\' string id in this map'
                         % kept if kept else '')})
    if reshielded:
        rows.append({'tag': 'scnr enemy weapons\\Jackal', 'field': 'Shielded Jackals (one-handed)',
                     'ok': True, 'reason': '%d Jackal locations given their shield back (variant '
                     'cleared / jackal_sniper -> %s)' % (reshielded, cnames[shielded].rsplit(chr(92), 1)[-1]
                                                          if shielded is not None else '?')})
    for w in sorted(missing):
        rows.append({'tag': 'scnr enemy weapons', 'field': 'Armed: ' + w.split('\\')[-1], 'ok': True,
                     'skip': True, 'reason': 'not in this level\'s weapon palette'})
    return rows, done


def _sorted_block(m, at, count, es, key):
    """Re-sort a relocated block's elements in place (Halo 2 'sort' blocks: modes, weapon
    classes and the weapon list are kept in ascending string-id order -- binary-searched)."""
    els = [bytes(m.data[at + i * es:at + (i + 1) * es]) for i in range(count)]
    els.sort(key=key)
    m.data[at:at + count * es] = b''.join(els)


def teach(m, hp, enemy, weapons):
    """THE TEACH. A Halo 2 unit refuses a weapon whose class its graph lacks and spawns with its
    biped default (seen 2026-10-20: SAW Grunts -- the Grunt graph is any / missile / pistol /
    unarmed), and a mode without the class makes it drop the weapon there (fleeing Grunts and
    Jackals drew their backup plasma pistol: their 'flee' mode is pistol-only). Every mode of the
    enemy's graph that lacks the weapon's class but holds a donor class (TEACH: Grunts the fuel
    rod's two-handed 'missile' set first, else 'pistol'; Jackals and Drones 'pistol') gets a copy of
    the donor labelled with the weapon's class -- weapon types / actions / overlays SHARED by
    pointer, nothing duplicated -- in sorted position, and the graph's Weapon List gets the
    (type, class) pairs tool would have written. An approximation: the unit holds the rifle with
    the donor's poses."""
    rows = []
    gname, donors = TEACH.get(enemy, (None, ()))
    want = {}
    for w in weapons:
        i = weapon_info(m, hp, w)
        if i and i['class'] not in ('unarmed', 'any'):
            want.setdefault(i['class_sid'], i['class'])
    if not want or not gname:
        return rows
    for gname in (gname,):
        t = dict(m.find_tags('jmad', gname)).get(gname)
        if t is None:
            continue
        modes = m.follow_all(t, [JMAD_MODES], [JMAD_MODE_ES], 'all')
        jobs, wl_new = [], []
        for md in modes:
            cls = m.follow_all(md, [MODE_CLASSES], [CLASS_ES], 'all')
            labels = [m.u32(c) for c in cls]
            by = {m.resolve_stringid(m.u32(c)): c for c in cls}
            donor = next((by[d] for d in donors if d in by), None)
            if donor is None:
                continue
            types = [m.u32(x) for x in m.follow_all(donor, [CLASS_TYPES], [TYPE_ES], 'all')]
            new = []
            for sid in want:
                if sid in labels:
                    continue
                e = bytearray(m.data[donor:donor + CLASS_ES])
                struct.pack_into('<I', e, 0, sid)
                new.append(bytes(e))
                for ty in types:
                    if m.resolve_stringid(ty) != 'any':
                        wl_new.append((ty, sid))
            if new:
                jobs.append((md, MODE_CLASSES, CLASS_ES, new))
        if not jobs:
            continue
        wl = m.follow_all(t, [JMAD_WEAPON_LIST], [WL_ES], 'all')
        have = {(m.u32(e), m.u32(e + 4)) for e in wl}
        wl_add = [struct.pack('<II', a, b) for a, b in sorted(set(wl_new)) if (a, b) not in have]
        if wl_add:
            jobs.append((t, JMAD_WEAPON_LIST, WL_ES, wl_add))
        offs = m.grow_blocks(jobs)
        for (tb, bo, es, _n), off in zip(jobs, offs):
            _sorted_block(m, off, m.i32(tb + bo), es,
                          (lambda b: struct.unpack_from('<II', b, 0)) if bo == JMAD_WEAPON_LIST
                          else (lambda b: struct.unpack_from('<I', b, 0)[0]))
        rows.append({'tag': 'jmad ' + gname, 'field': '%s teach: %s' % (enemy, '/'.join(sorted(want.values()))),
                     'ok': True, 'reason': '%d modes got the class (copy of %s), weapon list +%d'
                     % (len([j for j in jobs if j[1] == MODE_CLASSES]), ' / '.join(donors), len(wl_add))})
    return rows


def teach_type(m, hp, enemy, weapons):
    """The type teach (TEACH_TYPE) for the two-handed weapons handed to `enemy`."""
    rows = []
    gname, dclass, dtype = TEACH_TYPE.get(enemy, (None, None, None))
    if not gname:
        return rows
    t = dict(m.find_tags('jmad', gname)).get(gname)
    if t is None:
        return rows
    want = []
    for w in weapons:
        i = weapon_info(m, hp, w)
        if two_handed(i) and i['class'] not in ('unarmed', 'any', dclass):
            want.append((i['class_sid'], m.u32(dict(m.find_tags('weap', w))[w] + WEAP_CLASS + 4),
                         i['name']))
    if not want:
        return rows
    per_class, wl_new, modes_hit = {}, [], 0       # one grow job per class element
    for md in m.follow_all(t, [JMAD_MODES], [JMAD_MODE_ES], 'all'):
        cls = {m.u32(c): c for c in m.follow_all(md, [MODE_CLASSES], [CLASS_ES], 'all')}
        donor_cls = next((c for sid, c in cls.items() if m.resolve_stringid(sid) == dclass), None)
        if donor_cls is None:
            continue
        donor = next((x for x in m.follow_all(donor_cls, [CLASS_TYPES], [TYPE_ES], 'all')
                      if m.resolve_stringid(m.u32(x)) == dtype), None)
        if donor is None:
            continue
        hit = False
        for csid, nsid, _n in want:
            c = cls.get(csid)
            if c is None:
                continue
            if nsid in [m.u32(x) for x in m.follow_all(c, [CLASS_TYPES], [TYPE_ES], 'all')]:
                continue
            e = bytearray(m.data[donor:donor + TYPE_ES])
            struct.pack_into('<I', e, 0, nsid)
            if bytes(e) not in per_class.setdefault(c, []):
                per_class[c].append(bytes(e))
            wl_new.append((nsid, csid))
            hit = True
        modes_hit += hit
    jobs = [(c, CLASS_TYPES, TYPE_ES, els) for c, els in per_class.items()]
    if not jobs:
        return rows
    wl = m.follow_all(t, [JMAD_WEAPON_LIST], [WL_ES], 'all')
    have = {(m.u32(e), m.u32(e + 4)) for e in wl}
    wl_add = [struct.pack('<II', a, b) for a, b in sorted(set(wl_new)) if (a, b) not in have]
    if wl_add:
        jobs.append((t, JMAD_WEAPON_LIST, WL_ES, wl_add))
    offs = m.grow_blocks(jobs)
    for (tb, bo, es, _n), off in zip(jobs, offs):
        _sorted_block(m, off, m.i32(tb + bo), es,
                      (lambda b: struct.unpack_from('<II', b, 0)) if bo == JMAD_WEAPON_LIST
                      else (lambda b: struct.unpack_from('<I', b, 0)[0]))
    rows.append({'tag': 'jmad ' + gname, 'field': '%s type teach: %s' % (
        enemy, '/'.join(sorted({n for _c, _s, n in want}))), 'ok': True,
        'reason': '%d modes: the %s set (%s %s) as the weapon\'s type, weapon list +%d'
        % (modes_hit, enemy, dclass, dtype, len(wl_add))})
    return rows


def grunt_rates(m, hp, weapons):
    """THE GRUNT HALF RATE (user rule): every Grunt character in the map gets its OWN Firing
    Pattern Properties entry for each two-handed, non-heavy weapon handed to Grunts -- ai\\generic's
    two patterns with Rate Of Fire = half (the pattern's own rate, or the weapon's barrel rate
    where the pattern says 0 = 'the weapon's own'). Halo 2 resolves firing data per weapon up the
    parent chain (stock Grunts carry needlers with only a plasma-pistol entry of their own), so
    the other weapons keep ai\\generic's."""
    rows = []
    grunts =[(n, t) for n, t in m.find_tags('char', 'objects\\characters\\*')
              if enemy_of(n) == 'Grunt']
    for w in weapons:
        i = weapon_info(m, hp, w)
        if not grunt_half(i):
            continue
        _pe, pats, fe = entry(m, hp, w, with_fpp=True)
        if fe is None or not pats:
            rows.append({'tag': 'char grunt', 'field': 'Grunt half rate: ' + w.split('\\')[-1],
                         'ok': False, 'reason': 'no ai\\generic firing patterns in this map'})
            continue
        halves = []
        for p in pats:
            r = struct.unpack_from('<f', m.data, p)[0] or (i['rate'] or 0.0)
            e = bytearray(m.data[p:p + PAT_ES])
            struct.pack_into('<f', e, 0, r / 2.0)
            halves.append(bytes(e))
        if not halves or not struct.unpack_from('<f', halves[0], 0)[0]:
            rows.append({'tag': 'char grunt', 'field': 'Grunt half rate: ' + w.split('\\')[-1],
                         'ok': False, 'reason': 'no rate to halve'})
            continue
        n = 0
        for cname, ct in grunts:
            own = m.follow_all(ct, [FPP], [FPP_ES], 'all')
            hit = next((e for e in own if (hp._tag_name_by_id(m, m.u32(e + FPP_W)) or '').lower()
                        == w.lower()), None)
            if hit is not None:
                for k, p in enumerate(m.follow_all(hit, [FPP_PAT], [PAT_ES], 'all')[:len(halves)]):
                    m.data[p:p + PAT_ES] = halves[k]
                n += 1
                continue
            el = bytearray(m.data[fe:fe + FPP_ES])
            struct.pack_into('<iI', el, FPP_PAT, 0, 0)      # patterns: grown below
            count = m.i32(ct + FPP)
            off = m.grow_block(ct, FPP, FPP_ES, [bytes(el)])
            m.grow_block(off + count * FPP_ES, FPP_PAT, PAT_ES, halves)
            n += 1
        rows.append({'tag': 'char grunt*', 'field': 'Grunt half rate: ' + w.split('\\')[-1],
                     'ok': True, 'reason': '%d Grunt characters, rate %s' % (
                         n, ' / '.join('%.3g' % struct.unpack_from('<f', h, 0)[0] for h in halves))})
    return rows


def profiles():
    try:
        with open(PROFILE_FILE, encoding='utf-8') as fh:
            return json.load(fh).get(GAME) or {}
    except (OSError, ValueError):
        return {}


#: stock infantry weapons with BOTH ai\generic entries in Halo 2 (H2EK generic.character,
#: 2026-10-20; the disintegrator has Weapons Properties only, vehicle / Sentinel guns are no cards)
STOCK = tuple('objects\\weapons\\' + w for w in (
    'rifle\\battle_rifle\\battle_rifle', 'rifle\\shotgun\\shotgun', 'rifle\\smg\\smg',
    'rifle\\beam_rifle\\beam_rifle', 'support_high\\flak_cannon\\flak_cannon',
    'pistol\\plasma_pistol\\plasma_pistol', 'pistol\\needler\\needler', 'pistol\\magnum\\magnum',
    'support_high\\rocket_launcher\\rocket_launcher', 'support_low\\brute_shot\\brute_shot',
    'melee\\energy_blade\\energy_blade', 'rifle\\brute_plasma_rifle\\brute_plasma_rifle',
    'rifle\\covenant_carbine\\covenant_carbine', 'rifle\\sniper_rifle\\sniper_rifle',
    'rifle\\plasma_rifle\\plasma_rifle'))


def eligible_weapons():
    """Weapon tags an Armed card may hand out in Halo 2: firing data exists for them (stock, or
    a port whose entry h2_ai_firing wrote -- recorded in ai_firing_profiles.json['Halo 2'])."""
    return list(STOCK) + sorted(w for w in profiles() if w not in STOCK)


def entry(m, hp, weapon, char='ai\\generic', with_fpp=False):
    """(props element, [pattern elements]) of `weapon` in the map's ai\\generic, or (None, []);
    with_fpp: (props, patterns, its Firing Pattern Properties element)."""
    hit = dict(m.find_tags('char', char)).get(char)
    if hit is None:
        return (None, [], None) if with_fpp else (None, [])
    want = weapon.lower()
    pe = None
    for e in m.follow_all(hit, [PROPS], [PROPS_ES], 'all'):
        if (hp._tag_name_by_id(m, m.u32(e + PROPS_W)) or '').lower() == want:
            pe = e
            break
    pats, fe = [], None
    for e in m.follow_all(hit, [FPP], [FPP_ES], 'all'):
        if (hp._tag_name_by_id(m, m.u32(e + FPP_W)) or '').lower() == want:
            pats, fe = m.follow_all(e, [FPP_PAT], [PAT_ES], 'all'), e
            break
    return (pe, pats, fe) if with_fpp else (pe, pats)


def balance(m, hp, registry, weapons):
    """Write the Balanced AI rows of each weapon in `weapons` into the map's ai\\generic."""
    rows = []
    plugin = registry.get('char') if registry else None
    profs = profiles()
    for w in weapons or ():
        prof = profs.get(w)
        if not prof or not (prof.get('balanced_props') or prof.get('balanced_patterns')):
            continue
        pe, pats = entry(m, hp, w)
        if pe is None or not pats or plugin is None:
            rows.append({'tag': 'char ai\\generic', 'field': 'Balanced AI: ' + w.split('\\')[-1],
                         'ok': False, 'reason': 'no ai\\generic entry in this map'})
            continue
        fields = {(tuple(f['block_chain']), f['name']): f for f in plugin.fields}
        n = 0
        for name, v in (prof.get('balanced_props') or {}).items():
            f = fields[(('Weapons Properties',), name)]
            _put(m, pe + f['offset'], f['type'], v)
            n += 1
        for k, row in enumerate(prof.get('balanced_patterns') or ()):
            for name, v in (row or {}).items():
                f = fields[(('Firing Pattern Properties', 'Firing Patterns'), name)]
                for p in (pats[k:k + 1] if k < len(pats) else ()):
                    _put(m, p + f['offset'], f['type'], v)
                    n += 1
        rows.append({'tag': 'char ai\\generic', 'field': 'Balanced AI: ' + w.split('\\')[-1],
                     'ok': True, 'reason': '%d fields' % n})
    return rows


def _put(m, at, ftype, v):
    fmt = {'float32': '<f', 'degree': '<f', 'int16': '<h', 'enum16': '<H'}[ftype]
    struct.pack_into(fmt, m.data, at, int(round(v)) if fmt in ('<h', '<H') else v)


#: THE SPECIES SKILL RULE in Halo 2 (user, Halo 1 2026-10-14; Halo 2 2026-10-20). Halo 2 has no
#: per-species aim block: a species' skill is its OWN Weapons Properties entry for its signature
#: weapon, beside ai\generic's for the same weapon -- the Grunt's plasma pistol aims at about half
#: generic's accuracy bounds (Legendary 0.2-0.5 vs 0.6-1.0), takes 3-6x the accuracy time and waits
#: 3 s to surprise-fire (generic 1); the Jackal's equals generic's but waits 2 s. Each field below =
#: ai\generic's entry for the weapon handed out x (species' own / generic) for the signature
#: weapon, where generic's is not 0; bounds capped at 1. (cache offsets in the 0xCC element)
SKILL_FIELDS = (('First Burst Delay Time', 0x48), ('First Burst Delay Time Max', 0x4C),
                ('Surprise Delay Time', 0x50), ('Surprise Fire-Wildly Time', 0x54),
                ('Normal Accuracy Bounds', 0x98), ('Normal Accuracy Bounds Max', 0x9C),
                ('Normal Accuracy Time', 0xA0), ('Heroic Accuracy Bounds', 0xA4),
                ('Heroic Accuracy Bounds Max', 0xA8), ('Heroic Accuracy Time', 0xAC),
                ('Legendary Accuracy Bounds', 0xB0), ('Legendary Accuracy Bounds Max', 0xB4),
                ('Legendary Accuracy Time', 0xB8))
BOUNDS = (0x98, 0x9C, 0xA4, 0xA8, 0xB0, 0xB4)
_C = 'objects' + chr(92) + 'characters' + chr(92)
SKILL_SPECIES = {'Grunt': (_C + 'grunt' + chr(92) + 'ai' + chr(92) + 'grunt',
                           'objects' + chr(92) + 'weapons' + chr(92) + 'pistol' + chr(92) +
                           'plasma_pistol' + chr(92) + 'plasma_pistol'),
                 'Jackal': (_C + 'jackal' + chr(92) + 'ai' + chr(92) + 'jackal',
                            'objects' + chr(92) + 'weapons' + chr(92) + 'pistol' + chr(92) +
                            'plasma_pistol' + chr(92) + 'plasma_pistol')}


def _own_props(m, hp, ct, weapon):
    for e in m.follow_all(ct, [PROPS], [PROPS_ES], 'all'):
        if (hp._tag_name_by_id(m, m.u32(e + PROPS_W)) or '').lower() == weapon.lower():
            return e
    return None


def skill_ratios(m, hp, enemy):
    """{offset: ratio} of a species' signature entry over ai\\generic's, or {} (no signature)."""
    base, sig = SKILL_SPECIES.get(enemy, (None, None))
    ct = dict(m.find_tags('char', base)).get(base) if base else None
    gen_pe, _p = entry(m, hp, sig) if sig else (None, [])
    own = _own_props(m, hp, ct, sig) if ct is not None else None
    if own is None or gen_pe is None:
        return {}
    out = {}
    for _n, off in SKILL_FIELDS:
        g = struct.unpack_from('<f', m.data, gen_pe + off)[0]
        o = struct.unpack_from('<f', m.data, own + off)[0]
        # the species writing 0 (the Grunt's first-burst delay) is no skill data: skipped
        if g > 0 and o > 0 and abs(o - g) > 1e-6:
            out[off] = o / g
    return out


def species_skill(m, hp, done):
    """Every Grunt / Jackal character in the map gets its own Weapons Properties entry for each
    weapon handed to that species (none of its own yet): ai\\generic's, skill fields scaled."""
    rows = []
    for enemy in sorted(SKILL_SPECIES):
        weapons = sorted((done or {}).get(enemy) or ())
        ratios = skill_ratios(m, hp, enemy) if weapons else {}
        if not ratios:
            continue
        chars = [(n, t) for n, t in m.find_tags('char', _C + '*') if enemy_of(n) == enemy]
        for w in weapons:
            gen_pe, _p = entry(m, hp, w)
            if gen_pe is None:
                continue
            el = bytearray(m.data[gen_pe:gen_pe + PROPS_ES])
            for off, r in ratios.items():
                v = struct.unpack_from('<f', el, off)[0] * r
                struct.pack_into('<f', el, off, min(v, 1.0) if off in BOUNDS else v)
            n = 0
            for _cn, ct in chars:
                if _own_props(m, hp, ct, w) is not None:
                    continue                 # the species' own data for this weapon wins
                m.grow_block(ct, PROPS, PROPS_ES, [bytes(el)])
                n += 1
            names = {off: nm for nm, off in SKILL_FIELDS}
            rows.append({'tag': 'char ' + enemy.lower() + '*', 'field': 'Species skill: ' + w.split(chr(92))[-1],
                         'ok': True, 'reason': '%d %s characters; %s' % (n, enemy, ', '.join(
                             '%s x%.2f' % (names[o].replace('Accuracy ', 'acc ').replace(' Bounds', ''), r)
                             for o, r in sorted(ratios.items())))})
    return rows



def apply(m, hp, spec, registry=None, salt=None):
    """The patch pass: Armed cards (Jackals shieldless with two-handed weapons), the Grunt teach
    and half rate for what Grunts were handed, the species skill (Grunt / Jackal own entries),
    then the Balanced AI rows of switched-on ports
    (before the Grunt copies, so the Grunt entries carry the balanced values too)."""
    rows, done = arm(m, hp, (spec or {}).get('cards') or {}, salt=salt)
    rows += balance(m, hp, registry, (spec or {}).get('balanced'))
    for enemy in sorted(TEACH):
        if done.get(enemy):
            rows += teach(m, hp, enemy, sorted(done[enemy]))
    for enemy in sorted(TEACH_TYPE):
        if done.get(enemy):
            rows += teach_type(m, hp, enemy, sorted(done[enemy]))
    if done.get('Grunt'):
        rows += grunt_rates(m, hp, sorted(done['Grunt']))
    rows += species_skill(m, hp, done)
    for r in rows:              # the patch log's results view names every row by its effect
        r.setdefault('effect', 'enemy weapons')
    return rows
