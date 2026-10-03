r"""Halo 2 enemy ground speed: read and scale the root motion of move animations (2026-10-03).

Halo 2 keeps an animation's root motion OUTSIDE its codec data, as plain floats, and the
built campaign maps (uncompressed) carry it in the tag data itself:

  jmad Animations  +0x2C  elem 0x60   Name stringId +0x0, Frame Info Type u8 +0x11,
                                      Frame Count i16 +0x14, Resource dataref +0x28
                                      (size i32, pointer -> p2o),
                                      data sizes +0x30: u8 static flags, u8 animated
                                      flags, i16 movement, i16 pill, i16 default,
                                      i32 uncompressed (0 when built), i32 compressed
  blob: [default][compressed][static flags][animated flags][MOVEMENT][pill][uncompressed]
  Frame Info Type 1 dx,dy (8 B/frame) / 2 dx,dy,dyaw (12) / 3 dx,dy,dz,dyaw (16)

The sizes sum to the dataref size on every root-motion animation of all 14 campaign maps.
Several animations can share one movement block, so a block is scaled once (by offset).
Scaling multiplies dx and dy only. Halo 1's equivalent was confirmed in game on b30.

Test-only options (the 03a test): --swap-char FROM=TO remaps squads and starting
locations from one Character Palette index to another and gives them --swap-weapon;
--shield-mult scales the player's Maximum Shield Vitality; --paint colours an
enemy_colors row as a load-proof control.

    python h2_move_speed.py --map <map> --show [--jmad "*elite*"]
    python h2_move_speed.py --map <in> --out <out> --mult 2 --jmad "objects\characters\elite\elite" ...
"""
import argparse
import fnmatch
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo2_map as h2  # noqa: E402

ANIMS, ANIM_SZ = 0x2C, 0x60
PER = (0, 8, 12, 16)
FPS = 30.0


def move_anims(m, base):
    """[(name, info type, frames, movement file offset, movement bytes)] for every
    animation whose name holds `move_` and that carries root motion -- runs, strafes,
    the idle<->move transitions and the Drone's flight moves."""
    out = []
    for el in m.follow_all(base, [ANIMS], [ANIM_SZ], 'all'):
        fit = m.data[el + 0x11]
        if not (0 < fit < 4):
            continue
        nm = m.resolve_stringid(m.u32(el)) or ''
        if 'move_' not in nm or 'aim_move' in nm:
            continue
        fc = struct.unpack_from('<h', m.data, el + 0x14)[0]
        rsize, rptr = struct.unpack_from('<iI', m.data, el + 0x28)
        sf, af, mv, pill, dflt, unc, cmp = struct.unpack_from('<BBhhhii', m.data, el + 0x30)
        if (fc < 1 or mv != PER[fit] * fc or rsize <= 0
                or sf + af + mv + pill + dflt + unc + cmp != rsize):
            continue                     # layout not as measured: never write blind
        out.append((nm, fit, fc, m.p2o(rptr) + dflt + cmp + sf + af, mv))
    return out


def speed(m, fit, fc, off, size):
    per = PER[fit]
    sx = sum(struct.unpack_from('<f', m.data, off + i * per)[0] for i in range(fc))
    sy = sum(struct.unpack_from('<f', m.data, off + i * per + 4)[0] for i in range(fc))
    return sx, sy, (sx * sx + sy * sy) ** 0.5 / fc * FPS


def scale(m, fit, fc, off, mult):
    per = PER[fit]
    for i in range(fc):
        dx, dy = struct.unpack_from('<2f', m.data, off + i * per)
        struct.pack_into('<2f', m.data, off + i * per, dx * mult, dy * mult)


def swap_char(m, src, dst, weapon):
    """Squads and starting locations on palette index `src` -> `dst`, weapon -> `weapon`."""
    s = m.scenario_tag()['base']
    n = 0
    for sq in m.follow_all(s, [0x160], [0x74], 'all'):
        sq_hit = struct.unpack_from('<h', m.data, sq + 0x36)[0] == src
        if sq_hit:
            struct.pack_into('<h', m.data, sq + 0x36, dst)
            struct.pack_into('<h', m.data, sq + 0x3C, weapon)
            n += 1
        for loc in m.follow_all(sq, [0x48], [0x64], 'all'):
            ch, w1 = struct.unpack_from('<hh', m.data, loc + 0x20)
            if ch == src:
                struct.pack_into('<hh', m.data, loc + 0x20, dst, weapon)
                n += 1
            elif ch == -1 and sq_hit and w1 != -1:
                struct.pack_into('<h', m.data, loc + 0x22, weapon)   # inherits the swap
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--out')
    ap.add_argument('--jmad', action='append', default=None, help='jmad path glob (repeatable)')
    ap.add_argument('--mult', type=float)
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--swap-char', action='append', default=[], help='palette FROM=TO')
    ap.add_argument('--swap-weapon', type=int, default=-1)
    ap.add_argument('--shield-mult', type=float)
    ap.add_argument('--paint', action='append', default=[], help='"<enemy_colors row>=RRGGBB"')
    a = ap.parse_args()
    m = h2.Halo2Map(a.map)
    globs = [g.lower() for g in (a.jmad or ['objects\\characters\\*'])]
    done = set()
    for t in m.tags_of_class('jmad'):
        name = (t['name'] or '').lower()
        if t['base'] is None or not any(fnmatch.fnmatch(name, g) for g in globs):
            continue
        rows = move_anims(m, t['base'])
        if not rows:
            continue
        print(t['name'])
        for nm, fit, fc, off, size in rows:
            if not a.show and a.mult and off not in done:
                scale(m, fit, fc, off, a.mult)
                done.add(off)
            if nm.endswith('move_front') or ':move_front:var' in nm:
                sx, sy, v = speed(m, fit, fc, off, size)
                print('   %-40s f=%3d type=%d  %5.2f wu/s' % (nm, fc, fit, v))
    if a.show:
        return
    for spec in a.swap_char:
        src, dst = (int(x) for x in spec.split('='))
        print('swap palette %d -> %d (weapon %d): %d squad/location writes'
              % (src, dst, a.swap_weapon, swap_char(m, src, dst, a.swap_weapon)))
    if a.shield_mult:
        import halo_map as hm
        import assembly_plugins as apl
        pl = hm.Plugin(os.path.join(apl.plugins_dir(), 'Halo2MCC', 'hlmt.xml'))
        for path in ('objects\\characters\\masterchief\\masterchief',
                     'objects\\characters\\dervish\\dervish'):
            for _p, base in m.find_tags('hlmt', path):
                old = m.read_tag_field(base, 'Maximum Shield Vitality', pl, 'New Damage Info')
                m.write_tag_field(base, 'Maximum Shield Vitality', old * a.shield_mult, pl,
                                  'New Damage Info')
                print('shield %s: %s -> %s' % (path, old,
                      m.read_tag_field(base, 'Maximum Shield Vitality', pl, 'New Damage Info')))
    if a.paint:
        import enemy_colors as ec
        ov = {}
        for spec in a.paint:
            row, col = spec.rsplit('=', 1)
            ov[row.strip()] = {'0': col.strip()}
        for r in ec.apply(m, 'Halo 2', ov):
            print('paint:', r.get('field'), r.get('new') or r.get('reason'))
    print('scaled %d movement block(s) x%g' % (len(done), a.mult or 0))
    if not a.out:
        sys.exit('--out is required to write')
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()
