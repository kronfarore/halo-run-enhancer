r"""Make Halo 3 / ODST animations LONGER in a built map (2026-10-06) -- the inverted Reload
Time / Weapon Swap Speed cards.

Raising only the Frame Count (halo3_reload.scale_reload) makes the engine read past the
stored frames, so the frames are rebuilt at the new length here:

  * the codec data is decoded, resampled (rotations slerped, the rest lerped) and
    re-encoded IN ITS OWN CODEC -- 3 (8-byte int16 quaternions; ~92% of first-person
    animations) and 8 (stored raw, float quaternions). Keyframe codecs (4, 6) are left
    alone and reported;
  * the resource's page is re-laid: member blobs back to back, each padded to 16 bytes,
    every member's page-pointer fixup (0x4000_0000 | offset) moved with it, its member
    record's compressed / blob sizes and frame count rewritten;
  * the grown page goes back into its slot when it fits, else to the END OF THE FILE
    (header file size +0x8 grows; the map checksum runs to EOF anyway).

Codec header (32 bytes; R/T/S animated rotation/translation/scale tracks, F frames, q =
bytes per rotation: 8 for codec 3, 16 for codec 8):
    +0 codec | R<<8 | T<<16    +4, +8 codec-specific (kept)
    +12 32 + q*R*F (translations start)    +16 total size
    +20 q*F    +24 12*F    +28 4*F         (one track's bytes per channel)
then R tracks of F rotations, T tracks of F translations, S tracks of F scales --
NODE-MAJOR (memory h3-animation-format: reading it frame-major interpolates between bones).

    python h3_anim_lengthen.py --map <map> --check     (decode/encode round trip, every codec 3/8)
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

ROT_BYTES = {3: 8, 8: 16}
HDR = 32
PAGE_ALIGN = 16


# ----------------------------------------------------------------------------- codec
def decode(buf, frames, total=None):
    """codec data -> dict(codec, R, T, S, F, keep, rot, tr, sc) or None for a codec not
    handled here. rot[track][frame] = (x, y, z, w) floats."""
    codec = buf[0]
    q = ROT_BYTES.get(codec)
    if q is None:
        return None
    w0, = struct.unpack_from('<I', buf, 0)
    R, T = (w0 >> 8) & 0xFF, (w0 >> 16) & 0xFF
    F = frames
    tot = struct.unpack_from('<I', buf, 16)[0]
    S = (tot - HDR - F * (q * R + 12 * T)) // (4 * F) if F else 0
    if (struct.unpack_from('<I', buf, 12)[0] != HDR + q * R * F or S < 0
            or tot != HDR + F * (q * R + 12 * T + 4 * S) or (total is not None and tot > total)):
        return None
    at = HDR
    rot = []
    for _r in range(R):
        tr = []
        for _f in range(F):
            if q == 8:
                v = [c / 32767.0 for c in struct.unpack_from('<4h', buf, at)]
            else:
                v = list(struct.unpack_from('<4f', buf, at))
            tr.append(v)
            at += q
        rot.append(tr)
    trs = []
    for _t in range(T):
        trs.append([list(struct.unpack_from('<3f', buf, at + 12 * f)) for f in range(F)])
        at += 12 * F
    scs = []
    for _s in range(S):
        scs.append([struct.unpack_from('<f', buf, at + 4 * f)[0] for f in range(F)])
        at += 4 * F
    return dict(codec=codec, b3=buf[3], R=R, T=T, S=S, F=F, keep=bytes(buf[4:12]),
                rot=rot, tr=trs, sc=scs, raw_rot=None)


def encode(a):
    q = ROT_BYTES[a['codec']]
    R, T, S, F = a['R'], a['T'], a['S'], a['F']
    total = HDR + F * (q * R + 12 * T + 4 * S)
    out = bytearray(total)
    struct.pack_into('<I', out, 0, a['codec'] | R << 8 | T << 16 | a['b3'] << 24)
    out[4:12] = a['keep']
    struct.pack_into('<5I', out, 12, HDR + q * R * F, total, q * F, 12 * F, 4 * F)
    at = HDR
    for tr in a['rot']:
        for v in tr:
            if q == 8:
                struct.pack_into('<4h', out, at, *(max(-32767, min(32767, int(round(c * 32767.0))))
                                                   for c in v))
            else:
                struct.pack_into('<4f', out, at, *v)
            at += q
    for tr in a['tr']:
        for v in tr:
            struct.pack_into('<3f', out, at, *v)
            at += 12
    for tr in a['sc']:
        for v in tr:
            struct.pack_into('<f', out, at, v)
            at += 4
    return bytes(out)


# Keyframe codecs 4 and 6 (byte keyframes; 6 lists its tracks in reverse order): the
# header is 48 bytes, +12..+40 the starts of [translation descriptors, scale descriptors,
# rotation key frames, translation key frames, scale key frames, rotation data (8-byte
# aligned), translation data, scale data]. Rotation descriptors start at +48, one u32 per
# track: key count (low 12 bits) | first key << 12. A key frame is ONE BYTE (its frame
# number); a key's value is 8 bytes (int16 quaternion), 12 (translation) or 4 (scale).
# Lengthening only renumbers the key frames: same keys, same size, same values.
KEYFRAME_CODECS = (4, 6)
KEYFRAME_MAX = 256                       # frame numbers are bytes: 0..255


def keyframes(buf):
    """(rot, trans, scale) key-frame (offset, count) of a byte-keyframe codec, or None
    when the layout does not add up exactly."""
    if buf[0] not in KEYFRAME_CODECS or len(buf) < 48:
        return None
    w0, = struct.unpack_from('<I', buf, 0)
    R, T = (w0 >> 8) & 0xFF, (w0 >> 16) & 0xFF
    o = struct.unpack_from('<8I', buf, 12)
    S = (o[2] - o[1]) // 4
    if o[0] != 48 + 4 * R or o[1] != o[0] + 4 * T or S < 0:
        return None

    def keys(at, n):
        return sum(struct.unpack_from('<I', buf, at + 4 * i)[0] & 0xFFF for i in range(n))
    kr, kt, ks = keys(48, R), keys(o[0], T), keys(o[1], S)
    if (o[3] != o[2] + kr or o[4] != o[3] + kt or o[5] < o[4] + ks or o[5] % 8
            or o[6] != o[5] + 8 * kr or o[7] != o[6] + 12 * kt or len(buf) != o[7] + 4 * ks):
        return None
    return (o[2], kr), (o[3], kt), (o[4], ks)


def retime_keyframes(buf, fc, nf):
    """`buf` with every key frame renumbered for `nf` frames (first and last kept on the
    ends). None if the layout is not recognised."""
    parts = keyframes(buf)
    if parts is None:
        return None
    out = bytearray(buf)
    k = (nf - 1) / float(max(1, fc - 1))
    for at, n in parts:
        for i in range(n):
            out[at + i] = max(0, min(nf - 1, int(round(buf[at + i] * k))))
    return bytes(out)


def _slerp(a, b, u):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = [-x for x in b], -d
    if d > 0.9995:
        r = [x + (y - x) * u for x, y in zip(a, b)]
    else:
        th = math.acos(max(-1.0, min(1.0, d)))
        s = math.sin(th)
        ka, kb = math.sin((1 - u) * th) / s, math.sin(u * th) / s
        r = [ka * x + kb * y for x, y in zip(a, b)]
    n = math.sqrt(sum(x * x for x in r)) or 1.0
    return [x / n for x in r]


def _lerp(a, b, u):
    if isinstance(a, list):
        return [x + (y - x) * u for x, y in zip(a, b)]
    return a + (b - a) * u


def _resample_track(tr, n, fn):
    F = len(tr)
    if F == n:
        return list(tr)
    if F == 1:
        return [tr[0]] * n
    out = []
    for i in range(n):
        t = 0.0 if n == 1 else i * (F - 1) / float(n - 1)
        k = min(F - 2, int(t))
        out.append(fn(tr[k], tr[k + 1], t - k))
    return out


def _resample_floats(buf, per, fc, n, k=1.0):
    """Per-frame records of `per` bytes of float32, linearly resampled to `n` frames and
    multiplied by `k`."""
    w = per // 4
    tr = [list(struct.unpack_from('<%df' % w, buf, j * per)) for j in range(fc)]
    out = _resample_track(tr, n, _lerp)
    return b''.join(struct.pack('<%df' % w, *(v * k for v in r)) for r in out)


def resample(a, n):
    """The same motion over `n` frames; the first and last frames are kept exactly."""
    b = dict(a)
    b['F'] = n
    b['rot'] = [_resample_track(t, n, _slerp) for t in a['rot']]
    b['tr'] = [_resample_track(t, n, _lerp) for t in a['tr']]
    b['sc'] = [_resample_track(t, n, _lerp) for t in a['sc']]
    return b


def motion(a):
    """Mean rotation change per frame, degrees (the node-major ordering check)."""
    tot, n = 0.0, 0
    for tr in a['rot']:
        for x, y in zip(tr, tr[1:]):
            d = abs(sum(p * q for p, q in zip(x, y)))
            nx = math.sqrt(sum(p * p for p in x)) * math.sqrt(sum(p * p for p in y)) or 1.0
            tot += math.degrees(2 * math.acos(max(-1.0, min(1.0, d / nx))))
            n += 1
    return tot / n if n else 0.0


# ----------------------------------------------------------------------------- page
class Resource:
    """One animation resource (a jmad Tag Resource Group) of a built Halo 3 / ODST /
    Reach / Halo 4 map: its member records, fixups and the page holding its blobs.

    A member blob is its data sections back to back, in the order of the record's size
    list -- [default][compressed][static flags][animated flags][movement][pill]... The
    member record per game (sizes listed in BLOB order):
      Halo 3 / ODST 0x30: frame count i16 +0x8; sizes u8 sf +0xC, u8 af +0xD, i16 mv
                          +0xE, i16 pill +0x10, i16 default +0x12, i32 uncompressed
                          +0x14, i32 compressed +0x18; blob size +0x1C; pointer +0x28
      Reach         0x64: frame count i16 +0x8; 17 u32 sizes +0xC; blob +0x50; ptr +0x5C
      Halo 4        0x68: frame count u16 +0x8; 18 u32 sizes +0xC; blob +0x54; ptr +0x60
    Extra sections measured on the first-person graphs (m10 / m10_crash, 2026-10-06):
    #5 is 12 bytes a frame (three floats: a smooth position in Halo 4's Forerunner sniper,
    zeros in Reach) -- interpolated with the frames; #4 is root motion (8/12/16 bytes a
    frame) -- interpolated and scaled so the total distance stays; Halo 4's #17 (78-138
    bytes, codec byte 0x0B, then node indices up to 237, no frame numbers) is kept as it
    is. Any other non-empty section refuses the member."""

    KINDS = {
        'h3': dict(rec=0x30, fc='<h', blob=0x1C, ptr=0x28, n=None, per_frame={}, keep=()),
        'reach': dict(rec=0x64, fc='<h', blob=0x50, ptr=0x5C, n=17, per_frame={5: 12}, keep=()),
        'h4': dict(rec=0x68, fc='<H', blob=0x54, ptr=0x60, n=18, per_frame={5: 12}, keep=(17,)),
    }

    def __init__(self, m, pages, res):
        import halo_patch as HP
        import h3_raw_residency as R
        self.m, self.pages, self.res = m, pages, res
        self.kind = 'h4' if pages.h4 else 'reach' if pages.reach else 'h3'
        K = self.K = self.KINDS[self.kind]
        if self.kind == 'h4':
            e = self.entry = pages.rbase + res * 0x44
            self.seg = struct.unpack_from('<h', m.data, e + 0x1A)[0]
            lb = HP._block_base(m, e + 0x38)
            ok = self.seg >= 0 and m.i32(e + 0x38) > 0 and lb
            self.ctl = pages.cbase + m.i32(lb) if ok else None
            self.clen = m.i32(e + 0x14) if ok else 0
            self.seg_off = (struct.unpack_from('<i', m.data, pages.tabs['seg'][0] + self.seg * 0x18)[0]
                            if self.seg >= 0 else -1)
            fixat = e + 0x20
        else:
            e = self.entry = pages.rbase + res * 0x40
            self.ctl = pages.cbase + m.i32(e + 0x14)
            self.clen = m.i32(e + 0x18)
            self.seg = struct.unpack_from('<h', m.data, e + 0x22)[0]
            sb = pages.tabs['seg'][0] + self.seg * R.PLAY_SEG_ELEM
            self.seg_off = struct.unpack_from('<i', m.data, sb + 4)[0]
            fixat = e + 0x28
        self.fb = HP._block_base(m, fixat)
        self.nfix = max(0, m.i32(fixat))
        self.pi = pages.page_index(self.seg) if self.seg >= 0 else -1
        self.members = []
        if self.ctl is None:
            return
        fix = {m.u32(self.fb + k * 8): k for k in range(self.nfix)}
        for k in range(self.clen // K['rec']):
            fk = fix.get(k * K['rec'] + K['ptr'])
            if fk is None:
                break
            mo = self.ctl + k * K['rec']
            val = m.u32(self.fb + fk * 8 + 4)
            self.members.append(dict(rec=mo, fix=fk, start=val & 0x0FFFFFFF, ok=val >> 28 == 4,
                                     size=m.i32(mo + K['blob'])))

    def usable(self):
        return (self.seg_off == 0 and self.pi >= 0 and self.pages.local(self.pi)
                and bool(self.members) and all(x['ok'] for x in self.members))

    def blob(self, k):
        pg = self.pages.get(self.pi)
        x = self.members[k]
        return bytearray(pg[x['start']:x['start'] + x['size']])

    def frames(self, k):
        return struct.unpack_from(self.K['fc'], self.m.data, self.members[k]['rec'] + 8)[0]

    def section_sizes(self, k):
        """The member's data sections in BLOB order: [default, compressed, ...]."""
        mo = self.members[k]['rec']
        if self.kind == 'h3':
            sf, af, mv, pill, dflt, unc, cmp = struct.unpack_from('<BBhhhii', self.m.data, mo + 0xC)
            return [dflt, cmp, sf, af, mv, pill] + ([unc] if unc else [])
        return list(struct.unpack_from('<%dI' % self.K['n'], self.m.data, mo + 0xC))

    def sizes(self, k):
        """default / cmp (the compressed codec data) -- what the codec checks read."""
        s = self.section_sizes(k)
        return dict(dflt=s[0], cmp=s[1])

    def _set_sizes(self, k, cmp, fc, blob_len, extra):
        m, mo = self.m, self.members[k]['rec']
        struct.pack_into(self.K['fc'], m.data, mo + 8, fc)
        if self.kind == 'h3':
            struct.pack_into('<i', m.data, mo + 0x18, cmp)
            for i, v in extra.items():                  # i16 movement +0xE, pill +0x10
                struct.pack_into('<h', m.data, mo + {4: 0xE, 5: 0x10}[i], v)
        else:
            struct.pack_into('<I', m.data, mo + 0xC + 4, cmp)
            for i, v in extra.items():
                struct.pack_into('<I', m.data, mo + 0xC + 4 * i, v)
        struct.pack_into('<i', m.data, mo + self.K['blob'], blob_len)

    def lengthen(self, k, new_fc):
        """Rebuild member k at `new_fc` frames. Returns (old fc, new fc) or a reason str."""
        x = self.members[k]
        fc = self.frames(k)
        if new_fc == fc:
            return fc, fc
        secs = self.section_sizes(k)
        for i, v in enumerate(secs):
            if i < 4 or not v or i in self.K['keep']:
                continue
            if i in self.K['per_frame'] and v == self.K['per_frame'][i] * fc:
                continue
            if i == 4 and v % fc == 0 and v // fc in (8, 12, 16):
                continue                                  # root motion
            return 'carries data section #%d' % i
        blob = self.blob(k)
        parts, at = [], 0
        for v in secs:
            parts.append(bytes(blob[at:at + v]))
            at += v
        comp = parts[1]
        extra = {}
        if comp and comp[0] in KEYFRAME_CODECS:
            new_fc = min(new_fc, KEYFRAME_MAX)
            new = retime_keyframes(comp, fc, new_fc)
            if new is None:
                return 'keyframe codec %d layout not recognised' % comp[0]
        else:
            a = decode(comp, fc, len(comp))
            if a is None:
                return 'codec %d is not handled' % (comp[0] if comp else -1)
            if len(encode(a)) != len(comp):
                # 25 of 3152 on 010 (lip-sync, cutscenes, the Needler's ammo display)
                # carry bytes past the tracks whose meaning is unknown: never guess
                return 'codec data carries %d unknown trailing bytes' % (len(comp) - len(encode(a)))
            new = encode(resample(a, new_fc))
        parts[1] = new
        frame_secs = dict(self.K['per_frame'])
        if len(parts) > 4 and parts[4]:
            frame_secs[4] = len(parts[4]) // fc
        for i, per in frame_secs.items():
            if i < len(parts) and parts[i]:
                # root motion is movement PER FRAME: more frames each move less
                parts[i] = _resample_floats(parts[i], per, fc, new_fc,
                                            fc / float(new_fc) if i == 4 else 1.0)
                extra[i] = len(parts[i])
        x['data'] = b''.join(parts)
        self._set_sizes(k, len(new), new_fc, len(x['data']), extra)
        return fc, new_fc

    def relayout(self):
        """Write every member back, 16-byte aligned, in their original order, and repoint
        the fixups. The page is marked dirty (Pages.write_back recompresses it)."""
        pg = self.pages.get(self.pi)
        out = bytearray()
        for x in sorted(self.members, key=lambda x: x['start']):
            data = x.get('data') or bytes(pg[x['start']:x['start'] + x['size']])
            if len(out) % PAGE_ALIGN:
                out += bytes(PAGE_ALIGN - len(out) % PAGE_ALIGN)
            x['start'] = len(out)
            x['size'] = len(data)
            struct.pack_into('<I', self.m.data, self.fb + x['fix'] * 8 + 4, 0x40000000 | len(out))
            out += data
        self.pages.cache[self.pi] = out
        self.pages.dirty.add(self.pi)
        struct.pack_into('<I', self.m.data, self.pages.entry(self.pi) + 0x10, len(out))


