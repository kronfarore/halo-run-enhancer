r"""Halo 1: what weapons the AI carries -- the patch-time pass (2026-10-02).

Everything here is measured in game on b30 first (memory halo1-enemy-weapon-teaching):
  * an actor variant's (actv) Weapon tagref (+0x64) alone decides an AI's weapon;
  * a weapon whose animation LABEL the biped's antr lacks in its STAND stance falls back
    to the biped's default weapon -- teaching the label (a copy of a similar weapon
    type) fixes it (Grunt + AR, Elite + AR);
  * a weapon clone has to be a tag BUILT into the level (adding one to a finished map
    crashes it), so every level carries 20 generic SLOTS (characters\enhancer\slot NN,
    sprint_toolkit/h1_variant_slots.py) the patcher fills: source variant's struct +
    new weapon + the firing block of the most similar variant in the WHOLE GAME that
    already carries the weapon + a major-variant link to a second slot;
  * spawns are moved by the Starting Locations' actor-type override.

Two features use it (user, 2026-10-02):
  OPTION 1  every enemy variant carrying player 1's or player 2's STARTING weapon is
            replaced: by an existing variant of the same enemy with another weapon if
            the level has one, else by a slot taught the enemy's fallback weapon (the
            Options dropdown; Auto picks the weapon that enemy carries most across the
            game). Per-enemy switch. Runs FIRST, so cards always win.
  OPTION 2  cards 'Armed: <weapon>' per enemy type (Allies: Marines): each pick moves
            10% more of that enemy's spawns onto a variant carrying the weapon. Above
            100% in total the shares are weights.

Filled slots must look like their enemy to the rest of the patch: the map is told an
ALIAS for each ('<source> with <weapon>', the clone naming), and HaloMap.find_tags
matches actv lookups against aliases -- so 'characters\grunt\*' cards and the Grunt
colour rows reach a Grunt slot, and '*plasma pistol' cards do not reach an AR one.
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.join(HERE, 'sprint_toolkit')
if TOOLKIT not in sys.path:
    sys.path.insert(0, TOOLKIT)

import h1_variants as hv          # noqa: E402  (layout constants, ranking helpers)
import h1_variant_slots as vs     # noqa: E402
import h1_teach_weapon as tw      # noqa: E402

BS = chr(92)
GAME = 'Halo 1'
INDEX_FILE = os.path.join(HERE, 'h1_actv_index.json')
INDEX_VERSION = 2            # bump when an index entry gains a field (2: 'spawns')

# enemy type -> unit (bipd) path keywords. Checked in order: the Flood combat forms
# carry 'elite' / 'human' in their names, so they come before the Elite.
ENEMY_UNITS = (
    ('Flood Combat Form', ('floodcombat',)),
    ('Grunt', ('grunt',)),
    ('Jackal', ('jackal',)),
    ('Elite', ('elite',)),
    ('Hunter', ('hunter',)),
    ('Sentinel', ('sentinel',)),
    ('Marine', ('marine',)),
)
# no weapon to give, or a scripted set-piece rather than a combatant
EXCLUDED_UNITS = ('infection', 'carrier', 'cyborg', 'captain', 'wounded', 'sitting')
ENEMIES = [e for e, _k in ENEMY_UNITS if e != 'Marine']
# animation types to copy when teaching a label, most similar first
TEACH_DONORS = ('pr', 'ar', 'pp', 'ne', 'hp', 'sg')

# MELEE for a melee-only weapon (the energy sword; weap +0x308 bit 15 'AIs Use Weapon
# Melee Damage') on a unit that cannot melee. Measured on b30 (2026-10-06, two boots):
# Grunt / Jackal / Marine graphs have no 'melee' animation (weapon-class slot 39) in any
# class -- sword Grunts charged and stood -- and their bipeds no Melee Damage (+0x288):
# with a stand-in animation they swung for no damage; with a melee damage ref as well,
# the hits hurt. So: a FASTER COPY of the unit's own arm swing (throw-grenade, else
# signal-attack, else warn) becomes the melee of every class holding the weapon's label,
# and an empty biped Melee Damage takes the weapon's own melee damage effect.
WEAP_FLAGS, AI_WEAPON_MELEE = 0x308, 1 << 15
WEAP_MELEE_DAMAGE = 0x394                  # 'Player Melee Damage' tagref
BIPD_MELEE_DAMAGE = 0x288
CLASS_ANIMS, SLOT_MELEE = 0x98, 39
STAND_IN_SLOTS = (20, 33, 34)              # throw-grenade, signal-attack, warn
MELEE_FRAMES = 28                          # the Elite's sword melee is 28-35 frames


def enemy_of_unit(unit):
    u = (unit or '').lower()
    if any(k in u for k in EXCLUDED_UNITS):
        return None
    for enemy, keys in ENEMY_UNITS:
        if any(k in u for k in keys):
            return enemy
    return None


# ----------------------------------------------------------------------------- index
def build_index(map_paths, open_map):
    """Every actv in the game (from the given level files): name, unit, weapon,
    major (+ its weapon), traits and raw bytes. Cached in INDEX_FILE, keyed by the
    files' size and mtime, because opening all ten levels per patch is slow."""
    key = [INDEX_VERSION] + [[p, os.path.getsize(p), int(os.path.getmtime(p))]
                             for p in map_paths if os.path.exists(p)]
    try:
        with open(INDEX_FILE, encoding='utf-8') as f:
            cached = json.load(f)
        if cached.get('key') == key:
            return cached['actv']
    except Exception:
        pass
    out = []
    for p, _s, _t in key[1:]:
        m = open_map(p, GAME)
        tags = dict(m.find_tags('actv', '*'))
        # how often each variant actually spawns on this level (a promoted major
        # counts through its minor) -- 'used' means spawned, not merely shipped
        spawned = {}
        lv_s = _scnr(m)
        pal = hv._elems(m, lv_s + hv.S_PALETTE, hv.S_PAL_SZ) if lv_s is not None else []
        names = [m.tag_name_by_id(m.u32(x + 0xC)) for x in pal]
        for enc in hv._elems(m, lv_s + hv.S_ENC, hv.S_ENC_SZ) if lv_s is not None else []:
            for sq in hv._elems(m, enc + hv.SQ, hv.SQ_SZ):
                t = struct.unpack_from('<h', m.data, sq + hv.SQ_TYPE)[0]
                for sl in hv._elems(m, sq + hv.SL, hv.SL_SZ):
                    ov = struct.unpack_from('<h', m.data, sl + hv.SL_TYPE)[0]
                    i = ov if ov >= 0 else t
                    if 0 <= i < len(names) and names[i]:
                        spawned[names[i]] = spawned.get(names[i], 0) + 1
        for name, b in tags.items():
            low = name.lower()
            if low.startswith('characters' + BS + 'enhancer' + BS) or hv.CLONE_SEP in name:
                continue
            maj = hv._ref_name(m, b, hv.REF_MAJOR)
            mb = tags.get(maj)
            out.append({'level': os.path.basename(p)[:-4], 'name': name,
                        'spawns': spawned.get(name, 0),
                        'unit': hv._ref_name(m, b, hv.REF_UNIT),
                        'weapon': hv._ref_name(m, b, hv.REF_WEAPON),
                        'major': maj,
                        'major_weapon': hv._ref_name(m, mb, hv.REF_WEAPON) if mb is not None else None,
                        'traits': hv._floats(m, b, hv.TRAITS),
                        'bytes': bytes(m.data[b:b + hv.ACTV_SIZE]).hex(),
                        'major_bytes': bytes(m.data[mb:mb + hv.ACTV_SIZE]).hex() if mb is not None else None})
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump({'key': key, 'actv': out}, f)
    except Exception:
        pass
    return out


