r"""H4 SAW (storm_lmg) geometry -> Halo 2 JMS, on the cut GPMG's skeleton.

The Halo 1 and Halo 3 converters take their skeleton, rest pose and markers from the
donor: Halo 1 through Reclaimer's extraction, Halo 3 out of a render_model XML, because
neither game hands back the source. Halo 2 does. `tool extract-render-data` unzips
Bungie's ORIGINAL .jms out of the tag, so the template here is the authored file itself --
`fp_gpmg.jms` for first person, `L5_gpmg.jms` for the world model -- read and written by
`h2_jms.py`, which reproduces all four of them byte for byte.

**Placement.** The SAW's own `right_hand` marker sits exactly on its root bone, so the H4
mesh is authored around the trigger grip. Every vertex therefore moves by the GPMG's
`right_hand` marker and the two grips coincide by construction, which is what matters:
the first-person animations move the hands, and the right hand is the dominant one.

**Scale is 1.0, and that is measured, not chosen.** Grip to foregrip is 12.93 JMS units
on the GPMG and 12.73 on the SAW -- a 1.6% difference. With scale 1.0 the SAW's left hand
lands within half a unit of the GPMG's in all three axes, so the hand markers do not have
to be moved at all and nothing fights the animation. (The Halo 1 port needed 0.82 and the
Halo 3 port its own number; the two LMGs simply happen to be the same size.)

    python saw_to_jms_h2.py <storm_lmg_rm.xml> [scale]

What DOES move is the muzzle and the ejection port. Halo 2 fires from the barrel marker
named in the weapon tag, and for the GPMG that is `primary_trigger` -- 32.1 units forward,
which is past the end of the SAW. Left alone, the muzzle flash would hang in mid air.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_jms
import h4_rm

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
EXTRACTED = os.path.join(H2EK, 'data', '!extracted')
OUT_SUB = 'saw'                 # data\objects\weapons\rifle\<OUT_SUB>
SCALE = 1.0
UNITS = 100.0                   # JMS units per world unit

#: H4 part index -> the material this port gives it, or None to drop the part.
#: Part 0 is four triangles of a shared decal sheet and part 2 the depleted display, a
#: second quad laid over the live one -- Halo 4 switches between them, Halo 2 would
#: z-fight. Both are left out, exactly as the Halo 1 port leaves them out.
PART_MATERIAL = {0: None, 1: 'saw_gun', 2: None, 3: 'saw_display'}

#: How far the FIRST PERSON mesh is lifted, and why it needs to be.
#:
#: Anchoring on the grip put the barrel within a fifth of a unit of the donor's -- and
#: the gun still sat too low in the hands, which is what the first look in game said.
#: The reason is that the two guns carry their barrels at different heights: the SAW's
#: is 71% of the way up its body, the GPMG's 38%, so lining the barrels up drops the
#: SAW's bulk below where a Halo 2 weapon sits. Measured, the port's mesh centred 3.5
#: units under the donor's while their barrels were level.
#:
#: So the first person mesh is raised until its vertical band matches the donor's. None
#: of this applies to the world model, which was right first time.
#:
#: LIFT=None measures it from the two files; a number overrides.
LIFT = None

#: Where the first-person weapon sits in the view, after the lift. Halo's axes are X
#: forward, Y LEFT, Z up, so +Y moves it towards the middle of the screen and -Z drops it.
#: Set from a look in game: the gun read as sitting too far right and a little high, out
#: of the hand rather than in it. Applied to the first person model only.
FP_NUDGE = (0.0, 1.5, -1.5)

#: How far BELOW the bore the barrel marker goes, and why it is not zero.
#:
#: The first look in game said the muzzle flash sat above the muzzle. The marker was not
#: the problem -- measured, it is 0.07 units off the centre of the port's own barrel
#: opening, which is as close as the art allows. The effect is. The port borrows the
#: SMG's firing effect, and Bungie's SMG carries its barrel marker **1.40 units below its
#: own bore** (marker z 2.65, bore centre 4.04), so the particles are authored to draw
#: that far above where they are emitted. Hang that effect off a marker that IS on the
#: bore and the flash floats.
#:
#: So the port adopts the donor effect's convention instead of fighting it. The bullet
#: then leaves 1.4 units under the bore as well -- 0.014 world units, and exactly what
#: every SMG round in Halo 2 already does.
MUZZLE_DROP = 1.40

#: GPMG marker -> the SAW marker it should move to. Everything else keeps the GPMG's
#: position: the hands because the animation places them, `ground point` because it is
#: where the dropped weapon rests and belongs to the world, not to the model.
MARKER_FROM = {'primary_trigger': 'primary_trigger',
               'primary ejection': 'primary_ejection'}


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
        # JMS v is 1 - the tag's v. Measured, not assumed: the GPMG's own JMS runs
        # 0.017578..0.998047 where its tag's texcoord bounds run 0.001953..0.982422.
        tv = 1.0 - (v0 + v['uv'][1] * (v1 - v0))
        out.append((pos, v['n'] or (0.0, 0.0, 1.0), (u, tv), v['nodes'], v['w']))
    return out


def measure_lift(src, template, anchor):
    """How far to raise the mesh so its vertical band sits where the donor's does."""
    port = [pos[2] * SCALE + anchor[2] for pos, _n, _uv, _nodes, _w in src]
    donor = [v.pos[2] for v in template.verts]
    if not donor:
        return 0.0
    return ((min(donor) + max(donor)) - (min(port) + max(port))) / 2.0


