r"""Step 7 of a Halo 2 port: the weapon symbol on the HUD, painted into the BACKGROUND plate
(generalized from h2_saw_hud_plate.py, the SAW 2026-09-24 -- its notes stand: the plate behind
the weapon is interpolated row by row between the pixels either side of the box; the symbol is
FLAT bright cyan with its OWN green ramp over its own extent; only image 0 is written).

The config's `hud_plate` section:
    rel, donor, other    the backgrounds folder, the donor plate, a second plate to diff against
    name, hud            the port's plate bitmap name, the HUD that is repointed at it
    model_3p             the port's mesh (an H4 render dump, h3_weapon_glyph.mesh)
    fallback_box, stretch
    all_images           (the Spike Rifle, 2026-10-21: a DUAL-WIELD plate) {'dim': {dim image:
                         its bright twin}} -- EVERY image repainted and written back into the
                         donor tag's own COLOUR PLATE (Bungie's, stored compressed in the
                         .bitmap: blue background, magenta sequence lines), so the multi-image
                         bitmap and the widgets' sequence indices stay as Bungie made them. A
                         dim ('_out') image = its bright twin's repaint x the donor pair's
                         per-channel ratio, inside the weapon box only (the dim plate has no
                         divider line). Default: image 0 only (the single-wield plates).
                         'boxes' {image: (x0, x1, y0, y1)}: an image whose symbol Bungie drew
                         elsewhere (the Energy Blade plate's 'multi' images, the Gravity Hammer)

    python h2_port_hud_plate.py <key> [--write]
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
TEMP = os.environ.get('TEMP', '.')
# set from the config by setup()
REL = DONOR = OTHER = PORT = HUD = MODEL = NAME = None
FALLBACK_BOX = None
STRETCH = None
ICON = None
RAMP = None


def setup(key):
    global REL, DONOR, OTHER, PORT, HUD, MODEL, NAME, FALLBACK_BOX, STRETCH, ICON, RAMP
    h = ports_h2.get(key, 'hud_plate')
    REL, DONOR, OTHER, HUD, MODEL = h['rel'], h['donor'], h['other'], h['hud'], h['model_3p']
    NAME = h['name']
    PORT = B.join([REL, NAME])
    FALLBACK_BOX, STRETCH = tuple(h['fallback_box']), h['stretch']
    ICON = h.get('icon_art')
    RAMP = h.get('ramp')


def export(tag, prefix):
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', tag, prefix],
                   cwd=H2EK, capture_output=True, text=True)
    return sorted(glob.glob(prefix + os.path.basename(tag) + '_*.tga'))


def donor_images():
    """The donor plate's images, in order."""
    out = []
    for path in export(DONOR, os.path.join(TEMP, '_donor_')):
        out.append(np.asarray(Image.open(path).convert('RGBA')).astype(np.int16))
    return out


def weapon_box(donor, other):
    """Where the donor's plate differs from another weapon's: the silhouette."""
    d = np.abs(donor - other).sum(2)
    ys, xs = np.nonzero(d > 12)
    if not len(xs):
        return None
    return int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1


def solidify(cov):
    """Close the one-pixel holes a thin weapon leaves when it is shrunk to 29 rows.

    Bungie's symbols are CHUNKY: solid blocks with a few deliberate cutouts. A 13836
    triangle gun projected this small breaks into slivers instead, and a sliver with a
    part-lit pixel either side of it reads as a scratch rather than as a gun. So any
    pixel with solid neighbours on both sides, across or down, is filled in.
    """
    out = cov.copy()
    full = cov >= 0.999
    across = np.zeros_like(full)
    down = np.zeros_like(full)
    across[:, 1:-1] = full[:, :-2] & full[:, 2:]
    down[1:-1, :] = full[:-2, :] & full[2:, :]
    out[across | down] = 1.0
    return out


