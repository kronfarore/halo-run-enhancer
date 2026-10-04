r"""Merge FMOD FSB5 banks -- and the Halo kits' .info index beside each -- into one.

WHY (2026-10-04, probed on the H3EK): the Halo 3 kit's FSBank fails with "FSBank error!
(7) An operating system based file error" whenever ONE `sounds-single-layer` call puts
6+ permutations into a bank that ALREADY has entries -- any sound, and re-imported
(updated) permutations count too; 1-3 per call work, and into an EMPTY bank any count
works. The tool still writes the tag, so a build carries on with the sound missing from
the bank (the SAW's melee, 8 and 6 variations, shipped silent that way). Pinning the
tool to one core or NUMBER_OF_PROCESSORS=1 does not help. The ODST and Reach kits have
no such limit. So saw_port_sounds.py builds every sound into its own fresh bank (always
works) and merges them here.

FSB5 v1 as the kits write it (Vorbis, mode 15):
    0x00  'FSB5', version 1, sample count, sample-header bytes, name-table bytes,
          data bytes, mode; 0x1C..0x3C flags + a 16-byte build hash (not derived from
          the content -- kept from the first bank)
    0x3C  per sample a u64 (bit 0 = chunks follow, bits 1-4 rate, 5-6 channels,
          7-33 data offset / 32, 34+ sample count), then its chunks: u32 (bit 0 = more,
          bits 1-24 size, 25-31 type -- 11 = Vorbis setup crc + seek table) + payload
    name table: one u32 offset per sample, then the names, zero-padded so the data
          starts on a 32-byte boundary
    data: each sample at its offset, 32-byte aligned
The .info is one 280-byte entry per sample, in the same order (entry index = subsong).

    python fsb5_merge.py out.fsb a.fsb b.fsb ...     (each .fsb with its .fsb.info)
"""
import struct
import sys

HDR = 0x3C
INFO_ENTRY = 280
OFFSET_MASK = 0x7FFFFFF << 7


def read(path):
    """{'tail': header bytes 0x1C..0x3C, 'mode', 'samples': [(u64 without its offset,
    chunk bytes, name, data bytes)]}"""
    return parse(open(path, 'rb').read(), path)


def parse(d, path='bank'):
    magic, ver, n, shs, nts, ds, mode = struct.unpack_from('<4sIIIIII', d, 0)
    if magic != b'FSB5' or ver != 1:
        raise ValueError('%s: not an FSB5 v1 bank' % path)
    if HDR + shs + nts + ds != len(d):
        raise ValueError('%s: sizes do not add up to the file' % path)
    heads, o = [], HDR
    for _ in range(n):
        h = struct.unpack_from('<Q', d, o)[0]
        start, o, more = o + 8, o + 8, h & 1
        while more:
            c = struct.unpack_from('<I', d, o)[0]
            more = c & 1
            o += 4 + ((c >> 1) & 0xFFFFFF)
        heads.append((h, d[start:o]))
    if o != HDR + shs:
        raise ValueError('%s: sample headers do not fill their region' % path)
    nt = d[o:o + nts]
    names = [nt[k:nt.index(b'\0', k)] for k in struct.unpack_from('<%dI' % n, nt)]
    data = d[HDR + shs + nts:]
    offs = [((h & OFFSET_MASK) >> 7) * 32 for h, _c in heads] + [ds]
    samples = [(h & ~OFFSET_MASK, chunks, names[k], data[offs[k]:offs[k + 1]])
               for k, (h, chunks) in enumerate(heads)]
    return {'tail': d[0x1C:HDR], 'mode': mode, 'samples': samples}


def build(tail, mode, samples):
    """FSB5 bytes from read()-style samples (offsets recomputed, data 32-aligned)."""
    shdr, data = bytearray(), bytearray()
    for h, chunks, _name, blob in samples:
        if len(data) % 32:
            data += bytes(32 - len(data) % 32)
        shdr += struct.pack('<Q', h | ((len(data) // 32) << 7)) + chunks
        data += blob
    if len(data) % 32:
        data += bytes(32 - len(data) % 32)
    names = bytearray()
    offs = []
    for s in samples:
        offs.append(4 * len(samples) + len(names))
        names += s[2] + b'\0'
    nt = bytearray(struct.pack('<%dI' % len(samples), *offs)) + names
    while (HDR + len(shdr) + len(nt)) % 32:
        nt += b'\0'
    head = struct.pack('<4sIIIIII', b'FSB5', 1, len(samples), len(shdr), len(nt), len(data),
                       mode) + tail
    return bytes(head + shdr + nt + data)


def merge(dst, srcs):
    """Write dst (.fsb + .fsb.info) = the banks in srcs, in order. Returns the count."""
    banks = [read(s) for s in srcs]
    modes = set(b['mode'] for b in banks)
    if len(modes) != 1:
        raise ValueError('banks of different modes: %s' % sorted(modes))
    samples = [s for b in banks for s in b['samples']]
    info = b''
    for s, b in zip(srcs, banks):
        i = open(s + '.info', 'rb').read()
        if len(i) != INFO_ENTRY * len(b['samples']):
            raise ValueError('%s.info: %d bytes for %d samples' % (s, len(i), len(b['samples'])))
        info += i
    out = build(banks[0]['tail'], modes.pop(), samples)
    back = parse(out, dst)['samples']              # every sample reads back unchanged
    if len(back) != len(samples) or any(
            b[:3] != s[:3] or b[3] != s[3].ljust(len(b[3]), b'\0')
            for b, s in zip(back, samples)):
        raise ValueError('merged bank does not read back')
    with open(dst, 'wb') as f:
        f.write(out)
    with open(dst + '.info', 'wb') as f:
        f.write(info)
    return len(samples)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    print('%d samples -> %s' % (merge(sys.argv[1], sys.argv[2:]), sys.argv[1]))
