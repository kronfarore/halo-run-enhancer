"""Depth-first walker/locator for Halo 1 loose (HEK) tag files.

H1 loose tags have NO offset table: block element arrays and their pooled tagRef
path strings / dataref blobs are laid out depth-first after the 64-byte header,
and every reflexive/tagRef/dataref pointer in the file is 0 (rebuilt at load). So
the only way to find a block's data is to walk the whole structure, driven by the
Assembly plugin, reading counts/lengths BIG-ENDIAN.

Format (decoded 2026-07-25, see memory halo1-sprint-from-scratch):
  header      64 bytes; struct data starts at 0x40; no total-size field.
  root struct baseSize bytes; SAME field offsets as the cache plugin.
  reflexive   [count: BE int32][ptr: 0]  in the containing struct.
  tagRef      class(4) + ptr(0) + pathlen(BE int32 @+8) + id(0xFFFFFFFF); the
              path string is pooled in the depth-first stream.
  dataref     size(BE int32 @+0) ... ; `size` bytes pooled in the stream.
  layout      for a block: [all `count` element structs][then, per element in
              order, each pointered field's data in offset order, recursively].

This module LOCATES root blocks; insertion builds on it.
"""
import struct
import xml.etree.ElementTree as ET

HEADER = 0x40


def be32(d, o):
    return struct.unpack_from('>i', d, o)[0]


def _parse_block(node):
    """{elem_size, fields:[(offset, kind, child_def_or_None)]} sorted by offset,
    kind in {'block','tagref','dataref'}."""
    es = node.get('elementSize')
    elem_size = int(es, 16) if es else 0
    fields = []
    for ch in node:
        t = ch.tag.lower()
        off = ch.get('offset')
        if off is None:
            continue
        o = int(off, 16)
        if t in ('tagblock', 'reflexive', 'struct'):
            fields.append((o, 'block', _parse_block(ch)))
        elif t in ('tagref', 'tag_reference'):
            fields.append((o, 'tagref', None))
        elif t == 'dataref':
            fields.append((o, 'dataref', None))
    fields.sort(key=lambda f: f[0])
    return {'elem_size': elem_size, 'fields': fields}


def parse_plugin(path):
    root = ET.parse(path).getroot()
    bs = root.get('baseSize')
    b = _parse_block(root)
    b['elem_size'] = int(bs, 16) if bs else b['elem_size']
    return b


def _walk(d, array_base, count, bdef, pos, root_hits=None):
    """Advance `pos` (child-data cursor) past this block's child data. The element
    array [array_base, array_base+count*elem_size) is already placed. Returns the
    new cursor. If root_hits is a dict, records {field_offset: (child_array, count)}
    for the top-level element (i == 0 of the root)."""
    es = bdef['elem_size']
    for i in range(count):
        elem = array_base + i * es
        for (o, kind, child) in bdef['fields']:
            if kind == 'block':
                cc = be32(d, elem + o)
                child_array = pos
                pos = child_array + cc * child['elem_size']
                pos = _walk(d, child_array, cc, child, pos)
                if root_hits is not None and i == 0:
                    # Record AFTER recursion: pos is now the block's pool_end
                    # (start of the next sibling's data). (array, count, es, pool_end)
                    root_hits[o] = (child_array, cc, child['elem_size'], pos)
            elif kind == 'tagref':
                pl = be32(d, elem + o + 8)            # pooled path string...
                if pl:
                    pos += pl + 1                     # ...pathlen excludes the null; add it
            elif kind == 'dataref':
                pos += be32(d, elem + o)              # pooled data blob
    return pos


def locate_root_blocks(data, plugin_path):
    """Return {root_field_offset: (array_offset, count, elem_size, pool_end)} for
    every root tagblock, by walking the whole tag depth-first. pool_end is the file
    offset just past this block's element array AND its pooled child data (i.e. the
    start of the next sibling block's data) — where a new element's path is appended."""
    bdef = parse_plugin(plugin_path)
    hits = {}
    _walk(data, HEADER, 1, bdef, HEADER + bdef['elem_size'], root_hits=hits)
    return hits