def icon_mask(w, h):
    """`icon_art` {'sheet': H3 chud bitmap, 'sprite': k, 'flip': bool} (the Spartan Laser, A2 boot 3:
    'the HUD icon still has issues' -- a bulky gun rasterised 24 px tall reads as a soft blob): the
    SOURCE game's own drawn HUD icon (Halo 3's weapon_scematics sprite) as the coverage, mirrored to
    face right like Halo 2's symbols, fitted into the box keeping its aspect, centred; painted with the
    plate's own ramp like any symbol."""
    import h3_hud_art
    img, sprites = h3_hud_art.decode(ICON['sheet'])
    l, r, t, b = sprites[ICON['sprite']][:4]
    W, H = img.size
    art = img.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
    a = np.asarray(art)[:, :, 3]
    ys, xs = np.nonzero(a > 8)
    art = art.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    if ICON.get('flip', True):
        art = art.transpose(Image.FLIP_LEFT_RIGHT)
    # Halo 3's icon is an OUTLINE over a translucent body: filled solid (everything the outline
    # encloses), as Bungie's Halo 2 symbols are solid shapes
    from PIL import ImageDraw
    m = Image.fromarray(((np.asarray(art)[:, :, 3] > 8) * 255).astype(np.uint8), 'L')
    pad = Image.new('L', (m.width + 2, m.height + 2), 0)
    pad.paste(m, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)                  # the outside
    solid = Image.fromarray(((np.asarray(pad) != 128) * 255).astype(np.uint8), 'L').crop(
        (1, 1, m.width + 1, m.height + 1))
    # the box's WIDTH, as every shipped symbol spans it; the height fitted into the box (a long icon
    # is squashed a little rather than shrunk to a stub)
    kx = w / float(art.width)
    ky = min(h / float(art.height), kx)
    aw, ah = max(1, int(round(art.width * kx))), max(1, int(round(art.height * ky)))
    small = np.asarray(solid.resize((aw, ah), Image.LANCZOS)).astype(float) / 255.0
    small = (small >= 0.5).astype(float)         # hard edges, as Bungie's symbols
    cov = np.zeros((h, w))
    ox, oy = (w - aw) // 2, (h - ah) // 2
    cov[oy:oy + ah, ox:ox + aw] = small
    return cov, cov


def port_mask(w, h, ss=4):
    """The port drawn side on as coverage and shading, the way the shipped plates are.

    A solid silhouette is the wrong picture. Bungie's symbols are SHADED drawings -- the
    Battle Rifle's runs from (0,151,131) on average up to (0,228,236) at its brightest,
    with interior structure -- so a flat blob at one colour reads as a smudge however
    good the outline is, which is what the first version of this produced.

    So the mesh is rasterised properly: an orthographic side view with a z buffer, at
    four times the final size, shading each triangle by how much its normal faces the
    light. Coverage comes out of the same pass as the fraction of subpixels that were
    hit, which gives the edges their antialiasing for free.

    Returns (coverage 0..1, shade 0..1), both h x w.
    """
    if ICON:
        return icon_mask(w, h)
    import h3_weapon_glyph as wg
    verts, idx = wg.mesh(MODEL)
    W, H = w * ss, h * ss
    xs = [v[0] for v in verts]
    zs = [v[2] for v in verts]
    # Fit the width, then stretch to fill the height, up to STRETCH. Every shipped symbol
    # spans the box top to bottom; a long thin LMG drawn to a single scale would sit in a
    # band across the middle, and the plate's colour is a GRADIENT down the box, so it
    # would also come out flat green instead of running green to blue like the rest.
    ex, ez = max(xs) - min(xs), max(zs) - min(zs)
    sx = W / ex
    sz = min(H / ez, sx * STRETCH)
    ox, oy = (W - ex * sx) / 2.0, (H - ez * sz) / 2.0
    px = [((ox + (v[0] - min(xs)) * sx), (H - oy - (v[2] - min(zs)) * sz)) for v in verts]

    depth = np.full((H, W), 1e9)
    shade = np.zeros((H, W))
    light = np.array([0.0, -0.80, 0.60])          # from the viewer, a little above
    for t in range(len(idx) - 2):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        if i0 == i1 or i1 == i2 or i0 == i2:
            continue                               # degenerate strip stitch
        p = [px[i0], px[i1], px[i2]]
        x0 = max(int(min(q[0] for q in p)), 0)
        x1 = min(int(max(q[0] for q in p)) + 1, W)
        y0 = max(int(min(q[1] for q in p)), 0)
        y1 = min(int(max(q[1] for q in p)) + 1, H)
        if x1 <= x0 or y1 <= y0:
            continue
        ax, ay = p[0]
        bx, by = p[1]
        cx, cy = p[2]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-9:
            continue
        # the triangle's own depth and its facing, flat shaded: a weapon symbol at
        # twenty-nine pixels tall gains nothing from interpolating either
        d = (verts[i0][1] + verts[i1][1] + verts[i2][1]) / 3.0
        n = np.cross(np.subtract(verts[i1], verts[i0]), np.subtract(verts[i2], verts[i0]))
        ln = np.linalg.norm(n)
        lit = 0.25 if ln < 1e-9 else 0.25 + 0.75 * abs(float(np.dot(n / ln, light)))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        gx, gy = xx + 0.5, yy + 0.5
        l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / det
        l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / det
        inside = (l0 >= 0) & (l1 >= 0) & (l0 + l1 <= 1) & (d < depth[y0:y1, x0:x1])
        if inside.any():
            depth[y0:y1, x0:x1][inside] = d
            shade[y0:y1, x0:x1][inside] = lit

    hit = (depth < 1e9).astype(float)
    cov = solidify(hit.reshape(h, ss, w, ss).mean((1, 3)))
    lit = np.where(cov > 0,
                   (shade * hit).reshape(h, ss, w, ss).sum((1, 3))
                   / np.maximum(hit.reshape(h, ss, w, ss).sum((1, 3)), 1), 0.0)
    return cov, lit


