r"""Poke the H4 port's weapon fields straight into a BUILT Halo 4 map -- no rebuild.

A rebuild costs a build-cache-file run per experiment. The fields being tested sit at
fixed offsets in the built weapon tag (Assembly's Halo4MCC/weap.xml), so they can be
written into the installed map directly, tested, and only then made permanent in the
kit tags (h4_make_port_weapon.py) for the next real build.

    python h4_map_poke.py                 report: the port's fields beside the Beam Rifle's
    python h4_map_poke.py --fix           the NPC-gun leftovers -> the Beam Rifle's values
    python h4_map_poke.py --swap-fp       ALSO point the fp model at the Beam Rifle's
                                          render model (model fault vs weapon-tag fault)
    python h4_map_poke.py --map <path>    another map (default: installed m30_cryptum)

Offsets, weap (Halo4MCC/weap.xml):
    0x1C  object flags, bit 8 "Extension Of Parent" ("object uses parent's markers")
    0x20  bounding radius        0x24  bounding offset (3 floats)
    0x4B4 weapon class (string id)   0x4B8 weapon name (string id)
    0x4D4 First Person block (element 0x28): +0x00 fp model tagRef, +0x10 fp animations
    0x5EC weapon ready 1st person animation playback scale
Class and name are COPIED from the Beam Rifle's tag in the same map, so no string id has
to be looked up. Restore: copy the map back from H4EK\maps (the build output).
Uses the enhancer's map reader read-only; edits nothing of the enhancer.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch                                              # noqa: E402

MAP = (r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
       r'\halo4\maps\m30_cryptum.map')
PORT = r'objects\weapons\rifle\focus_rifle\focus_rifle'
BEAM = r'objects\weapons\rifle\storm_beam_rifle\storm_beam_rifle'

FLAGS, RADIUS, OFFSET = 0x1C, 0x20, 0x24
CLASS, NAME, FP, READY = 0x4B4, 0x4B8, 0x4D4, 0x5EC
EXT_OF_PARENT = 1 << 8


def fp_element(m, base):
    count, ptr = struct.unpack_from('<iI', m.data, base + FP)
    return m.data2off(ptr) if count else None


def report(m, base, label):
    d = m.data
    flags = struct.unpack_from('<I', d, base + FLAGS)[0]
    fp = fp_element(m, base)
    print('%-12s ext-of-parent %-5s radius %-6g offset %-22s ready %-4g class %08x name %08x'
          % (label, bool(flags & EXT_OF_PARENT), struct.unpack_from('<f', d, base + RADIUS)[0],
             ','.join('%g' % v for v in struct.unpack_from('<3f', d, base + OFFSET)),
             struct.unpack_from('<f', d, base + READY)[0],
             struct.unpack_from('<I', d, base + CLASS)[0],
             struct.unpack_from('<I', d, base + NAME)[0]))
    if fp is not None:
        print('%-12s fp model datum %08x  fp anims datum %08x'
              % ('', struct.unpack_from('<I', d, fp + 0xC)[0],
                 struct.unpack_from('<I', d, fp + 0x1C)[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', default=MAP)
    ap.add_argument('--fix', action='store_true')
    ap.add_argument('--swap-fp', action='store_true')
    ap.add_argument('--beam-test', action='store_true',
                    help='barrel 0 fires the Beam Rifle projectile + firing effect')
    ap.add_argument('--unswap', action='store_true',
                    help='point the fp model back at the own render model of the port')
    ap.add_argument('--model-flags', action='store_true',
                    help='render model 0x64 bit 5: do not use compressed vertex positions')
    a = ap.parse_args()

    m = halo_patch.open_map(a.map, 'Halo 4')
    port = m.find_tags('weap', PORT)
    beam = m.find_tags('weap', BEAM)
    if not port or not beam:
        raise SystemExit('not in this map: %s' % ('the port' if not port else 'the Beam Rifle'))
    pb, bb = port[0][1], beam[0][1]
    report(m, pb, 'focus rifle')
    report(m, bb, 'beam rifle')
    if not (a.fix or a.swap_fp or a.unswap or a.model_flags or a.beam_test):
        return

    d = m.data
    if a.fix:
        flags = struct.unpack_from('<I', d, pb + FLAGS)[0]
        struct.pack_into('<I', d, pb + FLAGS, flags & ~EXT_OF_PARENT)
        d[pb + RADIUS:pb + RADIUS + 16] = d[bb + RADIUS:bb + RADIUS + 16]   # radius + offset
        d[pb + CLASS:pb + CLASS + 8] = d[bb + CLASS:bb + CLASS + 8]         # class + name
        struct.pack_into('<f', d, pb + READY, struct.unpack_from('<f', d, bb + READY)[0])
    if a.swap_fp:
        pf, bf = fp_element(m, pb), fp_element(m, bb)
        d[pf:pf + 0x10] = d[bf:bf + 0x10]                                   # fp model tagRef
    if a.beam_test:
        # Barrel 0 (right trigger) fires the BEAM RIFLE's projectile with the Beam Rifle's
        # firing effect -- a beam known to draw from a player's weapon. Beam seen: the
        # port's weapon + model can show one, and the Sentinel's 1p tracer is the fault.
        # Not seen: something on the port blocks effects. weap.xml: Barrels 0x518
        # (0x190 each), Projectile +0x110, Firing Effects +0x184 (0xF4), effect +0x4.
        def barrel0(base):
            count, ptr = struct.unpack_from('<iI', d, base + 0x518)
            return m.data2off(ptr)
        pb0, bb0 = barrel0(pb), barrel0(bb)
        d[pb0 + 0x110:pb0 + 0x120] = d[bb0 + 0x110:bb0 + 0x120]
        pfx = m.data2off(struct.unpack_from('<I', d, pb0 + 0x184 + 4)[0])
        bfx = m.data2off(struct.unpack_from('<I', d, bb0 + 0x184 + 4)[0])
        d[pfx + 0x4:pfx + 0x14] = d[bfx + 0x4:bfx + 0x14]
        print('barrel 0: Beam Rifle projectile + firing effect')
    if a.unswap:
        own = next(t for t in m.tags if t['class'] == 'mode' and t['name'] == PORT)
        pf = fp_element(m, pb)
        struct.pack_into('<I', d, pf + 0xC, own['ident'])
    if a.model_flags:
        # The port's MESH stores raw positions (mesh flag 256 "doesn't use compressed
        # position") while its geometry flags (0x64) say nothing about it -- 4, budgets
        # only. The Beam Rifle's geometry carries 36 = budgets + bit 5 "Don't Use
        # Compressed Vertex Positions". Swap test (boot 7): the Beam Rifle's model DRAWS
        # in first person on the port's weapon, so the fault is in the port's model.
        mb = m.find_tags('mode', PORT)[0][1]
        was = struct.unpack_from('<I', d, mb + 0x64)[0]
        struct.pack_into('<I', d, mb + 0x64, was | 0x20)
        print('render model flags %d -> %d' % (was, was | 0x20))
    print('\nafter:')
    report(m, pb, 'focus rifle')
    m.save()
    print('saved %s' % a.map)


if __name__ == '__main__':
    main()