# --- insertion ----------------------------------------------------------------
# All integers in the tag STRUCTURE are big-endian; a tagRef is class(4) + ptr(0)
# + pathlen(BE, excludes null) + id(0xFFFFFFFF), with the path string pooled
# (pathlen+1 bytes, null-terminated) after the block's element array.
PROFILE_OFF = 0x348    # Player Starting Profile (elem 0x68: Name@0, Primary weap@0x28)
PALETTE_OFF = 0x27C    # Weapon Palette          (elem 0x30: Name weap@0)
EQUIP_PALETTE_OFF = 0x264   # Equipment Palette   (elem 0x30: Name eqip@0)
OBJECT_NAMES_OFF = 0x204    # Object Names        (elem 0x24: Name@0, Type@0x20, Place@0x22)
EQUIPMENT_OFF = 0x258       # Equipment placed    (elem 0x28: Pal@0, Name@2, Flags@4, Pos@8)
PLAYER_START_OFF = 0x354    # Player Starting Locations (elem 0x34: Position@0)

# Player-usable weapon tags, split by the H1 remastered restriction: adding a
# HUMAN weapon to a map forces a CLASSIC-graphics build; alien (Covenant) weapons
# build fine remastered. So there are two palette sets.
# ONLY weapons the player can normally use — i.e. the Enhancer's H1 pool (halo.json
# Missions Halo 1). Weapons outside this (energy sword, plasma_cannon, fuel rod =
# H2/H3 tags) lack proper H1 CLASSIC assets and corrupt the map's graphics; excluded.
HUMAN_WEAPONS = [
    'weapons\\assault rifle\\assault rifle', 'weapons\\flamethrower\\flamethrower',
    'weapons\\pistol\\pistol', 'weapons\\rocket launcher\\rocket launcher',
    'weapons\\shotgun\\shotgun', 'weapons\\sniper rifle\\sniper rifle',
]
ALIEN_WEAPONS = [
    'weapons\\needler\\needler', 'weapons\\plasma pistol\\plasma pistol',
    'weapons\\plasma rifle\\plasma rifle',
]
# Standard powerups only (present in campaign, so they have classic+remastered art).
EQUIPMENT = [
    'powerups\\active camouflage', 'powerups\\over shield', 'powerups\\health pack',
]


def _tagref(cls, path):
    """A 16-byte in-struct tagRef. path='' => empty ref (pathlen 0), class kept."""
    return cls + b'\x00\x00\x00\x00' + struct.pack('>I', len(path)) + b'\xff\xff\xff\xff'


def make_profile(name, primary_weapon):
    """A 0x68 Player Starting Profile element: Name, Primary Weapon tagRef, empty
    Secondary; everything else zero. Matches Guerilla's sprint_profile byte-for-byte."""
    e = bytearray(0x68)
    nb = name.encode('latin1')
    e[0:len(nb)] = nb
    e[0x28:0x38] = _tagref(b'weap', primary_weapon)
    e[0x3C:0x4C] = _tagref(b'weap', '')          # empty secondary (as Guerilla writes)
    return bytes(e)


def make_palette(cls, path):
    """A 0x30 palette element: a single tagRef (weap/eqip), rest zero."""
    e = bytearray(0x30)
    e[0:0x10] = _tagref(cls, path)
    return bytes(e)


def read_block_paths(data, plugin_path, root_offset, tagref_off=0):
    """The tagRef paths of a single-tagRef-per-element block (palettes), read from
    the pooled strings in element order. Used to avoid inserting duplicates."""
    info = locate_root_blocks(data, plugin_path).get(root_offset)
    if info is None:
        return []
    array, count, es, _ = info
    pool = array + count * es
    out = []
    for i in range(count):
        pl = be32(data, array + i * es + tagref_off + 8)
        if pl:
            out.append(bytes(data[pool:pool + pl]).decode('latin1'))
            pool += pl + 1
        else:
            out.append('')
    return out


def add_palette_entries(data, plugin_path, root_offset, cls, paths):
    """Append each of `paths` to a palette block, skipping any already present.
    Returns the list actually added."""
    have = set(read_block_paths(data, plugin_path, root_offset))
    added = []
    for p in paths:
        if p in have:
            continue
        insert_block_element(data, plugin_path, root_offset, make_palette(cls, p), p)
        have.add(p)
        added.append(p)
    return added


def insert_block_element(data, plugin_path, root_offset, elem, path):
    """Append `elem` to the root block at `root_offset`, pooling `path` (its tagRef
    path, or None) at the block's pool end, and bump the block's BE count. `data`
    is a bytearray, edited in place. Re-walks each call, so multiple inserts compose."""
    info = locate_root_blocks(data, plugin_path).get(root_offset)
    if info is None:
        raise ValueError('root block 0x%X not found' % root_offset)
    array, count, es, pool_end = info
    array_end = array + count * es
    # Pool the path FIRST (higher offset), then splice the element (lower offset),
    # so the element insert shifts the fresh path to just past the (shifted) pool.
    if path:
        data[pool_end:pool_end] = path.encode('latin1') + b'\x00'
    data[array_end:array_end] = elem
    o = HEADER + root_offset
    struct.pack_into('>i', data, o, be32(data, o) + 1)


