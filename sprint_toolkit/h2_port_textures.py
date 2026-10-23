r"""Step 2 of a Halo 2 port: the source weapon's maps as Halo 2 bitmaps, and the shaders pointed at them.

Generalized from h2_saw_textures.py (the SAW, 2026-09-23 -- its notes stand: a Halo 2 bump map
is a HEIGHT map, so a source normal map is integrated back into heights; each new .bitmap tag is
SEEDED from a Bungie tag carrying the wanted settings and `tool bitmaps` re-imports into it).
The config's `textures` section:

    kind          'h4' (h4_bitmap decodes the source tags) or 'h3' (h3_main: Halo 3's maps, reseeded shaders)
                  or 'h1' (h3_main with h1_decode: Halo 1's HCEEK maps; mode 'flat_bump' for its
                  bump-less shader_model -- the Flamethrower, S1)
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


def h1_decode(src, index=0):
    """A Halo 1 bitmap tag (HCEEK, reclaimer) -> (PIL image of bitmap `index`'s top mip, None), the
    shape h3_hud_art.decode hands back. DXT1/3/5 through PIL's BCn decoder; 32-bit formats are
    stored B, G, R, A (x8r8g8b8: alpha forced opaque); a8 / y8 / ay8 / a8y8 one or two bytes."""
    import port_env  # noqa: F401
    from reclaimer.hek.defs.bitm import bitm_def
    path = os.path.join(os.path.dirname(H2EK), 'HCEEK', 'tags', src)
    if not path.endswith('.bitmap'):
        path += '.bitmap'
    d = bitm_def.build(filepath=path).data.tagdata
    b = d.bitmaps.STEPTREE[index]
    w, h, fmt = b.width, b.height, b.format.enum_name
    raw = bytes(d.processed_pixel_data.data)[b.pixels_offset:]
    if fmt in ('dxt1', 'dxt3', 'dxt5'):
        n = {'dxt1': 1, 'dxt3': 2, 'dxt5': 3}[fmt]
        size = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * (8 if n == 1 else 16)
        img = Image.frombytes('RGBA', (w, h), raw[:size], 'bcn', n)
    elif fmt in ('a8r8g8b8', 'x8r8g8b8'):
        a = np.frombuffer(raw[:w * h * 4], np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]].copy()
        if fmt == 'x8r8g8b8':
            a[:, :, 3] = 255
        img = Image.fromarray(a, 'RGBA')
    elif fmt in ('a8', 'y8', 'ay8'):
        g = np.frombuffer(raw[:w * h], np.uint8).reshape(h, w)
        img = Image.fromarray(np.dstack([g, g, g, g if fmt != 'y8' else np.full_like(g, 255)]), 'RGBA')
    elif fmt == 'a8y8':
        a = np.frombuffer(raw[:w * h * 2], np.uint8).reshape(h, w, 2)
        img = Image.fromarray(np.dstack([a[:, :, 0]] * 3 + [a[:, :, 1]]), 'RGBA')
    else:
        raise SystemExit('Halo 1 bitmap format %s (%s) not handled' % (fmt, src))
    return img, None


def h3_main(t, argv):
    """kind 'h3' (the Assault Rifle, wave-A pilot, 2026-10-20): Halo 3's own maps decoded from
    the H3EK tags (h3_hud_art.decode: any format, the top mip), a Halo 3 bump map being a
    NORMAL map integrated into Halo 2's HEIGHT map (height_from_normal, as the SAW's); every
    shader RESEEDED each run from a Bungie Halo 2 shader carrying the template wanted and its
    bitmap references repointed (every copy) -- so a re-run is the same result.

        bitmaps   [(H3EK bitmap tag, port bitmap name, Bungie seed bitmap tag, 'color' | 'bump' |
                    'bump_snorm' (a signed DXN normal map, the AR's) | 'color_premul' |
                    ('tint', (r, g, b), dilate px) (a grey illum mask coloured, the Spiker's) |
                    ('alpha_from', source, channel) (another map's channel as alpha) | 'flat_bump'
                    (no source: a flat height) | ('gradient', 'u'|'v', reverse[, (lo, hi)]) (no
                    source: a meter's reveal ramp over a UV window) | ('mask_from', source,
                    channel) (the colour x another map's channel: a self-illum map) | ('sprite', k[,
                    then]) (one sprite of a Halo 1 sprite sheet),
                    (w, h) or None = the source's size)]
        shaders   [(port shader name, Bungie seed shader tag, {seed bitmap['#n']: port bitmap or
                    another tag})] -- a seed bitmap left out of the map stays Bungie's; '#n' moves
                    only its n-th copy
        rel, shaders_dir, bump_gain, report_rows
        string_ids  {port shader name: {old string id: new}} renamed after the reseed
    """
    import h3_hud_art
    decode = h1_decode if t.get('kind') == 'h1' else h3_hud_art.decode
    data = os.path.join(H2EK, 'data', t['rel'])
    tags = os.path.join(H2EK, 'tags', t['rel'])
    os.makedirs(data, exist_ok=True)
    os.makedirs(tags, exist_ok=True)
    if '--skip-decode' not in argv:
        print('decoding the Halo 3 maps:')
        for src, name, _seed, mode, size in t['bitmaps']:
            if mode == 'flat_bump':
                # a source with NO bump map (Halo 1's shader_model): a flat height, Halo 1's look
                out = Image.new('RGB', tuple(size or (64, 64)), (128, 128, 128))
                out.save(os.path.join(data, name + '.tif'), compression=None)
                print('   %-40s flat height %dx%d -> %s.tif' % ('(none)', out.size[0], out.size[1], name))
                continue
            if isinstance(mode, tuple) and mode[0] == 'gradient':
                # ('gradient', 'u' | 'v', reverse[, (lo, hi)]): no source -- a linear ramp 0 -> 255
                # along one texture axis (only over the window lo..hi of it, the part the quad's UVs
                # sample), in every channel: a METER's reveal map (Halo 2's meter shader shows a texel
                # while the meter value passes its level; the Flamethrower's heat gauge)
                w, h = tuple(size or (32, 128))
                lo, hi = mode[3] if len(mode) > 3 else (0.0, 1.0)
                at = np.linspace(0.0, 1.0, h if mode[1] == 'v' else w)
                ramp = np.clip((at - lo) / (hi - lo), 0.0, 1.0) * 255.0
                if len(mode) > 2 and mode[2]:
                    ramp = 255.0 - ramp
                g = np.tile(ramp[:, None], (1, w)) if mode[1] == 'v' else np.tile(ramp[None, :], (h, 1))
                # a 5th value 'alpha': white RGB, the ramp in ALPHA only -- the layout of Bungie's PR
                # gauge meter_map (its fill order in alpha; the colour is the shader's), boot 23
                rgb = np.full_like(g, 255.0) if len(mode) > 4 and mode[4] == 'alpha' else g
                out = Image.fromarray(np.dstack([rgb, rgb, rgb, g]).astype(np.uint8), 'RGBA')
                out.save(os.path.join(data, name + '.tif'), compression=None)
                print('   %-40s %s gradient %dx%d -> %s.tif' % ('(none)', mode[1], w, h, name))
                continue
            img, _ = decode(src)
            if isinstance(mode, tuple) and mode[0] == 'sprite':
                # ('sprite', k[, then mode]): sprite k of a Halo 1 sprite sheet's first sequence -- the
                # Flamethrower's flame contrail drawn with Halo 1's own `burning flame` sprite
                import port_env  # noqa: F401
                from reclaimer.hek.defs.bitm import bitm_def
                sheet = bitm_def.build(filepath=os.path.join(os.path.dirname(H2EK), 'HCEEK', 'tags',
                                                             src + '.bitmap')).data.tagdata
                sp = sheet.sequences.STEPTREE[0].sprites.STEPTREE[mode[1]]
                img, _ = decode(src, sp.bitmap_index)
                w0, h0 = img.size
                img = img.crop((int(sp.left_side * w0), int(sp.top_side * h0),
                                int(sp.right_side * w0), int(sp.bottom_side * h0)))
                mode = mode[2] if len(mode) > 2 else 'color'
            if mode in ('bump', 'bump_snorm'):
                if mode == 'bump_snorm':
                    # Halo 3's DXN (BC5) normals are SIGNED: decoded as unsigned bytes they sit
                    # at 0 and 255 for a flat surface (measured on the AR's bump); re-centre
                    a = np.asarray(img.convert('RGB')).astype(np.int16)
                    a = np.where(a >= 128, a - 256, a)[:, :, :2] / 127.0
                    a = np.clip((a + 1.0) * 127.5, 0, 255).astype(np.uint8)
                    img = Image.fromarray(np.dstack([a, np.full(a.shape[:2], 255, np.uint8)]), 'RGB')
                out = height_from_normal(img.convert('RGB'), t.get('bump_gain', 2.2))
            elif isinstance(mode, tuple) and mode[0] == 'tint':
                # ('tint', (r, g, b) 0..1, dilate px): a Halo 3 GREY self-illumination mask
                # coloured as its shader colours it (Halo 2's self_illum_map is drawn as it is),
                # thin lines grown by `dilate` px (no bloom; Halo 1's A5 rule) -- the Spike Rifle
                g = np.asarray(img.convert('L')).astype(np.float32)
                if mode[2]:
                    from PIL import ImageFilter
                    g = np.asarray(Image.fromarray(g.astype(np.uint8), 'L').filter(
                        ImageFilter.MaxFilter(2 * mode[2] + 1))).astype(np.float32)
                if len(mode) > 3 and mode[3]:
                    # a 4th value = SOFT radius (the Spiker, Armed boot: grown spots read as 'crosses
                    # taped on'): each spot a radial glow -- a gaussian of the mask, renormalised so
                    # its core keeps the mask's peak, then max'ed with the mask (the core stays sharp)
                    from PIL import ImageFilter
                    peak = g.max()
                    b = np.asarray(Image.fromarray(g.astype(np.uint8), 'L').filter(
                        ImageFilter.GaussianBlur(mode[3]))).astype(np.float32)
                    if b.max() > 0:
                        b = np.clip(b * (peak / b.max()) * 1.5, 0, 255)
                    g = np.maximum(g, b)
                rgb = np.dstack([g * c for c in mode[1]])
                out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')
            elif isinstance(mode, tuple) and mode[0] == 'alpha_from':
                # ('alpha_from', other source, channel): the colour with ANOTHER map's channel as
                # its alpha -- Halo 1's multipurpose RED (the reflection mask) as the specular mask
                # a Halo 2 diffuse carries in alpha (the Flamethrower, S1)
                other, _ = decode(mode[1])
                ch = np.asarray(other.convert('RGBA').resize(img.size, Image.LANCZOS))[:, :, mode[2]]
                rgb = np.asarray(img.convert('RGB'))
                out = Image.fromarray(np.dstack([rgb, ch]).astype(np.uint8), 'RGBA')
            elif isinstance(mode, tuple) and mode[0] == 'mask_from':
                # ('mask_from', other source, channel): the colour x ANOTHER map's channel -- a
                # self-illumination map from Halo 1's multipurpose GREEN (its self-illum mask): only
                # the lit parts keep their colour (the Flamethrower's tank window and lights)
                other, _ = decode(mode[1])
                ch = np.asarray(other.convert('RGBA').resize(img.size, Image.LANCZOS))[:, :, mode[2]]
                rgb = np.asarray(img.convert('RGB')).astype(np.float32) * (ch[:, :, None] / 255.0)
                out = Image.fromarray(rgb.astype(np.uint8), 'RGB')
            elif isinstance(mode, tuple) and mode[0] == 'alpha_window':
                # ('alpha_window', lo, hi): the colour with its ALPHA zeroed outside the rows lo..hi
                # (fractions of the height, top = 0) -- a meter's SHAPE cut where the fill must stop
                # (the Flamethrower's heat bar, boot 24: 'goes a bit above the display border')
                a = np.asarray(img.convert('RGBA')).copy()
                rows = np.linspace(0.0, 1.0, a.shape[0])
                a[(rows < mode[1]) | (rows > mode[2]), :, 3] = 0
                out = Image.fromarray(a, 'RGBA')
            elif mode == 'color_premul':
                # for an ADDITIVE shader: colour x alpha, so a transparent texel adds nothing
                # (the AR's holo display, boot 2: an opaque template drew every layer's square)
                a = np.asarray(img.convert('RGBA')).astype(np.float32)
                a[:, :, :3] *= a[:, :, 3:4] / 255.0
                out = Image.fromarray(a.astype(np.uint8), 'RGBA')
            else:
                out = img.convert('RGBA' if img.mode == 'RGBA' else 'RGB')
            if size:
                out = out.resize(tuple(size), Image.LANCZOS)
            out.save(os.path.join(data, name + '.tif'), compression=None)
            print('   %-40s %s %dx%d -> %s.tif' % (src.split(B)[-1], out.mode, out.size[0],
                                                   out.size[1], name))
    print('seeding the bitmap tags:')
    for _src, name, seed, _mode, _size in t['bitmaps']:
        dest = os.path.join(tags, name + '.bitmap')
        if os.path.exists(dest):
            print('   %-28s already exists, left alone' % (name + '.bitmap'))
            continue
        shutil.copy(os.path.join(H2EK, 'tags', seed + '.bitmap'), dest)
        print('   %-28s seeded from %s' % (name + '.bitmap', seed))
    print('tool bitmaps:')
    run('bitmaps', t['rel'])
    print('the shaders (reseeded, repointed):')
    sdir = os.path.join(H2EK, 'tags', t['shaders_dir'])
    os.makedirs(sdir, exist_ok=True)
    for name, seed, refs in t['shaders']:
        dest = os.path.join(sdir, name + '.shader')
        shutil.copy(os.path.join(H2EK, 'tags', seed + '.shader'), dest)
        print('   %-28s from %s' % (name + '.shader', seed))
        have = h2_tagref.references(dest)
        for old, new in refs.items():
            # 'path#n': only the n-th copy (a seed naming one bitmap as base AND self-illum map)
            old, _h, nth = old.partition('#')
            if ('bitm', old) in have:
                if nth:
                    h2_tagref.set_reference(dest, 'bitm', old, new, nth=int(nth))
                else:
                    h2_tagref.set_reference(dest, 'bitm', old, new, every=True)
                have = h2_tagref.references(dest)
        if t.get('string_ids', {}).get(name):
            # a reseeded shader's string ids renamed (its animation INPUT: the Flamethrower's hundreds
            # digit reads `primary_ammunition_hundreds`, which no Halo 2 weapon exports -> digit 0)
            import h2_stringid
            for old, new in t['string_ids'][name].items():
                if len(old) != len(new):
                    print('      ' + h2_stringid.rename(dest, {old: new}, write=True))
                    continue
                # SAME length: only the pooled string changes (no length byte to find -- the
                # rename's length-field search can be ambiguous, as in BR `tens`: 5 candidates);
                # kept when tool's export shows exactly that string id changed
                d = open(dest, 'rb').read()
                if d.count(old.encode()) != 1:
                    raise SystemExit('%s: %d pooled copies of %s' % (name, d.count(old.encode()), old))
                before = h2_stringid.string_ids(h2_stringid.export(dest))
                open(dest, 'wb').write(d.replace(old.encode(), new.encode()))
                after = h2_stringid.string_ids(h2_stringid.export(dest))
                diff = [(a, b) for a, b in zip(before, after) if a != b]
                if len(before) != len(after) or len(diff) != 1 or diff[0][1][2] != new:
                    open(dest, 'wb').write(d)
                    raise SystemExit('%s: renaming %s changed %s; restored' % (name, old, diff))
                print('      %s: string id %s -> %s' % (name, old, new))
    print('bump slope, against the game it has to sit in:')
    report(t)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    t = ports_h2.get(argv[0], 'textures')
    if t.get('kind') in ('h3', 'h1'):
        return h3_main(t, argv)
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
