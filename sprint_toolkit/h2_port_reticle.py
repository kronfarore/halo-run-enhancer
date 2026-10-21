r"""Step 7 of a Halo 2 port: the SOURCE game's crosshair, as the port's own one-image bitmap
(generalized from h2_saw_reticle.py, the SAW 2026-09-24 -- its notes stand: Halo 4 specifies a
reticle exactly in its .cui_screen (bitmap, left/top/width/height, flips, opacity); Halo 2
keeps its own colour convention (flat blue, the shape in the alpha, the widget tints it); the
port's own bitmap means every crosshair widget's sequence index becomes 0).

The config's `reticle` section:
    rel, donor, donor_sequence   the crosshairs folder, the shared sheet, the donor's sequence
    name, hud                    the port's bitmap name, the HUD repointed at it (every copy)
    footprint                    share of the donor's footprint the art fills (0.6 for the SAW)
    h4_art, layout               Halo 4 art folder + [(bitmap, left, top, w, h, flipx, flipy, opacity)]
    preview                      preview file name in %TEMP%
    h3_art                       a HALO 3 source instead (the AR, 2026-10-20): {'sheet': the H3
                                 chud sheet, 'sequence': the port's sprite, 'yardstick': the
                                 sprite of the weapon whose Halo 2 crosshair the donor's is (the
                                 same chud widget scale)} -- sized by the ratio rule: the port's
                                 sprite x (donor ink / yardstick sprite ink) (h3_compose)
A Reach source: wave B's pilot adds its art reader. Every crosshair widget naming the port's
bitmap gets its three sequence indices set to 0 (a one-image bitmap; the SAW's were already 0).

    python h2_port_reticle.py <key> [--write]
"""
import argparse
import glob
import os
import re
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
H4EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H4EK')
TAGS = os.path.join(H2EK, 'tags')
TEMP = os.environ.get('TEMP', '.')
# set from the config by setup()
REL = DONOR = NAME = PORT = HUD = H4_ART = PREVIEW = None
DONOR_SEQUENCE = FOOTPRINT = None
LAYOUT = []
H3_ART = {}


def setup(key):
    global REL, DONOR, NAME, PORT, HUD, H4_ART, PREVIEW, DONOR_SEQUENCE, FOOTPRINT, LAYOUT
    r = ports_h2.get(key, 'reticle')
    REL, DONOR, NAME, HUD, H4_ART = r['rel'], r['donor'], r['name'], r['hud'], r.get('h4_art')
    PORT = B.join([REL, NAME])
    DONOR_SEQUENCE, FOOTPRINT = r['donor_sequence'], r['footprint']
    LAYOUT = [tuple(x) for x in r.get('layout', ())]
    H3_ART.clear()
    H3_ART.update(r.get('h3_art') or {})
    PREVIEW = r.get('preview', NAME + '_preview.png')


def h4_art(name):
    """One of the Halo 4 reticle bitmaps, decoded to RGBA."""
    out = os.path.join(TEMP, 'h4_%s.png' % name)
    if not os.path.exists(out):
        tag = os.path.join(H4EK, 'tags', H4_ART, name + '.bitmap')
        meta = os.path.join(TEMP, 'h4_%s.xml' % name)
        subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml', tag, meta],
                       cwd=H4EK, capture_output=True, text=True)
        x = open(meta, encoding='utf-8', errors='replace').read()
        w = int(re.search(r'name="width" value="(\d+)"', x).group(1))
        h = int(re.search(r'name="height" value="(\d+)"', x).group(1))
        fmt = re.search(r'name="format" value="([^"]+)"', x).group(1)
        mips = int(re.search(r'name="mipmap count" value="(\d+)"', x).group(1))
        subprocess.run([sys.executable, os.path.join(HERE, 'h4_bitmap.py'), tag,
                        str(w), str(h), fmt, str(max(mips, 1)), out],
                       capture_output=True, text=True)
    return Image.open(out).convert('RGBA')


def donor_image(index=None):
    """The reticle the port is replacing, for its size and its colour."""
    index = DONOR_SEQUENCE if index is None else index
    pre = os.path.join(TEMP, '_ret_')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', DONOR, pre],
                   cwd=H2EK, capture_output=True, text=True)
    files = sorted(glob.glob(pre + os.path.basename(DONOR) + '_*.tga'))
    return Image.open(files[index]).convert('RGBA')


def compose(donor):
    """Halo 4's reticle, at the size and in the colour Halo 2 draws the donor's."""
    w, h = donor.size
    a = np.asarray(donor)
    ink = a[:, :, 3] > 0
    colour = a[:, :, :3][ink].mean(0) if ink.any() else np.array([0, 0, 202.0])

    # Halo 4 lays the reticle out in a box 72 units across (-36..+36). Scale that to the
    # donor's own footprint so the crosshair is the same size on screen as the one it
    # replaces -- the widget's box is not changing.
    scale = w * FOOTPRINT / 72.0
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    cx, cy = w / 2.0, h / 2.0
    for name, left, top, bw, bh, fx, fy, opacity in LAYOUT:
        art = h4_art(name)
        if fx:
            art = art.transpose(Image.FLIP_LEFT_RIGHT)
        if fy:
            art = art.transpose(Image.FLIP_TOP_BOTTOM)
        art = art.resize((max(int(round(bw * scale)), 1), max(int(round(bh * scale)), 1)),
                         Image.LANCZOS)
        # Halo 4's art is white with the shape in the alpha; Halo 2's is flat blue with
        # the shape in the alpha. Keep the coverage, take the donor's colour.
        px = np.asarray(art).astype(float)
        px[:, :, 0], px[:, :, 1], px[:, :, 2] = colour[0], colour[1], colour[2]
        px[:, :, 3] *= opacity
        piece = Image.fromarray(px.astype('uint8'), 'RGBA')
        out.alpha_composite(piece, (int(round(cx + left * scale)),
                                    int(round(cy + top * scale))))
    return out


