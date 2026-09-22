r"""Render the glyphs of a Halo 3 font package, so the icons can be SEEN.

Until `h3_font_codec` the payloads were opaque, so the only way to find out which private
use codepoint held which picture was to put one in a string and look at it in game. Now
every glyph decodes, and this draws them.

    python h3_font_sheet.py                          # the icon package, one sheet per font
    python h3_font_sheet.py --pkg font_package.bin --font 2
    python h3_font_sheet.py --cp 0xE128 --scale 6 --out saw.png
"""
import argparse, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_font_package as fp                                     # noqa: E402
import h3_font_codec as fc                                       # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

FONTS = fp.FONTS
BG = (24, 26, 30, 255)


def image(payload, w, h):
    im = Image.new('RGBA', (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    px = fc.decode(payload, w, h)
    im.putdata([(r * 17, g * 17, b * 17, a * 17) for a, r, g, b in px])
    return im


def sheet(entries, scale=2, cols=8, pad=6):
    cell_w = max(e[1].width for e in entries) * scale + pad * 2
    cell_h = max(e[1].height for e in entries) * scale + pad * 2 + 12
    rows = (len(entries) + cols - 1) // cols
    out = Image.new('RGBA', (cell_w * cols, cell_h * rows), BG)
    d = ImageDraw.Draw(out)
    for i, (cp, im) in enumerate(entries):
        cx = (i % cols) * cell_w
        cy = (i // cols) * cell_h
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        out.alpha_composite(big, (cx + pad, cy + pad + 12))
        d.text((cx + pad, cy + 2), '%04X' % cp, fill=(150, 200, 255, 255))
        d.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1], outline=(60, 64, 70, 255))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkg', default=fp.PKG)
    ap.add_argument('--font', type=int)
    ap.add_argument('--cp', type=lambda s: int(s, 0))
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--out', default=os.path.join(os.environ.get('TEMP', '.'), 'glyphs'))
    a = ap.parse_args()

    data = io.open(os.path.join(FONTS, a.pkg), 'rb').read()
    g = fp.glyphs(data)
    if a.cp is not None:
        font, w, h, size, at = g[a.cp]
        im = image(data[at + 16:at + 16 + size], w, h)
        im = im.resize((w * a.scale, h * a.scale), Image.NEAREST)
        out = a.out if a.out.endswith('.png') else a.out + '_%04X.png' % a.cp
        bg = Image.new('RGBA', im.size, BG)
        bg.alpha_composite(im)
        bg.save(out)
        print('%04X %dx%d -> %s' % (a.cp, w, h, out))
        return

    by_font = {}
    for cp, (font, w, h, size, at) in sorted(g.items()):
        if a.font is not None and font != a.font:
            continue
        by_font.setdefault(font, []).append(
            (cp, image(data[at + 16:at + 16 + size], w, h)))
    for font, entries in sorted(by_font.items()):
        cols = 8 if max(e[1].width for e in entries) > 40 else 16
        im = sheet(entries, a.scale, cols)
        out = a.out + '_font%d.png' % font
        im.save(out)
        print('font %d: %3d glyphs, up to %dx%d -> %s'
              % (font, len(entries),
                 max(e[1].width for e in entries),
                 max(e[1].height for e in entries), out))


if __name__ == '__main__':
    main()
