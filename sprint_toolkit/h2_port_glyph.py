r"""Step 8 of a Halo 2 port: its pickup icon at its RESERVED codepoint, in every English font
that draws HUD text (generalized from h2_saw_glyph.py, the SAW 2026-09-24 -- its notes stand:
`tool replace-font-char` draws the glyph, its codepoint argument is DECIMAL (hex reads as 0 and
rewrites notdef); h2_font_add.py creates the codepoint first; the fonts are edited inside H2EK
and copied back; no shipped glyph may change).

The codepoint is the config's `reservations['glyph']` (0xE13D the SAW, 0xE13E.. the wave ports:
H2_PORT_PLAN 0.3). The config's `glyph` section:
    box        the glyph's size (= its on-screen size; Bungie's widest is 160x62)
    model_3p   the port's mesh (an H4 render dump, h3_weapon_glyph.mesh)
    model_skip a JMS mesh's materials left out of the drawing (h3_weapon_glyph.mesh)
    tif        the drawn glyph's file name in %TEMP%
    colour     optional RGB the glyph is drawn in (default white, Halo 3's look; the AR: Halo
               2's HUD blue, sampled from a classic screenshot)

    python h2_port_glyph.py <key> [--cp 0xE13E] [--write [--redraw]] [--restore]
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_font as hf  # noqa: E402
import h2_font_add as fa  # noqa: E402
import ports_h2  # noqa: E402

B = os.sep
H2EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
LIVE = hf.FONTS
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'h2_fonts')

#: the fonts an English game draws HUD text with
FONTS = ('conduit-9', 'conduit-12', 'conduit-13', 'fixedsys-9',
         'handel_gothic-11', 'handel_gothic-13', 'handel_gothic-24', 'MSLCD-14')
# set from the config by setup()
BOX = CP = MODEL = TIF = None


COLOUR = None
STYLE = None
SKIP = ()
import numpy as np  # noqa: E402


def setup(key):
    global BOX, CP, MODEL, TIF, COLOUR, STYLE, SKIP
    g = ports_h2.get(key, 'glyph')
    COLOUR = tuple(g['colour']) if g.get('colour') else None
    STYLE = g.get('style')
    BOX, MODEL = tuple(g['box']), g['model_3p']
    SKIP = g.get('model_skip', ())
    CP = ports_h2.load(key)['reservations']['glyph']
    TIF = g.get('tif', key + '_h2_glyph.tif')


def art(path, box=None):
    """The SAW's silhouette as a TIFF, drawn from its own geometry."""
    import h3_weapon_glyph as wg
    from PIL import Image
    box = BOX if box is None else box
    verts, idx = wg.mesh(MODEL, SKIP)
    cov = wg.close_gaps(wg.silhouette(verts, idx, box[0], box[1], margin=0), 5)
    if STYLE:
        im = h2_style(verts, idx, cov, box)
        im.save(path, compression=None)
        return int((np.asarray(im)[:, :, 3] > 0).sum())
    px = wg.stylise(cov)
    im = Image.new('RGBA', box)
    if COLOUR:
        # the glyph DRAWN in a colour (the AR, boot 1, user: 'the pickup icon is white, the H2
        # icons are blue' -- a new codepoint's pixels are shown as written, nothing tints them)
        # tool's encoder writes a SEMI-transparent pixel with its WHITE shorthand (measured: of a
        # glyph drawn at alpha 170 only the 255 pixels kept their colour), so a coloured glyph is
        # OPAQUE wherever it has ink and its shading (Halo 3's grey body, bright outline) moves
        # from the alpha into the brightness
        # body (wg.FILL) = the colour, outline (wg.EDGE) = halfway to white, the antialiased fringe
        # dimmed by its coverage
        def tint(a):
            if a >= wg.EDGE:
                return tuple((c + 255) // 2 for c in COLOUR)
            k = min(1.0, a / float(wg.FILL))
            return tuple(int(c * k) for c in COLOUR)
        im.putdata([tint(a) + (255,) if a else (0, 0, 0, 0) for a, r, g, b in px])
    else:
        im.putdata([(r * 17, g * 17, b * 17, a * 17) for a, r, g, b in px])
    im.save(path, compression=None)
    return sum(1 for q in px if q[0])


def feature_lines(V, idx, W, H, ss=4, crease=35.0, margin=0):
    """[H][W] bool: the model's FEATURE LINES in the glyph's side view (x across, z up, the
    silhouette's own projection) -- every pixel where the visible surface's face normal turns
    by more than `crease` degrees, or the depth jumps (one part in front of another): the fine
    panel lines Bungie's Halo 2 (and Halo 3) icons carry. Rendered at ss x by a z-buffer (the
    camera on the -y side), then max-pooled to the glyph's pixels."""
    a = np.array([v[0] for v in V])
    b = np.array([v[2] for v in V])
    c = np.array([v[1] for v in V])
    ea, eb = a.max() - a.min(), b.max() - b.min()
    s = min((W - 2 * margin) / ea, (H - 2 * margin) / eb)
    ox, oy = (W - ea * s) / 2.0, (H - eb * s) / 2.0
    X = (ox + (a - a.min()) * s) * ss
    Y = (H - oy - (b - b.min()) * s) * ss
    Wn, Hn = W * ss, H * ss
    depth = np.full((Hn, Wn), np.inf)
    nrm = np.zeros((Hn, Wn, 3))
    P = np.stack([a, c, b], 1)
    for t in range(len(idx) - 2):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        if i0 == i1 or i1 == i2 or i0 == i2:
            continue
        n = np.cross(P[i1] - P[i0], P[i2] - P[i0])
        ln = np.linalg.norm(n)
        if ln == 0:
            continue
        n = n / ln
        xs, ys = np.array([X[i0], X[i1], X[i2]]), np.array([Y[i0], Y[i1], Y[i2]])
        x0, x1 = int(max(0, np.floor(xs.min()))), int(min(Wn - 1, np.ceil(xs.max())))
        y0, y1 = int(max(0, np.floor(ys.min()))), int(min(Hn - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-9:
            continue
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        z = w0 * c[i0] + w1 * c[i1] + w2 * c[i2]
        sub = depth[y0:y1 + 1, x0:x1 + 1]
        win = inside & (z < sub)
        sub[win] = z[win]
        nrm[y0:y1 + 1, x0:x1 + 1][win] = n if n[1] <= 0 else -n
    hit = np.isfinite(depth)
    edge = np.zeros((Hn, Wn), bool)
    cos = np.cos(np.radians(crease))
    jump = 0.02 * max(ea, eb)
    for dy, dx in ((0, 1), (1, 0)):
        A, Bn = nrm[:Hn - dy, :Wn - dx], nrm[dy:, dx:]
        both = hit[:Hn - dy, :Wn - dx] & hit[dy:, dx:]
        with np.errstate(invalid="ignore"):
            dz = np.abs(np.where(both, depth[:Hn - dy, :Wn - dx] - depth[dy:, dx:], 0))
        e = both & (((A * Bn).sum(2) < cos) | (dz > jump))
        edge[:Hn - dy, :Wn - dx] |= e
    return edge.reshape(H, ss, W, ss).any(axis=(1, 3))


def h2_style(V, idx, cov, box):
    """STYLE 'h2' (the AR, boot 2, user: 'it's missing the fine lines every vanilla weapon has',
    Bungie's BR icon beside it): Halo 2's look -- a TRANSLUCENT body, a bright 1 px outline and
    the model's own feature lines in the outline colour. tool's encoder keeps colour only on
    OPAQUE pixels (a semi-transparent one becomes white), so the body's translucency is a 1 px
    CHECKERBOARD of opaque body colour and clear (half coverage at icon size)."""
    from PIL import Image
    W, H = box
    solid = np.asarray(cov) > 128
    inner = np.zeros_like(solid)
    inner[1:-1, 1:-1] = (solid[1:-1, 1:-1] & solid[:-2, 1:-1] & solid[2:, 1:-1]
                         & solid[1:-1, :-2] & solid[1:-1, 2:])
    outline = solid & ~inner
    lines = feature_lines(V, idx, W, H) & inner
    line_c, body_c = STYLE['line'], STYLE['body']
    out = np.zeros((H, W, 4), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    # the DITHER (opt-in, 'dither': True) MANGLED the icon in game (the AR, boot 3): a checkerboard
    # has no runs, the glyph's payload grew 2.7 -> 8.3 KB and Halo 2 drew it sheared -- so the
    # body is SOLID by default, a darker blue standing in for the translucency
    body = inner & ~lines
    if STYLE.get('dither'):
        body &= (xx + yy) % 2 == 0
    out[body] = tuple(body_c) + (255,)
    out[outline | lines] = tuple(line_c) + (255,)
    return Image.fromarray(out, 'RGBA')


def one(name, tif, cp, write, redraw=False):
    live = os.path.join(LIVE, name)
    before = open(live, 'rb').read()
    mine = hf.glyph_of(before, cp)
    if mine is not None and not redraw:
        print('   %-20s 0x%04X already drawn by glyph %d' % (name, cp, mine))
        return True
    if mine is not None:
        # --redraw (the AR, boot 1: its glyph recoloured): tool replaces a MAPPED codepoint in
        # place; every other glyph must come out unchanged
        after = before
    else:
        after = fa.add(before, cp)
        problem = fa.verify(before, after, cp)
        if problem:
            print('   %-20s REFUSED: %s' % (name, problem))
            return False
    if not write:
        print('   %-20s would add glyph %d' % (name, hf.header(before)[0]))
        return True

    work = os.path.join(H2EK, 'h2_fonts', name)
    open(work, 'wb').write(after)
    # DECIMAL. Hex is read as zero and rewrites the notdef glyph instead.
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'replace-font-char',
                        B.join(['h2_fonts', name]), tif, str(cp)],
                       cwd=H2EK, capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    if 'replaced char %d' % cp not in out:
        print('   %-20s tool did not replace it: %s' % (name, ' '.join(out.split())[:90]))
        return False
    done = open(work, 'rb').read()
    i = hf.glyph_of(done, cp)
    rec = hf.record(done, i)
    disturbed = [k for k in range(hf.header(before)[0]) if k != mine
                 and (hf.record(before, k)[:6] != hf.record(done, k)[:6]
                      or hf.payload(before, k) != hf.payload(done, k))]
    if disturbed:
        print('   %-20s REFUSED: %d shipped glyph(s) changed' % (name, len(disturbed)))
        return False
    shutil.copy(work, live)
    print('   %-20s glyph %3d  %3dx%-3d advance %3d   %d -> %d bytes'
          % (name, i, rec[2], rec[3], rec[0], len(before), len(done)))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--cp', type=lambda s: int(s, 0), default=None)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--redraw', action='store_true', help='replace the existing glyph in place')
    a = ap.parse_args(argv)
    setup(a.key)
    if a.cp is None:
        a.cp = CP

    if a.restore:
        for name in FONTS:
            src = os.path.join(BACKUP, name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(LIVE, name))
                print('   restored %s' % name)
        return

    os.makedirs(BACKUP, exist_ok=True)
    for name in FONTS:
        keep = os.path.join(BACKUP, name)
        if not os.path.exists(keep):
            shutil.copy(os.path.join(LIVE, name), keep)

    tif = os.path.join(os.environ.get('TEMP', '.'), TIF)
    print('drawing the glyph: %d ink pixels in %dx%d' % (art(tif), BOX[0], BOX[1]))
    print('adding 0x%04X (decimal %d):' % (a.cp, a.cp))
    ok = True
    for name in FONTS:
        ok &= one(name, tif, a.cp, a.write, a.redraw)
    if not a.write:
        print('(dry run -- pass --write)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
