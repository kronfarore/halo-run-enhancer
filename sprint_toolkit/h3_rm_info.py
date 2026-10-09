r"""A Halo 3 render model at a glance: nodes (parent, bind rotation), materials, markers, mesh
vertex types -- and the ROOT ROTATION check of the Brute Shot (2026-10-09): a world model can be
authored TILTED (the brute shot's root `gun` rests ~55 deg rotated; its weapon frame is the
`body` node). Halo 3 holds weapons by markers, Halo 1 by the object frame, so a tilted root
needs `world_frame` (h3_rm_to_jms.convert frame=). With --frame NODE it prints the model's extent
and the markers re-expressed in that node's frame (x forward, z up = the weapon frame).

    python h3_rm_info.py objects\weapons\support_low\brute_shot\brute_shot.render_model
    python h3_rm_info.py objects\weapons\support_low\brute_shot\brute_shot.render_model --frame body
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h1_fp_retarget  # noqa: E402  (export_xml)
import h4_rm  # noqa: E402
import h3_rm_to_jms as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('render_model')
    ap.add_argument('--frame', help='a node: extent + markers in its bind frame')
    a = ap.parse_args()
    xml = h1_fp_retarget.export_xml(a.render_model)
    rm = h4_rm.load(xml)
    nodes = rm['nodes']
    for i, n in enumerate(nodes):
        q = n['rot']
        ang = math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q[3])))))
        print('node %-2d %-24s parent %-3s rot %s (%.0f deg)%s'
              % (i, n['name'], n['parent'], tuple(round(c, 3) for c in q), ang,
                 '  <-- TILTED ROOT' if (n['parent'] is None or n['parent'] < 0) and ang > 1 else ''))
    print('materials', rm['materials'])
    for m in rm['markers']:
        print('marker %-24s node %-2d pos %s' % (m['name'], m['node'], tuple(round(c, 4) for c in m['pos'])))
    txt = open(xml, encoding='utf-8', errors='replace').read()
    import re
    print('vertex types', sorted(set(re.findall(r'<field name="vertex type" value="([^"]*)"', txt))))
    if a.frame:
        names = [n['name'] for n in nodes]
        fq, fp = R._world(nodes, names.index(a.frame))
        inv = (-fq[0], -fq[1], -fq[2], fq[3])
        info = rm['compression']
        (x0, x1, y0), (y1, z0, z1) = info['pos0'], info['pos1']
        lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
        V = [R._qrot(inv, tuple(lo[k] + v['pos'][k] * span[k] - fp[k] for k in range(3)))
             for me in rm['meshes'] for v in me['verts']]
        print('in %s frame: min %s max %s' % (a.frame, tuple(round(min(c[k] for c in V), 3) for k in range(3)),
                                              tuple(round(max(c[k] for c in V), 3) for k in range(3))))
        for m in rm['markers']:
            mq, mp = R._world(nodes, m['node'])
            d = R._qrot(mq, m['pos'])
            w = tuple(mp[k] + d[k] - fp[k] for k in range(3))
            print('   %-24s %s' % (m['name'], tuple(round(c, 3) for c in R._qrot(inv, w))))


if __name__ == '__main__':
    main()
