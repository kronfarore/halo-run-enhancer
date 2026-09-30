r"""Build the port's render model from the DONOR'S OWN GEOMETRY, as a control.

WHAT THIS DECIDES. The bisect proved the world model fault is inside the port's render
model: with the model tag pointed at the Assault Rifle's render model a dropped weapon
appears (as an Assault Rifle), and with the port's own it appears as nothing. Every field
`export-tag-to-xml` can show has since been compared against the donor's and agrees, so
the difference is in the DATA and the XML cannot see it.

Two suspects are left, and they need opposite fixes:

    the JMS PIPELINE           -> the fix is the FBX/sidecar importer, a large job
    our H4 GEOMETRY DATA       -> the fix is in the converter, a small one

This tells them apart in one build. `tool export-render-model-mesh` writes the DONOR's
own geometry as a binary DirectX `.x`; this reads it, wraps it on the Reach skeleton the
port already uses, and writes it as the port's JMS. Render and build, and:

    still nothing in the world -> the pipeline is at fault. Donor geometry, donor
                                  skeleton, donor everything, and it still does not draw,
                                  so what is wrong is how a JMS becomes a render model.
    an ASSAULT-RIFLE-SHAPED    -> the pipeline is fine and OUR geometry data is at fault.
    weapon drops                  Look at the converter: tangents, normals, winding.

WHAT IS DELIBERATELY SIMPLIFIED, because it is a control and not a deliverable: the export
carries no skinning, so every vertex binds to `b_gun` alone, and the whole mesh uses ONE
material so the port's existing shader resolves. Both make the model LESS like the donor's,
not more, which only matters if the test PASSES -- and a pass is the outcome that sends us
to the converter anyway.

    python reach_donor_mesh.py <ar_mesh.x> <skeleton.xml>
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa: E402,F401
import h3_kit                                                   # noqa: E402
import saw_to_jms_h3 as conv                                     # noqa: E402
from reclaimer.model.jms import (JmsModel, JmsVertex, JmsTriangle,  # noqa: E402
                                 JmsMaterial)
from reclaimer.model.jms.file import write_jms                    # noqa: E402

#: binary .x token ids we care about
T_NAME, T_STRING, T_INT, T_GUID, T_INTLIST, T_FLOATLIST = 1, 2, 3, 5, 6, 7


def tokens(path):
    """(kind, value, payload offset) for a binary DirectX .x file."""
    d = open(path, 'rb').read()
    if not d.startswith(b'xof '):
        raise SystemExit('%s is not a .x file' % path)
    if b'bin' not in d[:16]:
        raise SystemExit('%s is not BINARY .x; this reader only does binary' % path)
    i, out = 16, []
    while i + 2 <= len(d):
        t = struct.unpack_from('<H', d, i)[0]
        i += 2
        if t in (T_NAME, T_STRING):
            n = struct.unpack_from('<I', d, i)[0]
            i += 4
            s = d[i:i + n].decode('latin1')
            i += n + (2 if t == T_STRING else 0)
            out.append(('NAME' if t == T_NAME else 'STR', s, None))
        elif t == T_INT:
            out.append(('INT', struct.unpack_from('<I', d, i)[0], None))
            i += 4
        elif t == T_GUID:
            i += 16
            out.append(('GUID', None, None))
        elif t in (T_INTLIST, T_FLOATLIST):
            n = struct.unpack_from('<I', d, i)[0]
            i += 4
            out.append(('INTLIST' if t == T_INTLIST else 'FLOATLIST', n, i))
            i += 4 * n
        else:
            out.append(('T', t, None))
    return d, out


def mesh(path):
    """(positions, normals, uvs, triangles) out of the .x file's Mesh object."""
    d, toks = tokens(path)
    # The DATA section follows the last `template`. The Mesh object is a NAME('Mesh')
    # followed by '{' and then, in order: nVertices, the vertex floats, and the face
    # list. MeshNormals and MeshTextureCoords are sibling objects with the same shape.
    start = max(k for k, t in enumerate(toks) if t[0] == 'T' and t[1] == 31)

    def obj(name, after=start):
        for k in range(after, len(toks)):
            if toks[k][0] == 'NAME' and toks[k][1] == name:
                return k
        return None

    def ints(k):
        n, at = toks[k][1], toks[k][2]
        return list(struct.unpack_from('<%dI' % n, d, at))

    def floats(k):
        n, at = toks[k][1], toks[k][2]
        return list(struct.unpack_from('<%df' % n, d, at))

    mk = obj('Mesh')
    if mk is None:
        raise SystemExit('no Mesh object in the .x file')
    lists = [k for k in range(mk, len(toks)) if toks[k][0] in ('INTLIST', 'FLOATLIST')]
    n_verts = ints(lists[0])[0]
    pos = floats(lists[1])
    faces_raw = ints(lists[2])

    nk = obj('MeshNormals')
    norms = floats([k for k in range(nk, len(toks))
                    if toks[k][0] == 'FLOATLIST'][0]) if nk else []
    tk = obj('MeshTextureCoords')
    uvs = floats([k for k in range(tk, len(toks))
                  if toks[k][0] == 'FLOATLIST'][0]) if tk else []

    # faces: nFaces, then per face (count, i0, i1, i2)
    n_faces, tris, i = faces_raw[0], [], 1
    while i < len(faces_raw) and len(tris) < n_faces:
        c = faces_raw[i]
        tris.append(tuple(faces_raw[i + 1:i + 1 + c]))
        i += 1 + c
    return n_verts, pos, norms, uvs, tris


