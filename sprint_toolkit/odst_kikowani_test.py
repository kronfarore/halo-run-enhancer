r"""Kikowani Station diagnostic: split the remaining explanations in ONE load.

Two independent things fail on sc150 and they need separating.

WEAPONS. Starting weapons come from a Player Starting Profile, not from a position,
so the dead spawn has nothing to do with them. The tags are not the problem either:
sc150 carries 16 of the 17 ODST weapons, the same as every other level (only Sniper
Rifle is genuinely absent). What is odd is the block itself -- profile 0 is named
"buck" and the other fifteen are all "a", where working levels use
"player starting profile_N", and the vanilla assault_rifle sits at indices 0, 4, 8
and 12. A stride of 4 across 16 entries looks like 4 players x 4 of something
(difficulty, or insertion point). If the level reads a profile other than 0, writing
profile 0 is simply writing the wrong row.

The secondary slot is fine, by the way: an early reading that it was "dead" came from
only ever putting weapons in it that this map cannot grant in either slot.

    --profiles all      write every profile (proves whether ANY row is read)
    --profiles 0,4,8,12 write the stride-4 rows only
    --profiles 0        the current behaviour, as a control

EQUIPMENT. A live scan put the player at (-326, 184, 4.6). The tool now drops items on
a nearby vanilla pickup, which lands ~17 units away -- in the level, but easy to walk
past. This drops a ring right ON the measured position instead, so "did it spawn" is
answered separately from "could I find it".

MCC must be closed: it holds the map open. The .bak is left alone, so the GUI's
baseline is unaffected and a normal patch restores everything.

    python odst_kikowani_test.py --profiles all
    python odst_kikowani_test.py --restore
"""
import argparse
import math
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402

ODST = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3odst\maps")
MAP = os.path.join(ODST, 'sc150.map')
PRISTINE = MAP + '.kikotest'          # our own baseline, so the GUI's .bak is untouched
GAME = 'Halo 3: ODST'
REAL = (-326.0, 184.0, 4.6)           # from odst_poswatch, live

# Deliberately unmistakable: neither is in sc150's vanilla loadout, and both are
# visually obvious the instant the level starts.
PRIMARY = 'objects\\weapons\\support_high\\rocket_launcher\\rocket_launcher'
SECONDARY = 'objects\\weapons\\rifle\\shotgun\\shotgun'
PLUGINS = (r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
           r"\Assembly-1-2023-11-29-1702446457\Plugins")


def _profile_block(m, reg):
    plug = reg.get('scnr')
    bf = (plug.find('Starting Health Damage', 'Player Starting Profile')
          or plug.find('Starting Health Modifier', 'Player Starting Profile'))
    if not bf:
        raise SystemExit('Player Starting Profile layout unavailable')
    scnr = HP._scnr_base(m)
    boff, esize = bf['block_offsets'][-1], bf['block_sizes'][-1]
    return scnr, boff, esize, m.i32(scnr + boff)


def _palette_path(m, want):
    """Full tag path of the Weapon Palette entry matching `want`, or None."""
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    n, base = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    for i in range(n) if base else []:
        nm = HP._tag_name_by_id(m, m.u32(base + i * pes + 0xC))
        if nm and str(nm).rsplit('\\', 1)[-1].lower() == want.lower():
            return str(nm)
    return None


def write_weapons(m, reg, which):
    scnr, boff, esize, n = _profile_block(m, reg)
    idxs = range(n) if which == 'all' else [i for i in which if 0 <= i < n]
    salt = HP._h3_ident_salt(m, scnr, boff, esize, n)
    done = []
    for slot, path in (('primary', PRIMARY), ('secondary', SECONDARY)):
        datum = HP._h3_tag_datum(m, 'weap', path)
        if datum is None:
            print('  !! %s tag not in this map: %s' % (slot, path))
            continue
        for i in idxs:
            poff = m.follow(scnr, [boff], [esize], i)
            if poff is None:
                continue
            HP._write_starting_weapon(m, poff, slot, datum, 2, 8, GAME)
            done.append(i)
    print('  weapons -> profiles %s  (of %d, salt 0x%04X)'
          % (sorted(set(done)) if len(set(done)) < 17 else 'ALL', n, salt or 0))