def symbol_ramp(donor, box):
    """The two ends of the gradient the donor's symbol is drawn with.

    Measured across the battle rifle, the SMG and the shotgun, and they agree. A symbol
    is BLUE at a near constant 215, and its GREEN is a ramp -- but the ramp belongs to
    the SYMBOL, not to the plate: it runs from about 225 at whatever row the weapon
    starts on down to about 7 at the row it ends on, whichever rows those are. The
    shotgun's drawing spans rows 4..24 and ramps 218..14 over exactly that span, while
    the plate underneath is running 189..22 there. So it is stretched to fit the weapon.

    That is also why the gradient reads as "slow, then sudden": green only overtakes
    blue in the last few rows at the top, so the shape is blue almost all the way up and
    then turns cyan and white right at the end.

    Sampling the donor row by row, which is what this did before, gets the top wrong:
    the plate's own green is 222 up there, so every background pixel passes for symbol
    and the port's top comes out plate coloured and faded.
    """
    reg = donor[box[2]:box[3], box[0]:box[1]].astype(float)
    rows = []
    for y in range(reg.shape[0]):
        bg = np.median(donor[box[2] + y, 10:100], 0)
        # BLUE above this ROW's background blue: the plate has none, the symbol has 215
        ink = reg[y][reg[y][:, 2] > bg[2] + 60]
        rows.append(ink.mean(0) if len(ink) >= 3 else None)
    lit = [y for y, r in enumerate(rows) if r is not None]
    if not lit:
        return np.array([0, 225, 215, 250.0]), np.array([0, 7, 215, 250.0])
    return rows[lit[0]], rows[lit[-1]]


def repaint(donor, box, mask):
    """The donor plate with its weapon erased and the port's drawn in its place.

    The plate behind the weapon is a smooth gradient, so it is rebuilt by interpolating
    each row between the pixels either side of the box -- both of which are plate, never
    weapon. That is steadier than averaging other weapons' plates together, which leaves
    the seams of whatever they happened to cover.

    The port's drawing is then composited over that, its own gradient stretched over its
    own vertical extent the way every shipped symbol's is, with coverage doing the
    blending so the edges are antialiased against the real background rather than cut out
    of it.
    """
    cov, _lit = mask
    x0, x1, y0, y1 = box
    out = donor.copy()
    for y in range(y0, y1):
        left = donor[y, max(x0 - 1, 0)].astype(float)
        right = donor[y, min(x1, donor.shape[1] - 1)].astype(float)
        span = max(x1 - x0, 1)
        for x in range(x0, x1):
            t = (x - x0 + 1) / (span + 1)
            out[y, x] = (left * (1 - t) + right * t).astype(np.int16)

    # `ramp` ((top rgb), (bottom rgb)) in the config (the Spartan Laser, A2 boot 3): the symbol's ramp
    # as measured on the donor's own symbol, where the box must also cover plate border pixels that
    # symbol_ramp would take for ink
    top, bottom = ((np.array(tuple(RAMP[0]) + (255,), float), np.array(tuple(RAMP[1]) + (255,), float)) if RAMP
                   else symbol_ramp(donor, box))
    drawn = [y for y in range(y1 - y0) if cov[y].max() > 0]
    first, last = (drawn[0], drawn[-1]) if drawn else (0, y1 - y0 - 1)
    span = max(last - first, 1)
    for y in range(y1 - y0):
        t = min(max((y - first) / float(span), 0.0), 1.0)
        colour = top + (bottom - top) * t
        for x in range(x1 - x0):
            c = cov[y][x]
            if c <= 0:
                continue
            base = out[y0 + y, x0 + x].astype(float)
            out[y0 + y, x0 + x] = (base * (1 - c) + colour * c).astype(np.int16)
    return out


