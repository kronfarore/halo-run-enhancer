r"""A Halo 3 weapon's geometry and look into Halo 1 (HCEEK): bitmaps, shader_model, world and
first-person gbxmodel -- generic, per weapon (PORTING steps 1 + 2).

  bitmaps   Halo 3's own maps decoded from the H3EK tags (h3_hud_art.decode: the largest
            tgda chunk; dxt / a8r8g8b8), written as TIFFs into HCEEK data and imported with
            `tool bitmaps`. Halo 1 needs a MULTIPURPOSE map or the gun renders white
            (PORTING, SAW): R = reflection mask (Halo 3's base-map alpha, its specular
            mask), G = self-illumination (Halo 3's illum map), B 0, A 255.
  shader    a copy of a Halo 1 shader_model (`template`) with those two maps and the glow
            colour of Halo 3's illum map.
  models    h3_rm_to_jms.py (Halo 3 nodes renamed `frame <name>`, strips unrolled), then
            `tool model` -- the world model and the first-person model.

    python h1_h3_weapon_model.py sentinel_beam [--skip-bitmaps]
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.soso import soso_def  # noqa: E402
from reclaimer.model.jms.file import write_jms  # noqa: E402
import h3_hud_art  # noqa: E402
import h3_rm_to_jms  # noqa: E402
import ports_h1  # noqa: E402

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
TAGS = os.path.join(HCEEK, 'tags')
B = '\\'
# per weapon: ports_h1/<weapon>.py, section 'model' (dir, world / fp H3 render models,
# world_name, shaders {name: (base map, illum map)}, template shader)
WEAPONS = ports_h1.section('model')


def tool(*args):
    r = subprocess.run([os.path.join(HCEEK, 'tool.exe')] + list(args), cwd=HCEEK,
                       capture_output=True, text=True, errors='replace')
    return r.stdout + r.stderr


def material_islands(jm, material):
    """[(triangles, verts)] of one material's connected pieces (shared positions) in a JMS --
    the Beam Rifle's gems: five UV islands, each a small square of the texture."""
    names = [m.name for m in jm.materials]
    if material not in names:
        return []
    si = names.index(material)
    tris = [t for t in jm.tris if t.shader == si]
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            a = parent[a]
        return a

    def key(v):
        x = jm.verts[v]
        return (round(x.pos_x, 2), round(x.pos_y, 2), round(x.pos_z, 2))
    for t in tris:
        ks = [key(v) for v in (t.v0, t.v1, t.v2)]
        for k in ks[1:]:
            parent[find(k)] = find(ks[0])
    isl = {}
    for t in tris:
        isl.setdefault(find(key(t.v0)), []).append(t)
    return [(ts, [jm.verts[v] for t in ts for v in (t.v0, t.v1, t.v2)]) for ts in isl.values()]


def lit_pieces(jm, material, illum, threshold=16):
    """[(triangles, verts)] -- each triangle of `material` whose UVs land on a LIT texel of
    the Halo 3 illum mask `illum` (sampled at 7 barycentric points, both v conventions; the
    fp_material_view test). The Spike Rifle's glow: Halo 3 lights a few tiny spots inside
    the big body / blade materials, so a material island would light far too much."""
    img, _ = h3_hud_art.decode(illum)
    a = np.array(img)[..., :3].max(axis=2)
    H, W = a.shape
    names = [m.name for m in jm.materials]
    if material not in names:
        return []
    si = names.index(material)
    out = []
    for t in jm.tris:
        if t.shader != si:
            continue
        vs = [jm.verts[i] for i in (t.v0, t.v1, t.v2)]
        uv = np.array([(v.tex_u % 1.0, v.tex_v % 1.0) for v in vs])
        best = 0
        for wt in ((1 / 3., 1 / 3., 1 / 3.), (.6, .2, .2), (.2, .6, .2), (.2, .2, .6), (1, 0, 0), (0, 1, 0), (0, 0, 1)):
            u, v = (np.array(wt)[:, None] * uv).sum(0)
            for y in (v, 1 - v):
                best = max(best, a[min(H - 1, int(y * H)), min(W - 1, int(u * W))])
        if best > threshold:
            out.append(([t], vs))
    return out


