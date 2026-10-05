r"""A uniformly scaled copy of a Halo 1 gbxmodel -- a first-person model out of a world model.

The Grunts' fuel rod (`weapons\fuel rod gun\fuel rod gun`) is 0.57 wu long: it is sized
for alien hands. Halo 1's own Master Chief-held fuel rod (the PC multiplayer
`weapons\plasma_cannon`) is 0.41 and Halo 3's FP fuel rod 0.43, so the original's
first-person model is its own mesh at 0.75 (0.43 long). Scaling is about the model origin:
vertices, node bind translations, markers and part centroids all scale, so every vertex
keeps its place relative to its node and the grip node stays the grip.

Nothing else changes -- shaders, regions, LODs and node rotations are the source's.

    python h1_scaled_model.py "weapons\fuel rod gun\fuel rod gun" "weapons\fuel rod gun\fp\fp" 0.75
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')


def scale_model(src_rel, dst_rel, k):
    tag = mod2_def.build(filepath=os.path.join(TAGS, src_rel + '.gbxmodel'))
    d = tag.data.tagdata
    for n in d.nodes.STEPTREE:
        n.translation.x *= k
        n.translation.y *= k
        n.translation.z *= k
        n.distance_from_parent *= k
    for r in d.regions.STEPTREE:
        for p in r.permutations.STEPTREE:
            for m in p.local_markers.STEPTREE:
                m.translation.x *= k
                m.translation.y *= k
                m.translation.z *= k
    for m in d.markers.STEPTREE:                       # legacy marker block, usually empty
        for inst in m.marker_instances.STEPTREE:
            inst.translation.x *= k
            inst.translation.y *= k
            inst.translation.z *= k
    verts = 0
    for g in d.geometries.STEPTREE:
        for p in g.parts.STEPTREE:
            c = p.centroid_translation
            c.x *= k
            c.y *= k
            c.z *= k
            for v in p.uncompressed_vertices.STEPTREE:
                v.position_x *= k
                v.position_y *= k
                v.position_z *= k
                verts += 1
            for v in p.compressed_vertices.STEPTREE:   # the second copy: positions are floats
                v.position_x *= k
                v.position_y *= k
                v.position_z *= k
    out = os.path.join(TAGS, dst_rel + '.gbxmodel')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tag.serialize(filepath=out, backup=False, temp=False)
    return out, verts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('scale', type=float)
    a = ap.parse_args()
    out, verts = scale_model(a.src, a.dst, a.scale)
    print('%s  (%d vertices x %.3f)' % (out, verts, a.scale))


if __name__ == '__main__':
    main()