def color_plate(tag):
    """Bungie's own colour plate inside a loose H2 .bitmap: (RGBA array, (w, h)). The data is
    the tag's zlib stream (size-prefixed); its width / height are the uint16 pair whose
    product is the pixel count (`color plate width / height`); pixels are BGRA."""
    import struct
    import zlib
    d = open(tag, 'rb').read()
    for i in range(len(d) - 1):
        if d[i] == 0x78 and d[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                raw = zlib.decompressobj().decompress(d[i:])
            except zlib.error:
                continue
            if len(raw) >= 1000 and len(raw) % 4 == 0:
                break
    else:
        raise SystemExit('%s carries no colour plate' % tag)
    n = len(raw) // 4
    for j in range(0, i - 3):
        w, h = struct.unpack_from('<HH', d, j)
        if w and h and w * h == n:
            a = np.frombuffer(raw, np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]]
            return a.astype(np.int16), (w, h)
    raise SystemExit('%s: no colour plate size matches %d pixels' % (tag, n))


def find_in_plate(plate, img):
    """Where an exported image sits in the colour plate (an exact RGB match of its rows)."""
    h, w = img.shape[:2]
    ph, pw = plate.shape[:2]
    rgb, prgb = img[:, :, :3], plate[:, :, :3]
    for y in range(ph - h + 1):
        for x in np.nonzero((prgb[y, :pw - w + 1] == rgb[0, 0]).all(1))[0]:
            if (prgb[y:y + h, x:x + w] == rgb).all():
                return int(x), int(y)
    raise SystemExit('an exported plate image is not in the colour plate')


