r"""Step 2 of a Halo 2 port: the source weapon's maps as Halo 2 bitmaps, and the shaders pointed at them.

Generalized from h2_saw_textures.py (the SAW, 2026-09-23 -- its notes stand: a Halo 2 bump map
is a HEIGHT map, so a source normal map is integrated back into heights; each new .bitmap tag is
SEEDED from a Bungie tag carrying the wanted settings and `tool bitmaps` re-imports into it).
The config's `textures` section:

    kind          'h4' (h4_bitmap decodes the source tags; other sources: the pilot adds a reader)
    src_dir       the source bitmap tags
    rel           kit-relative folder of the port's bitmaps (data + tags)
    shaders       kit-relative folder of the port's shaders
    seed_dir      where the seed tags live
    jobs          [(source tag, w, h, format, mips, port bitmap name, seed tag name)]
    bump_size, bump_gain
    shader_refs   [(shader file, the bitmap it names now, the port's bitmap)] -- repointed once
    lit           {'shader', 'seed', 'seed_map', 'map'}: a self-illuminated shader reseeded from
                  `seed` every run, its `seed_map` references repointed to `map` (every copy)
    report_rows   [(bitmap tag, label)] -- bump slope against the game's own

    python h2_port_textures.py <key> [--skip-decode]
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

B = os.sep
H2EK = h2_tagref.H2EK


def height_from_normal(img, gain):
    """A height map whose gradients are the normal map's, solved in the frequency domain
    (Poisson with FFTs), high-passed against the drift between atlas islands, then the
    relief driven by `gain` (measured against Bungie's own slope). See h2_saw_textures."""
    a = np.asarray(img, dtype=np.float32)[:, :, :2] / 255.0 * 2.0 - 1.0
    nx, ny = a[:, :, 0], a[:, :, 1]
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 1e-4, 1.0))
    p, q = -nx / nz, -ny / nz

    h, w = p.shape
    div = ((np.roll(p, -1, 1) - np.roll(p, 1, 1)) +
           (np.roll(q, -1, 0) - np.roll(q, 1, 0))) * 0.5
    fy = 2.0 * np.cos(2.0 * np.pi * np.fft.fftfreq(h)) - 2.0
    fx = 2.0 * np.cos(2.0 * np.pi * np.fft.fftfreq(w)) - 2.0
    denom = fy[:, None] + fx[None, :]
    denom[0, 0] = 1.0
    z = np.real(np.fft.ifft2(np.fft.fft2(div) / denom))

    blur = np.asarray(Image.fromarray(z.astype(np.float32), 'F')
                      .resize((max(1, w // 64), max(1, h // 64)), Image.BILINEAR)
                      .resize((w, h), Image.BILINEAR), dtype=np.float32)
    z -= blur
    lo, hi = np.percentile(z, 0.5), np.percentile(z, 99.5)
    z = (z - lo) / max(hi - lo, 1e-6)
    z = np.clip(0.5 + (z - 0.5) * gain, 0.0, 1.0)
    return Image.fromarray((z * 255.0).astype(np.uint8), 'L').convert('RGB')


def decode_all(t):
    import h4_bitmap
    data = os.path.join(H2EK, 'data', t['rel'])
    os.makedirs(data, exist_ok=True)
    for tag, w, h, fmt, mips, name, _seed in t['jobs']:
        img = h4_bitmap.decode(os.path.join(t['src_dir'], tag + '.bitmap'), w, h, fmt, mips)
        rough = h4_bitmap.roughness(img)
        if name.endswith('_bump'):
            out = height_from_normal(img, t['bump_gain']).resize(tuple(t['bump_size']), Image.LANCZOS)
        else:
            out = img.convert('RGB')
        path = os.path.join(data, name + '.tif')
        out.save(path, compression=None)
        print('   %-22s %-12s %dx%d  roughness %5.2f  -> %s'
              % (tag, out.mode, out.size[0], out.size[1], rough, os.path.basename(path)))


def seed_tags(t):
    tags = os.path.join(H2EK, 'tags', t['rel'])
    os.makedirs(tags, exist_ok=True)
    for _tag, _w, _h, _fmt, _mips, name, seed in t['jobs']:
        dest = os.path.join(tags, name + '.bitmap')
        if os.path.exists(dest):
            print('   %-22s already exists, left alone' % (name + '.bitmap'))
            continue
        shutil.copy(os.path.join(H2EK, 'tags', t['seed_dir'], seed + '.bitmap'), dest)
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


def report(t):
    out = os.path.join(os.environ.get('TEMP', '.'), '_h2bump')
    for tag, label in t.get('report_rows', ()):
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


def point(tag, cls, old, new, every=False):
    """Repoint unless it already points there (a re-run is harmless)."""
    have = h2_tagref.references(tag)
    if (cls, new) in have and (cls, old) not in have:
        print('   %-24s already names %s' % (os.path.basename(tag), new.split(B)[-1]))
        return
    h2_tagref.set_reference(tag, cls, old, new, every=every)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    t = ports_h2.get(argv[0], 'textures')
    if t.get('kind') != 'h4':
        raise SystemExit('textures kind %r has no reader yet -- the wave pilot adds it' % t.get('kind'))
    if '--skip-decode' not in argv:
        print('decoding the source maps:')
        decode_all(t)
    print('seeding the bitmap tags:')
    seed_tags(t)
    print('tool bitmaps:')
    run('bitmaps', t['rel'])
    print('pointing the shaders at them:')
    shaders = os.path.join(H2EK, 'tags', t['shaders'])
    for shader, old, new in t.get('shader_refs', ()):
        point(os.path.join(shaders, shader), 'bitm', old, new)
    lit = t.get('lit')
    if lit:
        dest = os.path.join(shaders, lit['shader'])
        shutil.copy(os.path.join(H2EK, 'tags', lit['seed']), dest)
        print('   %s reseeded from %s' % (lit['shader'], lit['seed'].split(B)[-1]))
        h2_tagref.set_reference(dest, 'bitm', lit['seed_map'], lit['map'], every=True)
    print('bump slope, against the game it has to sit in:')
    report(t)


if __name__ == '__main__':
    main()
