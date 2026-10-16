r"""An H4EK .material's PARAMETER VALUES (read-only) -- `tool export-tag-to-xml` refuses .material, so the
values are read from the tag bytes (the Binary Rifle, C6 2026-10-16: albedo tint, self-illum colour and
intensity for the look). Each parameter's name is followed by its function blob (`adgt` chunk: u32 size
at +8, data from +12): a constant real = the float at +4, a COLOUR = BGRA bytes at +4 (printed as RGB
0-1). Bitmap parameters carry no blob (their path is in the tag as text: printed too).

    python h4_material_params.py <material under H4EK\tags, with extension> [...]
"""
import os
import re
import struct
import sys

H4EK_TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'


def params(path):
    b = open(path, 'rb').read()
    names = [(m.start(), m.group(1).decode()) for m in re.finditer(rb'([a-z_0-9]+)frgt', b) if m.start() > 0x1200]
    for n, (i, name) in enumerate(names):
        end = names[n + 1][0] if n + 1 < len(names) else len(b)
        bm = re.search(rb'mtib(objects\\[ -~]+?|fx\\[ -~]+?|shaders\\[ -~]+?)isgt', b[i:end])
        j = b.find(b'adgt', i, end)
        size = struct.unpack_from('<I', b, j + 8)[0] if j >= 0 else 0
        blob = b[j + 12:j + 12 + size] if size else b''
        if bm:
            yield name, 'bitmap ' + bm.group(1).decode()
        elif len(blob) >= 8 and blob[2] == 2:            # a colour function: BGRA bytes at +4
            bl, g, r, a = blob[4:8]
            yield name, 'colour %.3f %.3f %.3f' % (r / 255.0, g / 255.0, bl / 255.0)
        elif len(blob) >= 8:
            yield name, 'real %.4g' % struct.unpack_from('<f', blob, 4)[0]
        else:
            yield name, '(no value)'


def main():
    for rel in sys.argv[1:]:
        print('==', rel)
        for name, v in params(os.path.join(H4EK_TAGS, rel)):
            print('   %-30s %s' % (name, v))


if __name__ == '__main__':
    main()
