r"""Halo 1 (MCC) sound banks: read and EXTEND `halo1\sound\pc\sounds_adpcm.fsb` and its index
`lst\sounds_adpcm.lst.bin` -- how a ported weapon's own sounds reach the game.

WHY (2026-10-04): MCC's Halo 1 does NOT play the sound data compiled into a map. It plays
FMOD banks, found by the sound TAG'S PATH through the .lst.bin indexes: classic view the
Xbox IMA ADPCM bank sounds_adpcm (3106 sounds, the classic tags' own audio sample for
sample, listed as `sound\old_sfx\...` for the maps' `sound\sfx\...`), the Anniversary view
sounds_debug (CELT). A port's new sound tag is in neither, so it is silent whatever the map
carries -- the first SAW build fired only the casing click of its effect.

FORMATS (measured):
  .lst.bin   u32 version 1, u32 count, then per entry: u32 length, the tag path (NUL
             included), u32 first subsong, u32 subsong count (one per permutation).
             Not sorted (sounds_debug is) -- entries are appended.
  FSB5 v1    0x3C header: 'FSB5', version, sample count, sample-header size, name-table
             size, data size, mode (7 = IMA ADPCM), 8 zero, 16-byte hash, 8 more. Sample
             header = u64: bit 0 extra chunks (none here), bits 1-4 rate index (5 = 22050,
             8 = 44100), bit 5 stereo, bits 6-33 data offset in 16-byte units, bits 34-63
             sample count. Name table: u32 offset per sample, then NUL-terminated names,
             padded so the data starts 32-aligned. Data: 16-aligned.
  XBOX IMA   36-byte blocks (mono): s16 predictor, u8 step index, u8 0, 32 bytes = 64
             4-bit codes (low nibble first) -> 64 samples per block.

APPENDING keeps every existing subsong index and data offset (data offsets are relative
to the data section), so the stock entries are untouched; only the new subsongs and the
new index entries are added. The header hash is left as shipped.
"""
import os
import struct

import numpy as np

HDR = 0x3C
RATES = {8000: 1, 11000: 2, 11025: 3, 16000: 4, 22050: 5, 24000: 6, 32000: 7, 44100: 8,
         48000: 9, 96000: 10}
STEPS = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55,
         60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
         337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411,
         1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
         5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500,
         20350, 22385, 24623, 27086, 29794, 32767]
INDEX = [-1, -1, -1, -1, 2, 4, 6, 8]


