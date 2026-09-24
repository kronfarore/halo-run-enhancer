r"""A collision model of the port's own, grown to the size of the gun it is wrapped round.

The port shipped using the GPMG's `collision_model` outright, because `tool collision` on
the render mesh asserts in `reduce_collision_geometry.cpp` -- a Halo 2 collision hull has
to be closed, convex-ish and simple, and a 13836-triangle weapon is none of those. That
is still true and is not what this does.

What it does instead is take **Bungie's own authored hull** back out of the donor tag
(`tool extract-collision-data` unzips it the same way `extract-render-data` unzips the
render source) and scale it. That keeps every property that makes it compile -- the same
closed shape, the same node weighting, the same material names -- and changes only how
big it is. The port then owns the tag rather than borrowing one, which matters the moment
the GPMG is restored.

**The factor is measured, not chosen, and it is one per axis.** The two render meshes are
compared axis by axis: the port is half again as WIDE as the donor and a tenth taller, but
it is also the SHORTER gun, so a single factor big enough for the width would stretch the
hull a third of a gun past the muzzle. Each axis therefore takes its own ratio, clamped to
[1.0, MAX_GROWTH] -- the hull never shrinks below the one Bungie authored, and never grows
so far past the silhouette that the weapon catches on scenery its model is nowhere near.

The hull is scaled about its OWN centre, not the origin, so it grows outwards evenly and
does not drift off the grip.

    python h2_saw_collision.py [--factor 1.1] [--write]
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_jms
import h2_tagref

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
DATA = os.path.join(H2EK, 'data')
DONOR = B.join(['objects', 'weapons', 'rifle', 'gpmg', 'gpmg'])
PORT = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
SRC = os.path.join(DATA, '!extracted', 'gpmg', 'collision', 'collision.JMS')
OUT = os.path.join(DATA, 'objects', 'weapons', 'rifle', 'saw', 'collision', 'saw.jms')
MODEL = os.path.join(TAGS, PORT + '.model')

#: How much bigger than the donor's the hull may get. A weapon that collides well past
#: its own silhouette catches on doorframes and rests wrong on the ground.
MAX_GROWTH = 1.25


def extract():
    """Bungie's authored hull, out of the donor's tag."""
    if not os.path.exists(SRC):
        subprocess.run([os.path.join(H2EK, 'tool.exe'), 'extract-collision-data', DONOR],
                       cwd=H2EK, capture_output=True, text=True)
    return h2_jms.read(SRC)


def extents(model):
    """(half extent per axis, centre per axis) of a JMS's vertices."""
    lo = [min(v.pos[k] for v in model.verts) for k in range(3)]
    hi = [max(v.pos[k] for v in model.verts) for k in range(3)]
    return ([(hi[k] - lo[k]) / 2.0 for k in range(3)],
            [(hi[k] + lo[k]) / 2.0 for k in range(3)])


def measure():
    """How much bigger the port's gun is than the donor's, over the three axes."""
    port = h2_jms.read(os.path.join(DATA, 'objects', 'weapons', 'rifle', 'saw',
                                    'render', 'saw.jms'))
    donor = h2_jms.read(os.path.join(DATA, '!extracted', 'gpmg', 'render', 'L5_gpmg.jms'))
    a, _ = extents(port)
    b, _ = extents(donor)
    ratio = [a[k] / b[k] for k in range(3)]
    print('   half extents  port %s' % [round(x, 2) for x in a])
    print('                donor %s   ratio %s'
          % ([round(x, 2) for x in b], [round(x, 2) for x in ratio]))
    return [max(1.0, min(MAX_GROWTH, r)) for r in ratio]


def grow(model, factor):
    """The hull scaled about its own centre, one factor per axis."""
    _half, mid = extents(model)
    out = h2_jms.Model()
    out.nodes = list(model.nodes)
    out.materials = list(model.materials)
    out.tris = list(model.tris)
    out.markers = list(model.markers)
    for v in model.verts:
        pos = tuple(mid[k] + (v.pos[k] - mid[k]) * factor[k] for k in range(3))
        out.verts.append(h2_jms.Vertex(pos, v.normal, v.influences, v.uvs))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--factor', type=float, default=None,
                    help='one factor for all three axes, instead of the measured ones')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    hull = extract()
    print('donor hull: %d verts, %d tris, materials %s'
          % (len(hull.verts), len(hull.tris), [m.name for m in hull.materials]))
    factor = [a.factor] * 3 if a.factor is not None else measure()
    grown = grow(hull, factor)
    before, _ = extents(hull)
    after, _ = extents(grown)
    print('   growing %s: %s -> %s'
          % ([round(f, 3) for f in factor], [round(x, 2) for x in before],
             [round(x, 2) for x in after]))
    if not a.write:
        print('(dry run -- pass --write)')
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    h2_jms.write(OUT, grown)
    print('   wrote %s' % OUT)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'collision',
                        os.path.dirname(os.path.dirname(OUT)).replace(DATA + B, '')],
                       cwd=H2EK, capture_output=True, text=True)
    text = ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10))
    for line in text.split(chr(10)):
        line = ' '.join(line.split())
        if line and ('triangle' in line or 'error' in line.lower() or 'node' in line
                     or 'assert' in line.lower() or 'material' in line):
            print('   | %s' % line)
    made = os.path.join(TAGS, PORT + '.collision_model')
    if not os.path.exists(made):
        raise SystemExit('tool collision wrote no tag; the hull did not compile')
    have = h2_tagref.references(MODEL)
    if ('coll', PORT) in have:
        print('   the model already points at the port hull')
    else:
        h2_tagref.set_reference(MODEL, 'coll', DONOR, PORT)


if __name__ == '__main__':
    main()
