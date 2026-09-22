r"""Give the Halo 3 SAW its own skin.

The shaders are Assault Rifle clones, so the model wears the Assault Rifle's textures.
The SAW's own maps were already decoded out of Halo 4 for the Halo 1 port and sit in the
HCEEK data folder as TIFs, so they only need importing into H3EK and the shader's DIFFUSE
reference pointing at them.

Only the base map is swapped. Halo 3's shader also takes detail, change-colour, bump,
microbump, illumination and reflection maps, and Halo 4's SAW does not ship equivalents
in the set that was extracted -- leaving those as the Assault Rifle's keeps the surface
behaving like a Halo 3 weapon while the colours become the SAW's.

Each bitmap is named so its tag path is EXACTLY as long as the Assault Rifle path it
replaces, which keeps the reference swap an in-place overwrite.

    python h3_saw_textures.py [--write]
"""
import argparse, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))  # balance tables live beside the JMS converters, see the port backup on F:
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402

B = os.sep
H3EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
HCEEK_BITMAPS = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'HCEEK',
                             'data', 'weapons', 'saw', 'bitmaps')
DATA_DIR = os.path.join(H3EK, 'data', 'objects', 'weapons', 'rifle', 'saw', 'bitmaps')
TAG_DIR = B.join(['objects', 'weapons', 'rifle', 'saw', 'bitmaps'])
SHADER_DIR = os.path.join(H3EK, 'tags', 'objects', 'weapons', 'rifle', 'saw', 'shaders')

AR_DIFFUSE = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'bitmaps',
                     'assault_rifle'])
# (source TIF, imported name -- length chosen so the tag path matches AR_DIFFUSE, shader)
JOBS = [('saw_diff.tif', 'saw_diffuse_from_halo_4', 'saw_body.shader'),
        ('saw_display.tif', 'saw_display_from_halo_4', 'saw_display.shader')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    print('the shader reference is overwritten in place, so lengths must match:')
    print('   %-56s %d' % (AR_DIFFUSE, len(AR_DIFFUSE)))
    ok = True
    for _tif, name, _sh in JOBS:
        tag = TAG_DIR + B + name
        same = len(tag) == len(AR_DIFFUSE)
        ok = ok and same
        print('   %-56s %d%s' % (tag, len(tag), '' if same else '   <== MUST MATCH'))
    if not ok:
        raise SystemExit('name lengths differ')

    print('\nimporting textures:')
    for tif, name, _sh in JOBS:
        src = os.path.join(HCEEK_BITMAPS, tif)
        dst = os.path.join(DATA_DIR, name + '.tif')
        if not os.path.exists(src):
            raise SystemExit('missing source texture: ' + src)
        print('   %-28s -> %s' % (tif, dst))
        if a.write:
            os.makedirs(DATA_DIR, exist_ok=True)
            shutil.copy2(src, dst)

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    r = subprocess.run([os.path.join(H3EK, 'tool.exe'), 'bitmaps', TAG_DIR],
                       cwd=H3EK, capture_output=True, text=True, errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    made = [l for l in out.splitlines() if 'saw_' in l][-4:]
    for l in made:
        print('   %s' % l.strip()[:100])
    for _tif, name, _sh in JOBS:
        tag = os.path.join(H3EK, 'tags', TAG_DIR, name + '.bitmap')
        print('   %-30s %s' % (name, 'imported' if os.path.exists(tag) else 'NOT CREATED'))

    print('\nrepointing the shaders:')
    for _tif, name, shader in JOBS:
        p = os.path.join(SHADER_DIR, shader)
        t = h3tag.Tag(p)
        before = len(t.data)
        n = t.repoint_in_place(AR_DIFFUSE, TAG_DIR + B + name, group='bitm')
        if len(t.data) != before:
            raise SystemExit('file size changed -- not an in-place overwrite')
        t.save()
        print('   %-22s %d reference(s) -> %s' % (shader, n, name))
    print('\nNow rebuild 010_jungle.')


if __name__ == '__main__':
    main()