def drop_materials(jm, names):
    """Triangles of the named materials removed, materials renumbered (the Spike Rifle's FP
    model: 20 triangles of Halo 3's `shaders\\invalid` -- a flat cap at both barrel ends,
    x 15.8 cm -- that Halo 3 does not draw)."""
    mats = [m.name for m in jm.materials]
    drop = {i for i, n in enumerate(mats) if n in names}
    if not drop:
        return
    n0 = len(jm.tris)
    jm.tris = [t for t in jm.tris if t.shader not in drop]
    keep = [i for i in range(len(mats)) if i not in drop]
    remap = {old: new for new, old in enumerate(keep)}
    for t in jm.tris:
        t.shader = remap[t.shader]
    jm.materials = [jm.materials[i] for i in keep]
    print('   dropped %d triangle(s) of %s' % (n0 - len(jm.tris), sorted(mats[i] for i in drop)))


def bitmaps(w):
    out = os.path.join(HCEEK, 'data', w['dir'], 'bitmaps')
    os.makedirs(out, exist_ok=True)
    glow = {}
    for name, (base, illum) in w['shaders'].items():
        b, _ = h3_hud_art.decode(base)
        rgba = np.array(b)
        diff = rgba.copy()
        diff[..., 3] = 255
        Image.fromarray(diff).save(os.path.join(out, name + '_diff.tif'))
        mp = np.zeros_like(rgba)
        mp[..., 0] = rgba[..., 3]                                 # reflection = specular mask
        mp[..., 3] = 255
        if illum:
            il, _ = h3_hud_art.decode(illum)
            il = il.resize(b.size, Image.LANCZOS)
            a = np.array(il)[..., :3].astype(np.float64)
            g = Image.fromarray(np.clip(a.max(axis=2), 0, 255).astype(np.uint8))
            if w.get('illum_dilate'):
                # thin glow lines THICKENED (the Carbine, test 2: 'the side strips barely
                # glow'): Halo 3 blooms them, Halo 1 has no bloom
                from PIL import ImageFilter
                g = g.filter(ImageFilter.MaxFilter(2 * w['illum_dilate'] + 1))
            mp[..., 1] = np.array(g)
            lit = a[a.max(axis=2) > 64]
            if isinstance(w.get('glow'), dict) and name in w['glow']:
                # a colour PER SHADER (the Spike Rifle: Halo 3's self_illum_color differs --
                # the body blue, the grip and blades hot orange, on one shared grey mask)
                glow[name] = tuple(w['glow'][name])
            elif w.get('glow') and not isinstance(w['glow'], dict):   # a set colour
                glow[name] = tuple(w['glow'])
            elif len(lit):                                        # the glow's own colour
                c = lit.mean(axis=0)
                glow[name] = tuple(float(x) for x in c / c.max())
        Image.fromarray(mp).save(os.path.join(out, name + '_mp.tif'))
    # a SOLID GLOW material (`glow_shaders` {name: rgb}; the Beam Rifle's `luminous` slits,
    # an animated energy field in Halo 3 on multiplayer bitmaps): a flat diffuse in its
    # colour and a multipurpose map fully self-lit (G 255)
    for name, spec in w.get('glow_shaders', {}).items():
        rgb = spec['rgb'] if isinstance(spec, dict) else spec
        if isinstance(spec, dict) and spec.get('additive'):
            # an ADDITIVE glow (the Beam Rifle, test 4: 'it looks like plain paint'): Halo 1
            # draws light as additive transparency (the needler's needles, the sword blade)
            if spec.get('mask'):
                # a GLOW TEXTURE from Halo 3's own mask (the Beam Rifle, test 5: 'still not
                # really glowing' -- a flat colour reads as paint even additive). Halo 3's
                # luminous energy field = `mask` (alpha: bright crackles fading to dark);
                # brightness v -> the colour up to v 0.5, then towards WHITE (a hot core)
                img, _ = h3_hud_art.decode(spec['mask'])
                if spec.get('mask_channel') == 'rgb':
                    # a GREY illum mask (the Spike Rifle's brute_bolter_illum: alpha 255
                    # everywhere, the light in RGB), thickened `dilate` px (no bloom in Halo 1)
                    from PIL import ImageFilter
                    g = Image.fromarray(np.array(img)[..., :3].max(axis=2).astype(np.uint8))
                    if spec.get('dilate'):
                        g = g.filter(ImageFilter.MaxFilter(2 * spec['dilate'] + 1))
                    v = np.array(g.resize((256, 256), Image.LANCZOS)).astype(np.float64) / 255.0
                else:
                    v = np.array(img.resize((256, 256), Image.LANCZOS))[..., 3].astype(np.float64) / 255.0
                v = np.clip(v * spec.get('gain', 1.0), 0.0, 1.0)
                lo = np.clip(v * 2.0, 0.0, 1.0)[..., None] * np.array(rgb)[None, None, :]
                hot = np.clip(v * 2.0 - 1.0, 0.0, 1.0)[..., None]
                c = lo * (1 - hot) + hot
                col = np.zeros((256, 256, 4), np.uint8)
                col[..., :3] = np.round(c * 255)
                col[..., 3] = 255
            elif spec.get('islands'):
                # each UV ISLAND of the material a radial glow (the Beam Rifle's gems, test
                # 6: flat white-pink did not glow): white-hot centre falling off to the colour
                # and dark at the island's edge. Painted at v and 1 - v (both conventions;
                # the unused copy is never sampled)
                N = 1024
                v = np.zeros((N, N))
                yy, xx = np.mgrid[0:N, 0:N]
                for key in ('world', 'fp'):
                    jm, _rm = h3_rm_to_jms.convert(w[key], markers=w.get('markers'))
                    for _ts, vs in material_islands(jm, spec.get('islands_of', name)):
                        U = np.array([(x.tex_u % 1.0, x.tex_v % 1.0) for x in vs])
                        (u0, v0), (u1, v1) = U.min(0), U.max(0)
                        for vv0, vv1 in ((v0, v1), (1 - v1, 1 - v0)):
                            cx, cy = (u0 + u1) / 2 * N, (vv0 + vv1) / 2 * N
                            r = max(u1 - u0, vv1 - vv0) / 2 * N * spec.get('radius', 1.15) + 1
                            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
                            v = np.maximum(v, np.clip(1 - d, 0, 1) ** spec.get('falloff', 0.6))
                v = v * spec.get('gain', 1.0)
                lo = np.clip(v * 2.0, 0.0, 1.0)[..., None] * np.array(rgb)[None, None, :]
                hot = (np.clip(v * 2.0 - 1.0, 0.0, 1.0) if spec.get('hot', True) else np.zeros_like(v))[..., None]
                c = lo * (1 - hot) + hot
                col = np.zeros((N, N, 4), np.uint8)
                col[..., :3] = np.round(c * 255)
                col[..., 3] = 255
            else:
                col = np.zeros((16, 16, 4), np.uint8)
                col[..., :3] = [int(round(c * 255)) for c in rgb]
                col[..., 3] = 255
            Image.fromarray(col).save(os.path.join(out, name + '_glow.tif'))
            continue
        col = np.zeros((16, 16, 4), np.uint8)
        col[..., :3] = [int(round(c * 255)) for c in rgb]
        col[..., 3] = 255
        Image.fromarray(col).save(os.path.join(out, name + '_diff.tif'))
        mp = np.zeros((16, 16, 4), np.uint8)
        mp[..., 1] = mp[..., 3] = 255
        Image.fromarray(mp).save(os.path.join(out, name + '_mp.tif'))
        glow[name] = tuple(rgb)
    log = tool('bitmaps', w['dir'] + B + 'bitmaps')
    print('   tool bitmaps: %s' % (log.strip().splitlines()[-1] if log.strip() else 'ok'))
    return glow