def _ink(img):
    a = np.asarray(img)[:, :, 3] > 8
    ys, xs = np.nonzero(a)
    return max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)


def h3_compose(donor):
    """A Halo 3 chud sprite (white, the shape in the alpha) at Halo 2's size by the ratio rule,
    in the donor's colour, centred on its registration point."""
    import h3_hud_art
    a = np.asarray(donor)
    ink = a[:, :, 3] > 0
    colour = a[:, :, :3][ink].mean(0) if ink.any() else np.array([0, 0, 202.0])
    art, reg = h3_hud_art.sprite(H3_ART['sheet'], H3_ART['sequence'])
    yard, _ = h3_hud_art.sprite(H3_ART['sheet'], H3_ART['yardstick'])
    k = _ink(donor) / float(_ink(yard))
    if H3_ART.get('target_ink'):
        # an ON-SCREEN size measured in game instead (the AR, boot 2: Halo 3's 72 px at 1080p)
        k = H3_ART['target_ink'] / float(_ink(art))
    w, h = max(1, int(round(art.width * k))), max(1, int(round(art.height * k)))
    art = art.resize((w, h), Image.LANCZOS)
    side = max(w, h, donor.width, donor.height)
    side += side % 2
    out = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    px = np.asarray(art).astype(float)
    px[:, :, 0], px[:, :, 1], px[:, :, 2] = colour[0], colour[1], colour[2]
    piece = Image.fromarray(px.astype('uint8'), 'RGBA')
    out.alpha_composite(piece, (int(round(side / 2.0 - reg[0] * k)),
                                int(round(side / 2.0 - reg[1] * k))))
    print('   Halo 3 sprite %s #%d x %.3f (donor ink %d / yardstick #%d ink %d) -> %dx%d on %dx%d'
          % (H3_ART['sheet'], H3_ART['sequence'], k, _ink(donor), H3_ART['yardstick'],
             _ink(yard), w, h, side, side))
    return out


def sequence_indices(tag):
    """Every crosshair widget's three sequence index fields, as tool.exe reports them."""
    out = os.path.join(TEMP, '_hud_seq.xml')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.abspath(tag), out], cwd=H2EK, capture_output=True, text=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    seg = x[x.index('<block name="bitmap widgets"'):]
    if '<block name="text widgets"' in seg:
        seg = seg[:seg.index('<block name="text widgets"')]
    rows = []
    for part in re.split(r'<element index="(\d+)"[^>]*>', seg)[1:]:
        nm = re.search(r'string id">([^<]+)<', part)
        ref = re.search(r'type="bitm">([^<]+)<', part)
        sq = re.findall(r'name="(fullscreen|halfscreen|quarterscreen) sequence index"'
                        r'[^>]*>(-?\d+)', part)
        if nm and ref and sq:
            rows.append((nm.group(1), ref.group(1), [int(v) for _k, v in sq]))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    setup(a.key)

    donor = donor_image()
    art = h3_compose(donor) if H3_ART else compose(donor)
    d = np.asarray(donor)
    n = np.asarray(art)
    print('donor reticle %dx%d, %d ink pixels; the port\'s %d'
          % (donor.width, donor.height, int((d[:, :, 3] > 0).sum()),
             int((n[:, :, 3] > 0).sum())))

    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, NAME + '.tif')
    art.save(tif, compression=None)
    print('   wrote %s' % tif)
    png = os.path.join(TEMP, PREVIEW)
    Image.alpha_composite(Image.new('RGBA', art.size, (20, 20, 24, 255)), art).save(png)
    print('   preview %s' % png)
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
    if ('bitm', PORT) in have:
        print('   the HUD already points at the port reticle')
    else:
        h2_tagref.set_reference(hud, 'bitm', DONOR, PORT, every=True)
    import h2_port_scope
    import h2_tagfield
    for idx, _name, ref, seq in h2_port_scope.widgets(hud):
        if ref == PORT and any(seq):
            for field in ('fullscreen', 'halfscreen', 'quarterscreen'):
                h2_tagfield.set_field(hud, field + ' sequence index', 0, 'bitmap widgets', idx)
    print('the crosshair widgets now read:')
    for name, ref, seq in sequence_indices(hud):
        if 'reticle' in ref or 'crosshair' in name:
            print('   %-22s %-46s %s' % (name, ref.split(B)[-1], seq))


if __name__ == '__main__':
    main()