def write_equipment(m):
    """A ring of every piece the level stocks, right on the measured position."""
    lay = HP._MAP_EQUIPMENT[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc = max(0, m.i32(scnr + poff))
    pbase = HP._block_base(m, scnr + poff)
    tags = []
    for i in range(pc):
        nm = HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if isinstance(nm, str) and nm not in tags:
            tags.append(nm)
    print('  equipment ring at %s from %d palette entr(ies)' % (REAL, len(tags)))
    res = HP._apply_spawn_equipment(m, GAME, {'groups': [tags]})
    for r in res:
        print('    %s' % {k: v for k, v in r.items() if k != 'effect'})
    # move whatever it just appended onto the real position, in a tight ring
    io, ies = lay['items']
    n = m.i32(scnr + io)
    base = HP._block_base(m, scnr + io)
    mask = HP._h3_mask_at(m, REAL, GAME) or 0x0002
    # TWO rings, because "nothing spawned" and "spawn protection ate it" look
    # identical from one ring. On Halo 3 every item 0-1u from the spawn was deleted
    # while everything 8u out survived, so the inner ring is the one at risk. If only
    # the outer ring appears, that is spawn protection, not a placement failure.
    added = list(range(max(0, n - len(tags)), n))
    inner, outer = added[:2], added[2:]
    for group, radius in ((inner, 1.6), (outer, 8.0)):
        for k, i in enumerate(group):
            e = base + i * ies
            ang = k * (2 * math.pi / max(1, len(group)))
            struct.pack_into('<fff', m.data, e + HP._EQ_POS,
                             REAL[0] + radius * math.cos(ang),
                             REAL[1] + radius * math.sin(ang), REAL[2])
            struct.pack_into('<H', m.data, e + HP._EQ_ATTACH, mask)
    print('    %d placement(s) on the real position: %d at 1.6u, %d at 8u, mask 0x%04X'
          % (len(added), len(inner), len(outer), mask))


def carbine_test(m):
    """Repalette every Covenant Carbine placement to the rocket launcher, and move the
    equipment onto the carbine nearest the real start.

    The point is that a vanilla placement is a spot the level definitely streams. If
    the rocket launcher appears where a carbine was, weapon tags render fine on sc150
    and the empty hands are a starting-profile problem. If it does not appear even
    there, the weapon cannot render on this map at all and the profile is innocent --
    which is the same streaming gate that stopped H3's auto turret.

    Repaletting an existing placement needs no block growth; only the palette may have
    to gain one entry."""
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)

    names = []
    for i in range(pc):
        nm = HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        names.append(str(nm) if nm else '')
    rocket = next((i for i, nm in enumerate(names) if 'rocket_launcher' in nm.lower()), None)
    if rocket is None:
        print('  !! rocket launcher is not in the weapon palette; using the shotgun')
        rocket = next((i for i, nm in enumerate(names) if 'shotgun' in nm.lower()), None)
    if rocket is None:
        print('  !! neither rocket launcher nor shotgun in the palette -- skipping')
        return None

    carbines = []
    for i in range(max(0, wn)):
        e = wbase + i * wes
        pi = struct.unpack_from('<h', m.data, e + lay['palette_index'])[0]
        if 0 <= pi < len(names) and 'carbine' in names[pi].lower():
            pos = struct.unpack_from('<fff', m.data, e + HP._EQ_POS)
            att = struct.unpack_from('<H', m.data, e + HP._EQ_ATTACH)[0]
            fl = struct.unpack_from('<I', m.data, e + HP._EQ_FLAGS)[0]
            carbines.append((i, pos, att, fl))
    if not carbines:
        print('  !! no carbine placements found')
        return None

    carbines.sort(key=lambda c: math.dist(c[1], REAL))
    print('  %d carbine placement(s); nearest to the real start:' % len(carbines))
    for i, pos, att, fl in carbines[:5]:
        print('    [%3d] (%8.1f,%8.1f,%6.1f) mask 0x%04X flags 0x%X  %.0f units'
              % (i, pos[0], pos[1], pos[2], att, fl, math.dist(pos, REAL)))

    for i, _pos, _att, fl in carbines:
        e = wbase + i * wes
        struct.pack_into('<h', m.data, e + lay['palette_index'], rocket)
        # clear Not Automatically / Never Placed so it spawns at load
        struct.pack_into('<I', m.data, e + HP._EQ_FLAGS,
                         fl & ~(HP._PLACE_NOT_AUTO | HP._PLACE_NEVER))
    print('  every carbine -> palette[%d] %s' % (rocket, names[rocket].rsplit('\\', 1)[-1]))
    return carbines[0]