PROFILE_FILE = os.path.join(HERE, 'ai_firing_profiles.json')


def profiles():
    """Firing profiles for PORTED weapons nobody in Halo 1 carries
    (sprint_toolkit/ai_firing_profile.py): {weapon path: {'source', 'fields'}}."""
    try:
        with open(PROFILE_FILE, encoding='utf-8') as f:
            return json.load(f).get(GAME, {})
    except Exception:
        return {}


def used_weapons_cached():
    """used_weapons from the cached index file AS IT IS, without checking that it
    matches today's maps -- for drawing cards, where reading ten maps would stall the
    window. None when there is no cache yet (the patch step checks for real)."""
    try:
        with open(INDEX_FILE, encoding='utf-8') as f:
            return used_weapons(json.load(f)['actv'])
    except Exception:
        return None


def used_weapons(index):
    """Weapons some character in the game actually SPAWNS with. The Flood combat
    flamethrower variants ship but are never placed -- an Armed: Flamethrower card was
    a mess in game (user, 2026-10-02) -- so those do not count."""
    # ...plus every PORTED weapon that has a firing profile to stand in for a donor
    return {e['weapon'] for e in index if e['weapon'] and e.get('spawns')} | set(profiles())


def _scnr(m):
    import halo_patch
    return halo_patch._scnr_base(m)


def best_donor(index, weapon, unit, traits):
    """(minor bytes, major bytes, name) of the most similar variant carrying `weapon`:
    same biped first, then the same family (biped name shares the character's), then
    the closest non-weapon numbers; a minor+major pair (major on the SAME weapon) is
    preferred. Scripted set-pieces never donate. None if nobody carries it."""
    fam = [w for w in (unit or '').rsplit(BS, 1)[-1].replace('_', ' ').split() if len(w) > 3]
    best = None
    seen = set()
    for e in index:
        if e['weapon'] != weapon or e['name'] in seen:
            continue
        if any(k in e['name'].lower() for k in ('wounded', 'sitting', 'cinematic')):
            continue
        seen.add(e['name'])
        score = 0.0 if e['unit'] == unit else 1.0
        if e['unit'] != unit and fam and any(w in (e['unit'] or '').lower() for w in fam):
            score -= 0.5
        score += hv._distance(e['traits'], traits)
        major = e['major_bytes'] if e['major_weapon'] == weapon else None
        if major is None:
            score += 0.1
        if best is None or score < best[0] or (score == best[0] and e['name'] < best[3]):
            best = (score, bytes.fromhex(e['bytes']), bytes.fromhex(major) if major else None, e['name'])
    # (minor, major, name, score) -- deterministic, so two co-op machines agree
    return best[1:] + (best[0],) if best else None


