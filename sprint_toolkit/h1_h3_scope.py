r"""A Halo 3 weapon's ZOOMED scope (its chud's zoom-only bitmap widgets) as a Halo 1 zoom mask.

Halo 1 draws a zoomed weapon's vignette as the weapon HUD's SCREEN EFFECT mask
(weapon_hud_interface screen_effect[0].mask, flag only_when_zoomed): a full-screen
a8r8g8b8 bitmap whose RGB is how DARK each point gets (the pistol's `pistol_scope_mask`:
black inside the lens, 131 grey outside, a white ring) and whose alpha is where the
convolution blurs. Halo 3's scopes are bitmap widgets drawn in BLACK (custom colour A = 0)
with the bitmap's alpha (the BR: a quarter ring mirrored both ways with 'extend border',
two rulers, a range meter) -- so the same darkening, and the whole Halo 3 scope bakes into
one Halo 1 mask. User, BR test 1 (2026-10-07): replace the zoom HUD ENTIRELY with Halo
3's, as the STANDARD procedure for zooming ports.

Halo 3 chud placement (the Reach scope's reading, PORTING 'Boot 21', and the BR's art):
1152x640 units, centred on the crosshair; a sprite is (px x widget scale) units; `widget
origin` is the sprite point (in half-extents, image y DOWN) that sits at anchor + `origin
offset` (y down); `mirror horizontal / vertical` add the copy reflected about the anchor;
`extend border` repeats the sprite's edge beyond it. Only widgets whose unit zoom state
excludes 'unzoomed' are taken (the reticle stays the HUD's own crosshair).

The mask spans `span` chud units tall and `span x aspect` wide, `size` px square; the blur
keeps the donor's convolution. WHERE HALO 1 DRAWS IT (BR tests 2-3, 2026-10-07, 1920x1080
screenshots): a centred 4:3 box whose size follows the TEXTURE -- about 1.09 px a texel
tall (512 -> 558 px, 1024 -> ~1116 px), x 4/3 wide; beyond it the edge texels repeat.
Hence `aspect` 4/3 (pre-squashed round) and a `span` chosen for the screen size wanted:
ring px = 369 units x size/span x 1.09 (the BR: span 660 on 1024 -> 623 px = Halo 3's 58%).
OBSERVATIONS from one weapon at one resolution -- check them on the next scope port. make_hud (h1_pickable_weapons, hud['scope']) points the
weapon's HUD at it and drops the donor's zoom crosshairs (the pistol's readouts).

    python h1_h3_scope.py "ui\chud\battle_rifle" "weapons\battle rifle\bitmaps\scope_mask" [--preview out.png]
"""
import argparse
import io
import math
import os
import re
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import h3_hud_art  # noqa: E402
import h1_fp_retarget  # noqa: E402  (export_xml, cached)

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
TEMPLATE = r'ui\hud\bitmaps\pistol\pistol_scope_mask'      # 512x512 a8r8g8b8, no mips


