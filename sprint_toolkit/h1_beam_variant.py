r"""TEST-ONLY beam variants of a Halo 1 port: a copy of the port's weapon + its projectile + its
contrails under `<weapon dir>\test`, the contrails re-skinned with baked beam textures -- judged
on the test map's SECONDARY (`h1_port_test_map.py <key> --secondary <variant weapon>`) beside
the real thing. Never shipped: `--clean` after the test (the h1_scope_variant pattern).

Written for THE FOCUS RIFLE'S BEAM RECIPE on the Spartan Laser (user, 2026-10-12, B7 boot 2:
'the best beam we have produced so far -- apply this recipe to the spartan laser for a test'):
Reach's 1p beam = a CORE (energy_trail: bright centre, edges falling off) + a PULSE (pulse: bright
knots ALONG the beam) through ONE palette, the pulse SCROLLING along the beam. Each re-skin:

    --skin <contrail name>=<profile bitmap>,<palette bitmap>[,w=<width wu>][,rep=<u>][,scroll=<u>][,size=<w>x<h>]

<profile> / <palette> are kit paths (`reach:` = HREK, else H3EK); the bake = palette[profile]
premultiplied (h1_h3_weapon_model `baked_textures`), DXT5. Contrails not named keep theirs.

    python h1_beam_variant.py spartan_laser fr --trigger 0 ^
        --skin "beam=reach:fx\bitmaps\contrails\energy_trail.bitmap,fx\particles\_gradients\laser_red_01.bitmap,w=0.22" ^
        --skin "beam glow=reach:fx\bitmaps\contrails\pulse.bitmap,fx\particles\_gradients\laser_red_01.bitmap,w=0.3,rep=0.15,scroll=5,size=512x64"
    python h1_port_test_map.py focus_rifle --level b30 --secondary "weapons\spartan laser\test\spartan laser fr" --stage
    python h1_beam_variant.py spartan_laser --clean
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.cont import cont_def  # noqa: E402
from reclaimer.hek.defs.bitm import bitm_def  # noqa: E402
import h3_hud_art  # noqa: E402
import ports_h1  # noqa: E402

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
TAGS = os.path.join(HCEEK, 'tags')
B = '\\'


def bake(profile, palette, size, out_tif):
    """colour = palette[profile] premultiplied, alpha = profile (h1_h3_weapon_model's bake)."""
    prof, _ = h3_hud_art.decode(profile)
    pal, _ = h3_hud_art.decode(palette)
    v = np.asarray(prof.convert('L').resize(size, Image.LANCZOS)).astype(np.float64)
    row = np.asarray(pal)[np.asarray(pal).shape[0] // 2, :, :3].astype(np.float64)
    col = row[np.clip((v / 255.0 * (len(row) - 1)).round().astype(int), 0, len(row) - 1)]
    col = col * (v / 255.0)[..., None]
    px = np.zeros(v.shape + (4,), np.uint8)
    px[..., :3] = np.clip(col, 0, 255).round()
    px[..., 3] = np.clip(v, 0, 255).round()
    Image.fromarray(px).save(out_tif)


def tool(*args):
    r = subprocess.run([os.path.join(HCEEK, 'tool.exe')] + list(args), cwd=HCEEK,
                       capture_output=True, text=True, errors='replace')
    return (r.stdout + r.stderr).strip().splitlines()[-1:] or ['ok']


def parse_skin(s):
    name, rest = s.split('=', 1)
    parts = rest.split(',')
    K = {'profile': parts[0], 'palette': parts[1], 'size': (64, 64)}
    for p in parts[2:]:
        k, v = p.split('=')
        if k == 'size':
            K['size'] = tuple(int(x) for x in v.split('x'))
        else:
            K[k] = float(v)
    return name.strip(), K


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port')
    ap.add_argument('name', nargs='?', help='variant suffix, e.g. fr')
    ap.add_argument('--trigger', type=int, default=0, help='the trigger whose projectile is copied')
    ap.add_argument('--skin', action='append', default=[])
    ap.add_argument('--clean', action='store_true')
    a = ap.parse_args()
    w = ports_h1.load(a.port)['pickable']
    wdir = w['weapon'].rsplit(B, 1)[0]
    test = wdir + B + 'test'
    if a.clean:
        for root in (TAGS, os.path.join(HCEEK, 'data')):
            p = os.path.join(root, test)
            if os.path.isdir(p):
                shutil.rmtree(p)
                print('removed', p)
        return
    base = w['weapon'].rsplit(B, 1)[1]
    wt = weap_def.build(filepath=os.path.join(TAGS, w['weapon'] + '.weapon'))
    tr = wt.data.tagdata.weap_attrs.triggers.STEPTREE[a.trigger]
    p_src = tr.projectile.projectile.filepath
    pt = proj_def.build(filepath=os.path.join(TAGS, p_src + '.projectile'))
    skins = dict(parse_skin(s) for s in a.skin)
    data_bm = os.path.join(HCEEK, 'data', test, 'bitmaps')
    os.makedirs(data_bm, exist_ok=True)
    for cname, K in skins.items():
        bake(K['profile'], K['palette'], K['size'], os.path.join(data_bm, a.name + ' ' + cname + '.tif'))
    print('bitmaps', tool('bitmaps', test + B + 'bitmaps'))
    for cname in skins:                    # interpolated alpha (DXT5), then import again
        bp = os.path.join(TAGS, test, 'bitmaps', a.name + ' ' + cname + '.bitmap')
        t = bitm_def.build(filepath=bp)
        t.data.tagdata.format.set_to('interpolated_alpha')
        t.serialize(temp=False, backup=False)
    print('bitmaps (DXT5)', tool('bitmaps', test + B + 'bitmaps'))
    n = 0
    for x in pt.data.tagdata.obje_attrs.attachments.STEPTREE:
        if x.type.tag_class.enum_name != 'contrail':
            continue
        cname = x.type.filepath.rsplit(B, 1)[1]
        ct = cont_def.build(filepath=os.path.join(TAGS, x.type.filepath + '.contrail'))
        if cname in skins:
            K = skins[cname]
            r = ct.data.tagdata.rendering
            r.bitmap.filepath = test + B + 'bitmaps' + B + a.name + ' ' + cname
            r.first_sequence_index, r.sequence_count = 0, 0
            r.framebuffer_blend_function.set_to('add')
            if 'rep' in K:
                r.texture_repeats_u = K['rep']
            if 'scroll' in K:
                r.texture_animation_u = K['scroll']
            if 'w' in K:
                sts = ct.data.tagdata.point_states.STEPTREE
                k = K['w'] / (sts[0].width or 1.0)
                for s in sts:
                    s.width *= k
        own = test + B + a.name + ' ' + cname
        ct.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, own + '.contrail'))
        x.type.filepath = own
        n += 1
        print('contrail %-12s -> %s%s' % (cname, own, '  (re-skinned)' if cname in skins else ''))
    p_own = test + B + a.name + ' ' + p_src.rsplit(B, 1)[1]
    pt.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, p_own + '.projectile'))
    tr.projectile.projectile.filepath = p_own
    w_own = test + B + base + ' ' + a.name
    wt.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, w_own + '.weapon'))
    print('weapon %s  (projectile %s, %d contrails)' % (w_own, p_own, n))
    print('then: python h1_port_test_map.py <the staged port> --level <its level> --secondary "%s" --stage' % w_own)


if __name__ == '__main__':
    main()
