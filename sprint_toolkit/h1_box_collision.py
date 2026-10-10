r"""A port's OWN Halo 1 collision model from boxes (HCEEK `tool collision-geometry`).

Written for the Gravity Hammer (boot 1, 2026-10-10): it was built on a copy of the plasma
pistol, whose small collision model (nodes `frame gun` ...) it kept -- a dropped hammer, 0.67 wu
long, rested on a pistol-sized hull and SANK into the ground. A port whose shape is far from
its template's needs its own hull; a few boxes are enough for an item resting on the ground.

The JMS takes the port's world model JMS (its nodes, so the collision nodes match the render
model's) with the geometry replaced by the config's boxes (world units, model space, every
vertex on node 0), one material; written to data\<dir>\physics\<name>.jms and compiled.
Config: ports_h1/<key>.py model['collision'] = {'material': 'metal', 'boxes': [(min xyz, max
xyz), ...]}; the weapon tag points at the result through pickable['fields'].

    python h1_box_collision.py gravity_hammer [--write]
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.model.jms.file import (JmsMaterial, JmsTriangle, JmsVertex, read_jms,  # noqa: E402
                                      write_jms)
import ports_h1  # noqa: E402

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
JMS_SCALE = 100.0                     # JMS units per world unit
# the 12 triangles of a box, corners indexed by (x, y, z) bits, wound outward
FACES = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]


def box_jms(world_jms, boxes, material):
    jm = read_jms(open(world_jms, encoding='utf-8', errors='replace').read())
    jm.materials[:] = [JmsMaterial(material)]
    jm.markers[:] = []
    jm.verts[:] = []
    jm.tris[:] = []
    region = 0
    for lo, hi in boxes:
        base = len(jm.verts)
        for i in range(8):
            p = [(hi if i >> k & 1 else lo)[k] * JMS_SCALE for k in range(3)]
            jm.verts.append(JmsVertex(0, p[0], p[1], p[2], 0.0, 0.0, 1.0, -1, 0.0, 0.0, 0.0))
        for a, b, c, d in FACES:
            jm.tris.append(JmsTriangle(region, 0, base + a, base + b, base + c))
            jm.tris.append(JmsTriangle(region, 0, base + a, base + c, base + d))
    jm.calculate_vertex_normals()
    return jm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('port')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    m = ports_h1.load(a.port)['model']
    C = m['collision']
    name = m['world_name']
    src = os.path.join(HCEEK, 'data', m['dir'], 'models', name + '.jms')
    jm = box_jms(src, C['boxes'], C.get('material', 'metal'))
    print('%d box(es), %d triangles, nodes %s' % (len(C['boxes']), len(jm.tris),
                                                   [n.name for n in jm.nodes]))
    if not a.write:
        print('(dry run -- --write to compile)')
        return
    d = os.path.join(HCEEK, 'data', m['dir'], 'physics')
    os.makedirs(d, exist_ok=True)
    write_jms(os.path.join(d, name + '.jms'), jm)
    r = subprocess.run([os.path.join(HCEEK, 'tool.exe'), 'collision-geometry', m['dir']],
                       cwd=HCEEK, capture_output=True, text=True, errors='replace')
    print((r.stdout + r.stderr).strip()[-1500:])
    out = os.path.join(HCEEK, 'tags', m['dir'], name + '.model_collision_geometry')
    print('->', out, 'OK' if os.path.exists(out) else 'MISSING')


if __name__ == '__main__':
    main()
