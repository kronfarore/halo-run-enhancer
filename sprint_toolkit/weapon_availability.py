r"""Which weapons can a level actually give the player? All five games.

The enhancer already had this for ODST alone (`halo_patch.odst_player_weapons`), and
that test does not generalise: it keys on the weap `First Person` block, which the
plugins never name and Halo 1 does not have at all. So this asks the scenario instead,
which every game answers the same way.

Five verdicts, strongest first:

  PLACED         the scenario places it -- a real pickup, or for a detached turret a
                 VEHICLE placement -- and at least one placement spawns automatically.
                 This is proof it exists; see the distance note below for whether you
                 will meet it early.
  SCRIPTED ONLY  placed, but EVERY placement is flagged Not Automatically (or Never
                 Placed), so nothing appears unless a script spawns that spot. Just
                 under half of a Reach level's weapon spots are like this.
  PALETTE        it sits in a palette but nothing places it. Something else spawns it:
                 a script, or a squad carrying it. Treat as likely, not proven --
                 Halo 3's The Storm carries the missile pod exactly this way and it is
                 unmistakably there in play.
  RESIDENT       the tag is in the map but in no palette. Usually a shared dependency,
                 or a weapon another tag references; rarely obtainable.
  ABSENT         not in the map at all. Inserting it means importing the tag first.

WHY A PLACED WEAPON CAN STILL BE MISSING WHERE YOU ARE
------------------------------------------------------
PLACED says the level contains it, not that you will find it. Both extra numbers on
that row exist because a swapped-in weapon looked completely absent in play:

  * how many placements spawn automatically, when only some do -- the raw placement
    count overstates it
  * `start +N` -- how far the nearest AUTOMATIC placement is from the mission start

Nightfall's energy sword is the case: 7 placements, 5 of them automatic, and still not
findable until deep into the level, because all five sit a long way from the spawn.
Neither the count nor the flags could have predicted that; the distance does. Fixing
it means adding the asset near the start, which is a Guerilla job.

Turrets matter here: they are placed as VEHICLES, not weapon pickups, so a
Weapons-only reader reports 0 for a machinegun turret you can plainly rip off its
mount. The Vehicles palette is walked too, and an entry there is kept only when a
WEAPON of the same name is also in the map -- that admits the rippable turret while
leaving Falcons and forklifts out.

    python weapon_availability.py --game "Halo 1"
    python weapon_availability.py --game "Halo 1" --weapon flamethrower
    python weapon_availability.py --game "Halo 1" --map b30 --verbose
    python weapon_availability.py --all --missing        # what halo.json offers but
                                                         # the map cannot supply
    python weapon_availability.py --game "Halo Reach" --both     # weapons AND abilities
    python weapon_availability.py --equipment --map m30          # abilities only

MARKER, in the equipment output, is a placement the map CONTAINS but has flagged Not
Automatically: it sits at the coordinates a designer chose and does nothing until the
patcher clears that bit. That is how a rebuilt Reach map carries an ability -- the
rebuild is what puts the ability's resources in the cache, and the marker is the
parked placement the patcher switches on. An ability the vanilla cache never uses
cannot be made to spawn by patching alone, which is why REBUILD NEEDED is spelled
out rather than left as "not placed".
Reads only; MCC may be running.
"""
import argparse
import collections
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                            # noqa: E402

S = chr(92)

