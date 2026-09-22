r"""Turn Halo 3's own font compiler into a Rosetta stone for the glyph codec.

The payloads in `maps\fonts\font_package_*.bin` are a packed opcode stream, and staring
at them gets nowhere: sizes run from 0.2 to 2.4 bytes per pixel, so it is not a bitmap,
and it is not zlib, bzip2 or lzma at any offset either.

It does not have to be guessed. `maps\fonts\build_fonts_icon.bat` shows the whole
pipeline, and both halves ship with the Editing Kit:

    tool windows-font-from-settings <settings>   bitmap tags -> a .font tag
    tool font-package <table>                    .font tags  -> font_package_<table>.bin

`icon=` in a settings line names a DIRECTORY OF BITMAP TAGS, one per icon, so feeding it
images whose every pixel is known and reading the payload that comes back gives an exact
(pixels -> bytes) pair. Every rule in `h3_font_codec` was found that way, by predicting
the output first and then checking it.

Two things constrain the probes. An icon tif must be named from the tool's own fixed list
or the run aborts at the first offender, and NAMES below are the twelve confirmed legal
ones. And the settings file is ICONS_ONLY, so nothing but the icons is rasterised.

    python h3_font_probe.py --demo        # re-run the probes that cracked the codec
    python h3_font_probe.py --verify      # decode every shipped package, both directions
"""
import argparse, io, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_font_package as fp                                     # noqa: E402
import h3_font_codec as fc                                       # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
DATA = os.path.join('data', 'ui', 'font_icons', 'test_18')
TAGS = os.path.join('tags', 'ui', 'font_icons', 'test_18')
SETTINGS = os.path.join('maps', 'fonts', 'icon_font_settings_test.txt')
TABLE = os.path.join('maps', 'fonts', 'font_table_test.txt')
PKG = os.path.join('maps', 'fonts', 'font_package_test.bin')

# the tool's icon-name table is fixed and alphabetical from 0xE112; these twelve are
# confirmed, which is as many probes as one build can carry
NAMES = ['assault_rifle', 'automag', 'ball', 'battle_rifle', 'bomb', 'carbine',
         'excavator', 'flag', 'golf_club', 'magnum', 'needler', 'sniper_rifle']
CP = {'assault_rifle': 0xE112, 'ball': 0xE113, 'battle_rifle': 0xE114,
      'bomb': 0xE115, 'carbine': 0xE117, 'excavator': 0xE11A, 'flag': 0xE11C,
      'magnum': 0xE123, 'needler': 0xE125, 'sniper_rifle': 0xE131,
      'automag': 0xE144, 'golf_club': 0xE145}


def _tool(*args):
    subprocess.run([os.path.join(EK, 'tool.exe')] + list(args), cwd=EK,
                   capture_output=True)


def _settings():
    io.open(os.path.join(EK, SETTINGS), 'w', encoding='utf-8', newline='\r\n').write(
        'ICONS_ONLY\n\nFONT: file=icon%stest-hud icon=ui%sfont_icons%stest_18 '
        'system=0 height=9 weight=400 italics=0 typeface=Fixedsys charset=0 scale=1\n'
        % (B, B, B))
    io.open(os.path.join(EK, TABLE), 'w', encoding='utf-8', newline='\r\n').write(
        'icon%stest-hud.font\n' % B)


def build(images):
    """Compile PIL images (aligned with NAMES) and return {name: (w, h, payload)}."""
    shutil.rmtree(os.path.join(EK, DATA), ignore_errors=True)
    shutil.rmtree(os.path.join(EK, TAGS), ignore_errors=True)
    os.makedirs(os.path.join(EK, DATA))
    _settings()
    for name, im in zip(NAMES, images):
        if im is not None:
            im.save(os.path.join(EK, DATA, name + '.tif'), compression=None)
    _tool('bitmaps', 'ui/font_icons/test_18')
    _tool('windows-font-from-settings', SETTINGS.replace(B, '/'))
    if os.path.exists(os.path.join(EK, PKG)):
        os.remove(os.path.join(EK, PKG))
    _tool('font-package', 'font_table_test')
    data = io.open(os.path.join(EK, PKG), 'rb').read()
    g = fp.glyphs(data)
    out = {}
    for name, im in zip(NAMES, images):
        cp = CP[name]
        if im is not None and cp in g:
            _f, w, h, size, at = g[cp]
            out[name] = (w, h, data[at + 16:at + 16 + size])
    return out


def cleanup():
    shutil.rmtree(os.path.join(EK, DATA), ignore_errors=True)
    shutil.rmtree(os.path.join(EK, TAGS), ignore_errors=True)
    for p in (SETTINGS, TABLE, PKG):
        if os.path.exists(os.path.join(EK, p)):
            os.remove(os.path.join(EK, p))


def demo():
    from PIL import Image, ImageDraw
    def art(w, h):
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w - 1, h - 1], outline=(255, 255, 255, 255))
        d.line([0, 0, w - 1, h - 1], fill=(255, 255, 255, 255))
        d.rectangle([4, 4, 12, 12], fill=(255, 255, 255, 255))
        d.line([0, h // 2, w - 1, h // 2], fill=(255, 255, 255, 255))
        return im
    sizes = [(155, 44), (99, 41), (24, 24), (70, 43), (136, 36), (31, 17),
             (129, 45), (64, 64), (17, 9), (100, 7), (7, 100), (13, 13)]
    imgs = [art(w, h) for w, h in sizes]
    got = build(imgs)
    print('%-14s %-10s %-10s %s' % ('icon', 'source', 'glyph', 'pixels identical'))
    bad = 0
    for name, im in zip(NAMES, imgs):
        if name not in got:
            continue
        w, h, pay = got[name]
        px = fc.decode(pay, w, h)
        want = list(im.convert("RGBA").getdata())
        same = sum(1 for p, q in zip(px, want)
                   if (p[0] > 7) == (q[3] > 127))
        bad += (same != len(want))
        print('%-14s %-10s %-10s %d/%d' % (name, '%dx%d' % im.size,
                                           '%dx%d' % (w, h), same, len(want)))
    print('\n%s' % ('every probe reproduced exactly' if not bad
                    else '%d probes disagree' % bad))
    cleanup()


def verify():
    total = exact = rt = 0
    for name in sorted(os.listdir(fp.FONTS)):
        if not name.endswith('.bin'):
            continue
        data = io.open(os.path.join(fp.FONTS, name), 'rb').read()
        try:
            g = fp.glyphs(data)
        except Exception as e:
            print('%-26s unreadable: %s' % (name, e))
            continue
        ok = 0
        for cp, (_f, w, h, size, at) in g.items():
            pay = data[at + 16:at + 16 + size]
            px = fc.decode(pay, w, h)
            ok += 1
            rt += (fc.decode(fc.encode(px), w, h) == px)
        total += len(g)
        exact += ok
        print('%-26s %6d glyphs   decoded %6d' % (name, len(g), ok))
    print('\n%d / %d glyphs decode with the payload consumed exactly; %d re-encode '
          'and decode back unchanged' % (exact, total, rt))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()
    if a.demo:
        demo()
    if a.verify or not a.demo:
        verify()


if __name__ == '__main__':
    main()
