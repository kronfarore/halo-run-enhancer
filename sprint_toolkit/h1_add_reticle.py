r"""Bring a Halo 3 reticle into Halo 1's `ui\hud\bitmaps\combined\hud_reticles` (HCEEK tag).

Halo 1 keeps every reticle as its own 256x256 a8y8 bitmap (luminance 255 = white, alpha =
the shape) behind one sequence, registered at (128, 125). A new reticle is APPENDED as a
bitmap + sequence copied from the PC fuel rod's (#15), so no stock index moves; a name
already present is replaced in place. It goes into `hud_reticles_r` at the SAME index
(h1_hud_sheet.py): written to the plain sheet only, the sword's reticle drew as a blue
square in game (2026-10-06).

SCALE. The same weapon's reticle in both games fixes it: the PC fuel rod's Halo 1 reticle
(#15) reaches 123 px from its centre, Halo 3's fuel rod reticle (hud_reticles #19) 97 px,
so Halo 3 art is drawn x123/97 = x1.27 in Halo 1's sheet (measured 2026-10-06). A weapon
HUD's crosshair element then points its overlay at the new sequence.

    python h1_add_reticle.py hud_reticles 13 "energy sword"
    python h1_add_reticle.py hud_reticles <h3 index> "smg" 19     # at the reserved index
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import h3_hud_art  # noqa: E402

TAG = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags',
                   'ui', 'hud', 'bitmaps', 'combined', 'hud_reticles.bitmap')
TEMPLATE_SEQ = 15            # the PC fuel rod's reticle
SIZE, CENTRE = 256, (128, 125)
SCALE = 123.0 / 97.0


def layer_art(src, index):
    """(RGBA, registration px) of a Halo 3 HUD piece: a sprite of a SHEET (`index` a number),
    or a whole single BITMAP (`index` None, registered at its centre: the Spartan Laser's
    `spartan_outerring`, one 100 px bitmap with no sequences)."""
    if index is None:
        img, _ = h3_hud_art.decode(src)
        return img, (img.width / 2.0, img.height / 2.0)
    return h3_hud_art.sprite(src, index)


def prefiltered(alpha, factor, gain=1.6):
    """The art as the SCREEN sees it (the Spartan Laser, test 2: unthickened Halo 3 strokes
    'fizzle out'): Halo 1 draws the reticle sheet at about half size with no mipmaps, so a 1-2
    texel stroke is undersampled and breaks up -- the reason earlier ports thickened (a max
    filter, which coarsens). Instead: area-averaged down by `factor` and back up, the alpha x
    `gain` -- each stroke becomes `factor` texels of anti-aliased coverage, continuous at the
    drawn size and as fine as the original."""
    w, h = alpha.size
    small = alpha.resize((w // factor, h // factor), Image.BOX)
    small = small.point(lambda v: min(255, int(round(v * gain))))
    return small.resize((w, h), Image.BILINEAR)


def pixel_doubled(alpha, factor=2, gamma=0.6):
    """The art as the SCREEN shows it, then each screen pixel a factor x factor BLOCK (the
    Spartan Laser, test 5: Halo 1 draws the reticle sheet at ~half size with no mipmaps, and
    any resampled art -- prefiltered, half size, Halo 3's size -- broke up or merged its 1 px
    ticks). Area-averaged down by `factor` (each texel = the screen pixel's coverage), thin
    lines brightened (alpha ** `gamma`), then up NEAREST: whichever texel of a block the
    unmipped minification samples, it reads the right screen pixel."""
    w, h = alpha.size
    small = alpha.resize((w // factor, h // factor), Image.BOX)
    small = small.point(lambda v: int(round(255 * (v / 255.0) ** gamma)))
    return small.resize((w, h), Image.NEAREST)


def hard_strokes(alpha, threshold=96, min_width=3):
    """HARD-EDGED strokes, only the THIN ones grown (the Spartan Laser, test 9's chart: MCC
    draws the reticle sheet at ~0.5 a texel, point-sampled at a non-integer scale -- a line
    under ~3 texels is MISSED at some points along a curve (the fizzle), a partial-alpha edge
    texel flickers; 2 px line pairs were the first to resolve). The art binarised at
    `threshold`; a stroke one 3 x 3 erosion removes (under 3 px) grown 1 px each side; the
    wider ones (Halo 3's 4 px ticks) and their gaps untouched."""
    from PIL import ImageChops, ImageFilter
    b = alpha.point(lambda v: 255 if v >= threshold else 0)
    core = b.filter(ImageFilter.MinFilter(min_width)).filter(ImageFilter.MaxFilter(min_width))
    thin = ImageChops.subtract(b, core)
    return ImageChops.lighter(b, thin.filter(ImageFilter.MaxFilter(3)))


def grow_to(alpha, min_width=3, ss=4, threshold=96):
    """Every stroke at least `min_width` sheet px (the Spartan Laser, test 9: MCC draws the
    reticle sheet at ~0.5 with BILINEAR sampling -- a 2 x 2 average -- so a 2 px line comes out
    1 px at 100 % or 2 px at 50 % by its phase: along a curve it flickers, the 'fizzle'; at 3
    px it never drops under ~75 %). At `ss` x supersampling: the strokes under `min_width`
    (one erosion removes them) grown by HALF a sheet px each side (+1 px in all), wider ones
    and the gaps untouched; back down area-averaged (soft edges are fine under bilinear)."""
    from PIL import ImageChops, ImageFilter
    w, h = alpha.size
    big = alpha.resize((w * ss, h * ss), Image.LANCZOS).point(lambda v: 255 if v >= threshold else 0)
    k = min_width * ss
    k += 1 - k % 2                                  # an odd filter size
    core = big.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    thin = ImageChops.subtract(big, core)
    grown = ImageChops.lighter(big, thin.filter(ImageFilter.MaxFilter(ss + 1)))
    return grown.resize((w, h), Image.BOX)


def simulate(alpha, out_png, scales=(0.47, 0.49, 0.52), offsets=((0, 0), (0.5, 0.5), (0.25, 0.75))):
    """What MCC's half-size, unmipped draw makes of a reticle -- BILINEAR sampling (test 9's
    chart: 1 px pairs averaged to grey, 2 px pairs resolved unevenly): a contact sheet, one
    tile per (scale, sub-pixel offset), each 4x enlarged."""
    import numpy as np
    a = np.asarray(alpha).astype(float)
    H, W = a.shape
    tiles = []
    for s in scales:
        for ox, oy in offsets:
            n = int(H * s)
            y = (np.arange(n) + 0.5 + oy) / s - 0.5
            x = (np.arange(n) + 0.5 + ox) / s - 0.5
            y0, x0 = np.clip(np.floor(y).astype(int), 0, H - 2), np.clip(np.floor(x).astype(int), 0, W - 2)
            fy, fx = np.clip(y - y0, 0, 1)[:, None], np.clip(x - x0, 0, 1)[None, :]
            v = (a[y0][:, x0] * (1 - fy) * (1 - fx) + a[y0 + 1][:, x0] * fy * (1 - fx)
                 + a[y0][:, x0 + 1] * (1 - fy) * fx + a[y0 + 1][:, x0 + 1] * fy * fx)
            t = Image.fromarray(np.clip(v, 0, 255).astype(np.uint8)).resize((n * 4, n * 4), Image.NEAREST)
            tiles.append(t)
    w = max(t.width for t in tiles)
    sheet = Image.new('L', (w * len(offsets), w * len(scales)), 40)
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % len(offsets)) * w, (i // len(offsets)) * w))
    sheet.save(out_png)


def add(h3_sheet, h3_index, name, index=None, thicken=0, layers=(), prefilter=0, scale=1.0,
        pixel=0, centre=CENTRE, mips=False, hard=0, min_width=0):
    """The Halo 3 sprite into `hud_reticles` AND `hud_reticles_r`, one sequence index (the
    port's reserved `index` when given). `thicken` px grows every stroke by that much on
    each side (a max filter): Halo 1 draws the 256 px sheet at about half size, and Halo
    3's thin strokes then break up -- 'pixels missing' (SMG test 1, 2026-10-07).
    `layers`: further Halo 3 pieces drawn into the SAME reticle, [(sheet or bitmap path,
    index or None, scale)] -- `scale` = that widget's chud scale / the main sprite's (the
    Spartan Laser's crosshair is TWO widgets: hud_reticles #11 at 0.59 and the inner double
    circle `spartan_outerring` at 0.95; test 1: 'the inner circle is missing')."""
    import h1_hud_sheet
    from PIL import ImageChops, ImageFilter
    canvas = Image.new('L', (SIZE, SIZE), 0)
    for src, idx, k in [(h3_sheet, h3_index, 1.0)] + list(layers):
        art, (rx, ry) = layer_art(src, idx)
        # `scale`: the art drawn that much smaller in the sheet (BOX: area-averaged), the
        # weapon HUD's overlay scaled up by the inverse (h1_pickable_weapons reticle_scale)
        k = k * scale
        w, h = round(art.width * SCALE * k), round(art.height * SCALE * k)
        alpha = art.split()[3].resize((w, h), Image.BOX if scale < 1 else Image.LANCZOS)
        if thicken:
            alpha = alpha.filter(ImageFilter.MaxFilter(2 * int(thicken) + 1))
        piece = Image.new('L', (SIZE, SIZE), 0)
        # `centre`: the registration point (the Spartan Laser, test 6 tried an even y against
        # the blur of pixel-doubled art -- it changed nothing: MCC's sampling phase is not tied
        # to it)
        piece.paste(alpha, (round(centre[0] - rx * SCALE * k), round(centre[1] - ry * SCALE * k)))
        if min_width:
            # per LAYER, keeping its own peak brightness (Halo 3's inner double circle is a
            # half-transparent grey, the outer ring full white)
            peak = piece.getextrema()[1]
            piece = grow_to(piece, min_width).point(lambda v: int(v * peak / 255.0))
        canvas = ImageChops.lighter(canvas, piece)
    if prefilter:
        canvas = prefiltered(canvas, prefilter)
    if pixel:
        canvas = pixel_doubled(canvas, pixel)
    if hard:
        canvas = hard_strokes(canvas, min_width=hard)
    simulate(canvas, os.path.join(HERE, 'out', 'reticle_%s_sim.png' % name.replace(' ', '_')))
    white = Image.new('L', (SIZE, SIZE), 255)
    img = Image.merge('RGBA', (white, white, white, canvas))
    canvas.save(os.path.join(HERE, 'out', 'reticle_%s.png' % name.replace(' ', '_')))
    return h1_hud_sheet.put_twins('hud_reticles', name, img, TEMPLATE_SEQ, (SIZE, SIZE), centre, mips=mips,
                                  index=index)


def orbit_frames(out_tag, h3_sheet, h3_index, scale, origin, n=16, sweep=180.0, size=512,
                 prefilter=0, sheet_index=None, art_scale=1.0, tight=True):
    """A CHARGE indicator as an OWN multi-frame bitmap (one sequence, n sprites): a Halo 3
    sprite whose chud widget sits `origin` half-extents (x, y down) from the crosshair and is
    rotated 0 -> `sweep` degrees by its animation over the charge (the Spartan Laser's
    `charge_triangle`, ui\\chud\\animations\\laser_charge 0 -> -180). Frame k = the sprite
    rotated k / (n - 1) of the sweep about the crosshair; `scale` = its widget scale / the
    reticle's (1.18 / 0.59). Halo 1's `charge` crosshair type shows it (h1_pickable_weapons
    hud `charge_crosshair`). The sheet is `size` px, the crosshair at its centre, the same
    pixels per Halo 3 unit as the reticle sheet. Returns the tag path written."""
    import copy
    import math
    import numpy as np
    from reclaimer.hek.defs.bitm import bitm_def
    import h1_hud_sheet
    art, (rx, ry) = h3_hud_art.sprite(h3_sheet, h3_index)
    k = SCALE * scale * art_scale
    w, h = round(art.width * k), round(art.height * k)
    alpha = art.split()[3].resize((w, h), Image.BOX if art_scale < 1 else Image.LANCZOS)
    # the sprite's centre relative to the crosshair (y down): the origin point sits ON it
    cx, cy = -origin[0] * w / 2.0, -origin[1] * h / 2.0
    c = size / 2.0
    frames = []
    for i in range(n):
        ang = sweep * i / float(n - 1)
        piece = Image.new('L', (size, size), 0)
        piece.paste(alpha, (round(c + cx - w / 2.0), round(c + cy - h / 2.0)))
        # PIL rotates counter-clockwise on screen: from below, that runs up the RIGHT side
        # to the top (the ticked half of Halo 3's ring)
        piece = piece.rotate(ang, resample=Image.BICUBIC, center=(c, c))
        if prefilter:
            piece = prefiltered(piece, prefilter)
        white = Image.new('L', (size, size), 255)
        frames.append(Image.merge('RGBA', (white, white, white, piece)))
    if sheet_index is not None:
        # INTO hud_reticles + its _r twin (test 2: an own bitmap drew nothing; MCC remaps
        # only the stock sheets listed in ui\hud\default.hud_globals to their _r copies --
        # the aim reticles on hud_reticles are the proven path): one sequence of n SMALL
        # sprites (the triangle's box), each registered at the crosshair
        import h1_hud_sheet
        sprites = []
        for img in frames:
            box = img.split()[3].getbbox()
            if not tight:            # the WHOLE canvas, registered at its centre (test 3)
                box = (2, 2, size - 2, size - 2)
            x0, y0, x1, y1 = box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2
            w2 = 1 << (x1 - x0 - 1).bit_length()
            h2 = 1 << (y1 - y0 - 1).bit_length()
            crop = Image.new('RGBA', (w2, h2), (255, 255, 255, 0))
            crop.paste(img.crop((x0, y0, x1, y1)), (0, 0))
            sprites.append((crop, (c - x0, c - y0)))
        for sheet in ('hud_reticles', 'hud_reticles_r'):
            h1_hud_sheet.put_frames(sheet, os.path.basename(out_tag), sprites, TEMPLATE_SEQ, sheet_index)
    else:
        # the tag AND an `_r` twin (32-bit, from hud_reticles_r)
        for src, suffix in ((TAG, ''), (TAG.replace('.bitmap', '_r.bitmap'), '_r')):
            _orbit_tag(src, out_tag + suffix, frames, size)
    strip = Image.new('RGBA', (size * 4, size * ((n + 3) // 4)), (40, 40, 40, 255))
    for i, img in enumerate(frames):
        strip.alpha_composite(img, ((i % 4) * size, (i // 4) * size))
    strip.save(os.path.join(HERE, 'out', 'charge_%s.png' % os.path.basename(out_tag)))
    return out_tag


def _orbit_tag(template, out_tag, frames, size):
    import copy
    from reclaimer.hek.defs.bitm import bitm_def
    import h1_hud_sheet
    t = bitm_def.build(filepath=template)
    d = t.data.tagdata
    tseq = copy.deepcopy(d.sequences.STEPTREE[TEMPLATE_SEQ])
    tb = copy.deepcopy(d.bitmaps.STEPTREE[tseq.sprites.STEPTREE[0].bitmap_index])
    fmt = tb.format.enum_name
    bms, seqs = d.bitmaps.STEPTREE, d.sequences.STEPTREE
    bms[:] = []
    seqs[:] = []
    pix = bytearray()
    seqs.append(tseq)
    sq = seqs[0]
    sq.sequence_name = 'charge'
    sprite = copy.deepcopy(sq.sprites.STEPTREE[0])
    sq.sprites.STEPTREE[:] = []
    for i, img in enumerate(frames):
        bms.append(copy.deepcopy(tb))
        b = bms[len(bms) - 1]
        b.width, b.height, b.mipmaps = size, size, 0
        b.pixels_offset = len(pix)
        pix += h1_hud_sheet._pixels(img, fmt, size, size)
        sq.sprites.STEPTREE.append(copy.deepcopy(sprite))
        sp = sq.sprites.STEPTREE[len(sq.sprites.STEPTREE) - 1]
        sp.bitmap_index = i
        sp.left_side, sp.right_side, sp.top_side, sp.bottom_side = 0.0, 1.0, 0.0, 1.0
        sp.registration_point_x = sp.registration_point_y = 0.5
    sq.first_bitmap_index, sq.bitmap_count = 0, len(frames)
    d.processed_pixel_data.data = bytes(pix)
    out = os.path.join(TAG.split(os.sep + 'ui' + os.sep)[0], out_tag + '.bitmap')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t.filepath = out
    t.serialize(temp=False, backup=False)


if __name__ == '__main__':
    # optional 4th argument: the port's reserved hud_reticles index (H1_PORT_PLAN.md)
    print('sequence', add(sys.argv[1], int(sys.argv[2]), sys.argv[3],
                          int(sys.argv[4]) if len(sys.argv) > 4 else None))
