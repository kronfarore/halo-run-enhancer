r"""A Halo 1 loaded-ammo readout in the ROCKET LAUNCHER's style, for any small magazine.

The Grunts' fuel rod never had a HUD (enemy-only). The user's call (2026-10-05): the
rocket launcher's meter instead of the Assault Rifle's bullet ticks. The RL readout is
`ui\hud\bitmaps\combined\hud_ammo_alphas` sequence 2 (a standalone 512x64 static sheet,
two rocket silhouettes) and `hud_ammo_meters` sequence 2 (a sprite, x 0..448 / y 120..192
of the shared 512x512 sheet). Both tags are COPIED whole -- every other sequence, every
sprite and its registration point untouched, so the copy places exactly like stock -- and
only that art is redrawn: N rockets at 1/2 scale where the RL has two.

Meter pixels: alpha = the silhouette, luminance = the tick's threshold over the WHOLE cell
(PORTING.md "Outlined ammo ticks": the threshold channel is a property of the cell, not
the tick, or spent ticks keep a lit rim). Thresholds and multiplier from ammo_meter.plan.

    python h1_rocket_meter.py 4 "weapons\fuel rod gun\bitmaps\fuel_rod_rockets"
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.bitm import bitm_def  # noqa: E402
import ammo_meter  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
COMB = os.path.join(TAGS, 'ui', 'hud', 'bitmaps', 'combined')
SEQ = 2                                    # the rocket launcher's sequence in both sheets


def _load(name):
    t = bitm_def.build(filepath=os.path.join(COMB, name + '.bitmap'))
    return t, t.data.tagdata


def _pixels(d, bi):
    bm = d.bitmaps.STEPTREE[bi]
    raw = bytes(d.processed_pixel_data.data)[bm.pixels_offset:
                                             bm.pixels_offset + bm.width * bm.height * 2]
    a = np.frombuffer(raw, np.uint8).reshape(bm.height, bm.width, 2).copy()
    return bm, a                                            # [..., 0] = L, [..., 1] = A


def _store(d, bi, arr):
    bm = d.bitmaps.STEPTREE[bi]
    blob = bytearray(d.processed_pixel_data.data)
    blob[bm.pixels_offset:bm.pixels_offset + arr.size] = arr.tobytes()
    d.processed_pixel_data.data = bytes(blob)


def _cells(alpha):
    """Column ranges of the two rocket silhouettes in a region (split at the widest gap)."""
    cols = np.where(alpha.max(axis=0) > 8)[0]
    gaps = np.diff(cols)
    cut = int(np.argmax(gaps))
    return (cols[0], cols[cut] + 1), (cols[cut + 1], cols[-1] + 1)


def redraw(region, n, meter):
    """region: (h, w, 2) LA pixels holding two rockets -> n rockets at half scale."""
    h, w, _ = region.shape
    (a0, a1), (b0, b1) = _cells(region[..., 1])
    pitch = (b0 - a0) / 2.0                                 # n half-size rockets, same pitch
    rows = np.where(region[:, a0:a1, 1].max(axis=1) > 8)[0]
    y0, y1 = rows[0], rows[-1] + 1
    one = Image.fromarray(np.ascontiguousarray(region[y0:y1, a0:a1, 1]))
    rw, rh = max(1, (a1 - a0) // 2), max(1, (y1 - y0) // 2)
    small = np.array(one.resize((rw, rh), Image.LANCZOS))
    out = np.zeros_like(region)
    top = y0 + ((y1 - y0) - rh) // 2
    step = ammo_meter.plan(n)[2]
    for k in range(n):
        x = int(round(a0 + k * pitch))
        sl = (slice(top, top + rh), slice(x, min(w, x + rw)))
        out[sl + (1,)] = np.maximum(out[sl + (1,)], small[:, :sl[1].stop - x])
        if not meter:
            out[sl + (0,)] = np.where(small[:, :sl[1].stop - x] > 0, 255, out[sl + (0,)])
    if meter:
        # the staircase over every pixel: cell k (k = 1..n) from its rocket's left edge on
        for x in range(w):
            k = min(n, max(1, int((x - a0) // pitch) + 1)) if x >= a0 else 1
            out[:, x, 0] = ammo_meter.threshold(k, n)
    return out


def h3_rod():
    """One rod of Halo 3's fuel rod meter (ballistic_meters #17: five rods stacked, alpha =
    the art), as an alpha array, plus the H3 rod pitch as a fraction of its height."""
    import h3_hud_art
    art, _reg = h3_hud_art.sprite('ballistic_meters', 17)
    a = np.array(art.split()[3])
    rows = a.max(axis=1) > 8
    bands, y = [], 0
    while y < len(rows):
        if rows[y]:
            y0 = y
            while y < len(rows) and rows[y]:
                y += 1
            bands.append((y0, y))
        y += 1
    y0, y1 = bands[0]
    cols = np.where(a[y0:y1].max(axis=0) > 8)[0]
    rod = a[y0:y1, cols[0]:cols[-1] + 1]
    pitch = (bands[1][0] - bands[0][0]) / float(y1 - y0) if len(bands) > 1 else 1.25
    return rod, pitch


def redraw_rods(region, n, meter):
    """The ORIGINAL fuel rod readout (user, 2026-10-06): Halo 3's rods, n of them stacked
    top to bottom like Halo 3 draws them, scaled to fill the region's height, left-aligned
    where the RL's first rocket starts. Halo 3 counts its thresholds down from the top,
    so the TOP rod has the highest threshold and goes out first."""
    h, w, _ = region.shape
    (a0, a1), _ = _cells(region[..., 1])
    # the frame is the RL rocket's own height in THIS sheet, so the static silhouettes and
    # the meter come out the same size, as the RL's two rockets do
    rows = np.where(region[:, a0:a1, 1].max(axis=1) > 8)[0]
    fy0, fy1 = rows[0], rows[-1] + 1
    rod, pitch = h3_rod()
    rh = max(2, int((fy1 - fy0) / (1 + (n - 1) * pitch)))
    rw = max(2, round(rod.shape[1] * rh / rod.shape[0]))
    small = np.array(Image.fromarray(rod).resize((rw, rh), Image.LANCZOS))
    step = rh * pitch
    top0 = fy0 + ((fy1 - fy0) - (rh + (n - 1) * step)) / 2.0
    out = np.zeros_like(region)
    for k in range(n):                       # k = 0 top
        y = int(round(top0 + k * step))
        sl = (slice(y, y + rh), slice(a0, a0 + rw))
        out[sl + (1,)] = np.maximum(out[sl + (1,)], small)
        if not meter:
            out[sl + (0,)] = np.where(small > 0, 255, out[sl + (0,)])
    if meter:
        for y in range(h):                   # every row belongs to its nearest rod
            k = min(n - 1, max(0, int(round((y - top0 - rh / 2.0) / step))))
            out[y, :, 0] = ammo_meter.threshold(n - k, n)
    return out


ART = {'rockets': redraw, 'h3_rods': redraw_rods}


def build(n, out_base, art='rockets'):
    redraw_fn = ART[art]
    written = []
    # static silhouettes: bitmap SEQ of hud_ammo_alphas, a standalone 512x64 sheet
    t, d = _load('hud_ammo_alphas')
    bi = d.sequences.STEPTREE[SEQ].first_bitmap_index
    bm, px = _pixels(d, bi)
    _store(d, bi, redraw_fn(px, n, meter=False))
    t.filepath = os.path.join(TAGS, out_base + '_alphas.bitmap')
    os.makedirs(os.path.dirname(t.filepath), exist_ok=True)
    t.serialize(temp=False, backup=False)
    written.append(t.filepath)
    # meter: sequence SEQ's sprite rectangle of the shared hud_ammo_meters sheet
    t, d = _load('hud_ammo_meters')
    sp = d.sequences.STEPTREE[SEQ].sprites.STEPTREE[0]
    bm, px = _pixels(d, sp.bitmap_index)
    x0, x1 = int(round(sp.left_side * bm.width)), int(round(sp.right_side * bm.width))
    y0, y1 = int(round(sp.top_side * bm.height)), int(round(sp.bottom_side * bm.height))
    px[y0:y1, x0:x1] = redraw_fn(px[y0:y1, x0:x1], n, meter=True)
    _store(d, sp.bitmap_index, px)
    t.filepath = os.path.join(TAGS, out_base + '_meters.bitmap')
    t.serialize(temp=False, backup=False)
    written.append(t.filepath)
    prev = Image.fromarray(np.concatenate([
        np.pad(_pixels(bitm_def.build(filepath=written[0]).data.tagdata, bi)[1][..., 1],
               ((0, 8), (0, 0))),
        px[y0:y1, :, 1], px[y0:y1, :, 0]], axis=0))
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    prev.save(os.path.join(HERE, 'out', '%s_meter_%d.png' % (art, n)))
    return written


if __name__ == '__main__':
    for p in build(int(sys.argv[1]), sys.argv[2], *sys.argv[3:4]):
        print(p)
    print('alpha_multiplier %d, alpha_bias 1, sequence %d' % (ammo_meter.plan(int(sys.argv[1]))[3], SEQ))
