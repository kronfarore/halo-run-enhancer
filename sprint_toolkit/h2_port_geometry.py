r"""Step 1 of a Halo 2 port: the source weapon's mesh -> Halo 2 JMS 8210 on the DONOR's skeleton.

Generalized from saw_to_jms_h2.py (the SAW, 2026-09-23; see its notes, all still true) for every
`ports_h2/<key>.py` config's `geometry` section. Each value the SAW had as a module constant is a
key of that section:

    kind            'h4_dump' (the only reader so far: an H4 render-model XML dump, h4_rm.load).
                    Halo 3 / Reach sources need their reader added here by the wave's pilot
                    (Halo 1's wave A read H3 render models with h3_rm_to_jms; the H2 skeleton
                    work is in H2_PORT_PLAN 0.4)
    dump            the source dump
    data_dir        data\<data_dir>\render\<world>.jms, \<fp>\render\<fp>.jms
    world, fp       the world / first-person model names
    donor_fp_jms, donor_world_jms   the donor's AUTHORED jms under data\!extracted
                    (tool extract-render-data <donor render model>)
    scale, part_material, node_map, lift, fp_nudge, muzzle_drop, marker_from, min_tris
    fp_species      {species: {'sub': model name, 'nudge': (x, y, z)}} -- a second FP model
    render          [folders under the weapon's parent dir] for `tool render` (--render)

    python h2_port_geometry.py <key> [--only world,fp,<sub>] [--render] [--dump <xml>] [scale]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_jms  # noqa: E402
import ports_h2  # noqa: E402

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
EXTRACTED = os.path.join(H2EK, 'data', '!extracted')
UNITS = 100.0                   # JMS units per world unit


class Geo:
    """One config's geometry section, with saw_to_jms_h2's defaults."""
    def __init__(self, g):
        self.g = g
        self.scale = g.get('scale', 1.0)
        self.part_material = g['part_material']
        self.lift = g.get('lift')
        self.fp_nudge = tuple(g.get('fp_nudge', (0.0, 0.0, 0.0)))
        self.muzzle_drop = g.get('muzzle_drop', 0.0)
        self.marker_from = g.get('marker_from', {})
        self.min_tris = g.get('min_tris', 1000)


def decompress(rm):
    """Raw vertices are stored 0..1 across the mesh's bounds; hand back JMS units."""
    ci = rm['compression']
    (x0, x1, y0), (y1, z0, z1) = ci['pos0'], ci['pos1']
    (u0, u1), (v0, v1) = ci['uv0'], ci['uv1']
    lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
    out = []
    for v in rm['meshes'][0]['verts']:
        pos = tuple((lo[k] + v['pos'][k] * span[k]) * UNITS for k in range(3))
        u = u0 + v['uv'][0] * (u1 - u0)
        # JMS v is 1 - the tag's v (measured on the GPMG, saw_to_jms_h2)
        tv = 1.0 - (v0 + v['uv'][1] * (v1 - v0))
        out.append((pos, v['n'] or (0.0, 0.0, 1.0), (u, tv), v['nodes'], v['w']))
    return out


def measure_lift(geo, src, template, anchor):
    """How far to raise the mesh so its vertical band sits where the donor's does."""
    port = [pos[2] * geo.scale + anchor[2] for pos, _n, _uv, _nodes, _w in src]
    donor = [v.pos[2] for v in template.verts]
    if not donor:
        return 0.0
    return ((min(donor) + max(donor)) - (min(port) + max(port))) / 2.0


def convert(geo, rm, template, node_map, lift=0.0, nudge=(0.0, 0.0, 0.0)):
    """A Halo 2 JMS: the source mesh under the template's skeleton and markers."""
    src = decompress(rm)
    anchor = {mk.name: mk for mk in template.markers}['right_hand'].pos
    anchor = (anchor[0] + nudge[0], anchor[1] + nudge[1], anchor[2] + lift + nudge[2])

    out = h2_jms.Model()
    out.nodes = list(template.nodes)

    mats, mat_index = [], {}
    for part in rm['meshes'][0]['parts']:
        name = geo.part_material.get(part['material'])
        if name is not None and name not in mat_index:
            mat_index[name] = len(mats)
            # "(1) base gun": LOD 1, permutation, region -- there is no REGIONS section
            mats.append(h2_jms.Material(name, '(1) %s %s'
                                        % (template.materials[0].permutation,
                                           template.materials[0].region)))
    out.materials = mats

    for pos, normal, uv, nodes, weights in src:
        p = tuple(pos[k] * geo.scale + anchor[k] for k in range(3))
        infl = [(node_map[n], w) for n, w in zip(nodes, weights) if n >= 0 and w > 0]
        infl.sort(key=lambda t: -t[1])
        if not infl:
            infl = [(node_map[0], 1.0)]
        total = sum(w for _n, w in infl)
        infl = [(n, w / total) for n, w in infl]
        out.verts.append(h2_jms.Vertex(p, normal, infl, [uv]))

    indices = rm['meshes'][0]['indices']
    for part in rm['meshes'][0]['parts']:
        name = geo.part_material.get(part['material'])
        if name is None:
            continue
        idx = indices[part['start']:part['start'] + part['count']]
        for i in range(0, len(idx) - 2, 3):
            out.tris.append((mat_index[name], (idx[i], idx[i + 1], idx[i + 2])))

    # A weapon is thousands of triangles; fewer means the part map and the dump disagree
    # about what the render method indices mean (the SAW's two-triangle weapon).
    if len(out.tris) < geo.min_tris:
        raise SystemExit('only %d triangles came through: this dump numbers its parts '
                         'differently (%s).'
                         % (len(out.tris), [(p['material'], p['count']) for p in rm['meshes'][0]['parts']]))

    by_name = {}
    for m in rm['markers']:
        by_name.setdefault(m['name'], m)          # duplicates: take the first
    for mk in template.markers:
        src_mk = by_name.get(geo.marker_from.get(mk.name, ''))
        pos = mk.pos
        if src_mk:
            pos = tuple(src_mk['pos'][k] * UNITS * geo.scale + anchor[k] for k in range(3))
            if mk.name == 'primary_trigger':
                pos = (pos[0], pos[1], pos[2] - geo.muzzle_drop)
        out.markers.append(h2_jms.Marker(mk.name, mk.node, mk.rot, pos, mk.radius))
    return out


