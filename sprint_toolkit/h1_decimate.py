r"""Fewer triangles for a port's render model -- Halo 1's 32 MiB MODEL BUFFER (H1_PORT_PLAN 0.1:
tool build-cache-file crashes once a map's model vertices x 68 + strip indices x 2 pass 32 MiB;
the Reach / Halo 4 sources carry 5-11x the triangles of a Halo 3 port).

A port opts in with `model['decimate'] = {'keep': <% of triangles>, ...}` in its config. The model
step (h1_h3_weapon_model.models) then runs Blender's collapse decimation on the JMS before `tool
model`, world and fp alike (h1_decimate_blend.py, in Blender, background):
  * what the player SEES in first person is collapsed last: `views` (written by `set`, from the
    port's FP animations: idle / moving / fire weight 1, ready / reload / melee / put away 0.5)
    -- a vertex inside a view's frustum whose ray from the eye is not blocked gets that weight
    in a protect group; `protect` = the decimator's group factor (default 1.0);
  * `lock` [Halo 1 material names] + every material with <= 64 triangles stay whole (displays,
    glows, decals, numerals: their UV islands are exact);
  * node (bone) weights ride along as vertex groups, the source normals are transferred back.
The views are stored in the config (model space, wu) so the model step never reads the FP
animations the later retarget step writes.

    python h1_decimate.py show <key>                    materials, triangles, the setting, cost
    python h1_decimate.py preview <key> --keep 45 [--render]
        decimate in memory only: cost, shape error (mm); --render: out\decimate_<key>_<keep>.png,
        the first-person view (FP idle, 70 deg, hands not drawn) + a side view, full vs kept
    python h1_decimate.py set <key> --keep 45 [--protect 1.0]
        writes model['decimate'] (keep, protect, views) into ports_h1/<key>.py; the port's model
        step must then be rerun (a DONE port: 'rework' first -- H1_PORT_PLAN 2b)
    python h1_decimate.py set <key> --off               removes it
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
BLENDER = r'F:\Tools\blender-5.2.2-windows-x64\blender.exe'
SCRIPT = os.path.join(HERE, 'h1_decimate_blend.py')
SMALL = 64                      # a material with this many triangles or fewer is never decimated
CAP = 32 * 1024 * 1024          # Halo 1's model buffer, vertices x 68 + strip indices x 2
# FP animations a view is sampled from, and the view's weight
VIEW_ANIMS = (('first-person idle', 1.0), ('first-person moving', 1.0), ('first-person fire-1', 1.0),
              ('first-person ready', 0.5), ('first-person reload-empty', 0.5),
              ('first-person reload-full', 0.5), ('first-person melee', 0.5),
              ('first-person put away', 0.5))


def locked(jm, D):
    names = [m.name for m in jm.materials]
    count = [0] * len(names)
    for t in jm.tris:
        count[t.shader] += 1
    want = set(D.get('lock', ()))
    return sorted(i for i, n in enumerate(names) if n in want or count[i] <= SMALL)


def decimate_jms(jm, D, label=''):
    """`jm` (reclaimer JmsModel) decimated in place to D['keep'] % of its triangles."""
    from reclaimer.model.jms.file import JmsTriangle, JmsVertex
    V = [[v.pos_x, v.pos_y, v.pos_z, v.norm_i, v.norm_j, v.norm_k, v.tex_u, v.tex_v,
          v.node_0, v.node_1 if v.node_1_weight > 0 else -1, v.node_1_weight if v.node_1_weight > 0 else 0.0]
         for v in jm.verts]
    T = [[t.region, t.shader, t.v0, t.v1, t.v2] for t in jm.tris]
    J = {'verts': V, 'tris': T, 'keep': D['keep'] / 100.0, 'lock': locked(jm, D),
         'protect': D.get('protect', 1.0), 'floor': D.get('floor', 0.0),
         # views are stored in wu, the JMS in JMS units (x100)
         'views': [[[c * 100 for c in e], list(f), list(u), w] for e, f, u, w in D.get('views', ())]}
    tmp = tempfile.mkdtemp(prefix='h1_decimate_')
    src, dst = os.path.join(tmp, 'in.json'), os.path.join(tmp, 'out.json')
    json.dump(J, open(src, 'w'))
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '-P', SCRIPT, '--', src, dst],
                       capture_output=True, text=True, errors='replace')
    if not os.path.exists(dst):
        raise SystemExit('h1_decimate: Blender failed (%s)\n%s' % (label, (r.stdout + r.stderr)[-3000:]))
    O = json.load(open(dst))
    for f in (src, dst):
        os.remove(f)
    os.rmdir(tmp)
    n0 = len(jm.tris)
    jm.verts[:] = [JmsVertex(int(x[8]), x[0], x[1], x[2], x[3], x[4], x[5], int(x[9]), x[10], x[6], x[7])
                   for x in O['verts']]
    jm.tris[:] = [JmsTriangle(int(t[0]), int(t[1]), int(t[2]), int(t[3]), int(t[4])) for t in O['tris']]
    prot = re.search(r'protected vertices: (\d+) of (\d+)', r.stdout)
    print('   decimate %s: keep %s%% -> %d of %d triangles, %d verts%s' % (
        label, D['keep'], len(jm.tris), n0, len(jm.verts),
        ', FP-visible protected %s/%s' % prot.groups() if prot else ''))
    return jm


def fp_views(key):
    """[(eye, forward, up, weight)] in the port's MODEL space (wu): Halo 1's FP camera (origin,
    looking +x, +z up; fp_render's space) mapped back through the gun's most-weighted node,
    sampled at the first / middle / last frame of each FP animation in VIEW_ANIMS."""
    import ports_h1
    import fp_render as F
    from reclaimer.hek.defs.mod2 import mod2_def
    from reclaimer.hek.defs.antr import antr_def
    P = ports_h1.load(key)
    pk = P['pickable']
    d = mod2_def.build(filepath=os.path.join(F.TAGS, pk['fp_anims'] + '.gbxmodel')).data.tagdata
    nodes = d.nodes.STEPTREE
    names = [n.name for n in nodes]
    parents = [names[n.parent_node] if n.parent_node >= 0 else None for n in nodes]
    bind = {n.name: ((n.rotation.w, n.rotation.i, n.rotation.j, n.rotation.k),
                     (n.translation.x, n.translation.y, n.translation.z)) for n in nodes}
    weight = [0.0] * len(nodes)
    for p in d.geometries.STEPTREE[0].parts.STEPTREE:
        loc = ([ln for ln in p.local_nodes][:p.local_node_count] if p.flags.ZONER else None)
        for v in p.uncompressed_vertices.STEPTREE:
            for ni, w in ((v.node_0_index, v.node_0_weight), (v.node_1_index, v.node_1_weight)):
                if ni >= 0 and w > 0:
                    weight[ni if loc is None else loc[ni]] += w
    body = names[weight.index(max(weight))]
    Wb = F.compose(names, parents, bind)
    have = [a.name for a in antr_def.build(filepath=os.path.join(F.TAGS, pk['fp_anims'] + '.model_animations'))
            .data.tagdata.animations.STEPTREE]
    views = []
    for anim, w in VIEW_ANIMS:
        if anim not in have:
            continue
        frames = F.anim_pose(pk['fp_anims'], anim, 0)[3]
        for fr in sorted({0, frames // 2, max(0, frames - 1)}):
            nn, par, local, _n = F.anim_pose(pk['fp_anims'], anim, fr)
            world = F.compose(nn, par, local)
            if body not in world:
                continue
            # model point m -> FP space: world[body] o inverse(Wb[body]); its inverse maps FP -> model
            inv = F.inverse(world[body])

            def to_model(p):
                return F.xform(Wb[body], F.xform(inv, p))
            e = to_model((0.0, 0.0, 0.0))
            fx = [a - b for a, b in zip(to_model((1.0, 0.0, 0.0)), e)]
            uz = [a - b for a, b in zip(to_model((0.0, 0.0, 1.0)), e)]
            views.append((tuple(round(c, 4) for c in e), tuple(round(c, 4) for c in fx),
                          tuple(round(c, 4) for c in uz), w))
    return views


def base_jms(key, which='world'):
    """The port's JMS as the model step builds it before decimation."""
    import ports_h1
    import h1_h3_weapon_model as M
    return M.base_jms(ports_h1.load(key)['model'], which)


def cost(jm):
    """Model buffer bytes of a JMS once built: vertices x 68 + ~1.5 strip indices a triangle x 2."""
    uniq = {(round(v.pos_x, 3), round(v.pos_y, 3), round(v.pos_z, 3), round(v.norm_i, 3), round(v.norm_j, 3),
             round(v.norm_k, 3), round(v.tex_u, 5), round(v.tex_v, 5), v.node_0, v.node_1) for v in jm.verts}
    return len(uniq) * 68 + int(len(jm.tris) * 1.5) * 2


def cmd_show(key):
    import ports_h1
    w = ports_h1.load(key)['model']
    jm = base_jms(key)
    cnt = {}
    for t in jm.tris:
        cnt[t.shader] = cnt.get(t.shader, 0) + 1
    D = w.get('decimate')
    lk = locked(jm, D or {})
    print('%s: %d triangles, %d verts, ~%.3f MiB of the model buffer (undecimated)'
          % (key, len(jm.tris), len(jm.verts), cost(jm) / 2 ** 20))
    for i, m in enumerate(jm.materials):
        print('   %-44s %6d tris%s' % (m.name, cnt.get(i, 0), '  LOCKED' if i in lk else ''))
    print('setting:', {k: v for k, v in D.items() if k != 'views'} if D else 'none (full detail)',
          '(%d views)' % len(D.get('views', ())) if D else '')


def cmd_preview(key, keep, protect, render=False, floor=0.0):
    jm = base_jms(key)
    import copy
    full = copy.deepcopy(jm)
    D = {'keep': keep, 'protect': protect, 'floor': floor, 'views': fp_views(key)}
    import ports_h1
    D['lock'] = ports_h1.load(key)['model'].get('decimate', {}).get('lock', ())
    decimate_jms(jm, D, key)
    # shape error: every source vertex to the nearest decimated triangle (numpy, brute force per chunk)
    import numpy as np
    P = np.array([(v.pos_x, v.pos_y, v.pos_z) for v in full.verts]) / 100.0
    Q = np.array([(v.pos_x, v.pos_y, v.pos_z) for v in jm.verts]) / 100.0
    A, B_, C = (Q[[getattr(t, k) for t in jm.tris]] for k in ('v0', 'v1', 'v2'))
    err = np.array([_tri_dist(p, A, B_, C) for p in P[::max(1, len(P) // 4000)]])
    print('   cost ~%.3f MiB (was %.3f); shape error mean %.2f mm, 99%% %.2f mm, max %.2f mm'
          % (cost(jm) / 2 ** 20, cost(full) / 2 ** 20, err.mean() * 3048, np.percentile(err, 99) * 3048,
             err.max() * 3048))
    if not render:
        return
    d = os.path.join(HERE, 'out', 'decimate_%s' % key)
    os.makedirs(d, exist_ok=True)
    pose = _fp_pose(key)
    tag = '%g' % keep
    for name, m in (('full', full), (tag, jm)):
        _write_obj(os.path.join(d, name + '.obj'), m, None)
        _write_obj(os.path.join(d, name + '_fp.obj'), m, pose)
    subprocess.run([BLENDER, '-b', '--factory-startup', '-P', os.path.join(HERE, 'h1_decimate_render.py'),
                    '--', d, 'full', tag], capture_output=True)
    from PIL import Image, ImageChops, ImageDraw
    fp = [Image.open(os.path.join(d, n + '_fp.png')).convert('RGB') for n in ('full', tag)]
    sd = [Image.open(os.path.join(d, n + '_side.png')).convert('RGB') for n in ('full', tag)]
    bg = Image.new('RGB', fp[0].size, fp[0].getpixel((0, 0)))
    b = ImageChops.difference(fp[0], bg).getbbox() or (0, 0, 1920, 1080)
    b = (max(0, b[0] - 20), max(0, b[1] - 20), min(1920, b[2] + 20), min(1080, b[3] + 20))
    cw = 960
    fp = [i.crop(b).resize((cw, int((b[3] - b[1]) * cw / (b[2] - b[0])))) for i in fp]
    sd = [i.resize((cw, int(i.height * cw / i.width))) for i in sd]
    sheet = Image.new('RGB', (2 * cw + 10, 40 + fp[0].height + 10 + sd[0].height), (12, 12, 14))
    dr = ImageDraw.Draw(sheet)
    for i, label in enumerate(('full detail: %d triangles, ~%.2f MiB' % (len(full.tris), cost(full) / 2 ** 20),
                               '%s%%: %d triangles, ~%.2f MiB' % (tag, len(jm.tris), cost(jm) / 2 ** 20))):
        dr.text((i * (cw + 10) + 8, 12), label, fill=(235, 235, 235))
        sheet.paste(fp[i], (i * (cw + 10), 40))
        sheet.paste(sd[i], (i * (cw + 10), 40 + fp[0].height + 10))
    out = os.path.join(HERE, 'out', 'decimate_%s_%s.png' % (key, tag))
    sheet.save(out)
    print('   first person (top, idle frame 0, hands not drawn) + side:', out)


def _fp_pose(key):
    """{node name: (posed world, inverse bind)} for the port's FP idle, frame 0 (fp_render)."""
    import ports_h1
    import fp_render as F
    from reclaimer.hek.defs.mod2 import mod2_def
    pk = ports_h1.load(key)['pickable']
    d = mod2_def.build(filepath=os.path.join(F.TAGS, pk['fp_anims'] + '.gbxmodel')).data.tagdata
    nodes = d.nodes.STEPTREE
    names = [n.name for n in nodes]
    parents = [names[n.parent_node] if n.parent_node >= 0 else None for n in nodes]
    bind = {n.name: ((n.rotation.w, n.rotation.i, n.rotation.j, n.rotation.k),
                     (n.translation.x, n.translation.y, n.translation.z)) for n in nodes}
    Wb = F.compose(names, parents, bind)
    nn, par, local, _n = F.anim_pose(pk['fp_anims'], 'first-person idle', 0)
    world = F.compose(nn, par, local)
    return {n: (world.get(n, Wb[n]), F.inverse(Wb[n])) for n in names}


def _write_obj(path, jm, pose):
    """A JMS as OBJ in wu (normals, uvs); `pose` skins it into Halo 1's FP view space."""
    import fp_render as F
    names = [n.name for n in jm.nodes]
    with open(path, 'w') as f:
        for v in jm.verts:
            p = (v.pos_x / 100.0, v.pos_y / 100.0, v.pos_z / 100.0)
            nrm = (v.norm_i, v.norm_j, v.norm_k)
            if pose:
                acc, accn, tot = [0.0] * 3, [0.0] * 3, 0.0
                for ni, w in ((v.node_0, 1.0 - max(0.0, v.node_1_weight)), (v.node_1, v.node_1_weight)):
                    if ni is None or ni < 0 or w <= 0:
                        continue
                    wp, ib = pose[names[ni]]
                    q = F.xform(wp, F.xform(ib, p))
                    r = F.qrot(wp[0], F.qrot(ib[0], nrm))
                    acc = [a + w * c for a, c in zip(acc, q)]
                    accn = [a + w * c for a, c in zip(accn, r)]
                    tot += w
                p = tuple(c / (tot or 1.0) for c in acc)
                nrm = tuple(accn)
            f.write('v %.6f %.6f %.6f\nvn %.5f %.5f %.5f\nvt %.6f %.6f\n' % (p + nrm + (v.tex_u, v.tex_v)))
        for t in jm.tris:
            a, b, c = t.v0 + 1, t.v1 + 1, t.v2 + 1
            f.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (a, a, a, b, b, b, c, c, c))


def _tri_dist(p, A, B, C):
    """Distance from p to the nearest of the triangles (A, B, C arrays): closest point on each."""
    import numpy as np
    ab, ac, ap = B - A, C - A, p - A
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp, cp = p - B, p - C
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    den = va + vb + vc
    den[den == 0] = 1e-12
    v = vb / den
    w = vc / den
    X = A + ab * v[:, None] + ac * w[:, None]
    # outside the triangle: fall back to the nearest vertex / edge (cheap, conservative)
    out = (v < 0) | (w < 0) | (v + w > 1)
    if out.any():
        best = np.minimum(np.minimum(((p - A) ** 2).sum(1), ((p - B) ** 2).sum(1)), ((p - C) ** 2).sum(1))
        for P0, P1 in ((A, B), (B, C), (C, A)):
            e = P1 - P0
            tt = np.clip(((p - P0) * e).sum(1) / np.maximum((e * e).sum(1), 1e-12), 0, 1)
            best = np.minimum(best, ((P0 + e * tt[:, None] - p) ** 2).sum(1))
        X2 = ((X - p) ** 2).sum(1)
        X2[out] = best[out]
        return math.sqrt(X2.min())
    return math.sqrt(((X - p) ** 2).sum(1).min())


def cmd_set(key, keep, protect, off=False):
    path = os.path.join(HERE, 'ports_h1', key + '.py')
    raw = open(path, 'rb').read().decode()
    NL = '\r\n' if '\r\n' in raw else '\n'
    lines = raw.replace('\r\n', '\n').split('\n')
    old = [i for i, l in enumerate(lines) if l.startswith("        'decimate': ")]
    for i in reversed(old):
        del lines[i]
    if not off:
        import ports_h1
        lock = ports_h1.load(key)['model'].get('decimate', {}).get('lock')
        D = {'keep': keep, 'protect': protect}
        if lock:
            D['lock'] = list(lock)
        D['views'] = fp_views(key)
        at = [i for i, l in enumerate(lines) if l.startswith("        'world_name': ")]
        if len(at) != 1:
            raise SystemExit('%s: no single model world_name line to put decimate after' % path)
        lines.insert(at[0] + 1, "        'decimate': %r," % (D,))
        print('%s: decimate keep %s%%, protect %s, %d FP views' % (key, keep, protect, len(D['views'])))
    else:
        print('%s: decimate removed' % key)
    open(path, 'wb').write(NL.join(lines).encode())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=('show', 'preview', 'set'))
    ap.add_argument('key')
    ap.add_argument('--keep', type=float, help='% of the triangles kept')
    ap.add_argument('--protect', type=float, default=1.0)
    ap.add_argument('--floor', type=float, default=0.0, help='protect weight of what FP never shows')
    ap.add_argument('--off', action='store_true')
    ap.add_argument('--render', action='store_true', help='preview: first-person + side views, full vs kept')
    a = ap.parse_args()
    import port_env  # noqa: F401
    if a.verb == 'show':
        cmd_show(a.key)
    elif a.verb == 'preview':
        cmd_preview(a.key, a.keep, a.protect, a.render, a.floor)
    else:
        if not a.off and not a.keep:
            raise SystemExit('set needs --keep N (or --off)')
        cmd_set(a.key, a.keep, a.protect, a.off)


if __name__ == '__main__':
    main()
