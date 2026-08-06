r"""Insertion into Halo 2 loose (H2EK) tag files -- the H2 counterpart of h1_loosetag.py.

WHY THIS EXISTS. The H2 ability plumbing used to patch the BUILT cache, which meant
`(object_create X)` and `(unit_add_equipment ... X)` could only name things the
scenario already declared: the compiler resolves those to an INDEX at compile time, so
a name appended to the cache is invisible. Every level therefore had to BORROW a spare
object name and a spare starting profile -- and 03b had no spare profile at all and had
to take "respawn profile", which only survives because solo play never touches it.

Editing the SCENARIO TAG before build-cache-file removes the whole problem, exactly as
Halo 1 does it: the name exists when the scripts compile, so nothing is borrowed and
every level gets the SAME script stub.

FORMAT (decoded 2026-08-06 against the 13 campaign scenarios; see memory
halo2-loose-tag-format). Unlike Halo 1's loose tags -- no offset table, everything
big-endian, walk-or-die -- the H2 format is SELF-DESCRIBING and little-endian:

  header      0x40 bytes; class magic (reversed 4CC) at 0x24; root chunk at 0x40.
  chunk       16 bytes: 'dfbt' + version + count + elementSize, then count*elementSize
              bytes of element array, then this block's child data, depth-first and
              contiguous. The root struct is 0x5C4 bytes at 0x50.
  tagblock    12 bytes IN-STRUCT: count, address(0), definition(0). The cache packs
              the same field into 8, which is the ONLY reason loose and cache root
              offsets differ -- see _loose() below.
  tagref      16 bytes: class (reversed 4CC), pointer(0), path length (LE, EXCLUDING
              the null), datum id (0xFFFFFFFF). The path itself is pooled null-
              terminated after the element array, in element order. An empty ref
              (length 0) pools nothing.
  count       stored TWICE -- in the chunk header AND in the parent struct's tagblock
              field. Both must be bumped or tool.exe reads a truncated block.

CAVEAT: a block with count 0 emits NO chunk header at all, so inserting into an empty
block means CREATING one at the right depth-first position. 08b_deltacontrol is the
only campaign mission with no equipment at all; see insert_element().
"""
import os
import struct

SIG = b'dfbt'
HEADER = 0x40
ROOT = 0x50                 # root struct data begins here (after the root chunk header)
CHUNK = 0x10                # chunk header size


