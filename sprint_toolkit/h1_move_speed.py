r"""Halo 1 enemy ground speed: read and scale the root motion of move-* animations (2026-10-03).

Halo 1 has no ground-speed field for AI. Each antr animation carries a Frame Info buffer
of UNCOMPRESSED per-frame floats -- the root motion the base node was stripped of:

  Animations  +0x74  elem 0xB4   Name ascii +0x0, Frame Count i16 +0x22,
                                 Frame Info Type enum16 +0x26, Frame Info data ref +0x48
  Frame Info Type  0 none / 1 dx,dy (8 B/frame) / 2 dx,dy,dyaw (12) / 3 dx,dy,dz,dyaw (16)

Every enemy move-* animation is type 1, and its speed is sum(dx, dy) / frames * 30 wu/s
(Elite stand move-front 2.25 wu over 26 frames = 2.60 wu/s). Scaling multiplies dx and dy
of every frame (dz and dyaw untouched), so the leg cycle is unchanged -- a x2 enemy
should cover twice the ground with sliding feet, IF the engine moves AI by this data.
That is what the b30 test (h1_move_speed_test.cmd) decides.

A buffer two animations share is scaled once (keyed by file offset).

    python h1_move_speed.py --map <map> --show [--antr "*grunt*"]
    python h1_move_speed.py --map <in> --out <out> --mult 2 --antr "characters\*" \
        --skip "*cyborg*" --skip "*marine*" [--paint "grunt minor=00FF00"]
"""
import argparse
import fnmatch
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch as hp  # noqa: E402
import halo3_reload as hr  # noqa: E402

# The readers and the scaler live in halo3_reload (the Movement Speed cards use them).
move_anims = hr.h1_move_anims
speed = hr.h1_move_speed


def _pick(m, globs, skips):
    out = []
    for p, b in m.find_tags('antr', '*'):
        pl = p.lower()
        if any(fnmatch.fnmatch(pl, g.lower()) for g in globs) and \
                not any(fnmatch.fnmatch(pl, s.lower()) for s in skips):
            out.append((p, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--out')
    ap.add_argument('--antr', action='append', default=None,
                    help='antr tag path glob (repeatable), default "characters\\*"')
    ap.add_argument('--skip', action='append', default=[], help='antr glob to leave alone')
    ap.add_argument('--mult', type=float)
    ap.add_argument('--paint', action='append', default=[],
                    help='load-proof control: "<enemy_colors row>=RRGGBB", slot 0')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()
    m = hp.open_map(a.map, 'Halo 1')
    tags = _pick(m, a.antr or ['characters' + chr(92) + '*'], a.skip)
    if not tags:
        sys.exit('no antr matches')
    done = set()
    for p, b in tags:
        print(p)
        for nm, fc, it, size, off in move_anims(m, b):
            if not a.show and a.mult and off is not None and off not in done:
                per = hr.H1_INFO_SIZES[it] if 0 <= it < len(hr.H1_INFO_SIZES) else 0
                for i in range(min(fc, size // per) if per else 0):
                    dx, dy = struct.unpack_from('<2f', m.data, off + i * per)
                    struct.pack_into('<2f', m.data, off + i * per, dx * a.mult, dy * a.mult)
                done.add(off)
            sx, sy, v = speed(m, fc, it, size, off)
            print('   %-36s fc=%3d type=%d  dx=%7.3f dy=%7.3f  %5.2f wu/s' % (nm, fc, it, sx, sy, v))
    if a.show:
        return
    if not a.mult or a.mult <= 0:
        sys.exit('--mult is required to write')
    if a.paint:
        import enemy_colors as ec
        ov = {}
        for spec in a.paint:
            row, col = spec.rsplit('=', 1)
            ov[row.strip()] = {'0': col.strip()}
        for r in ec.apply(m, 'Halo 1', ov):
            print('paint:', r.get('field'), r.get('new') or r.get('reason'))
    print('scaled %d frame-info buffer(s) x%g' % (len(done), a.mult))
    if not a.out:
        sys.exit('--out is required to write')
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()
