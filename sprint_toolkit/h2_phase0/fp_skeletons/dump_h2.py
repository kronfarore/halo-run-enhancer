import sys, math, collections
sys.path.insert(0, r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit')
import h2_jms

for p in sys.argv[1:]:
    h2_jms.VERSION = open(p,encoding="latin-1").read().splitlines()[1].strip()
    m = h2_jms.read(p)
    print('=== %s : %d nodes, %d markers, %d verts' % (p, len(m.nodes), len(m.markers), len(m.verts)))
    used = collections.Counter()
    for v in m.verts:
        for n, w in v.influences:
            if w > 0: used[n] += 1
    for i, n in enumerate(m.nodes):
        par = m.nodes[n.parent].name if n.parent >= 0 else '-'
        d = ''
        if n.parent >= 0:
            pp = m.nodes[n.parent].pos
            d = '%.3f' % math.dist(pp, n.pos)
        print('%2d %-28s par=%-24s pos=(%8.3f %8.3f %8.3f) rot=(%.3f %.3f %.3f %.3f) len=%s verts=%d' % (
            i, n.name, par, *n.pos, *n.rot, d, used[i]))
    for mk in m.markers:
        print('  marker %-20s node=%-24s pos=(%.3f %.3f %.3f)' % (mk.name, m.nodes[mk.node].name, *mk.pos))
    print('  materials:', sorted(set(x.spec for x in m.materials)))
