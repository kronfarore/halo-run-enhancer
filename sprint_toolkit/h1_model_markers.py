r"""The markers of Halo 1 gbxmodels (HCEEK tags): name, node, node-relative position. Halo 1 keeps
markers per region PERMUTATION (`local markers`), not in the model's top-level `markers` block --
reading that block shows none (the Brute Shot's grenade, 2026-10-09: its `exhaust` marker looked
missing). Checks a port's `primary trigger` (muzzle flash), `exhaust` / `smoke` / `glow`
(projectile attachments) and template markers it lacks (the rocket's `primary ejection`).

    python h1_model_markers.py "weapons\brute shot\fp\fp" "weapons\rocket launcher\fp\fp"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for t in sys.argv[1:]:
        m = mod2_def.build(filepath=os.path.join(TAGS, t + '.gbxmodel')).data.tagdata
        nodes = [n.name for n in m.nodes.STEPTREE]
        seen = {}
        for r in m.regions.STEPTREE:
            for p in r.permutations.STEPTREE:
                for x in p.local_markers.STEPTREE:
                    seen[x.name] = (nodes[x.node_index], tuple(round(c, 3) for c in x.translation))
        print(t)
        for k, v in sorted(seen.items()):
            print('   %-24s %-20s %s' % (k, v[0], v[1]))


if __name__ == '__main__':
    main()