def numeric(w):
    """An AMMO COUNTER on the gun (the BR, 2026-10-07): each `numeric` material gets a copy
    of a Halo 1 numeric shader_transparent_chicago (the AR's `numbers`: flag numeric, its
    digit bitmaps a 10-bitmap sequence) with the counter limit set; the digit PLACE is the
    gbxmodel shader entry's permutation index (the AR: 0 and 1), set after `tool model`."""
    from reclaimer.hek.defs.schi import schi_def
    N = w['numeric']
    out = os.path.join(TAGS, w['dir'], 'shaders')
    os.makedirs(out, exist_ok=True)
    for name in N['places']:
        stale = os.path.join(out, name + '.shader_model')    # `tool model` must find ONE
        if os.path.exists(stale):
            os.remove(stale)
        t = schi_def.build(filepath=os.path.join(TAGS, N['from'] + '.shader_transparent_chicago'))
        t.data.tagdata.schi_attrs.chicago_shader.numeric_counter_limit = N['limit']
        t.filepath = os.path.join(out, name + '.shader_transparent_chicago')
        t.serialize(temp=False, backup=False)
        print('   numeric shader %s  limit %d  place %d' % (t.filepath, N['limit'], N['places'][name]))


def numeric_places(w):
    from reclaimer.hek.defs.mod2 import mod2_def
    for sub, fname in (('', w['world_name']), (B + 'fp', 'fp')):
        p = os.path.join(TAGS, w['dir'] + sub, fname + '.gbxmodel')
        t = mod2_def.build(filepath=p)
        n = 0
        for s in t.data.tagdata.shaders.STEPTREE:
            name = s.shader.filepath.rsplit(B, 1)[-1]
            if name in w['numeric']['places']:
                s.permutation_index = w['numeric']['places'][name]
                n += 1
        t.serialize(temp=False, backup=False)
        print('   %s: %d numeric shader entr(ies) placed' % (w['dir'] + sub, n))