def drop_weapons(m, wanted, radius=3.0, at=None):
    """Repalette and move the level's own weapon placements onto the real start.

    This is the test for the zone-set explanation AND the prototype of the fix.
    sc150's script `ins_basin_1a` loads in `set_intro` -- a cinematic zone set on
    BSP 0 -- plays the intro, and only THEN switches to `set_basin_1a` and teleports
    the players to where the level really begins. The starting profile is applied
    while `set_intro` is loaded, so the only weapons that can be created are the ones
    that cinematic streams: Buck's assault rifle and Dutch/Mickey's silenced SMG.
    That is exactly the set that works, and it is why a carbine sitting 23 units from
    the start still cannot be granted.

    Placements are read AFTER the teleport, in `set_basin_1a`, where the level's own
    shotgun sits 14 units from the player. So a weapon the profile cannot grant can
    still be laid on the ground at the player's feet. Empty hands then become the
    delivery mechanism rather than the bug: Halo auto-equips a weapon walked over
    while a slot is free.

    `at` overrides the drop point. Dropping on the measured start (-326, 184, 4.6)
    produced NOTHING in-game, and that spot has never actually been confirmed to
    render anything -- the equipment result everyone remembers as "works at the start"
    was on a vanilla pickup 17 units away, not here. So the coordinate is a suspect in
    its own right, and `--drop-at` aims at a spot the level itself already renders a
    weapon on (its shotgun, at -313.3, 190.6, 5.1) to separate "placement is broken"
    from "that position is bad".

    Returns the placements used, or None.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    names = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at'])) or '')
             for i in range(pc)]

    picks = []
    for want in wanted:
        idx = next((i for i, nm in enumerate(names)
                    if nm.rsplit('\\', 1)[-1].lower() == want.lower()), None)
        if idx is None:
            print('  !! %s is not in the Weapon Palette -- skipping' % want)
            continue
        picks.append((want, idx))
    if not picks or wn <= 0:
        print('  !! nothing to drop (%d placement(s) available)' % max(0, wn))
        return None

    spot = tuple(at) if at else REAL
    mask = HP._h3_mask_at(m, spot, GAME) or 0x0002
    used = []
    for k, (want, pi) in enumerate(picks[:wn]):
        e = wbase + k * wes
        ang = k * (2 * math.pi / min(len(picks), wn))
        struct.pack_into('<h', m.data, e + lay['palette_index'], pi)
        struct.pack_into('<fff', m.data, e + HP._EQ_POS,
                         spot[0] + radius * math.cos(ang),
                         spot[1] + radius * math.sin(ang), spot[2])
        struct.pack_into('<H', m.data, e + HP._EQ_ATTACH, mask)
        fl = struct.unpack_from('<I', m.data, e + HP._EQ_FLAGS)[0]
        struct.pack_into('<I', m.data, e + HP._EQ_FLAGS,
                         fl & ~(HP._PLACE_NOT_AUTO | HP._PLACE_NEVER))
        # -1 = no editor folder, so no object_destroy_folder can sweep it away.
        # sc150's own weapon placements sit in folders 41/42 and the intro script
        # destroys folders by name.
        struct.pack_into('<h', m.data, e + 0x42, -1)
        used.append((k, want))
    print('  %d weapon placement(s) moved to (%.1f, %.1f, %.1f), r=%.1f, mask 0x%04X:'
          % (len(used), spot[0], spot[1], spot[2], radius, mask))
    for k, want in used:
        print('    placement[%d] -> %s' % (k, want))
    return used


def repalette_nearest(m, want, donor=None):
    """Change ONE field -- the Palette Index of the placement nearest the real start.

    Position, placement flags, attach mask and editor folder are left exactly as
    shipped, so this is the strictly-one-variable version of --drop. sc150's own
    shotgun sits 14 units from where the level teleports the players, in editor
    folder 41 `wp_basin_1a`, which no `object_destroy_folder` call touches -- so that
    spot definitely renders a weapon in vanilla.

    If the new weapon appears there, repaletting works and the earlier --drop failure
    was the coordinate. If it does not appear even here, then weapon placements do not
    behave like the equipment placements that are already solved, and the drop-at-feet
    fix is dead in the water.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    names = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at'])) or '')
             for i in range(pc)]
    idx = next((i for i, nm in enumerate(names)
                if nm.rsplit('\\', 1)[-1].lower() == want.lower()), None)
    if idx is None:
        print('  !! %s is not in the Weapon Palette' % want)
        return None

    best, bestd = None, None
    for i in range(max(0, wn)):
        e = wbase + i * wes
        pos = struct.unpack_from('<fff', m.data, e + HP._EQ_POS)
        pi = struct.unpack_from('<h', m.data, e + lay['palette_index'])[0]
        cur = names[pi].rsplit('\\', 1)[-1].lower() if 0 <= pi < pc else ''
        if donor and donor.lower() not in cur:
            continue                       # only overwrite the named donor placement
        d = math.dist(pos, REAL)
        if bestd is None or d < bestd:
            best, bestd = i, d
    if best is None:
        print('  !! no weapon placement matching donor %r' % (donor or 'any'))
        return None

    e = wbase + best * wes
    was = struct.unpack_from('<h', m.data, e + lay['palette_index'])[0]
    pos = struct.unpack_from('<fff', m.data, e + HP._EQ_POS)
    struct.pack_into('<h', m.data, e + lay['palette_index'], idx)
    print('  placement[%d] at (%.1f, %.1f, %.1f), %.0fu from the real start:'
          % (best, pos[0], pos[1], pos[2], bestd))
    print('    palette index %d %s -> %d %s   (nothing else touched)'
          % (was, names[was].rsplit('\\', 1)[-1] if 0 <= was < pc else '?', idx, want))
    return best


