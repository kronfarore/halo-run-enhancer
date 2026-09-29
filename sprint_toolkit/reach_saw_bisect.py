r"""Localise the world-model fault to ONE side of the model tag, in a single build.

THE SYMPTOM. The Reach port draws where the scenario places it and draws in first person,
and draws NOTHING when it is dropped or handed to an ally. Everything structural has been
compared against the donor and matches: residency and its full closure, the geometry
chunks in the map, the model tag (identical in all 99 fields but the render-model
reference), the region and permutation names, the mesh format, the compression bounds,
the node names, the node ORDER and the node list checksum.

So the cheap checks are spent, and this is the experiment Halo 3 used when it had the
same symptom: point the port's model tag at the DONOR's render model and rebuild.

    the weapon still draws nothing   -> the fault is OUTSIDE the render model: the weapon
                                        tag, the model tag, or how the object is built.
                                        Nothing in either tag differs from the donor, so
                                        the next suspect is the weapon's own fields.
    an ASSAULT RIFLE appears in your -> the fault is INSIDE the port's render model, in
    hands when you drop it              something only the world path reads. The next cut
                                        is between geometry and the rest of the tag.

Nothing else is touched, so the build is otherwise the real port: its own bullet, numbers,
chud, animations and messages. Only what you SEE changes.

    python reach_saw_bisect.py --donor      # point the model at the Assault Rifle's
    python reach_saw_bisect.py --restore    # back to the port's own
    python reach_saw_bisect.py              # which is it pointing at now?
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402

B = os.sep
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW = h3_kit.SAW_WEAPON
MODEL = SAW + '.model'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--donor', action='store_true',
                    help="point the port's model tag at the Assault Rifle's render model")
    ap.add_argument('--restore', action='store_true',
                    help="point it back at the port's own")
    a = ap.parse_args()
    if not h3_kit.IS_REACH:
        raise SystemExit('Reach only -- refusing to run against %s' % h3_kit.banner())

    path = os.path.join(h3_kit.TAGS, MODEL)
    if not os.path.exists(path):
        raise SystemExit('no such model: %s' % path)
    tag = h3tag.Tag(path)
    now = sorted({p for _o, g, p in tag.references() if g == 'mode'})
    print('%s' % h3_kit.banner())
    print('   %s currently renders from: %s' % (os.path.basename(MODEL), ', '.join(now)))

    if not (a.donor or a.restore):
        print('\n(pass --donor or --restore)')
        return
    old, new = (SAW, AR) if a.donor else (AR, SAW)
    if old not in now:
        print('   already pointing at %s -- nothing to do' % new)
        return
    n = tag.repoint(old, new, 'mode')
    ok, covered, total = tag.check()
    if not ok:
        raise SystemExit('the chunk tree no longer spans the file (%d of %d) -- NOT saved'
                         % (covered, total))
    tag.save(path)
    print('   repointed %d reference(s) -> %s' % (n, new))
    print('   tree spans %d of %d; wrote %s' % (covered, total, os.path.basename(path)))
    print('\nRebuild, then: an ASSAULT RIFLE in your hands when you drop it means the '
          'fault is\nINSIDE the port\'s render model. Nothing at all means it is outside.'
          if a.donor else '\nRebuild to go back to the port\'s own geometry.')


if __name__ == '__main__':
    main()