def meters(w):
    """On-gun METERS (the Carbine, 2026-10-07): Halo 3's meter shaders (`meter_map` +
    `meter_value` <- ammo) as Halo 1 shader_transparent_meters, copied from `from` (the
    plasma rifle's heat gauge). THE CHANNELS SWAP: Halo 3's meter map is the SHAPE in RGB
    and the fill GRADIENT in alpha (the carbine display: 18 steps, one a round); Halo 1's
    is the gradient in RGB and the shape in alpha (the gauge). `gradient` 'alpha' takes
    Halo 3's alpha, a number is constant (0: lit while the value is above 0 -- the switch).
    The bitmap is a raw a8r8g8b8 tag (h1_h3_scope's template: no compression, no mips);
    `value` = the weapon OUT that drives it (the AR's layout: out A = loaded ammo)."""
    from reclaimer.hek.defs.smet import smet_def
    from reclaimer.hek.defs.bitm import bitm_def
    import h1_h3_scope
    out = os.path.join(TAGS, w['dir'], 'shaders')
    os.makedirs(out, exist_ok=True)
    for name, M in w['meters'].items():
        img, _ = h3_hud_art.decode(M['map'])
        a = np.array(img)
        shape = a[..., :3].max(axis=2)
        grad = a[..., 3] if M.get('gradient', 'alpha') == 'alpha' else np.full_like(shape, int(round(M['gradient'] * 255)))
        if M.get('steps'):
            # Halo 3's steps are GAMMA-spaced (the display: 223, 189, 168 ... 3, 1 = (k/18)^2.2)
            # and Halo 1 compares linearly (lit while gradient < value) -- test 2: 'drains only
            # from the 3rd shot, irregular steps'. By RANK: the r-th brightest interior step ->
            # (N - 1 - r + 0.5) / N, so k shots darken k steps; the 255 / 0 edge columns join
            # their neighbours (the brightest step / always lit)
            n = M['steps']
            vals = sorted({int(v) for v in np.unique(grad)} - {0, 255}, reverse=True)
            lut = np.zeros(256)
            for r, v in enumerate(vals):
                lut[v] = (n - 1 - r + 0.5) / n
            lut[255] = lut[vals[0]] if vals else 1.0
            grad = np.clip(np.round(lut[grad] * 255), 0, 255).astype(np.uint8)
            print('   %s: %d gamma steps -> linear thresholds of %d' % (name, len(vals), n))
        h, wd = shape.shape
        t = bitm_def.build(filepath=os.path.join(TAGS, h1_h3_scope.TEMPLATE + '.bitmap'))
        d = t.data.tagdata
        b = d.bitmaps.STEPTREE[0]
        b.width, b.height = wd, h
        b.registration_point_x, b.registration_point_y = wd // 2, h // 2
        d.processed_pixel_data.data = bytearray(np.stack([grad, grad, grad, shape], axis=-1).astype(np.uint8).tobytes())
        bm = w['dir'] + B + 'bitmaps' + B + name + '_meter'
        t.filepath = os.path.join(TAGS, bm + '.bitmap')
        os.makedirs(os.path.dirname(t.filepath), exist_ok=True)
        t.serialize(temp=False, backup=False)
        stale = os.path.join(out, name + '.shader_model')        # `tool model` must find ONE
        if os.path.exists(stale):
            os.remove(stale)
        s = smet_def.build(filepath=os.path.join(TAGS, M['from'] + '.shader_transparent_meter'))
        sm = s.data.tagdata.smet_attrs
        sm.meter_shader.map.filepath = bm
        c = sm.colors
        on, off = M['color'], M.get('color_off', tuple(x * 0.25 for x in M['color']))
        for blk, rgb in ((c.gadient_min, on), (c.gadient_max, on), (c.background, off), (c.tint, (1.0, 1.0, 1.0))):
            blk.r, blk.g, blk.b = rgb
        c.background_transparency = M.get('background_transparency', c.background_transparency)
        sm.external_function_sources.value.set_to(M.get('value', 'A_out'))
        s.filepath = os.path.join(out, name + '.shader_transparent_meter')
        s.serialize(temp=False, backup=False)
        print('   meter shader %s  map %s %dx%d  value %s' % (s.filepath, bm, wd, h, M.get('value', 'A_out')))