def stock_nearest(m, wanted):
    """Put the chosen weapons on the level's own nearest weapon spawns.

    The delivery route that actually works. The starting profile can only grant a
    weapon the engine considers resident at the instant the player is created, which
    on sc150 is three weapons and no amount of patching object_new or the
    give-weapon-to-unit rejects changed that. But a PLACEMENT is read after the intro,
    once the level has switched zones -- proven in-game by swapping the shotgun and
    carbine spawns for an SMG and an assault rifle and finding both.

    sc150's nearest spawn is 14 units from where the players land, which is a couple
    of seconds' walk, and unlike a moved placement it sits on a spot the level already
    renders -- no invented coordinate to get wrong.

    Only offer weapons whose resource pages exist; check with
    `h3_raw_residency.py MAP --survey` first.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    names = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at'])) or '')
             for i in range(pc)]
    short = [n.rsplit('\\', 1)[-1].lower() for n in names]

    order = sorted(range(max(0, wn)),
                   key=lambda i: math.dist(
                       struct.unpack_from('<fff', m.data, wbase + i * wes + HP._EQ_POS),
                       REAL))
    out = []
    for k, want in enumerate(wanted):
        if k >= len(order):
            print('  !! only %d weapon placement(s) on this level' % len(order))
            break
        if want.lower() not in short:
            print('  !! %s is not in the Weapon Palette' % want)
            continue
        i = order[k]
        e = wbase + i * wes
        was = struct.unpack_from('<h', m.data, e + lay['palette_index'])[0]
        pos = struct.unpack_from('<fff', m.data, e + HP._EQ_POS)
        struct.pack_into('<h', m.data, e + lay['palette_index'], short.index(want.lower()))
        print('    spawn[%d] %.0fu out at (%.1f, %.1f, %.1f):  %s -> %s'
              % (i, math.dist(pos, REAL), pos[0], pos[1], pos[2],
                 short[was] if 0 <= was < pc else '?', want))
        out.append((i, want))
    return out


def swap_spawns(m, pairs):
    """Repalette placements by name: --swap old=new, repeatable.

    A health check on the whole repalette path, using weapons that are known to work.
    The level's carbine and shotgun spawns become an assault rifle and a silenced SMG
    -- both active at level start, both grantable, both certain to render if the
    machinery is sound. If they appear, repaletting is proven good and the earlier
    "rocket launcher never showed at the carbine spot" result isolates the WEAPON
    rather than the mechanism. If they do not appear, the mechanism was the problem
    all along and every placement conclusion in this file needs re-reading.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    names = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at'])) or '')
             for i in range(pc)]
    short = [n.rsplit('\\', 1)[-1].lower() for n in names]

    done = []
    for spec in pairs:
        if '=' not in spec:
            print('  !! --swap wants old=new, got %r' % spec)
            continue
        old, new = (s.strip().lower() for s in spec.split('=', 1))
        if new not in short:
            print('  !! %s is not in the Weapon Palette' % new)
            continue
        ni = short.index(new)
        hit = 0
        for i in range(max(0, wn)):
            e = wbase + i * wes
            pi = struct.unpack_from('<h', m.data, e + lay['palette_index'])[0]
            if not (0 <= pi < pc) or short[pi] != old:
                continue
            pos = struct.unpack_from('<fff', m.data, e + HP._EQ_POS)
            struct.pack_into('<h', m.data, e + lay['palette_index'], ni)
            print('    placement[%d] at (%.1f, %.1f, %.1f), %.0fu out:  %s -> %s'
                  % (i, pos[0], pos[1], pos[2], math.dist(pos, REAL), old, new))
            hit += 1
        if not hit:
            print('  !! no placement currently holds %s' % old)
        done.append((old, new, hit))
    return done


