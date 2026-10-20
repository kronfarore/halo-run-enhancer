"""Compare source FP arm skeletons with Halo 2's after a rigid alignment (Kabsch on the
shoulder/elbow/wrist joints, positions relative to `base`), so a pure axis convention
difference (Reach's flat export) drops out. H4 names mapped b_x -> x, finger 1/2/3 -> low/mid/tip.

    python align.py
"""
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skel

FING = {'1': 'low', '2': 'mid', '3': 'tip'}


def h4name(n):
    n = n[2:] if n.startswith('b_') else n
    m = re.match(r'([lr])_(index|middle|ring|pinky|thumb)(\d)$', n)
    if m:
        if m.group(3) == '0':
            return n  # pinky metacarpal, no H2 counterpart
        return '%s_%s_%s' % (m.group(1), m.group(2), FING[m.group(3)])
    return n


def table(nodes, rename=None):
    out = {}
    for n in nodes:
        nm = rename(n['name']) if rename else n['name']
        out[nm] = np.array(n['pos'], float)
    return out


def kabsch(P, Q):
    """R, t minimising |R P + t - Q| (rows = points)."""
    pc, qc = P.mean(0), Q.mean(0)
    H = (P - pc).T @ (Q - qc)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    return R, qc - R @ pc


CHAIN = ['l_upperarm', 'l_forearm', 'l_hand', 'r_upperarm', 'r_forearm', 'r_hand']


def bone(t, a, b):
    return float(np.linalg.norm(t[a] - t[b]))


def report(h2name, h2, srcname, src, align_on=('l_upperarm', 'r_upperarm', 'base')):
    common = [k for k in h2 if k in src]
    print('### %s vs %s: %d of %d H2 nodes by name; missing in source: %s' % (
        h2name, srcname, len(common), len(h2), [k for k in h2 if k not in src]))
    print('    extra in source: %s' % [k for k in src if k not in h2])
    # align on base + shoulders only (rigid, the rest-pose of the limbs may differ)
    al = [k for k in align_on if k in h2 and k in src]
    P = np.array([src[k] for k in al]); Q = np.array([h2[k] for k in al])
    R, t = kabsch(P, Q)
    print('    rotation (source -> H2 frame):', np.round(R, 3).tolist(), 'translation', np.round(t, 3).tolist())
    worst = (0, None)
    for k in common:
        p = R @ src[k] + t
        d = float(np.linalg.norm(p - h2[k]))
        if d > worst[0]: worst = (d, k)
        flag = '' if d < 0.01 else ('  <-- %.3f' % d)
        print('      %-16s H2=(%8.3f %8.3f %8.3f) src->H2=(%8.3f %8.3f %8.3f)%s' % (k, *h2[k], *p, flag))
    print('    worst residual %.4f at %s' % worst)
    for nm, a, b in [('shoulder spread', 'l_upperarm', 'r_upperarm'), ('L upper arm', 'l_upperarm', 'l_forearm'),
                     ('R upper arm', 'r_upperarm', 'r_forearm'), ('L forearm', 'l_forearm', 'l_hand'),
                     ('R forearm', 'r_forearm', 'r_hand')]:
        x, y = bone(h2, a, b), bone(src, a, b)
        print('    %-16s H2 %7.3f  src %7.3f  %+6.1f%%' % (nm, x, y, 100 * (y - x) / x))


if __name__ == '__main__':
    mc, _ = skel.load_jms(os.path.join(HERE, 'h2_mc_fp_arms.jms'))
    dv, _ = skel.load_jms(os.path.join(HERE, 'h2_dervish_fp_arms.jms'))
    H2 = {'H2 masterchief': table(mc), 'H2 dervish': table(dv)}
    SRC = [('H3 masterchief fp', r'objects\characters\masterchief\fp\fp.render_model', None),
           ('H3 dervish fp', r'objects\characters\dervish\fp\fp.render_model', None),
           ('H3 elite fp_arms', r'objects\characters\elite\fp_arms\fp_arms.render_model', None),
           ('Reach spartans fp', r'reach:objects\characters\spartans\fp\fp.render_model', None),
           ('Reach elite fp', r'reach:objects\characters\elite\fp\fp.render_model', None),
           ('H4 storm_fp', r'h4:objects\characters\storm_fp\storm_fp.render_model', h4name)]
    for title, rel, ren in SRC:
        n, _m = skel.load_tag(rel)
        src = table(n, ren)
        for hn, h in H2.items():
            report(hn, h, title, src)
            print()