# ports whose BALANCED box is on in this patch (apply's spec 'balanced'): their firing
# profile's `balanced_fields` (the Armed Weapon Damage Modifier rule, ai_firing_profile
# wdm_rule) go over `fields`. Absent -> the default fields, as before.
BALANCED = set()


def _fields(prof, weapon):
    f = dict(prof.get('fields') or {})
    if weapon in BALANCED:
        f.update(prof.get('balanced_fields') or {})
    return f or None


def donor_for(m, index, weapon, unit, traits, forced=None):
    """(minor bytes, major bytes, description, profile fields or None).

    A character in the game that carries the weapon, if there is one (best_donor);
    otherwise -- a PORTED weapon -- the best donor among weapons sharing its animation
    LABEL (the SAW is 'ar', so an AR carrier), with the weapon's firing profile to be
    written over it."""
    if forced:
        # a SAVED choice (presets / the shared run) wins, so both co-op machines clone
        # from the same donor whatever their own ranking would say
        e = next((e for e in index if e['name'] == forced), None)
        if e is not None:
            major = e['major_bytes'] if e['major_weapon'] == e['weapon'] else None
            prof = profiles().get(weapon) if e['weapon'] != weapon else None
            return (bytes.fromhex(e['bytes']), bytes.fromhex(major) if major else None,
                    e['name'] + (' + ' + _prof_desc(prof) if prof else ''),
                    _fields(prof, weapon) if prof else None)
    d = best_donor(index, weapon, unit, traits)
    if d:
        return d[0], d[1], d[2], None
    prof = profiles().get(weapon)
    if prof and prof.get('donor_weapon'):
        # a SAME-GAME profile (ai_firing_profile.py --donor-weapon): fire like the best
        # character carrying that weapon -- Halo 1's Sentinel Beam ('sb', a label no one
        # else has) like Halo 1's own Sentinel, whose beam it replaces
        d = best_donor(index, prof['donor_weapon'], unit, traits)
        if d:
            return d[0], d[1], '%s + %s' % (d[2], _prof_desc(prof)), _fields(prof, weapon)
    label = m.weapon_label(weapon)
    if not prof or not label:
        return None
    same = sorted(w for w in {e['weapon'] for e in index if e['weapon']}
                  if m.tag_id(('weap', w)) is not None and m.weapon_label(w) == label)
    best = None
    for w in same:                      # sorted + lowest score: the same on every machine
        d = best_donor(index, w, unit, traits)
        if d and (best is None or d[3] < best[3]):
            best = d
    if best is None:
        return None
    # the FULL donor path stays first: it is what gets saved and looked up again
    return best[0], best[1], '%s + %s' % (best[2], _prof_desc(prof)), _fields(prof, weapon)


def _prof_desc(prof):
    """'Halo 4 storm_lmg profile' from a profile's source line."""
    src = prof.get('source', '?').split(' (')[0]
    return '%s %s profile' % (' '.join(src.split()[:2]), src.rsplit(BS, 1)[-1])


def short_donor(d):
    """A donor description with its path cut to the variant name (patch log only)."""
    head, _sep, tail = str(d).partition(' + ')
    return head.rsplit(BS, 1)[-1] + (' + ' + tail if tail else '')


def write_profile(m, base, fields):
    for off, (fmt, value, _name) in (fields or {}).items():
        struct.pack_into(fmt, m.data, base + int(off, 16), value)


def index_fingerprint(index):
    """A short, order-free code for the donor index: two machines whose codes match
    built their clones from the same donors (co-op patch codes)."""
    import hashlib
    h = hashlib.sha1()
    for e in sorted(index, key=lambda e: (e['level'], e['name'])):
        h.update(('%s|%s|%s|' % (e['level'], e['name'], e['bytes'])).encode('latin-1'))
    return h.hexdigest()[:8]


def carried_weapons(index, enemy):
    """Weapons this enemy type carries anywhere in the game, most common first."""
    from collections import Counter
    c = Counter(e['weapon'] for e in index if e['weapon'] and enemy_of_unit(e['unit']) == enemy)
    return [w for w, _n in c.most_common()]


def auto_fallbacks(lv, index, enemy, unit):
    """The 'Auto' fallback order for an enemy with no other-weapon variant on the
    level: weapons it carries elsewhere in the game (most common first), then weapons
    its STAND animations already cover (no teaching), then every weapon on the level
    (taught from the closest animation set). Vanilla Jackals only ever carry the plasma
    pistol, so the second step is what gives them the needler."""
    out = list(carried_weapons(index, enemy))
    labels = set()
    bipd = dict(lv.m.find_tags('bipd', unit or '-')).get(unit)
    antr = hv._ref_name(lv.m, bipd, 0x38) if bipd is not None else None
    for _p, base in lv.m.find_tags('antr', antr or '-'):
        labels = {l for ul, _u, _c, _w, ls in tw.walk(lv.m, base) if ul == 'stand' for l in ls}
    weapons = [p for p, _o in lv.m.find_tags('weap', '*')
               if p.lower().startswith('weapons' + BS)]
    out += [w for w in weapons if lv.m.weapon_label(w) in labels and w not in out]
    out += [w for w in weapons if w not in out]
    return out


