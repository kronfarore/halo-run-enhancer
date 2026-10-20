r"""Step 9 of a Halo 2 port: first-person animation graphs of its OWN, one per player species,
and the sounds they cue (generalized from h2_saw_animations.py, the SAW 2026-09-23/24).

A port inherits the donor's graphs, which a live weapon may share (the GPMG borrows the SNIPER
RIFLE's), so retiming the port would retime that weapon: both graphs are cloned and the weapon
repointed; the graph's `snd!` references move to the balance donor's one for one (then to the
port's own sounds at step 10). Retiming is h2_anim_retime.py (generic; codec 3, ends pinned).
For a HALO 3 source, its own FP graphs copy node-for-node onto both species (H2_PORT_PLAN 0.4:
H3's arm skeletons ARE Halo 2's); that import is the wave-A pilot's to build -- this clone is the
SAW's donor route.

The config's `animations` section:
    weapon      the port's weapon (kit-relative, with extension)
    graphs      [(species, the donor graph, the port's own copy)] (paths without extension)
    sounds      [(donor sound, the balance donor's equivalent)]
    untouched   a live weapon whose graphs must stay its own (printed as the check)

    python h2_port_animations.py <key> [--force]
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402

B = os.sep
TAGS = os.path.join(h2_tagref.H2EK, 'tags')
EXT = '.model_animation_graph'
GRAPHS, SOUNDS = [], []
WEAPON = UNTOUCHED = None


def setup(key):
    global GRAPHS, SOUNDS, WEAPON, UNTOUCHED
    a = ports_h2.get(key, 'animations')
    GRAPHS = [tuple(g) for g in a['graphs']]
    SOUNDS = [tuple(x) for x in a.get('sounds', ())]
    WEAPON, UNTOUCHED = a['weapon'], a.get('untouched')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    setup(argv[0])
    force = '--force' in argv
    print('cloning the graphs a live weapon would otherwise share:')
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

    print('giving it the balance donor\'s noises instead of the donor graph\'s:')
    for _species, _donor, port in GRAPHS:
        graph = os.path.join(TAGS, port + EXT)
        have = h2_tagref.references(graph)
        for old, new in SOUNDS:
            if ('snd!', new) in have:
                print('   %-22s already the balance donor\'s' % os.path.basename(new))
            elif ('snd!', old) in have:
                h2_tagref.set_reference(graph, 'snd!', old, new)
            else:
                print('   %-22s not named by %s' % (os.path.basename(old), port))

    if not UNTOUCHED:
        return
    print('what %s still points at, which must be untouched:' % os.path.basename(UNTOUCHED))
    for cls, ref in h2_tagref.references(os.path.join(TAGS, UNTOUCHED)):
        if cls == 'jmad':
            print('   %s' % ref)


if __name__ == '__main__':
    main()
