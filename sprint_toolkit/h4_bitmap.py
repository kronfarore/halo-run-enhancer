"""Decode an H4EK source bitmap tag's top mip to PNG/TGA, without the kit's exporter
(which fails with "rasterizer\\invalid" off a live renderer).

The pixel blob is the tag file's data chunk: 'tgbl' reversed ('lbgt') chunks precede it;
it is found as the u32 size (= mip-chain size + 8) directly followed by the pixels. Width,
height, format and mip count come from `tool export-tag-to-xml` of the same tag.
Supports dxt1 / dxt3 / dxt5 (Pillow decodes them from a DDS header) and a8r8g8b8.

    python h4_bitmap.py <bitmap tag> <width> <height> <format> <mips> <out.png>
"""
import io, struct, sys
from PIL import Image

BPB = {'dxt1': 8, 'dxt3': 16, 'dxt5': 16, 'dxn': 16}
SWAP16 = False
FOURCC = {'dxt1': b'DXT1', 'dxt3': b'DXT3', 'dxt5': b'DXT5', 'dxn': b'ATI2'}


def chain_size(w, h, fmt, mips):
    total = 0
    for _ in range(mips):
        if fmt in BPB:
            total += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * BPB[fmt]
        else:
            total += w * h * 4
        w, h = max(1, w // 2), max(1, h // 2)
    return total


def find_pixels(blob, size):
    """Offset of the pixel blob: right after its u32 size (mip chain + 8). The same value
    also appears in the data chunk's HEADER a few hundred bytes earlier, so the LAST
    match that leaves room for the pixels is the one."""
    best = None
    for want in (size + 8, size):
        key = struct.pack('<I', want)
        i = blob.find(key)
        while i != -1:
            if i + 4 + size <= len(blob):
                best = i + 4
            i = blob.find(key, i + 1)
        if best is not None:
            return best
    return len(blob) - size


def decode(tag, w, h, fmt, mips):
    blob = open(tag, 'rb').read()
    size = chain_size(w, h, fmt, mips)
    start = find_pixels(blob, size)
    top = blob[start:start + chain_size(w, h, fmt, 1)]
    if SWAP16:
        # Source tags keep the Xbox 360 byte order: every 16-bit word swapped (the block
        # layout itself is linear, so only the colours come out as noise without this).
        a = bytearray(top)
        a[0::2], a[1::2] = top[1::2], top[0::2]
        top = bytes(a)
    if fmt in FOURCC:
        hdr = (b'DDS ' + struct.pack('<7I', 124, 0x1007, h, w, len(top), 0, 1) + bytes(44)
               + struct.pack('<2I', 32, 0x4) + FOURCC[fmt] + struct.pack('<5I', 0, 0, 0, 0, 0)
               + struct.pack('<5I', 0x1000, 0, 0, 0, 0))
        img = Image.open(io.BytesIO(hdr + top))
        img.load()
        return img.convert('RGBA')
    return Image.frombytes('RGBA', (w, h), top, 'raw', 'BGRA')


if __name__ == '__main__':
    tag, w, h, fmt, mips, out = sys.argv[1:7]
    img = decode(tag, int(w), int(h), fmt, int(mips))
    img.save(out)
    print(out, img.size, img.mode)