def main():
    if not h3_kit.IS_REACH:
        raise SystemExit('Reach only -- refusing to run against %s' % h3_kit.banner())
    if len(sys.argv) < 3:
        raise SystemExit(__doc__.strip().splitlines()[-1].strip())
    xpath, skel = sys.argv[1], sys.argv[2]

    n_verts, pos, norms, uvs, tris = mesh(xpath)
    print('%s: %d vertices, %d triangles' % (os.path.basename(xpath), n_verts, len(tris)))
    xs = pos[0::3]
    print('   x %.4f .. %.4f world units (%.2f m long)'
          % (min(xs), max(xs), (max(xs) - min(xs)) * 3.048))

    tmpl, by_name = conv.template_from_xml(skel)
    print('   skeleton: %s' % [n.name for n in tmpl.nodes])
    print('   markers : %d' % len(tmpl.markers))

    U = conv.UNITS
    verts = []
    for v in range(n_verts):
        x, y, z = pos[3 * v], pos[3 * v + 1], pos[3 * v + 2]
        ni, nj, nk = (norms[3 * v], norms[3 * v + 1], norms[3 * v + 2]) if norms \
            else (0.0, 0.0, 1.0)
        tu, tv = (uvs[2 * v], uvs[2 * v + 1]) if uvs else (0.0, 0.0)
        # node 0 for every vertex: the export carries no skinning, and a weapon that is
        # rigid on its own root is a valid model -- see the note at the top.
        verts.append(JmsVertex(0, x * U, y * U, z * U, ni, nj, nk, -1, 0.0, tu, 1 - tv, 0))
    tset = [JmsTriangle(0, 0, t[0], t[1], t[2]) for t in tris if len(t) == 3]

    jm = JmsModel('saw', 0, tmpl.nodes, [JmsMaterial('saw_body')], tmpl.markers,
                  [conv.REGION], verts, tset)
    out = os.path.join(h3_kit.DATA, 'objects', 'weapons', 'rifle', conv.OUT_SUB,
                       'render', conv.REGION + '.jms')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_jms(out, jm)
    print('wrote %s\n   %d verts, %d tris, ONE material (saw_body), all on node 0'
          % (out, len(verts), len(tset)))
    print('\nNow: tool render, reach_node_names.py --write, then build.')


if __name__ == '__main__':
    main()
