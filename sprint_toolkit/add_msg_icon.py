"""Add a weapon's pickup-prompt icon to Halo 1's shared hud_msg_icons sheet (HCEEK tags),
as a NEW bitmap + NEW sequence, so every existing index stays where it was. Prints the
new sequence index for the weapon's HUD interface (messaging sequence_index).

The first run backs the stock tag up (hud_msg_icons.bitmap.stock); --restore puts it back.
It edits the CURRENT sheet: a name already present is replaced in place (same bitmap,
same sequence index), a new name is appended. (Until 2026-10-05 it rebuilt from the stock
backup every time, which would have dropped every earlier port's icon -- the SAW is 25.)

    python add_msg_icon.py <icon.png> <sequence name>
    python add_msg_icon.py --restore
"""
import copy, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.bitm import bitm_def
from PIL import Image

TAG = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags',
                   'ui', 'hud', 'bitmaps', 'combined', 'hud_msg_icons.bitmap')
BAK = os.path.join(HERE, 'hud_msg_icons.bitmap.stock')
SHEET_W, SHEET_H = 512, 128
TEMPLATE_SEQ = 8                 # the AR's icon: copy its sprite's field layout


def main():
    if sys.argv[1] == '--restore':
        shutil.copy2(BAK, TAG)
        print('restored', TAG)
        return
    icon_path, name = sys.argv[1], sys.argv[2]
    if not os.path.exists(BAK):
        shutil.copy2(TAG, BAK)
        print('backed up stock tag ->', BAK)
    t = bitm_def.build(filepath=TAG)          # the current sheet: earlier ports' icons stay
    d = t.data.tagdata
    icon = Image.open(icon_path).convert('RGBA')
    # stock icons run ~130-160 px tall (plasma rifle 250x161): a taller one gets a 512x256
    # sheet of its own
    sheet_h = SHEET_H if icon.height <= SHEET_H else 256
    if icon.width > SHEET_W or icon.height > sheet_h:
        raise SystemExit('icon larger than %dx%d' % (SHEET_W, sheet_h))
    sheet = Image.new('RGBA', (SHEET_W, sheet_h), (0, 0, 0, 0))
    sheet.paste(icon, (0, 0))
    raw = sheet.tobytes('raw', 'BGRA')

    bms = d.bitmaps.STEPTREE
    seqs = d.sequences.STEPTREE
    pix = bytearray(d.processed_pixel_data.data)
    have = [i for i, q in enumerate(seqs) if q.sequence_name == name[:31]]
    if have:                                    # replace in place: indices never move
        ns = seqs[have[0]]
        bi = ns.sprites.STEPTREE[0].bitmap_index
        nb = bms[bi]
        if nb.width * nb.height * 4 != len(raw):
            raise SystemExit('%r: the new icon needs a %dx%d sheet, its bitmap %d is %dx%d'
                             % (name, SHEET_W, sheet_h, bi, nb.width, nb.height))
        pix[nb.pixels_offset:nb.pixels_offset + len(raw)] = raw
    else:
        tmpl_b = bms[len(bms) - 1]
        bms.append(copy.deepcopy(tmpl_b))
        nb = bms[len(bms) - 1]
        nb.width, nb.height = SHEET_W, sheet_h
        nb.pixels_offset = len(pix)
        nb.mipmaps = 0
        pix += raw
        bi = len(bms) - 1
        seqs.append(copy.deepcopy(seqs[TEMPLATE_SEQ]))
        ns = seqs[len(seqs) - 1]
        ns.sequence_name = name[:31]
    d.processed_pixel_data.data = bytes(pix)
    sp = ns.sprites.STEPTREE[0]
    sp.bitmap_index = bi
    sp.left_side, sp.right_side = 0.0, icon.width / SHEET_W
    sp.top_side, sp.bottom_side = 0.0, icon.height / sheet_h
    # registration point in bitmap-normalised units, relative to the sprite: the stock
    # AR icon registers at half its width and 40% of its height
    sp.registration_point_x = icon.width / 2.0 / SHEET_W
    sp.registration_point_y = icon.height * 0.40 / sheet_h
    t.filepath = TAG
    t.serialize(temp=False, backup=False)
    print('%s bitmap %d, sequence %d (%r) -> %s'
          % ('replaced' if have else 'added', bi, have[0] if have else len(seqs) - 1,
             name, TAG))


if __name__ == '__main__':
    main()
