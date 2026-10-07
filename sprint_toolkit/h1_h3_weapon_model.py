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
            mp[..., 1] = np.clip(a.max(axis=2), 0, 255).astype(np.uint8)
            lit = a[a.max(axis=2) > 64]
            if len(lit):                                          # the glow's own colour
                c = lit.mean(axis=0)
                glow[name] = tuple(float(x) for x in c / c.max())
        Image.fromarray(mp).save(os.path.join(out, name + '_mp.tif'))
    log = tool('bitmaps', w['dir'] + B + 'bitmaps')
    print('   tool bitmaps: %s' % (log.strip().splitlines()[-1] if log.strip() else 'ok'))
    return glow


def shaders(w, glow):
    out = os.path.join(TAGS, w['dir'], 'shaders')
    os.makedirs(out, exist_ok=True)
    for name in w['shaders']:
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
        jm, _rm = h3_rm_to_jms.convert(w[key])
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('weapon', choices=sorted(WEAPONS))
    ap.add_argument('--skip-bitmaps', action='store_true')
    a = ap.parse_args()
    w = WEAPONS[a.weapon]
    glow = {} if a.skip_bitmaps else bitmaps(w)
    shaders(w, glow)
    models(w)


if __name__ == '__main__':
    main()
