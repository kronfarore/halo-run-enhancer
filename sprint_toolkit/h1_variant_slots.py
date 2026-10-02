r"""Halo 1 actor-variant SLOTS: placeholder actv tags the patcher fills at patch time.

Why (user, 2026-10-02): a weapon clone has to be a real tag BUILT into the level
(adding one to a finished map crashed it), but building one per enemy x weapon --
future ports included -- does not scale. So each level carries SLOTS_PER_LEVEL generic
actor variants, inserted once into its Actor Palette in Guerilla and built in; the
patcher then overwrites a slot's values with a clone's (proven route: the kit-built
'grunt minor plasma pistol with assault rifle' held, fired and dropped ARs).

A slot is a full 0x238-byte actv plus room for SLOT_COLOURS Change Colors elements
(the most any shipped variant uses is 1). It starts as a copy of
'characters\grunt\grunt minor plasma pistol' -- small, valid build dependencies --
with no Major Variant. A clone takes one slot, and a second for its major.

    python h1_variant_slots.py make            -> writes the 20 kit tags
    python h1_variant_slots.py fill --map M --out O --slot 1 --source S --weapon W [--major-slot 2] [--share 0.5]
        (fill: copy the clone's values into a slot of a BUILT map, then move a share
         of the source's spawns onto it; the patcher will do this itself later)
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import halo_patch as hp  # noqa: E402
import h1_kit_variants as kit  # noqa: E402
import h1_variants as hv  # noqa: E402

SLOTS_PER_LEVEL = 20
SLOT_COLOURS = 2
SLOT_DIR = 'characters\\enhancer'
SLOT_BASE = 'characters\\grunt\\grunt minor plasma pistol'


def slot_path(i):
    return '%s\\slot %02d' % (SLOT_DIR, i)


def make():
    head, body, refs, _colours = kit.read(SLOT_BASE)
    refs.pop(0x24, None)                         # no Major Variant
    colours = bytes(SLOT_COLOURS * 0x20)         # room; the count is set when filled
    for i in range(1, SLOTS_PER_LEVEL + 1):
        print('wrote', kit.write(slot_path(i), head, body, dict(refs), colours))


# ----------------------------------------------------------------------------- fill
def _slot_base(m, i):
    return dict(m.find_tags('actv', slot_path(i))).get(slot_path(i))


def fill_slot(m, slot, src_base, weref, donor=None, major_ref=None):
    """Overwrite slot tag `slot` (index) with the source variant's values, the new
    weapon, the donor's firing block and (optionally) a major-variant ref. The slot
    keeps its own Change Colors storage; up to SLOT_COLOURS source colours go in."""
    sb = _slot_base(m, slot)
    if sb is None:
        raise SystemExit('this map has no %s' % slot_path(slot))
    keep = bytes(m.data[sb + hv.CHANGE_COLORS:sb + hv.CHANGE_COLORS + 12])   # its block
    data = bytearray(m.data[src_base:src_base + hv.ACTV_SIZE])
    data[hv.REF_WEAPON:hv.REF_WEAPON + 16] = weref
    if donor is not None:
        for lo, hi in hv.FIRING:
            data[lo:hi] = donor[lo:hi]
    if major_ref is not None:
        data[hv.REF_MAJOR:hv.REF_MAJOR + 16] = major_ref
    else:
        data[hv.REF_MAJOR:hv.REF_MAJOR + 16] = b'vtca' + b'\0' * 8 + b'\xff' * 4
    n = min(m.u32(src_base + hv.CHANGE_COLORS), SLOT_COLOURS)
    data[hv.CHANGE_COLORS:hv.CHANGE_COLORS + 12] = keep
    struct.pack_into('<I', data, hv.CHANGE_COLORS, n)
    if n:
        src = (m.u32(src_base + hv.CHANGE_COLORS + 4) - m.magic) & 0xFFFFFFFF
        dst = (m.u32(sb + hv.CHANGE_COLORS + 4) - m.magic) & 0xFFFFFFFF
        m.data[dst:dst + n * hv.CC_SZ] = m.data[src:src + n * hv.CC_SZ]
    m.data[sb:sb + hv.ACTV_SIZE] = data
    return sb


def slot_ref(m, slot):
    """A 16-byte actv tagref to slot `slot`."""
    ref = bytearray(16)
    ref[0:4] = b'vtca'
    struct.pack_into('<I', ref, 4, m.tag_name_ptr(('actv', slot_path(slot))))
    struct.pack_into('<I', ref, 0xC, m.tag_id(('actv', slot_path(slot))))
    return bytes(ref)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('make')
    f = sub.add_parser('fill')
    f.add_argument('--map', required=True)
    f.add_argument('--out', required=True)
    f.add_argument('--slot', type=int, required=True)
    f.add_argument('--major-slot', type=int)
    f.add_argument('--source', required=True)
    f.add_argument('--weapon', required=True)
    f.add_argument('--share', type=float, default=0.5)
    a = ap.parse_args()
    if a.cmd == 'make':
        make()
        return
    m = hp.open_map(a.map, 'Halo 1')
    tags = dict(m.find_tags('actv', '*'))
    sb = tags[a.source]
    weref = hv._weapon_ref(m, a.weapon)
    if weref is None:
        raise SystemExit('this level has no ' + a.weapon)
    ranked = hv.find_donors(a.weapon, hv._ref_name(m, sb, hv.REF_UNIT), hv._floats(m, sb, hv.TRAITS))
    dmin = ranked[0][5] if ranked else None
    dmaj = (ranked[0][6] or dmin) if ranked else None
    print('donor:', ranked[0][2] if ranked else '(none: firing left as the source)')
    major_ref = None
    src_major = hv._ref_name(m, sb, hv.REF_MAJOR)
    if a.major_slot and src_major in tags:
        fill_slot(m, a.major_slot, tags[src_major], weref, dmaj)
        major_ref = slot_ref(m, a.major_slot)
        print('slot %02d <- %s + %s' % (a.major_slot, src_major.split(chr(92))[-1], a.weapon.split(chr(92))[-1]))
    fill_slot(m, a.slot, sb, weref, dmin, major_ref)
    print('slot %02d <- %s + %s' % (a.slot, a.source.split(chr(92))[-1], a.weapon.split(chr(92))[-1]))
    moved, of = hv.repoint_share(m, a.source, m.tag_id(('actv', slot_path(a.slot))), slot_path(a.slot), a.share)
    print('%d of %d spawns -> slot %02d' % (moved, of, a.slot))
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()
