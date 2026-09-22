r"""Decoding Halo 3 animation data, so a ported weapon's reload can be resampled.

Step 9 needs an animation made LONGER -- the cloned graph holds the Assault Rifle's
58-frame reload and the SAW wants 109 -- and nothing short of rebuilding the frames will
do it (see h3_anim_inspect.py for the shortcuts that were ruled out).

THE SECTION SIZES
-----------------
Each animation is one "resource member" declaring seven section sizes:
static_node_flags, animated_node_flags, movement_data, pill_offset_data, default_data,
uncompressed_data and compressed_data.

WHERE THE BLOBS ARE
-------------------
Each animation is its own `tgst` chunk, always exactly 24 bytes longer than the sum of
its sections -- two chunk headers: an EMPTY `tgst` (length 0), then a `tgda` whose
length equals the section sum exactly. That equality is the proof a member was found,
and it holds for all seventeen. Sections begin at `payload_at + 24`.

They are NOT a flat run inside `bdat`; they are chunks in the tree, one per animation.

DEFAULT_DATA COMES FIRST, AND DESCRIBES ITSELF
----------------------------------------------
It opens with a 32-byte header:
    +0   `01 n m 01` -- n static rotations, m static translations, one scale
    +12  8 * (n + 4), the offset to the translations
    +16  default_data - 4, the offset to the scale
so `default_data == 32 + 8n + 12m + 4`, exact for every animation. Its rotations are the
only quantised thing in the format: 8-byte int16 quaternions over 32767.

THE LAYOUT, CRACKED
-------------------
    [default_data][compressed_data][static flags 24][animated flags 24][uncompressed]

The flag fields were found by signature, not by guessing an order: their first three
masks' popcounts are exactly (n, m, 1), the counts default_data's header declares. They
sit at `default_data + compressed_data` in all seventeen animations. The last three
masks are the ANIMATED nodes: R rotations, T translations, S scales.

The frames are CHANNEL-MAJOR. Not one record per frame -- every rotation for every
frame, then every translation, then every scale:

    [ frames * R quaternions, 16 bytes -- four float32 ]
    [ frames * T translations, 12 bytes -- three float32 ]
    [ frames * S scales, 4 bytes ]

so `uncompressed_data == 32 + frames*(16R + 12T + 4S)`, exact for all seventeen. That is
why it looked like a per-frame stride of 16R+12T+4S -- that number is just the total
divided by the frames, and reading it as a record is what made every earlier attempt
fail. The giveaway was that the non-unit quaternions were never scattered: they were
always one contiguous run at the END, starting at exactly frames*R.

Nothing is quantised and nothing is packed, so the compressed section can be ignored
entirely. Verified: all 17 decode to unit quaternions (error 0.000000), translations
come out small and smooth, and decode -> pack reproduces the original bytes EXACTLY for
every animation. `resample` slerps rotations and lerps the rest; an identity resample is
byte-identical, endpoints are preserved exactly, and 58 -> 109 frames gives 51448 bytes,
which is what 32 + 109*(16*25 + 12*6) predicts.

Only the default pose is quantised: its rotations are 8-byte int16 quaternions
(/32767), its translations three float32, and its single scale 1.0.

    python h3_anim_decode.py --tree            # the real chunk tree
    python h3_anim_decode.py --sizes           # the section table and the stride law
    python h3_anim_decode.py --blobs           # locate each animation's data
    python h3_anim_decode.py --layout          # sections, counts, and the quaternion check
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


def records(tag, mem, want=13):
    """Where do the per-frame records start, and what shape are they?

    Real motion is smooth: frame n+1 resembles frame n. Noise does not. So the frames
    are hunted by reading every candidate offset as int16 and scoring the mean absolute
    difference between consecutive records at the known stride.
    """
    import array
    e = next((g for g in blobs(tag, mem) if g['index'] == want), None)
    if e is None:
        print('no animation %d' % want)
        return
    blob = bytes(tag.data[e['at']:e['at'] + e['size']])
    frames = e['frames']
    stride = (e['uncompressed_data'] - 32) // frames
    need = 32 + frames * stride
    print('animation %d: %d frames, stride %d, needs %d of %d blob bytes'
          % (want, frames, stride, need, len(blob)))

    def rough(at, k=4):
        tot = cnt = 0
        for i in range(min(k, frames - 2)):
            a, b = array.array('h'), array.array('h')
            a.frombytes(blob[at + 32 + i * stride:at + 32 + (i + 1) * stride])
            b.frombytes(blob[at + 32 + (i + 1) * stride:at + 32 + (i + 2) * stride])
            for x, y in zip(a, b):
                tot += abs(x - y)
                cnt += 1
        return tot / max(cnt, 1)

    best = sorted((rough(at), at) for at in range(0, len(blob) - need + 1, 2))
    print('\nlowest frame-to-frame difference:')
    for v, at in best[:5]:
        print('   offset %-7d mean |delta| %.1f' % (at, v))
    mid = best[len(best) // 2]
    print('   (a middling offset %d scores %.1f, so the best is %.1fx better)'
          % (mid[1], mid[0], mid[0] / max(best[0][0], 1e-9)))

    at = best[0][1]
    recs = [blob[at + 32 + i * stride:at + 32 + (i + 1) * stride] for i in range(frames)]
    ch = [sum(1 for i in range(frames - 1) if recs[i][j] != recs[i + 1][j])
          for j in range(stride)]
    print('\nbyte columns that change, first 32 at offset %d:' % at)
    print('   ' + ' '.join('%2d' % c for c in ch[:32]))
    for period in (4, 8, 12, 16):
        groups = [[ch[j] for j in range(k, stride, period)] for k in range(period)]
        spread = sum(max(g) - min(g) for g in groups) / float(period)
        print('   period %-3d mean spread within a lane %.1f' % (period, spread))


def layout(tag, mem):
    """Where every section of every blob is, and what shape its frames are.

    THE BLOB, settled against all seventeen animations:

        [default_data][compressed_data][static flags 24][animated flags 24][uncompressed]

    `default_data` comes FIRST and opens with a 32-byte header:
        +0   four bytes, `01 n m 01` -- n static rotations, m static translations, 1 scale
        +12  8 * (n + 4), the offset to the translations
        +16  default_data - 4, the offset to the single scale
    so `default_data == 32 + 8n + 12m + 4`, exact for every animation.

    The two flag fields sit at `default_data + compressed_data`, which is how they were
    found: the first three masks' popcounts are exactly (n, m, 1), matching the header.
    The last three are the ANIMATED nodes, and they size the frames:

        stride == 16 * R + 12 * T + 4 * S

    exact for all seventeen, including the awkward 324 that is not a multiple of 8.
    So a rotation is SIXTEEN bytes -- four float32, a plain unit quaternion -- a
    translation twelve, and a scale four. Nothing is quantised and nothing is packed,
    which is what makes resampling arithmetic.

    Confirmed by the data itself: every animation with no animated translations reads
    as exactly unit quaternions, on every frame, to five decimal places. The eight that
    DO have translations do not yet, so how a frame interleaves the two is still open.
    """
    pc = lambda v: bin(v).count('1')                          # noqa: E731
    out = []
    for e in blobs(tag, mem):
        b = tag.data[e['at']:e['at'] + e['size']]
        hdr = struct.unpack_from('<I', b, 0)[0]
        n, mm = (hdr >> 8) & 0xFF, (hdr >> 16) & 0xFF
        flags_at = e['default_data'] + e['compressed_data']
        w = struct.unpack_from('<6Q', b, flags_at)
        R, T, Sc = pc(w[3]), pc(w[4]), pc(w[5])
        stride = (e['uncompressed_data'] - 32) // e['frames'] if e['frames'] else 0
        out.append(dict(e, static=(n, mm, 1), animated=(R, T, Sc), flags_at=flags_at,
                        frames_at=flags_at + 48 + 32, stride=stride,
                        default_ok=e['default_data'] == 32 + 8 * n + 12 * mm + 4,
                        stride_ok=stride == 16 * R + 12 * T + 4 * Sc,
                        static_ok=(pc(w[0]), pc(w[1]), pc(w[2])) == (n, mm, 1)))
    return out


def quaternions(tag, e, frame):
    """The rotations of one frame, as (w, x, y, z) floats.

    Channel-major: every frame's rotations sit together before any translation, so a
    frame's block starts at `frames_at + frame * R * 16`, NOT at a per-frame stride.
    """
    b = tag.data[e['at']:e['at'] + e['size']]
    R = e['animated'][0]
    at = e['frames_at'] + frame * R * 16
    return [struct.unpack_from('<4f', b, at + i * 16) for i in range(R)]


def report_layout(tag, mem):
    import math
    print('%-5s %-7s %-7s %-14s %-14s %-9s %s'
          % ('anim', 'frames', 'stride', 'static R/T/S', 'animated R/T/S', 'frames@',
             'checks'))
    ok = {'default': 0, 'static': 0, 'stride': 0, 'unit': 0, 'unit_possible': 0}
    for e in layout(tag, mem):
        ok['default'] += e['default_ok']
        ok['static'] += e['static_ok']
        ok['stride'] += e['stride_ok']
        worst = 0.0
        for f in range(e['frames']):
            for q in quaternions(tag, e, f):
                worst = max(worst, abs(math.sqrt(sum(c * c for c in q)) - 1.0))
        unit = worst < 1e-3
        ok['unit_possible'] += 1
        ok['unit'] += unit
        print('%-5d %-7d %-7d %-14s %-14s %-9d %s%s%s  quat err %.5f%s'
              % (e['index'], e['frames'], e['stride'], str(e['static']),
                 str(e['animated']), e['frames_at'],
                 'D' if e['default_ok'] else '-', 'S' if e['static_ok'] else '-',
                 'T' if e['stride_ok'] else '-', worst,
                 '' if unit else '   <-- NOT UNIT'))
    n = len(mem)
    print('\ndefault_data == 32 + 8n + 12m + 4 : %d/%d' % (ok['default'], n))
    print('static masks popcount (n, m, 1)   : %d/%d' % (ok['static'], n))
    print('stride == 16R + 12T + 4S          : %d/%d' % (ok['stride'], n))
    print('unit quaternions every frame      : %d/%d' % (ok['unit'], ok['unit_possible']))
    exact_bytes = 0
    for e in layout(tag, mem):
        blob = bytes(tag.data[e['at']:e['at'] + e['size']])
        want = blob[e['frames_at']:e['frames_at'] + e['uncompressed_data'] - 32]
        exact_bytes += pack_animation(read_animation(tag, e)) == want
    print('round trip decode -> pack exact    : %d/%d' % (exact_bytes, n))


def read_animation(tag, e):
    """Decode one animation's poses.

    The frames are CHANNEL-MAJOR, not one record per frame -- which is what made the
    earlier readings fail. Every rotation for every frame comes first, then every
    translation, then every scale:

        [ frames * R quaternions, 16 bytes each ]
        [ frames * T translations, 12 bytes each ]
        [ frames * S scales, 4 bytes each ]

    so `uncompressed_data == 32 + frames*(16R + 12T + 4S)`. That is why the size looked
    like a per-frame stride of 16R+12T+4S: it is simply the total divided by the frames.

    Returns {'rotations': [[(w,x,y,z) per animated node] per frame], 'translations':
    [[(x,y,z)]], 'scales': [[f]]} -- plain floats, nothing quantised.
    """
    b = tag.data[e['at']:e['at'] + e['size']]
    F = e['frames']
    R, T, S = e['animated']
    at = e['frames_at']
    tbase = at + F * R * 16
    sbase = tbase + F * T * 12
    # NODE-major within each channel: all of node 0's frames, then all of node 1's.
    # Reading it frame-major costs nothing in the round trip (same bytes, regrouped) and
    # still gives unit quaternions, so neither of those checks catches the mistake -- but
    # it interpolates between DIFFERENT NODES, and in game that is a weapon that snaps
    # and a screen that shakes. The tell is smoothness: mean frame-to-frame step on the
    # idle is 0.05 degrees read this way against 6.18 read frame-major.
    return {
        'frames': F,
        'rotations': [[struct.unpack_from('<4f', b, at + (i * F + f) * 16)
                       for i in range(R)] for f in range(F)],
        'translations': [[struct.unpack_from('<3f', b, tbase + (j * F + f) * 12)
                          for j in range(T)] for f in range(F)],
        'scales': [[struct.unpack_from('<f', b, sbase + (k * F + f) * 4)[0]
                    for k in range(S)] for f in range(F)],
    }


def _slerp(a, b, u):
    """Shortest-arc interpolation between two unit quaternions.

    The endpoints are returned untouched. q and -q are the same rotation, so slerp is
    free to flip one of them to take the short way round -- but that would hand back a
    sign-flipped copy of a frame that was not interpolated at all, and an unchanged
    animation should come back unchanged.
    """
    import math
    if u <= 0.0:
        return tuple(a)
    if u >= 1.0:
        return tuple(b)
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:                       # take the short way round
        b = tuple(-y for y in b)
        dot = -dot
    if dot > 0.9995:                    # nearly parallel: straight line, renormalised
        out = tuple(x + (y - x) * u for x, y in zip(a, b))
    else:
        th = math.acos(max(-1.0, min(1.0, dot)))
        s = math.sin(th)
        wa, wb = math.sin((1 - u) * th) / s, math.sin(u * th) / s
        out = tuple(x * wa + y * wb for x, y in zip(a, b))
    n = math.sqrt(sum(c * c for c in out)) or 1.0
    return tuple(c / n for c in out)


def canonicalise(anim):
    """Put every node's rotation track in one hemisphere.

    q and -q are the SAME rotation. Interpolating across a flip goes wrong: slerp takes
    the short arc within each pair, but consecutive output frames come from DIFFERENT
    pairs, so they could land in opposite hemispheres and the engine would then take the
    long way round at playback.

    The Assault Rifle's shipped tracks turn out to have NO flips once they are read
    node-major, so this is a safeguard rather than a fix. It looked like a fix at first:
    reading the frames in the wrong order reported 150 flips in the reload, which is what
    interpolating between different nodes looks like from here. Flipping a track into one
    hemisphere costs nothing when there is nothing to flip.
    """
    out = [list(f) for f in anim['rotations']]
    nodes = len(out[0]) if out else 0
    for n in range(nodes):
        for f in range(1, len(out)):
            if sum(x * y for x, y in zip(out[f - 1][n], out[f][n])) < 0.0:
                out[f][n] = tuple(-c for c in out[f][n])
    return dict(anim, rotations=out)


def resample(anim, frames):
    """The same motion at a different frame count.

    Rotations are slerped and everything else interpolated linearly, both sampled at the
    same normalised position, so the animation keeps its shape and only its duration
    changes. This is the whole point of decoding the format: making a reload longer is
    arithmetic, with no codec to re-encode.

    The source is canonicalised first -- see `canonicalise`, without which the output
    shakes.
    """
    old = anim['frames']
    if frames < 1 or old < 1:
        raise ValueError('need at least one frame')
    if frames == old:
        return dict(anim, rotations=[list(f) for f in anim['rotations']],
                    translations=[list(f) for f in anim['translations']],
                    scales=[list(f) for f in anim['scales']])
    anim = canonicalise(anim)
    if old == 1:
        return dict(anim, frames=frames,
                    rotations=[list(anim['rotations'][0]) for _ in range(frames)],
                    translations=[list(anim['translations'][0]) for _ in range(frames)],
                    scales=[list(anim['scales'][0]) for _ in range(frames)])
    out = {'frames': frames, 'rotations': [], 'translations': [], 'scales': []}
    for f in range(frames):
        pos = f * (old - 1) / float(frames - 1) if frames > 1 else 0.0
        i = min(int(pos), old - 2)
        u = pos - i
        out['rotations'].append([_slerp(a, b, u) for a, b in
                                 zip(anim['rotations'][i], anim['rotations'][i + 1])])
        out['translations'].append([tuple(x + (y - x) * u for x, y in zip(a, b))
                                    for a, b in zip(anim['translations'][i],
                                                    anim['translations'][i + 1])])
        out['scales'].append([a + (b - a) * u for a, b in
                              zip(anim['scales'][i], anim['scales'][i + 1])])
    return out


def read_animation_frame_major(tag, e):
    """The WRONG reading, kept on purpose: every node for frame 0, then frame 1.

    It exists so the ordering can be tested rather than assumed -- `ordering_ok`
    compares the two and insists the node-major one describes smoother motion.
    """
    b = tag.data[e['at']:e['at'] + e['size']]
    F = e['frames']
    R, T, S = e['animated']
    at = e['frames_at']
    tbase = at + F * R * 16
    sbase = tbase + F * T * 12
    return {
        'frames': F,
        'rotations': [[struct.unpack_from('<4f', b, at + (f * R + i) * 16)
                       for i in range(R)] for f in range(F)],
        'translations': [[struct.unpack_from('<3f', b, tbase + (f * T + j) * 12)
                          for j in range(T)] for f in range(F)],
        'scales': [[struct.unpack_from('<f', b, sbase + (f * S + k) * 4)[0]
                    for k in range(S)] for f in range(F)],
    }


def ordering_ok(tag, e):
    """(ok, node_major_mean, frame_major_mean) -- is the frame order the right way round?

    Reading the frames the wrong way is byte-exact on a round trip and leaves every
    quaternion unit, so the obvious checks pass. This compares the two readings and
    requires the node-major one to describe smoother motion, which is the property that
    actually distinguishes them.

    Resampling does NOT distinguish them: interpolating to more frames lowers the mean
    step either way, so "did the resample get smoother" is not a test -- it was tried,
    and it passed the wrong reading.

    Judged with slack, because an animation that barely moves cannot tell the orderings
    apart: `first_person:overlays` is nine frames of near-identity rotations and reads
    1.04 node-major against 0.99 frame-major, which is noise. A real mistake is not
    close -- the reload reads 3.16 against 32.83, the idle 0.05 against 6.18.
    """
    a = smoothness(read_animation(tag, e))[1]
    b = smoothness(read_animation_frame_major(tag, e))[1]
    return a <= b * 1.5 + 0.25, a, b


def smoothness(anim):
    """(max, mean) angle in degrees between consecutive frames, over every node.

    The check that distinguishes a correct reading from a plausible one. A round trip
    stays byte-exact and every quaternion stays unit whether the frames are read
    node-major or frame-major, because both are the same bytes regrouped -- so neither
    catches reading them the wrong way. Motion does: the Assault Rifle's IDLE averages
    0.05 degrees a frame read correctly and 6.18 read frame-major, and a resample built
    on the wrong one shakes the screen in game.

    A resample to MORE frames must LOWER these numbers; if it raises them, the reading
    is wrong.
    """
    import math
    worst = total = 0.0
    count = 0
    for n in range(len(anim['rotations'][0]) if anim['frames'] else 0):
        for f in range(anim['frames'] - 1):
            dot = abs(sum(x * y for x, y in
                          zip(anim['rotations'][f][n], anim['rotations'][f + 1][n])))
            ang = 2.0 * math.degrees(math.acos(min(1.0, dot)))
            worst = max(worst, ang)
            total += ang
            count += 1
    return worst, total / max(count, 1)


def pack_animation(anim):
    """The bytes an animation's frame section should hold: channel-major, and NODE-major
    within each channel -- see `read_animation`."""
    F = anim['frames']
    out = bytearray()
    for i in range(len(anim['rotations'][0]) if F else 0):
        for f in range(F):
            out += struct.pack('<4f', *anim['rotations'][f][i])
    for j in range(len(anim['translations'][0]) if F else 0):
        for f in range(F):
            out += struct.pack('<3f', *anim['translations'][f][j])
    for k in range(len(anim['scales'][0]) if F else 0):
        for f in range(F):
            out += struct.pack('<f', anim['scales'][f][k])
    return bytes(out)


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
    ap.add_argument('--layout', action='store_true')
    ap.add_argument('--records', type=int, nargs='?', const=13, default=None,
                    help='hunt for the per-frame records of this animation')
    a = ap.parse_args()

    d = io.open(a.tag, 'rb').read()
    print('%s  %d bytes\n' % (os.path.basename(a.tag), len(d)))
    opts = (a.sizes or a.scan or a.blobs or a.header or a.layout
            or a.records is not None)
    if a.tree or not opts:
        tree(d)
    if not opts:
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
    if a.layout:
        sys.path.insert(0, HERE)
        import h3tag
        report_layout(h3tag.Tag(a.tag), mem)
    if a.records is not None:
        sys.path.insert(0, HERE)
        import h3tag
        records(h3tag.Tag(a.tag), mem, a.records)
    if a.scan:
        scan(d, mem, HEADER, min(len(d) - sum(e['size'] for e in mem), 0x8000))


if __name__ == '__main__':
    main()
