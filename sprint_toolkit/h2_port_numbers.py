r"""Step 4 of a Halo 2 port: the SOURCE weapon's own numbers into the port's tags
(generalized from h2_saw_numbers.py, the SAW 2026-09-23).

A port carries its original numbers by default; the balance option (step 5) swaps in the derived
ones. Each value goes through h2_tagfield (the field is FOUND by probing a copy, and tool.exe's
export confirms the write). The config's `numbers` section:

    numbers   [(tag file, field, block, element, nth, value or [values][, opt])] -- `nth` because
              tool flattens nested structs (a barrel prints two "minimum error"s; the live one is
              1); opt {'anchor': (field, byte delta)} places a field still reading ZERO by a
              non-zero neighbour (pin(): probed, then remembered)
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
    for tag, name, block, index, nth, want in (r[:6] for r in n['numbers']):
        rows = tf.read_all(tf.export(os.path.join(TAGS, tag)), indices=True)
        row = tf.pick(rows, name, block, index, nth)
        now = row[4].splitlines()[0]
        wants = want if isinstance(want, list) else [want]
        print('   %-26s %-24s %-22s -> %s'
              % (os.path.basename(tag), ('%s.' % block if block else '') + name,
                 now, ','.join('%g' % v for v in wants)))


def pin(tag_path, name, block, index, nth, anchor, delta, anchor_index=None):
    """A field still reading ZERO cannot be found by its value (it reads like the padding around
    it): place it at `delta` bytes from a non-zero neighbour of the same struct (`anchor`, found
    as usual), PROVE it the way h2_tagfield does -- a probe written there into a copy must move
    that field and nothing else in tool's export -- and remember it for this tag, so set_field
    uses it (the Flamethrower, S1: the projectile's timer / radii, the damage flags). `anchor_index`
    takes the anchor from ANOTHER element of the same block (the Mauler, A4: a graph's sound-reference
    flags reading 0 beside an element whose flags do not; default: the field's own element)."""
    import struct
    key = ('%s[%d].%s' % (block, index, name) if block else name) + ('#%d' % nth if nth else '')
    # (a cached offset is NOT trusted for a zero: a longer path written earlier in the file -- a
    # re-wiring -- shifts every later byte, and zero cannot be re-validated by its value)
    rows = tf.read_all(tf.export(tag_path), indices=True)
    row = tf.pick(rows, name, block, index, nth)
    if any(tf._numbers(row[4])):
        return                  # non-zero now: h2_tagfield finds it by its value
    at = tf.offset_of(tag_path, anchor, block, index if anchor_index is None else anchor_index, 0,
                      verbose=False) + delta
    original = open(tag_path, 'rb').read()
    code = tf.SCALARS[row[3]][0]
    edited = bytearray(original)
    # an ENUM probes with 1 (valid in any enum: 3 is out of range in a 3-value one and tool prints
    # it unchanged -- the Spartan Laser's overcharged action, A2)
    struct.pack_into(code, edited, at, 0.5 if code == '<f' else 1 if row[3] in ('enum', 'char enum') else 3)
    probe = '%s._pin_%d%s' % (os.path.splitext(tag_path)[0], os.getpid(), os.path.splitext(tag_path)[1])
    try:
        open(probe, 'wb').write(bytes(edited))
        after = tf.read_all(tf.export(probe) or '', indices=True)
    finally:
        if os.path.exists(probe):
            os.remove(probe)
    moved = [i for i, (a, b) in enumerate(zip(rows, after)) if a[4] != b[4]]
    if len(after) != len(rows) or len(moved) != 1 or rows[moved[0]] is not row:
        raise LookupError('%s is not at %s %+d (0x%04X): the probe moved %d fields'
                          % (key, anchor, delta, at, len(moved)))
    print('   %-44s pinned at 0x%04X (%s %+d)' % (key, at, anchor, delta))
    tf._remember(tf.tag_key(tag_path), key, at)


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
    for row in n['numbers']:
        tag, name, block, index, nth, want = row[:6]
        try:
            if len(row) > 6 and row[6].get('anchor'):
                pin(os.path.join(TAGS, tag), name, block, index, nth, *row[6]['anchor'])
            tf.set_field(os.path.join(TAGS, tag), name, want, block, index, nth)
        except Exception as exc:
            print('   %-30s FAILED: %s' % (name, exc))
    print('left as Halo 2 had it, on purpose:')
    for name, why in n.get('skipped', ()):
        print('   %-22s %s' % (name, why))


if __name__ == '__main__':
    main()
