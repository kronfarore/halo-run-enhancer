r"""What is decoded of the Halo 2 animation (jmad) frame format, and what is not.

The port's reload is the donor's length because a Halo 2 animation cannot yet be made
LONGER: `halo3_reload` only rewrites frame counts, and there are no frames past the end to
stretch into. Halo 3's frames were decoded (`h3-animation-format`), Halo 2's have not been.
This is the standing progress on that, written as a reader so the next attempt starts from
measurements rather than from scrollback.

Everything below is verified across all fifteen animations of `fp_saw` (the sniper rifle's
graph) unless it says otherwise.

FINDING THE DATA. A loose graph's `animations` block is at the second `dfbt` chunk, 136
bytes per element. In the element:

    +0x13  u8   node count          42 for a first-person graph
    +0x14  u16  frame count
    +0x34  u32  frame data size
    +0x40  u32  a 2004 runtime pointer, garbage, as in a tag reference
    +0x48  u32  6168 in every animation -- NOT a size of anything stored; the frame data
                sizes alone account for 97% of the file
    +0x50  u32  first stream size
    +0x54  u32  second stream size

The blob itself is not pointed at from the element. It sits in the child data, immediately
after the animation's NAME string, which is pooled there with no terminator -- so the blob
is found by searching for the name and stepping past it, and `+0x34` says how long it is.

THE BLOB. A 32-byte header, then two tables, then the data:

    +0x00  u8[4]  (1, b, c, 1)   -- the two middle bytes are counts, the outer two always 1
    +0x04  u32    0
    +0x08  u32    0
    +0x0C  u32    X = 32 + 8*b   -- end of table A / start of table B
    +0x10  u32    Y = X + 12*c   -- end of table B / start of the data
    +0x14         20 bytes of zero

    table A   b entries of 8 bytes: a packed quaternion, four i16. Entry values read as
              rotations -- the first is (0, 0, 0, 32767), exactly identity.
    table B   c entries of 12 bytes: three floats, a translation (0.0964, 0.0075, 0.0368).

Both tables are STATIC poses, one per node that does not move in that animation, which is
why b and c vary so much between animations (melee b=1, fire b=33).

THE DATA REGION opens with a 52-byte sub-header, and then -- for codec 3 -- it is FULL
FRAME, which is the whole point of this file:

    +0x00  f32    1.0 in every animation
    +0x04  u8     CODEC. 3 in eleven of the fifteen, including both reloads; 6 in three
                  and 8 in one, and those four do not follow anything below.
    +0x05  u8     R, the number of nodes with an animated ROTATION
    +0x06  u8     T, the number of nodes with an animated TRANSLATION
    +0x07  u8     0
    +0x08  f32  } two floats, roughly 1e-4 and 0.5
    +0x0C  f32  }
    +0x10  u32    A  = 32 + R * frames * 8
    +0x14  u32    B  = A + T * frames * 12
    +0x18  u32    frames * 8      one frame of packed quaternion
    +0x1C  u32    frames * 12     one frame of translation
    +0x20  u32    frames * 4      one frame of scalar
    +0x24         16 bytes that read as two more packed quaternions

A and B are not sizes, they are the boundaries of the sections that follow the sub-header:

    [0, A)      R nodes x frames x 8: a packed i16 quaternion PER FRAME
    [A, B)      T nodes x frames x 12: three floats, a translation PER FRAME,
                then a 32-byte TRAILER
    [B, end)    the tail, whose size is exactly the element's first stream size (+0x50):
                a 32-byte HEADER, then the same animation at full precision --
                R x frames x 16 float quaternions and T x frames x 12 translations

**The 32 bytes are at the END of the compressed half and at the START of the uncompressed
one**, and getting that backwards is not a silent error -- it shifts every quaternion by
four frames and `build-cache-file` asserts in `uncompressed_static_data_codec.h` on
`node < header->total_rotated_nodes`. Two measurements settle it: reading the packed
quaternions from offset 0 yields more unit-length ones than reading from 32, and comparing
the packed half against the float half node by node and frame by frame gives a mean error
three times lower at 0 than at 32 (the two halves hold the same rotations, so they can be
checked against each other).

The uncompressed half's 32 bytes are a real header -- (codec 2, R, T, 0), then its own A
and B and its own three strides -- and must be rewritten when the length changes.

**Those two formulas hold on all eleven codec-3 animations, to the byte, and the tail
lands exactly on the element's own number every time.** That is the finding: the rotation
and translation of every moving node are stored once per frame, so stretching them is
resampling and nothing else -- the same job Halo 3 needed, and already solved there.

WHAT IS STILL OPEN:

* **The tail.** It is the largest section (30848 of reload_full's 48448) and it is NOT per
  frame: 428.4 bytes a frame for reload, 99.2 for overlays, 668.9 for melee. It reads as
  packed i16 quaternions when dumped. Until it is understood a rewritten animation cannot
  be reassembled, so this is the one thing between here and a longer reload.
* **Codecs 6 and 8** (put_away, sprint, throw_grenade, pitch_and_turn) are undecoded. Both
  reloads are codec 3, so they do not block the job in hand.
* The two floats at +0x08 are unidentified; a scale and a bias would be the guess.

    python h2_anim.py [<graph>]          report every animation's structure
"""
import os
import struct
import sys

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
DEFAULT = os.path.join(H2EK, 'tags', 'objects', 'characters', 'masterchief', 'fp',
                       'weapons', 'rifle', 'fp_saw', 'fp_saw.model_animation_graph')