# Placement blocks per game. The weapon entries come from halo_patch._MAP_WEAPONS so
# the two cannot drift; the rest are read off the scnr plugin.
# Every palette offset is stated OUTRIGHT rather than derived from the placement block.
# A tagblock is 12 bytes in Halo 1 and from Halo 3 on, but only 8 in Halo 2, so the
# fixed +0xC this used to assume would read Halo 2's LIGHTMAPS as its vehicle palette.
# The same trap is already called out for weapons below; it applies here identically.
# Only VEHICLES beyond the weapon list: that is where detached turrets live. Scenery
# and Crates carry hundreds of props and would bury the answer in furniture.
_EXTRA = {
    # Halo 1 and Halo 2 are here because without them this tool could not see a
    # vehicle placement in either game at all, so every turret verdict it gave for
    # them was meaningless -- a Shade read RESIDENT ("in no palette") when the level
    # plainly places it. Offsets from the scnr plugins; the palette shapes match the
    # weapon palettes of the same game, which is the cross-check that they are right.
    'Halo 1': {'Vehicles': dict(block=(0x240, 0x78), palette=(0x24C, 0x30),
                                pal_id_at=0xC, palette_index=0x0)},
    'Halo 2': {'Vehicles': dict(block=(0x70, 0x54), palette=(0x78, 0x28),
                                pal_id_at=0x4, palette_index=0x0)},
    'Halo 3': {'Vehicles': dict(block=(0xE4, 0xA8), palette=(0xF0, 0x10),
                                pal_id_at=0xC, palette_index=0x0)},
    'Halo 3: ODST': {'Vehicles': dict(block=(0x100, 0xA8), palette=(0x10C, 0x10),
                                      pal_id_at=0xC, palette_index=0x0)},
    'Halo Reach': {'Vehicles': dict(block=(0x12C, 0xD0), palette=(0x138, 0x10),
                                    pal_id_at=0xC, palette_index=0x0)},
}
def _weapon_layout(game):
    # Reach used to be carried here as a local copy, because _MAP_WEAPONS had no row
    # for it. It has one now (derived independently from Reach's own scnr plugin and
    # landing on the same offsets), so there is one definition again.
    return HP._MAP_WEAPONS.get(game)


def _tag_class(m, rid):
    """Tag class of a palette datum, or None. The Vehicles palette holds real vehicles
    as well as detached turrets; only the turrets are `weap` tags, so the class is what
    separates a rippable plasma cannon from a Falcon."""
    row = rid & 0xFFFF
    tags = getattr(m, 'tags', None)
    if isinstance(tags, dict):                      # H1: {(class, name): off}
        nm = HP._tag_name_by_id(m, rid)
        for (c, n) in tags:
            if n == nm:
                return c
        return None
    t = m.tag(row) if hasattr(m, 'tag') else None
    return str(t['class']).strip() if t and t.get('class') else None


def _palette(m, scnr, pal_off, elem, id_at):
    """[(index, basename, class)] for one placement block's palette."""
    out = []
    for i, el in enumerate(m.follow_all(scnr, [pal_off], [elem], 'all')):
        rid = m.u32(el + id_at)
        nm = HP._tag_name_by_id(m, rid)
        out.append((i, str(nm).rsplit(S, 1)[-1] if nm else None, _tag_class(m, rid)))
    return out


# Per-placement fields that decide whether a placement the block CONTAINS is a thing
# the player can actually walk up to. Offsets differ by game and Reach is the only one
# with a zone-set mask -- Halo 3 and ODST gate by BSP instead and declare no
# `Zone Set Flags` at all, so their entries carry None and the zone column stays blank.
#
# Read off each game's own scnr plugin, and the same within-entry offsets serve the
# Weapons and Equipment blocks in that game.
_PLACE_EXTRA = {
    'Halo 3':       {'flags': 0x4, 'pos': 0x8, 'zone_flags': None, 'bsp_policy': 0x40,
                     'origin_bsp': 0x3C},
    'Halo 3: ODST': {'flags': 0x4, 'pos': 0x8, 'zone_flags': None, 'bsp_policy': 0x40,
                     'origin_bsp': 0x3C},
    'Halo Reach':   {'flags': 0x4, 'pos': 0x8, 'zone_flags': 0x34, 'bsp_policy': 0x33,
                     'origin_bsp': 0x40},
}
# Placement Flags bits that decide whether a row in the block becomes an object the
# player can walk up to. MEASURED on Reach's campaign, which is what corrected an
# earlier guess that zone sets were the gate:
#
#   m10  12 placements 0x100, 10 placements 0x101
#   m30  25 placements 0x100, 30 placements 0x101
#   m70  27 x 0x101, 4 x 0x301, 2 x 0x100
#
# 0x100 is bit 8 "Create At Rest" and is on nearly everything. The bit that matters is
# bit 0, NOT AUTOMATICALLY: the engine does not spawn that placement on its own, a
# script has to. Just under half of every level's weapon spots are like this, so a
# swap that lands on them produces a weapon which is genuinely in the map and simply
# never appears -- which is exactly how Nightfall's energy sword behaved.
#
# Zone Set Flags turned out NOT to be the gate: the mask is 0 for 22/22 placements on
# m10, 47/55 on m30 and 33/33 on m70, and 0 means UNRESTRICTED rather than nowhere.
# The handful of non-zero masks (mask 12 on m30) pair with BSP Policy 2, Manual BSP
# Index. It is still reported, because a non-zero mask really does restrict, but it
# explains far less than the flags do.
NOT_AUTOMATICALLY_BIT = 0
NEVER_PLACED_BIT = 6
# Zone Sets block: scnr 0xAC, 0x13C elements, with the name as a plain ascii string at
# +0x4 (there is a stringid at +0x0 as well, but the ascii needs no string table).
_ZONE_SETS = (0xAC, 0x13C)
_ZONE_NAME_AT = 0x4


