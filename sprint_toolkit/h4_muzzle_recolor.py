r"""Halo 4 port, step 6 (muzzle flash colour): an OWN copy of the Storm Rifle's firing
flash, recoloured to the Reach Focus Rifle's.

WHY: Reach's own muzzle particles do not draw in Halo 4 (boot 18), so the port borrows
the Storm Rifle's flash (h4_make_port_weapon.py MUZZLE_FX) -- which is Covenant
blue-violet. REACH'S FOCUS RIFLE MUZZLE IS ORANGE (read off HREK's
objects\weapons\rifle\focus_rifle\fx\firing.effect through ManagedBlam, 2026-10-02):
    flash        particle tint (255,98,42) -> (255,92,0)
    sparks       (255,200,72) -> (238,83,31)
    plasma       white -> (255,222,167)
    firing light (71,73,255) -- the light stays blue-violet, as in Reach
so every colour here moves to Reach's orange hue (TARGET_HUE) and keeps its saturation
and brightness; whites stay white.

WHAT CARRIES COLOUR in the Storm Rifle flash:
  * COLOUR FUNCTIONS (particle colour, lens flare tints): function_definition_data whose
    byte 2 is the colour count; a two-colour function keeps its colours in slots 0 and 3
    (u32 ARGB at +4 and +16) -- the same layout as Reach's tint functions.
  * PALETTE BITMAPS (shader parameters `palette` / `palettemap`: grad_bishop_glow,
    grad_plasma_blue, muzzle_flare_*, blue_plasma): own recoloured copies, imported with
    the donor bitmap tags' settings (the tag is copied before `tool bitmaps`).
  * the lights (firing_1p/3p) are left as they are.
The copied effect drops its SOUND part (the Storm Rifle's fire sound would play on top
of the Focus Rifle's own).

    python h4_muzzle_recolor.py [--write]
then h4_make_port_weapon.py points the weapon's secondary firing effect at
OWN_EFFECT (MUZZLE_FX). Needs a rebuild.
"""
import argparse
import colorsys
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
TAGS = os.path.join(H4EK, 'tags')
BLENDER = r'F:\Tools\blender-5.2.2-windows-x64\blender.exe'
B = '\\'
DONOR_EFFECT = B.join(['objects', 'weapons', 'rifle', 'storm_assault_carbine', 'fx', 'firing'])
OWN_DIR = B.join(['objects', 'weapons', 'rifle', 'focus_rifle', 'fx', 'muzzle'])
OWN_EFFECT = OWN_DIR + B + 'firing'
OWN_BITMAPS = OWN_DIR + B + 'bitmaps'
TARGET_HUE = 18 / 360.0          # Reach's flash: (255,98,42) is 16 deg, (255,92,0) 22 deg
EXT = {'prt3': 'particle', 'lens': 'lens_flare'}
LIST_JSON = os.path.join(H4EK, 'temp', 'focus_muzzle_parts.json')


def recolour_rgb(r, g, b):
    """Move a colour to Reach's orange, keeping saturation and brightness."""
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if s < 0.08:
        return r, g, b
    # keep a little of the original spread so a two-colour ramp stays a ramp
    d = ((h - 2 / 3.0 + 0.5) % 1.0) - 0.5
    h = (TARGET_HUE + d * 0.2) % 1.0
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return round(rr * 255), round(gg * 255), round(bb * 255)


def blender(args):
    r = subprocess.run([BLENDER, '--background', '--python', os.path.join(HERE, 'h4_muzzle_tags.py'),
                        '--'] + args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = [l for l in r.stdout.splitlines() if l.startswith(('MUZZLE', '   '))]
    print('\n'.join(out))
    if not any(l.startswith('MUZZLE OK') for l in out):
        print(r.stdout[-2000:])
        raise SystemExit('the Blender tag pass failed')


def bitmap_info(tag):
    out = os.path.join(H4EK, 'temp', 'focus_muzzle_bitmap.xml')
    subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml', os.path.join(TAGS, tag), out],
                   cwd=H4EK, capture_output=True)
    s = open(out, encoding='utf-8', errors='replace').read()
    d = dict(re.findall(r'name="(width|height|format|mipmap count)" value="([^"]*)"', s))
    if 'width' not in d:
        return None
    return int(d['width']), int(d['height']), d['format'], int(d.get('mipmap count', '0')) + 1


def make_palettes(palettes, write):
    """Own recoloured copies of the palette bitmaps. Returns {donor path: own path}."""
    from PIL import Image
    sys.path.insert(0, HERE)
    data = os.path.join(H4EK, 'data', OWN_BITMAPS)
    tags = os.path.join(TAGS, OWN_BITMAPS)
    repoint = {}
    for p in sorted(palettes):
        name = p.rsplit(B, 1)[-1]
        info = bitmap_info(p + '.bitmap')
        if info is None:
            print('   palette %-34s: the kit cannot export it, left as it is' % name)
            continue
        w, h, fmt, mips = info
        png = os.path.join(H4EK, 'temp', 'focus_muzzle_' + name + '.png')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'h4_bitmap.py'), os.path.join(TAGS, p + '.bitmap'),
                            str(w), str(h), fmt, str(mips), png], capture_output=True, text=True)
        if not os.path.exists(png):
            print('   palette %-34s %dx%d %s: could not decode, left as it is (%s)'
                  % (name, w, h, fmt, (r.stdout + r.stderr).strip()[-80:]))
            continue
        im = Image.open(png).convert('RGBA')
        px = [recolour_rgb(*q[:3]) + (q[3],) for q in im.get_flattened_data()]
        im.putdata(px)
        print('   palette %-34s %dx%d %-9s -> own copy' % (name, w, h, fmt))
        repoint[p] = OWN_BITMAPS + B + name
        if write:
            os.makedirs(data, exist_ok=True)
            os.makedirs(tags, exist_ok=True)
            im.save(os.path.join(data, name + '.tif'))
            shutil.copyfile(os.path.join(TAGS, p + '.bitmap'), os.path.join(tags, name + '.bitmap'))
    if write and repoint:
        r = subprocess.run([os.path.join(H4EK, 'tool.exe'), 'bitmaps', OWN_BITMAPS], cwd=H4EK,
                           capture_output=True, text=True, errors='replace')
        print('   tool bitmaps: %d imported' % (r.stdout + r.stderr).count('imported as'))
    return repoint


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    blender(['--list', LIST_JSON])
    parts = json.load(open(LIST_JSON))
    print('parts to copy: %d; palettes: %d' % (len(parts['parts']), len(parts['palettes'])))
    repoint = make_palettes(parts['palettes'], a.write)
    if not a.write:
        print('(dry run -- pass --write)')
        return
    json.dump({'parts': parts['parts'], 'palettes': repoint}, open(LIST_JSON, 'w'))
    blender(['--write', LIST_JSON])


if __name__ == '__main__':
    main()