def shaders(w, glow):
    out = os.path.join(TAGS, w['dir'], 'shaders')
    os.makedirs(out, exist_ok=True)
    # a Halo 3 material with no Halo 1 maps of its own (the Beam Rifle: a reflective glass,
    # an animated energy `luminous`) = a COPY of a stock Halo 1 shader under the material's
    # name (`shader_copies` {name: tag path WITH extension}); `tool model` finds it by name
    import shutil
    for name, src in w.get('shader_copies', {}).items():
        ext = os.path.splitext(src)[1]
        for e in ('.shader_model', '.shader_transparent_chicago', '.shader_transparent_generic',
                  '.shader_transparent_glass', '.shader_transparent_meter'):
            stale = os.path.join(out, name + e)               # `tool model` must find ONE
            if e != ext and os.path.exists(stale):
                os.remove(stale)
        shutil.copy2(os.path.join(TAGS, src), os.path.join(out, name + ext))
        print('   shader %s = a copy of %s' % (name + ext, src))
    for name, spec in w.get('glow_shaders', {}).items():
        if not (isinstance(spec, dict) and spec.get('additive')):
            continue
        from reclaimer.hek.defs.schi import schi_def
        stale = os.path.join(out, name + '.shader_model')          # `tool model` must find ONE
        if os.path.exists(stale):
            os.remove(stale)
        t = schi_def.build(filepath=os.path.join(TAGS, spec.get('from', r'weapons\needler\shaders\needler luminous')
                                                 + '.shader_transparent_chicago'))
        mp = t.data.tagdata.schi_attrs.maps.STEPTREE[0]
        mp.bitmap.filepath = w['dir'] + B + 'bitmaps' + B + name + '_glow'
        if spec.get('v_scroll'):                 # Halo 3 scrolls its noise: slide along v
            mp.v_animation.function.set_to('slide')
            mp.v_animation.period = spec['v_scroll']
            mp.v_animation.scale = 1.0
        t.filepath = os.path.join(out, name + '.shader_transparent_chicago')
        t.serialize(temp=False, backup=False)
        print('   shader %s  ADDITIVE glow %s' % (t.filepath, tuple(spec['rgb'])))
    for name in list(w['shaders']) + [k for k, v in w.get('glow_shaders', {}).items()
                                      if not (isinstance(v, dict) and v.get('additive'))]:
        if (name in w.get('numeric', {}).get('places', {}) or name in w.get('meters', {})
                or name in w.get('shader_copies', {})):
            continue
        t = soso_def.build(filepath=os.path.join(TAGS, w['template'] + '.shader_model'))
        m = t.data.tagdata.soso_attrs
        m.maps.diffuse_map.filepath = w['dir'] + B + 'bitmaps' + B + name + '_diff'
        m.maps.multipurpose_map.filepath = w['dir'] + B + 'bitmaps' + B + name + '_mp'
        if name in glow:
            si = m.self_illumination
            for bound in (si.color_lower_bound, si.color_upper_bound):
                bound.r, bound.g, bound.b = glow[name]
        t.filepath = os.path.join(out, name + '.shader_model')
        t.serialize(temp=False, backup=False)
        print('   shader %s  glow %s' % (t.filepath, tuple(round(c, 2) for c in glow.get(name, ()))))


