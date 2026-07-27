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
