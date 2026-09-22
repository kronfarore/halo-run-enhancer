r"""Retime an animation inside a Halo 3 Editing Kit graph, by rebuilding its frames.

This is step 9's write half. `h3_anim_decode` proved the frames are plain float32 and
channel-major; this resamples them to a new frame count and puts them back, together
with every number that has to agree with them:

  * the frame data itself, in the member's `tgda` chunk (the chunk grows, so its length
    and every ancestor's are corrected -- h3tag.replace_payload)
  * the resource member element: frame count and uncompressed_data size
  * the Animations block element: Frame Count
  * the frame and sound EVENT frames, scaled by the same ratio, so the reload's sound
    and its "allow interruption" point stay where they belong in the motion

WHERE THE FIELDS ARE, all read off the Assault Rifle's first-person graph and checked
against `tool export-tag-to-xml`:
  * resource member elements: 48 bytes each, frame count at +0, node count +2,
    static/animated flag sizes +4/+5, default_data +10, uncompressed +12, compressed +16.
    The array starts right after a 16-byte header at the members block's payload.
  * Animations block elements: 0x88 bytes each, Frame Count at +0x10, event counts at
    +0x2C (frame), +0x38 (sound), +0x44 (effect), +0x50 (dialogue) -- the same offsets
    the map plugin uses, which is worth knowing: the tag and the cache agree here.
  * event data lives after the animations array. A block is located by matching the
    EXACT frame sequence the XML reports, searching forward so the two reloads (both
    firing at 34 and 52) resolve to their own copies. A heuristic "run of plausible
    frame numbers" does NOT work: that region is full of zero padding which satisfies
    every structural test, and it cheerfully returned runs of zeros as the events.

FINISH THE JOB WITH THE OFFICIAL TOOL. This rewrites the UNCOMPRESSED frames; the member
still carries a compressed stream built for the old frame count, and `current compression`
is not "none", so the engine may well prefer it. `tool model-animation-reset-compression
<graph>` regenerates the compressed stream FROM the uncompressed data -- verified: after
retiming the reload to 128 frames it rebuilt compressed_data from 15808 to 12752 and left
the frame count and the moved events alone. So the pipeline is: retime here, recompress
there.

Proven on the Assault Rifle's first-person graph, reload_empty 58 -> 128 frames:
uncompressed_data 27408 -> 60448 (= 32 + 128*472), events 34 -> 76 and 52 -> 116, the
tag still spans its file, `tool export-tag-to-xml` reads back 128 frames, and after
recompression all seventeen animations still decode to unit quaternions with an exact
round trip.

    python h3_anim_retime.py --xml <export.xml> --show
    python h3_anim_retime.py --xml <export.xml> --anim 13 --frames 128 --out <tag>
"""
import argparse, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402
import h3_anim_decode as dec                                   # noqa: E402

MEMBER_ES = 48
ANIM_ES = 0x88
ANIM_FRAMES = 0x10
EVENT_BLOCKS = ((0x2C, 4), (0x38, 8))      # (count offset, element size)


def members_block(tag, mem):
    """(first element offset, element size) for the resource member array."""
    got = dec.blobs(tag, mem)
    first = min(g['chunk'] for g in got)
    parent = max((n for n in tag.nodes()
                  if n.marker == 'tgbl' and n.payload_at < first
                  and n.payload_at + n.length > first), key=lambda n: n.payload_at)
    return parent.payload_at + 16, MEMBER_ES


def animations_block(tag, mem):
    """Offset of animation element 0, found by matching every frame count in order."""
    want = [e['frames'] for e in mem]
    d = tag.data
    for start in range(0x40, len(d) - len(want) * ANIM_ES):
        if all(struct.unpack_from('<h', d, start + i * ANIM_ES)[0] == f
               for i, f in enumerate(want)):
            return start - ANIM_FRAMES
    raise SystemExit('could not find the animations block')


