r"""Give the Halo 2 SAW a pickup glyph of its own, in every font that draws one.

The Halo 3 side of this had to write the glyph payload by hand. Halo 2 does not: H2EK
ships `tool replace-font-char`, so Bungie's own encoder draws the pixels. What it will NOT
do is add a codepoint -- an unmapped one resolves to the font's notdef glyph and the tool
replaces THAT, which would turn every unmapped character in the game into a SAW. So
`h2_font_add.py` creates the entry first and this drives the pair over every font.

Two things that cost a run each:

* **the codepoint argument is DECIMAL.** `replace-font-char ... 0xE13D` is read as 0 and
  silently rewrites the notdef glyph -- it even says "replaced char 0" while reporting the
  notdef's 34x34 size, which is the only sign anything went wrong;
* the fonts must be edited where the tool can reach them, so each is copied into H2EK,
  edited there and copied back.

0xE13D is free in all eight English fonts, and there are 195 more above it, so the next
port takes the next one. The Halo 2 icon list grows the same way the Halo 3 one now does.

    python h2_saw_glyph.py [--cp 0xE13D] [--write]
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_font as hf
import h2_font_add as fa

B = os.sep
H2EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
LIVE = hf.FONTS
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'h2_fonts')

#: the fonts an English game draws HUD text with
FONTS = ('conduit-9', 'conduit-12', 'conduit-13', 'fixedsys-9',
         'handel_gothic-11', 'handel_gothic-13', 'handel_gothic-24', 'MSLCD-14')

#: Bungie's widest weapon icon is 160x62 and the SAW is a long weapon, so it takes the
#: same box. The box IS the on-screen size, as it was in Halo 3.
BOX = (160, 62)
CP = 0xE13D
MODEL = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK',
                     'saw_3p_rm.xml')


def art(path, box=BOX):
    """The SAW's silhouette as a TIFF, drawn from its own geometry."""
    import h3_weapon_glyph as wg
    from PIL import Image
    verts, idx = wg.mesh(MODEL)
    cov = wg.close_gaps(wg.silhouette(verts, idx, box[0], box[1], margin=0), 5)
    px = wg.stylise(cov)
    im = Image.new('RGBA', box)
    im.putdata([(r * 17, g * 17, b * 17, a * 17) for a, r, g, b in px])
    im.save(path, compression=None)
    return sum(1 for q in px if q[0])


def one(name, tif, cp, write):
    live = os.path.join(LIVE, name)
    before = open(live, 'rb').read()
    if hf.glyph_of(before, cp) is not None:
        print('   %-20s 0x%04X already drawn by glyph %d'
              % (name, cp, hf.glyph_of(before, cp)))
        return True
    after = fa.add(before, cp)
    problem = fa.verify(before, after, cp)
    if problem:
        print('   %-20s REFUSED: %s' % (name, problem))
        return False
    if not write:
        print('   %-20s would add glyph %d' % (name, hf.header(before)[0]))
        return True

    work = os.path.join(H2EK, 'h2_fonts', name)
    open(work, 'wb').write(after)
    # DECIMAL. Hex is read as zero and rewrites the notdef glyph instead.
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'replace-font-char',
                        B.join(['h2_fonts', name]), tif, str(cp)],
                       cwd=H2EK, capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    if 'replaced char %d' % cp not in out:
        print('   %-20s tool did not replace it: %s' % (name, ' '.join(out.split())[:90]))
        return False
    done = open(work, 'rb').read()
    i = hf.glyph_of(done, cp)
    rec = hf.record(done, i)
    disturbed = [k for k in range(hf.header(before)[0])
                 if hf.record(before, k)[:6] != hf.record(done, k)[:6]
                 or hf.payload(before, k) != hf.payload(done, k)]
    if disturbed:
        print('   %-20s REFUSED: %d shipped glyph(s) changed' % (name, len(disturbed)))
        return False
    shutil.copy(work, live)
    print('   %-20s glyph %3d  %3dx%-3d advance %3d   %d -> %d bytes'
          % (name, i, rec[2], rec[3], rec[0], len(before), len(done)))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cp', type=lambda s: int(s, 0), default=CP)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()

    if a.restore:
        for name in FONTS:
            src = os.path.join(BACKUP, name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(LIVE, name))
                print('   restored %s' % name)
        return

    os.makedirs(BACKUP, exist_ok=True)
    for name in FONTS:
        keep = os.path.join(BACKUP, name)
        if not os.path.exists(keep):
            shutil.copy(os.path.join(LIVE, name), keep)

    tif = os.path.join(os.environ.get('TEMP', '.'), 'saw_h2_glyph.tif')
    print('drawing the glyph: %d ink pixels in %dx%d' % (art(tif), BOX[0], BOX[1]))
    print('adding 0x%04X (decimal %d):' % (a.cp, a.cp))
    ok = True
    for name in FONTS:
        ok &= one(name, tif, a.cp, a.write)
    if not a.write:
        print('(dry run -- pass --write)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