def encode_xbox_ima(pcm):
    """int16 mono samples -> XBOX IMA ADPCM blocks (36 bytes / 64 samples). Returns
    (bytes, sample count = blocks * 64; the tail is padded with silence)."""
    x = np.asarray(pcm, dtype=np.int32)
    blocks = -(-len(x) // 64)
    x = np.concatenate([x, np.zeros(blocks * 64 - len(x), dtype=np.int32)])
    out = bytearray()
    idx = 0
    for b in range(blocks):
        # the HEADER sample is the block's first output sample (vgmstream's XBOX IMA, as
        # measured: a predictor-only header put the decode one sample late, 12.6 dB SNR);
        # the 64 codes then give samples 1..63 -- the last code is padding
        blk = x[b * 64:(b + 1) * 64]
        pred = int(max(-32768, min(32767, blk[0])))
        out += struct.pack('<hBB', pred, idx, 0)
        codes = []
        for s in list(blk[1:]) + [blk[-1]]:
            step = STEPS[idx]
            diff = int(s) - pred
            code = 0
            if diff < 0:
                code = 8
                diff = -diff
            delta = step >> 3
            if diff >= step:
                code |= 4
                diff -= step
                delta += step
            if diff >= step >> 1:
                code |= 2
                diff -= step >> 1
                delta += step >> 1
            if diff >= step >> 2:
                code |= 1
                delta += step >> 2
            pred = pred - delta if code & 8 else pred + delta
            pred = max(-32768, min(32767, pred))
            idx = max(0, min(88, idx + INDEX[code & 7]))
            codes.append(code)
        out += bytes(codes[i] | (codes[i + 1] << 4) for i in range(0, 64, 2))
    return bytes(out), blocks * 64


def read_fsb(path):
    """(header fields dict, [sample header u64], [name], data bytes offset in file)."""
    with open(path, 'rb') as f:
        head = f.read(HDR)
        magic, ver, n, shs, nts, ds, mode = struct.unpack_from('<4sIIIIII', head, 0)
        if magic != b'FSB5' or ver != 1:
            raise ValueError('not an FSB5 v1 bank')
        sh = list(struct.unpack('<%dQ' % n, f.read(8 * n)))
        if shs != 8 * n or any(x & 1 for x in sh):
            raise ValueError('sample headers with extra chunks are not handled')
        nt = f.read(nts)
    offs = struct.unpack_from('<%dI' % n, nt, 0)
    names = [nt[o:nt.index(b'\0', o)].decode('latin-1') for o in offs]
    return dict(head=head, n=n, shs=shs, nts=nts, ds=ds, mode=mode), sh, names, HDR + shs + nts


def sample_header(rate, offset16, samples, stereo=False):
    return (RATES[rate] << 1) | (int(stereo) << 5) | (offset16 << 6) | (samples << 34)


def append_fsb(src, dst, new, keep=None):
    """Write `dst` = the first `keep` samples of `src` (all by default) + the `new`
    samples [(name, rate, ADPCM bytes, sample count)] appended. Kept indices/offsets are
    unchanged. Returns the first new subsong index. `src` may be `dst` (temp + swap)."""
    info, sh, names, data_at = read_fsb(src)
    if info['mode'] != 7:
        raise ValueError('bank mode %d, not IMA ADPCM' % info['mode'])
    if keep is not None and keep < info['n']:
        # drop the tail (an earlier install of port samples): data up to its first one
        info['ds'] = ((sh[keep] >> 6) & 0x0FFFFFFF) * 16
        sh, names, info['n'] = sh[:keep], names[:keep], keep
    pos = info['ds'] + (-info['ds'] % 16)
    blobs = bytearray(b'\0' * (pos - info['ds']))
    sh = list(sh)
    for name, rate, blob, ns in new:
        sh.append(sample_header(rate, pos // 16, ns))
        blobs += blob
        pos += len(blob)
        pad = -pos % 16
        blobs += b'\0' * pad
        pos += pad
    names = names + [n for n, _r, _b, _s in new]
    n = len(sh)
    table = bytearray()
    strings = bytearray()
    base = 4 * n
    for nm in names:
        table += struct.pack('<I', base + len(strings))
        strings += nm.encode('latin-1') + b'\0'
    nt = table + strings
    nt += b'\0' * (-(HDR + 8 * n + len(nt)) % 32)
    head = bytearray(info['head'])
    struct.pack_into('<IIII', head, 8, n, 8 * n, len(nt), info['ds'] + len(blobs))
    tmp = dst + '.h1_fsb_tmp'
    with open(src, 'rb') as f, open(tmp, 'wb') as o:
        o.write(head)
        o.write(struct.pack('<%dQ' % n, *sh))
        o.write(nt)
        f.seek(data_at)
        left = info['ds']
        while left:
            c = f.read(min(1 << 24, left))
            o.write(c)
            left -= len(c)
        o.write(blobs)
    os.replace(tmp, dst)
    return info['n']


def read_lst(path):
    d = open(path, 'rb').read()
    ver, cnt = struct.unpack_from('<II', d, 0)
    i, out = 8, []
    for _ in range(cnt):
        n = struct.unpack_from('<I', d, i)[0]
        name = d[i + 4:i + 4 + n].rstrip(b'\0').decode('latin-1')
        i += 4 + n
        first, count = struct.unpack_from('<II', d, i)
        i += 8
        out.append((name, first, count))
    return ver, out


def write_lst(path, ver, entries):
    out = bytearray(struct.pack('<II', ver, len(entries)))
    for name, first, count in entries:
        b = name.encode('latin-1') + b'\0'
        out += struct.pack('<I', len(b)) + b + struct.pack('<II', first, count)
    tmp = path + '.h1_fsb_tmp'
    open(tmp, 'wb').write(out)
    os.replace(tmp, path)