def zone_set_names(m, scnr):
    """['set name', ...] in bit order, so a Zone Set Flags mask can be read out loud."""
    off, elem = _ZONE_SETS
    try:
        n = m.i32(scnr + off)
    except Exception:
        return []
    names = []
    for i in range(max(0, min(n, 16))):
        e = m.follow(scnr, [off], [elem], i)
        if e is None:
            names.append('?')
            continue
        raw = bytes(m.data[e + _ZONE_NAME_AT:e + _ZONE_NAME_AT + 0x100])
        names.append(raw.split(b'\0')[0].decode('latin-1') or ('set %d' % i))
    return names


def survey(m, game, weap_names=None):
    """{basename: {'placed': n, 'blocks': {block: n}}} for every palette in the map."""
    weap_names = weap_names if weap_names is not None else resident(m)
    tags = m.find_tags('scnr', '*')
    if not tags:
        return {}
    scnr = tags[0][1]
    lay = _weapon_layout(game)
    blocks = {}
    if lay:
        # The weapon palette's offset is given explicitly, never derived: a tagblock is
        # 12 bytes in Halo 1 and from Halo 3 on, but only 8 in Halo 2, so assuming a
        # fixed delta from the placement block reads Halo 2's LIGHTMAPS as weapons.
        blocks['Weapons'] = (lay['weapons'][0], lay['weapons'][1],
                             lay['palette'][0], lay['palette'][1], lay['pal_id_at'],
                             lay.get('palette_index', 0))
    for name, lay2 in (_EXTRA.get(game) or {}).items():
        blocks[name] = (lay2['block'][0], lay2['block'][1],
                        lay2['palette'][0], lay2['palette'][1],
                        lay2['pal_id_at'], lay2.get('palette_index', 0))
    out = {}
    extra = _PLACE_EXTRA.get(str(game).strip()) or {}
    # Where the mission starts, so a placement's distance from it can be reported.
    # Every starting location is used and the nearest wins: which one is the live spawn
    # is its own unsolved question in Reach (the insertion-point index), and taking the
    # minimum means this number never depends on resolving that.
    try:
        starts = [p for p, _bsp in HP.h3_player_spawns(m, game)]
    except Exception:
        starts = []
    for bname, (off, elem, pal_off, pal_elem, id_at, idx_at) in blocks.items():
        pal = _palette(m, scnr, pal_off, pal_elem, id_at)
        if not pal:
            continue
        cnt = collections.Counter()
        live = collections.Counter()
        near = {}                             # palette idx -> nearest auto placement          # placements NOT flagged Never Placed
        zmask = collections.Counter()         # union of Zone Set Flags, per palette idx
        for el in m.follow_all(scnr, [off], [elem], 'all'):
            pi = struct.unpack_from('<h', m.data, el + idx_at)[0]
            cnt[pi] += 1
            auto = True
            if extra.get('flags') is not None:
                fl = struct.unpack_from('<I', m.data, el + extra['flags'])[0]
                auto = not (fl & ((1 << NEVER_PLACED_BIT)
                                  | (1 << NOT_AUTOMATICALLY_BIT)))
            if auto:
                live[pi] += 1
                # Distance from the mission start to the nearest AUTOMATIC placement.
                # This is the number that answers "will I have this weapon early",
                # and neither the placement count nor the flags can stand in for it:
                # on a patched m10 the energy sword has 7 placements and 5 of them
                # automatic, and it still could not be found until deep into the
                # level, because all five sit far from where the player starts.
                if starts and extra.get('pos') is not None:
                    px, py, pz = struct.unpack_from('<fff', m.data,
                                                    el + extra['pos'])
                    for (sx, sy, sz) in starts:
                        d = ((px - sx) ** 2 + (py - sy) ** 2 + (pz - sz) ** 2) ** 0.5
                        if pi not in near or d < near[pi]:
                            near[pi] = d
            if extra.get('zone_flags') is not None:
                zmask[pi] |= struct.unpack_from(
                    '<H', m.data, el + extra['zone_flags'])[0]
        for i, nm, cls in pal:
            # Keep weapons, and keep a VEHICLE only when a weapon of the same name
            # is also in the map -- that is a mounted turret whose gun the player can
            # rip off. It is what admits the machinegun turret while leaving Falcons
            # and forklifts out.
            if not nm:
                continue
            cls = cls or 'weap'
            if cls != 'weap' and not (cls == 'vehi' and nm in weap_names):
                continue
            rec = out.setdefault(nm, {'placed': 0, 'blocks': {}, 'live': 0,
                                      'zones': 0, 'has_zones': False,
                                      'near': None})
            n = cnt.get(i, 0)
            rec['placed'] += n
            rec['live'] += live.get(i, 0)
            rec['blocks'][bname] = rec['blocks'].get(bname, 0) + n
            if extra.get('zone_flags') is not None:
                rec['zones'] |= zmask.get(i, 0)
                rec['has_zones'] = True
            if i in near and (rec.get('near') is None or near[i] < rec['near']):
                rec['near'] = near[i]
    return out


