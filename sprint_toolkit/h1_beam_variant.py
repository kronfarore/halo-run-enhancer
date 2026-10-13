r"""TEST-ONLY beam variants of a Halo 1 port: a copy of the port's weapon + its projectile + its
contrails under a test folder, the contrails re-skinned with baked beam textures -- judged on the
test map's SECONDARY (`h1_port_test_map.py <key> --secondary <variant weapon>`) beside the real
thing. Never shipped: `--clean` after the test (the h1_scope_variant pattern).

Written for THE FOCUS RIFLE'S BEAM RECIPE on the Spartan Laser (user, 2026-10-12, B7 boot 2:
'the best beam we have produced so far -- apply this recipe to the spartan laser for a test'):
Reach's 1p beam = a CORE (energy_trail: bright centre, edges falling off) + a PULSE (pulse: bright
knots ALONG the beam) through ONE palette. The laser took it (57b5e67).

`--out`: the test folder (default <weapon dir>\test). A DONE port's folder is RESTORED by the other
parallel session's proofs (the Focus Rifle's laser copy vanished mid-build, 2026-10-12): put a copy
of a done port under the in-progress port's folder.

QUICK re-skins (the laser test):
    --skin <contrail name>=<profile bitmap>,<palette bitmap>[,w=<width wu>][,rep=<u>][,scroll=<u>][,size=<w>x<h>]

A SPEC (the Focus Rifle's colour + animation test, 2026-10-13: 'animate the beam, more of a Reach
colour'): `--spec file.json` = {"layers": [...]}, each layer one contrail:
    "contrail": an existing contrail's name to re-skin, or "new": a name for an ADDED contrail
                (a copy of the projectile's first contrail on the same marker)
    "profile": bitmap (kit path, `reach:` = HREK, else H3EK)
    "palette": bitmap  OR  "stops": [[t, [r, g, b]], ...] (0..1, 0..255; t = profile brightness)
    "gain": premultiplied brightness x (default 1), "size": [w, h] (default 64 x 64)
    "width": wu, "rep": texture repeats u, "scroll": texture animation u, "blend": add / ...
    "secondary": a greyscale SECONDARY MAP on the contrail, animated by a FUNCTION -- Halo 1's map
                animations run on GAME time (the contrail's own u scroll drew static: every 30/s
                beam starts at the same phase) -- {"profile", "size", "floor" (0..1, the darkest
                grey), "function" (slide, cosine, ...), "period" s, "scale", "anchor"
                (with_primary / with_screen_space / with_zsprite)}

    python h1_beam_variant.py focus_rifle anim --spec spec.json
    python h1_port_test_map.py focus_rifle --level b30 --secondary "weapons\focus rifle\test\focus rifle anim" --stage
    python h1_beam_variant.py focus_rifle --clean
"""
import argparse
import copy
import json
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


def profile_px(profile, size):
    prof, _ = h3_hud_art.decode(profile)
    return np.asarray(prof.convert('L').resize(tuple(size), Image.LANCZOS)).astype(np.float64)


