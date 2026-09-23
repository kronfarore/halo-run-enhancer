"""Add a weapon's pickup-prompt icon to Halo 1's shared hud_msg_icons sheet (HCEEK tags),
as a NEW bitmap + NEW sequence, so every existing index stays where it was. Prints the
new sequence index for the weapon's HUD interface (messaging sequence_index).

The first run backs the stock tag up to the scratchpad; --restore puts it back.
Re-running with the same name replaces that entry instead of adding another.

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
    t = bitm_def.build(filepath=BAK)          # always start from stock: idempotent
    d = t.data.tagdata
    icon = Image.open(icon_path).convert('RGBA')
    if icon.width > SHEET_W or icon.height > SHEET_H:
        raise SystemExit('icon larger than %dx%d' % (SHEET_W, SHEET_H))
    sheet = Image.new('RGBA', (SHEET_W, SHEET_H), (0, 0, 0, 0))
    sheet.paste(icon, (0, 0))
    raw = sheet.tobytes('raw', 'BGRA')

    bms = d.bitmaps.STEPTREE
    tmpl_b = bms[len(bms) - 1]
    pix = bytearray(d.processed_pixel_data.data)
    bms.append(copy.deepcopy(tmpl_b))
    nb = bms[len(bms) - 1]
    nb.width, nb.height = SHEET_W, SHEET_H
    nb.pixels_offset = len(pix)
    nb.mipmaps = 0
    pix += raw
    d.processed_pixel_data.data = bytes(pix)
    bi = len(bms) - 1

    seqs = d.sequences.STEPTREE
    seqs.append(copy.deepcopy(seqs[TEMPLATE_SEQ]))
    ns = seqs[len(seqs) - 1]
    ns.sequence_name = name[:31]
    sp = ns.sprites.STEPTREE[0]
    sp.bitmap_index = bi
    sp.left_side, sp.right_side = 0.0, icon.width / SHEET_W
    sp.top_side, sp.bottom_side = 0.0, icon.height / SHEET_H
    # registration point in bitmap-normalised units, relative to the sprite: the stock
    # AR icon registers at half its width and 40% of its height
    sp.registration_point_x = icon.width / 2.0 / SHEET_W
    sp.registration_point_y = icon.height * 0.40 / SHEET_H
    t.filepath = TAG
    t.serialize(temp=False, backup=False)
    print('added bitmap %d and sequence %d (%r) -> %s' % (bi, len(seqs) - 1, name, TAG))


if __name__ == '__main__':
    main()