def widgets(chud):
    """[(name, fields)] of every bitmap widget of a Halo 3 chud_definition.
    A widget with NO state of its own takes its COLLECTION's (the Carbine, 2026-10-07:
    `scope_bitmaps` carries 'zoom lvl 1', its eight widgets none -- read per widget alone,
    nothing was zoom-only and nothing baked)."""
    s = io.open(h1_fp_retarget.export_xml(chud + '.chud_definition'), encoding='utf-8',
                errors='replace').read()
    out = []
    parts = re.split(r'<element index="\d+" name="([^"]+)">\s*<field name="base" value=" " type="struct"/>', s)
    coll_zoom = 0
    for name, body in zip(parts[1::2], parts[2::2]):
        if '<block name="bitmap widgets"' in body:          # a collection (its own states)
            zc = re.search(r'name="unit zoom state" value="(\d+)"', body)
            coll_zoom = int(zc.group(1)) if zc else 0
            continue
        if '<field name="bitmap" value=' not in body:
            continue
        g = lambda k: (re.search(r'name="%s" value="([^"]*)"' % re.escape(k), body) or [None, None])[1]  # noqa: E731
        fl = re.search(r'<field name="flags" value="\d+" type="word flags"(?:/>|>(.*?)</field>)', body, re.S)
        flags = set(x.strip() for x in (fl.group(1) or '').splitlines() if x.strip()) if fl else set()
        zm = re.search(r'name="unit zoom state" value="(\d+)"', body)
        out.append((name, {
            'bitmap': g('bitmap').split(',')[0], 'sequence': int(g('sequence index')),
            'anchor': g('anchor type'), 'origin': tuple(float(x) for x in g('widget origin').split(',')),
            'offset': tuple(float(x) for x in g('origin offset').split(',')),
            'scale': tuple(float(x) for x in g('widget scale').split(',')),
            'zoom': int(zm.group(1)) if zm else coll_zoom, 'color': g('custom color A'), 'flags': flags,
            # 'distortion and blur' (the Carbine's carbine_distortion) refracts, it does not
            # darken; an ACTIVE animation (.chad) may set what the static fields leave at 0
            'shader': g('shader type'),
            'active': (re.search(r'name="active" value=" " type="struct"/>.*?name="animation" value="([^",]*)',
                                 body, re.S) or [None, None])[1] or None}))
    return out


def zoom_only(w):
    return w['zoom'] and not (w['zoom'] & 1)        # bit 0 = unzoomed


def bake(chud, size=512, span=640.0, aspect=1.0, per_widget=None):
    """(darkness, used): bake_maps without the blur map (the BR's call)."""
    dark, _blur, used = bake_maps(chud, size, span, aspect, per_widget)
    return dark, used