SPRINT_WEAPON = 'weapons\\sprint\\sprint'


def profile_names(data, plugin_path):
    """Names of the Player Starting Profile elements (read from the element structs)."""
    info = locate_root_blocks(data, plugin_path).get(PROFILE_OFF)
    if not info:
        return []
    array, count, es, _ = info
    return [bytes(data[array + i * es:array + i * es + 32]).split(b'\x00')[0].decode('latin1')
            for i in range(count)]


def add_sprint(data, plugin_path):
    """Insert the sprint_profile Player Starting Profile. That alone is enough:
    the script gives the sprint weapon via player_add_equipment sprint_profile, and
    the profile's Primary Weapon tagRef pulls the weapon tag into the build — no
    Weapon Palette entry needed (verified: profile-only build includes the weapon).
    Idempotent: skips if a sprint_profile already exists (e.g. Guerilla-edited b30)."""
    if 'sprint_profile' in profile_names(data, plugin_path):
        return
    insert_block_element(data, plugin_path, PROFILE_OFF,
                         make_profile('sprint_profile', SPRINT_WEAPON), SPRINT_WEAPON)


CAMO_TAG = 'powerups\\active camouflage'
CAMO_OBJECT_NAME = 'camo_ability'    # our inserted, non-auto-spawning pickup


def _block(data, plugin_path, off):
    info = locate_root_blocks(data, plugin_path).get(off)
    if info is None:
        raise ValueError('root block 0x%X not found' % off)
    return info


def object_names(data, plugin_path):
    """Names in the Object Names block, in index order."""
    array, count, es, _ = _block(data, plugin_path, OBJECT_NAMES_OFF)
    return [bytes(data[array + i * es:array + i * es + 32]).split(b'\x00')[0].decode('latin1')
            for i in range(count)]


def make_object_name(name, otype, placement_index):
    """A 0x24 Object Names element: Name[32], Type enum16 @0x20, Placement Index @0x22.
    All scalars big-endian, as everywhere in a loose tag."""
    e = bytearray(0x24)
    nb = name.encode('latin1')[:31]
    e[0:len(nb)] = nb
    struct.pack_into('>h', e, 0x20, otype)
    struct.pack_into('>h', e, 0x22, placement_index)
    return bytes(e)


def make_equipment_placement(pal_index, name_index, pos, flags=1, bsp_flags=0x0):
    """A 0x28 Equipment placement. flags bit0 = "Not Automatically", so the pickup does
    NOT spawn at level load and only appears when a script object_creates it.
    BSP flags are 0 to match every stock placement in the campaign scenarios (the
    editor leaves them clear and the engine resolves the BSP from the position)."""
    e = bytearray(0x28)
    struct.pack_into('>h', e, 0x00, pal_index)
    struct.pack_into('>h', e, 0x02, name_index)
    struct.pack_into('>H', e, 0x04, flags)
    struct.pack_into('>fff', e, 0x08, *pos)
    struct.pack_into('>H', e, 0x20, bsp_flags)
    struct.pack_into('>H', e, 0x22, 1)          # Initially At Rest (doesn't fall)
    return bytes(e)


def find_placement(data, plugin_path, block_off, palette_off, tag_substr):
    """Index of the first placement in `block_off` whose palette tag contains
    `tag_substr`, or None. Placement elem: Palette Index (BE int16) @0x0."""
    pal = read_block_paths(data, plugin_path, palette_off)
    array, count, es, _ = _block(data, plugin_path, block_off)
    for i in range(count):
        pi = struct.unpack_from('>h', data, array + i * es)[0]
        if 0 <= pi < len(pal) and tag_substr in pal[pi]:
            return i
    return None


def name_placement(data, plugin_path, block_off, placement_index, otype, name):
    """Give an EXISTING placement an object name so scripts can address it. Inserts the
    Object Names element first, then re-locates the placement block (the insert shifts
    everything after it) and writes the placement's Name Index."""
    if name in object_names(data, plugin_path):
        return False
    name_index = _block(data, plugin_path, OBJECT_NAMES_OFF)[1]
    insert_block_element(data, plugin_path, OBJECT_NAMES_OFF,
                         make_object_name(name, otype, placement_index), None)
    array, _, es, _ = _block(data, plugin_path, block_off)
    struct.pack_into('>h', data, array + placement_index * es + 0x02, name_index)
    return True


