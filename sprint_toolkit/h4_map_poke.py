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
PP_GRAPH = r'objects\characters\storm_fp\weapons\pistol\fp_plasma_pistol\storm_fp_plasma_pistol'
PORT_BEAM = r'objects\weapons\rifle\focus_rifle\projectiles\focus_rifle_beam'
BR_PROJ_FX = r'objects\weapons\rifle\storm_beam_rifle\fx\projectile'
FP_TRACER = r'objects\weapons\pistol\storm_sentinel_beam\fx\friendly_beam\projectile_1p'

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
    ap.add_argument('--fp-offset', metavar='X,Y,Z',
                    help='first person projectile offset: +x forward, +y left, +z up')
    ap.add_argument('--no-overheat-shake', action='store_true',
                    help='null the overheated damage effect (camera shake + rumble)')
    ap.add_argument('--graph-pp', action='store_true',
                    help='fp animations -> the Plasma Pistol graph (diagnostic)')
    ap.add_argument('--graph-back', action='store_true',
                    help='fp animations back to the Beam Rifle graph')
    ap.add_argument('--streak-back', action='store_true',
                    help='projectile attachment back to the Beam Rifle streak')
    ap.add_argument('--fp-tracer', action='store_true',
                    help='the original beam tracer: set "draw in first person pass"')
    ap.add_argument('--weapon-origin', action='store_true',
                    help='barrel flag: projectiles come out of the gun, not the camera')
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
    if not (a.fix or a.swap_fp or a.unswap or a.model_flags or a.beam_test or
            a.weapon_origin or a.fp_tracer or a.graph_back or a.streak_back or
            a.no_overheat_shake or a.graph_pp or a.fp_offset):
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
    if a.fp_offset:
        # each barrel's "First Person Offset" block (weap.xml: barrel +0x100, 0xC per
        # point, +x forward, +z up, +y left) -- where the beam spawns in first person.
        # The block needs an element already (the kit build adds one).
        x, y, z = (float(v) for v in a.fp_offset.split(','))
        count, ptr = struct.unpack_from('<iI', d, pb + 0x518)
        first = m.data2off(ptr)
        for i in range(count):
            n, p2 = struct.unpack_from('<iI', d, first + i * 0x190 + 0x100)
            if not n:
                raise SystemExit('barrel %d has no first person offset element -- rebuild first' % i)
            at = m.data2off(p2)
            was = struct.unpack_from('<3f', d, at)
            struct.pack_into('<3f', d, at, x, y, z)
            print('barrel %d first person offset %s -> %s' % (i, ','.join('%g' % v for v in was), a.fp_offset))
    if a.no_overheat_shake:
        # weap 0x330 "Overheated Damage Effect" tagRef -> null. The Sentinel base names
        # globals\damage_responses	rigger_overheat: a CAMERA SHAKE + rumble on overheat --
        # the whole-view jerk the user still felt (boot 13) after every animation seam was
        # closed. The Beam Rifle leaves this field empty.
        was = struct.unpack_from('<I', d, pb + 0x330 + 0xC)[0]
        struct.pack_into('<I', d, pb + 0x330 + 0xC, 0xFFFFFFFF)
        print('overheated damage effect datum %08x -> null' % was)
    if a.graph_pp:
        # fp animations -> the PLASMA PISTOL's graph: its overheat chain is used all the
        # time in normal play. One-frame pop at ~52%% heat gone -> the Beam Rifle chain's
        # state handling; still there -> something on the port's weapon tag (boot 14).
        g = next((t for t in m.tags if t['class'] == 'jmad' and t['name'] == PP_GRAPH), None)
        if g is None:
            raise SystemExit('the Plasma Pistol fp graph is not in this map')
        pf = fp_element(m, pb)
        struct.pack_into('<I', d, pf + 0x10 + 0xC, g['ident'])
        print('fp animations -> %s' % PP_GRAPH)
    if a.graph_back:
        # fp animations -> the Beam Rifle's own graph (First Person +0x10): does the
        # port's re-exported graph cause the freeze after the overheat jerk (boot 12)?
        pf, bf = fp_element(m, pb), fp_element(m, bb)
        d[pf + 0x10:pf + 0x20] = d[bf + 0x10:bf + 0x20]
        print('fp animations -> the Beam Rifle graph')
    if a.streak_back:
        # the port projectile's attachment (proj.xml Attachments 0x118, 0x20 each, Type
        # tagRef +0x0) -> the Beam Rifle's projectile effect, the thin streak that DREW
        # (boot 10). The unpinned Sentinel tracer drew nothing (boot 12).
        own = m.find_tags('proj', PORT_BEAM)[0][1]
        brfx = next(t for t in m.tags if t['class'] == 'effe' and t['name'] == BR_PROJ_FX)
        count, ptr = struct.unpack_from('<iI', d, own + 0x118)
        el = m.data2off(ptr)
        # pick the EFFECT attachment by its group -- element 0 of the port's projectile
        # is the Sentinel's looping fire SOUND (lsnd); a blind index once wrote an effect
        # datum under an lsnd group
        hits = [el + i * 0x20 for i in range(count) if bytes(d[el + i * 0x20:el + i * 0x20 + 4])[::-1] == b'effe']
        if len(hits) != 1:
            raise SystemExit('expected one effect attachment, found %d' % len(hits))
        struct.pack_into('<I', d, hits[0] + 0xC, brfx['ident'])
        print('projectile attachment -> %s (%d attachment(s))' % (BR_PROJ_FX, count))
    if a.fp_tracer:
        # The Sentinel's (= the Focus Rifle's converted) first-person beam tracer carries
        # only "point-to-point" (flags u32 at +0x0, bit 0; measured: 1 on both Sentinel
        # tracers, 0 on the Beam Rifle's streak). Bit 1 is "draw in first person pass
        # (dangerous)" -- without it a tracer is not drawn in first person at all, which
        # is why the original beam never showed for the player (boots 2-8).
        tr = m.find_tags('trac', FP_TRACER)
        if not tr:
            raise SystemExit('no %s in this map' % FP_TRACER)
        tb = tr[0][1]
        was = struct.unpack_from('<I', d, tb)[0]
        struct.pack_into('<I', d, tb, was | 0x2)
        print('fp tracer flags %#x -> %#x' % (was, was | 0x2))
    if a.weapon_origin:
        # Barrel flags (+0x0) bit 2 "Projectiles Use Weapon Origin": "instead of coming
        # out of the magic first person camera origin, the projectiles for this weapon
        # actually come out of the gun". From the camera, the beam's projectile streak
        # flies straight away from the eye -- seen end-on, "visible only when I move"
        # (boot 10). From the gun it is seen from the side.
        count, ptr = struct.unpack_from('<iI', d, pb + 0x518)
        first = m.data2off(ptr)
        for i in range(count):
            at = first + i * 0x190
            was = struct.unpack_from('<I', d, at)[0]
            struct.pack_into('<I', d, at, was | 0x4)
            print('barrel %d flags %#x -> %#x' % (i, was, was | 0x4))
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
