r"""Teach a Halo 1 character to wield a weapon its animations do not cover (2026-10-02).

Measured on b30: an actor variant (actv) given a weapon whose LABEL its biped's
animation graph (antr) does not list spawns with the biped's default weapon instead
(grunt + assault rifle -> plasma pistol). The weapon's label (weap +0x30C: 'ar', 'pr',
'pp', ...) is looked up among the antr's Weapon Types, and the weapon class that owns
the matching type supplies the animations.

So teaching is an antr edit: under every unit (stance) and weapon class that carries a
DONOR label (e.g. 'pr', the plasma rifle), append a Weapon Types element that is the
donor's verbatim copy with the label renamed to the new one ('ar'). The copy keeps the
donor's Animations reflexive pointing at the donor's index array -- read-only data, so
sharing it is fine -- which means the new weapon animates exactly like the donor.

antr layout (Halo1 plugin antr.xml):
  UNITS          +0x0C  elem 0x64   Label ascii +0x0
    Weapons      +0x58  elem 0xBC   Name ascii +0x0
      Weapon Types +0xB0 elem 0x3C  Label ascii +0x0, Animations reflexive +0x30

    python h1_teach_weapon.py --map <in.map> --out <out.map> --antr "*grunt*" --donor pr --label ar
    python h1_teach_weapon.py --map <map> --antr "*grunt*" --show
"""
import argparse
import fnmatch
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch as hp  # noqa: E402

UNITS, UNIT_SZ = 0x0C, 0x64
WEAPONS, WEAPON_SZ = 0x58, 0xBC
TYPES, TYPE_SZ = 0xB0, 0x3C


def _ascii(m, off, n=0x20):
    return bytes(m.data[off:off + n]).split(b'\0')[0].decode('latin-1')


def _elems(m, at, size):
    n = m.u32(at)
    if not n or n > 10000:
        return []
    base = (m.u32(at + 4) - m.magic) & 0xFFFFFFFF
    return [base + i * size for i in range(n)]


def walk(m, antr_base):
    """[(unit label, unit off, class name, class off, [type labels])]"""
    out = []
    for u in _elems(m, antr_base + UNITS, UNIT_SZ):
        for w in _elems(m, u + WEAPONS, WEAPON_SZ):
            labs = [_ascii(m, t) for t in _elems(m, w + TYPES, TYPE_SZ)]
            out.append((_ascii(m, u), u, _ascii(m, w), w, labs))
    return out


def teach(m, antr_base, donor, label):
    """Append a `label` Weapon Type, copied from `donor`, under every class with the
    donor and without the label already. Returns the number of classes taught."""
    n = 0
    for _ul, _u, _cn, w, labs in walk(m, antr_base):
        if donor not in labs or label in labs:
            continue
        src = _elems(m, w + TYPES, TYPE_SZ)[labs.index(donor)]
        elem = bytearray(m.data[src:src + TYPE_SZ])
        elem[0:0x20] = label.encode('latin-1').ljust(0x20, b'\0')
        m.grow_block(w, TYPES, TYPE_SZ, [bytes(elem)])
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--out')
    ap.add_argument('--antr', required=True, help='antr tag path glob, e.g. "*grunt*"')
    ap.add_argument('--donor', default='pr')
    ap.add_argument('--label', default='ar')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()
    m = hp.open_map(a.map, 'Halo 1')
    tags = [(p, b) for p, b in m.find_tags('antr', '*') if fnmatch.fnmatch(p.lower(), a.antr.lower())]
    if not tags:
        sys.exit('no antr matches %s' % a.antr)
    for p, b in tags:
        print(p)
        if not a.show:
            print('  taught %r (copy of %r) in %d weapon class(es)'
                  % (a.label, a.donor, teach(m, b, a.donor, a.label)))
        for ul, _u, cn, _w, labs in walk(m, b):
            print('   unit %-24s class %-12s types %s' % (ul, cn, labs))
    if not a.show:
        if not a.out:
            sys.exit('--out is required to write')
        m.save(a.out)
        print('written:', a.out)


if __name__ == '__main__':
    main()
