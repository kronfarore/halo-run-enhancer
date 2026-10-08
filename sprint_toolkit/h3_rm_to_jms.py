r"""A Halo 3 render model (H3EK) as a Halo 1 JMS, on its OWN skeleton -- for a port whose
first-person animations come from Halo 3 too (h1_fp_retarget.py), so no donor skeleton.

saw_to_jms.py put a Halo 4 mesh onto a Halo 1 donor's skeleton so the donor's animations
could drive it; here the Halo 3 nodes are kept (Halo 3 animates them: the Sentinel Beam's
clamps and power cores), renamed the Halo 1 way (`gun` -> `frame gun`).

The render model is read from `tool export-tag-to-xml` (h4_rm.load parses H3's too):
  positions   compressed to the model bounds: p = lo + v * (hi - lo), bounds paired as
              (x0, x1, y0) / (y1, z0, z1) -- world units, x100 into JMS
  indices     TRIANGLE STRIPS (index buffer type 'triangle strip'): parts index the strip,
              winding alternates, degenerate triangles dropped
  skinning    up to four node weights per vertex; JMS takes the two largest
  nodes       bind transforms parent-relative; quaternions CONJUGATED into Halo 1's
              convention (h1_fp_retarget.py: Halo 1 stores the inverse rotation)
  markers     node-relative, renamed per MARKERS (Halo 3 `primary_trigger` ->
              Halo 1 `primary trigger`)

    python h3_rm_to_jms.py <render_model tag path (H3EK)> <out.jms> [--material NAME ...]
"""
import argparse
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import h4_rm  # noqa: E402
import h1_fp_retarget  # noqa: E402  (export_xml)
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402
from reclaimer.model.model_decompilation import extract_model  # noqa: E402
from reclaimer.model.jms import JmsVertex, JmsTriangle, JmsMaterial, JmsNode, JmsMarker  # noqa: E402
from reclaimer.model.jms.file import write_jms  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
TEMPLATE = r'weapons\plasma rifle\plasma rifle'
MARKERS = {'primary_trigger': 'primary trigger', 'ground_point': 'ground point',
           'left_hand_mc': 'left hand', 'flashlight': 'flashlight', 'fx_overheat': 'overheat'}


def h1_name(n):
    return 'frame ' + n.replace('_', ' ')


def strip_tris(idx):
    out = []
    for k in range(len(idx) - 2):
        a, b, c = idx[k], idx[k + 1], idx[k + 2]
        if a == b or b == c or a == c:
            continue
        out.append((a, b, c) if k % 2 == 0 else (b, a, c))
    return out


def convert(rel, materials=None, markers=None):
    """`markers`: extra Halo 3 -> Halo 1 marker names over MARKERS (the Beam Rifle's
    fx_vent -> overheat, where the template's overheat steam spawns)."""
    rm = h4_rm.load(h1_fp_retarget.export_xml(rel))
    tmpl = extract_model(mod2_def.build(filepath=os.path.join(TAGS, TEMPLATE + '.gbxmodel')).data.tagdata,
                         TEMPLATE, write_jms=False)[0]
    jm = copy.deepcopy(tmpl)
    # nodes: parent-relative bind, Halo 1 quaternion convention
    nodes = rm['nodes']
    jn = []
    for i, n in enumerate(nodes):
        kids = [j for j, m in enumerate(nodes) if m['parent'] == i]
        sib = [j for j, m in enumerate(nodes) if m['parent'] == n['parent'] and j > i]
        qi, qj, qk, qw = n['rot']                       # H3 xml: i, j, k, w
        jn.append(JmsNode(h1_name(n['name']), kids[0] if kids else -1, sib[0] if sib else -1,
                          -qi, -qj, -qk, qw,            # conjugate
                          n['pos'][0] * 100, n['pos'][1] * 100, n['pos'][2] * 100,
                          parent_index=n['parent']))
    jm.nodes = jn
    info = rm['compression']
    (x0, x1, y0), (y1, z0, z1) = info['pos0'], info['pos1']
    (u0, u1), (v0, v1) = info['uv0'], info['uv1']
    lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
    verts, tris = [], []
    names = [m or 'material' for m in rm['materials']]
    mats = materials or [n.rsplit('\\', 1)[-1] for n in names]
    for me in rm['meshes']:
        base = len(verts)
        for v in me['verts']:
            p = [(lo[k] + v['pos'][k] * span[k]) * 100 for k in range(3)]
            u = u0 + v['uv'][0] * (u1 - u0)
            vv = v0 + v['uv'][1] * (v1 - v0)
            ns = sorted([(n, w) for n, w in zip(v['nodes'], v['w']) if n >= 0 and w > 0],
                        key=lambda t: -t[1])
            n0, w0 = ns[0] if ns else (0, 1.0)
            n1, w1 = ns[1] if len(ns) > 1 and ns[1][0] != n0 else (-1, 0.0)
            tot = w0 + w1
            nrm = v['n'] or (0.0, 0.0, 1.0)
            verts.append(JmsVertex(n0, p[0], p[1], p[2], nrm[0], nrm[1], nrm[2],
                                   n1, (w1 / tot) if tot else 0.0, u, 1.0 - vv))
        strip = 'strip' in (me['index_type'] or '')
        for part in me['parts']:
            idx = me['indices'][part['start']:part['start'] + part['count']]
            tt = strip_tris(idx) if strip else [tuple(idx[i:i + 3]) for i in range(0, len(idx) - 2, 3)]
            for a, b, c in tt:
                tris.append(JmsTriangle(0, max(0, part['material']), base + a, base + b, base + c))
    # keep only the materials a triangle uses (the world model lists an unused
    # `shaders\invalid` first), renumbered in order
    used = sorted({t.shader for t in tris})
    remap = {old: new for new, old in enumerate(used)}
    for t in tris:
        t.shader = remap[t.shader]
    jm.verts, jm.tris = verts, tris
    jm.materials = [JmsMaterial(mats[i]) for i in used]
    marks = []
    for m in rm['markers']:
        nm = dict(MARKERS, **(markers or {})).get(m['name'])
        if nm is None:
            continue
        qi, qj, qk, qw = m['rot']
        marks.append(JmsMarker(nm, '', 0, m['node'], -qi, -qj, -qk, qw,
                               m['pos'][0] * 100, m['pos'][1] * 100, m['pos'][2] * 100))
    jm.markers = marks
    return jm, rm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render_model')
    ap.add_argument('out')
    ap.add_argument('--material', action='append')
    a = ap.parse_args()
    jm, rm = convert(a.render_model, a.material)
    write_jms(a.out, jm)
    xs = [v.pos_x for v in jm.verts]
    print('wrote %s | nodes %s | verts %d | tris %d | materials %s | markers %s | x %.1f..%.1f'
          % (a.out, [n.name for n in jm.nodes], len(jm.verts), len(jm.tris),
             [m.name for m in jm.materials], [m.name for m in jm.markers], min(xs), max(xs)))


if __name__ == '__main__':
    main()
