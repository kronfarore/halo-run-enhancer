r"""Look at a Halo 2 JMS before importing it: side (x/z) and top (x/y) views.

`jms_preview.py` reads through Reclaimer, which only speaks JMS 8200, so it cannot open
a Halo 2 file at all. This one goes through `h2_jms.py` and draws the same two views,
flat shaded by facing so the shape reads, with the markers labelled -- the cheapest way
to catch a mesh that came out inside out, scattered across its nodes or at the wrong
scale, before `tool render` turns it into a tag.

    python h2_jms_preview.py <out.png> <model.jms> [more.jms ...]

Several models draw over each other in different colours, which is how a port gets
compared against the donor it has to sit inside.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_jms
from PIL import Image, ImageDraw

W, H, PX = 1500, 940, 26          # canvas, pixels per JMS unit
OX = 420                          # x of the model origin in both views
COLOURS = [(120, 170, 255), (255, 150, 90), (140, 230, 140)]


def shade(colour, tri, verts, axis):
    """Flat shading from the face normal, so curvature is visible in a flat projection."""
    p, q, r = (verts[i].pos for i in tri)
    u = [q[k] - p[k] for k in range(3)]
    v = [r[k] - p[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    length = sum(c * c for c in n) ** 0.5 or 1.0
    # light from the viewer's side of whichever axis is being flattened
    k = 1 if axis == 'y' else 2
    lit = 0.45 + 0.55 * abs(n[k] / length)
    return tuple(int(c * lit) for c in colour)


def draw(img, m, colour, axis, oy, alpha, labels):
    d = ImageDraw.Draw(img, 'RGBA')
    k = 1 if axis == 'y' else 2
    order = sorted(range(len(m.tris)), key=lambda i: -m.verts[m.tris[i][1][0]].pos[k])
    for i in order:
        tri = m.tris[i][1]
        pts = [(OX + m.verts[v].pos[0] * PX, oy - m.verts[v].pos[k] * PX) for v in tri]
        d.polygon(pts, fill=shade(colour, tri, m.verts, axis) + (alpha,))
    for mk in m.markers:
        x, y = OX + mk.pos[0] * PX, oy - mk.pos[k] * PX
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 235, 60, 255))
        if labels:
            d.text((x + 6, y - 12), mk.name, fill=(255, 235, 60, 255))


def main():
    out = sys.argv[1]
    paths = sys.argv[2:]
    img = Image.new('RGB', (W, H), (26, 28, 32))
    d = ImageDraw.Draw(img)
    for oy, axis, title in ((300, 'z', 'side  (x / z)'), (720, 'y', 'top  (x / y)')):
        d.line((0, oy, W, oy), fill=(60, 64, 72))
        d.line((OX, oy - 260, OX, oy + 260), fill=(60, 64, 72))
        d.text((16, oy - 274), title, fill=(150, 156, 168))
    for i, p in enumerate(paths):
        m = h2_jms.read(p)
        colour = COLOURS[i % len(COLOURS)]
        alpha = 255 if len(paths) == 1 else 150
        for oy, axis in ((300, 'z'), (720, 'y')):
            draw(img, m, colour, axis, oy, alpha, labels=(i == 0))
        d.text((16, 16 + i * 18),
               '%s  -  %d verts, %d tris' % (os.path.basename(p), len(m.verts),
                                             len(m.tris)),
               fill=colour)
    img.save(out)
    print('wrote %s' % out)


if __name__ == '__main__':
    main()
