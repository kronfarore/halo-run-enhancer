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

The mask spans `span` chud units square (640: the screen height, the pistol mask's own
convention -- its ring is round in the square texture), `size` px; the blur is switched
off (Halo 3 does not blur). make_hud (h1_pickable_weapons, hud['scope']) points the
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
    """[(name, fields)] of every bitmap widget of a Halo 3 chud_definition."""
    s = io.open(h1_fp_retarget.export_xml(chud + '.chud_definition'), encoding='utf-8',
                errors='replace').read()
    out = []
    parts = re.split(r'<element index="\d+" name="([^"]+)">\s*<field name="base" value=" " type="struct"/>', s)
    for name, body in zip(parts[1::2], parts[2::2]):
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
            'zoom': int(zm.group(1)) if zm else 0, 'color': g('custom color A'), 'flags': flags}))
    return out


def zoom_only(w):
    return w['zoom'] and not (w['zoom'] & 1)        # bit 0 = unzoomed


def bake(chud, size=512, span=640.0, aspect=1.0):
    """The darkness image (float 0..1, size x size) of the chud's zoom-only widgets."""
    dark = np.zeros((size, size))
    px_per_u = (size / (span * aspect), size / span)   # x, y
    used = []
    for name, w in widgets(chud):
        if not zoom_only(w) or 'hud_reticles' in w['bitmap']:
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
        a = np.array(img)[..., 3].astype(np.float64) / 255.0
        wu, hu = img.width * w['scale'][0], img.height * w['scale'][1]        # units
        cx = w['offset'][0] - w['origin'][0] * wu / 2.0
        cy = w['offset'][1] - w['origin'][1] * hu / 2.0
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
                dark[ya:yb, xa:xb] = np.maximum(dark[ya:yb, xa:xb], spr[ya - Y:yb - Y, xa - X:xb - X])
            if 'extend border' in w['flags']:
                # beyond the sprite, its OUTER edge value (the quadrant away from the anchor)
                edge = float(spr[-1 if sy > 0 else 0, -1 if sx > 0 else 0])
                xs = slice(min(size, X + sw), size) if sx > 0 else slice(0, max(0, X))
                ys = slice(min(size, Y + sh), size) if sy > 0 else slice(0, max(0, Y))
                xq = slice(max(0, min(size, int(round(size / 2)))), size) if sx > 0 else slice(0, int(round(size / 2)))
                yq = slice(int(round(size / 2)), size) if sy > 0 else slice(0, int(round(size / 2)))
                dark[yq, xs] = np.maximum(dark[yq, xs], edge)
                dark[ys, xq] = np.maximum(dark[ys, xq], edge)
        used.append('%s (%s #%d, %d copies)' % (name, w['bitmap'].rsplit('\\', 1)[-1], w['sequence'], len(copies)))
    return dark, used


def write(dark, out):
    """A copy of the pistol's mask tag with this darkness as RGB, alpha 0 (no blur)."""
    from reclaimer.hek.defs.bitm import bitm_def
    size = dark.shape[0]
    t = bitm_def.build(filepath=os.path.join(TAGS, TEMPLATE + '.bitmap'))
    d = t.data.tagdata
    b = d.bitmaps.STEPTREE[0]
    if (b.width, b.height, b.format.enum_name, b.mipmaps) != (size, size, 'a8r8g8b8', 0):
        raise SystemExit('the template is %dx%d %s +%d mips' % (b.width, b.height, b.format.enum_name, b.mipmaps))
    v = np.clip(np.round(dark * 255), 0, 255).astype(np.uint8)
    bgra = np.stack([v, v, v, np.zeros_like(v)], axis=-1)
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
    ap.add_argument('--preview')
    a = ap.parse_args()
    dark, used = bake(a.chud, span=a.span, aspect=a.aspect)
    print('baked: ' + '; '.join(used))
    if a.preview:
        bg = np.array(Image.new('RGB', dark.shape[::-1], (120, 160, 110))).astype(np.float64)
        Image.fromarray((bg * (1 - dark[..., None])).astype(np.uint8)).save(a.preview)
        print('preview', a.preview)
    if a.out:
        print('wrote', write(dark, a.out))


if __name__ == '__main__':
    main()