def models(w):
    for key, sub, fname in (('world', '', w['world_name']), ('fp', B + 'fp', 'fp')):
        jm, _rm = h3_rm_to_jms.convert(w[key], markers=w.get('markers'))
        drop_materials(jm, w.get('drop_materials', ()))
        # a marker at the centre of each piece of a material (`material_markers` {prefix:
        # material}; the Beam Rifle's gems, for a lens-flare test): `<prefix> <n>`, on the
        # piece's node (bind rotation identity there: checked on the beam rifle's `frame gun`)
        from reclaimer.model.jms.file import JmsMarker
        # WORLD model only: object attachments use it, and the FP pieces hang off child nodes
        for prefix, mat in (w.get('material_markers', {}).items() if key == 'world' else ()):
            for i, (_ts, vs) in enumerate(material_islands(jm, mat)):
                nd = vs[0].node_0
                n = jm.nodes[nd]
                P = np.array([(x.pos_x, x.pos_y, x.pos_z) for x in vs]).mean(0)
                jm.markers.append(JmsMarker('%s %d' % (prefix, i), '', 0, nd, 0.0, 0.0, 0.0, 1.0,
                                            P[0] - n.pos_x, P[1] - n.pos_y, P[2] - n.pos_z))
        # GLOW CARDS (the Beam Rifle's gems, test 7: a gradient inside a few-pixel gem reads
        # flat; Halo 1 has no bloom): each piece of `material` copied, scaled `scale` about
        # its centre and lifted `lift` (JMS units) along its mean normal, as material `shader`
        # (an additive glow whose texture falls to 0 at the piece's UV box edge: a halo
        # around the gem). Same UVs, so the card's texture is the piece's box stretched
        import copy as _copy
        from reclaimer.model.jms.file import JmsMaterial, JmsTriangle
        for mat, C in w.get('glow_cards', {}).items():
            # `lit`: only the triangles on lit illum texels (the Spike Rifle), else the
            # material's islands (the Beam Rifle's gems)
            pieces = lit_pieces(jm, mat, C['lit']) if C.get('lit') else material_islands(jm, mat)
            if not pieces:
                continue
            jm.materials.append(JmsMaterial(C['shader']))
            si = len(jm.materials) - 1
            n_new = 0
            for ts, vs in pieces:
                P = np.array([(x.pos_x, x.pos_y, x.pos_z) for x in vs]).mean(0)
                Nm = np.array([(x.norm_i, x.norm_j, x.norm_k) for x in vs]).mean(0)
                Nm = Nm / (np.linalg.norm(Nm) or 1.0)
                for t in ts:
                    idx = []
                    for v in (t.v0, t.v1, t.v2):
                        x = _copy.copy(jm.verts[v])
                        q = P + (np.array([x.pos_x, x.pos_y, x.pos_z]) - P) * C.get('scale', 1.8) + Nm * C.get('lift', 0.05)
                        x.pos_x, x.pos_y, x.pos_z = float(q[0]), float(q[1]), float(q[2])
                        jm.verts.append(x)
                        idx.append(len(jm.verts) - 1)
                    jm.tris.append(JmsTriangle(t.region, si, *idx))
                    n_new += 1
            print('   glow cards %s: %d piece(s), %d triangle(s) as %s' % (mat, len(pieces), n_new, C['shader']))
        d = os.path.join(HCEEK, 'data', w['dir'] + sub, 'models')
        os.makedirs(d, exist_ok=True)
        write_jms(os.path.join(d, fname + '.jms'), jm)
        log = tool('model', w['dir'] + sub)
        tag = os.path.join(TAGS, w['dir'] + sub, fname + '.gbxmodel')
        ok = os.path.exists(tag)
        print('   model %-40s %s  (%d verts, %d tris, nodes %d)'
              % (w['dir'] + sub, 'OK' if ok else 'FAILED', len(jm.verts), len(jm.tris), len(jm.nodes)))
        if not ok or 'error' in log.lower():
            print(log[-2000:])