def vehicle_survey(m, game):
    """{basename: {'placed': n, 'palette': True}} for the Vehicles palette, unfiltered.

    `survey` keeps a vehicle only when a WEAPON of the same basename is also in the map,
    which is the right rule for "can this level arm the player" -- it admits a rippable
    machinegun turret and leaves Falcons out. It is the wrong rule for asking what
    TURRETS a level places, and it fails on Halo 1 outright, where the Shade is the
    vehicle `c gun turret` while its gun is `c gun turret gun`: different basenames, so
    the filter dropped a turret the level places five of. This asks the palette
    directly and lets the caller decide what counts.
    """
    lay = (_EXTRA.get(game) or {}).get('Vehicles')
    tags = m.find_tags('scnr', '*')
    if not lay or not tags:
        return {}
    scnr = tags[0][1]
    pal = _palette(m, scnr, lay['palette'][0], lay['palette'][1], lay['pal_id_at'])
    if not pal:
        return {}
    cnt = collections.Counter()
    for el in m.follow_all(scnr, [lay['block'][0]], [lay['block'][1]], 'all'):
        cnt[struct.unpack_from('<h', m.data, el + lay.get('palette_index', 0))[0]] += 1
    out = {}
    for i, base, cls in pal:
        if not base:
            continue
        rec = out.setdefault(base, {'placed': 0, 'cls': cls})
        rec['placed'] += cnt.get(i, 0)
    return out


_DB = []


def _db():
    """The halo.json ModifierDatabase, loaded once -- it is what maps a display name
    ('Sniper Rifle') to the weap tag path the maps are keyed by."""
    if not _DB:
        import os as _os
        _os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        # load_data prints a checkmark, and on a redirected cp1252 stream that raises
        # -- which load_data swallows, leaving every pool empty and every lookup a
        # miss. Only halo_enhancer.main() guards this, and this is not that entry.
        for _s in (sys.stdout, sys.stderr):
            try:
                _s.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        import halo_enhancer as _he
        _he.load_settings()
        _DB.append(_he.ModifierDatabase())
    return _DB[0]


def offered(game):
    """[(display name, tag basename)] the enhancer can offer in this game.

    The per-map listings only ever walked the scenario palette, so a weapon the map
    does not carry at all was simply invisible -- which is how six absent weapons on
    m20 went unnoticed. The goal is every weapon offered in the game, so the worklist
    has to start from the offer list, not from the map.
    """
    out = []
    for disp in sorted(_db().weapon_mods):
        tag = _db().weap_tag_for(disp, game)
        if not tag:
            continue
        out.append((disp, tag.split(' & ')[0].split(' ', 1)[1].strip().rsplit(S, 1)[-1]))
    return out


_UNIVERSE = {}


