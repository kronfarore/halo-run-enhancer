r"""Step 5 of a Halo 2 port: a collision model of its own -- the DONOR's authored hull, scaled
per axis to the port's size (generalized from h2_saw_collision.py, the SAW 2026-09-24).

`tool collision` on a render mesh asserts in reduce_collision_geometry.cpp; `tool
extract-collision-data <donor>` unzips Bungie's own hull, which scales and recompiles cleanly.
Each axis takes the ratio of the two RENDER meshes, clamped to [1.0, max_growth], about the
hull's own centre. The config's `collision` section:

    donor             the donor's tag path (no extension) -- extract-collision-data source
    port              the port's model path (no extension): <port>.model, <port>.collision_model
    src               the extracted hull, under data\!extracted
    out               the port's hull JMS, under data (tool collision builds the tag from its folder)
    port_render_jms   data-relative; donor_render_jms under data\!extracted
    max_growth
    nodes_from_render  True: the hull takes the port's RENDER skeleton (influences remapped by
                      name, else node 0) -- the Spiker, whose own nodes are not the BR donor's

    python h2_port_collision.py <key> [--factor 1.1] [--write]
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_jms  # noqa: E402
import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
DATA = os.path.join(H2EK, 'data')


def extract(c):
    src = os.path.join(DATA, '!extracted', c['src'])
    if not os.path.exists(src):
        subprocess.run([os.path.join(H2EK, 'tool.exe'), 'extract-collision-data', c['donor']],
                       cwd=H2EK, capture_output=True, text=True)
    return h2_jms.read(src)


def extents(model):
    lo = [min(v.pos[k] for v in model.verts) for k in range(3)]
    hi = [max(v.pos[k] for v in model.verts) for k in range(3)]
    return ([(hi[k] - lo[k]) / 2.0 for k in range(3)],
            [(hi[k] + lo[k]) / 2.0 for k in range(3)])


def measure(c):
    port = h2_jms.read(os.path.join(DATA, c['port_render_jms']))
    donor = h2_jms.read(os.path.join(DATA, '!extracted', c['donor_render_jms']))
    a, _ = extents(port)
    b, _ = extents(donor)
    ratio = [a[k] / b[k] for k in range(3)]
    print('   half extents  port %s' % [round(x, 2) for x in a])
    print('                donor %s   ratio %s'
          % ([round(x, 2) for x in b], [round(x, 2) for x in ratio]))
    return [max(1.0, min(c['max_growth'], r)) for r in ratio]


def grow(model, factor, skeleton=None):
    """skeleton: a render JMS whose nodes the hull takes instead of the donor's (influences
    remapped by name, a node the render model lacks -> node 0) -- `nodes_from_render`."""
    _half, mid = extents(model)
    out = h2_jms.Model()
    out.nodes = list(skeleton.nodes if skeleton else model.nodes)
    names = [n.name.lower() for n in out.nodes]
    remap = {i: (names.index(n.name.lower()) if n.name.lower() in names else 0)
             for i, n in enumerate(model.nodes)}
    out.materials = list(model.materials)
    out.tris = list(model.tris)
    out.markers = list(model.markers)
    for v in model.verts:
        pos = tuple(mid[k] + (v.pos[k] - mid[k]) * factor[k] for k in range(3))
        out.verts.append(h2_jms.Vertex(pos, v.normal, [(remap[n], w) for n, w in v.influences], v.uvs))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--factor', type=float, default=None)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    c = ports_h2.get(a.key, 'collision')
    out = os.path.join(DATA, c['out'])
    model = os.path.join(TAGS, c['port'] + '.model')

    hull = extract(c)
    print('donor hull: %d verts, %d tris, materials %s'
          % (len(hull.verts), len(hull.tris), [m.name for m in hull.materials]))
    factor = [a.factor] * 3 if a.factor is not None else measure(c)
    skeleton = (h2_jms.read(os.path.join(DATA, c['port_render_jms'])) if c.get('nodes_from_render')
                else None)
    grown = grow(hull, factor, skeleton)
    if skeleton:
        print('   nodes: the render model\'s %s (the donor\'s %s)'
              % ([n.name for n in grown.nodes], [n.name for n in hull.nodes]))
    before, _ = extents(hull)
    after, _ = extents(grown)
    print('   growing %s: %s -> %s'
          % ([round(f, 3) for f in factor], [round(x, 2) for x in before],
             [round(x, 2) for x in after]))
    if not a.write:
        print('(dry run -- pass --write)')
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    h2_jms.write(out, grown)
    print('   wrote %s' % out)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'collision',
                        os.path.dirname(os.path.dirname(out)).replace(DATA + B, '')],
                       cwd=H2EK, capture_output=True, text=True)
    text = ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10))
    for line in text.split(chr(10)):
        line = ' '.join(line.split())
        if line and ('triangle' in line or 'error' in line.lower() or 'node' in line
                     or 'assert' in line.lower() or 'material' in line):
            print('   | %s' % line)
    made = os.path.join(TAGS, c['port'] + '.collision_model')
    if not os.path.exists(made):
        raise SystemExit('tool collision wrote no tag; the hull did not compile')
    have = h2_tagref.references(model)
    if ('coll', c['port']) in have:
        print('   the model already points at the port hull')
    else:
        h2_tagref.set_reference(model, 'coll', c['donor'], c['port'])


if __name__ == '__main__':
    main()
