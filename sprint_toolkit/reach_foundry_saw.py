r"""Build the Reach SAW's render model through Foundry, Bungie's sidecar route.

Run INSIDE Blender (the portable 5.2 on F:, with the Foundry extension):

    blender --background --python reach_foundry_saw.py -- --build     # make saw.blend
    blender --background --python reach_foundry_saw.py -- --export    # + export tags

WHY THIS EXISTS. A JMS rendered with `tool render` produces a Reach render model that
draws in first person and where the scenario places it, and draws NOTHING when dropped or
held by an ally. Every field the XML shows was matched against the donor's; the donor's
OWN geometry pushed through the JMS path failed the same way; and the donor's own render
model, swapped in, drew. So the JMS importer is what is wrong. Bungie's assets came in
through FBX -> Granny .gr2 -> sidecar -> `tool import`, and the .gr2 needs an exporter
the kit does not ship. Foundry is the community exporter that writes it.

HOW. Foundry imports the Assault Rifle's own model tag natively, which gives a scaffold it
built itself -- armature with the five b_ bones in the donor's order, a mesh object with
the region/permutation properties, all 20 markers, the scene set up as a model asset. This
script keeps all of that and swaps ONLY the mesh data for the SAW's, read from the JMS the
toolkit already builds (`saw_to_jms_h3.py`), then moves the markers the SAW carries in
different places. Nothing about the export is set up by hand, so nothing can be set up
wrong by hand.

SCALE. Foundry's scene is in Blender metres: the Assault Rifle spans -0.2971..0.6668 in
Blender against -0.0975..0.2188 world units, a factor of 3.048. The JMS is in world units
x 100. So a JMS coordinate goes into Blender multiplied by 0.03048.

TOOL PATCHES. Foundry ships with `allow_tool_patches` on, which lets it modify HREK's
tool.exe. It has been switched OFF in this portable install and this script refuses to
export if it finds it back on.
"""
import os
import sys

import bpy

EK = r'F:\SteamLibrary\steamapps\common\HREK'
SAW_DIR = os.path.join(EK, 'data', 'objects', 'weapons', 'rifle', 'saw')
SCAFFOLD = os.path.join(SAW_DIR, 'saw_scaffold.blend')
BLEND = os.path.join(SAW_DIR, 'saw.blend')
JMS = os.path.join(SAW_DIR, 'render', 'default.jms')
SHADERS = 'objects\\weapons\\rifle\\saw\\shaders\\'
KEY = 'bl_ext.user_default.io_scene_foundry'

SCALE = 0.03048                       # JMS units (world x 100) -> Foundry Blender metres
#: markers the converter moves to the SAW's own positions; the rest stay the donor's
MOVED = ('muzzle_flash', 'primary_trigger', 'primary_ejection', 'flashlight')


def read_jms(path):
    """nodes, materials, markers, verts, tris from a version 8200 JMS (text)."""
    lines = [l.rstrip('\r') for l in open(path, encoding='latin-1').read().split('\n')]
    it = iter(lines)
    nxt = lambda: next(it)
    assert nxt() == '8200', 'not a version 8200 JMS'
    nxt()                                             # node list checksum
    nodes = []
    for _ in range(int(nxt())):
        name = nxt(); nxt(); nxt(); nxt(); nxt()      # child, sibling, rot, pos
        nodes.append(name)
    mats = []
    for _ in range(int(nxt())):
        mats.append(nxt()); nxt()
    markers = []
    for _ in range(int(nxt())):
        name = nxt(); nxt(); node = int(nxt()); nxt()  # region, node, rotation
        pos = [float(v) for v in nxt().split()]
        nxt()                                          # radius
        markers.append((name, node, pos))
    for _ in range(int(nxt())):                        # regions
        nxt()
    verts = []
    for _ in range(int(nxt())):
        n0 = int(nxt())
        pos = [float(v) for v in nxt().split()]
        nrm = [float(v) for v in nxt().split()]
        n1 = int(nxt()); w1 = float(nxt())
        # reclaimer writes U, V and W on three SEPARATE lines -- an 8-line record
        uv = [float(nxt()), float(nxt())]
        nxt()
        verts.append((n0, pos, nrm, n1, w1, uv))
    tris = []
    for _ in range(int(nxt())):
        region, shader = int(nxt()), int(nxt())
        a, b, c = (int(v) for v in nxt().split())
        tris.append((shader, a, b, c))
    return nodes, mats, markers, verts, tris