def game_universe(game, doc):
    """Every weap tag basename that exists in ANY map of this game.

    Splits the two very different reasons a weapon is missing from a map. One is that
    the map does not carry it but the game does, which an editing-kit rebuild can fix.
    The other is that the weapon is not in the game at all -- the enhancer offers
    eleven Halo 3 weapons for Reach whose tags resolve to another game's paths, and no
    amount of Sapien work will ever place a Battle Rifle in Reach. Telling a user to
    add one is worse than saying nothing.
    """
    if game in _UNIVERSE:
        return _UNIVERSE[game]
    seen = set()
    for mid in doc['Missions'].get(game, {}):
        path = V.resolve(game, mid)
        if not path:
            continue
        try:
            seen |= resident(HP.open_map(path, game))
        except Exception:
            continue
    _UNIVERSE[game] = seen
    return seen


def resident(m):
    """Every weap tag basename physically in the map."""
    return {str(t).rsplit(S, 1)[-1] for t, _b in m.find_tags('weap', '*')}


def _verdict(name, pal, res, zones=None, start_zone=0):
    r"""(verdict, why) for one weapon.

    PLACED is not the end of the story, and assuming it was cost an in-game test: a
    weapon can be placed, render correctly and still be unreachable at the point the
    mission starts, because its placements live in a zone set that streams in later.
    Nightfall's energy sword is the case that taught this -- swapped in, present, and
    only found deep into the level. Two qualifiers now split that out:

      NOT AT START   placements exist but none is in the mission's first zone set
      NEVER PLACED   every placement carries Placement Flags bit 6, so the engine
                     spawns none of them however many rows the block holds

    Both mean "add the asset where the player will be", which is a Guerilla job, and
    both used to read as a clean PLACED.
    """
    rec = pal.get(name)
    if rec and rec['placed'] > 0:
        where = ', '.join('%s x%d' % (b, n) for b, n in sorted(rec['blocks'].items())
                          if n)
        auto = rec.get('live', rec['placed'])
        note = ''
        if rec.get('has_zones') and rec.get('zones'):
            note = ' -- restricted to %s' % ', '.join(
                zones[i] if zones and i < len(zones) else 'set %d' % i
                for i in range(16) if rec['zones'] & (1 << i))
        if not auto:
            return 'SCRIPTED ONLY', ('%s, every placement needs a script '
                                     '(Not Automatically / Never Placed)%s'
                                     % (where, note))
        d = rec.get('near')
        dist = ', start +%.0f' % d if d is not None else ''
        if auto < rec['placed']:
            return 'PLACED', ('%s, %d of %d spawn automatically%s%s'
                              % (where, auto, rec['placed'], dist, note))
        return 'PLACED', where + dist + note
    if rec:
        return 'PALETTE', 'in %s, never placed' % ', '.join(sorted(rec['blocks']))
    if name in res:
        return 'RESIDENT', 'tag present, in no palette'
    return 'ABSENT', 'not in this map'


def verdict(name, pal, res, zones=None, start_zone=0, live=None):
    """_verdict, plus whether the tag is resident when the mission starts.

    A placement is inert if its tag is not in the first zone set's pool, however
    correct the placement is -- that accounted for every weapon that would not spawn
    on m10. This is a separate axis from the placement zone-set restriction above:
    that one asks where the PLACEMENT lives, this asks whether the TAG is loaded.
    Unlike ABSENT it is fixable without an editing kit, so it is a qualifier and not
    a verdict of its own.
    """
    v, why = _verdict(name, pal, res, zones, start_zone)
    if live is not None and v != 'ABSENT' and name not in live:
        why = (why + ' -- ') if why else ''
        why += 'NOT RESIDENT at start, run reach_pools --fix'
    return v, why


def start_resident(m, game):
    """Basenames whose tag bit is set in the mission's FIRST zone set (Reach only).

    Returns None where the question does not apply, so a caller can tell "not asked"
    from "not resident".
    """
    if str(game).strip() != 'Halo Reach':
        return None
    try:
        import reach_pools as RP
        zb = RP.zone_base(m)
    except Exception:
        return None
    except SystemExit:
        return None
    sets = RP.zone_sets(m, zb)
    out = set()
    for t in m.tags:
        if t.get('class') not in ('weap', 'eqip'):
            continue
        i = t.get('index')
        if i is None:
            continue
        if RP.START_SET in RP.resident_in(m, sets, i):
            out.add(str(t.get('name')).rsplit(S, 1)[-1])
    return out


