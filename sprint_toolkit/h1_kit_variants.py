r"""Create Halo 1 weapon-clone actor variants as EDITING-KIT tags (HCEEK\tags).

Adding a tag to a built MCC map crashed the level (2026-10-02, h1_variants.add_tags),
so clones are made where tags are SUPPOSED to be added: as .actor_variant files in the
kit, which the user puts in the scenario's Actor Palette in Sapien and builds with
tool.exe. Everything else stays proven map-side: the antr label teaching
(h1_teach_weapon.py) and the patcher's card/colour lookups (a clone is named
'<source>~<weapon>', see h1_variants.py).

Kit tag format (actv): 0x40-byte header ('actv' at 0x24, header size 0x40 at 0x2C,
'blam' at 0x3C), then the 0x238-byte struct BIG-ENDIAN, then the tail: the path of
every tagref with a non-zero length, in field order, NUL-terminated; then the Change
Colors elements (count at +0x22C, 0x20 each). A tagref in the struct is
group fourcc, junk pointer, path length, -1.

Per clone: the source variant's struct; Weapon ref -> the new weapon; Major Variant
ref -> the clone of the source's major; the firing block (0x74-0x15F, 0x1D8-0x1E3)
from the donor -- the most similar variant in the whole game that already carries the
weapon (h1_variants.find_donors, read off the built maps), its minor for the minor
clone and its major for the major clone, taken from the donor's own KIT tag.

    python h1_kit_variants.py --source "characters\grunt\grunt minor plasma pistol" --weapon "weapons\assault rifle\assault rifle"
    (add --dry-run to only print the plan)
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import halo_patch as hp  # noqa: E402
import h1_variants as hv  # noqa: E402

KIT_TAGS = r"F:\SteamLibrary\steamapps\common\HCEEK\tags"
HDR, SIZE = 0x40, 0x238
REFS = (0x04, 0x14, 0x24, 0x64, 0x1C0)          # Actor Def, Unit, Major, Weapon, Equipment
GROUPS = {0x04: b'actr', 0x14: b'unit', 0x24: b'actv', 0x64: b'weap', 0x1C0: b'eqip'}


def tag_file(path):
    return os.path.join(KIT_TAGS, path + '.actor_variant')


def read(path):
    """-> (header, struct bytearray, {ref offset: path}, change-colour elements)"""
    raw = open(tag_file(path), 'rb').read()
    head, body = raw[:HDR], bytearray(raw[HDR:HDR + SIZE])
    pos = HDR + SIZE
    refs = {}
    for o in REFS:
        n = struct.unpack_from('>i', body, o + 8)[0]
        if n > 0:
            refs[o] = raw[pos:pos + n].decode('latin-1')
            pos += n + 1
    cc = struct.unpack_from('>i', body, 0x22C)[0]
    colours = raw[pos:pos + cc * 0x20]
    return head, body, refs, colours


def write(path, head, body, refs, colours):
    body = bytearray(body)
    tail = b''
    for o in REFS:
        p = refs.get(o)
        if p:
            struct.pack_into('>i', body, o + 8, len(p))
            struct.pack_into('>i', body, o + 0xC, -1)
            tail += p.encode('latin-1') + b'\0'
        else:
            struct.pack_into('>i', body, o + 8, 0)
    struct.pack_into('>i', body, 0x22C, len(colours) // 0x20)
    out = tag_file(path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(head + bytes(body) + tail + colours)
    return out


def make_clone(source, weapon, donor, major_clone=None):
    """Build the clone of `source` carrying `weapon`, firing from kit tag `donor`."""
    head, body, refs, colours = read(source)
    _dh, dbody, _dr, _dc = read(donor)
    for lo, hi in hv.FIRING:
        body[lo:hi] = dbody[lo:hi]
    refs[0x64] = weapon
    body[0x64:0x68] = GROUPS[0x64]
    if major_clone:
        refs[0x24] = major_clone
        body[0x24:0x28] = GROUPS[0x24]
    name = source + hv.CLONE_SEP + weapon.rsplit(chr(92), 1)[-1]
    return name, (head, body, refs, colours)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, help='kit path of the variant to clone (no extension)')
    ap.add_argument('--weapon', required=True, help='kit path of the weapon tag (no extension)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    if not os.path.exists(os.path.join(KIT_TAGS, a.weapon + '.weapon')):
        sys.exit('no such weapon in the kit: ' + a.weapon)
    _h, sbody, srefs, _c = read(a.source)
    # the donor search reads the BUILT maps (the whole game), comparing against the
    # source as the maps carry it
    m = None
    for lvl in hv.LEVELS:
        p = os.path.join(hv.MAPS, lvl + '.map')
        mm = hp.open_map(p, 'Halo 1') if os.path.exists(p) else None
        if mm is not None and dict(mm.find_tags('actv', a.source)):
            m = mm
            break
    if m is None:
        sys.exit('the source variant is on no built level, so it cannot be compared')
    lb = dict(m.find_tags('actv', a.source))[a.source]
    ranked = hv.find_donors(a.weapon, hv._ref_name(m, lb, hv.REF_UNIT), hv._floats(m, lb, hv.TRAITS))
    for score, lvl, name, _u, maj, _a, _b in ranked[:6]:
        print('  %.3f  %-4s %-55s major=%s' % (score, lvl, name, (maj or '-').split(chr(92))[-1]))
    if not ranked:
        sys.exit('no variant in the game carries ' + a.weapon)
    _s, _lvl, dminor, _u, dmajor, _x, _y = ranked[0]
    print('donor: %s / %s' % (dminor, dmajor or '(no major: minor reused)'))

    major_src = srefs.get(0x24)
    written = []
    major_clone = None
    if major_src:
        major_clone, data = make_clone(major_src, a.weapon, dmajor or dminor)
        written.append((major_clone, data))
    minor_clone, data = make_clone(a.source, a.weapon, dminor, major_clone)
    written.append((minor_clone, data))
    for name, data in written:
        if a.dry_run:
            print('would write', tag_file(name))
        else:
            print('wrote', write(name, *data))


if __name__ == '__main__':
    main()