# ----------------------------------------------------------------------------- map
class Level:
    """One H1 map's actor palette, spawns and slots, with the bookkeeping to move
    spawns between variants."""

    def __init__(self, m, hp):
        self.m, self.hp = m, hp
        self.s = hp._scnr_base(m)
        self.tags = dict(m.find_tags('actv', '*'))
        self.pal = hv._elems(m, self.s + hv.S_PALETTE, hv.S_PAL_SZ)
        self.pal_names = [m.tag_name_by_id(m.u32(p + 0xC)) for p in self.pal]
        self.rescan()
        self.free_slots = [i for i in range(1, vs.SLOTS_PER_LEVEL + 1)
                           if vs.slot_path(i) in self.tags]
        self.alias = {}                        # slot path -> '<source> with <weapon>'
        self.clones = {}                       # (source, weapon) -> palette index
        self.moved = set()                     # spawn offsets a card already moved
        self.log = []                          # (slot, alias, donor) per filled slot
        self.forced = {}                       # 'source||weapon' -> saved donor name
        self.chosen = {}                       # ...and what this patch used

    def rescan(self):
        """Re-read every spawn's variant -- after another pass (h1_species_swap) moved
        squads, which shares this Level so its slots and aliases stay known."""
        m = self.m
        self.spawns = []                       # [start location offset, palette index]
        for enc in hv._elems(m, self.s + hv.S_ENC, hv.S_ENC_SZ):
            for sq in hv._elems(m, enc + hv.SQ, hv.SQ_SZ):
                t = struct.unpack_from('<h', m.data, sq + hv.SQ_TYPE)[0]
                for sl in hv._elems(m, sq + hv.SL, hv.SL_SZ):
                    ov = struct.unpack_from('<h', m.data, sl + hv.SL_TYPE)[0]
                    self.spawns.append([sl, ov if ov >= 0 else t])

    def ref(self, name, what):
        return hv._ref_name(self.m, self.tags[name], what) if name in self.tags else None

    def palette_index(self, name):
        """Palette index of actv `name`, appending it if the palette lacks it."""
        if name in self.pal_names:
            return self.pal_names.index(name)
        ref = bytearray(16)
        ref[0:4] = b'vtca'
        struct.pack_into('<I', ref, 4, self.m.tag_name_ptr(('actv', name)))
        struct.pack_into('<I', ref, 0xC, self.m.tag_id(('actv', name)))
        self.m.grow_block(self.s, hv.S_PALETTE, hv.S_PAL_SZ, [bytes(ref)])
        self.pal = hv._elems(self.m, self.s + hv.S_PALETTE, hv.S_PAL_SZ)
        self.pal_names.append(name)
        return len(self.pal_names) - 1

    def spawns_of(self, pal_idx):
        return [sp for sp in self.spawns if sp[1] == pal_idx]

    def move(self, spawn, pal_idx):
        struct.pack_into('<h', self.m.data, spawn[0] + hv.SL_TYPE, pal_idx)
        spawn[1] = pal_idx

    def enemy_of_index(self, i):
        n = self.pal_names[i] if 0 <= i < len(self.pal_names) else None
        if not n or n.lower().startswith('characters' + BS + 'enhancer' + BS):
            src = self.alias.get(n)
            return enemy_of_unit(self.ref(src.split(hv.CLONE_SEP)[0], hv.REF_UNIT)) if src else None
        return enemy_of_unit(self.ref(n, hv.REF_UNIT))

    def weapon_of_index(self, i):
        return self.ref(self.pal_names[i], hv.REF_WEAPON)

    # --- teaching
    def ensure_label(self, unit, weapon):
        """Make sure the unit's antr has the weapon's label in its STAND stance.
        Returns a note, or None when nothing was needed."""
        label = self.m.weapon_label(weapon)
        bipd = dict(self.m.find_tags('bipd', unit or '-')).get(unit)
        antr = hv._ref_name(self.m, bipd, 0x38) if bipd is not None else None
        for _p, base in self.m.find_tags('antr', antr or '-'):
            stand = {l for ul, _u, _c, _w, ls in tw.walk(self.m, base) if ul == 'stand' for l in ls}
            if not label or label in stand:
                return None
            donor = next((d for d in TEACH_DONORS if d in stand), None)
            if donor is None:
                return 'no animation set to copy for %r' % label
            n = tw.teach(self.m, base, donor, label)
            return 'taught %r (from %r, %d classes)' % (label, donor, n)
        return None

    def ensure_melee(self, unit, weapon):
        """Give `unit` a melee for a melee-only `weapon` (see MELEE_FRAMES). A note, or
        None when nothing was needed."""
        wb = dict(self.m.find_tags('weap', weapon)).get(weapon)
        if wb is None or not self.m.u32(wb + WEAP_FLAGS) & AI_WEAPON_MELEE:
            return None
        bipd = dict(self.m.find_tags('bipd', unit or '-')).get(unit)
        if bipd is None:
            return None
        notes = []
        if hv._ref_name(self.m, bipd, BIPD_MELEE_DAMAGE) is None:
            ref = bytes(self.m.data[wb + WEAP_MELEE_DAMAGE:wb + WEAP_MELEE_DAMAGE + 16])
            if hv._ref_name(self.m, wb, WEAP_MELEE_DAMAGE):
                self.m.data[bipd + BIPD_MELEE_DAMAGE:bipd + BIPD_MELEE_DAMAGE + 16] = ref
                notes.append('melee damage %s' % hv._ref_name(self.m, wb, WEAP_MELEE_DAMAGE)
                             .rsplit(BS, 1)[-1])
        label = self.m.weapon_label(weapon)
        antr = hv._ref_name(self.m, bipd, 0x38)
        done = self.__dict__.setdefault('_melee_copies', {})
        for _p, base in self.m.find_tags('antr', antr or '-'):
            n = 0
            for _ul, _u, _cn, w, labs in tw.walk(self.m, base):
                if label not in labs:
                    continue
                slots = tw._elems(self.m, w + CLASS_ANIMS, 2)
                if len(slots) <= SLOT_MELEE or _i16(self.m, slots[SLOT_MELEE]) >= 0:
                    continue
                src = next((_i16(self.m, slots[k]) for k in STAND_IN_SLOTS
                            if len(slots) > k and _i16(self.m, slots[k]) >= 0), None)
                if src is None:
                    continue
                if (antr, src) not in done:
                    done[(antr, src)] = _fast_copy(self.m, base, src, MELEE_FRAMES)
                    base = dict(self.m.find_tags('antr', antr))[antr]   # block moved
                struct.pack_into('<h', self.m.data, slots[SLOT_MELEE], done[(antr, src)])
                n += 1
            if n:
                notes.append('melee animation in %d class(es)' % n)
        return ', '.join(notes) or None

    # --- clones
    def clone(self, source, weapon, index):
        """Palette index of a variant like `source` carrying `weapon`: an existing
        variant of the same biped already carrying it, else a filled slot pair.
        Returns (index, note) or (None, reason)."""
        key = (source, weapon)
        if key in self.clones:
            return self.clones[key], None
        unit = self.ref(source, hv.REF_UNIT)
        actor = self.ref(source, hv.REF_ACTOR)
        existing = [n for n, b in self.tags.items()
                    if not n.lower().startswith('characters' + BS + 'enhancer' + BS)
                    and hv._ref_name(self.m, b, hv.REF_UNIT) == unit
                    and hv._ref_name(self.m, b, hv.REF_ACTOR) == actor
                    and hv._ref_name(self.m, b, hv.REF_WEAPON) == weapon
                    and not any(k in n.lower() for k in ('wounded', 'sitting', 'cinematic'))
                    and n not in {hv._ref_name(self.m, x, hv.REF_MAJOR) for x in self.tags.values()}]
        if existing:
            existing.sort(key=lambda n: -len(self.spawns_of(self.pal_names.index(n)))
                          if n in self.pal_names else 0)
            idx = self.palette_index(existing[0])
            self.clones[key] = idx
            return idx, 'existing variant %s' % existing[0].rsplit(BS, 1)[-1]
        weref = hv._weapon_ref(self.m, weapon)
        if weref is None:
            return None, 'the level has no %s' % weapon.rsplit(BS, 1)[-1]
        major = self.ref(source, hv.REF_MAJOR)
        need = 2 if major in self.tags else 1
        if len(self.free_slots) < need:
            return None, 'no free variant slot (%d left)' % len(self.free_slots)
        donor = donor_for(self.m, index, weapon, unit,
                          hv._floats(self.m, self.tags[source], hv.TRAITS),
                          self.forced.get(source + '||' + weapon))
        if donor:
            self.chosen[source + '||' + weapon] = donor[2].split(' + ')[0]
        dmin, dmaj = (donor[0], donor[1] or donor[0]) if donor else (None, None)
        prof = donor[3] if donor else None
        dname = donor[2] if donor else 'itself (no donor)'
        major_ref = None
        if need == 2:
            ms = self.free_slots.pop(0)
            write_profile(self.m, vs.fill_slot(self.m, ms, self.tags[major], weref, dmaj), prof)
            major_ref = vs.slot_ref(self.m, ms)
            self.alias[vs.slot_path(ms)] = major + hv.CLONE_SEP + weapon.rsplit(BS, 1)[-1]
            self.log.append((ms, self.alias[vs.slot_path(ms)], dname))
        sl = self.free_slots.pop(0)
        write_profile(self.m, vs.fill_slot(self.m, sl, self.tags[source], weref, dmin, major_ref), prof)
        self.alias[vs.slot_path(sl)] = source + hv.CLONE_SEP + weapon.rsplit(BS, 1)[-1]
        self.log.append((sl, self.alias[vs.slot_path(sl)], dname))
        # a major has a biped of its own (Jackal major), which needs the melee too
        major_unit = self.ref(major, hv.REF_UNIT) if need == 2 else None
        taught = '; '.join(x for x in (
            self.ensure_label(unit, weapon), self.ensure_melee(unit, weapon),
            self.ensure_melee(major_unit, weapon) if major_unit not in (None, unit) else None)
            if x)
        idx = self.palette_index(vs.slot_path(sl))
        self.clones[key] = idx
        return idx, 'slot %02d%s, firing from %s%s' % (
            sl, ' (+major)' if need == 2 else '', short_donor(dname),
            '; ' + taught if taught else '')


