r"""Halo 4 port, step 2: the port's MATERIALS and their bitmaps, in H4EK.

WHY BY HAND. A model brought in through Foundry keeps its legacy shader paths, and H4EK has
no legacy shader definitions at all -- no .shader tags, no shader.render_method_definition.
Foundry's own `nwo.shader_to_material` copies the Reach shaders into H4EK and then fails to
load the first one, so every surface exports as `shaders\invalid`. Halo 4 surfaces are
`.material` tags on a material shader instead.

HOW. Every material is a COPY of a donor Halo 4 weapon's material -- the Beam Rifle's, a
Covenant weapon of the same family -- with its bitmap references repointed at the port's
own bitmaps. The shader, the reflection cube and the detail maps stay the donor's, so
nothing here invents a material parameter.

THE BITMAPS come from the textures Foundry extracted from the Reach tags into HREK's data
folder (diffuse + normal). Halo 4's `srf_char_blinn_reflection` also wants a CONTROL map
(R specular, G gloss, B reflection): Reach keeps the weapon's specular mask in the diffuse
ALPHA, so that becomes R; gloss is a constant, reflection half the specular. Rubber gets a
duller one. `tool bitmaps` imports them; the Beam Rifle's own control map is a
'Diffuse Map' too, so the default usage is the donor's.

    python h4_port_materials.py            # dry run
    python h4_port_materials.py --write
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
HREK = r'F:\SteamLibrary\steamapps\common\HREK'
B = '\\'

PORT = 'objects\\weapons\\rifle\\focus_rifle'
SOURCE_TEX = os.path.join(HREK, 'data', PORT, 'bitmaps')        # Foundry's extraction
DONOR = 'objects\\weapons\\rifle\\storm_beam_rifle'
DONOR_MATS = DONOR + '\\shaders\\storm_beam_rifle_default\\'
DONOR_BMPS = DONOR + '\\bitmaps\\storm_beam_rifle_default\\storm_beam_rifle_default_'

#: port material -> (donor material, {donor bitmap suffix: port bitmap name})
OWN = {'diff': 'focus_rifle_diff', 'normal': 'focus_rifle_normal',
       'control': 'focus_rifle_control'}
MATERIALS = {
    'focus_rifle_metal': ('storm_beam_rifle_metal', OWN),
    'focus_rifle_shell': ('storm_beam_rifle_shell', OWN),
    'focus_rifle_rubber': ('storm_beam_rifle_metal',
                           dict(OWN, control='focus_rifle_rubber_control')),
    # the glowing surfaces keep the donor's display material as it is: first pass
    'focus_rifle_display': ('storm_beam_rifle_display', {}),
    'focus_rifle_display2': ('storm_beam_rifle_display', {}),
    'focus_rifle_illum_plasma': ('storm_beam_rifle_display', {}),
    'focus_rifle_indicator': ('storm_beam_rifle_display', {}),
    'focus_rifle_scope_alpha': ('storm_beam_rifle_display', {}),
}


def make_bitmaps(write):
    from PIL import Image
    dst = os.path.join(H4EK, 'data', PORT, 'bitmaps')
    d = Image.open(os.path.join(SOURCE_TEX, 'focus_rifle_diffuse.tiff'))
    n = Image.open(os.path.join(SOURCE_TEX, 'focus_rifle_normal.tiff'))
    spec = d.getchannel('A')                       # Reach: specular mask in diffuse alpha
    w, h = d.size
    out = {
        'focus_rifle_diff.tif': d.convert('RGB'),
        'focus_rifle_normal.tif': n.convert('RGB'),
        'focus_rifle_control.tif': Image.merge(
            'RGB', (spec, Image.new('L', (w, h), 150), spec.point(lambda v: v // 2))),
        'focus_rifle_rubber_control.tif': Image.merge(
            'RGB', (spec.point(lambda v: v // 4), Image.new('L', (w, h), 40),
                    Image.new('L', (w, h), 0))),
    }
    for name in out:
        print('bitmap source %s' % name)
    if not write:
        return
    os.makedirs(dst, exist_ok=True)
    for name, im in out.items():
        im.save(os.path.join(dst, name))
    r = subprocess.run([os.path.join(H4EK, 'tool.exe'), 'bitmaps', PORT + '\\bitmaps'],
                       cwd=H4EK, capture_output=True, text=True)
    print('\n'.join(l for l in r.stdout.splitlines() if 'imported as' in l))


def make_materials(write):
    for mat, (donor, repoint) in MATERIALS.items():
        src = os.path.join(H4EK, 'tags', DONOR_MATS + donor + '.material')
        dst = os.path.join(H4EK, 'tags', PORT, 'shaders', mat + '.material')
        print('%-26s <- %s  %s' % (mat, donor, sorted(repoint)))
        if not write:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        t = h3tag.Tag(dst)
        for suffix, own in repoint.items():
            n = t.repoint(DONOR_BMPS + suffix, PORT + '\\bitmaps\\' + own, 'bitm')
            if n != 1:
                raise SystemExit('%s: %s repointed %d times, expected 1' % (mat, suffix, n))
        t.save()
        if not h3tag.Tag(dst).check()[0]:
            raise SystemExit('%s no longer spans its file' % mat)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    make_bitmaps(a.write)
    make_materials(a.write)
    if not a.write:
        print('\n(dry run -- pass --write)')


if __name__ == '__main__':
    main()
