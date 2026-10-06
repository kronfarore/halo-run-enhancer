"""Add a weapon's pickup-prompt icon to Halo 1's shared hud_msg_icons sheet (HCEEK tags),
as a NEW bitmap + NEW sequence, so every existing index stays where it was. Prints the
new sequence index for the weapon's HUD interface (messaging sequence_index).

The first run backs the stock tag up (hud_msg_icons.bitmap.stock); --restore puts it back.
It edits the CURRENT sheet: a name already present is replaced in place (same bitmap,
same sequence index), a new name is appended -- in `hud_msg_icons` AND its 32-bit twin
`hud_msg_icons_r`, at one index (h1_hud_sheet.py; the SAW's icon reached only the first). (Until 2026-10-05 it rebuilt from the stock
backup every time, which would have dropped every earlier port's icon -- the SAW is 25.)

    python add_msg_icon.py <icon.png> <sequence name>
    python add_msg_icon.py --restore
"""
import os, shutil, sys
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
    import h1_hud_sheet
    icon = Image.open(icon_path).convert('RGBA')
    # stock icons run ~130-160 px tall (plasma rifle 250x161): a taller one gets a 512x256
    # sheet of its own
    sheet_h = SHEET_H if icon.height <= SHEET_H else 256
    if icon.height > 256:
        raise SystemExit('icon taller than 256 px')
    if icon.width > SHEET_W or icon.height > sheet_h:
        raise SystemExit('icon larger than %dx%d' % (SHEET_W, sheet_h))
    # registration: the stock AR icon registers at half its width and 40% of its height
    i = h1_hud_sheet.put_twins('hud_msg_icons', name, icon, TEMPLATE_SEQ, (SHEET_W, sheet_h),
                               (icon.width / 2.0, icon.height * 0.40))
    print('sequence %d (%r) in hud_msg_icons and hud_msg_icons_r' % (i, name))


if __name__ == '__main__':
    main()
