r"""Give the Halo 2 SAW its own skin: the Halo 4 maps, imported as Halo 2 bitmaps.

The port arrives from `saw_to_jms_h2.py` wearing copies of `gpmg_gun.shader`, which is
itself a hand-me-down -- the cut GPMG borrows the Warthog turret's textures. This puts
the SAW's own maps on it.

**Halo 2 bump maps are HEIGHT maps.** Bungie's `h_turret_mp_gun_bump` has
`usage = height map` and `bump height = 4.0`, and tool turns that into the engine's
`p8-bump`. Halo 4 ships a tangent-space NORMAL map instead, so it has to be integrated
back into a height field -- see `height_from_normal`. Feeding the normal map straight in
would import it as if its red and green channels were heights and light the gun wrongly.

**The settings live in the tag, not in the import.** A .bitmap tag created from nothing
comes out `usage = default`, which is wrong for a bump map, and there is no way to set
the field short of editing bytes. So each new bitmap STARTS as a copy of the Bungie tag
that already has the settings wanted -- the turret's gun and gun_bump -- and
`tool bitmaps` re-imports into it, keeping them. That also keeps the port honest about
where a setting came from.

    python h2_saw_textures.py [--skip-decode]

Decoding is the slow part (three 2048x1024 maps, one of them integrated), so a re-run
that only needs the import and the shader edits can skip it.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h4_bitmap
import h2_tagref
import numpy as np
from PIL import Image

B = os.sep
H2EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
H4EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H4EK')
SRC = os.path.join(H4EK, 'tags', 'objects', 'weapons', 'rifle', 'storm_lmg', 'bitmaps',
                   'storm_lmg_default')
REL = B.join(['objects', 'weapons', 'rifle', 'saw', 'bitmaps'])
DATA = os.path.join(H2EK, 'data', REL)
TAGS = os.path.join(H2EK, 'tags', REL)
SHADERS = os.path.join(H2EK, 'tags', 'objects', 'weapons', 'rifle', 'saw', 'shaders')
TURRET = os.path.join(H2EK, 'tags', 'objects', 'weapons', 'fixed', 'h_turret_mp',
                      'bitmaps')

#: Halo 2 stores a bump map as `p8-bump`, a 256-entry palette of normals, and it only
#: reaches for that format at a modest size -- a 2048x1024 height map came back as
#: x8r8g8b8 instead, eleven megabytes for one weapon, where Bungie's whole turret bump
#: is 256x256. Half the diffuse's resolution in each axis keeps the atlas layout and the
#: format.
BUMP_SIZE = (512, 256)

#: How hard the relief is driven. Integrating Halo 4's normal map and importing it as it
#: came out gave a bump map with about HALF the slope of Halo 2's own -- standard
#: deviation 8/12 per channel against the SMG's 21/27 -- so the gun read as too smooth
#: for the game around it. The gain is set by measuring against Bungie's, not by eye:
#: `--report` prints both.
BUMP_GAIN = 2.2

#: (H4 tag, width, height, format, mips, what it becomes, which Bungie tag seeds it)
JOBS = [('storm_lmg_diff', 2048, 1024, 'dxt1', 11, 'saw_gun', 'h_turret_mp_gun'),
        ('storm_lmg_normal', 2048, 1024, 'dxn', 11, 'saw_gun_bump',
         'h_turret_mp_gun_bump'),
        ('storm_lmg_display_diff', 64, 128, 'dxt5', 1, 'saw_display',
         'h_turret_mp_gun')]

#: The display is the SAW's ammo counter -- an orange ladder that GLOWS in Halo 4, and
#: `tex_bump` has no way to say so. Halo 2's own answer is `tex_bump_illum`, and the
#: shotgun's lit sight is already built on it with the one map serving as both base and
#: self-illumination, so the display shader is a clone of that rather than of the GPMG's.
#: It also has no bump_map parameter at all, which is the right answer for a quad whose
#: UVs address its own little texture and not the gun's atlas.
DISPLAY_SEED = os.path.join(H2EK, 'tags', 'objects', 'weapons', 'rifle', 'shotgun',
                            'shaders', 'shotgun_light.shader')
DISPLAY_SEED_MAP = B.join(['objects', 'weapons', 'rifle', 'shotgun', 'bitmaps',
                           'illum_sights'])

#: what the shaders point at afterwards. The GPMG's shader names the turret's maps, and
#: both of its paths are distinct strings, so each swap is unambiguous.
TURRET_BASE = B.join(['objects', 'weapons', 'fixed', 'h_turret_mp', 'bitmaps',
                      'h_turret_mp_gun'])
TURRET_BUMP = TURRET_BASE + '_bump'


def height_from_normal(img):
    """A height map whose gradients are the normal map's, solved in the frequency domain.

    A tangent-space normal gives the surface's slope at every texel; height is its
    integral, and integrating a 2D gradient field means solving Poisson's equation. Done
    with FFTs that is a few lines and exact up to the constant term.

    The result is high-passed afterwards. An atlas is dozens of unconnected islands, and
    Poisson has no way to know that, so it drifts slowly across the sheet and one island
    ends up sitting far above another. Only the local detail is wanted -- the shape is
    the model's job -- so the drift is subtracted back out.
    """
    a = np.asarray(img, dtype=np.float32)[:, :, :2] / 255.0 * 2.0 - 1.0
    nx, ny = a[:, :, 0], a[:, :, 1]
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 1e-4, 1.0))
    p, q = -nx / nz, -ny / nz

    h, w = p.shape
    # divergence of the gradient field, by central differences
    div = ((np.roll(p, -1, 1) - np.roll(p, 1, 1)) +
           (np.roll(q, -1, 0) - np.roll(q, 1, 0))) * 0.5
    fy = 2.0 * np.cos(2.0 * np.pi * np.fft.fftfreq(h)) - 2.0
    fx = 2.0 * np.cos(2.0 * np.pi * np.fft.fftfreq(w)) - 2.0
    denom = fy[:, None] + fx[None, :]
    denom[0, 0] = 1.0                       # the constant term is arbitrary
    z = np.real(np.fft.ifft2(np.fft.fft2(div) / denom))

    blur = np.asarray(Image.fromarray(z.astype(np.float32), 'F')
                      .resize((max(1, w // 64), max(1, h // 64)), Image.BILINEAR)
                      .resize((w, h), Image.BILINEAR), dtype=np.float32)
    z -= blur
    lo, hi = np.percentile(z, 0.5), np.percentile(z, 99.5)
    z = (z - lo) / max(hi - lo, 1e-6)
    z = np.clip(0.5 + (z - 0.5) * BUMP_GAIN, 0.0, 1.0)
    # RGB, not L: tool writes the colour plate straight out of the source, and Bungie's
    # plates are 24-bit.
    return Image.fromarray((z * 255.0).astype(np.uint8), 'L').convert('RGB')


def decode_all():
    os.makedirs(DATA, exist_ok=True)
    for tag, w, h, fmt, mips, name, _seed in JOBS:
        img = h4_bitmap.decode(os.path.join(SRC, tag + '.bitmap'), w, h, fmt, mips)
        rough = h4_bitmap.roughness(img)
        if name.endswith('_bump'):
            out = height_from_normal(img).resize(BUMP_SIZE, Image.LANCZOS)
        else:
            out = img.convert('RGB')
        path = os.path.join(DATA, name + '.tif')
        out.save(path, compression=None)
        print('   %-22s %-12s %dx%d  roughness %5.2f  -> %s'
              % (tag, out.mode, out.size[0], out.size[1], rough, os.path.basename(path)))


def seed_tags():
    """Start each bitmap tag from the Bungie one whose settings it should inherit."""
    os.makedirs(TAGS, exist_ok=True)
    for _tag, _w, _h, _fmt, _mips, name, seed in JOBS:
        dest = os.path.join(TAGS, name + '.bitmap')
        if os.path.exists(dest):
            print('   %-22s already exists, left alone' % (name + '.bitmap'))
            continue
        shutil.copy(os.path.join(TURRET, seed + '.bitmap'), dest)
        print('   %-22s seeded from %s' % (name + '.bitmap', seed))


def run(*args):
    p = subprocess.run([os.path.join(H2EK, 'tool.exe')] + list(args), cwd=H2EK,
                       capture_output=True, text=True)
    text = (p.stdout or '') + (p.stderr or '')
    for line in text.replace('\r', '\n').split('\n'):
        line = ' '.join(line.split())
        if line and '%' not in line and 'from scratch' not in line:
            print('   | %s' % line)
    return text


def report():
    """Slope of each bump map, ours against Bungie's -- the check that sets BUMP_GAIN."""
    out = os.path.join(os.environ.get('TEMP', '.'), '_h2bump')
    rows = [(B.join([REL, 'saw_gun_bump']), 'the port'),
            (B.join(['objects', 'weapons', 'rifle', 'smg', 'bitmaps', 'smg_bump']),
             'Bungie SMG'),
            (B.join(['objects', 'weapons', 'fixed', 'h_turret_mp', 'bitmaps',
                     'h_turret_mp_gun_bump']), 'Bungie turret')]
    for tag, label in rows:
        subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', tag, out],
                       cwd=H2EK, capture_output=True, text=True)
        name = out + tag.split(B)[-1] + '_00_00.tga'
        if not os.path.exists(name):
            print('   %-14s (could not export)' % label)
            continue
        a = np.asarray(Image.open(name).convert('RGB'), dtype=float)
        print('   %-14s %-11s slope %s'
              % (label, '%dx%d' % (a.shape[1], a.shape[0]),
                 [round(float(a[:, :, i].std()), 1) for i in range(3)]))


def main():
    if '--skip-decode' not in sys.argv:
        print('decoding the Halo 4 maps:')
        decode_all()
    print('seeding the bitmap tags:')
    os.makedirs(TAGS, exist_ok=True)
    seed_tags()
    print('tool bitmaps:')
    run('bitmaps', REL)
    print('pointing the shaders at them:')
    base = B.join([REL, 'saw_gun'])
    bump = B.join([REL, 'saw_gun_bump'])
    display = B.join([REL, 'saw_display'])
    gun = os.path.join(SHADERS, 'saw_gun.shader')
    h2_tagref.set_reference(gun, 'bitm', TURRET_BASE, base)
    h2_tagref.set_reference(gun, 'bitm', TURRET_BUMP, bump)

    lit = os.path.join(SHADERS, 'saw_display.shader')
    shutil.copy(DISPLAY_SEED, lit)
    print('   saw_display.shader reseeded from the shotgun lit sight')
    h2_tagref.set_reference(lit, 'bitm', DISPLAY_SEED_MAP, display, every=True)
    print('bump slope, against the game it has to sit in:')
    report()


if __name__ == '__main__':
    main()
