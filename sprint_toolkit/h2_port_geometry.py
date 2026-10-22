r"""Step 1 of a Halo 2 port: the source weapon's mesh -> Halo 2 JMS 8210 on the DONOR's skeleton.

Generalized from saw_to_jms_h2.py (the SAW, 2026-09-23; see its notes, all still true) for every
`ports_h2/<key>.py` config's `geometry` section. Each value the SAW had as a module constant is a
key of that section:

    kind            'h4_dump' (an H4 render-model XML dump onto the donor's skeleton, h4_rm.load)
                    or 'h3' (a Halo 3 render model on its OWN skeleton -- h3_convert; the AR
                    pilot, 2026-10-20) or 'h1' (a Halo 1 gbxmodel on its OWN skeleton -- h1_convert;
                    the Flamethrower, S1). A Reach reader is wave B's pilot's to add
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
        self.part_material = g.get('part_material')
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


def _qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def _qrot(q, v):
    w, x, y, z = q
    p = _qmul(_qmul(q, (0.0, v[0], v[1], v[2])), (w, -x, -y, -z))
    return p[1:]


def h3_convert(g, rel, world):
    """kind 'h3' (the Assault Rifle, the wave-A pilot, 2026-10-20): a Halo 3 render model as a
    Halo 2 JMS on its OWN skeleton -- no donor template. Halo 3's FP arms ARE Halo 2's
    (H2_PORT_PLAN 0.4), so the port keeps its source's weapon nodes (the AR's gun, magazine,
    ophandle, safety, switch) and its own Halo 3 FP animations drive them (h2_port_fp_anims.py).

    Conventions, measured on the masterchief FP arms (H3 fp.render_model vs Bungie's own H2
    fp_arms.jms, every node equal): a JMS 8210 node = the Halo 3 bind COMPOSED into model space
    (translation x100, the rotation as Halo 3 stores it, sign flipped to w <= 0 as Bungie writes
    it); a MARKER stays node-relative exactly as Halo 3's (x100); vertices model space x100,
    v = 1 - the tag's (h3_rm_to_jms / saw_to_jms_h2), indices triangle strips.

    Section keys: world_rm / fp_rm (H3EK render model tags), node_names {h3: H2 JMS name}
    (default 'frame <name>'), materials {Halo 3 shader basename: H2 material name, None =
    dropped; Bungie's name SYMBOLS may follow, e.g. `=?` on the BR's counter digits},
    regions {H2 material: region}, permutation / region (FP), world_permutation /
    world_region (what the world .model's variants name; default 'standard'), markers
    {Halo 3 marker: H2 name} (unlisted markers dropped), muzzle_drop, ground_point."""
    import h4_rm
    import h1_fp_retarget
    import h3_rm_to_jms as H3
    rm = h4_rm.load(h1_fp_retarget.export_xml(rel))
    names = g.get('node_names', {})
    out = h2_jms.Model()
    # fp_root_identity (the Spike Rifle, boot 1, 2026-10-21): Halo 2 MIRRORS the left-hand dual
    # weapon across its root node's local y. Bungie's FP guns bind that node at identity (y =
    # sideways); Halo 3's FP Spiker binds it turned 180 deg about the y=z diagonal (local y = UP),
    # so the left gun came out UPSIDE DOWN. The root's bind becomes identity at the same place;
    # vertices are model space (unchanged), markers on the root are re-expressed in the new frame,
    # and h2_port_fp_anims `root_identity` re-expresses the root's animated frames to match
    root_q = None
    if not world and g.get('fp_root_identity'):
        root_q = H3._world(rm['nodes'], 0)[0]
    for i, n in enumerate(rm['nodes']):
        q, p = H3._world(rm['nodes'], i)
        if i == 0 and root_q is not None:
            q = (0.0, 0.0, 0.0, -1.0)
        if q[3] > 0:
            q = tuple(-c for c in q)
        par = n['parent'] if n['parent'] is not None and n['parent'] >= 0 else -1
        out.nodes.append(h2_jms.Node(names.get(n['name'], 'frame ' + n['name']), par, q,
                                     tuple(c * UNITS for c in p)))
    mats, mat_index, src_mat = [], {}, {}
    for k, path in enumerate(rm['materials']):
        base = (path or '').rsplit('\\', 1)[-1]
        name = g['materials'].get(base)
        if name is None:
            continue
        if name not in mat_index:
            mat_index[name] = len(mats)
            # the WORLD model's region / permutation must be the ones its .model's variants name
            # (the BR's: `base` / `gun`; a mismatch renders nothing), the FP model's are free
            perm = g.get('world_permutation' if world else 'permutation', 'standard')
            region = g.get('regions', {}).get(name) or g.get('world_region' if world else 'region',
                                                             'standard')
            mats.append(h2_jms.Material(name, '(%d) %s %s' % (len(mats) + 1, perm, region)))
        src_mat[k] = mat_index[name]
    out.materials = mats
    ci = rm['compression']
    (x0, x1, y0), (y1, z0, z1) = ci['pos0'], ci['pos1']
    (u0, u1), (v0, v1) = ci['uv0'], ci['uv1']
    lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
    for me in rm['meshes']:
        base = len(out.verts)
        for v in me['verts']:
            pos = tuple((lo[k] + v['pos'][k] * span[k]) * UNITS for k in range(3))
            uv = (u0 + v['uv'][0] * (u1 - u0), 1.0 - (v0 + v['uv'][1] * (v1 - v0)))
            infl = sorted([(n, w) for n, w in zip(v['nodes'], v['w']) if n >= 0 and w > 0],
                          key=lambda t: -t[1]) or [(0, 1.0)]
            tot = sum(w for _n, w in infl)
            out.verts.append(h2_jms.Vertex(pos, v['n'] or (0.0, 0.0, 1.0),
                                           [(n, w / tot) for n, w in infl], [uv]))
        strip = 'strip' in (me['index_type'] or '')
        for part in me['parts']:
            if part['material'] not in src_mat:
                continue
            idx = me['indices'][part['start']:part['start'] + part['count']]
            tris = H3.strip_tris(idx) if strip else [tuple(idx[i:i + 3])
                                                     for i in range(0, len(idx) - 2, 3)]
            for a, b, c in tris:
                out.tris.append((src_mat[part['material']], (base + a, base + b, base + c)))
    if len(out.tris) < g.get('min_tris', 1000):
        raise SystemExit('only %d triangles from %s' % (len(out.tris), rel))
    for m in rm['markers']:
        nm = g.get('markers', {}).get(m['name'])
        if nm is None:
            continue
        pos = [c * UNITS for c in m['pos']]
        rot = m['rot']
        if root_q is not None and m['node'] == 0:
            # root-relative: p' = R_root p (the same model-space point from the identity root);
            # the marker's own rotation composed the same way
            x, y, z, w = root_q
            pos = list(_qrot((w, x, y, z), pos))
            mx, my, mz, mw = rot
            r = _qmul((w, x, y, z), (mw, mx, my, mz))
            rot = (r[1], r[2], r[3], r[0])
        if nm in ('primary_trigger', 'primary trigger'):
            pos[2] -= g.get('muzzle_drop', 0.0)
        out.markers.append(h2_jms.Marker(nm, m['node'], rot, pos, -1.0))
    gp = g.get('ground_point')
    if world and gp:
        # the middle of the model's x and z extent on its -y surface (Halo 1's 'auto', the
        # user's rule for every port), the rotation of Bungie's own (the SMG's) ground point;
        # on node 0, whose bind is identity at the origin in a Halo 3 weapon
        xs = [v.pos[0] for v in out.verts]
        ys = [v.pos[1] for v in out.verts]
        zs = [v.pos[2] for v in out.verts]
        out.markers.append(h2_jms.Marker('ground point', 0, tuple(gp['rot']),
                                         ((min(xs) + max(xs)) / 2.0, min(ys),
                                          (min(zs) + max(zs)) / 2.0), -1.0))
    return out


def h1_convert(g, rel, world):
    """kind 'h1' (the Flamethrower, S1, 2026-10-21): a Halo 1 gbxmodel (HCEEK) as a Halo 2 JMS on
    its OWN skeleton. Halo 1's FP arms ARE Halo 2's masterchief (H2_PORT_PLAN 0.4), so the port keeps
    its source's weapon nodes (the flamethrower's gun, ammo, cover) and Halo 1's own FP animations
    drive them (h2_port_fp_anims.py kind 'h1').

    Conventions: Halo 1 stores the INVERSE rotation (fp_render), so a node's Halo 3-convention local
    rotation is the conjugate; then exactly h3_convert's rule (bind composed into model space x100,
    w <= 0). Vertices are model space (x100), UVs x the gbxmodel's base map scale (0 = 1) with
    v = 1 - v, triangles a strip (-1 padded; even triangles flipped: each face then agrees with its
    vertex normals). Markers: the permutation's local
    markers, or the model's marker block (first instance), node-relative, rotation conjugated.
    The highest LOD (superhigh) of every region / permutation.

    Section keys: world_gbx / fp_gbx (HCEEK gbxmodel paths without extension), node_names {H1 name:
    H2 JMS name} (default: the H1 name, 'frame x'), materials {H1 shader basename or
    'basename#permutation' (a counter's digits): H2 material, None = dropped}, root_identity (bool:
    the root's bind rotation dropped and the vertices re-expressed in its frame -- markers are
    node-relative already), plus h3_convert's world_permutation /
    world_region / permutation / region / markers / muzzle_drop / ground_point."""
    import port_env  # noqa: F401
    import h3_rm_to_jms as H3
    from reclaimer.hek.defs.mod2 import mod2_def
    hceek = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
    d = mod2_def.build(filepath=os.path.join(hceek, rel + '.gbxmodel')).data.tagdata
    names = g.get('node_names', {})
    nodes = []
    for n in d.nodes.STEPTREE:
        rot = (-n.rotation.i, -n.rotation.j, -n.rotation.k, n.rotation.w)      # conjugate
        if n.parent_node < 0 and g.get('root_identity'):
            rot = (0.0, 0.0, 0.0, 1.0)
        nodes.append({'name': n.name, 'parent': n.parent_node,
                      'rot': rot, 'pos': (n.translation.x, n.translation.y, n.translation.z)})
    out = h2_jms.Model()
    for i, n in enumerate(nodes):
        q, p = H3._world(nodes, i)
        if q[3] > 0:
            q = tuple(-c for c in q)
        out.nodes.append(h2_jms.Node(names.get(n['name'], n['name']), n['parent'], q,
                                     tuple(c * UNITS for c in p)))
    # root_identity: the root's bind rotation dropped and the vertices RE-EXPRESSED in its frame (the
    # Flamethrower's world model stores them tilted with its root; its markers are root-relative)
    inv_root = None
    if g.get('root_identity'):
        n0 = d.nodes.STEPTREE[0]
        inv_root = (n0.rotation.i, n0.rotation.j, n0.rotation.k, n0.rotation.w)   # conj of the H3 rot
    us = d.base_map_u_scale or 1.0
    vs = d.base_map_v_scale or 1.0
    mats, mat_index, src_mat = [], {}, {}
    for k, s in enumerate(d.shaders.STEPTREE):
        base = s.shader.filepath.rsplit('\\', 1)[-1]
        # a Halo 1 counter names one shader per digit, told apart by its permutation (0 = ones)
        key = '%s#%d' % (base, s.permutation_index)
        name = g['materials'][key] if key in g['materials'] else g['materials'].get(base)
        if name is None:
            continue
        if name not in mat_index:
            mat_index[name] = len(mats)
            perm = g.get('world_permutation' if world else 'permutation', 'standard')
            region = g.get('regions', {}).get(name) or g.get('world_region' if world else 'region',
                                                             'standard')
            mats.append(h2_jms.Material(name, '(%d) %s %s' % (len(mats) + 1, perm, region)))
        src_mat[k] = mat_index[name]
    out.materials = mats
    geoms = sorted({p.superhigh_geometry_block for r in d.regions.STEPTREE for p in r.permutations.STEPTREE})
    for gi in geoms:
        for part in d.geometries.STEPTREE[gi].parts.STEPTREE:
            if part.shader_index not in src_mat:
                continue
            local = list(part.local_nodes)[:part.local_node_count] if part.flags.ZONER else None
            base = len(out.verts)
            for v in part.uncompressed_vertices.STEPTREE:
                infl = []
                for ni, w in ((v.node_0_index, v.node_0_weight), (v.node_1_index, v.node_1_weight)):
                    if ni >= 0 and w > 0:
                        infl.append((local[ni] if local else ni, w))
                infl = sorted(infl, key=lambda t: -t[1]) or [(0, 1.0)]
                tot = sum(w for _n, w in infl)
                pos, nrm = (v.position_x, v.position_y, v.position_z), (v.normal_i, v.normal_j, v.normal_k)
                if inv_root is not None:
                    pos, nrm = H3._qrot(inv_root, pos), H3._qrot(inv_root, nrm)
                out.verts.append(h2_jms.Vertex(
                    tuple(c * UNITS for c in pos), nrm,
                    [(n, w / tot) for n, w in infl], [(v.u * us, 1.0 - v.v * vs)]))
            strip = []
            for t in part.triangles.STEPTREE:
                strip.extend((t.v0_index, t.v1_index, t.v2_index))
            strip = [i for i in strip if i >= 0]
            for k in range(len(strip) - 2):
                a, b, c = strip[k], strip[k + 1], strip[k + 2]
                if a == b or b == c or a == c:
                    continue
                # Halo 1's strips start CLOCKWISE for Halo 2: the EVEN triangles flip (boots 1-7
                # flipped the odd ones -- every face pointed away from its own normals, the gun drew
                # inside-out: the fuel screen and heat bar culled, the stripes seen only from inside)
                if not k % 2:
                    a, b = b, a
                out.tris.append((src_mat[part.shader_index], (base + a, base + b, base + c)))
    if len(out.tris) < g.get('min_tris', 200):
        raise SystemExit('only %d triangles from %s' % (len(out.tris), rel))
    for card in (() if world else g.get('fp_cards', ())):
        # fp_cards [(material, centre, (width, height)[, axis])]: two crossed cards on node 0, the
        # material's own UVs 0-1 (v along the height) -- the Flamethrower's FIRST-PERSON pilot flame
        # (boot 8: Halo 2 draws attachment effects at the WORLD model's markers, even in FP). axis
        # 'z' (default) = upright; 'x' = the height along the gun's forward axis (a flame licking
        # forward off the barrel: boot 15, 'move it forward and turn it')
        mat, centre, (w, h) = card[:3]
        axis = card[3] if len(card) > 3 else 'z'
        if mat not in mat_index:
            mat_index[mat] = len(mats)
            mats.append(h2_jms.Material(mat, '(%d) %s %s' % (len(mats) + 1,
                                                          g.get('permutation', 'standard'),
                                                          g.get('region', 'standard'))))
        cx, cy, cz = centre
        # (width offset, normal) per card; the height runs along `axis`
        cards = ((((w / 2, 0.0, 0.0), (0.0, -1.0, 0.0)), ((0.0, w / 2, 0.0), (1.0, 0.0, 0.0))) if axis == 'z'
                 else (((0.0, w / 2, 0.0), (0.0, 0.0, 1.0)), ((0.0, 0.0, w / 2), (0.0, -1.0, 0.0))))
        up = (0.0, 0.0, h) if axis == 'z' else (h, 0.0, 0.0)
        for ax, nrm in cards:
            base = len(out.verts)
            for su, sv in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
                pos = tuple(c + su * ax[i] + (sv - 0.5) * up[i] for i, c in enumerate((cx, cy, cz)))
                out.verts.append(h2_jms.Vertex(pos, nrm, [(0, 1.0)], [((su + 1) / 2, float(sv))]))
            k = mat_index[mat]
            for t in ((0, 1, 2), (0, 2, 3), (0, 2, 1), (0, 3, 2)):       # both faces
                out.tris.append((k, tuple(base + i for i in t)))
    sp = g.get('digit_spread')
    if sp:
        # digit_spread ((material A, material B), f): two counter quads pushed APART along the line
        # between their centres, each by f x that distance (the Flamethrower's two digits, boot 4:
        # 'move the digits a bit apart'; Halo 1 drew three side by side)
        # an optional 3rd value SHIFTS both along the row (towards B, x the spacing: boot 8, 'the
        # numbers can be re-aligned' -- they sat over the box divider)
        (ma, mb), f = sp[:2]
        shift = sp[2] if len(sp) > 2 else 0.0
        # a 4th value moves both DOWN the screen by that fraction of A's height (along A's image
        # vertical: its high-v vertices are the top -- boot 9, 'left and down on the box')
        down = sp[3] if len(sp) > 3 else 0.0
        cen, own = {}, {}
        for name in (ma, mb):
            k = mat_index.get(name)
            own[name] = sorted({v for m, t in out.tris if m == k for v in t})
            P = [out.verts[v].pos for v in own[name]]
            cen[name] = [sum(p[i] for p in P) / max(1, len(P)) for i in range(3)]
        d_ab = [cen[mb][i] - cen[ma][i] for i in range(3)]
        hi = [out.verts[v].pos for v in own[ma] if out.verts[v].uvs[0][1] >= 0.5]
        lo = [out.verts[v].pos for v in own[ma] if out.verts[v].uvs[0][1] < 0.5]
        up = [sum(p[i] for p in hi) / max(1, len(hi)) - sum(p[i] for p in lo) / max(1, len(lo))
              for i in range(3)]
        for name, s in ((ma, shift - f), (mb, shift + f)):
            for v in own[name]:
                vx = out.verts[v]
                vx.pos = tuple(vx.pos[i] + s * d_ab[i] - down * up[i] for i in range(3))
    raw = []
    for r in d.regions.STEPTREE:
        for p in r.permutations.STEPTREE:
            raw += [(m.name, m.node_index, m.translation, m.rotation) for m in p.local_markers.STEPTREE]
    for m in d.markers.STEPTREE:
        if m.marker_instances.STEPTREE:
            i = m.marker_instances.STEPTREE[0]
            raw.append((m.name, i.node_index, i.translation, i.rotation))
    seen = set()
    for name, node, t, r in raw:
        nm = g.get('markers', {}).get(name)
        if nm is None or name in seen:
            continue
        seen.add(name)
        pos = (t.x, t.y, t.z)
        rot = (-r.i, -r.j, -r.k, r.w)
        pos = [c * UNITS for c in pos]
        if nm in ('primary_trigger', 'primary trigger'):
            pos[2] -= g.get('muzzle_drop', 0.0)
        out.markers.append(h2_jms.Marker(nm, node, rot, pos, -1.0))
    for nm, node, rot, pos in (g.get('world_extra_markers', ()) if world else ()):
        # markers only the FP model has in Halo 1 (the Flamethrower's pilot / steam vents), placed on
        # the world model where the weapon's attachments look them up (boot 5: the pilot never drew)
        out.markers.append(h2_jms.Marker(nm, node, tuple(rot), list(pos), -1.0))
    gp = g.get('ground_point')
    if world and gp:
        xs = [v.pos[0] for v in out.verts]
        ys = [v.pos[1] for v in out.verts]
        zs = [v.pos[2] for v in out.verts]
        out.markers.append(h2_jms.Marker('ground point', 0, tuple(gp['rot']),
                                         ((min(xs) + max(xs)) / 2.0, min(ys),
                                          (min(zs) + max(zs)) / 2.0), -1.0))
    return out


def h1_jobs(g):
    base = os.path.join(H2EK, 'data', g['data_dir'])
    return [('world', g['world_gbx'], os.path.join(base, 'render', g['world'] + '.jms'), True),
            ('fp', g['fp_gbx'], os.path.join(base, g['fp'], 'render', g['fp'] + '.jms'), False)]


def h3_particle_model(pm):
    """`particle_models` {name: {'from': H3EK .particle_model, 'data_dir', 'material', 'node',
    'permutation', 'region'}} (the Spike Rifle, boot 1: 'the spike is not visible'): a Halo 3
    PARTICLE MODEL (one rigid mesh: raw vertices compressed to the bounds, raw indices a strip)
    as a one-node Halo 2 JMS -- the projectile's own model, Bungie's needle's way (frame needle,
    base / needle). Read as h3_rm_to_jms.convert_particle_model reads it."""
    import io
    import re
    import h1_fp_retarget
    import h3_rm_to_jms as H3
    s = io.open(h1_fp_retarget.export_xml(pm['from']), encoding='utf-8', errors='replace').read()

    def nums(name, blk=s):
        return [tuple(float(x) for x in v.split(','))
                for v in re.findall(r'name="%s" value="([^"]*)"' % re.escape(name), blk)]
    (x0, x1, y0), (y1, z0, z1) = nums('position bounds 0')[0], nums('position bounds 1')[0]
    (u0, u1), (v0, v1) = nums('texcoord bounds 0')[0], nums('texcoord bounds 1')[0]
    raw = s[s.find('<block name="raw vertices"'):s.find('<block name="raw indices"')]
    pos, uv, nrm = nums('position', raw), nums('texcoord', raw), nums('normal', raw)
    idx = [int(v) for v in re.findall(r'name="word" value="(\d+)"', s[s.find('<block name="raw indices"'):])]
    out = h2_jms.Model()
    out.nodes = [h2_jms.Node(pm.get('node', 'frame spike'), -1, (0.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0))]
    out.materials = [h2_jms.Material(pm['material'], '(1) %s %s' % (pm.get('permutation', 'base'),
                                                                    pm.get('region', 'needle')))]
    lo, span = (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0)
    for p, t, n in zip(pos, uv, nrm):
        out.verts.append(h2_jms.Vertex(tuple((lo[k] + p[k] * span[k]) * UNITS for k in range(3)), n,
                                       [(0, 1.0)], [(u0 + t[0] * (u1 - u0), 1.0 - (v0 + t[1] * (v1 - v0)))]))
    out.tris = [(0, tri) for tri in H3.strip_tris(idx)]
    return out


def h3_jobs(g):
    base = os.path.join(H2EK, 'data', g['data_dir'])
    return [('world', g['world_rm'], os.path.join(base, 'render', g['world'] + '.jms'), True),
            ('fp', g['fp_rm'], os.path.join(base, g['fp'], 'render', g['fp'] + '.jms'), False)]


def h3_main(key, g, rest):
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in rest if a.startswith('--'))
    only = set(filter(None, opts.get('only', '').split(',')))
    h1 = g.get('kind') == 'h1'
    for name, pm in (g.get('particle_models') or {}).items():
        if only and name not in only:
            continue
        jm = h3_particle_model(pm)
        pm_path = os.path.join(H2EK, 'data', pm['data_dir'], 'render', name + '.jms')
        h2_jms.write(pm_path, jm)
        xs = [v.pos[0] for v in jm.verts]
        print('wrote %s\n   %d verts, %d tris, x %.2f..%.2f' % (pm_path, len(jm.verts), len(jm.tris),
                                                           min(xs), max(xs)))
    for label, rel, out_path, world in (h1_jobs(g) if h1 else h3_jobs(g)):
        if only and label not in only:
            continue
        jm = (h1_convert if h1 else h3_convert)(g, rel, world)
        h2_jms.write(out_path, jm)
        xs = [v.pos[0] for v in jm.verts]
        zs = [v.pos[2] for v in jm.verts]
        print('wrote %s' % out_path)
        print('   %d nodes %s' % (len(jm.nodes), [n.name for n in jm.nodes]))
        print('   %d verts, %d tris, materials %s'
              % (len(jm.verts), len(jm.tris), [(m.name, m.spec) for m in jm.materials]))
        print('   x %.2f..%.2f  z %.2f..%.2f' % (min(xs), max(xs), min(zs), max(zs)))
        for mk in jm.markers:
            print('   marker %-18s node %d %s' % (mk.name, mk.node, tuple(round(c, 2) for c in mk.pos)))
    if '--render' in rest:
        tool_render(g, g.get('render') or [])


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
    if g.get('kind') in ('h3', 'h1'):
        return h3_main(key, g, rest)
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