def player_start_position(data, plugin_path):
    """Position of the first Player Starting Location -- a spot guaranteed to be inside
    the level, used as the camo pickup's nominal home before it is attached."""
    array, count, es, _ = _block(data, plugin_path, PLAYER_START_OFF)
    if not count:
        return (0.0, 0.0, 0.0)
    return struct.unpack_from('>fff', data, array)


def add_camo_ability(data, plugin_path):
    """Insert a NAMED, non-auto-spawning active-camouflage pickup so a script can
    `object_create camo_ability` and attach it to a player, granting the REAL equipment
    camo (which has a genuine 45s duration) instead of the permanent cheat camo.
    Idempotent. Returns True if it inserted anything."""
    if CAMO_OBJECT_NAME in object_names(data, plugin_path):
        return False
    add_palette_entries(data, plugin_path, EQUIP_PALETTE_OFF, b'eqip', [CAMO_TAG])
    pal = read_block_paths(data, plugin_path, EQUIP_PALETTE_OFF)
    pal_index = pal.index(CAMO_TAG)
    # The two blocks cross-reference by index, and each new element lands at the end,
    # so both indices are the counts taken BEFORE inserting.
    placement_index = _block(data, plugin_path, EQUIPMENT_OFF)[1]
    name_index = _block(data, plugin_path, OBJECT_NAMES_OFF)[1]
    pos = player_start_position(data, plugin_path)
    insert_block_element(data, plugin_path, EQUIPMENT_OFF,
                         make_equipment_placement(pal_index, name_index, pos), None)
    insert_block_element(data, plugin_path, OBJECT_NAMES_OFF,
                         make_object_name(CAMO_OBJECT_NAME, 3, placement_index), None)
    return True


def outfit(data, plugin_path, alien_only=False):
    """Full map outfit for the sprint mod pack: sprint_profile + every player weapon
    (alien-only when `alien_only`, else human+alien) + every equipment powerup, added
    to the palettes with de-duplication. `alien_only` builds REMASTERED; the full set
    (human weapons) must build CLASSIC. Returns (weapons_added, equipment_added)."""
    add_sprint(data, plugin_path)
    weapons = ALIEN_WEAPONS if alien_only else (HUMAN_WEAPONS + ALIEN_WEAPONS)
    w = add_palette_entries(data, plugin_path, PALETTE_OFF, b'weap', weapons)
    e = add_palette_entries(data, plugin_path, EQUIP_PALETTE_OFF, b'eqip', EQUIPMENT)
    return w, e


if __name__ == '__main__':
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import paths  # install paths — edit paths.py
    HCEEK = paths.HCEEK
    SCNR = paths.SCNR_XML
    labels = {0x27C: 'Weapon Palette', 0x348: 'Player Starting Profile',
              0x264: 'Equipment Palette', 0x270: 'Weapons(placed)'}

    def tagpath(name):
        return f'{HCEEK}\\tags\\levels\\{name}\\{name}.scenario'

    def show(name):
        hits = locate_root_blocks(open(tagpath(name), 'rb').read(), SCNR)
        for off, lab in labels.items():
            info = hits.get(off)
            print('  %-24s @0x%03X -> array 0x%s count %s'
                  % (lab, off, ('%X' % info[0]) if info else '----',
                     info[1] if info else '?'))

    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    if cmd == 'insert':
        # insert <map> [sprint|all|alien]  — edits <map>.scenario (backs up .presprint).
        #   sprint = sprint_profile only; all = + human&alien weapons + equipment
        #   (build CLASSIC); alien = + alien weapons only + equipment (build REMASTERED)
        import os
        import shutil
        name = sys.argv[2]
        mode = sys.argv[3] if len(sys.argv) > 3 else 'sprint'
        p = tagpath(name)
        bak = p + '.presprint'
        if not os.path.exists(bak):
            shutil.copy2(p, bak)
            print('backed up ->', bak)
        data = bytearray(open(bak, 'rb').read())     # always start from pristine
        print('before:'); show(name)
        if mode == 'sprint':
            add_sprint(data, SCNR)
        else:
            w, e = outfit(data, SCNR, alien_only=(mode == 'alien'))
            print('added %d weapon(s), %d equipment' % (len(w), len(e)))
        open(p, 'wb').write(data)
        print('after (%d -> %d bytes):' % (os.path.getsize(bak), len(data)))
        show(name)
    else:                                  # show <map> block locations (default b30)
        name = sys.argv[2] if len(sys.argv) > 2 else 'b30'
        print('%s.scenario block locations:' % name)
        show(name)