def stem(name):
    """b_a_gun (the toolkit's sort-keyed name) -> b_gun, the bone Foundry built."""
    parts = name.split('_')
    if len(parts) >= 3 and parts[0] == 'b' and len(parts[1]) == 1:
        return 'b_' + '_'.join(parts[2:])
    return name


def build():
    bpy.ops.wm.open_mainfile(filepath=SCAFFOLD)
    nodes, mats, markers, verts, tris = read_jms(JMS)
    print('JMS: %d nodes, %d materials, %d markers, %d verts, %d tris'
          % (len(nodes), len(mats), len(markers), len(verts), len(tris)))

    ob = bpy.data.objects['default:default']
    me = bpy.data.meshes.new('saw')
    me.from_pydata([[c * SCALE for c in v[1]] for v in verts], [],
                   [(t[1], t[2], t[3]) for t in tris])
    me.update()
    for poly, t in zip(me.polygons, tris):
        poly.material_index = t[0]
        poly.use_smooth = True
    uv = me.uv_layers.new(name='UVMap0')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            u, v = verts[vi][5][0], verts[vi][5][1]
            uv.data[li].uv = (u, v)
    me.normals_split_custom_set_from_vertices([v[2] for v in verts])

    for name in mats:
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.nwo.shader_path = SHADERS + name + '.shader'
        me.materials.append(m)

    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    ob.vertex_groups.clear()
    groups = {}
    for vi, (n0, _p, _n, n1, w1, _uv) in enumerate(verts):
        for node, w in ((n0, 1.0 - (w1 if n1 >= 0 else 0.0)), (n1, w1)):
            if node < 0 or w <= 0:
                continue
            bone = stem(nodes[node])
            g = groups.get(bone) or ob.vertex_groups.new(name=bone)
            groups[bone] = g
            g.add([vi], w, 'REPLACE')
    print('vertex groups:', {k: len([1 for v in ob.data.vertices
                                     for gg in v.groups if gg.group == g.index])
                             for k, g in groups.items()})

    xs = [v.co.x for v in me.vertices]
    print('SAW mesh x range in blender: %.4f .. %.4f' % (min(xs), max(xs)))

    placed = {}
    for name, _node, pos in markers:
        if name in MOVED:
            placed.setdefault(name, pos)
    for obj in bpy.data.objects:
        base = obj.name.split('.')[0]
        if obj.type == 'EMPTY' and base in placed:
            loc = [c * SCALE for c in placed[base]]
            # A BONE-parented object is placed from the bone's TAIL, one bone length
            # along the bone's own Y. Setting the JMS position straight into .location
            # shifted every moved marker 0.1524 m (b_gun's length) = 0.05 tag units
            # sideways -- the muzzle flash hung off the side of the barrel in game.
            if obj.parent_type == 'BONE' and obj.parent_bone:
                loc[1] -= obj.parent.data.bones[obj.parent_bone].length
            obj.location = loc
            print('marker %-18s -> %s' % (obj.name, tuple(round(c, 4) for c in obj.location)))

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print('saved', BLEND)


#: FOUNDRY REWRITES THE MODEL TAG. Its export regenerates `saw.model` from what the scene
#: holds -- render and markers only -- so it DROPS the collision, physics and world
#: animation references the port borrows from the Assault Rifle, and points the imposter
#: at a SAW imposter that does not exist. A weapon dropped on that model has no physics
#: body. It also writes a `saw.scenery` nothing references. What we want from Foundry is
#: the RENDER MODEL; the model tag stays ours, so it is kept aside and put back.
TAGS_SAW = os.path.join(EK, 'tags', 'objects', 'weapons', 'rifle', 'saw')
KEEP = ('saw.model',)
DISCARD = ('saw.scenery',)


def export():
    p = bpy.context.preferences.addons[KEY].preferences
    if p.allow_tool_patches:
        raise SystemExit('Foundry allow_tool_patches is ON -- refusing to export')
    kept = {}
    for name in KEEP:
        path = os.path.join(TAGS_SAW, name)
        if os.path.exists(path):
            kept[name] = open(path, 'rb').read()
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    try:
        res = bpy.ops.nwo.export_scene()
        print('export result', res)
    finally:
        for name, data in kept.items():
            open(os.path.join(TAGS_SAW, name), 'wb').write(data)
            print('restored %s (%d bytes) -- Foundry rewrote it' % (name, len(data)))
        for name in DISCARD:
            path = os.path.join(TAGS_SAW, name)
            if os.path.exists(path):
                os.remove(path)
                print('removed %s -- Foundry wrote it, nothing references it' % name)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if '--build' in argv:
        build()
    if '--export' in argv:
        export()