def palette_row(K):
    """256 RGB entries: a palette bitmap's middle row, or linear colour `stops`."""
    if 'stops' in K:
        t = np.linspace(0, 1, 256)
        st = sorted(K['stops'])
        xs = [s[0] for s in st]
        return np.stack([np.interp(t, xs, [s[1][c] for s in st]) for c in range(3)], axis=1)
    pal, _ = h3_hud_art.decode(K['palette'])
    return np.asarray(pal)[np.asarray(pal).shape[0] // 2, :, :3].astype(np.float64)


def bake(K, out_tif):
    """colour = palette[profile] premultiplied x gain, alpha = profile (h1_h3_weapon_model's bake)."""
    v = profile_px(K['profile'], K.get('size', (64, 64)))
    row = palette_row(K)
    col = row[np.clip((v / 255.0 * (len(row) - 1)).round().astype(int), 0, len(row) - 1)]
    col = col * (v / 255.0)[..., None] * K.get('gain', 1.0)
    px = np.zeros(v.shape + (4,), np.uint8)
    px[..., :3] = np.clip(col, 0, 255).round()
    px[..., 3] = np.clip(v, 0, 255).round()
    Image.fromarray(px).save(out_tif)


def bake_grey(S, out_tif):
    """A greyscale secondary map: floor + (1 - floor) x profile, alpha 255."""
    v = profile_px(S['profile'], S.get('size', (64, 64))) / 255.0
    g = S.get('floor', 0.3) + (1.0 - S.get('floor', 0.3)) * v
    px = np.zeros(v.shape + (4,), np.uint8)
    px[..., :3] = np.clip(g * 255, 0, 255).round()[..., None]
    px[..., 3] = 255
    Image.fromarray(px).save(out_tif)


def tool(*args):
    r = subprocess.run([os.path.join(HCEEK, 'tool.exe')] + list(args), cwd=HCEEK,
                       capture_output=True, text=True, errors='replace')
    return (r.stdout + r.stderr).strip().splitlines()[-1:] or ['ok']


def parse_skin(s):
    name, rest = s.split('=', 1)
    parts = rest.split(',')
    K = {'contrail': name.strip(), 'profile': parts[0], 'palette': parts[1], 'size': (64, 64)}
    for p in parts[2:]:
        k, v = p.split('=')
        if k == 'size':
            K['size'] = tuple(int(x) for x in v.split('x'))
        elif k == 'w':
            K['width'] = float(v)
        else:
            K[k] = float(v)
    return K


def skin_contrail(ct, K, bm_tag, sec_tag):
    r = ct.data.tagdata.rendering
    r.bitmap.filepath = bm_tag
    r.first_sequence_index, r.sequence_count = 0, 0
    r.framebuffer_blend_function.set_to(K.get('blend', 'add'))
    if 'rep' in K:
        r.texture_repeats_u = K['rep']
    if 'scroll' in K:
        r.texture_animation_u = K['scroll']
    if 'width' in K:
        sts = ct.data.tagdata.point_states.STEPTREE
        k = K['width'] / (sts[0].width or 1.0)
        for s in sts:
            s.width *= k
    if sec_tag:
        S = K['secondary']
        sm = ct.data.tagdata.secondary_map
        sm.bitmap.filepath = sec_tag
        sm.anchor.set_to(S.get('anchor', 'with_primary'))
        ua = sm.u_animation
        ua.source.set_to('none')
        ua.function.set_to(S.get('function', 'slide'))
        ua.period = S.get('period', 0.5)
        ua.scale = S.get('scale', 1.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port')
    ap.add_argument('name', nargs='?', help='variant suffix, e.g. fr')
    ap.add_argument('--trigger', type=int, default=0, help='the trigger whose projectile is copied')
    ap.add_argument('--skin', action='append', default=[])
    ap.add_argument('--spec', help='JSON {"layers": [...]} (see the docstring)')
    ap.add_argument('--clean', action='store_true')
    ap.add_argument('--out', help='test folder, kit tag path')
    a = ap.parse_args()
    w = ports_h1.load(a.port)['pickable']
    wdir = w['weapon'].rsplit(B, 1)[0]
    test = a.out or (wdir + B + 'test')
    if a.clean:
        for root in (TAGS, os.path.join(HCEEK, 'data')):
            p = os.path.join(root, test)
            if os.path.isdir(p):
                shutil.rmtree(p)
                print('removed', p)
        return
    layers = [parse_skin(s) for s in a.skin]
    if a.spec:
        layers += json.load(open(a.spec, encoding='utf-8'))['layers']
    base = w['weapon'].rsplit(B, 1)[1]
    wt = weap_def.build(filepath=os.path.join(TAGS, w['weapon'] + '.weapon'))
    tr = wt.data.tagdata.weap_attrs.triggers.STEPTREE[a.trigger]
    p_src = tr.projectile.projectile.filepath
    pt = proj_def.build(filepath=os.path.join(TAGS, p_src + '.projectile'))
    data_bm = os.path.join(HCEEK, 'data', test, 'bitmaps')
    os.makedirs(data_bm, exist_ok=True)
    names = []
    for K in layers:
        ln = K.get('contrail') or K['new']
        bake(K, os.path.join(data_bm, '%s %s.tif' % (a.name, ln)))
        names.append('%s %s' % (a.name, ln))
        if K.get('secondary'):
            bake_grey(K['secondary'], os.path.join(data_bm, '%s %s sec.tif' % (a.name, ln)))
    print('bitmaps', tool('bitmaps', test + B + 'bitmaps'))
    for n in names:                        # interpolated alpha (DXT5), then import again
        t = bitm_def.build(filepath=os.path.join(TAGS, test, 'bitmaps', n + '.bitmap'))
        t.data.tagdata.format.set_to('interpolated_alpha')
        t.serialize(temp=False, backup=False)
    print('bitmaps (DXT5)', tool('bitmaps', test + B + 'bitmaps'))

    def tags_for(K):
        ln = K.get('contrail') or K['new']
        bm = test + B + 'bitmaps' + B + '%s %s' % (a.name, ln)
        return bm, (bm + ' sec' if K.get('secondary') else None)
    by_name = {K['contrail']: K for K in layers if K.get('contrail')}
    atts = pt.data.tagdata.obje_attrs.attachments.STEPTREE
    first = None
    n = 0
    for x in list(atts):
        if x.type.tag_class.enum_name != 'contrail':
            continue
        first = first or x
        cname = x.type.filepath.rsplit(B, 1)[1]
        ct = cont_def.build(filepath=os.path.join(TAGS, x.type.filepath + '.contrail'))
        if cname in by_name:
            skin_contrail(ct, by_name[cname], *tags_for(by_name[cname]))
        own = test + B + a.name + ' ' + cname
        ct.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, own + '.contrail'))
        x.type.filepath = own
        n += 1
        print('contrail %-12s -> %s%s' % (cname, own, '  (re-skinned)' if cname in by_name else ''))
    for K in layers:                       # ADDED layers: copies of the first contrail
        if not K.get('new'):
            continue
        src = first.type.filepath
        ct = cont_def.build(filepath=os.path.join(TAGS, src + '.contrail'))
        skin_contrail(ct, K, *tags_for(K))
        own = test + B + a.name + ' ' + K['new']
        ct.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, own + '.contrail'))
        atts.append(copy.deepcopy(first))
        atts[len(atts) - 1].type.filepath = own
        n += 1
        print('contrail %-12s -> %s  (added)' % (K['new'], own))
    p_own = test + B + a.name + ' ' + p_src.rsplit(B, 1)[1]
    pt.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, p_own + '.projectile'))
    tr.projectile.projectile.filepath = p_own
    w_own = test + B + base + ' ' + a.name
    wt.serialize(temp=False, backup=False, filepath=os.path.join(TAGS, w_own + '.weapon'))
    print('weapon %s  (projectile %s, %d contrails)' % (w_own, p_own, n))
    print('then: python h1_port_test_map.py <the staged port> --level <its level> --secondary "%s" --stage' % w_own)


if __name__ == '__main__':
    main()