def equipment_at(m, spot, label, radius=2.0):
    """Ring the already-appended equipment around a given point."""
    lay = HP._MAP_EQUIPMENT[GAME]
    scnr = HP._scnr_base(m)
    io, ies = lay['items']
    n, base = m.i32(scnr + io), HP._block_base(m, scnr + io)
    pos, mask = spot[1], spot[2]
    count = min(5, n)
    for k, i in enumerate(range(n - count, n)):
        e = base + i * ies
        ang = k * (2 * math.pi / count)
        struct.pack_into('<fff', m.data, e + HP._EQ_POS,
                         pos[0] + radius * math.cos(ang),
                         pos[1] + radius * math.sin(ang), pos[2])
        struct.pack_into('<H', m.data, e + HP._EQ_ATTACH, mask)
    print('  %d equipment moved to the %s carbine at (%.1f, %.1f, %.1f), r=%.1f, mask 0x%04X'
          % (count, label, pos[0], pos[1], pos[2], radius, mask))


# scnr Squads: name @0x0, Team @0x24. Each squad holds Designer Cells @0x54 and
# Templated Cells @0x60 (both 0x84 bytes), and a cell carries its loadout as one-entry
# BLOCKS of a 16-byte tagRef: Initial Weapon @0x20, Secondary @0x2C, Equipment @0x38.
_SQUADS = (0x3B8, 0x6C)
_SQ_NAME, _SQ_TEAM = 0x0, 0x24
_CELL_BLOCKS = ((0x54, 0x84), (0x60, 0x84))
# A cell does NOT hold tagRefs. Character Type / Initial Weapon are one-entry tagblocks
# whose payload is an int16 INDEX at +0xC into a scenario palette: Character Palette
# @0x3E8 for the character, and the same Weapon Palette @0x13C the placements use for
# the weapon. Reading them as tagRefs produced a census of cubemaps and shaders.
_CHAR_PALETTE = (0x3E8, 0x10)
_CELL_IDX_AT = 0xC
_CELL_CHARACTER = 0x14
_CELL_PRIMARY, _CELL_SECONDARY = 0x20, 0x2C
# Every sc150 squad reports team 0 (Default) -- the team comes from the character tag,
# not the squad -- so the squad's Team field cannot pick out friendlies. The character
# tag name can.
_FRIENDLY_CHARS = ('marine', 'odst', 'buck', 'dutch', 'romeo', 'mickey', 'dare',
                   'johnson', 'civilian', 'police')


def _palette_names(m, off, esize):
    """Tag names of a scenario palette, indexed as the cells index it."""
    scnr = HP._scnr_base(m)
    n, base = m.i32(scnr + off), HP._block_base(m, scnr + off)
    out = []
    for i in range(max(0, n)) if base else []:
        nm = HP._tag_name_by_id(m, m.u32(base + i * esize + 0xC))
        out.append(str(nm) if nm else '')
    return out


def _cell_char_name(m, ce, chars):
    """Name of the character a squad cell spawns, or ''."""
    n, base = m.i32(ce + _CELL_CHARACTER), HP._block_base(m, ce + _CELL_CHARACTER)
    if not base or n <= 0:
        return ''
    idx = struct.unpack_from('<h', m.data, base + _CELL_IDX_AT)[0]
    return chars[idx] if 0 <= idx < len(chars) else ''


