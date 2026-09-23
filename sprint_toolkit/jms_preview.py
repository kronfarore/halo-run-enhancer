"""Side (x/z) and top (x/y) views of JMS models overlaid: flat-shaded triangles, one colour
per model; the magazine node's triangles tinted. Markers as dots."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.model.jms.file import read_jms
from PIL import Image, ImageDraw

W, H, PX = 1400, 900, 30          # canvas, pixels per JMS unit
OX, OY = 330, 300                 # origin of the side view


def load(p):
    return read_jms(open(p, encoding='utf-8', errors='replace').read())


def draw(img, jm, colour, mag_colour, axis, oy, alpha):
    d = ImageDraw.Draw(img, 'RGBA')
    mag = next((i for i, n in enumerate(jm.nodes) if n.name == 'frame magazine'), None)
    for t in jm.tris:
        vs = [jm.verts[t.v0], jm.verts[t.v1], jm.verts[t.v2]]
        pts = [(OX + v.pos_x * PX, oy - getattr(v, axis) * PX) for v in vs]
        c = mag_colour if mag is not None and vs[0].node_0 == mag else colour
        d.polygon(pts, fill=c + (alpha,))
    for mk in jm.markers:
        x, y = OX + mk.pos_x * PX, oy - getattr(mk, axis.replace('pos_', 'pos_')) * PX
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 0, 255))
        d.text((x + 5, y - 12), mk.name, fill=(255, 255, 0, 255))


def main(a, b, out):
    img = Image.new('RGB', (W, H), (20, 20, 20))
    ja, jb = load(a), load(b)
    for axis, oy in (('pos_z', OY), ('pos_y', OY + 400)):
        draw(img, jb, (80, 140, 255), (80, 140, 255), axis, oy, 90)      # AR: blue
        draw(img, ja, (255, 120, 60), (60, 220, 90), axis, oy, 70)        # SAW: orange, mag green
    d = ImageDraw.Draw(img)
    d.line((OX, 0, OX, H), fill=(90, 90, 90))
    d.text((10, 10), 'side (x/z) top; top view (x/y) below. SAW orange (box mag green), AR blue; '
                     'grey line = grip origin', fill=(230, 230, 230))
    img.save(out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
