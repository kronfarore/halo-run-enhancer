r"""Make a Halo 2 animation LONGER, by resampling its frames.

`halo3_reload` can only shorten: it rewrites an animation's frame count and its event
frames and leaves the data alone, so there are no frames past the end to stretch into. That
is why the Halo 2 SAW reloads at the sniper rifle's 72 frames instead of its own 128. With
codec 3 decoded (`h2_anim.py`) the data can be rebuilt instead, at any length.

A codec-3 blob holds the animation TWICE, which is what the layout turned out to mean:

    [0, A)      32 bytes, then R nodes x frames x 8   packed i16 quaternion per frame
    [A, B)                     T nodes x frames x 12  float3 translation per frame
    [B, end)    32 bytes, then R nodes x frames x 16  FLOAT quaternion per frame
                               T nodes x frames x 12  float3 translation per frame

The first pair is what the engine plays; the second is the uncompressed source the kit kept
so it can recompress without a re-import (which is exactly what
`tool model-animation-reset-compression` does). Both are node-major -- all of one node's
frames, then the next node's -- and both are rewritten here, because leaving the source at
the old length would make the next recompression undo the work.

Every array is resampled with the ENDS PINNED: new frame t reads old position
t*(frames-1)/(new-1), so the first and last poses are exactly the ones the animator set and
only the middle is interpolated. Rotations are interpolated as quaternions with the sign of
the second aligned to the first -- without that, two quaternions that represent the same
rotation with opposite signs interpolate the long way round and the arm swings through the
body halfway between two frames.

**Event frames are NOT scaled yet.** The sound and effect keys live in child blocks of the
animation element, and matching each chunk to its animation in a loose tag has not been
done. It does not bite here -- every reload in the port's graph carries a single sound
event at frame 1, which is frame 1 at any length -- but a weapon whose reload rings a key
halfway through would need this first, so check before reusing.

**NOT EVERY LENGTH WORKS, AND THE RULE IS NOT KNOWN.** On the sniper rifle's graph,
`reload_full` 72 -> 128 and 72 -> 144 rebuild and pass `build-cache-file`; 72 -> 73 does not,
and neither does `ready` at 21, 32 or 40, `moving` at 16, 21, 24 or 40, or `overlays` at 20.
A "multiple of 16" rule fitted the first seven results and was then falsified by testing it
(32 and 16 both assert), which is why it is not in the code. The failures assert in
`uncompressed_static_data_codec.h` on `node < header->total_rotated_nodes`, the same place a
mis-placed 32-byte block does, so something else about the rebuilt data is still not right.

So **always `--check` before building**. It copies the graph to a scratch tag and runs
`tool model-animation-reset-compression`, which exercises the same codecs in seconds and
reproduces the assert -- rather than finding out three minutes into a map build.

    python h2_anim_retime.py <graph> <animation> <frames> [--write]
    python h2_anim_retime.py <graph> reloads <frames> [--check] [--write]
"""
import argparse
import math
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_anim

SUB = h2_anim.SUB_HEADER
PRE = 32                    # the preamble in front of each of the two halves


def _lerp(a, b, t):
    return a + (b - a) * t


def _qlerp(a, b, t):
    """Normalised lerp between two quaternions, with b's sign aligned to a's.

    Two quaternions q and -q are the same rotation, and the compressed data uses both.
    Interpolating between them without aligning the signs takes the long way round, which
    in game is a limb swinging through the body between two otherwise fine frames.
    """
    if sum(x * y for x, y in zip(a, b)) < 0.0:
        b = [-x for x in b]
    out = [_lerp(a[k], b[k], t) for k in range(4)]
    n = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / n for x in out]


