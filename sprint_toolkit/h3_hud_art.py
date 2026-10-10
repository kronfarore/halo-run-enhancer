r"""Read one sprite of a Halo 3 HUD sheet (H3EK `ui\chud\bitmaps\*.bitmap`) as an RGBA image.

H3EK's `tool export-bitmap-tga` fails on these ("rasterizer\invalid") and the generic
H4 decoder's pixel search lands a few bytes off (channels come out rotated). The pixels
are simply the tag's LARGEST `tgda` chunk, linear, top mip first (h3_meter_art.py,
h3_weapon_schematic.py): a8r8g8b8 stored B, G, R, A; dxt5 as plain 4x4 blocks.
Sheet size, format and the sprite boxes come from `tool export-tag-to-xml`.

Sprites used so far (2026-10-06): ballistic_meters 17 = the fuel rod's five-rod ammo
meter; hud_reticles 19 = fuel rod reticle, 13 = energy sword reticle.

    python h3_hud_art.py hud_reticles 13 out.png
"""
import io
import os
import re
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                    # noqa: E402
import h3_sprite_box            # noqa: E402
import h1_fp_retarget           # noqa: E402  (export_xml, cached)
import h4_bitmap                # noqa: E402  (chain_size, FOURCC)

REL = 'ui\\chud\\bitmaps\\%s.bitmap'


def decode(rel):
    """(RGBA image of the top mip, sprite boxes) of ANY Halo 3 bitmap tag (H3EK path); a
    `reach:` path is an HREK bitmap (reach_tags.decode_bitmap, the same shapes)."""
    if h1_fp_retarget.reach_tags.is_reach(rel):
        return h1_fp_retarget.reach_tags.decode_bitmap(rel)
    xml = h1_fp_retarget.export_xml(rel)
    s = io.open(xml, encoding='utf-8', errors='replace').read()
    g = lambda k: re.search(r'name="%s" value="([^"]*)"' % k, s).group(1)   # noqa: E731
    w, h, fmt = int(g('width')), int(g('height')), g('format')
    tag = h3tag.Tag(os.path.join(h1_fp_retarget.H3EK, 'tags', rel))
    nd = max((x for x in tag.nodes() if x.marker == 'tgda'), key=lambda x: x.length)
    blob = bytes(tag.data[nd.payload_at:nd.payload_at + nd.length])
    if fmt == 'a8r8g8b8':
        img = Image.frombytes('RGBA', (w, h), blob[:w * h * 4], 'raw', 'BGRA')
    elif fmt == 'a8':                     # alpha only (the BR's scope, 2026-10-07): white + alpha
        a = Image.frombytes('L', (w, h), blob[:w * h])
        img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
        img.putalpha(a)
    elif fmt in h4_bitmap.FOURCC:
        size = h4_bitmap.chain_size(w, h, fmt, 1)
        hdr = (b'DDS ' + struct.pack('<7I', 124, 0x1007, h, w, size, 0, 1) + bytes(44)
               + struct.pack('<2I', 32, 0x4) + h4_bitmap.FOURCC[fmt]
               + struct.pack('<5I', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0))
        img = Image.open(io.BytesIO(hdr + blob[:size]))
        img.load()
        img = img.convert('RGBA')
    else:
        raise SystemExit('%s: format %s not handled' % (rel, fmt))
    return img, h3_sprite_box.sprites(xml)


def sheet(name):
    """(RGBA image, [sprite boxes]) of a whole HUD sheet."""
    return decode(REL % name)


def sprite(name, index):
    """(RGBA crop, registration point in crop pixels)."""
    img, boxes = sheet(name)
    l, r, t, b, rx, ry = boxes[index]
    w, h = img.size
    return (img.crop((round(l * w), round(t * h), round(r * w), round(b * h))),
            (rx * w, ry * h))


if __name__ == '__main__':
    im, reg = sprite(sys.argv[1], int(sys.argv[2]))
    im.save(sys.argv[3])
    print(sys.argv[3], im.size, 'registration', reg)