def convert(rm, template, node_map, lift=0.0, nudge=(0.0, 0.0, 0.0)):
    """A Halo 2 JMS: the SAW's mesh under the template's skeleton and markers."""
    src = decompress(rm)
    anchor = {mk.name: mk for mk in template.markers}['right_hand'].pos
    anchor = (anchor[0] + nudge[0], anchor[1] + nudge[1], anchor[2] + lift + nudge[2])

    out = h2_jms.Model()
    out.nodes = list(template.nodes)

    # materials, in the order the kept parts first use them
    mats, mat_index = [], {}
    for part in rm['meshes'][0]['parts']:
        name = PART_MATERIAL.get(part['material'])
        if name is not None and name not in mat_index:
            mat_index[name] = len(mats)
            # "(1) base gun": LOD 1, permutation `base`, region `gun` -- the strings the
            # model tag looks for. There is no REGIONS section to put them in.
            mats.append(h2_jms.Material(name, '(1) %s %s'
                                        % (template.materials[0].permutation,
                                           template.materials[0].region)))
    out.materials = mats

    for pos, normal, uv, nodes, weights in src:
        p = tuple(pos[k] * SCALE + anchor[k] for k in range(3))
        infl = [(node_map[n], w) for n, w in zip(nodes, weights) if n >= 0 and w > 0]
        infl.sort(key=lambda t: -t[1])
        if not infl:
            infl = [(node_map[0], 1.0)]
        total = sum(w for _n, w in infl)
        infl = [(n, w / total) for n, w in infl]
        out.verts.append(h2_jms.Vertex(p, normal, infl, [uv]))

    indices = rm['meshes'][0]['indices']
    for part in rm['meshes'][0]['parts']:
        name = PART_MATERIAL.get(part['material'])
        if name is None:
            continue
        idx = indices[part['start']:part['start'] + part['count']]
        for i in range(0, len(idx) - 2, 3):
            out.tris.append((mat_index[name], (idx[i], idx[i + 1], idx[i + 2])))

    by_name = {}
    for m in rm['markers']:
        by_name.setdefault(m['name'], m)          # duplicates: take the first
    for mk in template.markers:
        src_mk = by_name.get(MARKER_FROM.get(mk.name, ''))
        pos = mk.pos
        if src_mk:
            pos = tuple(src_mk['pos'][k] * UNITS * SCALE + anchor[k] for k in range(3))
            if mk.name == 'primary_trigger':
                pos = (pos[0], pos[1], pos[2] - MUZZLE_DROP)
        out.markers.append(h2_jms.Marker(mk.name, mk.node, mk.rot, pos, mk.radius))
    return out


def main():
    global SCALE
    rm = h4_rm.load(sys.argv[1])
    if len(sys.argv) > 2:
        SCALE = float(sys.argv[2])
    print('scale %s' % SCALE)

    base = os.path.join(H2EK, 'data', 'objects', 'weapons', 'rifle', OUT_SUB)
    jobs = [(os.path.join(EXTRACTED, 'fp_gpmg', 'render', 'fp_gpmg.jms'),
             os.path.join(base, 'fp_' + OUT_SUB, 'render', 'fp_%s.jms' % OUT_SUB)),
            (os.path.join(EXTRACTED, 'gpmg', 'render', 'L5_gpmg.jms'),
             os.path.join(base, 'render', '%s.jms' % OUT_SUB))]

    for tmpl_path, out_path in jobs:
        template = h2_jms.read(tmpl_path)
        names = [n.name for n in template.nodes]
        # the SAW's two skinned bones -> the GPMG nodes that move the same parts
        node_map = {0: names.index('frame gun'), 1: names.index('frame magazine')}
        lift = 0.0
        if 'fp_' in os.path.basename(out_path):
            anchor = {mk.name: mk for mk in template.markers}['right_hand'].pos
            lift = LIFT if LIFT is not None else measure_lift(decompress(rm), template,
                                                              anchor)
            print('   lifting the first person mesh %.2f units, nudging %s'
                  % (lift, FP_NUDGE))
        jm = convert(rm, template, node_map, lift,
                     FP_NUDGE if lift else (0.0, 0.0, 0.0))
        h2_jms.write(out_path, jm)
        xs = [v.pos[0] for v in jm.verts]
        zs = [v.pos[2] for v in jm.verts]
        print('wrote %s' % out_path)
        print('   %d verts, %d tris, materials %s'
              % (len(jm.verts), len(jm.tris), [(m.name, m.spec) for m in jm.materials]))
        print('   x %.2f..%.2f  z %.2f..%.2f   nodes %s'
              % (min(xs), max(xs), min(zs), max(zs), names))
        for mk in jm.markers:
            was = {m.name: m for m in template.markers}[mk.name].pos
            moved = '   MOVED from %s' % (tuple(round(c, 2) for c in was),) \
                if mk.pos != was else ''
            print('   marker %-18s %s%s'
                  % (mk.name, tuple(round(c, 2) for c in mk.pos), moved))


if __name__ == '__main__':
    main()