def _slot(pages, pi, off):
    """Bytes free from `off` up to the next page that lives in this file, or to EOF --
    read off the CURRENT page table, so pages moved earlier in the same pass count.
    Records with offset 0xFFFFFFFF are not pages (2026-10-06: counting one gave the last
    page a 3.5 GB slot, and its rewrite ran over the page moved in behind it)."""
    m = pages.m
    pb, pc = pages.tabs['page']
    nxt = len(m.data)
    for i in range(pc):
        if i == pi or not pages.local(i):
            continue
        o, c = struct.unpack_from('<II', m.data, pages.entry(i) + 8)
        if off < o < nxt and o != 0xFFFFFFFF and c:
            nxt = o
    return nxt - off


def write_back(pages):
    """Recompress every edited page: into its own slot when it fits, else at the END OF
    THE FILE (4 KB aligned, like the slots; header file size +0x8 grows). Checksums
    refreshed either way."""
    import hashlib
    import zlib
    m = pages.m
    out = []
    for pi in sorted(pages.dirty):
        e = pages.entry(pi)
        off, comp = struct.unpack_from('<II', m.data, e + 8)
        data = bytes(pages.cache[pi])
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        new = c.compress(data) + c.flush()
        if len(new) <= _slot(pages, pi, off):
            at = off
            m.data[off:off + len(new)] = new
            if len(new) < comp:
                m.data[off + len(new):off + comp] = bytes(comp - len(new))
            out.append(('in place', pi, comp, len(new), at))
        else:
            end = len(m.data)
            pad = (-end) % 0x1000
            at = end + pad
            m.data.extend(bytes(pad) + new + bytes((-len(new)) % 0x1000))
            struct.pack_into('<I', m.data, 0x8, len(m.data))
            m.data[off:off + comp] = bytes(comp)        # the old slot is free now
            out.append((pi, comp, len(new), at))
        struct.pack_into('<II', m.data, e + 8, at, len(new))
        struct.pack_into('<I', m.data, e + 0x10, len(data))
        struct.pack_into('<I', m.data, e + 0x14, (zlib.crc32(data) ^ 0xFFFFFFFF) & 0xFFFFFFFF)
        m.data[e + 0x18:e + 0x2C] = hashlib.sha1(data).digest()
        m.data[e + 0x2C:e + 0x40] = hashlib.sha1(data[:0x400]).digest()
        m.data[e + 0x40:e + 0x54] = hashlib.sha1(data[-0x400:]).digest()
    pages.dirty.clear()
    return out


