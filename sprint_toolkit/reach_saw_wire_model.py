r"""Give the Reach SAW its own model -- and in Reach that is ONE model, not two.

Halo 3 and ODST need two wiring steps because a weapon there has a first-person render
model of its own beside its world one. Reach has no such thing. Its `first person` block
pairs the weapon's OWN render model with a per-species animation graph, so the Assault
Rifle's references read:

    hlmt  objects\weapons\rifle\assault_rifle\assault_rifle     <- the model tag
    mode  objects\weapons\rifle\assault_rifle\assault_rifle     <- first person, Spartan
    jmad  objects\characters\spartans\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle
    mode  objects\weapons\rifle\assault_rifle\assault_rifle     <- first person, Elite
    jmad  objects\characters\elite\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle

Both `mode` references are the SAME render model. So the whole job is one model tag and
three repoints, and what you hold, what you drop and what an ally carries are the same
geometry by construction -- the class of bug that made the Halo 3 port invisible when
dropped cannot occur here.

THE PATHS ARE NOT THE SAME LENGTH, and that is deliberate. Halo 3's tools name every
clone to the exact length of what it replaces so a repoint is a byte overwrite. Reach's
port path is 17 characters shorter than the Assault Rifle's and padding it to match would
be inventing an ugly name to avoid code that already exists: `h3tag.repoint` rewrites the
reference's length and every ancestor's. `check()` re-walks the tree afterwards and the
save is refused if it no longer spans the file.

The collision, physics and animation references stay the Assault Rifle's: the SAW is the
same size and is meant to animate like one until step 9 retimes it.

    python reach_saw_wire_model.py [--write]
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402

B = os.sep
TAGS = h3_kit.TAGS
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW = h3_kit.SAW_WEAPON                    # objects\weapons\rifle\saw\saw


def full(rel, ext=''):
    return os.path.join(TAGS, rel + ext)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if not h3_kit.IS_REACH:
        raise SystemExit('this is the Reach wiring -- refusing to run against %s.\n'
                         'Halo 3 and ODST have a separate first-person render model and '
                         'use\nh3_saw_wire_model.py and h3_saw_world_model.py instead.'
                         % h3_kit.banner())

    for need in (SAW + '.render_model', SAW + '.weapon'):
        if not os.path.exists(full(need)):
            raise SystemExit('missing %s -- run h3_make_saw.py and tool render first'
                             % need)

    print('%s' % h3_kit.banner())
    print('model tag: %s.model -> %s.model' % (AR, SAW))
    if a.write:
        shutil.copy2(full(AR, '.model'), full(SAW, '.model'))

    if not a.write:
        t = h3tag.Tag(full(SAW, '.weapon'))
        for _o, grp, path in t.references():
            if grp in ('hlmt', 'mode') and path == AR:
                print('   would repoint %-5s %s -> %s' % (grp, path, SAW))
        print('\n(dry run -- pass --write)')
        return

    # (tag, group, what it should point at) -- the model tag first, so that by the time
    # the weapon names it, it already resolves.
    for rel, group in ((SAW + '.model', 'mode'), (SAW + '.weapon', 'hlmt'),
                       (SAW + '.weapon', 'mode')):
        t = h3tag.Tag(full(rel))
        before = len(t.data)
        n = t.repoint(AR, SAW, group=group)
        ok, covered, total = t.check()
        if not ok:
            raise SystemExit('%s: the chunk tree no longer spans the file (%d of %d) -- '
                             'NOT saved' % (rel, covered, total))
        t.save()
        print('   %-14s %-5s %d reference(s), %d -> %d bytes, tree spans %d of %d'
              % (os.path.basename(rel), group, n, before, len(t.data), covered, total))

    print('\nreferences now:')
    t = h3tag.Tag(full(SAW, '.weapon'))
    for _o, grp, path in t.references():
        if grp in ('hlmt', 'mode', 'jmad'):
            print('   %-5s %s' % (grp, path))
    print('\nNote the two jmad graphs are still the Assault Rifle\'s, one per species.')
    print('That is step 9, and Reach needs BOTH retimed -- Spartan and Elite.')


if __name__ == '__main__':
    main()