SIG = b'dfbt'
#: An animation element is 136 bytes as the kit ships graphs -- and 124 after
#: `model-animation-reset-compression` has rewritten one, which also takes the root struct
#: from 260 to 236: the same fields in a tighter layout, whose offsets have not been
#: mapped. The block is still FOUND in a recompressed graph, and then reported as such
#: rather than read with the wrong offsets -- `tool export-tag-to-xml` is the way to check
#: one of those, and it confirms the retimed frame counts survive recompression.
ELEMS = (136, 124)
ELEM = 136
SUB_HEADER = 52


def animations_chunk(data):
    """(offset, count, element size) of the animations block."""
    i = data.find(SIG)
    while i >= 0:
        _ver, count, elem = struct.unpack_from('<III', data, i + 4)
        if elem in ELEMS:
            return i, count, elem
        i = data.find(SIG, i + 4)
    raise SystemExit('no block of %s-byte elements: not a Halo 2 animation graph'
                     % ' or '.join(str(e) for e in ELEMS))


def element(data, base, k, elem=ELEM):
    """The numbers a single animation's element carries."""
    e = base + k * elem
    return {'nodes': data[e + 0x13],
            'frames': struct.unpack_from('<H', data, e + 0x14)[0],
            'size': struct.unpack_from('<I', data, e + 0x34)[0],
            's1': struct.unpack_from('<I', data, e + 0x50)[0],
            's2': struct.unpack_from('<I', data, e + 0x54)[0]}


def names(data, count):
    """Animation names, in element order, read out of the mode tree's pooled strings."""
    out, at = [], 0
    while len(out) < count:
        i = data.find(b'first_person:', at)
        if i < 0:
            break
        n = i
        while n < len(data) and 32 <= data[n] < 127:
            n += 1
        name = data[i:n].decode('latin-1')
        if name not in out:
            out.append(name)
        at = i + 1
    return out


def blob(data, name):
    """Where an animation's frame data starts: immediately after its pooled name."""
    i = data.find(name.encode('latin-1'))
    return -1 if i < 0 else i + len(name)


def header(data, at):
    """The blob's 32-byte header, and the two tables it delimits."""
    a, b, c, e = struct.unpack_from('<4B', data, at)
    x, y = struct.unpack_from('<2I', data, at + 12)
    return {'a': a, 'static_rotations': b, 'static_translations': c, 'e': e,
            'table_b': x, 'data': y,
            'consistent': x == 32 + 8 * b and y == x + 12 * c}


def sub(data, at, y):
    """The 52-byte sub-header at the top of the data region."""
    o = at + y
    f0 = struct.unpack_from('<f', data, o)[0]
    fa, fb = struct.unpack_from('<2f', data, o + 8)
    codec, r, t, _z = struct.unpack_from('<4B', data, o + 4)
    a, b, s8, s12, s4 = struct.unpack_from('<5I', data, o + 16)
    return {'one': f0, 'codec': codec, 'R': r, 'T': t, 'floats': (fa, fb),
            'A': a, 'B': b, 'stride8': s8, 'stride12': s12, 'stride4': s4}


def sections(e, h, s):
    """Where each section of the data region starts and ends, per the decoded model."""
    f = e['frames']
    a = 32 + s['R'] * f * 8
    b = a + s['T'] * f * 12
    tail = e['size'] - h['data'] - SUB_HEADER - b
    return {'A': a, 'B': b, 'tail': tail,
            'ok': a == s['A'] and b == s['B'] and tail == e['s1']}


def report(path):
    data = open(path, 'rb').read()
    chunk, count, elem = animations_chunk(data)
    base = chunk + 16
    print('%s  %d bytes, %d animations' % (os.path.basename(path), len(data), count))
    print('%-28s %-5s %-6s %-4s %-4s %-7s %-8s %s'
          % ('name', 'frms', 'codec', 'R', 'T', 'size', 'tail', 'checks'))
    good = 0
    for k, name in enumerate(names(data, count)):
        e = element(data, base, k, elem)
        at = blob(data, name)
        if at < 0:
            print('%-28s  no blob found' % name)
            continue
        h = header(data, at)
        s = sub(data, at, h['data'])
        m = sections(e, h, s)
        checks = ['hdr' if h['consistent'] else 'HDR?']
        if s['codec'] != 3:
            checks.append('codec %d, not decoded' % s['codec'])
        else:
            checks.append('sections' if m['ok'] else 'SECTIONS?')
            good += m['ok']
        print('%-28s %-5d %-6d %-4d %-4d %-7d %-8d %s'
              % (name, e['frames'], s['codec'], s['R'], s['T'], e['size'], m['tail'],
                 ' '.join(checks)))
    total = sum(1 for _k, n in enumerate(names(data, count))
                if sub(data, blob(data, n), header(data, blob(data, n))['data'])['codec'] == 3)
    print('%d of %d codec-3 animations decode exactly' % (good, total))


if __name__ == '__main__':
    report(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
