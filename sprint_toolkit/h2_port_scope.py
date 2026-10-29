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


def setup(key):
    global REL, DONOR, NAME, PORT, HUD, SCOPE, SIZE, DISC
    c = ports_h2.get(key, 'scope')
    REL, DONOR, NAME = c['rel'], c['donor'], c['name']
    PORT = B.join([REL, NAME])
    HUD = os.path.join(TAGS, c['hud'])
    SCOPE, SIZE = tuple(c['widgets']), tuple(c['size'])
    DISC = c.get('disc')


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

    for idx, name, _ref, _sq in targets:
        for field in ('fullscreen', 'halfscreen', 'quarterscreen'):
            key = field + ' sequence index'
            now = h2_tagfield.get(HUD, key, 'bitmap widgets', idx)
            if now and int(now[0]) == 0:
                continue
            h2_tagfield.set_field(HUD, key, 0, 'bitmap widgets', idx)

    print('after:')
    for idx, name, ref, sq in widgets(HUD):
        print('   %2d %-18s %-28s %s' % (idx, name, ref.split(B)[-1], sq))


if __name__ == '__main__':
    main()
