"""Extract the Halo 1 AR models (fp + 3p) to JMS with Reclaimer, and summarise nodes,
markers and the geometry bounds per node -- the target the SAW has to be fitted to."""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.mod2 import mod2_def
from reclaimer.model.model_decompilation import extract_model

TAGS = r'F:\SteamLibrary\steamapps\common\HCEEK\tags'
OUT = os.path.join(HERE, 'h1_ar_jms')
for rel in (r'weapons\assault rifle\fp\fp', r'weapons\assault rifle\assault rifle'):
    t = mod2_def.build(filepath=os.path.join(TAGS, rel + '.gbxmodel'))
    models = extract_model(t.data.tagdata, rel, write_jms=False)
    print('=====', rel, '->', len(models), 'jms model(s)')
    for jm in models[:1]:
        print(' name', jm.name, '| nodes', len(jm.nodes), '| verts', len(jm.verts),
              '| tris', len(jm.tris), '| materials', [m.name for m in jm.materials])
        for i, n in enumerate(jm.nodes):
            print('  node %d %-22s parent %-3s pos (%.3f %.3f %.3f) rot (%.3f %.3f %.3f %.3f)' % (
                i, n.name, n.parent_index, n.pos_x, n.pos_y, n.pos_z,
                n.rot_i, n.rot_j, n.rot_k, n.rot_w))
        for mk in jm.markers:
            print('  marker %-20s node %d pos (%.3f %.3f %.3f)' % (
                mk.name, mk.parent, mk.pos_x, mk.pos_y, mk.pos_z))
        bounds = collections.defaultdict(lambda: [[1e9] * 3, [-1e9] * 3])
        for v in jm.verts:
            b = bounds[v.node_0]
            for k, c in enumerate((v.pos_x, v.pos_y, v.pos_z)):
                b[0][k] = min(b[0][k], c)
                b[1][k] = max(b[1][k], c)
        for ni, (lo, hi) in sorted(bounds.items()):
            print('  verts on node %d: x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f' % (
                ni, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