def _resample(values, new_frames, blend):
    """`values` is a list of per-frame items for ONE node; hand back `new_frames` of them."""
    old = len(values)
    if old == new_frames:
        return list(values)
    if old == 1:
        return [values[0]] * new_frames
    out = []
    for t in range(new_frames):
        pos = t * (old - 1) / float(new_frames - 1) if new_frames > 1 else 0.0
        i = min(int(pos), old - 2)
        out.append(blend(values[i], values[i + 1], pos - i))
    return out


def _read_quats(data, at, count, packed):
    if packed:
        return [[v / 32767.0 for v in struct.unpack_from('<4h', data, at + i * 8)]
                for i in range(count)]
    return [list(struct.unpack_from('<4f', data, at + i * 16)) for i in range(count)]


def _write_quats(quats, packed):
    out = bytearray()
    for q in quats:
        if packed:
            out += struct.pack('<4h', *[max(-32767, min(32767, int(round(v * 32767.0))))
                                        for v in q])
        else:
            out += struct.pack('<4f', *q)
    return bytes(out)


def _read_vecs(data, at, count):
    return [list(struct.unpack_from('<3f', data, at + i * 12)) for i in range(count)]


def _write_vecs(vecs):
    out = bytearray()
    for v in vecs:
        out += struct.pack('<3f', *v)
    return bytes(out)


def _half(data, at, nodes_r, nodes_t, frames, new_frames, packed):
    """One of the blob's two halves, resampled: rotations then translations.

    The 32 bytes are in a DIFFERENT PLACE in each half, which cost a build to find out.

    * the COMPRESSED half runs [rotations][translations][32-byte trailer]. The data starts
      at offset 0. Two checks say so: reading the quaternions from 0 gives a higher
      proportion of unit-length ones than reading from 32, and -- the decisive one -- the
      two halves hold the same rotations, so comparing packed against float across every
      node and frame gives a mean error three times lower at offset 0 than at 32.
    * the UNCOMPRESSED half runs [32-byte header][rotations][translations], and that header
      is real: (codec 2, R, T, 0), its own A and B, and its own three strides.

    Getting this backwards puts the trailer at the front, shifts every quaternion by four
    frames, and `build-cache-file` stops with an assert in
    `uncompressed_static_data_codec.h` on `node < header->total_rotated_nodes`.
    """
    rot_size = 16 if not packed else 8
    span = nodes_r * frames * rot_size + nodes_t * frames * 12
    out = bytearray()
    if not packed:
        head = bytearray(data[at:at + PRE])
        a = PRE + nodes_r * new_frames * rot_size
        b = a + nodes_t * new_frames * 12
        struct.pack_into('<5I', head, 12, a, b, new_frames * rot_size, new_frames * 12,
                         new_frames * 4)
        out += head
        o = at + PRE
    else:
        o = at

    for n in range(nodes_r):
        quats = _read_quats(data, o + n * frames * rot_size, frames, packed)
        out += _write_quats(_resample(quats, new_frames, _qlerp), packed)
    t0 = o + nodes_r * frames * rot_size
    for n in range(nodes_t):
        vecs = _read_vecs(data, t0 + n * frames * 12, frames)
        out += _write_vecs(_resample(vecs, new_frames,
                                     lambda a_, b_, t: [_lerp(a_[k], b_[k], t)
                                                        for k in range(3)]))
    if packed:
        # the trailer, whatever it is, carried through untouched
        out += data[at + span:at + span + PRE]
    return bytes(out)


def blob_of(data, base, k, name):
    """Everything needed to rewrite one animation."""
    e = h2_anim.element(data, base, k)
    at = h2_anim.blob(data, name)
    h = h2_anim.header(data, at)
    s = h2_anim.sub(data, at, h['data'])
    m = h2_anim.sections(e, h, s)
    return e, at, h, s, m


