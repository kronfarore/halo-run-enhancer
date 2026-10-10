r"""Two Halo 1 model_animations tags compared ANIMATION BY ANIMATION: frame count, node count,
sound / sound frame, key / loop frame, flags, and SHA-1 of the frame and default data; the
node count and sound reference list. Byte equality says little for these tags (the regen
chain re-writes tested ones as content-equal noise, H1_PORT_PLAN "B1"); this says what changed.

Used on the Energy Blade's FP offset (2026-10-10): regenerated as configured = the tested tag in
every animation; after the view_offset change only the base animations' pose data moved.

    python h1_antr_diff.py <a.model_animations> <b.model_animations>
"""
import argparse
import hashlib
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.antr import antr_def  # noqa: E402


def load(path):
    a = antr_def.build(filepath=path).data.tagdata
    out = {}
    for x in a.animations.STEPTREE:
        out[x.name] = dict(frames=x.frame_count, nodes=x.node_count, sound=x.sound,
                           sframe=x.sound_frame_index, key=x.key_frame_index,
                           loop=x.loop_frame_index, flags=int(x.flags.data),
                           data=hashlib.sha1(bytes(x.frame_data.data)).hexdigest()[:10],
                           default=hashlib.sha1(bytes(x.default_data.data)).hexdigest()[:10])
    return out, [s.sound.filepath for s in a.sound_references.STEPTREE], len(a.nodes.STEPTREE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a')
    ap.add_argument('b')
    a = ap.parse_args()
    A, sa, na = load(a.a)
    B, sb, nb = load(a.b)
    print('nodes %d / %d | sound references %s' % (na, nb, 'same' if sa == sb else '%s -> %s' % (sa, sb)))
    n = 0
    for k in sorted(set(A) | set(B)):
        x, y = A.get(k) or {}, B.get(k) or {}
        if x == y:
            continue
        n += 1
        print(k)
        for f in sorted(set(x) | set(y)):
            if x.get(f) != y.get(f):
                print('   %-8s %s -> %s' % (f, x.get(f), y.get(f)))
    print('%d animation(s) differ' % n)


if __name__ == '__main__':
    main()