# ----------------------------------------------------------------------------- passes
def _i16(m, off):
    return struct.unpack_from('<h', m.data, off)[0]


def _fast_copy(m, antr_base, src, frames):
    """Append to the antr's Animations block a copy of animation `src` resampled to at
    most `frames` frames, with buffers of its OWN (the original keeps playing as it was:
    Grunts still throw grenades with it). Returns the copy's index."""
    import halo3_reload as hr
    el = tw._elems(m, antr_base + hr.H1_ANIM_BLK, hr.H1_ANIM_EL)[src]
    new = bytearray(m.data[el:el + hr.H1_ANIM_EL])
    fc = _i16(m, el + hr.H1_FC)
    nf = max(2, min(fc, frames))
    flags = struct.unpack_from('<H', m.data, el + 0x3A)[0]
    if nf != fc and not flags & 1:                     # compressed data: keep its length
        per = [(hr.H1_FRAME_DATA, _i16(m, el + hr.H1_FRAME_SIZE))]
        itype = _i16(m, el + hr.H1_INFO_TYPE)
        if 0 <= itype < len(hr.H1_INFO_SIZES) and hr.H1_INFO_SIZES[itype]:
            per.append((hr.H1_FRAME_INFO, hr.H1_INFO_SIZES[itype]))
        for off, size in per:
            n, at = hr._h1_dataref(m, el, off)
            have = min(fc, n // size) if at is not None and size > 0 else 0
            if have < 1:
                continue
            out = bytearray()
            for i in range(nf):
                k = int(round(i * (have - 1) / float(nf - 1)))
                if off == hr.H1_FRAME_INFO:
                    # root motion is per-frame movement: keep the total distance
                    out += _scaled_info(m.data[at + k * size:at + (k + 1) * size], fc / float(nf))
                else:
                    out += m.data[at + k * size:at + (k + 1) * size]
            na = m.append_raw(bytes(out))
            struct.pack_into('<i', new, off, len(out))
            struct.pack_into('<I', new, off + 0xC, (na + m.magic) & 0xFFFFFFFF)
        struct.pack_into('<h', new, hr.H1_FC, nf)
        mult = nf / float(fc)
        for off in hr.H1_I16_FRAMES:
            v = struct.unpack_from('<h', new, off)[0]
            struct.pack_into('<h', new, off, max(0, min(nf - 1, int(round(v * mult)))))
        for off in hr.H1_I8_FRAMES:
            if new[off] not in (0, 0xFF):
                new[off] = max(0, min(nf - 1, int(round(new[off] * mult))))
    nf = struct.unpack_from('<h', new, hr.H1_FC)[0]
    if struct.unpack_from('<h', new, 0x34)[0] <= 0:    # the hit lands at the key frame
        struct.pack_into('<h', new, 0x34, nf // 2)
    struct.pack_into('<h', new, 0x38, -1)              # no next animation
    name = tw._ascii(m, el).rsplit(' ', 1)[0] + ' melee (enhancer)'
    new[0:0x20] = name.encode('latin-1')[:0x1F].ljust(0x20, b'\0')
    count = m.u32(antr_base + hr.H1_ANIM_BLK)
    m.grow_block(antr_base, hr.H1_ANIM_BLK, hr.H1_ANIM_EL, [bytes(new)])
    return count


def _scaled_info(frame, k):
    """One Frame Info record (dx, dy[, dz][, dyaw] floats) times k."""
    vals = struct.unpack('<%df' % (len(frame) // 4), bytes(frame))
    return struct.pack('<%df' % len(vals), *(v * k for v in vals))


def _row(effect, field, ok=True, skip=False, old=None, new=None, reason=None):
    r = {'effect': effect, 'field': field, 'ok': ok, 'tag': 'scnr'}
    if skip:
        r['skip'] = True
    if old is not None:
        r['old'] = old
    if new is not None:
        r['new'] = new
    if reason:
        r['reason'] = reason
    return r


def option1(lv, index, first_weapons, enabled, fallback):
    """Replace every variant carrying a player's starting weapon."""
    out = []
    first = {w for w in first_weapons if w}
    for i in range(len(lv.pal_names)):
        enemy = lv.enemy_of_index(i)
        weapon = lv.weapon_of_index(i)
        # allies are never touched by this option -- it is about what ENEMIES drop
        if not enemy or enemy == 'Marine' or weapon not in first or not enabled.get(enemy, True):
            continue
        spawns = lv.spawns_of(i)
        if not spawns:
            continue
        src = lv.pal_names[i]
        unit = lv.ref(src, hv.REF_UNIT)
        # an existing variant of this biped with another weapon, most spawned first
        actor = lv.ref(src, hv.REF_ACTOR)
        # a stand-in must be the same KIND of actor, not just the same biped: stealth
        # Elites share the Elite biped with the sword Commanders and lost their
        # camouflage when swapped onto them
        others = [j for j in range(len(lv.pal_names)) if j != i
                  and (lv.pal_names[j] in lv.alias or not (lv.pal_names[j] or '').lower()
                       .startswith('characters' + BS + 'enhancer' + BS))   # no empty slots
                  and lv.ref(lv.pal_names[j], hv.REF_UNIT) == unit
                  and lv.ref(lv.pal_names[j], hv.REF_ACTOR) == actor
                  and lv.weapon_of_index(j) not in first and lv.weapon_of_index(j)]
        others.sort(key=lambda j: -len(lv.spawns_of(j)))
        target, note = (others[0], 'existing variant %s' % lv.pal_names[others[0]].rsplit(BS, 1)[-1]) \
            if others else (None, None)
        if target is None:
            choices = [fallback.get(enemy)] if fallback.get(enemy) else auto_fallbacks(lv, index, enemy, unit)
            choices = [w for w in choices if w and w not in first and lv.m.tag_id(('weap', w)) is not None]
            if not choices:
                out.append(_row('enemy weapons', '%s %s' % (enemy, src.rsplit(BS, 1)[-1]), skip=True,
                                reason='no other weapon available on this level'))
                continue
            target, note = lv.clone(src, choices[0], index)
            if target is None:
                out.append(_row('enemy weapons', '%s %s' % (enemy, src.rsplit(BS, 1)[-1]),
                                ok=False, reason=note))
                continue
        for sp in spawns:
            lv.move(sp, target)
        out.append(_row('enemy weapons', '%s %s' % (enemy, src.rsplit(BS, 1)[-1]),
                        old=weapon.rsplit(BS, 1)[-1],
                        new='%d spawn(s) -> %s (%s)' % (len(spawns), (lv.weapon_of_index(target) or '?').rsplit(BS, 1)[-1], note)))
    return out


def fix_promotions(lv, index, first, enabled):
    """A variant that still spawns must not PROMOTE into a starting weapon either:
    the needler Elite promotes into 'elite major plasma rifle'. Such a major gets a
    slot copy carrying the minor's own weapon (or, if that is a starting weapon too,
    the first Auto fallback), and the minor is pointed at it. Vanilla minors only --
    a filled slot's major was cloned with its new weapon already."""
    out = []
    first = {w for w in first if w}
    fixed = {}
    for i in sorted({sp[1] for sp in lv.spawns}):
        name = lv.pal_names[i]
        enemy = lv.enemy_of_index(i)
        if (not name or not enemy or enemy == 'Marine' or not enabled.get(enemy, True)
                or name.lower().startswith('characters' + BS + 'enhancer' + BS)):
            continue
        major = lv.ref(name, hv.REF_MAJOR)
        if not major or major not in lv.tags or lv.ref(major, hv.REF_WEAPON) not in first:
            continue
        own = lv.ref(name, hv.REF_WEAPON)
        weapon = own if own and own not in first else next(
            (w for w in auto_fallbacks(lv, index, enemy, lv.ref(name, hv.REF_UNIT))
             if w not in first and lv.m.tag_id(('weap', w)) is not None), None)
        if not weapon:
            continue
        key = (major, weapon)
        if key not in fixed:
            weref = hv._weapon_ref(lv.m, weapon)
            if weref is None or not lv.free_slots:
                out.append(_row('enemy weapons', '%s promotion' % name.rsplit(BS, 1)[-1], ok=False,
                                reason='no free variant slot' if weref else 'no %s here' % weapon))
                continue
            d = donor_for(lv.m, index, weapon, lv.ref(major, hv.REF_UNIT),
                          hv._floats(lv.m, lv.tags[major], hv.TRAITS),
                          lv.forced.get(major + '||' + weapon))
            if d:
                lv.chosen[major + '||' + weapon] = d[2].split(' + ')[0]
            sl = lv.free_slots.pop(0)
            write_profile(lv.m, vs.fill_slot(lv.m, sl, lv.tags[major], weref,
                                             (d[1] or d[0]) if d else None), d[3] if d else None)
            lv.alias[vs.slot_path(sl)] = major + hv.CLONE_SEP + weapon.rsplit(BS, 1)[-1]
            lv.log.append((sl, lv.alias[vs.slot_path(sl)], d[2] if d else 'itself (no donor)'))
            fixed[key] = vs.slot_ref(lv.m, sl)
        b = lv.tags[name]
        lv.m.data[b + hv.REF_MAJOR:b + hv.REF_MAJOR + 16] = fixed[key]
        out.append(_row('enemy weapons', '%s promotion' % name.rsplit(BS, 1)[-1],
                        old='%s (%s)' % (major.rsplit(BS, 1)[-1], lv.ref(major, hv.REF_WEAPON).rsplit(BS, 1)[-1]),
                        new='promotes into a %s copy' % weapon.rsplit(BS, 1)[-1]))
    return out


def cards(lv, index, picks):
    """picks = {enemy: {weapon: share}}. Each enemy's spawns, per biped, move to a
    variant carrying the weapon by its share (weights above 100%), spread evenly."""
    out = []
    for enemy, shares in picks.items():
        shares = {w: float(s) for w, s in shares.items() if s and float(s) > 0}
        total = sum(shares.values())
        if total > 1.0:
            shares = {w: s / total for w, s in shares.items()}
        units = {}
        for sp in lv.spawns:
            if lv.enemy_of_index(sp[1]) == enemy:
                units.setdefault(lv.ref(lv.pal_names[sp[1]], hv.REF_UNIT)
                                 or lv.alias.get(lv.pal_names[sp[1]]), []).append(sp)
        if not units:
            continue
        # how many of each biped's spawns every weapon gets, decided TOGETHER: at a
        # full 100% (weights) the counts must add up to every spawn -- rounding each
        # on its own left a vanilla Grunt behind (largest remainder fixes it)
        wants = {}
        for unit, sps in units.items():
            raw = {w: sh * len(sps) for w, sh in shares.items()}
            got = {w: int(math.floor(v)) for w, v in raw.items()}
            target = int(round(sum(raw.values())))
            for w in sorted(raw, key=lambda w: raw[w] - got[w], reverse=True):
                if sum(got.values()) >= target:
                    break
                got[w] += 1
            wants[unit] = got
        used = used_weapons(index)
        for weapon, share in shares.items():
            # decided HERE, not when the card is drawn (user, 2026-10-06: no map reads
            # at draw time): a weapon no character spawns with has no firing to copy
            if weapon not in used:
                out.append(_row('enemy weapons', '%s +%s' % (enemy, weapon.rsplit(BS, 1)[-1]),
                                skip=True, reason='no Halo 1 character spawns with the %s, '
                                'so there is no firing pattern to copy' % weapon.rsplit(BS, 1)[-1]))
                continue
            if lv.m.tag_id(('weap', weapon)) is None:
                out.append(_row('enemy weapons', '%s +%s' % (enemy, weapon.rsplit(BS, 1)[-1]),
                                skip=True, reason='the level has no %s' % weapon.rsplit(BS, 1)[-1]))
                continue
            moved = 0
            notes = []
            for _unit, sps in units.items():
                want = wants[_unit][weapon]
                pool = [sp for sp in sps if sp[0] not in lv.moved and lv.weapon_of_index(sp[1]) != weapon]
                if not want or not pool:
                    continue
                # clone from the variant most of this biped's spawns use
                from collections import Counter
                src_idx = Counter(sp[1] for sp in pool).most_common(1)[0][0]
                src = lv.pal_names[src_idx]
                if src.lower().startswith('characters' + BS + 'enhancer' + BS):
                    src = lv.alias[src].split(hv.CLONE_SEP)[0]
                target, note = lv.clone(src, weapon, index)
                if target is None:
                    notes.append(note)
                    continue
                notes.append(note)
                step = len(pool) / float(want)
                for k in range(min(want, len(pool))):
                    sp = pool[int(k * step)]
                    lv.move(sp, target)
                    lv.moved.add(sp[0])
                    moved += 1
            total_e = sum(len(s) for s in units.values())
            out.append(_row('enemy weapons', '%s +%s' % (enemy, weapon.rsplit(BS, 1)[-1]),
                            ok=bool(moved) or not notes, skip=not moved,
                            old='%d spawn(s)' % total_e,
                            new='%d moved (%.0f%%, asked %.0f%%) -- %s' % (
                                moved, 100.0 * moved / max(1, total_e), 100.0 * share,
                                '; '.join(n for n in notes if n)) if moved else None,
                            reason=None if moved else '; '.join(n for n in notes if n) or 'nothing to move'))
    return out


def apply(m, hp, spec):
    """The whole pass. `spec` = {'levels': [level .map paths for the donor index],
    'first_weapons': [...], 'option1': bool, 'enabled': {enemy: bool},
    'fallback': {enemy: weapon path}, 'cards': {enemy: {weapon path: share}}}."""
    # h1_species_swap runs first and leaves its Level here: same slots, same aliases
    lv = getattr(m, '_h1_level', None)
    if lv is None:
        lv = Level(m, hp)
    else:
        lv.rescan()
    lv.forced = dict(spec.get('donors') or {})
    BALANCED.clear()
    BALANCED.update(spec.get('balanced') or ())
    if not lv.free_slots and (spec.get('option1') or spec.get('cards')):
        note = _row('enemy weapons', 'variant slots', skip=True,
                    reason='this level has no enhancer variant slots (rebuild it with '
                           'characters\\enhancer\\slot 01-20 in the Actor Palette)')
    else:
        note = None
    index = build_index(spec.get('levels') or [], hp.open_map)
    out = []
    if spec.get('option1'):
        out += option1(lv, index, spec.get('first_weapons') or [], spec.get('enabled') or {},
                       spec.get('fallback') or {})
    if spec.get('cards'):
        out += cards(lv, index, spec['cards'])
    if spec.get('option1'):
        out += fix_promotions(lv, index, spec.get('first_weapons') or [], spec.get('enabled') or {})
    # the log a co-op partner compares: what every slot became, and from which donors
    for sl, alias, donor in lv.log:
        out.append(_row('enemy weapons', 'slot %02d' % sl, old='empty',
                        new='%s -- firing from %s' % (alias.rsplit(BS, 1)[-1], short_donor(donor))))
    if lv.log:
        row = _row('enemy weapons', 'donor index', old='%d variants' % len(index),
                   new='fingerprint %s; %d donor choice(s), %d saved before' % (
                       index_fingerprint(index), len(lv.chosen),
                       sum(1 for k in lv.chosen if k in lv.forced)))
        row['donors'] = dict(lv.chosen)        # the patcher stores these with the magnitudes
        out.append(row)
    m.actv_alias = dict(lv.alias)            # cards and colours see slots as their enemy
    if note and any(r.get('reason', '').startswith('no free variant slot') for r in out):
        out.append(note)
    return out