def retime(data, name, new_frames):
    """`data` with that animation rebuilt at `new_frames`, everything else untouched."""
    chunk, count = h2_anim.animations_chunk(data)
    base = chunk + 16
    names = h2_anim.names(data, count)
    if name not in names:
        raise SystemExit('%s is not in this graph' % name)
    k = names.index(name)
    e, at, h, s, m = blob_of(data, base, k, name)
    if s['codec'] != 3:
        raise SystemExit('%s is codec %d; only 3 is decoded' % (name, s['codec']))
    if not m['ok']:
        raise SystemExit('%s does not match the decoded layout; refusing' % name)

    f, R, T = e['frames'], s['R'], s['T']
    data_at = at + h['data'] + SUB
    first = _half(data, data_at, R, T, f, new_frames, True)
    second = _half(data, at + h['data'] + SUB + s['B'], R, T, f, new_frames, False)

    a = PRE + R * new_frames * 8
    b = a + T * new_frames * 12
    tail = PRE + R * new_frames * 16 + T * new_frames * 12
    if len(first) != b or len(second) != tail:
        raise SystemExit('rebuilt sections are %d/%d, expected %d/%d'
                         % (len(first), len(second), b, tail))

    sub_at = at + h['data']
    head = bytearray(data[sub_at:sub_at + SUB])
    struct.pack_into('<5I', head, 16, a, b, new_frames * 8, new_frames * 12,
                     new_frames * 4)

    blob = data[at:sub_at] + bytes(head) + first + second
    size = len(blob)
    out = bytearray(data[:at] + blob + data[at + e['size']:])

    # the element: frame count, total size, tail size, and B
    el = base + k * h2_anim.ELEM
    struct.pack_into('<H', out, el + 0x14, new_frames)
    struct.pack_into('<I', out, el + 0x34, size)
    struct.pack_into('<I', out, el + 0x50, tail)
    struct.pack_into('<I', out, el + 0x54, b)
    return bytes(out), dict(name=name, frames=f, new=new_frames, R=R, T=T,
                            size=e['size'], new_size=size)


def check(data):
    """Put a rebuilt graph past tool.exe, which asserts on data it cannot recompress.

    `model-animation-reset-compression` runs the same codecs `build-cache-file` does, in
    seconds rather than minutes, and fails the same way -- so a rebuilt animation is tried
    here before anything is written or built.
    """
    rel = os.path.join('objects', 'characters', 'masterchief', 'fp', 'weapons', 'rifle',
                       'fp_retime_check', 'fp_retime_check')
    dst = os.path.join(h2_anim.H2EK, 'tags', rel + '.model_animation_graph')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        open(dst, 'wb').write(data)
        p = subprocess.run([os.path.join(h2_anim.H2EK, 'tool.exe'),
                            'model-animation-reset-compression', rel],
                           cwd=h2_anim.H2EK, capture_output=True, text=True)
        out = (p.stdout or '') + (p.stderr or '')
        ok = 'ASSERTION' not in out
        print('   tool.exe: %s' % ('accepts the rebuilt graph' if ok else
                                   'ASSERTS -- ' + ' '.join(out.split())[-90:]))
        return ok
    finally:
        shutil.rmtree(os.path.dirname(dst), ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('graph')
    ap.add_argument('animation', help='an animation name, or "reloads" for every '
                                      'animation whose name contains reload')
    ap.add_argument('frames', type=int)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true',
                    help='run the result past tool.exe before trusting it')
    a = ap.parse_args()

    data = open(a.graph, 'rb').read()
    names = ([n for n in h2_anim.names(data, h2_anim.animations_chunk(data)[1])
              if 'reload' in n] if a.animation == 'reloads' else [a.animation])
    for name in names:
        data, info = retime(data, name, a.frames)
        print('%-28s %d -> %d frames   %d -> %d bytes  (R=%d T=%d)'
              % (info['name'], info['frames'], info['new'], info['size'],
                 info['new_size'], info['R'], info['T']))
    if a.check and not check(data):
        raise SystemExit('tool.exe asserts on this result; NOT written')
    if a.write:
        open(a.graph, 'wb').write(data)
        print('written')
    else:
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main()
