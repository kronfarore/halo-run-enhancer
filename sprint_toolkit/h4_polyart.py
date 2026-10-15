r"""Halo 4 POLYART (the 3D vector HUD art of a .cui_screen, e.g. a scope frame) rasterized to an image.
Read-only research / art tool (the LightRifle, C4 2026-10-15: Halo 4's zoomed scope has no bitmaps).

A .polyart_asset holds half-float vertices (x, y, z, alpha, u, v), a triangle index list and a camera
(`placement data`: horizontal / vertical fov, camera position). Each triangle is projected through
that camera onto a W x H canvas (the screen) and filled with the vertex alpha interpolated
(per-pixel barycentric), 4x supersampled. The CUI screen tints it (a colour) -- applied by the caller.

    python h4_polyart.py <out.png> <polyart tag> [<polyart tag> ...] [--size 1920,1080]
    (tags relative to H4EK\tags, no extension; each drawn in white, alpha = coverage x vertex alpha)
"""
import argparse
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402


def _half(v):
    return float(np.array([int(v) & 0xFFFF], np.uint16).view(np.float16)[0])


def load(rel):
    """{'cam': (hfov, vfov, (x, y, z)), 'verts': N x 4 (x, y, z, a), 'tris': M x 3}"""
    t = open(h4_tags.export_xml(rel + '.polyart_asset'), encoding='utf-8', errors='replace').read()
    hf = float(re.search(r'name="horizontal fov" value="([^"]+)"', t).group(1))
    vf = float(re.search(r'name="vertical fov" value="([^"]+)"', t).group(1))
    cp = tuple(float(x) for x in re.search(r'name="camera position" value="([^"]+)"', t).group(1).split(','))
    vb = t[t.index('<block name="vertices"'):t.index('<block name="indices"')]
    vals = re.findall(r'name="half (x|y|z|alpha)" value="(-?\d+)"', vb)
    V = []
    for i in range(0, len(vals), 4):
        V.append([_half(vals[i + j][1]) for j in range(4)])
    ib = t[t.index('<block name="indices"'):]
    idx = [int(x) for x in re.findall(r'name="index" value="(-?\d+)"', ib)]
    T = np.array(idx[:len(idx) // 3 * 3]).reshape(-1, 3)
    return {'cam': (hf, vf, cp), 'verts': np.array(V), 'tris': T}


def project(P, cam, W, H):
    """Screen px of model points: a pinhole at the camera position looking down +z."""
    hf, vf, cp = cam
    d = P[:, :3] - np.array(cp)
    fx = (W / 2.0) / np.tan(np.radians(hf) / 2.0)
    fy = (H / 2.0) / np.tan(np.radians(vf) / 2.0)
    x = W / 2.0 + fx * d[:, 0] / d[:, 2]
    y = H / 2.0 - fy * d[:, 1] / d[:, 2]
    return np.stack([x, y], 1)


def raster(pa, W, H, ss=4):
    """Coverage x vertex alpha, float H x W in 0..1 (triangles composited with max)."""
    S = project(pa['verts'], pa['cam'], W * ss, H * ss)
    A = pa['verts'][:, 3]
    img = np.zeros((H * ss, W * ss), np.float32)
    for a, b, c in pa['tris']:
        p = S[[a, b, c]]
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W * ss - 1), min(y1, H * ss - 1)
        if x1 < x0 or y1 < y0:
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
        (ax, ay), (bx, by), (cx, cy) = p
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        val = np.where(inside, w0 * A[a] + w1 * A[b] + w2 * A[c], 0.0)
        sub = img[y0:y1 + 1, x0:x1 + 1]
        np.maximum(sub, val, out=sub)
    return np.array(Image.fromarray(img).resize((W, H), Image.BOX))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out')
    ap.add_argument('tags', nargs='+')
    ap.add_argument('--size', default='1920,1080')
    a = ap.parse_args()
    W, H = (int(x) for x in a.size.split(','))
    acc = np.zeros((H, W), np.float32)
    for rel in a.tags:
        pa = load(rel)
        r = raster(pa, W, H)
        print('%-70s %4d verts %4d tris  cam %s  alpha %.2f-%.2f' % (
            rel, len(pa['verts']), len(pa['tris']), pa['cam'], pa['verts'][:, 3].min(), pa['verts'][:, 3].max()))
        acc = np.maximum(acc, r)
    Image.fromarray((np.clip(acc, 0, 1) * 255).astype(np.uint8)).save(a.out)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
