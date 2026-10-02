r"""Halo 4 port, step 8 (icon): the port's OWN pickup pictogram in Halo 4's icon fonts.

HALO 4'S ICON PACKAGES, measured 2026-10-02 (maps\fonts\font_package_icon[_x2|_x3|_x4].bin):
  * the SAME container as Halo 3 / ODST / Reach -- header triples with each font's block
    range, the per-block key index (+0x410 offset, +0x414 count), first-fit layout -- with
    0x10000 BLOCKS instead of 0xC000. h3_font_repack.py rebuilds all four shipped Halo 4
    packages BYTE FOR BYTE with BLOCK = 0x10000, so it is the writer here too.
  * a glyph RECORD has a 12-byte header, not Halo 3's 16:
        u16 advance, u16 payload size, u16 width, u16 height, u16 0, u16 12 * resolution
    then the payload in Halo 3's codec (h3_font_codec): all 408 glyphs of the x1 package
    decode with the payload consumed exactly.
  * x2/x3/x4 are exactly 2x/3x/4x of x1 (the Beam Rifle-class pictograms: 120x35 ->
    240x70 -> 360x105 -> 480x140).
  * the pickup pictograms are font 2, icon\fixedsys-hud.
  * Halo 4 has no Focus Rifle / Sentinel Beam macro, so the port draws its own: the
    side silhouette of its render mesh (h4_mesh_dump.py), styled like the shipped icons
    (h3_weapon_glyph.stylise: grey body, bright outline), at a FREE codepoint of font 2.
    The pickup lines then carry that literal character (a private-use character works in
    place of a macro -- the Halo 3 lesson), see h4_port_messages.py --glyph.

    python h4_weapon_glyph.py [--write] [--restore]
"""
import argparse
import io
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_font_codec as fc                                     # noqa: E402
import h3_font_repack as fr                                    # noqa: E402
import h3_weapon_glyph as wg                                   # noqa: E402

FONTS = (r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
         r'\halo4\maps\fonts')
PACKAGES = {'font_package_icon.bin': 1, 'font_package_icon_x2.bin': 2,
            'font_package_icon_x3.bin': 3, 'font_package_icon_x4.bin': 4}
BACKUP = r'E:\HaloBackups\h4_live_fonts'
MESH = (r'F:\SteamLibrary\steamapps\common\H4EK\data\objects\weapons\rifle\focus_rifle'
        r'\focus_rifle_mesh.json')
FONT = 2
BOX = (136, 40)                      # x1; the shipped weapon pictograms run 117-158 x 35-56
GLYPH = 0xE1F6                       # first free above font 2's shipped top (0xE1F5)
H4_BLOCK = 0x10000


def silhouette(V, T, W, H, ss=8, margin=0):
    """Side view (-y across = muzzle right, z up) of a TRIANGLE list, antialiased."""
    from PIL import Image, ImageDraw
    a = [-v[1] for v in V]
    b = [v[2] for v in V]
    ea, eb = max(a) - min(a), max(b) - min(b)
    s = min((W - 2 * margin) / ea, (H - 2 * margin) / eb)
    ox, oy = (W - ea * s) / 2.0, (H - eb * s) / 2.0
    P = [((ox + (a[i] - min(a)) * s) * ss, (H - oy - (b[i] - min(b)) * s) * ss)
         for i in range(len(V))]
    im = Image.new('L', (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    for i0, i1, i2 in T:
        d.polygon([P[i0], P[i1], P[i2]], fill=255)
    return im.resize((W, H), Image.LANCZOS)


def record(payload, w, h, res):
    rec = struct.pack('<HHHHHH', w, len(payload), w, h, 0, 12 * res) + payload
    return rec + b'\0' * (-len(rec) % 16)


def build(name, res, V, T, write):
    path = os.path.join(FONTS, name)
    d = open(path, 'rb').read()
    W, H = BOX[0] * res, BOX[1] * res
    cov = wg.close_gaps(silhouette(V, T, W, H), 4 * res + 1)
    px = wg.stylise(cov)
    pay = fc.encode(px, full=True)
    if fc.decode(pay, W, H) != px:
        raise SystemExit('%s: the glyph does not survive its own codec' % name)
    fr.BLOCK = H4_BLOCK
    have = {(c, f) for c, f, _r, _s in fr.entries(d)[1]}
    if (GLYPH, FONT) in have:
        print('%-26s U+%04X already present -- rebuilding it' % (name, GLYPH))
        d = remove_glyph(d, GLYPH, FONT)
    out = fr.repack(d, add=[(GLYPH, FONT, record(pay, W, H, res))])
    out = fr.font_header_add(out, GLYPH, FONT, pay, (W, H))
    if not fr.check_index(out)[0]:
        raise SystemExit('%s: bad index after the add' % name)
    got = {(c, f): rec for c, f, rec, _s in fr.entries(out)[1]}
    rec = got[(GLYPH, FONT)]
    if fc.decode(rec[12:12 + len(pay)], W, H) != px:
        raise SystemExit('%s: the written glyph does not read back' % name)
    print('%-26s U+%04X %dx%d, %d payload bytes, %d -> %d blocks'
          % (name, GLYPH, W, H, len(pay), len(d) // H4_BLOCK - 1, len(out) // H4_BLOCK - 1))
    if write:
        keep = os.path.join(BACKUP, name)
        if not os.path.exists(keep):
            os.makedirs(BACKUP, exist_ok=True)
            shutil.copyfile(path, keep)
        open(path, 'wb').write(out)
    return px, W, H


def remove_glyph(d, cp, font):
    header, ents, _split = fr.entries(d)
    keep = [e for e in ents if (e[0], e[1]) != (cp, font)]
    return fr.assemble(header, fr.layout(keep))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.restore:
        for name in PACKAGES:
            shutil.copyfile(os.path.join(BACKUP, name), os.path.join(FONTS, name))
            print('restored', name)
        return
    m = json.load(open(MESH))
    V, T = m['vertices'], m['triangles']
    from PIL import Image
    shots = []
    for name, res in PACKAGES.items():
        px, W, H = build(name, res, V, T, a.write)
        if res == 1:
            im = Image.new('RGBA', (W, H))
            im.putdata([(r * 17, g * 17, b * 17, al * 17) for al, r, g, b in px])
            shots.append(im)
    prev = os.path.join(os.environ.get('TEMP', '.'), 'h4_focus_glyph.png')
    sheet = Image.new('RGBA', (shots[0].width + 8, shots[0].height + 8), (20, 22, 26, 255))
    sheet.alpha_composite(shots[0], (4, 4))
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(prev)
    print('preview -> %s' % prev)
    print('written into the LIVE packages (no rebuild)' if a.write else '(dry run -- pass --write)')


if __name__ == '__main__':
    main()
