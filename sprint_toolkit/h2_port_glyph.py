r"""Step 8 of a Halo 2 port: its pickup icon at its RESERVED codepoint, in every English font
that draws HUD text (generalized from h2_saw_glyph.py, the SAW 2026-09-24 -- its notes stand:
`tool replace-font-char` draws the glyph, its codepoint argument is DECIMAL (hex reads as 0 and
rewrites notdef); h2_font_add.py creates the codepoint first; the fonts are edited inside H2EK
and copied back; no shipped glyph may change).

The codepoint is the config's `reservations['glyph']` (0xE13D the SAW, 0xE13E.. the wave ports:
H2_PORT_PLAN 0.3). The config's `glyph` section:
    box        the glyph's size (= its on-screen size; Bungie's widest is 160x62)
    model_3p   the port's mesh (an H4 render dump, h3_weapon_glyph.mesh)
    tif        the drawn glyph's file name in %TEMP%

    python h2_port_glyph.py <key> [--cp 0xE13E] [--write] [--restore]
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_font as hf  # noqa: E402
import h2_font_add as fa  # noqa: E402
import ports_h2  # noqa: E402

B = os.sep
H2EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
LIVE = hf.FONTS
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'h2_fonts')

#: the fonts an English game draws HUD text with
FONTS = ('conduit-9', 'conduit-12', 'conduit-13', 'fixedsys-9',
         'handel_gothic-11', 'handel_gothic-13', 'handel_gothic-24', 'MSLCD-14')
# set from the config by setup()
BOX = CP = MODEL = TIF = None


def setup(key):
    global BOX, CP, MODEL, TIF
    g = ports_h2.get(key, 'glyph')
    BOX, MODEL = tuple(g['box']), g['model_3p']
    CP = ports_h2.load(key)['reservations']['glyph']
    TIF = g.get('tif', key + '_h2_glyph.tif')


def art(path, box=None):
    """The SAW's silhouette as a TIFF, drawn from its own geometry."""
    import h3_weapon_glyph as wg
    from PIL import Image
    box = BOX if box is None else box
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--cp', type=lambda s: int(s, 0), default=None)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args(argv)
    setup(a.key)
    if a.cp is None:
        a.cp = CP

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

    tif = os.path.join(os.environ.get('TEMP', '.'), TIF)
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