def events_from_xml(path):
    """{animation index: {'frame': [...], 'sound': [...]}} -- the frames each event is on.

    Read from `tool export-tag-to-xml` rather than guessed at. A heuristic search for
    "a run of plausible frame numbers" does not work out here: the region is full of
    zero padding that satisfies every structural test, and it happily returned runs of
    zeros as the reload's events.
    """
    s = open(path, encoding='utf-8', errors='replace').read()
    heads = [(m.start(), int(m.group(1)), m.group(2))
             for m in re.finditer(r'<element index="(\d+)" name="(first_person:[^"]*)">', s)]
    out = {}
    for k, (pos, idx, _name) in enumerate(heads):
        seg = s[pos:heads[k + 1][0] if k + 1 < len(heads) else len(s)]
        got = {}
        for key, block in (('frame', 'frame events'), ('sound', 'sound events')):
            m = re.search(r'<block name="%s" value="[^"]*,(\d+)">(.*?)</block>' % block,
                          seg, re.S)
            if m and int(m.group(1)):
                got[key] = [int(x) for x in
                            re.findall(r'name="frame" value="(-?\d+)"', m.group(2))]
        if got:
            out[idx] = got
    return out


def event_blocks(tag, mem, anim_start, xml):
    """{animation index: [(offset, frames, element size), ...]}.

    Located by matching the EXACT frame sequence the XML reports, searching forward so
    the blocks stay in animation order -- two animations with identical events (the two
    reloads both fire at 34 and 52) then resolve to their own copies rather than both
    to the first.
    """
    d = tag.data
    want = events_from_xml(xml)
    out, at = {}, anim_start + len(mem) * ANIM_ES
    for i in sorted(want):
        for key, esz in (('frame', 4), ('sound', 8)):
            frames = want[i].get(key)
            if not frames:
                continue
            found = None
            for o in range(at, len(d) - len(frames) * esz):
                if all(struct.unpack_from('<h', d, o + k * esz + 2)[0] == f
                       for k, f in enumerate(frames)):
                    found = o
                    break
            if found is None:
                continue
            out.setdefault(i, []).append((found, frames, esz))
            at = found + len(frames) * esz
    return out


