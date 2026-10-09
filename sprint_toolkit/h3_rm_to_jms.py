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


def convert_particle_model(rel, material, node='frame spike'):
    """A Halo 3 PARTICLE MODEL (.particle_model, one rigid mesh) as a one-node Halo 1 JMS --
    the Spike Rifle's stuck spike (`fx\\particles\\models\\weapons\\brute_spike`): Halo 3
    spawns it as a model particle where a spike hits; Halo 1 has no model particles, so it
    becomes the PROJECTILE's model (the needle's way). Read from the export's `raw vertices`
    (compressed to the bounds, as a render model's) and `raw indices` (a triangle strip)."""
    import io
    import re
    s = io.open(h1_fp_retarget.export_xml(rel), encoding='utf-8', errors='replace').read()

    def nums(name, blk=s):
        return [tuple(float(x) for x in v.split(','))
                for v in re.findall(r'name="%s" value="([^"]*)"' % re.escape(name), blk)]
    (x0, x1, y0), (y1, z0, z1) = nums('position bounds 0')[0], nums('position bounds 1')[0]
    (u0, u1), (v0, v1) = nums('texcoord bounds 0')[0], nums('texcoord bounds 1')[0]
    raw = s[s.find('<block name="raw vertices"'):s.find('<block name="raw indices"')]
    pos, uv, nrm = nums('position', raw), nums('texcoord', raw), nums('normal', raw)
    idx = [int(v) for v in re.findall(r'name="word" value="(\d+)"',
                                      s[s.find('<block name="raw indices"'):])]
    tmpl = extract_model(mod2_def.build(filepath=os.path.join(TAGS, TEMPLATE + '.gbxmodel')).data.tagdata,
                         TEMPLATE, write_jms=False)[0]
    jm = copy.deepcopy(tmpl)
    jm.nodes = [JmsNode(node, -1, -1, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, parent_index=-1)]
    lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
    jm.verts = [JmsVertex(0, *[(lo[k] + p[k] * span[k]) * 100 for k in range(3)], *n,
                          -1, 0.0, u0 + t[0] * (u1 - u0), 1.0 - (v0 + t[1] * (v1 - v0)))
                for p, t, n in zip(pos, uv, nrm)]
    jm.tris = [JmsTriangle(0, 0, a, b, c) for a, b, c in strip_tris(idx)]
    jm.materials = [JmsMaterial(material)]
    jm.markers = []
    return jm


def _qrot(q, v):
    """v rotated by quaternion q = (i, j, k, w), Halo 3's convention (as stored)."""
    i, j, k, w = q
    ux, uy, uz = i, j, k
    cx = (uy * v[2] - uz * v[1]) + w * v[0]
    cy = (uz * v[0] - ux * v[2]) + w * v[1]
    cz = (ux * v[1] - uy * v[0]) + w * v[2]
    return (v[0] + 2 * (uy * cz - uz * cy), v[1] + 2 * (uz * cx - ux * cz),
            v[2] + 2 * (ux * cy - uy * cx))


def _qmul(a, b):
    ai, aj, ak, aw = a
    bi, bj, bk, bw = b
    return (aw * bi + ai * bw + aj * bk - ak * bj, aw * bj - ai * bk + aj * bw + ak * bi,
            aw * bk + ai * bj - aj * bi + ak * bw, aw * bw - ai * bi - aj * bj - ak * bk)


def _world(nodes, i):
    """(rotation, translation) of node i in model space (Halo 3 convention)."""
    n = nodes[i]
    if n['parent'] is None or n['parent'] < 0:
        return tuple(n['rot']), tuple(n['pos'])
    pq, pp = _world(nodes, n['parent'])
    d = _qrot(pq, n['pos'])
    return _qmul(pq, tuple(n['rot'])), (pp[0] + d[0], pp[1] + d[1], pp[2] + d[2])


def convert(rel, materials=None, markers=None, frame=None):
    """`markers`: extra Halo 3 -> Halo 1 marker names over MARKERS (the Beam Rifle's
    fx_vent -> overheat, where the template's overheat steam spawns).
    `frame`: a node name -- the model re-expressed in that node's bind frame (the Brute
    Shot, 2026-10-09: Halo 3's world model is authored TILTED, its root `gun` rotated ~55
    deg, the weapon frame -- x forward, z up, the muzzle marker 0.25 forward -- is the
    `body` node; Halo 3 holds weapons by markers, Halo 1 by the object frame). Vertices
    (model space) and the root's bind transform change; every other node and every marker
    is parent-relative and stays."""
    rm = h4_rm.load(h1_fp_retarget.export_xml(rel))
    F = None
    if frame:
        names = [n['name'] for n in rm['nodes']]
        fq, fp = _world(rm['nodes'], names.index(frame))
        F = ((-fq[0], -fq[1], -fq[2], fq[3]), fp)          # the inverse rotation, the origin
        for n in rm['nodes']:
            if n['parent'] is None or n['parent'] < 0:      # root: F^-1 * (its bind)
                d = _qrot(F[0], (n['pos'][0] - fp[0], n['pos'][1] - fp[1], n['pos'][2] - fp[2]))
                n['pos'], n['rot'] = d, _qmul(F[0], tuple(n['rot']))
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
            p = [lo[k] + v['pos'][k] * span[k] for k in range(3)]
            if F:
                p = _qrot(F[0], (p[0] - F[1][0], p[1] - F[1][1], p[2] - F[1][2]))
                if v['n']:
                    v['n'] = _qrot(F[0], v['n'])
            p = [c * 100 for c in p]
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
