"""H4 SAW (storm_lmg) -> Halo 1 JMS, first and third person, on the Halo 1 Assault
Rifle's skeleton so the AR's animations drive it.

  * geometry from the H4EK render_model XML (raw vertices are compressed to the mesh's
    bounds: pos = lo + p * (hi - lo); bounds are x0,x1,y0 / y1,z0,z1), in world units
    -> x100 JMS units, scaled by SCALE (0.82: puts the SAW's first-person left hand where
    the AR animations put the left hand, 8.9 units ahead of the grip)
  * b_gun -> 'frame gun', b_magazine -> 'frame magazine' (first person; third person has
    no magazine node, so it rides on 'frame gun')
  * nodes, hierarchy, rest pose, node-list checksum and markers come from the AR's own
    extracted JMS; muzzle / smoke / ejection / flashlight move to the SAW's positions
  * texture v flipped (JMS v = 1 - tag v, as Reclaimer's extractor writes them)

    python saw_to_jms.py <lmg_rm.xml> <out data dir> [scale]
"""
import copy, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
import h4_rm
from reclaimer.hek.defs.mod2 import mod2_def
from reclaimer.model.model_decompilation import extract_model
from reclaimer.model.jms import JmsVertex, JmsTriangle, JmsMaterial, JmsModel
from reclaimer.model.jms.file import write_jms

SCALE = 0.82
TAGS = r'F:\SteamLibrary\steamapps\common\HCEEK\tags'
# H4 part material -> Halo 1 shader name (None = part dropped). The decals are four
# triangles of a separate decal sheet, and the depleted display is a second quad over the
# display (H4 switches between them; in H1 they would z-fight) -- both left out for now.
MATERIALS = ['saw_body', 'saw_display']
PART_SHADER = {0: None, 1: 0, 2: None, 3: 1}
# AR marker -> SAW marker it should sit on (others keep the AR's position)
MARKER_FROM = {'primary trigger': 'primary_trigger', 'smoke': 'muzzle_flash',
               'primary ejection': 'primary_ejection', 'flashlight': 'flashlight',
               'secondary trigger': 'primary_trigger'}


def ar_template(rel):
    t = mod2_def.build(filepath=os.path.join(TAGS, rel + '.gbxmodel'))
    return extract_model(t.data.tagdata, rel, write_jms=False)[0]


def convert(rm, template, node_map):
    me = rm['meshes'][0]
    info = rm['compression']
    (x0, x1, y0), (y1, z0, z1) = info['pos0'], info['pos1']
    (u0, u1), (v0, v1) = info['uv0'], info['uv1']
    lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
    verts = []
    for v in me['verts']:
        p = [(lo[k] + v['pos'][k] * span[k]) * 100 * SCALE for k in range(3)]
        u = u0 + v['uv'][0] * (u1 - u0)
        vv = v0 + v['uv'][1] * (v1 - v0)
        ns = [(node_map[n], w) for n, w in zip(v['nodes'], v['w']) if n >= 0 and w > 0]
        ns.sort(key=lambda t: -t[1])
        n0, w0 = ns[0] if ns else (0, 1.0)
        n1, w1 = ns[1] if len(ns) > 1 and ns[1][0] != n0 else (-1, 0.0)
        tot = w0 + w1
        nrm = v['n'] or (0.0, 0.0, 1.0)
        verts.append(JmsVertex(n0, p[0], p[1], p[2], nrm[0], nrm[1], nrm[2],
                               n1, (w1 / tot) if tot else 0.0, u, 1.0 - vv))
    tris = []
    for part in me['parts']:
        shader = PART_SHADER.get(part['material'])
        if shader is None:
            continue
        idx = me['indices'][part['start']:part['start'] + part['count']]
        for i in range(0, len(idx) - 2, 3):
            tris.append(JmsTriangle(0, shader, idx[i], idx[i + 1], idx[i + 2]))
    jm = copy.deepcopy(template)
    jm.verts = verts
    jm.tris = tris
    jm.materials = [JmsMaterial(n) for n in MATERIALS]
    h4m = {}
    for m in rm['markers']:
        h4m.setdefault(m['name'], m)
    for mk in jm.markers:
        src = h4m.get(MARKER_FROM.get(mk.name, ''))
        if src:
            mk.pos_x, mk.pos_y, mk.pos_z = (c * 100 * SCALE for c in src['pos'])
    return jm


def main():
    global SCALE
    rm = h4_rm.load(sys.argv[1])
    out = sys.argv[2]
    if len(sys.argv) > 3:
        SCALE = float(sys.argv[3])
    print('scale', SCALE)
    fp = ar_template(r'weapons\assault rifle\fp\fp')
    tp = ar_template(r'weapons\assault rifle\assault rifle')
    names_fp = [n.name for n in fp.nodes]
    names_tp = [n.name for n in tp.nodes]
    fp_map = {0: names_fp.index('frame gun'), 1: names_fp.index('frame magazine')}
    tp_map = {0: names_tp.index('frame gun'), 1: names_tp.index('frame gun')}
    for sub, tmpl, nmap in (('fp', fp, fp_map), ('', tp, tp_map)):
        jm = convert(rm, tmpl, nmap)
        d = os.path.join(out, 'weapons', 'saw', sub, 'models')
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, ('fp' if sub else 'saw') + '.jms')
        write_jms(path, jm)
        xs = [v.pos_x for v in jm.verts]
        print('wrote', path, '| verts', len(jm.verts), '| tris', len(jm.tris),
              '| nodes', [n.name for n in jm.nodes], '| x %.1f..%.1f' % (min(xs), max(xs)),
              '| checksum', jm.node_list_checksum)


if __name__ == '__main__':
    main()