def bake_maps(chud, size=512, span=640.0, aspect=1.0, per_widget=None):
    """(darkness, blur, used): float 0..1 images (size x size) of the chud's zoom-only
    widgets. `per_widget` {name: {'drop': True} | {'scale': (x, y)} | {'offset': (x, y)} |
    {'blur': strength}}: a decision per widget (the Carbine's animated crosshair pieces sit
    at scale 0 and get their size from the .chad; a mask is static). A 'distortion and
    blur' widget is skipped unless named here (it refracts; a mask can only darken); with
    'blur' its sprite alpha x strength goes to the BLUR map instead (write() puts it in
    the mask's alpha: the Carbine's distortion over the side cells, user 2026-10-07)."""
    dark = np.zeros((size, size))
    blur = np.zeros((size, size))
    px_per_u = (size / (span * aspect), size / span)   # x, y
    used = []
    per_widget = per_widget or {}
    for name, w in widgets(chud):
        if not zoom_only(w) or 'hud_reticles' in w['bitmap']:
            continue
        o = per_widget.get(name, {})
        if o.get('drop'):
            used.append('%s DROPPED' % name)
            continue
        if w['shader'] == 'distortion and blur' and not o:
            print('   SKIPPED %s: a distortion widget (decide it per widget)' % name)
            continue
        w = dict(w, **{k: tuple(v) for k, v in o.items() if k in ('scale', 'offset', 'origin')})
        target = blur if o.get('blur') else dark
        if w['scale'] == (0.0, 0.0):
            print('   WARNING %s: scale 0 (animated by %s?) -- give it a scale' % (name, w['active']))
            continue
        if w['anchor'] not in ('crosshair', 'center'):
            raise SystemExit('%s: anchor %s not handled' % (name, w['anchor']))
        if w['color'] not in ('0', None):
            print('   WARNING %s: colour %s -- a Halo 1 mask can only darken' % (name, w['color']))
        img, boxes = h3_hud_art.decode(w['bitmap'] + '.bitmap')
        if boxes:
            l, r, t, b, _rx, _ry = boxes[w['sequence']]
            W, H = img.size
            img = img.crop((round(l * W), round(t * H), round(r * W), round(b * H)))
        a = np.array(img)[..., 3].astype(np.float64) / 255.0 * (o.get('blur') or 1.0)
        wu, hu = img.width * w['scale'][0], img.height * w['scale'][1]        # units
        cx = w['offset'][0] - w['origin'][0] * wu / 2.0
        cy = w['offset'][1] - w['origin'][1] * hu / 2.0
        # a NEGATIVE scale (the Carbine's blip1, -1.4) flips the sprite about its centre
        if wu < 0:
            a, wu = a[:, ::-1], -wu
        if hu < 0:
            a, hu = a[::-1, :], -hu
        copies = [(1, 1)]
        if 'mirror horizontal' in w['flags']:
            copies.append((-1, 1))
        if 'mirror vertical' in w['flags']:
            copies += [(sx, -1) for sx, _ in list(copies)]
        for sx, sy in copies:
            sw, sh = max(1, round(wu * px_per_u[0])), max(1, round(hu * px_per_u[1]))
            spr = np.array(Image.fromarray((a * 255).astype(np.uint8)).resize((sw, sh), Image.LANCZOS)) / 255.0
            if sx < 0:
                spr = spr[:, ::-1]
            if sy < 0:
                spr = spr[::-1, :]
            x0 = size / 2.0 + (sx * cx - wu / 2.0) * px_per_u[0]
            y0 = size / 2.0 + (sy * cy - hu / 2.0) * px_per_u[1]
            X, Y = int(round(x0)), int(round(y0))
            xa, ya = max(0, X), max(0, Y)
            xb, yb = min(size, X + sw), min(size, Y + sh)
            if xa < xb and ya < yb:
                target[ya:yb, xa:xb] = np.maximum(target[ya:yb, xa:xb], spr[ya - Y:yb - Y, xa - X:xb - X])
            if 'extend border' in w['flags']:
                # beyond the sprite, its OUTER edge value (the quadrant away from the anchor)
                edge = float(spr[-1 if sy > 0 else 0, -1 if sx > 0 else 0])
                xs = slice(min(size, X + sw), size) if sx > 0 else slice(0, max(0, X))
                ys = slice(min(size, Y + sh), size) if sy > 0 else slice(0, max(0, Y))
                xq = slice(max(0, min(size, int(round(size / 2)))), size) if sx > 0 else slice(0, int(round(size / 2)))
                yq = slice(int(round(size / 2)), size) if sy > 0 else slice(0, int(round(size / 2)))
                target[yq, xs] = np.maximum(target[yq, xs], edge)
                target[ys, xq] = np.maximum(target[ys, xq], edge)
        used.append('%s (%s #%d, %d copies%s)' % (name, w['bitmap'].rsplit('\\', 1)[-1], w['sequence'], len(copies),
                                                 ', BLUR x%g' % o['blur'] if o.get('blur') else ''))
    # 'blur_inside' (any widget naming it): the blur only where the mask is DARK -- the
    # Carbine's distortion hexes are larger than the side cells they sit on, and their blur
    # spilled over the cells' bright outline and the lens corners (test 2: 'the outer
    # hexagons look malformed'). Kept in full from darkness `t` up, faded below it
    t = max([o['blur_inside'] for o in per_widget.values() if o.get('blur_inside')] or [0])
    if t:
        blur *= np.clip(dark / t, 0.0, 1.0) ** 2
    return dark, blur, used


