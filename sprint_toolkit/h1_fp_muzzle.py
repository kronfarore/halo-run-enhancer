r"""A Halo 1 FP model's MARKER in camera space (forward / left / up wu) in one animation frame --
the trigger's `first person offset` that starts a contrail at the first-person muzzle (the
Sentinel Beam's end-on contrail, the Beam Rifle's / DMR's / Needle Rifle's 'trail from the muzzle').
Earlier ports read it with a scratch script (marker_dir.py, lost); this is it as a tool (the
Focus Rifle, wave B7, 2026-10-12). Read-only.

Halo 1's FP view is the animation's own space (fp_render): camera at the origin looking down +x,
+y left, +z up. A marker's position is relative to its node, so its view position is
W_node(pose) * marker translation.

    python h1_fp_muzzle.py "weapons\focus rifle\fp\fp" [--marker "primary trigger"]
                           [--antr <FP animations tag>] [--anim "first-person idle"] [--frame 0]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import fp_render as R  # noqa: E402
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402


def marker_view(model, marker='primary trigger', antr=None, anim='first-person idle', frame=0):
    """[(forward, left, up) wu] of every instance of `marker` in the posed FP view."""
    d = mod2_def.build(filepath=os.path.join(R.TAGS, model + '.gbxmodel')).data.tagdata
    names = [n.name for n in d.nodes.STEPTREE]
    nn, par, local, _n = R.anim_pose(antr or model, anim, frame)
    world = R.compose(nn, par, local)
    out, seen = [], set()
    # Halo 1 keeps markers per region PERMUTATION (`local markers`; h1_model_markers.py)
    for r in d.regions.STEPTREE:
        for p in r.permutations.STEPTREE:
            for x in p.local_markers.STEPTREE:
                t = tuple(x.translation)
                if x.name != marker or (x.node_index, t) in seen:
                    continue
                seen.add((x.node_index, t))
                out.append(R.xform(world[names[x.node_index]], t))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('model', help='FP gbxmodel tag path, no extension')
    ap.add_argument('--marker', default='primary trigger')
    ap.add_argument('--antr', help='FP model_animations tag (default: the model path)')
    ap.add_argument('--anim', default='first-person idle')
    ap.add_argument('--frame', type=int, default=0)
    a = ap.parse_args()
    pts = marker_view(a.model, a.marker, a.antr, a.anim, a.frame)
    if not pts:
        raise SystemExit('no marker %r in %s' % (a.marker, a.model))
    for p in pts:
        print('%s  forward %.4f  left %.4f  up %.4f wu' % (a.marker, p[0], p[1], p[2]))


if __name__ == '__main__':
    main()