def all_images(donor, sheets, boxes, cfg):
    """Every image repainted into the donor's colour plate; returns the plate image."""
    plate, _size = color_plate(os.path.join(TAGS, DONOR + '.bitmap'))
    out = plate.copy()
    dim = {int(k): v for k, v in (cfg.get('dim') or {}).items()}
    skip = set(cfg.get('skip') or ())
    for idx, img in enumerate(donor):
        if idx in skip:
            continue                 # Bungie's own pixels stay in the plate untouched
        x, y = find_in_plate(plate, img)
        if idx in dim:
            twin = dim[idx]
            x0, x1, y0, y1 = boxes[twin]
            src = np.asarray(sheets[twin]).astype(float)
            ratio = (donor[idx][y0:y1, x0:x1].reshape(-1, 4).sum(0) + 1.0) / \
                    (donor[twin][y0:y1, x0:x1].reshape(-1, 4).sum(0) + 1.0)
            new = donor[idx].astype(float)
            new[y0:y1, x0:x1] = src[y0:y1, x0:x1] * ratio
            sheet = np.clip(new, 0, 255)
            print('   image %d: image %d\'s repaint x %s (dim)' % (idx, twin, np.round(ratio, 3)))
        else:
            sheet = np.asarray(sheets[idx]).astype(float)
        # alpha 0 in the plate is the background's; keep the image's own alpha where it is
        out[y:y + img.shape[0], x:x + img.shape[1]] = sheet.astype(np.int16)
    return Image.fromarray(np.clip(out, 0, 255).astype('uint8'), 'RGBA')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    setup(a.key)
    every = ports_h2.get(a.key, 'hud_plate').get('all_images')

    donor = donor_images()
    other = [np.asarray(Image.open(p).convert('RGBA')).astype(np.int16)
             for p in export(OTHER, os.path.join(TEMP, '_other_'))]
    print('%d image(s) in the donor plate' % len(donor))

    sheets, boxes = [], []
    skip = set((every or {}).get('skip') or ())
    for idx, img in enumerate(donor):
        if idx in skip:
            # all_images 'skip' (the Spartan Laser, A2: the beam rifle plate's zoom-arc images, no
            # weapon symbol, another size): written back exactly as the donor's
            sheets.append(Image.fromarray(np.clip(img, 0, 255).astype('uint8'), 'RGBA'))
            boxes.append(None)
            continue
        box = (weapon_box(img, other[idx])
               if idx < len(other) and other[idx].shape == img.shape else None)
        # images past the first pair are the half and quarter screen variants, whose
        # weapon sits in the same place; a box covering the whole plate means the two
        # differ in more than the weapon and is not one
        if not box or (box[1] - box[0]) > img.shape[1] * 0.8:
            box = FALLBACK_BOX
        if every and boxes:
            box = boxes[0]       # Bungie draws the symbol in the same place on every image
        # all_images 'boxes' {image: (x0, x1, y0, y1)} -- except where it does not (the Gravity
        # Hammer, 2026-10-29: the Energy Blade plate's short 'multi' images 2 / 3 carry the sword
        # 36 px further left; image 0's box left its tip standing beside the port's symbol)
        box = tuple((every or {}).get('boxes', {}).get(idx, box))
        mask = port_mask(box[1] - box[0], box[3] - box[2])
        sheets.append(Image.fromarray(
            np.clip(repaint(img, box, mask), 0, 255).astype('uint8'), 'RGBA'))
        boxes.append(box)
        print('   image %d: weapon box x %d..%d y %d..%d' % ((idx,) + box))

    # ONLY the first image. Stacking all four into one colour plate makes tool import a
    # single 206x152 bitmap, because a multi-image interface bitmap is split by separator
    # colours this does not write -- and the widget asks for sequence 0 at every screen
    # size anyway, so the other three were never drawn. A dual-wield plate (all_images)
    # is written into the donor's own colour plate instead, separators and all
    sheet = all_images(donor, sheets, boxes, every) if every else sheets[0]
    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, NAME + '.tif')
    sheet.save(tif, compression=None)
    print('   wrote %s (%dx%d)' % (tif, sheet.width, sheet.height))
    if not a.write:
        print('(dry run -- pass --write)')
        return

    dest = os.path.join(TAGS, PORT + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, DONOR + '.bitmap'), dest)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', REL],
                       cwd=H2EK, capture_output=True, text=True)
    for line in ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10)).split(chr(10)):
        line = ' '.join(line.split())
        if NAME in line or 'bitmap created' in line:
            print('   | %s' % line)
    hud = os.path.join(TAGS, HUD + '.new_hud_definition')
    have = h2_tagref.references(hud)
    if ('bitm', PORT) in have and ('bitm', DONOR) not in have:
        print('   the HUD already points at the port plate')
    else:
        # a BR-shaped HUD names its plate TWICE (weapon_background_single seq 0 and
        # weapon_background_out seq 1 -- the AR, 2026-10-20; the SAW's GPMG HUD once): every
        # copy moves, and on the one-image plate each widget's sequence index becomes 0
        n = have.count(('bitm', DONOR))
        try:
            h2_tagref.set_reference(hud, 'bitm', DONOR, PORT, every=n > 1)
        except ValueError:
            # every=True refuses when another record has the path's length (the SMG's plate,
            # named x4 -- the Spike Rifle): one copy at a time
            for _k in range(n):
                h2_tagref.set_reference(hud, 'bitm', DONOR, PORT, nth=0)
    import h2_port_scope
    import h2_tagfield
    for idx, _name, ref, seq in h2_port_scope.widgets(hud):
        if ref == PORT and any(seq) and not every:
            for field in ('fullscreen', 'halfscreen', 'quarterscreen'):
                h2_tagfield.set_field(hud, field + ' sequence index', 0, 'bitmap widgets', idx)


if __name__ == '__main__':
    main()