def write(dark, out, alpha=255, blur=None):
    """A copy of the pistol's mask tag with this darkness as RGB and a flat `alpha`.
    THE ALPHA (BR tests 2-3): alpha 0 everywhere + convolution radius 0 SMEARED the whole
    zoomed view; the stock pistol and sniper masks are alpha 0 in the lens, 255 outside.
    Test 4: alpha 255 with the donor's own convolution -- what it shows decides whether
    255 is sharp or blurred (an open question until then)."""
    from reclaimer.hek.defs.bitm import bitm_def
    size = dark.shape[0]
    t = bitm_def.build(filepath=os.path.join(TAGS, TEMPLATE + '.bitmap'))
    d = t.data.tagdata
    b = d.bitmaps.STEPTREE[0]
    if (b.format.enum_name, b.mipmaps) != ('a8r8g8b8', 0):
        raise SystemExit('the template is %s +%d mips' % (b.format.enum_name, b.mipmaps))
    if size & (size - 1):
        raise SystemExit('size %d is not a power of 2' % size)
    b.width = b.height = size                    # the template's 512, or larger (BR test 3: 1024)
    b.registration_point_x = b.registration_point_y = size // 2
    v = np.clip(np.round(dark * 255), 0, 255).astype(np.uint8)
    if alpha == 'outside':
        # Halo 1's own style (BR test 5, user: 'keep it' -- every stock zoom does it: pistol,
        # rocket launcher, sniper): blurred OUTSIDE the lens only. Outside = the VIGNETTE
        # region connected to the texture border (flood fill over the vignette's own grey,
        # 0.4..0.65 -- not the ring or the rulers' black bars, which touch the ring and
        # would pull the blur into the lens), its edge softened like the stock gradient
        from PIL import ImageDraw, ImageFilter
        grey = (dark > 0.4) & (dark < 0.65)
        img = Image.fromarray((grey * 255).astype(np.uint8)).copy()  # own buffer: floodfill
        for corner in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
            if img.getpixel(corner) == 255:
                ImageDraw.floodfill(img, corner, 128)
        outer = (np.array(img) == 128).astype(np.uint8) * 255
        a = np.array(Image.fromarray(outer).filter(ImageFilter.GaussianBlur(size / 128.0)))
    else:
        a = np.full_like(v, alpha)
    if blur is not None:                 # widgets turned into blur (bake_maps 'blur')
        a = np.maximum(a, np.clip(np.round(blur * 255), 0, 255).astype(np.uint8))
    bgra = np.stack([v, v, v, a], axis=-1)
    d.processed_pixel_data.data = bytearray(bgra.tobytes())
    p = os.path.join(TAGS, out + '.bitmap')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    t.filepath = p
    t.serialize(temp=False, backup=False)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('chud', help=r'Halo 3 chud, e.g. ui\chud\battle_rifle')
    ap.add_argument('out', nargs='?', help=r'Halo 1 bitmap tag to write (no extension)')
    ap.add_argument('--span', type=float, default=640.0)
    ap.add_argument('--aspect', type=float, default=1.0)
    ap.add_argument('--size', type=int, default=512)
    ap.add_argument('--preview')
    ap.add_argument('--port', help='a ports_h1 key: its hud scope settings (per_widget, size...)')
    a = ap.parse_args()
    kw = {'span': a.span, 'aspect': a.aspect, 'size': a.size}
    if a.port:
        import ports_h1
        S = ports_h1.load(a.port)['pickable']['hud']['scope']
        kw = {'span': S.get('span', 640.0), 'aspect': S.get('aspect', 1.0), 'size': S.get('size', 512),
              'per_widget': S.get('per_widget')}
    dark, blur, used = bake_maps(a.chud, **kw)
    print('baked: ' + '; '.join(used))
    if a.preview:
        bg = np.array(Image.new('RGB', dark.shape[::-1], (120, 160, 110))).astype(np.float64)
        bg[..., 2] += blur * 120                 # the blur map shows as a blue tint
        Image.fromarray(np.clip(bg * (1 - dark[..., None]), 0, 255).astype(np.uint8)).save(a.preview)
        print('preview', a.preview)
    if a.out:
        S = ports_h1.load(a.port)['pickable']['hud']['scope'] if a.port else {}
        print('wrote', write(dark, a.out, alpha=S.get('alpha', 255), blur=blur))


if __name__ == '__main__':
    main()
