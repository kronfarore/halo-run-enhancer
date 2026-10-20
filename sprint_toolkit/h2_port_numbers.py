r"""Step 4 of a Halo 2 port: the SOURCE weapon's own numbers into the port's tags
(generalized from h2_saw_numbers.py, the SAW 2026-09-23).

A port carries its original numbers by default; the balance option (step 5) swaps in the derived
ones. Each value goes through h2_tagfield (the field is FOUND by probing a copy, and tool.exe's
export confirms the write). The config's `numbers` section:

    numbers   [(tag file, field, block, element, nth, value or [values])] -- `nth` because tool
              flattens nested structs (a barrel prints two "minimum error"s; the live one is 1)
    skipped   [(field, why)] -- source values deliberately NOT carried (printed)

    python h2_port_numbers.py <key> [--show]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagfield as tf  # noqa: E402
import ports_h2  # noqa: E402

TAGS = os.path.join(tf.H2EK, 'tags')


def show(n):
    for tag, name, block, index, nth, want in n['numbers']:
        rows = tf.read_all(tf.export(os.path.join(TAGS, tag)))
        row = tf.pick(rows, name, block, index, nth)
        now = row[4].splitlines()[0]
        wants = want if isinstance(want, list) else [want]
        print('   %-26s %-24s %-22s -> %s'
              % (os.path.basename(tag), ('%s.' % block if block else '') + name,
                 now, ','.join('%g' % v for v in wants)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    n = ports_h2.get(argv[0], 'numbers')
    if '--show' in argv:
        print('what the port says now, and what the source says:')
        show(n)
        return
    print('writing the source weapon\'s numbers into the port:')
    for tag, name, block, index, nth, want in n['numbers']:
        try:
            tf.set_field(os.path.join(TAGS, tag), name, want, block, index, nth)
        except Exception as exc:
            print('   %-30s FAILED: %s' % (name, exc))
    print('left as Halo 2 had it, on purpose:')
    for name, why in n.get('skipped', ()):
        print('   %-22s %s' % (name, why))


if __name__ == '__main__':
    main()
