r"""Point the SAW's world model back at the Assault Rifle's, as a BISECT.

The ported SAW vanishes when dropped or handed to an ally, but renders in the player's
hands and where the scenario places it. Residency was the obvious suspect and it was
wrong: the pool bits are set and the behaviour did not change. The tags are byte-identical
to the Assault Rifle's apart from the intended path swaps, and the world model matches it
in nodes, markers and node order -- so guessing further is not worth a boot.

This puts the weapon's `hlmt` back to the Assault Rifle's stock model tag, leaving the
SAW's own FIRST-PERSON model in place. The next test then says something definite:

  * dropping works  -> the fault is in OUR model tag or world render model, and the only
    known difference left is the region/permutation name ('default' where every stock
    model says 'standard').
  * dropping still fails -> the fault has nothing to do with the world model; it predates
    it, and the weapon tag or the runtime-creation path is where to look.

    python h3_saw_world_revert.py [--write] [--undo]
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))  # balance tables live beside the JMS converters, see the port backup on F:
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402

B = os.sep
TAGS = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK', 'tags')
AR_MODEL = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW_MODEL = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw_h4_original_numbers'])
WEAPON = os.path.join(TAGS, 'objects', 'weapons', 'rifle', 'saw', 'saw.weapon')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--undo', action='store_true', help='point it back at the SAW model')
    a = ap.parse_args()
    old, new = (SAW_MODEL, AR_MODEL) if not a.undo else (AR_MODEL, SAW_MODEL)
    t = h3tag.Tag(WEAPON)
    present = [(g, p) for _o, g, p in [] ] or None
    print('weapon hlmt: %s\n          -> %s' % (old, new))
    if not a.write:
        print('\n(dry run -- pass --write)')
        return
    before = len(t.data)
    n = t.repoint_in_place(old, new, group='hlmt')
    if len(t.data) != before:
        raise SystemExit('file size changed -- not an in-place overwrite')
    t.save()
    print('%d reference(s) rewritten' % n)
    print('first-person model is untouched -- only the world model reverts')


if __name__ == '__main__':
    main()
