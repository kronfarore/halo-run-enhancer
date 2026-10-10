r"""WHERE a Halo 3 port glows: its Halo 1 world model side-on (left, right, end-on), every
triangle carrying LIT texels of Halo 3's illum map in bright blue over a grey model.

Written for the Gravity Hammer (boot 1, 2026-10-10: the user could not see the glow and asked
'highlight them for me'): Halo 3 lights a few thin lines per triangle and blooms them, so a
picture of WHERE they are comes before deciding how to make them visible (glow_spots /
glow_cards, h1_h3_weapon_model). Each lit triangle is marked whole -- it holds only lines or
spots of glow. Reads the port config's model section: the world JMS in HCEEK data and every
shader whose illum map is set (h1_h3_weapon_model.lit_pieces does the texel test).

    python h1_glow_map.py gravity_hammer [--out out\glow_map.png] [--z-forward]

--z-forward: a model whose long axis is +z (the hammer's, the flag's) is drawn along x.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.model.jms.file import read_jms  # noqa: E402
import h1_h3_weapon_model as M  # noqa: E402
import ports_h1  # noqa: E402

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('port')
    ap.add_argument('--out', default=None)
    ap.add_argument('--z-forward', action='store_true')
    a = ap.parse_args()
    m = ports_h1.load(a.port)['model']
    jms = os.path.join(HCEEK, 'data', m['dir'], 'models', m['world_name'] + '.jms')
    jm = read_jms(open(jms, encoding='utf-8', errors='replace').read())
    lit = set()
    for mat, (_base, illum) in m['shaders'].items():
        if illum:
            for tris, _v in M.lit_pieces(jm, mat, illum):
                lit.update(id(t) for t in tris)
    print('lit triangles', len(lit))
    P = np.array([(v.pos_x, v.pos_y, v.pos_z) for v in jm.verts])
    long_ax = 2 if a.z_forward else 0
    up_ax = 0 if a.z_forward else 2
    # (name, horizontal axis, sign, vertical axis, depth axis, depth sign)
    views = [('left side', long_ax, 1, up_ax, 1, 1), ('right side', long_ax, -1, up_ax, 1, -1),
             ('end-on', 1, 1, up_ax, long_ax, 1)]
    S, PAD = 900, 30
    panels = []
    for name, hx, hs, vx, dax, dsgn in views:
        H, V = P[:, hx] * hs, P[:, vx]
        sc = (S - 2 * PAD) / max(H.max() - H.min(), V.max() - V.min())
        img = Image.new('RGB', (S, int((V.max() - V.min()) * sc + 2 * PAD) + 30), (28, 30, 36))
        d = ImageDraw.Draw(img)
        tris = sorted(jm.tris, key=lambda t: -dsgn * np.mean([P[i][dax] for i in (t.v0, t.v1, t.v2)]))
        for t in tris:
            pa, pb, pc = (P[i] for i in (t.v0, t.v1, t.v2))
            n = np.cross(pb - pa, pc - pa)
            shade = int(70 + 120 * abs(n[dax]) / (np.linalg.norm(n) or 1))
            pts = [(PAD + (p[hx] * hs - H.min()) * sc, 30 + PAD + (V.max() - p[vx]) * sc) for p in (pa, pb, pc)]
            hot = id(t) in lit
            d.polygon(pts, fill=(60, 140, 255) if hot else (shade, shade, shade),
                      outline=(255, 255, 255) if hot else None)
        d.text((8, 6), name, fill=(230, 230, 230))
        panels.append(img)
    out = Image.new('RGB', (sum(p.width for p in panels), max(p.height for p in panels)), (28, 30, 36))
    x = 0
    for p in panels:
        out.paste(p, (x, 0))
        x += p.width
    path = a.out or os.path.join(HERE, 'out', 'glow_map_%s.png' % a.port)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path)
    print(path)


if __name__ == '__main__':
    main()
