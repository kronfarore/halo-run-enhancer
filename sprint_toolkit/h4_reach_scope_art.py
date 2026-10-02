r"""Halo 4 port, step 7 (scope art): Reach's Focus Rifle scope, redrawn for a Halo 4 HUD.

Reach draws the scope from its chud definition (ui\chud\focus_rifle.chud_definition),
read 2026-10-02:
  * scope_mask   beam_rifle_scope (a8, "double sized"), origin -1,-1, scale 1.2, mirrored
                 both ways = the lower-right quadrant of a 2:1 mask, extend border; colour
                 black, alpha = the bitmap: the octagonal lens and the dark surround.
  * meter_heat   beam_rifle_meter_r at +435,0, scale 1.19 (weapon heat)
  * meter_batt   beam_rifle_meter_l at -435,0, scale -1.19,1.14 (weapon battery)
  * meter_border beam_rifle_scope_meter_border ("triple sized"), origin 6.8,0.95, scale
                 1.2,1.23, mirrored both ways: the two side frames the meters sit in
  * crosshair    hud_reticles sequence 22 ("triple sized") at scale 0.5
  Units: a 1152x640 chud screen centred on the crosshair; "double sized" = 2 px a unit;
  a widget's origin is in half-extents of its bitmap (origin -1,-1 = top-left corner).
  The meter bitmaps are horizontal arcs; in the scope they stand upright inside the side
  frames, so they are drawn rotated a quarter turn here.

What Halo 4 gets (H4EK data ui\hud\weapons\covenant\focus_rifle\bitmap\, then `tool
bitmaps`):
  * scope_frame.tif  -- one full-screen RGBA picture: mask + side frames + reticle,
                        drawn for the 1280x720 HUD screen (the Halo 4 scope template's
                        bar-outline widget shows it, h4_reach_scope.py).
  * meter_heat.tif / meter_batt.tif -- Halo 4 METER bitmaps. Halo 4's hud_meter reads
    them like the Beam Rifle's heat_bar: R = A = the shape, G = B = the fill threshold
    (255 at the top, 0 at the bottom; measured on heat_bar/ammo_bar). Reach keeps the
    shape in A and its own gradient along the arc, so the shape is kept and the
    threshold is redrawn top-to-bottom.
  The bitmap TAGS are copies of the Beam Rifle's (bar_outlines: dxt5; heat_bar:
  a8r8g8b8, no mips) made before the import, so `tool bitmaps` keeps their settings.

    python h4_reach_scope_art.py [--write]
"""
import argparse
import os
import shutil
import subprocess

from PIL import Image, ImageChops, ImageOps

HREK = r'F:\SteamLibrary\steamapps\common\HREK'
H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
B = '\\'
SRC = os.path.join(H4EK, 'temp', 'focus_rifle_reach_scope')   # Reach exports land here
OWN = B.join(['ui', 'hud', 'weapons', 'covenant', 'focus_rifle', 'bitmap'])
DONOR = B.join(['ui', 'hud', 'weapons', 'covenant', 'beam_rifle', 'bitmap'])
#: own bitmap -> the Beam Rifle bitmap tag whose import settings it starts from
SETTINGS = {'scope_frame': 'bar_outlines', 'meter_heat': 'heat_bar', 'meter_batt': 'heat_bar'}
REACH = {'scope': r'ui\chud\bitmaps\scopes\beam_rifle_scope',
         'meter_l': r'ui\chud\bitmaps\scopes\beam_rifle_meter_l',
         'meter_r': r'ui\chud\bitmaps\scopes\beam_rifle_meter_r',
         'border': r'ui\chud\bitmaps\beam_rifle_scope_meter_border',
         'reticles': r'ui\chud\bitmaps\hud_reticles'}
RETICLE = (1040, 0, 1320, 275)     # hud_reticles sequence 22: 0.5078-0.6445 x 0-0.2686 of 2048x1024
CHUD = (1152, 640)                 # Reach chud units
SCREEN = (1280, 720)               # Halo 4 HUD units
FRAME_PX = (1920, 1080)            # scope_frame.tif
K = 2                              # compose at 2 px a chud unit
#: Reach's HUD colours for the frame lines and the reticle (chud "highlight"-ish blue)
FRAME_RGB = (150, 210, 255)
RETICLE_RGB = (210, 235, 255)
#: boot 23 (user): the HUD's own reticle is used zoomed too -- no Reach reticle in the art
DRAW_RETICLE = False
#: the meters, in Reach units: centre and size after the quarter turn (80x234 units of
#: bitmap at scale 1.19)
METER_CENTRE_X = 435
METER_SCALE = 1.19


def reach_export():
    os.makedirs(SRC, exist_ok=True)
    out = {}
    for key, tag in REACH.items():
        name = tag.rsplit(B, 1)[-1] + '_00_00.tga'
        path = os.path.join(SRC, name)
        if not os.path.exists(path):
            subprocess.run([os.path.join(HREK, 'tool.exe'), 'export-bitmap-tga', tag, SRC + B],
                           cwd=HREK, capture_output=True, text=True)
        if not os.path.exists(path):
            raise SystemExit('could not export %s from HREK' % tag)
        out[key] = Image.open(path)
    return out


def tinted(im, rgb):
    """Colour a bitmap: its brightness x alpha becomes the alpha of a flat colour."""
    im = im.convert('RGBA')
    lum = im.convert('L').point(lambda v: min(255, v * 2))
    a = ImageChops.multiply(im.getchannel('A'), lum)
    return Image.merge('RGBA', [Image.new('L', im.size, c) for c in rgb] + [a])