#: The Reach armour abilities, by display name. Health Pack is deliberately absent --
#: the user has ruled it out repeatedly and it has no eqip tag in halo.json.
_REACH_ABILITIES = ['Armor Lock', 'Active Camouflage', 'Drop Shield', 'Hologram',
                    'Jet Pack', 'Sprint']


def _equipment_rows(m, game, indent='      '):
    """Print one line per armour ability for an ALREADY-OPEN map. Shared by
    --equipment (equipment only) and --both (alongside the weapons)."""
    lay = HP._MAP_EQUIPMENT.get(game)
    if not lay:
        return 0
    extra = _PLACE_EXTRA.get(game) or {}
    fl_at = extra.get('flags', 0x4)
    scnr = HP._scnr_base(m)
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    n = m.i32(scnr + ioff)
    base = HP._block_base(m, scnr + ioff)
    names = {}
    for i in range(max(0, m.i32(scnr + poff))):
        e = HP._block_base(m, scnr + poff) + i * pes
        nm = HP._tag_name_by_id(m, m.u32(e + lay['pal_id_at']))
        names[i] = str(nm).rsplit(S, 1)[-1] if nm else '?'
    auto, marker = {}, {}
    for i in range(max(0, n)) if base else []:
        e = base + i * ies
        nm = names.get(struct.unpack_from('<h', m.data, e)[0])
        if not nm:
            continue
        fl = struct.unpack_from('<I', m.data, e + fl_at)[0]
        d = marker if fl & ((1 << NOT_AUTOMATICALLY_BIT)
                            | (1 << NEVER_PLACED_BIT)) else auto
        d[nm] = d.get(nm, 0) + 1
    res = {str(t).rsplit(S, 1)[-1] for t, _b in m.find_tags('eqip', '*')}
    ready = 0
    for disp in _REACH_ABILITIES:
        tag = _db().eqip_tag_for(disp, game)
        if not tag:
            print('%s%-26s %-12s %s' % (indent, disp, 'NO TAG', 'none in halo.json'))
            continue
        bn = tag.split(' ', 1)[1].split('&')[0].strip().rsplit(S, 1)[-1]
        if auto.get(bn):
            v, why = 'PLACED', '%d spawn automatically' % auto[bn]
            ready += 1
        elif marker.get(bn):
            v, why = 'MARKER', ('%d inert placement(s) -- the patcher flips '
                                'Not Automatically' % marker[bn])
            ready += 1
        elif bn in names.values():
            v, why = 'PALETTE', 'in the palette, never placed -- REBUILD NEEDED'
        elif bn in res:
            v, why = 'RESIDENT', 'tag present, not in a palette -- REBUILD NEEDED'
        else:
            v, why = 'ABSENT', 'not in this map -- REBUILD NEEDED'
        print('%s%-26s %-12s %s' % (indent, disp, v, why))
    return ready


def _equipment_main(a):
    r"""Is each map REBUILT with a marker for every armour ability?

    This exists because of what m10 settled: an ability the vanilla cache does not
    already use will not spawn from a patched-in placement, however correct that
    placement is. All six are resident with real tag data and an identical model
    chain, and no eqip field separates the three that work from the three that do
    not -- what the vanilla map lacks is the resource/streaming layer, and only an
    editing-kit rebuild adds that.

    So the question per map is no longer "can I place this" but "has this map been
    rebuilt with the ability present", and the marker pattern used on m10 is the
    answer: one placement of every ability, appended past the stock block, flagged
    Not Automatically so it sits inert until the patcher flips that bit.

    Verdicts per ability:

      MARKER      a Not-Automatically placement exists -- the rebuild pattern. The
                  patcher only has to clear the flag.
      PLACED      the level places it and it spawns on its own already.
      SCRIPTED    placed, but every placement is Not Automatically AND the map is not
                  otherwise prepared, so a script owns it.
      PALETTE     in the palette, never placed. Needs the rebuild.
      RESIDENT    tag present, not in the palette. Needs the rebuild.
      ABSENT      not in the map at all.
    """
    tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = json.load(open(os.path.join(tool, 'halo.json'), encoding='utf-8'))
    game = a.game or 'Halo Reach'
    lay = HP._MAP_EQUIPMENT.get(game)
    if not lay:
        print('no equipment layout for %s' % game)
        return 1
    extra = _PLACE_EXTRA.get(game) or {}
    fl_at = extra.get('flags', 0x4)
    print('\n=== %s: equipment / armour-ability readiness ===' % game)
    print('%-10s %-20s %-9s %s' % ('map', 'ability', 'verdict', 'detail'))
    for mid in doc['Missions'].get(game, {}):
        if a.map and mid != a.map:
            continue
        path = V.resolve(game, mid)
        if not path:
            continue
        m = HP.open_map(path, game)
        print('   %s (%s)' % (mid, doc['Missions'][game][mid].get('name', '')))
        ready = _equipment_rows(m, game)
        print('      %d of %d ready without a rebuild'
              % (ready, len(_REACH_ABILITIES)))
    return 0