def jobs(g):
    """(label, template, output, is_fp, nudge or None) for every model of the section."""
    base = os.path.join(H2EK, 'data', g['data_dir'])
    fp_t = os.path.join(EXTRACTED, g['donor_fp_jms'])
    out = [('fp', fp_t, os.path.join(base, g['fp'], 'render', g['fp'] + '.jms'), True, None),
           ('world', os.path.join(EXTRACTED, g['donor_world_jms']),
            os.path.join(base, 'render', g['world'] + '.jms'), False, None)]
    for sp, d in (g.get('fp_species') or {}).items():
        out.append((d['sub'], fp_t, os.path.join(base, d['sub'], 'render', d['sub'] + '.jms'),
                     True, tuple(d['nudge'])))
    return out


def tool_render(g, what):
    parent = os.path.dirname(g['data_dir'])
    for sub in what:
        rel = os.path.join(parent, sub)
        p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'render', rel], cwd=H2EK,
                           capture_output=True, text=True, errors='replace')
        text = ((p.stdout or '') + (p.stderr or '')).replace('\r', '\n')
        tri = [ln.strip() for ln in text.split('\n') if 'triangle' in ln.lower() or 'error' in ln.lower()]
        print('   tool render %s: %s' % (rel, '; '.join(tri[-3:]) or 'done'))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    key, rest = argv[0], argv[1:]
    g = ports_h2.get(key, 'geometry')
    geo = Geo(g)
    args = [a for a in rest if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in rest if a.startswith('--'))
    if g.get('kind') != 'h4_dump':
        raise SystemExit('geometry kind %r has no reader yet -- the wave pilot adds it here'
                         % g.get('kind'))
    import h4_rm
    rm = h4_rm.load(opts.get('dump') or g['dump'])
    if args:
        geo.scale = float(args[0])
    print('%s: scale %s' % (key, geo.scale))
    only = set(filter(None, opts.get('only', '').split(',')))
    for label, tmpl_path, out_path, is_fp, nudge in jobs(g):
        if only and label not in only:
            continue
        template = h2_jms.read(tmpl_path)
        names = [n.name for n in template.nodes]
        node_map = {int(k): names.index(v) for k, v in g['node_map'].items()}
        lift = 0.0
        use_nudge = nudge if nudge is not None else geo.fp_nudge
        if is_fp:
            anchor = {mk.name: mk for mk in template.markers}['right_hand'].pos
            lift = geo.lift if geo.lift is not None else measure_lift(geo, decompress(rm),
                                                                      template, anchor)
            print('   %s: lifting the first person mesh %.2f units, nudging %s'
                  % (label, lift, use_nudge))
        jm = convert(geo, rm, template, node_map, lift,
                     use_nudge if lift else (0.0, 0.0, 0.0))
        h2_jms.write(out_path, jm)
        xs = [v.pos[0] for v in jm.verts]
        zs = [v.pos[2] for v in jm.verts]
        print('wrote %s' % out_path)
        print('   %d verts, %d tris, materials %s'
              % (len(jm.verts), len(jm.tris), [(m.name, m.spec) for m in jm.materials]))
        print('   x %.2f..%.2f  z %.2f..%.2f' % (min(xs), max(xs), min(zs), max(zs)))
        for mk in jm.markers:
            was = {m.name: m for m in template.markers}[mk.name].pos
            moved = '   MOVED from %s' % (tuple(round(c, 2) for c in was),) if mk.pos != was else ''
            print('   marker %-18s %s%s' % (mk.name, tuple(round(c, 2) for c in mk.pos), moved))
    if '--render' in rest:
        tool_render(g, g.get('render') or [])


if __name__ == '__main__':
    main()
