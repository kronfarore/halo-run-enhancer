"""Dump render-model skeletons of H3 / Reach / H4 FP arms (and weapons) in model space, JMS units,
and compare them with Halo 2's masterchief / dervish FP arms (absolute JMS 8209/8210).

    python skel.py            (prints everything)
"""
import math, os, sys
TK = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit'
sys.path.insert(0, TK)
import h1_fp_retarget, h4_rm, h2_jms  # noqa
import reach_tags  # noqa
HERE = os.path.dirname(os.path.abspath(__file__))


def qrot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy); ty = 2 * (z * vx - x * vz); tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def qmul(a, b):
    ai, aj, ak, aw = a; bi, bj, bk, bw = b
    return (aw * bi + ai * bw + aj * bk - ak * bj, aw * bj - ai * bk + aj * bw + ak * bi,
            aw * bk + ai * bj - aj * bi + ak * bw, aw * bw - ai * bi - aj * bj - ak * bk)


def load_tag(rel):
    load = reach_tags.load_render_model if reach_tags.is_reach(rel) else h4_rm.load
    rm = load(h1_fp_retarget.export_xml(rel))
    nodes = rm['nodes']
    W = {}
    def world(i):
        if i in W: return W[i]
        n = nodes[i]
        if n['parent'] is None or n['parent'] < 0:
            W[i] = (tuple(n['rot']), tuple(n['pos']))
        else:
            pq, pp = world(n['parent'])
            d = qrot(pq, n['pos'])
            W[i] = (qmul(pq, tuple(n['rot'])), (pp[0] + d[0], pp[1] + d[1], pp[2] + d[2]))
        return W[i]
    out = []
    for i, n in enumerate(nodes):
        q, p = world(i)
        out.append({'name': n['name'], 'parent': n['parent'] if n['parent'] is not None else -1,
                    'pos': tuple(100 * c for c in p), 'local': tuple(100 * c for c in n['pos'])})
    return out, rm['markers']


def load_jms(path):
    h2_jms.VERSION = open(path, encoding='latin-1').read().splitlines()[1].strip()
    m = h2_jms.read(path)
    out = [{'name': n.name[2:] if n.name.startswith('b_') else n.name, 'parent': n.parent,
            'pos': n.pos} for n in m.nodes]
    return out, m.markers


def dist(a, b):
    return math.dist(a, b)


def measures(nodes):
    by = {n['name']: n for n in nodes}
    def g(*cands):
        for c in cands:
            if c in by: return by[c]['pos']
        return None
    r = {}
    lu, ru = g('l_upperarm'), g('r_upperarm')
    lf, rf = g('l_forearm'), g('r_forearm')
    lh, rh = g('l_hand'), g('r_hand')
    if lu and ru: r['shoulder_spread'] = dist(lu, ru)
    if lu: r['l_shoulder'] = lu
    if ru: r['r_shoulder'] = ru
    if lu and lf: r['l_upper'] = dist(lu, lf)
    if ru and rf: r['r_upper'] = dist(ru, rf)
    if lf and lh: r['l_fore'] = dist(lf, lh)
    if rf and rh: r['r_fore'] = dist(rf, rh)
    return r


def dump(title, nodes, markers=None):
    print('=== %s : %d nodes' % (title, len(nodes)))
    for i, n in enumerate(nodes):
        par = nodes[n['parent']]['name'] if n['parent'] >= 0 else '-'
        print('  %2d %-28s par=%-24s world=(%8.3f %8.3f %8.3f)' % (i, n['name'], par, *n['pos']))
    m = measures(nodes)
    for k, v in m.items():
        print('  %-16s %s' % (k, ('%.3f' % v) if isinstance(v, float) else '(%.3f %.3f %.3f)' % v))
    if markers:
        for mk in markers:
            nm = mk['name'] if isinstance(mk, dict) else mk.name
            nd = mk['node'] if isinstance(mk, dict) else mk.node
            ps = mk['pos'] if isinstance(mk, dict) else mk.pos
            sc = 100 if isinstance(mk, dict) else 1
            print('  marker %-22s node=%-20s local=(%.3f %.3f %.3f)' % (nm, nodes[nd]['name'] if 0 <= nd < len(nodes) else nd, *(sc * c for c in ps)))
    return m


def compare(a_title, a, b_title, b):
    ba = {n['name']: n for n in a}; bb = {n['name']: n for n in b}
    common = [n['name'] for n in a if n['name'] in bb]
    only_a = [n['name'] for n in a if n['name'] not in bb]
    only_b = [n['name'] for n in b if n['name'] not in ba]
    print('--- compare %s (%d) vs %s (%d): %d by name' % (a_title, len(a), b_title, len(b), len(common)))
    print('  only in %s: %s' % (a_title, only_a))
    print('  only in %s: %s' % (b_title, only_b))
    worst = 0
    par_diff = []
    for nm in common:
        d = dist(ba[nm]['pos'], bb[nm]['pos'])
        worst = max(worst, d)
        pa = a[ba[nm]['parent']]['name'] if ba[nm]['parent'] >= 0 else '-'
        pb = b[bb[nm]['parent']]['name'] if bb[nm]['parent'] >= 0 else '-'
        if pa != pb: par_diff.append((nm, pa, pb))
        print('  %-22s delta=%7.3f  a=(%8.3f %8.3f %8.3f) b=(%8.3f %8.3f %8.3f)' % (nm, d, *ba[nm]['pos'], *bb[nm]['pos']))
    print('  max delta %.4f JMS units; parent differences: %s' % (worst, par_diff))
    ma, mb = measures(a), measures(b)
    for k in ('shoulder_spread', 'l_upper', 'r_upper', 'l_fore', 'r_fore'):
        if k in ma and k in mb:
            print('  %-16s %8.3f vs %8.3f  (%+.1f%%)' % (k, ma[k], mb[k], 100 * (mb[k] - ma[k]) / ma[k]))


if __name__ == '__main__':
    H2 = {}
    H2['h2_mc'] = load_jms(os.path.join(HERE, 'h2_mc_fp_arms.jms'))
    H2['h2_dervish'] = load_jms(os.path.join(HERE, 'h2_dervish_fp_arms.jms'))
    for k, (n, mk) in H2.items():
        dump(k, n, mk)
    tags = [a for a in sys.argv[1:]]
    loaded = {}
    for rel in tags:
        try:
            n, mk = load_tag(rel)
        except SystemExit as e:
            print('!! %s: %s' % (rel, e)); continue
        loaded[rel] = n
        dump(rel, n, mk)
    for rel, n in loaded.items():
        for k, (h2n, _m) in H2.items():
            compare(k, h2n, rel, n)
