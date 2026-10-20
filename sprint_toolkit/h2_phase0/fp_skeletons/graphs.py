"""Skeleton node lists of H3 / Reach / H4 FP animation graphs, and FP weapon render-model nodes.

    python graphs.py graph <rel> ...      (h3 path, reach:..., h4:...)
    python graphs.py rm <rel> ...
"""
import os, sys
TK = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit'
sys.path.insert(0, TK)
import h1_fp_retarget, h3_fp_pose, reach_tags, h4_rm  # noqa
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skel

mode = sys.argv[1]
for rel in sys.argv[2:]:
    try:
        x = h1_fp_retarget.export_xml(rel)
    except SystemExit as e:
        print('!!', rel, e); continue
    if mode == 'graph':
        if reach_tags.is_reach(rel):
            sk = reach_tags.skeleton(reach_tags.tree(x))
        else:
            sk = h3_fp_pose.skeleton_from_xml(x)
        print('=== %s : %d skeleton nodes' % (rel, len(sk)))
        print('   ' + ', '.join('%d:%s<%s' % (i, n, sk[p][0] if p >= 0 else '-') for i, (n, p) in enumerate(sk)))
    else:
        n, mk = skel.load_tag(rel)
        print('=== %s : %d nodes' % (rel, len(n)))
        for i, a in enumerate(n):
            print('   %2d %-24s par=%-20s local=(%7.3f %7.3f %7.3f)' % (i, a['name'], n[a['parent']]['name'] if a['parent'] >= 0 else '-', *a['local']))
        for m in mk:
            print('   marker %-22s node=%s' % (m['name'], n[m['node']]['name'] if 0 <= m['node'] < len(n) else m['node']))
