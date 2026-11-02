r"""Step 7 of a Halo 2 port: blank scope widgets for a port that does not zoom
(generalized from h2_saw_scope.py, the SAW 2026-09-24 -- its notes stand: the scope widgets
DO draw whatever their `unit is zoomed` gate says, so they get a blank one-image bitmap and every
sequence index 0; the widgets stay in the tag, drawing nothing). A ZOOMING port skips this step
and keeps (or ports) its scope.

The config's `scope` section:
    rel, donor, name   the scope_masks folder, the donor mask bitmap, the port's blank bitmap name
    hud                the port's HUD (kit-relative, with extension)
    widgets            the bitmap widget names to blank
    size               the blank bitmap's size
    disc               (opt-in) a ZOOMING port's mask instead of a blank: one quarter of a dark disc
    art                (opt-in) a ZOOMING port with its SOURCE scope (the DMR, wave B1): Reach's / Halo 3's
                       chud baked by h1_h3_scope into two images, the listed `widgets` otherwise blank.
                       {'chud', 'ring': (chud widget, H2 widget, bitmap name) -- a quarter ring, top-left
                       of the bake, centre at its bottom-right corner, for a widget registered there,
                       mirrored and STRETCHED to the screen quarter; 'span' chud units tall on screen,
                       'aspect' the screen's, 'ring_size' its px --, 'picture': (H2 widget, bitmap name) --
                       every other zoom widget as ONE centred picture, `per_widget` as in h1_h3_scope,
                       'picture_size' px at 'px_per_unit' a chud unit; 'glyphs', 'shaders': a sprite on
                       its own widget in its own colour (the Needle Rifle); 'ring_quarter' (w, h): the
                       ring at the picture's scale instead of stretched; 'rgb': the picture's and
                       glyphs' flat colour (for widget_simple_flash shaders)}

    python h2_port_scope.py <key> [--write]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagfield  # noqa: E402
import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402
from PIL import Image  # noqa: E402

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
TEMP = os.environ.get('TEMP', '.')
# set from the config by setup()
REL = DONOR = NAME = PORT = HUD = None
SCOPE = ()
SIZE = None
DISC = None
ART = None


def setup(key):
    global REL, DONOR, NAME, PORT, HUD, SCOPE, SIZE, DISC, ART
    c = ports_h2.get(key, 'scope')
    REL, DONOR, NAME = c['rel'], c['donor'], c['name']
    PORT = B.join([REL, NAME])
    HUD = os.path.join(TAGS, c['hud'])
    SCOPE, SIZE = tuple(c['widgets']), tuple(c['size'])
    DISC = c.get('disc')
    ART = c.get('art')


def widgets(tag):
    """(index, name, bitmap, [sequence indices]) for every bitmap widget."""
    out = os.path.join(TEMP, '_scope_hud.xml')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.abspath(tag), out], cwd=H2EK, capture_output=True, text=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    seg = x[x.index('<block name="bitmap widgets"'):]
    if '<block name="text widgets"' in seg:
        seg = seg[:seg.index('<block name="text widgets"')]
    parts = re.split(r'<element index="(\d+)"[^>]*>', seg)
    rows = []
    for k in range(1, len(parts) - 1, 2):
        b = parts[k + 1]
        nm = re.search(r'string id">([^<]+)<', b)
        ref = re.search(r'type="bitm">([^<]+)<', b)
        sq = re.findall(r'name="(fullscreen|halfscreen|quarterscreen) sequence index"'
                        r'[^>]*>(-?\d+)', b)
        if nm and ref:
            rows.append((int(parts[k]), nm.group(1), ref.group(1),
                         [int(v) for _f, v in sq]))
    return rows


def blank():
    """A bitmap with nothing in it, for a widget that must not draw."""
    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, NAME + '.tif')
    img = Image.new('RGBA', SIZE, (0, 0, 0, 0))
    if DISC:
        # `disc` {'radius', 'alpha', 'rim', 'rim_width'} (the Spartan Laser, A2 -- a ZOOMING port
        # with Halo 3's scope look: a translucent dark disc round the crosshair, a darker rim, the
        # world clear outside): ONE QUARTER, its centre the image's bottom-right corner -- the
        # beam rifle's mask widget registers at (1, 1) and mirrors it both ways
        import numpy as np
        w, h = SIZE
        yy, xx = np.mgrid[0:h, 0:w]
        R, rw = float(DISC['radius']), float(DISC.get('rim_width', 3))
        # 'ry' (boot 3): the widget's `(scope) stretch` flag stretches the quarter to the SCREEN
        # quarter, so a disc round on screen is an ellipse in the image (radius in x, ry in y)
        ky = R / float(DISC.get('ry', R))
        r = np.hypot(w - 0.5 - xx, (h - 0.5 - yy) * ky)
        out = DISC.get('outside', 0.0)           # 'outside' (boot 3: 'not darkened outside the scope')
        a = np.where(r <= R - rw, DISC['alpha'], out)
        a = np.where((r > R - rw) & (r <= R), DISC.get('rim', DISC['alpha']), a)
        edge = (r > R) & (r <= R + 1)                 # a one-pixel antialiased outer edge
        rim = DISC.get('rim', DISC['alpha'])
        a = np.where(edge, rim + (out - rim) * (r - R), a)
        px = np.zeros((h, w, 4), np.uint8)
        px[:, :, 3] = np.clip(a * 255.0, 0, 255).astype(np.uint8)
        img = Image.fromarray(px, 'RGBA')
    img.save(tif, compression=None)
    dest = os.path.join(TAGS, PORT + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, DONOR + '.bitmap'), dest)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', REL],
                       cwd=H2EK, capture_output=True, text=True)
    for line in ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10)).split(chr(10)):
        line = ' '.join(line.split())
        if NAME in line or 'bitmap created' in line:
            print('   | %s' % line)
    return os.path.exists(dest)


def art_images():
    """`art`: the two tifs + their seeded tags; {H2 widget: bitmap path}."""
    import numpy as np
    import h1_h3_scope
    a = ART
    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    ring_w, ring_h2, ring_name = a['ring']
    pic_h2, pic_name = a['picture']
    names = [n for n, _w in h1_h3_scope.widgets(a['chud'])]
    only_ring = {n: {'drop': True} for n in names if n != ring_w}
    if a.get('ring_quarter'):
        # `ring_quarter` (w, h) px (the Needle Rifle, boot 1: the stretch flag left a 512 square at the
        # picture's 1.117 screen px a bitmap px -- the ring tall and narrow): the quarter at the picture's
        # scale, as big as the screen quarter
        w, h = a['ring_quarter']
        n = 2 * max(w, h)
        dark, used = h1_h3_scope.bake(a['chud'], n, n / float(a['px_per_unit']), 1.0, only_ring)
        ring = dark[n // 2 - h:n // 2, n // 2 - w:n // 2]
    else:
        q = a['ring_size']
        dark, used = h1_h3_scope.bake(a['chud'], q * 2, a['span'], a['aspect'], only_ring)
        ring = dark[:q, :q]
    # `rgb` (the Needle Rifle): the picture's and the glyphs' flat colour -- a widget_simple_flash shader
    # tints the shape in the alpha (Halo 2's reticle convention: flat blue); the ring stays black
    rgb = a.get('rgb')
    per = dict(a.get('per_widget', {}), **{ring_w: {'drop': True}})
    s = a['picture_size']
    pic, used2 = h1_h3_scope.bake(a['chud'], s, s / float(a['px_per_unit']), 1.0, per)
    for name, img in ((ring_name, ring), (pic_name, pic)):
        px = np.zeros(img.shape + (4,), np.uint8)
        if rgb and name == pic_name:
            px[:, :, :3] = rgb
        px[:, :, 3] = np.clip(img * 255.0, 0, 255).astype(np.uint8)
        Image.fromarray(px, 'RGBA').save(os.path.join(data, name + '.tif'), compression=None)
        dest = os.path.join(TAGS, REL, name + '.bitmap')
        if not os.path.exists(dest):
            shutil.copy(os.path.join(TAGS, DONOR + '.bitmap'), dest)
    print('   ring:', [u for u in used if 'DROPPED' not in u])
    print('   picture:', [u for u in used2 if 'DROPPED' not in u])
    own = {ring_h2: B.join([REL, ring_name]), pic_h2: B.join([REL, pic_name])}
    # `glyphs` [(H2 widget, bitmap name, (sheet, sequence), (w, h), alpha, gamma)] (the Needle Rifle): a
    # source sprite on its own widget, the shape alone: its colour is the widget's shader (`shaders`)
    for widget, name, (sheet, seq), size, alpha, gamma in a.get('glyphs', ()):
        import h3_hud_art
        g = h3_hud_art.sprite(sheet, seq, native=True)[0].convert('RGBA').resize(size, Image.LANCZOS)
        v = np.asarray(g).astype(float)[:, :, 3] / 255.0
        px = np.zeros(v.shape + (4,), np.uint8)
        if rgb:
            px[:, :, :3] = rgb
        px[:, :, 3] = np.clip((v / max(v.max(), 1e-6)) ** gamma * alpha * 255.0, 0, 255).astype(np.uint8)
        Image.fromarray(px, 'RGBA').save(os.path.join(data, name + '.tif'), compression=None)
        dest = os.path.join(TAGS, REL, name + '.bitmap')
        if not os.path.exists(dest):
            shutil.copy(os.path.join(TAGS, DONOR + '.bitmap'), dest)
        own[widget] = B.join([REL, name])
    return own


def widget_shaders():
    """`shaders` {H2 widget: shader tag} (the Needle Rifle's coloured glyphs): the widget's shader
    repointed, the copies counted in widget order."""
    x = h2_tagfield.export(HUD)
    seg = x[x.index('<block name="bitmap widgets"'):]
    seg = seg[:seg.index('<block name="text widgets"')] if '<block name="text widgets"' in seg else seg
    rows = re.findall(r'<field name="name" type="string id">([^<]+)<.*?<tag_reference name="shader" type="shad">'
                      r'([^<]*)<', seg, re.S)
    moved = 0
    for k, (name, shader) in enumerate(rows):
        new = ART['shaders'].get(name)
        if new and new != shader:
            nth = sum(1 for n, s in rows[:k] if s == shader and ART['shaders'].get(n) in (None, s))
            h2_tagref.set_reference(HUD, 'shad', shader, new, nth=nth)
            moved += 1
    return moved


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    setup(a.key)

    before = widgets(HUD)
    targets = [r for r in before if r[1] in SCOPE]
    print('scope widgets in the port HUD:')
    for idx, name, ref, sq in targets:
        print('   %2d %-18s %-28s %s' % (idx, name, ref.split(B)[-1], sq))
    if not a.write:
        print('(dry run -- pass --write)')
        return

    own = art_images() if ART else {}
    blank()
    have = h2_tagref.references(HUD)
    if ('bitm', DONOR) in have:
        try:
            h2_tagref.set_reference(HUD, 'bitm', DONOR, PORT, every=True)
        except ValueError:
            # every=True refuses when other records have the path's length (the beam rifle HUD's
            # mask, the Spartan Laser A2 -- as h2_port_hud_plate's plate): one copy at a time
            for _k in range(have.count(('bitm', DONOR))):
                h2_tagref.set_reference(HUD, 'bitm', DONOR, PORT, nth=0)
    else:
        print('   the HUD already names no donor scope mask')

    # `art`: the two widgets off the blank, the k-th copy of its path in widget order
    k = 0
    for idx, name, ref, _sq in widgets(HUD):
        if ref != PORT:
            continue
        if name in own:
            h2_tagref.set_reference(HUD, 'bitm', PORT, own[name], nth=k)
        else:
            k += 1

    for idx, name, _ref, _sq in targets:
        for field in ('fullscreen', 'halfscreen', 'quarterscreen'):
            key = field + ' sequence index'
            now = h2_tagfield.get(HUD, key, 'bitmap widgets', idx)
            if now and int(now[0]) == 0:
                continue
            h2_tagfield.set_field(HUD, key, 0, 'bitmap widgets', idx)
    if ART and ART.get('shaders'):
        print('   widget shaders repointed: %d' % widget_shaders())

    print('after:')
    for idx, name, ref, sq in widgets(HUD):
        print('   %2d %-18s %-28s %s' % (idx, name, ref.split(B)[-1], sq))


if __name__ == '__main__':
    main()