# ----------------------------------------------------------------------------- check
def main():
    import halo_patch as HP
    import h3_move_speed as ms
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--game', default='Halo 3')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    m = HP.open_map(a.map, a.game)
    pages = ms.Pages(m)
    n = ok = 0
    worst = 0.0
    seen = set()
    for _name, base in m.find_tags('jmad', '*'):
        for g in m.follow_all(base, [0xF8], [0xC], 'all'):
            res = m.u32(g + 4) & 0xFFFF
            if res in seen:
                continue
            seen.add(res)
            r = Resource(m, pages, res)
            if not r.usable():
                continue
            for k, x in enumerate(r.members):
                s = r.sizes(k)
                fc = struct.unpack_from('<h', m.data, x['rec'] + 8)[0]
                comp = r.blob(k)[s['dflt']:s['dflt'] + s['cmp']]
                if not comp or comp[0] not in ROT_BYTES:
                    continue
                n += 1
                d = decode(comp, fc, s['cmp'])
                if d is None:
                    print('no decode', _name, k, comp[0])
                    continue
                if encode(d) == bytes(comp[:len(encode(d))]) and len(encode(d)) == s['cmp']:
                    ok += 1
                worst = max(worst, motion(d))
    print('codec 3/8 animations: %d, byte-exact round trip: %d, largest mean motion %.2f deg/frame'
          % (n, ok, worst))


if __name__ == '__main__':
    main()
