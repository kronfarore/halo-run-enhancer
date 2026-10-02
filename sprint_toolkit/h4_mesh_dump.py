r"""Dump a port's render mesh from its Foundry .blend as JSON: world-space vertices and
triangles, for h4_weapon_glyph.py's side-view silhouette.

    blender --background <port>.blend --python h4_mesh_dump.py -- <out.json>

Only the RENDER mesh is taken (the object Foundry imported as `default:default`, the one
carrying the port's materials); collision/physics hulls and markers are skipped. Halo's
forward axis is Blender -Y in a Foundry scene (measured on the Reach SAW: JMS +x ->
Blender -y), so the glyph uses (-y, z) -- muzzle to the right, as the shipped icons.
"""
import json
import sys

import bpy

out = sys.argv[sys.argv.index('--') + 1]
V, T = [], []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or not ob.data.materials:
        continue
    if any(m and m.name in ('Collision', 'Physics') for m in ob.data.materials):
        continue
    me = ob.data
    me.calc_loop_triangles()
    base = len(V)
    mw = ob.matrix_world
    V.extend([list(mw @ v.co) for v in me.vertices])
    T.extend([[base + i for i in t.vertices] for t in me.loop_triangles])
    print('mesh %s: %d vertices, %d triangles' % (ob.name, len(me.vertices), len(me.loop_triangles)))
json.dump({'vertices': V, 'triangles': T}, open(out, 'w'))
print('wrote', out)