def place(can, im, scale, origin=(0, 0), offset=(0, 0), dsize=2.0, mirror_h=False,
          mirror_v=False, paste=False):
    """Reach chud placement onto a canvas of CHUD*K, centre origin."""
    sx, sy = scale
    w, h = im.width / dsize * abs(sx), im.height / dsize * abs(sy)
    img = im.resize((max(1, round(w * K)), max(1, round(h * K))), Image.LANCZOS)
    if sx < 0:
        img = ImageOps.mirror(img)
    if sy < 0:
        img = ImageOps.flip(img)
    cx = offset[0] - origin[0] * w / 2 * (1 if sx > 0 else -1)
    cy = offset[1] - origin[1] * h / 2 * (1 if sy > 0 else -1)
    W, H = CHUD

    def put(i, x, y):
        at = (round((W / 2 + x) * K - i.width / 2), round((H / 2 + y) * K - i.height / 2))
        if paste:
            can.paste(i, at)
        else:
            can.alpha_composite(i, (max(0, at[0]), max(0, at[1])),
                                (max(0, -at[0]), max(0, -at[1])))
    put(img, cx, cy)
    if mirror_h:
        put(ImageOps.mirror(img), -cx, cy)
    if mirror_v:
        put(ImageOps.flip(img), cx, -cy)
    if mirror_h and mirror_v:
        put(ImageOps.flip(ImageOps.mirror(img)), -cx, -cy)


def frame(src):
    W, H = CHUD
    a = src['scope'].convert('L')
    # extend border: the quadrant's outer corner value fills what the mask does not cover
    edge = a.getpixel((a.width - 1, a.height - 1))
    can = Image.new('RGBA', (W * K, H * K), (0, 0, 0, edge))
    mask = Image.merge('RGBA', [Image.new('L', a.size, 0)] * 3 + [a])
    place(can, mask, (1.2, 1.2), (-1, -1), mirror_h=True, mirror_v=True, paste=True)
    place(can, tinted(src['border'], FRAME_RGB), (1.2, 1.23), (6.8, 0.95), dsize=3.0,
          mirror_h=True, mirror_v=True)
    if DRAW_RETICLE:
        ret = src['reticles'].convert('RGBA').crop(RETICLE)
        place(can, tinted(ret, RETICLE_RGB), (0.5, 0.5), dsize=3.0)
    return can.resize(FRAME_PX, Image.LANCZOS)


def meter(im):
    """A Reach meter arc -> an upright Halo 4 meter bitmap (R = A = shape, G = B = the
    fill threshold, 255 at the top to 0 at the bottom)."""
    shape = im.convert('RGBA').getchannel('A').rotate(90, expand=True)
    w, h = shape.size
    grad = Image.new('L', (w, h))
    grad.putdata([round(255 * (1 - y / (h - 1))) for y in range(h) for _x in range(w)])
    return Image.merge('RGBA', (shape, grad, grad, shape))


def meter_rects():
    """Each meter's HUD rectangle (left, top, width, height) in 1280x720 units."""
    fx, fy = SCREEN[0] / CHUD[0], SCREEN[1] / CHUD[1]
    w = 160 / 2 * METER_SCALE * fx          # the arc is 468x160 px before the quarter turn
    h = 468 / 2 * METER_SCALE * fy
    out = {}
    for name, x in (('meter_heat', METER_CENTRE_X), ('meter_batt', -METER_CENTRE_X)):
        cx = SCREEN[0] / 2 + x * fx
        out[name] = (round(cx - w / 2, 1), round(SCREEN[1] / 2 - h / 2, 1), round(w, 1), round(h, 1))
    return out


def preview(art, meters, path):
    W, H = SCREEN
    can = Image.new('RGBA', (W, H), (95, 115, 95, 255))
    can.alpha_composite(art.resize((W, H), Image.LANCZOS))
    for name, (l, t, w, h) in meter_rects().items():
        m = meters[name]
        rgb = (255, 120, 60) if name == 'meter_heat' else (90, 170, 255)
        show = Image.merge('RGBA', [Image.new('L', m.size, c) for c in rgb] + [m.getchannel('A')])
        can.alpha_composite(show.resize((round(w), round(h)), Image.LANCZOS), (round(l), round(t)))
    can.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    src = reach_export()
    art = frame(src)
    meters = {'meter_heat': meter(src['meter_r']), 'meter_batt': meter(src['meter_l'])}
    prev = os.path.join(SRC, 'preview.png')
    preview(art, meters, prev)
    print('preview -> %s' % prev)
    for k, v in meter_rects().items():
        print('   %s rect (left, top, width, height) = %s' % (k, v))
    if not a.write:
        print('(dry run -- pass --write)')
        return
    data = os.path.join(H4EK, 'data', OWN)
    os.makedirs(data, exist_ok=True)
    art.save(os.path.join(data, 'scope_frame.tif'))
    for k, im in meters.items():
        im.save(os.path.join(data, k + '.tif'))
    tags = os.path.join(H4EK, 'tags', OWN)
    os.makedirs(tags, exist_ok=True)
    for own, donor in SETTINGS.items():
        dst = os.path.join(tags, own + '.bitmap')
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(H4EK, 'tags', DONOR, donor + '.bitmap'), dst)
    r = subprocess.run([os.path.join(H4EK, 'tool.exe'), 'bitmaps', OWN], cwd=H4EK,
                       capture_output=True, text=True, errors='replace')
    for line in (r.stdout + r.stderr).splitlines():
        if any(w in line.lower() for w in ('error', 'warning', 'import', 'bitmap')):
            print('   tool: ' + line.strip()[:110])
    for own in SETTINGS:
        p = os.path.join(tags, own + '.bitmap')
        print('   %-12s %8d bytes' % (own, os.path.getsize(p)))


if __name__ == '__main__':
    main()