def retime(tag, mem, index, frames, xml):
    """Rebuild one animation at `frames` frames. Returns a report."""
    lay = {e['index']: e for e in dec.layout(tag, mem)}
    e = lay[index]
    old = e['frames']
    anim = dec.read_animation(tag, e)
    done = dec.resample(anim, frames)
    packed = dec.pack_animation(done)
    # Test the frame ORDER rather than assume it. Reading it the wrong way round is
    # byte-exact on a round trip and leaves every quaternion unit, so nothing else here
    # notices -- and in game it shakes the screen.
    order, node_major, frame_major = dec.ordering_ok(tag, e)
    if not order:
        raise SystemExit('anim %d reads SMOOTHER frame-major (%.2f) than node-major '
                         '(%.2f deg/frame) -- the frame order is wrong'
                         % (index, frame_major, node_major))
    smooth_before, smooth_after = dec.smoothness(anim), dec.smoothness(done)

    # Rebuild BOTH copies of the frames. The member carries a compressed stream as well
    # as the uncompressed one, and the engine reads the compressed one -- so rewriting
    # only the uncompressed frames leaves the old motion playing, which is what happened
    # the first two times. `tool model-animation-reset-compression` was meant to close
    # that and did not: it changed the codec from "best accuracy" to "best score" and
    # the animation still played wrong.
    #
    # Codec 8 is the way out: the Assault Rifle's own pitch_and_turn uses it, and there
    # the compressed section is the uncompressed one byte for byte apart from two header
    # fields -- the codec byte, and a float that reads 1.0 instead of 0.0. So the frames
    # can be stored RAW in the compressed slot, losslessly, with no encoder at all.
    blob = bytes(tag.data[e['at']:e['at'] + e['size']])
    # THE SECTION HEADER IS FRAME-DEPENDENT AND MUST BE REBUILT, not copied. It carries
    # the size of ONE node's track for each channel, and where the translations begin:
    #
    #   +0   codec | R<<8 | T<<16        +12  32 + 16*R*F   (translations start here)
    #   +4   0                           +16  total size
    #   +8   0.0 (1.0 when stored raw)   +20  16*F   +24  12*F   +28  4*F
    #
    # Derived exactly from (frames, R, T, S) for all seventeen of the donor's
    # animations, so this is the format rather than a guess. Copying it verbatim is
    # what broke the retimed reload in game: 128 frames of data read with 58-frame
    # strides puts every node's track at the wrong offset.
    R, T, S = e['animated']
    trans_at = 32 + 16 * R * frames
    total = trans_at + 12 * T * frames + 4 * S * frames
    old_head = struct.unpack_from('<8I', blob, e['frames_at'] - 32)
    unc_header = bytearray(struct.pack('<8I', old_head[0], 0, 0, trans_at, total,
                                       16 * frames, 12 * frames, 4 * frames))
    raw_header = bytearray(unc_header)
    raw_header[0] = 8                                   # codec: stored raw
    struct.pack_into('<f', raw_header, 8, 1.0)

    default = blob[:e['default_data']]
    flags_at = e['default_data'] + e['compressed_data']
    flags = blob[flags_at:flags_at + 48]
    new_blob = (default + bytes(raw_header) + packed + flags
                + bytes(unc_header) + packed)
    new_unc = 32 + len(packed)

    # the member's own data chunk is the `tgda` inside its `tgst`
    chunk = next(n for n in tag.nodes() if n.off == e['chunk'])
    tgda = next(n for n in chunk.children if n.marker == 'tgda')
    delta = tag.replace_payload(tgda, new_blob)

    mbase, mes = members_block(tag, mem)
    mo = mbase + index * mes
    struct.pack_into('<h', tag.data, mo, frames)
    struct.pack_into('<I', tag.data, mo + 12, new_unc)
    struct.pack_into('<I', tag.data, mo + 16, new_unc)   # compressed == uncompressed now

    astart = animations_block(tag, mem)
    ao = astart + index * ANIM_ES
    struct.pack_into('<h', tag.data, ao + ANIM_FRAMES, frames)

    scaled = []
    for off, frames_list, esz in event_blocks(tag, mem, astart, xml).get(index, ()):
        for k in range(len(frames_list)):
            at = off + k * esz + 2
            was = struct.unpack_from('<h', tag.data, at)[0]
            now = int(round(was * (frames - 1) / float(old - 1))) if old > 1 else was
            now = max(0, min(frames - 1, now))
            struct.pack_into('<h', tag.data, at, now)
            scaled.append((was, now))
    return {'index': index, 'old': old, 'new': frames, 'bytes': delta,
            'uncompressed': new_unc, 'events': scaled,
            'smooth': (smooth_before, smooth_after)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default=dec.AR_FP)
    ap.add_argument('--xml', required=True)
    ap.add_argument('--anim', type=int)
    ap.add_argument('--frames', type=int)
    ap.add_argument('--out')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()

    mem = dec.members_from_xml(a.xml)
    tag = h3tag.Tag(a.tag)
    ok, cov, tot = tag.check()
    print('%s parses: %s (%d/%d)' % (os.path.basename(a.tag), ok, cov, tot))

    astart = animations_block(tag, mem)
    print('animations block at %#x, members at %#x' % (astart, members_block(tag, mem)[0]))
    if a.show:
        ev = event_blocks(tag, mem, astart, a.xml)
        for i in sorted(ev):
            for off, fr, esz in ev[i]:
                print('   anim %-3d (%d frames) %d event(s) @%#x at frames %s'
                      % (i, mem[i]['frames'], len(fr), off, fr))
        return

    if a.anim is None or a.frames is None:
        raise SystemExit('need --anim and --frames (or --show)')
    rep = retime(tag, mem, a.anim, a.frames, a.xml)
    print('anim %d: %d -> %d frames, data %+d bytes, uncompressed_data %d'
          % (rep['index'], rep['old'], rep['new'], rep['bytes'], rep['uncompressed']))
    (mw, mm), (rw, rm) = rep['smooth']
    print('   frame-to-frame motion: max %.1f -> %.1f deg, mean %.2f -> %.2f deg'
          % (mw, rw, mm, rm))
    for was, now in rep['events']:
        print('   event frame %d -> %d' % (was, now))
    ok, cov, tot = tag.check()
    print('tag still parses: %s (%d/%d)' % (ok, cov, tot))
    if not ok:
        raise SystemExit('tree no longer spans the file -- not saved')
    if a.out:
        tag.save(a.out)
        print('wrote %s' % a.out)
    else:
        print('(no --out, nothing written)')


if __name__ == '__main__':
    main()