def _loose(cache_off):
    """Cache root offset -> loose root offset.

    Every scnr root field from Object Names onward is a tagblock, 8 bytes in the cache
    and 12 in the tag, so the two layouts drift by 4 per preceding block. Anchored on
    Object Names (cache 0x48 -> loose 0x74); it independently predicts the equipment
    palette at 0xD4 and the profiles at 0x17C, both of which were then confirmed by
    searching all 13 scenarios for the block whose count matches.
    """
    return 0x74 + ((cache_off - 0x48) // 8) * 0xC


OBJECT_NAMES, NES = _loose(0x48), 0x24     # Name[0x20], Type@0x20, Placement@0x22
EQUIPMENT, IES = _loose(0x80), 0x38        # Palette@0, Name@2, Flags@4, Position@8
EQUIP_PALETTE, PES = _loose(0x88), 0x30    # a single eqip tagref at 0
PROFILES, PRS = _loose(0xF8), 0x54         # Name[0x20], Primary@0x28, Secondary@0x3C
PLAYER_START, SES = _loose(0x100), 0x34    # Position@0

FLAG_NOT_AUTOMATICALLY = 0x1
FLAG_CREATE_AT_REST = 0x100
TYPE_EQUIPMENT = 3

CAMO_TAG = 'objects/powerups/active_camouflage/active_camouflage'.replace('/', chr(92))
TOKEN = 'objects/weapons/melee/unarmed/unarmed'.replace('/', chr(92))
# One pickup per player so co-op camo doesn't contend, mirroring H1's camo_ability0/1.
CAMO_OBJECT_NAMES = ('ab_camo0', 'ab_camo1')
SPRINT_PROFILE = 'ab_sprint'


# --- reading ------------------------------------------------------------------

def chunks(data):
    """Every chunk in file order, as (offset, version, count, elem_size). File order
    IS depth-first order, because blocks are laid out contiguously."""
    out = []
    i = data.find(SIG)
    while i >= 0:
        ver, cnt, es = struct.unpack_from('<III', data, i + 4)
        out.append((i, ver, cnt, es))
        i = data.find(SIG, i + 4)
    return out


def root_count(data, root_off):
    return struct.unpack_from('<I', data, ROOT + root_off)[0]


def _set_root_count(data, root_off, value):
    struct.pack_into('<I', data, ROOT + root_off, value)


def _printable_names(data, chunk, count, elem_size, limit=6):
    """True if the block's elements start with a plausible C string -- the cheap
    discriminator between Object Names / Profiles and same-sized numeric blocks.

    Must never look past element `count`: the pooled tagref paths sit immediately
    after the array and are themselves printable, so an over-long scan reports a
    false PASS on a short block and a false FAIL on one whose pool is elsewhere."""
    base = chunk + CHUNK
    for i in range(min(limit, count)):
        s = data[base + i * elem_size:base + i * elem_size + 0x20].split(b'\x00')[0]
        if not s or not all(32 <= c < 127 for c in s):
            return False
    return True


def _tagref_class(data, off):
    return bytes(data[off:off + 4])[::-1]


# Per-block validators. Several blocks share an element size (three different blocks
# are 0x24), so count alone is ambiguous; these pin it down.
_VALIDATE = {
    OBJECT_NAMES: lambda d, c, n: _printable_names(d, c, n, NES),
    PROFILES: lambda d, c, n: _printable_names(d, c, n, PRS),
    EQUIP_PALETTE: lambda d, c, n: _tagref_class(d, c + CHUNK) == b'eqip',
}


def locate(data, root_off, elem_size, after=0):
    """The chunk offset for a root block, or None when the block is empty (count 0,
    which emits no chunk at all). Candidates must match BOTH the count recorded in the
    root struct and the element size; where that is still ambiguous a validator picks
    the real one, and `after` enforces depth-first ordering against an already-located
    earlier block."""
    n = root_count(data, root_off)
    if n == 0:
        return None
    ok = _VALIDATE.get(root_off)
    hits = [c[0] for c in chunks(data)
            if c[2] == n and c[3] == elem_size and c[0] > after
            and (ok is None or ok(data, c[0], n))]
    if not hits:
        raise ValueError('no chunk for root+0x%X (count=%d, elem=0x%X)'
                         % (root_off, n, elem_size))
    return hits[0]


def elements(data, root_off, elem_size):
    """(index, absolute offset) for each element of a root block."""
    c = locate(data, root_off, elem_size)
    if c is None:
        return []
    n = root_count(data, root_off)
    return [(i, c + CHUNK + i * elem_size) for i in range(n)]


def names_in(data, root_off, elem_size):
    return [bytes(data[o:o + 0x20]).split(b'\x00')[0].decode('latin-1')
            for _, o in elements(data, root_off, elem_size)]


def object_names(data):
    return names_in(data, OBJECT_NAMES, NES)


def profile_names(data):
    return names_in(data, PROFILES, PRS)


def player_start_position(data):
    els = elements(data, PLAYER_START, SES)
    if not els:
        raise ValueError('scenario has no player starting location')
    return struct.unpack_from('<fff', data, els[0][1])


def _pool_end(data, chunk, count, elem_size, tagref_offsets):
    """End of a block's pooled tagref strings -- where a new element's paths append.
    Empty refs (length 0) pool nothing, matching how the stock tags are written."""
    pos = chunk + CHUNK + count * elem_size
    for i in range(count):
        e = chunk + CHUNK + i * elem_size
        for t in tagref_offsets:
            pl = struct.unpack_from('<I', data, e + t + 8)[0]
            if pl:
                pos += pl + 1
    return pos


# --- writing ------------------------------------------------------------------

def make_tagref(cls, path):
    """A 16-byte in-struct tagref. path='' gives an empty ref, which pools nothing."""
    return cls + b'\x00\x00\x00\x00' + struct.pack('<I', len(path)) + b'\xff\xff\xff\xff'


def make_palette(path, cls=b'eqip'):
    e = bytearray(PES)
    e[0:0x10] = make_tagref(cls, path)
    return bytes(e)


def make_profile(name, primary=TOKEN, loaded=0, total=0, grenades=0):
    """A Player Starting Profile. The primary weapon tagref is what pulls the token
    weapon tag into the build, so no weapon palette entry is needed (same as H1)."""
    e = bytearray(PRS)
    nb = name.encode('latin-1')
    e[0:len(nb)] = nb
    e[0x28:0x38] = make_tagref(b'weap', primary)
    struct.pack_into('<hh', e, 0x38, loaded, total)
    e[0x3C:0x4C] = make_tagref(b'weap', '')      # empty secondary, as the stock tags write it
    struct.pack_into('<I', e, 0x50, grenades)
    return bytes(e)


# Placement blocks whose element size is unambiguous in every campaign scenario, used
# to pick a fresh unique ID. Unique IDs are MAP-WIDE, so scanning only the equipment
# block could collide with a scenery or vehicle id.
UNIQUE_ID = 0x28
_PLACEMENT_BLOCKS = ((_loose(0x50), 0x60),      # scenery
                     (_loose(0x60), 0x54),      # vehicles
                     (EQUIPMENT, IES))


def max_unique_id(data):
    """Highest placement unique id in use. Only the LOW 16 bits are the counter -- the
    high word is a per-object tag id that stock placements keep -- so that is what gets
    compared and incremented."""
    top = 0
    for off, es in _PLACEMENT_BLOCKS:
        try:
            for _, o in elements(data, off, es):
                top = max(top, struct.unpack_from('<I', data, o + UNIQUE_ID)[0] & 0xFFFF)
        except ValueError:
            continue        # block we cannot resolve unambiguously; the others suffice
    return top


def make_object_name(name, otype=TYPE_EQUIPMENT, placement=-1):
    e = bytearray(NES)
    nb = name.encode('latin-1')
    e[0:len(nb)] = nb
    struct.pack_into('<hh', e, 0x20, otype, placement)
    return bytes(e)


def child_run(data, chunk, count, elem_size):
    """(run_length, region_end) for a block whose elements carry inline structs, or
    (0, array_end) when they do not.

    Some blocks emit a fixed run of 16-byte struct DESCRIPTORS per element after the
    element array -- equipment placements emit three (`sobj`, `obj#`, `seqt`), 48 bytes,
    byte-identical for every element. Appending an element without appending its run
    leaves the descriptors one short: tool.exe then loads the block but the new
    placement is not a real object, and the script compiler rejects the name pointing
    at it with "this is not a valid object name". Cost us a build to find.

    The run length is recovered as the repeat period of the region, which needs at
    least two elements to measure -- with one or none there is nothing to copy from.
    """
    array_end = chunk + CHUNK + count * elem_size
    if count < 2 or bytes(data[array_end:array_end + 4]) == SIG:
        return 0, array_end
    head = bytes(data[array_end:array_end + CHUNK])
    # The run must START with a chunk signature. Without this, a block whose elements
    # pool tagref STRINGS reports a bogus run: the repeating period of path text
    # ("objects\weapons\...") looks exactly like a repeating descriptor to a plain
    # byte-period search, and the palette and the profiles both tripped it.
    if not all(97 <= b <= 122 or 48 <= b <= 57 for b in head[:4]):
        return 0, array_end
    nxt = data.find(head, array_end + 1)
    if nxt < 0:
        return 0, array_end
    run = nxt - array_end
    region_end = array_end + count * run
    # Only trust it if every run really is that same block.
    if bytes(data[region_end - run:region_end - run + CHUNK]) != head:
        return 0, array_end
    return run, region_end


def insert_element(data, root_off, elem_size, elem, paths=(), tagref_offsets=()):
    """Append one element to a root block. `paths` are the new element's pooled tagref
    strings in field order. Bumps the count in BOTH the chunk header and the root
    struct. `data` is a bytearray, edited in place; re-locates each call, so repeated
    inserts compose."""
    n = root_count(data, root_off)
    chunk = locate(data, root_off, elem_size)
    if chunk is None:
        raise NotImplementedError(
            'root+0x%X is empty in this scenario, so it has no chunk header to extend. '
            'Creating one means placing it at the right depth-first position; only '
            '08b_deltacontrol needs this (it ships no equipment at all).' % root_off)
    array_end = chunk + CHUNK + n * elem_size
    pool_end = _pool_end(data, chunk, n, elem_size, tagref_offsets)
    # Pooled strings and per-element descriptor runs are alternatives, never both, so
    # a block with tagrefs is never asked for a child run.
    run, region_end = ((0, array_end) if tagref_offsets
                       else child_run(data, chunk, n, elem_size))

    # Edit from the HIGHEST offset down, so each splice leaves the offsets below it
    # untouched: the per-element struct descriptors, then the pooled tagref strings,
    # then the element itself.
    if run:
        data[region_end:region_end] = bytes(data[region_end - run:region_end])
    for p in paths:
        if p:
            data[pool_end:pool_end] = p.encode('latin-1') + b'\x00'
    data[array_end:array_end] = elem

    struct.pack_into('<I', data, chunk + 8, n + 1)     # chunk header count
    _set_root_count(data, root_off, n + 1)
    return n                                            # index of the new element


# --- the two things the Run Enhancer needs ------------------------------------

def add_sprint_profile(data, name=SPRINT_PROFILE):
    """Insert the sprint starting profile. Idempotent."""
    if name in profile_names(data):
        return False
    insert_element(data, PROFILES, PRS, make_profile(name),
                   paths=(TOKEN, ''), tagref_offsets=(0x28, 0x3C))
    return True


def _palette_paths(data):
    c = locate(data, EQUIP_PALETTE, PES)
    if c is None:
        return []
    n = root_count(data, EQUIP_PALETTE)
    pool = c + CHUNK + n * PES
    out = []
    for i in range(n):
        pl = struct.unpack_from('<I', data, c + CHUNK + i * PES + 8)[0]
        out.append(bytes(data[pool:pool + pl]).decode('latin-1') if pl else '')
        pool += pl + 1 if pl else 0
    return out


def add_camo_palette(data, tag=CAMO_TAG):
    """Ensure the camo eqip tag is in the Equipment palette; returns its index."""
    have = _palette_paths(data)
    if tag in have:
        return have.index(tag)
    return insert_element(data, EQUIP_PALETTE, PES, make_palette(tag),
                          paths=(tag,), tagref_offsets=(0x0,))


def add_camo_ability(data, names=CAMO_OBJECT_NAMES, offset=(0.0, 0.0, 0.5)):
    """Insert the camo pickups: palette entry, one NON-auto-spawning placement per
    player, and an Object Name for each so (object_create ab_camo0) resolves.

    Non-auto because the script creates them on demand; CREATE_AT_REST so they don't
    settle under gravity. Placement bytes are copied from an existing equipment
    placement so every field we don't understand keeps a known-good value -- the same
    precaution h2_place_equipment.py takes on the cache side."""
    added = []
    have = object_names(data)
    if all(n in have for n in names):
        return added
    pal = add_camo_palette(data)
    at = player_start_position(data)
    pos = tuple(a + b for a, b in zip(at, offset))

    for nm in names:
        if nm in object_names(data):
            continue
        chunk = locate(data, EQUIPMENT, IES)
        if chunk is None:
            raise NotImplementedError(
                'this scenario has no equipment placements to copy from (08b)')
        n = root_count(data, EQUIPMENT)
        elem = bytearray(data[chunk + CHUNK:chunk + CHUNK + IES])   # copy element 0
        struct.pack_into('<hh', elem, 0x0, pal, len(object_names(data)))
        struct.pack_into('<I', elem, 0x4, FLAG_CREATE_AT_REST | FLAG_NOT_AUTOMATICALLY)
        struct.pack_into('<fff', elem, 0x8, *pos)
        # A fresh unique id. Copying element 0 verbatim left BOTH new pickups carrying
        # element 0's id, and a duplicate makes the placement unusable -- the script
        # compiler then rejects the name pointing at it with "this is not a valid
        # object name". Keep the copied high word, replace the low-16 counter.
        high = struct.unpack_from('<I', elem, UNIQUE_ID)[0] & 0xFFFF0000
        struct.pack_into('<I', elem, UNIQUE_ID, high | ((max_unique_id(data) + 1) & 0xFFFF))
        placement = insert_element(data, EQUIPMENT, IES, bytes(elem))
        insert_element(data, OBJECT_NAMES, NES,
                       make_object_name(nm, TYPE_EQUIPMENT, placement))
        added.append(nm)
    return added


def outfit(data):
    """Everything a mission scenario needs for the ability set. Idempotent."""
    return {'profile': add_sprint_profile(data), 'camo': add_camo_ability(data)}


# --- cli ----------------------------------------------------------------------

def _scenario(h2ek, level):
    return os.path.join(h2ek, 'tags', 'scenarios', 'solo', level, level + '.scenario')


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('scenario', help='path to a .scenario tag')
    ap.add_argument('--show', action='store_true', help='report the blocks and exit')
    ap.add_argument('--apply', action='store_true', help='insert profile + camo pickups')
    ap.add_argument('--out', help='write elsewhere instead of in place')
    a = ap.parse_args(argv)

    data = bytearray(open(a.scenario, 'rb').read())
    if a.apply:
        bak = a.scenario + '.preability'
        if not os.path.exists(bak) and not a.out:
            open(bak, 'wb').write(bytes(data))
            print('backed up -> %s' % os.path.basename(bak))
        r = outfit(data)
        print('profile inserted: %s   camo names inserted: %s'
              % (r['profile'], r['camo'] or 'none (already present)'))
        open(a.out or a.scenario, 'wb').write(bytes(data))
        print('wrote %s' % (a.out or a.scenario))
        return

    for label, off, es in (('object names', OBJECT_NAMES, NES),
                           ('equipment', EQUIPMENT, IES),
                           ('equip palette', EQUIP_PALETTE, PES),
                           ('profiles', PROFILES, PRS),
                           ('player starts', PLAYER_START, SES)):
        n = root_count(data, off)
        c = locate(data, off, es) if n else None
        print('  %-14s root+0x%-4X count=%-5d chunk=%s'
              % (label, off, n, ('0x%X' % c) if c else '(empty)'))
    print('  profiles      : %s' % ', '.join(profile_names(data)))
    print('  camo present  : %s' % [n for n in CAMO_OBJECT_NAMES if n in object_names(data)])


if __name__ == '__main__':
    main()