def extra_models(w):
    """Further models from Halo 3 PARTICLE MODELS (`extra_models` {name: {'from': .particle_model
    path, 'dir': tag folder, 'material': shader name from `shaders`}}): the Spike Rifle's
    stuck spike, the projectile's model (h3_rm_to_jms.convert_particle_model). The folder
    sits under the weapon's, so `tool model` finds the shader in <weapon>\\shaders."""
    for name, X in w.get('extra_models', {}).items():
        jm = h3_rm_to_jms.convert_particle_model(X['from'], X['material'])
        d = os.path.join(HCEEK, 'data', X['dir'], 'models')
        os.makedirs(d, exist_ok=True)
        write_jms(os.path.join(d, name + '.jms'), jm)
        log = tool('model', X['dir'])
        ok = os.path.exists(os.path.join(TAGS, X['dir'], name + '.gbxmodel'))
        print('   model %-40s %s  (%d verts, %d tris)' % (X['dir'], 'OK' if ok else 'FAILED', len(jm.verts), len(jm.tris)))
        if not ok or 'error' in log.lower():
            print(log[-2000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('weapon', choices=sorted(WEAPONS))
    ap.add_argument('--skip-bitmaps', action='store_true')
    a = ap.parse_args()
    w = WEAPONS[a.weapon]
    glow = {} if a.skip_bitmaps else bitmaps(w)
    shaders(w, glow)
    if 'numeric' in w:
        numeric(w)
    if 'meters' in w:
        meters(w)
    models(w)
    extra_models(w)
    if 'numeric' in w:
        numeric_places(w)


if __name__ == '__main__':
    main()