def _vehicles_main(a):
    """--vehicles: every Vehicles-palette entry per map, with its placement count."""
    tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = json.load(open(os.path.join(tool, 'halo.json'), encoding='utf-8'))
    games = [a.game] if a.game else list(doc['Missions'])
    for game in games:
        if game not in doc['Missions']:
            continue
        if not (_EXTRA.get(game) or {}).get('Vehicles'):
            print('\n=== %s: no vehicle-placement layout' % game)
            continue
        print('\n=== %s' % game)
        totals = {}
        for mid in doc['Missions'][game]:
            if a.map and mid != a.map:
                continue
            path = V.resolve(game, mid)
            if not path:
                continue
            try:
                m = HP.open_map(path, game)
            except Exception as e:
                print('   %-10s could not open (%s)' % (mid, e))
                continue
            veh = vehicle_survey(m, game)
            for base, rec in veh.items():
                if a.weapon and a.weapon.lower() not in base.lower():
                    continue
                t = totals.setdefault(base, {'placed': 0, 'maps': [], 'cls': rec['cls']})
                t['placed'] += rec['placed']
                if rec['placed']:
                    t['maps'].append('%s x%d' % (mid, rec['placed']))
                elif a.verbose:
                    t['maps'].append('%s(palette only)' % mid)
        for base, t in sorted(totals.items(), key=lambda kv: -kv[1]['placed']):
            print('   %-30s %-5s %4d placement(s)   %s'
                  % (base[:30], t['cls'], t['placed'],
                     ', '.join(t['maps'][:8]) or 'palette only, never placed'))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', help='one game; default every game')
    ap.add_argument('--map', help='one mission id')
    ap.add_argument('--weapon', help='tag basename substring, e.g. flamethrower')
    ap.add_argument('--all', action='store_true', help='list every weapon per map')
    ap.add_argument('--missing', action='store_true',
                    help="only what halo.json's mission list offers but the map cannot")
    ap.add_argument('--gaps', action='store_true',
                    help='every weapon the game offers vs what each map can grant -- '
                         'the only view that shows weapons ABSENT from a map')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--both', action='store_true',
                    help='weapons AND equipment for each map in one listing')
    ap.add_argument('--equipment', action='store_true',
                    help='check the EQUIPMENT block instead: which armour abilities '
                         'each map can spawn, and whether the map has been rebuilt '
                         'with a marker for each (see _equipment_main)')
    ap.add_argument('--vehicles', action='store_true',
                    help='list the Vehicles palette instead, unfiltered -- what a '
                         'level actually places, which is how you find turrets')
    a = ap.parse_args(argv)

    if a.equipment or a.both:
        # Load the effect database NOW. It prints a startup banner on first use, and
        # lazily loading it mid-listing dropped fifty lines of mission list into the
        # middle of a map's table.
        _db()
    if a.equipment:
        return _equipment_main(a)
    if a.vehicles:
        return _vehicles_main(a)

    tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = json.load(open(os.path.join(tool, 'halo.json'), encoding='utf-8'))
    games = [a.game] if a.game else list(doc['Missions'])

    for game in games:
        if game not in doc['Missions']:
            print('unknown game %r' % game)
            continue
        if not _weapon_layout(game):
            print('\n=== %s: no weapon-placement layout' % game)
            continue
        print('\n=== %s' % game)
        for mid, md in doc['Missions'][game].items():
            if a.map and mid != a.map:
                continue
            path = V.resolve(game, mid)
            if not path:
                print('   %-10s map not found' % mid)
                continue
            m = HP.open_map(path, game)
            res = resident(m)
            pal = survey(m, game, res)
            live = start_resident(m, game)
            _t = m.find_tags('scnr', '*')
            zones = zone_set_names(m, _t[0][1]) if _t else []
            if a.weapon:
                hits = sorted(n for n in set(pal) | res if a.weapon.lower() in n.lower())
                if not hits:
                    v, why = verdict(a.weapon, pal, res, zones, live=live)
                    print('   %-10s %-9s %s' % (mid, v, why))
                for n in hits:
                    v, why = verdict(n, pal, res, zones, live=live)
                    print('   %-10s %-26s %-9s %s' % (mid, n, v, why))
                continue
            if a.all or a.verbose:
                print('   %s (%s)' % (mid, md.get('name', '')))
                for n in sorted(set(pal) | (res if a.verbose else set())):
                    v, why = verdict(n, pal, res, zones, live=live)
                    print('      %-30s %-9s %s' % (n, v, why))
                continue
            if a.gaps:
                # The ceiling is what the GAME has, not what the mod list mentions:
                # a weapon whose tag exists in no map of this game can never be
                # placed, and halo.json does not offer those anyway. Anything the
                # game does have is fair game for this map, whether the mission
                # currently offers it or not -- that difference is the worklist.
                uni = game_universe(game, doc)
                here = set(md.get('weapons') or [])
                rows = []
                for disp, base in offered(game):
                    if base not in uni:
                        continue
                    v, why = verdict(base, pal, res, zones, live=live)
                    rows.append((disp, base, disp in here, v, why))
                order = {'ABSENT': 0, 'RESIDENT': 1, 'PALETTE': 2,
                         'SCRIPTED ONLY': 3, 'PLACED': 4}
                rows.sort(key=lambda r: (order.get(r[3], 9), r[0]))
                absent = [r for r in rows if r[3] == 'ABSENT']
                notlive = [r for r in rows
                           if r[3] != 'ABSENT' and 'NOT RESIDENT' in r[4]]
                unoffered = [r for r in rows if not r[2] and r[3] != 'ABSENT']
                print('   %s (%s): %d of the game, %d offered here, %d ABSENT '
                      '(Sapien can add), %d need residency, %d grantable but '
                      'not offered'
                      % (mid, md.get('name', ''), len(rows), len(here),
                         len(absent), len(notlive), len(unoffered)))
                for disp, base, off, v, why in rows:
                    print('      %-22s %-24s %-8s %-13s %s'
                          % (disp, base, 'offered' if off else '-', v, why))
                continue
            if a.missing:
                # What this mission OFFERS in halo.json vs what the map can actually
                # grant. An offer the map cannot honour is the whole point of the
                # import work, so the verdict per offered weapon is the worklist:
                # PALETTE and RESIDENT need placements, ABSENT needs the tag too.
                rows = []
                for disp in (md.get('weapons') or []):
                    tag = _db().weap_tag_for(disp, game)
                    if not tag:
                        rows.append((disp, '-', 'NO TAG', 'halo.json offers it, no '
                                     'weap tag maps to it in this game'))
                        continue
                    base = tag.split(' ', 1)[1].strip().rsplit(S, 1)[-1]
                    v, why = verdict(base, pal, res, zones, live=live)
                    if v != 'PLACED':
                        rows.append((disp, base, v, why))
                print('   %-10s %d of %d offered weapon(s) not placed'
                      % (mid, len(rows), len(md.get('weapons') or [])))
                for disp, base, v, why in rows:
                    print('      %-22s %-26s %-8s %s' % (disp, base, v, why))
                continue
            # ONE LINE PER WEAPON. The old two-line form packed every name into a
            # comma list truncated at 96 characters, so the interesting entries fell
            # off the end and nothing could be grepped or eyeballed down a column.
            print('   %s (%s)' % (mid, md.get('name', '')))
            for n in sorted(pal):
                v, why = verdict(n, pal, res, zones, live=live)
                print('      %-26s %-12s %s' % (n, v, why))
            uni = game_universe(game, doc)
            gap = [d for d, b in offered(game)
                   if verdict(b, pal, res, zones, live=live)[0] == 'ABSENT'
                   and b in uni]
            if gap:
                print('      %d offered weapon(s) ABSENT from this map: %s'
                      % (len(gap), ', '.join(gap)))
            if a.both and game in HP._MAP_EQUIPMENT:
                print('      -- equipment --')
                ready = _equipment_rows(m, game)
                print('      %d of %d abilit(ies) ready without a rebuild'
                      % (ready, len(_REACH_ABILITIES)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
