r"""Step 4: put the Halo 4 SAW's own numbers into the Halo 2 tags.

Until now the port is a SAW that shoots like the cut GPMG, which shoots like the Warthog
turret. These are the values `tool export-tag-to-xml` reports for `storm_lmg` in H4EK,
written into the port's tags through `h2_tagfield.py`, which finds each field by probing
for it and makes tool.exe confirm every write.

A port carries its ORIGINAL numbers by default; the balance option (step 5) is what
swaps in values derived for the target game. So this is deliberately a transcription,
not a judgement -- with two exceptions, both noted in SKIPPED below.

The interesting part is that the two guns land in nearly the same place anyway:

    Halo 4 SAW    7.5 damage at 20 rounds/sec  = 150 a second
    Halo 2 GPMG    15 damage at 10-13 rps      = 150 to 195 a second

so the port is not going to arrive twice as strong as the game around it. The magazine
is what really changes: 72 loaded against 40.

    python h2_saw_numbers.py [--show]

`--show` prints what is there now and what would be written, and changes nothing.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagfield as tf

B = os.sep
TAGS = os.path.join(tf.H2EK, 'tags')
SAW = os.path.join('objects', 'weapons', 'rifle', 'saw')

WEAPON = os.path.join(SAW, 'saw.weapon')
BULLET = os.path.join(SAW, 'damage_effects', 'saw_bullet.damage_effect')

#: (tag, field, block, element, which occurrence of the name, the Halo 4 value)
#:
#: `nth` matters: tool flattens a block's nested structs into one list, so `barrels`
#: prints TWO "minimum error" fields and two "error angle"s. The first pair belongs to
#: the firing-error struct and reads zero; the live ones are the second.
NUMBERS = [
    (WEAPON, 'rounds loaded maximum', 'magazines', 0, 0, 72),
    (WEAPON, 'rounds reloaded', 'magazines', 0, 0, 72),
    (WEAPON, 'rounds total initial', 'magazines', 0, 0, 216),
    (WEAPON, 'rounds total maximum', 'magazines', 0, 0, 288),
    (WEAPON, 'rounds per second', 'barrels', 0, 0, [20.0, 20.0]),
    (WEAPON, 'minimum error', 'barrels', 0, 1, 0.0),
    (WEAPON, 'error angle', 'barrels', 0, 1, [0.3, 2.75]),
    (BULLET, 'damage lower bound', '', 0, 0, 7.5),
    (BULLET, 'damage upper bound', '', 0, 0, [7.5, 7.5]),
]

#: Halo 4 values deliberately NOT carried across, and why.
SKIPPED = [
    ('fire recovery time', '0.0666667 in Halo 4, which caps a weapon at 15 rounds a '
                           'second -- it would fight the 20 this one is being given. '
                           'Halo 2 paces automatic fire with rounds per second.'),
    ('maximum range 75', 'Halo 2 does it with the projectile\'s air damage range, '
                         'already 0..80 -- near enough that changing it is noise.'),
    ('damage reporting type', 'still says "human turret", which decides which medal a '
                              'kill counts as. Cosmetic, and it belongs with the HUD '
                              'work rather than here.'),
]


def show():
    for tag, name, block, index, nth, want in NUMBERS:
        path = os.path.join(TAGS, tag)
        rows = tf.read_all(tf.export(path))
        row = tf.pick(rows, name, block, index, nth)
        now = row[4].splitlines()[0]
        wants = want if isinstance(want, list) else [want]
        print('   %-26s %-24s %-22s -> %s'
              % (os.path.basename(tag), ('%s.' % block if block else '') + name,
                 now, ','.join('%g' % v for v in wants)))


def main():
    if '--show' in sys.argv:
        print('what the port says now, and what Halo 4 says:')
        show()
        return
    print('writing the Halo 4 SAW\'s numbers into the port:')
    for tag, name, block, index, nth, want in NUMBERS:
        path = os.path.join(TAGS, tag)
        try:
            tf.set_field(path, name, want, block, index, nth)
        except Exception as exc:
            print('   %-30s FAILED: %s' % (name, exc))
    print('left as Halo 2 had it, on purpose:')
    for name, why in SKIPPED:
        print('   %-22s %s' % (name, why))


if __name__ == '__main__':
    main()
