r"""Which MATERIAL is where in a Halo 1 port's first-person view: the FP model posed (any
animation frame) with every triangle coloured by its shader, plus the hands -- and, with
--illum, the triangles whose UVs land on a Halo 3 illum / glow map's lit texels in white.

Written for the Beam Rifle (2026-10-08): the user's 'four glowing spots are missing' were the
`beam_rifle_glass` material (an ADDITIVE Halo 3 template, not glass), and the illum-map
lines all sat on hidden down-facing triangles -- both found with this view, after three boots
of guessing. Run it BEFORE deciding how a material should glow (H1_PORT_PLAN "A4").

UVs: Halo 1 gbxmodels store them normalized with a model-wide base_map_u/v_scale; they are
multiplied back before sampling the illum map.

    python fp_material_view.py beam_rifle --out view.png [--anim "first-person idle"] [--frame 0]
                               [--illum objects\weapons\rifle\beam_rifle\bitmaps\beam_rifle_illum.bitmap]
"""
import argparse
import colorsys
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import fp_render as R  # noqa: E402
import ports_h1  # noqa: E402
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402
from PIL import ImageDraw, Image  # noqa: E402

B = '\\'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port', help='a ports_h1 key (its model dir holds fp\\fp)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--anim', default='first-person idle')
    ap.add_argument('--frame', type=int, default=0)
    ap.add_argument('--illum', help='Halo 3 bitmap (H3EK tags path): mark triangles on its lit texels')
    ap.add_argument('--threshold', type=int, default=64, help='lit = max(RGB) above this')
    ap.add_argument('--list-lit', action='store_true', help='print each lit triangle')
    ap.add_argument('--texels', type=int, default=0,
                    help='draw the lit texels on lit triangles (each cut n x n), not the whole triangle')
    ap.add_argument('--size', default='1920x1080')
    a = ap.parse_args()
    cfg = ports_h1.load(a.port)
    rel = cfg['model']['dir'] + B + 'fp' + B + 'fp'
    antr = (cfg.get('pickable') or {}).get('fp_anims', rel)
    d = mod2_def.build(filepath=os.path.join(R.TAGS, rel + '.gbxmodel')).data.tagdata
    shnames = [s.shader.filepath.rsplit(B, 1)[-1] for s in d.shaders.STEPTREE]
    uniq = sorted(set(shnames))
    colours = {n: tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / max(1, len(uniq)), 0.75, 0.95))
               for i, n in enumerate(uniq)}
    lit = None
    if a.illum:
        import h3_hud_art
        img, _ = h3_hud_art.decode(a.illum)
        lit = np.array(img)[..., :3].max(axis=2) > a.threshold
    us, vs = d.base_map_u_scale or 1.0, d.base_map_v_scale or 1.0
    nodes = d.nodes.STEPTREE
    names = [n.name for n in nodes]
    parents = [names[n.parent_node] if n.parent_node >= 0 else None for n in nodes]
    bind = {n.name: ((n.rotation.w, n.rotation.i, n.rotation.j, n.rotation.k),
                     (n.translation.x, n.translation.y, n.translation.z)) for n in nodes}
    nn, par, local, nframes = R.anim_pose(antr, a.anim, a.frame)
    world = R.compose(nn, par, local)
    Wb = R.compose(names, parents, bind)
    M = {n: (world.get(n, Wb[n]), R.inverse(Wb[n])) for n in names}
    tris, counts = [], {}
    for g in d.geometries.STEPTREE[:1]:
        for p in g.parts.STEPTREE:
            vsx = p.uncompressed_vertices.STEPTREE
            ln = [x for x in p.local_nodes][:p.local_node_count] if p.flags.ZONER else None
            sh = shnames[p.shader_index]
            strip = [i for t in p.triangles.STEPTREE for i in (t.v0_index, t.v1_index, t.v2_index) if i >= 0]
            for k in range(len(strip) - 2):
                i0, i1, i2 = strip[k], strip[k + 1], strip[k + 2]
                if i0 == i1 or i1 == i2 or i0 == i2:
                    continue
                if k % 2:
                    i0, i1 = i1, i0
                col = colours[sh]
                if lit is not None:
                    H, W = lit.shape
                    uv = np.array([(vsx[i].u * us, vsx[i].v * vs) for i in (i0, i1, i2)])
                    # EXACT coverage (the Spike Rifle, test 3): every texel whose centre lies in
                    # the UV triangle; lit = ANY lit texel. The old 6x6 sampling with a 15%
                    # share missed thin lit lines on larger faces (4 of 30 triangles)
                    off = np.floor(uv.min(0))
                    q = (uv - off) * (W, H)
                    x0, y0 = np.floor(q.min(0)).astype(int)
                    x1, y1 = np.ceil(q.max(0)).astype(int)
                    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
                    (ax, ay), (bx, by), (cx, cy) = q
                    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                    hits = 0
                    if abs(den) > 1e-12:
                        l1 = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / den
                        l2 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / den
                        ins = (l1 >= 0) & (l2 >= 0) & (1 - l1 - l2 >= 0)
                        hits = int(lit[(yy[ins].astype(int)) % H, (xx[ins].astype(int)) % W].sum())
                    if hits:
                        if a.list_lit:
                            print('   lit %-22s %3d texel(s)' % (sh, hits))
                        col = (255, 255, 255)
                        counts[sh + ' (lit)'] = counts.get(sh + ' (lit)', 0) + 1
                pts = []
                for i in (i0, i1, i2):
                    v = vsx[i]
                    acc, w = [0.0, 0.0, 0.0], 0.0
                    for nd, wt in ((v.node_0_index, v.node_0_weight), (v.node_1_index, v.node_1_weight)):
                        nd = nd if nd < 0 or ln is None else ln[nd]
                        if nd < 0 or wt <= 0:
                            continue
                        wp, ib = M[names[nd]]
                        q = R.xform(wp, R.xform(ib, (v.position_x, v.position_y, v.position_z)))
                        acc = [x + wt * y for x, y in zip(acc, q)]
                        w += wt
                    pts.append(tuple(x / (w or 1.0) for x in acc))
                if a.texels and col == (255, 255, 255):
                    # the lit TEXELS themselves (the Spike Rifle, test 4: which part of a lit
                    # face glows): the triangle cut into n x n pieces, each white where its UV
                    # centre lands on a lit texel, else the material's colour
                    n = a.texels
                    P = np.array(pts)
                    for i in range(n):
                        for j in range(n - i):
                            for corners in (((i, j), (i + 1, j), (i, j + 1)),
                                            ((i + 1, j), (i + 1, j + 1), (i, j + 1))):
                                if any(x + y > n for x, y in corners):
                                    continue
                                bc = [np.array([1 - (x + y) / n, x / n, y / n]) for x, y in corners]
                                sub = [tuple(w @ P) for w in bc]
                                c_uv = sum(bc) / 3 @ uv
                                hit = lit[int((c_uv[1] % 1) * H) % H, int((c_uv[0] % 1) * W) % W]
                                tris.append((sub, (255, 255, 255) if hit else colours[sh]))
                else:
                    tris.append((pts, col))
                counts[sh] = counts.get(sh, 0) + 1
    hands = R.posed_tris(R.load_model(R.HANDS), world, (200, 170, 120))
    size = tuple(int(x) for x in a.size.split('x'))
    R.render([hands, tris], a.out, size=size, hfov=70.0,
             title='%s  %s  frame %d/%d' % (a.port, a.anim, a.frame, nframes))
    img = Image.open(a.out)
    dr = ImageDraw.Draw(img)
    y = 30
    for n in uniq + (['lit texels (--illum)'] if lit is not None else []):
        dr.rectangle((10, y, 28, y + 14), fill=colours.get(n, (255, 255, 255)))
        dr.text((34, y), n, fill=(230, 230, 230))
        y += 20
    img.save(a.out)
    for k, v in sorted(counts.items()):
        print('  %-36s %5d triangle(s)' % (k, v))
    print(a.out)


if __name__ == '__main__':
    main()
