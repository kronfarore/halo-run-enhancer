r"""Decoding Halo 3 animation data, so a ported weapon's reload can be resampled.

Step 9 needs an animation made LONGER -- the cloned graph holds the Assault Rifle's
58-frame reload and the SAW wants 109 -- and nothing short of rebuilding the frames will
do it (see h3_anim_inspect.py for the shortcuts that were ruled out).

WHAT IS PROVEN HERE
-------------------
Each animation is one "resource member" declaring seven sections, whose sizes the tag
reports: static_node_flags, animated_node_flags, movement_data, pill_offset_data,
default_data, uncompressed_data and compressed_data.

The important one is a law that holds EXACTLY for all seventeen animations in the
Assault Rifle's first-person graph:

    uncompressed_data == 32 + frame_count * stride

   member  frames  uncompressed   stride          member  frames  uncompressed  stride
        0       5           512       96               9      90         30272     336
        3     100         14432      144              10     109         38400     352
        4      30         14432      480              12      20          6512     324
        5      30         14912      496              13      58         27408     472
        6      20          1952       96              15      41         15776     384

That is the whole point: the uncompressed form is a 32-byte header followed by one
fixed-size record per FRAME. Resampling is then interpolation between records rather
than a codec problem, and the tag carries the uncompressed size alongside the compressed
one -- so the poses may be readable without touching the compression at all.

The stride is per animation because it depends on how many nodes move: the two 24-byte
flag fields are three 64-bit masks each (rotation / translation / scale, static and
animated), which is enough for the graph's 43 nodes.

WHERE THE BLOBS ARE
-------------------
Each animation is its own `tgst` chunk, and the chunk is always exactly 24 bytes longer
than the sum of its declared sections -- which turned out to be two chunk headers rather
than any member fields: an EMPTY `tgst` (length 0), then a `tgda` whose length equals the
section sum exactly. Verified for all seventeen animations, so the sections begin at
`payload_at + 24` and `tgda`'s length is the check that the member was found.

Searching for the blobs as a flat run of members from the start of `bdat` never worked
because they are not laid out that way: they are chunks in the tree, one per animation,
under the resource-members block.

THE BLOB STARTS WITH A DESCRIPTOR, NOT BITMASKS
-----------------------------------------------
The tag lists the section SIZES in a `data sizes` struct, and it is tempting to read the
blob in that order -- 24 bytes of static node flags, then 24 animated. That is wrong. The
first 24 bytes are a descriptor of six u32s, and one of them settles it:

    u32 at +16 == default_data - 4        exactly, for all seventeen animations
    (360/356, 312/308, 144/140, 136/132, 216/212, 232/228, 168/164, 192/188, ...)

A bitmask cannot track a section size like that. The other fields fit a descriptor too:
+0 packs four small bytes, `01 <n> <m> 01`, where n runs 11..33 and m is 1, 3 or 5; +12
is a second offset sitting either 16 or 64 below default_data.

The earlier reading looked plausible because the first 24 bytes DO parse as three 64-bit
masks with every bit below the skeleton's 43 nodes. What killed it: animations with
identical popcounts there have completely different strides (five share [6,3,4] while
their strides are 96, 96, 96, 336 and 352), so whatever those bytes are, they are not
what sizes the per-frame record. The skeleton really is 43 nodes, checked in the graph.

    python h3_anim_decode.py --tree            # the real chunk tree
    python h3_anim_decode.py --sizes           # the section table and the stride law
    python h3_anim_decode.py --blobs           # locate each animation's data
"""
import argparse, io, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
AR_FP = os.path.join(EK, 'tags', 'objects', 'characters', 'masterchief', 'fp', 'weapons',
                     'rifle', 'fp_assault_rifle', 'fp_assault_rifle.model_animation_graph')
SECTIONS = ('static_node_flags', 'animated_node_flags', 'movement_data',
            'pill_offset_data', 'default_data', 'uncompressed_data', 'compressed_data')
HEADER = 0x40
NODES = 43


def members_from_xml(path):
    """The per-animation section sizes, as `tool export-tag-to-xml` reports them."""
    s = io.open(path, encoding='utf-8', errors='replace').read()
    out = []
    for m in re.finditer(r'<element index="(\d+)" name="\d+\. '
                         r'model_animation_tag_resource_member">(.*?)</element>', s, re.S):
        body = m.group(2)

        def g(k):
            hit = re.search(r'name="%s" value="([^"]*)"' % k, body)
            return int(hit.group(1)) if hit else 0

        e = {'index': int(m.group(1)), 'frames': g('frame count'),
             'nodes': g('node count')}
        for k in SECTIONS:
            e[k] = g(k)
        e['size'] = sum(e[k] for k in SECTIONS)
        out.append(e)
    return out


def tree(d, start=HEADER, end=None, depth=0):
    """The chunk tree, walked strictly: 4cc reversed, u32 flags, u32 length, payload."""
    end = len(d) if end is None else end
    off = start
    while off + 12 <= end:
        mark = bytes(d[off:off + 4])[::-1].decode('latin1', 'replace')
        flags, length = struct.unpack_from('<II', d, off + 4)
        if off + 12 + length > end:
            print('%s!! %r @%#x length %d overruns its parent' % ('  ' * depth, mark, off, length))
            return
        print('%s%-6r @%#08x flags=%#x len=%d' % ('  ' * depth, mark, off, flags, length))
        if mark in ('tag!',) and depth < 4:
            tree(d, off + 12, off + 12 + length, depth + 1)
        off += 12 + length


