r"""Step 9: give the Halo 2 port animation graphs of its own.

The cut GPMG borrows the SNIPER RIFLE's first-person animations, one graph per player
species, and `sniper_rifle.weapon` still points at exactly the same two. So the port and a
live weapon share them, which is the same leak step 3 cleared out of the projectile: retime
the port's reload and the sniper rifle's reload changes with it.

This clones both and repoints the port, so the timing work has somewhere safe to happen:

    objects\characters\masterchief\fp\weapons\rifle\fp_saw\fp_saw.model_animation_graph
    objects\characters\dervish\fp\weapons\rifle\fp_saw\fp_saw.model_animation_graph

**The SOUNDS are fixed here**, and they were the audible half: the graph carries four
sound references and every one of them was the sniper rifle's, so the port reloaded with a
bolt-action's noises. They now point at the SMG's, the same donor the balance follows.

**The retiming is NOT done, and it now has a measured reason.** Halo 2 animation retiming
can only ever SHORTEN -- `halo3_reload` rewrites an animation's frame count and its event
frames, and there are no frames past the end to stretch into. The Halo 4 SAW's own reload
is 128 frames; the longest first-person reload Halo 2 ships anywhere is the rocket
launcher's 112, and of the ten graphs that reload at all only five animate a `magazine`
node -- which is the bone a magazine swap actually moves, and the one the port's model
carries. The sniper rifle's 72 is the longest of those five:

    rocket launcher 112   gun only, and no reload_empty at all
    brute shot       95   gun only
    flak cannon      90   gun only
    SNIPER RIFLE     72   gun + magazine   <- what the port has
    covenant carbine 69   gun only
    battle rifle     58   gun + magazine
    SMG              50   gun + magazine

So the port already reloads as slowly as Halo 2's art allows, and it reloads with its own
magazine moving, because the H4 SAW's magazine bone is mapped onto `frame magazine`.
Reaching the SAW's real 4.3 seconds needs animation SOURCE, and unlike a render model a
jmad carries none: `extract-render-data` unzips a .jms out of the tag, there is no
equivalent verb for animations, and the three zlib-looking runs in the file are
coincidence, not a stored .jma. That is the gap, stated exactly.

    python h2_saw_animations.py [--force] [--write]
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

#: The sniper's sound -> the SMG's equivalent. One for one: every sound the graph names
#: has a counterpart in the SMG's set, so nothing is dropped and nothing is invented.
SOUNDS = [
    (B.join(['sound', 'weapons', 'sniper_rifle', 'sniper_reload']),
     B.join(['sound', 'weapons', 'smg', 'smg_reload'])),
    (B.join(['sound', 'weapons', 'sniper_rifle', 'sniper_ready']),
     B.join(['sound', 'weapons', 'smg', 'smg_ready'])),
    (B.join(['sound', 'weapons', 'sniper_rifle', 'sniper_posing']),
     B.join(['sound', 'weapons', 'smg', 'smg_posing_var0'])),
    (B.join(['sound', 'weapons', 'sniper_rifle', 'sniper_melee_first']),
     B.join(['sound', 'weapons', 'smg', 'smg_melee1'])),
]


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

    print('giving it the SMG noises instead of the sniper rifle ones:')
    for _species, _donor, port in GRAPHS:
        graph = os.path.join(TAGS, port + EXT)
        have = h2_tagref.references(graph)
        for old, new in SOUNDS:
            if ('snd!', new) in have:
                print('   %-22s already the SMG version' % os.path.basename(new))
            elif ('snd!', old) in have:
                h2_tagref.set_reference(graph, 'snd!', old, new)
            else:
                print('   %-22s not named by %s' % (os.path.basename(old), port))

    print('what the sniper rifle still points at, which must be untouched:')
    sniper = os.path.join(TAGS, 'objects', 'weapons', 'rifle', 'sniper_rifle',
                          'sniper_rifle.weapon')
    for cls, ref in h2_tagref.references(sniper):
        if cls == 'jmad':
            print('   %s' % ref)


if __name__ == '__main__':
    main()
