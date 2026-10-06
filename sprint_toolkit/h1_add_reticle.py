r"""Bring a Halo 3 reticle into Halo 1's `ui\hud\bitmaps\combined\hud_reticles` (HCEEK tag).

Halo 1 keeps every reticle as its own 256x256 a8y8 bitmap (luminance 255 = white, alpha =
the shape) behind one sequence, registered at (128, 125). A new reticle is APPENDED as a
bitmap + sequence copied from the PC fuel rod's (#15), so no stock index moves; a name
already present is replaced in place. It goes into `hud_reticles_r` at the SAME index
(h1_hud_sheet.py): written to the plain sheet only, the sword's reticle drew as a blue
square in game (2026-10-06).

SCALE. The same weapon's reticle in both games fixes it: the PC fuel rod's Halo 1 reticle
(#15) reaches 123 px from its centre, Halo 3's fuel rod reticle (hud_reticles #19) 97 px,
so Halo 3 art is drawn x123/97 = x1.27 in Halo 1's sheet (measured 2026-10-06). A weapon
HUD's crosshair element then points its overlay at the new sequence.

    python h1_add_reticle.py hud_reticles 13 "energy sword"
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import h3_hud_art  # noqa: E402

TAG = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags',
                   'ui', 'hud', 'bitmaps', 'combined', 'hud_reticles.bitmap')
TEMPLATE_SEQ = 15            # the PC fuel rod's reticle
SIZE, CENTRE = 256, (128, 125)
SCALE = 123.0 / 97.0


def add(h3_sheet, h3_index, name):
    """The Halo 3 sprite into `hud_reticles` AND `hud_reticles_r`, one sequence index."""
    import h1_hud_sheet
    art, (rx, ry) = h3_hud_art.sprite(h3_sheet, h3_index)
    w, h = round(art.width * SCALE), round(art.height * SCALE)
    alpha = art.split()[3].resize((w, h), Image.LANCZOS)
    canvas = Image.new('L', (SIZE, SIZE), 0)
    canvas.paste(alpha, (round(CENTRE[0] - rx * SCALE), round(CENTRE[1] - ry * SCALE)))
    white = Image.new('L', (SIZE, SIZE), 255)
    img = Image.merge('RGBA', (white, white, white, canvas))
    canvas.save(os.path.join(HERE, 'out', 'reticle_%s.png' % name.replace(' ', '_')))
    return h1_hud_sheet.put_twins('hud_reticles', name, img, TEMPLATE_SEQ, (SIZE, SIZE), CENTRE)


if __name__ == '__main__':
    print('sequence', add(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
