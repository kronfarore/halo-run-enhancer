r"""How deep does each first-person HAND sink into the GUN, per animation (C1 Storm Rifle, promoted
from the scratchpad 2026-10-14). Retargets the port's animations (h1_fp_retarget), poses the Halo 1
arms and the port's FP gun (fp_render) and counts the hand triangles whose centre lies INSIDE the
gun mesh (ray parity), near the chosen wrist, summed over the frames -- the number the Storm
Rifle's hand_offset was measured with (idle 2771 -> 32, melee 853 -> 132). Fix per ANIMATION
(`hand_offset_anims`): a global offset broke the melee grip.

    python h1_fp_hand_clip.py storm_rifle "first_person:melee" "first_person:posing:var1"
    python h1_fp_hand_clip.py storm_rifle "first_person:idle" --side r --step 3 ^
        --try 0,-0.01,0 --try 0,-0.02,0

Each --try (x,y,z in the gun's space, metres) is counted as a trial hand_offset for that side
(nothing is written); without --try the config as it stands. Read-only.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_render as R            # noqa: E402
import h1_fp_retarget as T       # noqa: E402

WRIST = {'l': 'frame l wriste', 'r': 'frame r wriste'}


def tri_arr(model, W):
    return np.array([p for p, _c in R.posed_tris(model, W, (0, 0, 0))], dtype=float)


def inside(pts, tris):
    """Points inside a closed mesh: parity of +z ray crossings (Moller-Trumbore)."""
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0.0, 0.0, 1.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    ok = np.abs(a) > 1e-12
    f = np.where(ok, 1.0 / np.where(ok, a, 1), 0)
    cnt = np.zeros(len(pts), int)
    for i, p in enumerate(pts):
        s = p - v0
        u = f * (s * h).sum(1)
        q = np.cross(s, e1)
        v = f * (q @ d)
        t = f * (e2 * q).sum(1)
        cnt[i] = (ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)).sum()
    return cnt % 2 == 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port')
    ap.add_argument('anims', nargs='+', help='source animation names (the config retarget map keys)')
    ap.add_argument('--side', choices='lr', default='l')
    ap.add_argument('--step', type=int, default=1, help='every Nth frame')
    ap.add_argument('--radius', type=float, default=0.12, help='hand triangles within this of the wrist')
    ap.add_argument('--try', dest='tries', action='append', metavar='X,Y,Z')
    a = ap.parse_args()
    w = a.port
    nodes, anims, defaults, _ = T.load(w)
    names, parents = T.h1_skeleton(w, nodes)
    hands = R.load_model(R.HANDS)
    gun = R.load_model(T.ensure_model(w))
    cfg = T.WEAPONS[w]
    tries = [tuple(float(x) for x in t.split(',')) for t in (a.tries or [])] or [None]
    keep = (cfg.get('hand_offset'), cfg.get('hand_offset_anims'))
    for anim in a.anims:
        line = []
        for off in tries:
            if off is not None:          # a trial: this side only, every animation
                cfg['hand_offset'] = {a.side: off}
                cfg['hand_offset_anims'] = {}
            _typ, fr = T.retarget(w, anim, nodes, anims, defaults)
            total = 0
            for k in range(0, len(fr), a.step):
                W = R.compose(names, parents, fr[k])
                ht, gt = tri_arr(hands, W), tri_arr(gun, W)
                pts = ht.mean(1)
                pts = pts[np.linalg.norm(pts - np.array(W[WRIST[a.side]][1]), axis=1) < a.radius]
                total += int(inside(pts, gt).sum())
            # put back as found: a key the config never had stays absent (None broke the next
            # animation's `.get(...)` -- the Boltshot, which has no hand offsets yet)
            for k, v in zip(('hand_offset', 'hand_offset_anims'), keep):
                if v is None:
                    cfg.pop(k, None)
                else:
                    cfg[k] = v
            line.append('%s:%d' % ('config' if off is None else ','.join('%g' % x for x in off), total))
        print('%-36s %s' % (anim, '  '.join(line)))


if __name__ == '__main__':
    main()
