r"""Give the Reach SAW its own skin -- step 2.

The two shaders are Assault Rifle clones, so out of the box the port wears the Assault
Rifle's textures. This imports the SAW's own maps, decoded out of Halo 4 for the Halo 1
port and still sitting in HCEEK's data folder as TIFs, and points each shader's base map
at them.

ONLY THE BASE MAP, in both shaders. Reach's shader also takes a normal map, a microbump,
an illumination map and a cubemap, and the Halo 4 set that was extracted has no
equivalents -- leaving those as the Assault Rifle's keeps the surface behaving like a
Reach weapon while the colours become the SAW's. The display shader gets the same
treatment on its plate.

WHY THIS IS NOT h3_saw_textures.py. Two things differ and both matter:

  * Halo 3's base map is `assault_rifle`; Reach's is `assault_rifle_diffuse`, and its
    display plate is a separate `display_plate`. Different tags, different lengths.
  * Halo 3 names every imported bitmap so its tag path is EXACTLY as long as the one it
    replaces, so the swap is a byte overwrite. That constraint buys nothing here --
    `h3tag.repoint` rewrites the reference's length and every ancestor's, and `check()`
    proves the tree still spans the file -- and honouring it would mean padding a name
    to 31 characters for no reason. Reach's port uses repoint, as the model wiring does.

Reach's shaders list each reference TWICE (the tag carries two passes), so a swap that
reported one change would be a half-done shader. Both are expected and both are counted.

    python reach_saw_textures.py [--write]

Re-render afterwards: a shader that arrives after a render is not in it.
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402

B = os.sep
HCEEK_BITMAPS = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'HCEEK',
                             'data', 'weapons', 'saw', 'bitmaps')
DATA_DIR = os.path.join(h3_kit.DATA, 'objects', 'weapons', 'rifle', 'saw', 'bitmaps')
TAG_DIR = B.join(['objects', 'weapons', 'rifle', 'saw', 'bitmaps'])
SHADERS = B.join(['objects', 'weapons', 'rifle', 'saw', 'shaders'])
AR_BITMAPS = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'bitmaps'])

#: (source TIF, imported name, shader, the Assault Rifle map it replaces)
JOBS = [
    ('saw_diff.tif', 'saw_diffuse_from_halo_4', 'saw_body.shader', 'assault_rifle_diffuse'),
    ('saw_display.tif', 'saw_display_from_halo_4', 'saw_display.shader', 'display_plate'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if not h3_kit.IS_REACH:
        raise SystemExit('this is the Reach skin -- refusing to run against %s.\n'
                         'Halo 3 and ODST use h3_saw_textures.py.' % h3_kit.banner())

    print('%s' % h3_kit.banner())
    for tif, name, shader, _old in JOBS:
        src = os.path.join(HCEEK_BITMAPS, tif)
        if not os.path.exists(src):
            raise SystemExit('missing source texture: %s' % src)
        sh = os.path.join(h3_kit.TAGS, SHADERS, shader)
        if not os.path.exists(sh):
            raise SystemExit('missing %s -- clone it from the Assault Rifle first' % sh)
        print('   %-24s -> %s%s%s.tif' % (tif, TAG_DIR, B, name))

    if not a.write:
        for _tif, _name, shader, old in JOBS:
            t = h3tag.Tag(os.path.join(h3_kit.TAGS, SHADERS, shader))
            n = sum(1 for _o, g, p in t.references()
                    if g == 'bitm' and p == AR_BITMAPS + B + old)
            print('   %-20s %d reference(s) to %s' % (shader, n, old))
        print('\n(dry run -- pass --write)')
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    for tif, name, _sh, _old in JOBS:
        shutil.copy2(os.path.join(HCEEK_BITMAPS, tif),
                     os.path.join(DATA_DIR, name + '.tif'))
    print('\nimporting:')
    p = subprocess.run([h3_kit.TOOL, 'bitmaps', TAG_DIR], cwd=h3_kit.EK,
                       capture_output=True, text=True, errors='replace')
    text = (p.stdout or '') + (p.stderr or '')
    for tif, name, _sh, _old in JOBS:
        made = os.path.join(h3_kit.TAGS, TAG_DIR, name + '.bitmap')
        print('   %-42s %s' % (name + '.bitmap',
                               'ok' if os.path.exists(made) else 'NOT CREATED'))
        if not os.path.exists(made):
            print(text[-800:])
            raise SystemExit('tool bitmaps did not produce %s' % made)

    print('\npointing each shader at it:')
    for _tif, name, shader, old in JOBS:
        path = os.path.join(h3_kit.TAGS, SHADERS, shader)
        t = h3tag.Tag(path)
        before = len(t.data)
        n = t.repoint(AR_BITMAPS + B + old, TAG_DIR + B + name, group='bitm')
        ok, covered, total = t.check()
        if not ok:
            raise SystemExit('%s: tree no longer spans the file (%d of %d) -- NOT saved'
                             % (shader, covered, total))
        if not n:
            raise SystemExit('%s: found no reference to %s -- nothing was swapped'
                             % (shader, old))
        t.save()
        print('   %-20s %d reference(s), %d -> %d bytes, tree spans %d of %d'
              % (shader, n, before, len(t.data), covered, total))

    print('\nNow re-render, or the model keeps the shaders it was built with:')
    print('    tool render %s final' % B.join(['objects', 'weapons', 'rifle', 'saw']))


if __name__ == '__main__':
    main()
