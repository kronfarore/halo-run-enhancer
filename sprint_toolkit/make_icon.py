"""Halo 1 pickup-prompt icon for a ported weapon, drawn from its own JMS in the style of
the stock icons (hud_msg_icons): light outlines of every part (235 grey, alpha ~230) over
a dark see-through fill (79 grey, alpha ~59), muzzle to the right.

Side view (x right, z up), painter's-order flat shading by normal; the part outlines are
the shading's edges plus the silhouette.

    python make_icon.py <model.jms> <out.png> [height px, default 132]
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.model.jms.file import read_jms

SS = 4                      # supersampling
EDGE = 70                   # shading-edge threshold: higher = fewer, cleaner lines


def main(jms_path, out, height=132):
    jm = read_jms(open(jms_path, encoding='utf-8', errors='replace').read())
    P = np.array([(v.pos_x, v.pos_y, v.pos_z) for v in jm.verts])
    xs, zs = P[:, 0], P[:, 2]
    pad = 0.06
    w_units, h_units = xs.max() - xs.min(), zs.max() - zs.min()
    H = height * SS
    scale = H * (1 - 2 * pad) / h_units
    W = int(w_units * scale + 2 * pad * H)
    ox, oz = pad * H - xs.min() * scale, H - pad * H + zs.min() * scale

    def px(p):
        return (ox + p[0] * scale, oz - p[2] * scale)

    shade = Image.new('L', (W, H), 0)
    mask = Image.new('L', (W, H), 0)
    ds, dm = ImageDraw.Draw(shade), ImageDraw.Draw(mask)
    tris = []
    for t in jm.tris:
        a, b, c = P[t.v0], P[t.v1], P[t.v2]
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln == 0:
            continue
        n = n / ln
        depth = (a[1] + b[1] + c[1]) / 3.0          # viewer on -y: nearer = smaller y
        tris.append((depth, a, b, c, n))
    tris.sort(key=lambda t: -t[0])                    # far first
    light = np.array([0.3, -0.8, 0.5])
    light /= np.linalg.norm(light)
    for depth, a, b, c, n in tris:
        s = int(40 + 215 * abs(float(np.dot(n, light))))
        pts = [px(a), px(b), px(c)]
        ds.polygon(pts, fill=s)
        dm.polygon(pts, fill=255)
    edges = shade.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > EDGE else 0)
    sil = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 0 else 0)
    lines = Image.fromarray(np.maximum(np.array(edges), np.array(sil)))
    lines = lines.filter(ImageFilter.MaxFilter(2 * SS - 1))
    # compose at supersampled size, then shrink
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fill = Image.new('RGBA', (W, H), (79, 79, 79, 59))
    img.paste(fill, (0, 0), mask)
    line_rgba = Image.new('RGBA', (W, H), (235, 235, 235, 230))
    img.paste(line_rgba, (0, 0), lines)
    img = img.resize((W // SS, H // SS), Image.LANCZOS)
    img.save(out)
    prev = Image.new('RGBA', (img.width * 2, img.height * 2), (40, 60, 90, 255))
    prev.alpha_composite(img.resize(prev.size))
    prev.save(out.replace('.png', '_preview.png'))
    print(out, img.size)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *(int(x) for x in sys.argv[3:4]))
