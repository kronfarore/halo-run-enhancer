r"""Step 9: give the Halo 2 port animation graphs of its own.

The cut GPMG borrows the SNIPER RIFLE's first-person animations, one graph per player
species, and `sniper_rifle.weapon` still points at exactly the same two. So the port and a
live weapon share them, which is the same leak step 3 cleared out of the projectile: retime
the port's reload and the sniper rifle's reload changes with it.

This clones both and repoints the port, so the timing work has somewhere safe to happen:

    objects\characters\masterchief\fp\weapons\rifle\fp_saw\fp_saw.model_animation_graph
    objects\characters\dervish\fp\weapons\rifle\fp_saw\fp_saw.model_animation_graph

**The retiming itself is not done yet**, and it needs the Halo 2 jmad frame format, which
has not been decoded here -- `h3-animation-format` is the Halo 3 one and does not carry
over. What the port has now is a sniper rifle's timing on a drum-fed machine gun: the
motions are a sniper's, and so are their durations. Two separate problems, and only the
second is step 9's.

    python h2_saw_animations.py [--force]
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref

B = os.sep
TAGS = os.path.join(h2_tagref.H2EK, 'tags')
EXT = '.model_animation_graph'

#: (species, donor graph, the port's own copy)
GRAPHS = [
    (species,
     B.join(['objects', 'characters', species, 'fp', 'weapons', 'rifle',
             'fp_sniper_rifle', 'fp_sniper_rifle']),
     B.join(['objects', 'characters', species, 'fp', 'weapons', 'rifle',
             'fp_saw', 'fp_saw']))
    for species in ('masterchief', 'dervish')
]
WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw.weapon'])


def main():
    force = '--force' in sys.argv
    print('cloning the graphs the sniper rifle would otherwise share:')
    for species, donor, port in GRAPHS:
        src = os.path.join(TAGS, donor + EXT)
        dest = os.path.join(TAGS, port + EXT)
        if os.path.exists(dest) and not force:
            print('   %-12s exists, left alone' % species)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(src, dest)
            print('   %-12s %.0f KB <- %s' % (species, os.path.getsize(dest) / 1024,
                                              donor))

    print('pointing the weapon at them:')
    path = os.path.join(TAGS, WEAPON)
    have = h2_tagref.references(path)
    for species, donor, port in GRAPHS:
        if ('jmad', port) in have:
            print('   %-12s already the port\'s' % species)
            continue
        h2_tagref.set_reference(path, 'jmad', donor, port)

    print('what the sniper rifle still points at, which must be untouched:')
    sniper = os.path.join(TAGS, 'objects', 'weapons', 'rifle', 'sniper_rifle',
                          'sniper_rifle.weapon')
    for cls, ref in h2_tagref.references(sniper):
        if cls == 'jmad':
            print('   %s' % ref)


if __name__ == '__main__':
    main()