def sizes(mem):
    print('%-4s %-7s %-6s %s' % ('anim', 'frames', 'stride', '   '.join(SECTIONS)))
    good = 0
    for e in mem:
        rest = e['uncompressed_data'] - 32
        stride = rest / float(e['frames']) if e['frames'] else 0
        exact = e['frames'] and rest % e['frames'] == 0
        good += bool(exact)
        print('%-4d %-7d %-6s %s%s'
              % (e['index'], e['frames'], ('%d' % stride) if exact else '%.2f' % stride,
                 ' '.join('%6d' % e[k] for k in SECTIONS), '' if exact else '   NOT EXACT'))
    print('\nuncompressed_data == 32 + frames * stride holds for %d of %d animations'
          % (good, len(mem)))


def blobs(tag, mem):
    """Each animation's data chunk, matched to its declared sizes.

    A member is a `tgst` whose length is its section sum plus 24 -- an empty `tgst` and
    a `tgda` header. `tgda`'s own length must equal the section sum, which is what makes
    the match a proof rather than a guess.
    """
    want = {e['size'] for e in mem}
    found = sorted((n for n in tag.nodes()
                    if n.marker == 'tgst' and (n.length - 24) in want),
                   key=lambda n: n.off)
    out = []
    for n, e in zip(found, mem):
        inner = struct.unpack_from('<I', tag.data, n.payload_at + 12 + 8)[0]
        out.append(dict(e, chunk=n.off, at=n.payload_at + 24, tgda=inner,
                        ok=inner == e['size']))
    return out


def header(tag, mem):
    """The 24-byte descriptor each blob opens with, against the declared sizes."""
    print('%-5s %-12s %-9s %-9s %-9s %s'
          % ('anim', '+0', '+4/+8', '+12', '+16', 'default_data  (+16 == default-4?)'))
    exact = 0
    for e in blobs(tag, mem):
        f = struct.unpack_from('<6I', tag.data, e['at'])
        hit = f[4] == e['default_data'] - 4
        exact += hit
        print('%-5d %#-12x %-9s %-9d %-9d %-13d %s'
              % (e['index'], f[0], '%d/%d' % (f[1], f[2]), f[3], f[4],
                 e['default_data'], 'yes' if hit else 'NO'))
    print('\n+16 == default_data - 4 for %d of %d animations' % (exact, len(mem)))


def scan(d, mem, lo, hi):
    """Look for a start where every member's flag fields read as real flags: sparse, and
    with no bit set above the graph's node count."""
    best = None
    for start in range(lo, hi):
        off, ok, score = start, True, 0
        for e in mem:
            for k in range(2):
                for w in struct.unpack_from('<3Q', d, off + k * 24):
                    if w >> NODES:
                        ok = False
                        break
                    score += bin(w).count('1')
                if not ok:
                    break
            if not ok:
                break
            off += e['size']
        if ok and (best is None or score < best[1]):
            best = (start, score)
    if best:
        print('candidate start %#x (total set bits %d)' % best)
    else:
        print('no start in %#x..%#x lays the members out back to back with valid flags'
              % (lo, hi))
        print('-> the members are not simply concatenated in declaration order')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default=AR_FP)
    ap.add_argument('--xml', help='tool export-tag-to-xml output for the same tag')
    ap.add_argument('--tree', action='store_true')
    ap.add_argument('--sizes', action='store_true')
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--blobs', action='store_true')
    ap.add_argument('--header', action='store_true')
    a = ap.parse_args()

    d = io.open(a.tag, 'rb').read()
    print('%s  %d bytes\n' % (os.path.basename(a.tag), len(d)))
    if a.tree or not (a.sizes or a.scan or a.blobs or a.header):
        tree(d)
    if not (a.sizes or a.scan or a.blobs or a.header):
        return
    if not a.xml or not os.path.exists(a.xml):
        raise SystemExit('--sizes and --scan need --xml from tool export-tag-to-xml')
    mem = members_from_xml(a.xml)
    print('%d animation(s)\n' % len(mem))
    if a.sizes:
        sizes(mem)
    if a.blobs:
        sys.path.insert(0, HERE)
        import h3tag
        got = blobs(h3tag.Tag(a.tag), mem)
        print('%-5s %-10s %-10s %-8s %s' % ('anim', 'chunk', 'data at', 'tgda', 'sections'))
        for e in got:
            print('%-5d %#-10x %#-10x %-8d %-8d %s'
                  % (e['index'], e['chunk'], e['at'], e['tgda'], e['size'],
                     'ok' if e['ok'] else 'MISMATCH'))
        print('\n%d of %d animations located' % (sum(e['ok'] for e in got), len(mem)))
    if a.header:
        sys.path.insert(0, HERE)
        import h3tag
        header(h3tag.Tag(a.tag), mem)
    if a.scan:
        scan(d, mem, HEADER, min(len(d) - sum(e['size'] for e in mem), 0x8000))


if __name__ == '__main__':
    main()