def arm_friendlies(m, path):
    """Give every friendly squad's cells the named weapon.

    An NPC gets its weapon from a completely different place than the player does --
    the squad cell's Initial Weapon, not a starting profile -- so if the tag is alive
    on this map a marine will visibly carry it. If nobody carries it either, the tag
    is dead on sc150 the way the Battle Rifle is dead ODST-wide, and no amount of
    fixing the player's loadout path will ever produce it."""
    scnr = HP._scnr_base(m)
    chars = _palette_names(m, *_CHAR_PALETTE)
    weaps = _palette_names(m, *HP._MAP_WEAPONS[GAME]['palette'])
    widx = next((i for i, nm in enumerate(weaps) if path.rsplit('\\', 1)[-1] in nm.lower()),
                None)
    if widx is None:
        print('  !! %s is not in the Weapon Palette' % path.rsplit('\\', 1)[-1])
        return
    print('  weapon palette index %d = %s' % (widx, weaps[widx].rsplit('\\', 1)[-1]))
    soff, ses = _SQUADS
    n, base = m.i32(scnr + soff), HP._block_base(m, scnr + soff)
    if not base or n <= 0:
        print('  !! no squads')
        return
    census, armed, cells, skipped = {}, set(), 0, 0
    for i in range(n):
        se = base + i * ses
        sname = bytes(m.data[se:se + 32]).split(b'\0')[0].decode('latin-1')
        for coff, ces in _CELL_BLOCKS:
            cn, cbase = m.i32(se + coff), HP._block_base(m, se + coff)
            if not cbase or cn <= 0:
                continue
            for c in range(cn):
                ce = cbase + c * ces
                cname = _cell_char_name(m, ce, chars)
                short = cname.rsplit('\\', 1)[-1] or '(none)'
                census[short] = census.get(short, 0) + 1
                if not any(k in cname.lower() for k in _FRIENDLY_CHARS):
                    continue
                # primary only: leaving the secondary alone keeps the change legible
                wn, wbase = m.i32(ce + _CELL_PRIMARY), HP._block_base(m, ce + _CELL_PRIMARY)
                if not wbase or wn <= 0:
                    skipped += 1
                    continue
                for k in range(wn):
                    struct.pack_into('<h', m.data, wbase + k * 0x10 + _CELL_IDX_AT, widx)
                cells += 1
                armed.add(sname)
    print('  characters on this map:')
    for nm, c in sorted(census.items(), key=lambda kv: -kv[1]):
        friendly = any(k in nm.lower() for k in _FRIENDLY_CHARS)
        print('    %-34s %4d %s' % (nm, c, 'FRIENDLY' if friendly else ''))
    print('  armed %d squad(s), %d cell slot(s) -> %s%s'
          % (len(armed), cells, path.rsplit('\\', 1)[-1],
             '  (%d friendly cell(s) have no weapon slot)' % skipped if skipped else ''))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profiles', default='all',
                    help='"all", "none", or a comma list like 0,4,8,12')
    ap.add_argument('--primary', help='weapon basename for the primary slot')
    ap.add_argument('--secondary', help='weapon basename for the secondary slot')
    ap.add_argument('--no-equipment', action='store_true')
    ap.add_argument('--carbines', action='store_true',
                    help='repalette every carbine to a rocket launcher and put the '
                         'equipment on the carbine nearest the real start')
    ap.add_argument('--arm-friendlies', action='store_true',
                    help='give every friendly squad --friendly-weapon')
    ap.add_argument('--friendly-weapon', default='rocket_launcher',
                    help='what friendlies carry; defaults to a weapon sc150 never '
                         'places or carries, so it stays a control on the player test')
    ap.add_argument('--drop', metavar='W1,W2',
                    help='lay these weapons (palette basenames) on the ground at the '
                         'real start by repaletting the level\'s own placements')
    ap.add_argument('--drop-radius', type=float, default=3.0)
    ap.add_argument('--stock', metavar='W1,W2',
                    help='put these weapons on the level\'s nearest weapon spawns, '
                         'closest first -- the delivery route that works')
    ap.add_argument('--swap', metavar='OLD=NEW', action='append', default=[],
                    help='repalette every placement holding OLD to NEW. Repeatable. '
                         'A health check on the repalette path when NEW is a weapon '
                         'that definitely works, e.g. --swap shotgun=smg_silenced')
    ap.add_argument('--repalette', metavar='WEAPON',
                    help='change only the Palette Index of the placement nearest the '
                         'real start, leaving position/flags/folder as shipped')
    ap.add_argument('--repalette-donor', metavar='WEAPON',
                    help='which existing placement to overwrite, by the weapon it '
                         'currently holds (e.g. covenant_carbine). Default: nearest.')
    ap.add_argument('--drop-at', metavar='X,Y,Z',
                    help='where to drop, instead of the measured start. Negative '
                         'coordinates need the = form: --drop-at=-313.3,190.6,5.1')
    ap.add_argument('--ring', type=float, default=2.0,
                    help='equipment ring radius in world units (default 2.0)')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args(argv)

    if not os.path.exists(MAP):
        raise SystemExit('not found: %s' % MAP)
    if a.restore:
        if not os.path.exists(PRISTINE):
            raise SystemExit('no %s to restore from' % PRISTINE)
        shutil.copy2(PRISTINE, MAP)
        print('restored sc150.map')
        return 0
    if not os.path.exists(PRISTINE):
        # Seed from the GUI's .bak, which IS vanilla. Seeding from sc150.map captured
        # whatever the last enhancer run had written (an earlier copy carried a
        # gravity_hammer secondary), which then silently rode along in every test.
        src = MAP + '.bak' if os.path.exists(MAP + '.bak') else MAP
        shutil.copy2(src, PRISTINE)
        print('saved a pristine copy from %s: %s' % (os.path.basename(src), PRISTINE))
    shutil.copy2(PRISTINE, MAP)        # always build from pristine, never stack patches

    m = HP.open_map(MAP, GAME)
    reg = HP.PluginRegistry(PLUGINS, ['ODSTMCC', 'ODST'])
    print('sc150 diagnostic:')
    global PRIMARY, SECONDARY
    for name, slot in ((a.primary, 'PRIMARY'), (a.secondary, 'SECONDARY')):
        if not name:
            continue
        path = _palette_path(m, name)
        if not path:
            raise SystemExit('%r is not in this map\'s Weapon Palette' % name)
        globals()[slot] = path
        print('  %s slot -> %s' % (slot.lower(), path))
    if a.profiles != 'none':
        which = 'all' if a.profiles == 'all' else [int(x) for x in a.profiles.split(',')]
        write_weapons(m, reg, which)
    if not a.no_equipment:
        write_equipment(m)
    stocked = (stock_nearest(m, [w.strip() for w in a.stock.split(',') if w.strip()])
               if a.stock else None)
    swapped = swap_spawns(m, a.swap) if a.swap else None
    repal = (repalette_nearest(m, a.repalette, a.repalette_donor)
             if a.repalette else None)
    at = [float(v) for v in a.drop_at.split(',')] if a.drop_at else None
    dropped = drop_weapons(m, [w.strip() for w in a.drop.split(',') if w.strip()],
                           a.drop_radius, at) if a.drop else None
    spot = carbine_test(m) if a.carbines else None
    if spot and not a.no_equipment:
        equipment_at(m, spot, 'nearest', a.ring)
    if a.arm_friendlies:
        fw = _palette_path(m, a.friendly_weapon) or a.friendly_weapon
        arm_friendlies(m, fw)
    m.save(MAP)
    print('\nwritten. Load Kikowani Station and report:')
    if stocked:
        print('  - a few steps from where you land, are the level\'s weapon spawns')
        print('    now %s?' % ' and '.join(w for _, w in stocked))
    if swapped:
        print('  HEALTH CHECK -- at the two weapon spawns near the start, do you now')
        print('  find %s?' % ', '.join('a %s where the %s was' % (n, o)
                                       for o, n, k in swapped if k))
        print('  If yes, repaletting works and only the WEAPON was ever the problem.')
    if repal is not None:
        print('  - an AUTO MAGNUM in hand confirms the patched map actually loaded')
        print('  - go to where the %s normally lies: is it a %s now?'
              % (a.repalette_donor or 'nearest weapon', a.repalette))
    if dropped:
        print('  - what, if anything, is IN YOUR HANDS when the intro ends?')
        print('  - are the dropped weapons lying on the ground where you land,')
        print('    and can you pick them up and fire them?')
    if a.carbines:
        print('  - is there a ROCKET LAUNCHER where the carbine near the start was?')
        print('  - equipment ringed around that same spot?')
    else:
        print('  - rocket launcher + shotgun in hand at the start?')
        print('  - a ring of equipment where you are standing?')
    print('undo with:  python odst_kikowani_test.py --restore')
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
