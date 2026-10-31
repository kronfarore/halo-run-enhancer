"""Fill an EMPTY reference that sits right after a known, filled neighbour (field order).

h2_tagref.fill_reference tries every empty record x up to 400 spots (one tool export each): on a
weapon tag (dozens of empty references) that ran for hours. Here the candidates are the few empty
records within `window` bytes after the neighbour's record, and the spot is right after the
neighbour's pooled string (strings are pooled in field order). Accepted exactly as fill_reference
accepts: references = before + this one, every exported field value as before, and the NAMED field
reads the new path. Else the tag is restored.

    python anchored_fill.py <tag file> <class> <new path> <field> <neighbour class> <neighbour path>
"""
import os
import struct
import sys

sys.path.insert(0, r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit')
import h2_tagref as R  # noqa: E402
import h2_tagfield as tf  # noqa: E402


def main(tag, cls, new, field, ncls, npath, window=96):
    original = open(tag, 'rb').read()
    x0 = tf.export(tag)
    if ('<tag_reference name="%s" type="%s">%s<' % (field, cls, new)) in x0:
        print('already filled')
        return
    before = R.references(tag)
    rows0 = [r[4] for r in tf.read_all(x0)]
    nrecs = R.records(original, len(npath), ncls)
    strs = R.pooled(original, npath)
    want = cls.encode('latin-1')[::-1]
    raw = new.encode('latin-1') + b'\0'
    tried = 0
    for nr in nrecs:
        for i in range(nr + 16, nr + 16 + window, 4):
            head = original[i:i + 4]
            if head != want and head != b'\xff' * 4:
                continue
            _p, n, datum = struct.unpack_from('<III', original, i + 4)
            if n != 0 or datum != R.NULL:
                continue
            for s in strs:
                spot = s + len(npath) + 1
                out = bytearray(original)
                out[i:i + 4] = want
                struct.pack_into('<I', out, i + 8, len(new))
                out[spot:spot] = raw
                open(tag, 'wb').write(bytes(out))
                tried += 1
                if sorted(R.references(tag)) != sorted(before + [(cls, new)]):
                    continue
                x = tf.export(tag)
                if not x or [r[4] for r in tf.read_all(x)] != rows0:
                    continue
                if ('<tag_reference name="%s" type="%s">%s<' % (field, cls, new)) not in x:
                    continue
                print('%s: %s -> %s (record 0x%X, path at 0x%X, %d tries)'
                      % (os.path.basename(tag), field, new, i, spot, tried))
                return
    open(tag, 'wb').write(original)
    raise SystemExit('no anchored spot worked (%d tries); restored' % tried)


if __name__ == '__main__':
    main(*sys.argv[1:7], window=int(sys.argv[7]) if len(sys.argv) > 7 else 96)
