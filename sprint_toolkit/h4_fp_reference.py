r"""Render HALO 4's OWN first-person arms + gun from its camera bone at given animation frames: the
reference a Halo 1 retarget of a Halo 4 FP graph is judged against (C1 Storm Rifle, promoted from
the scratchpad 2026-10-14; the C1 recipe: render beside fp_render BEFORE a boot).

Blender + Foundry (H4EK); the rig comes from h4_fp_jump.build_rig (the graph's own arms render
model), the gun is the weapon's render model placed on b_gun each frame. Workbench render, one PNG
per spec 'animation@frame' (animation names as Foundry lists them, e.g. 'first_person:melee').

    blender -b -P sprint_toolkit\h4_fp_reference.py -- <out dir> <graph tag> <gun render model> ^
        "first_person:idle@0" "first_person:melee@12"

<graph tag> / <gun render model>: paths under H4EK\tags, e.g.
objects\characters\storm_fp\weapons\rifle\fp_assault_carbine\storm_fp_assault_carbine.model_animation_graph
objects\weapons\rifle\storm_assault_carbine\storm_assault_carbine.render_model
FOV: environment variable FOV (degrees, default 70). Foundry's stray '<folder><basename>' copy of
the graph is removed if this run made it.
"""
import importlib.util
import math
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('h4_fp_jump', os.path.join(HERE, 'h4_fp_jump.py'))
jump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jump)

argv = sys.argv[sys.argv.index('--') + 1:]
out_dir, rel, gun_rel, specs = argv[0], argv[1], argv[2], argv[3:]
src = os.path.join(jump.TAGS, rel)
stray = os.path.dirname(src) + os.path.basename(src)
had = os.path.exists(stray)
arm = jump.build_rig(rel)
if not had and os.path.exists(stray):
    os.remove(stray)

# the gun: its own model space on b_gun (Blender = G x Halo x 3.048 on both, so world = pose(b_gun))
before = set(bpy.data.objects)
gun_rm = os.path.join(jump.TAGS, gun_rel)
bpy.ops.nwo.foundry_import(filepath=gun_rm, directory=os.path.dirname(gun_rm),
                           files=[{'name': os.path.basename(gun_rm)}], build_blender_materials=False)
gun_objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
for o in gun_objs:
    o.parent = None
    for mod in list(o.modifiers):
        o.modifiers.remove(mod)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 480, 300
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'SINGLE'
cam_data = bpy.data.cameras.new('refcam')
cam_data.sensor_fit = 'HORIZONTAL'
cam_data.angle = math.radians(float(os.environ.get('FOV', 70)))
cam_data.clip_start = 0.01
cam = bpy.data.objects.new('refcam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
anims = {a.name: a for a in scene.nwo.animations}
arm.animation_data_create()
B = Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0)))    # columns: cam X = -halo y, cam Y = halo z, cam Z = -halo x
os.makedirs(out_dir, exist_ok=True)
for s in specs:
    name, frame = s.rsplit('@', 1)
    a = anims[name]
    arm.animation_data.action = a.action_tracks[0].action
    scene.frame_set(int(a.frame_start) + int(frame))
    M = arm.matrix_world @ arm.pose.bones['b_camera_control'].matrix
    cam.matrix_world = Matrix.Translation(M.to_translation()) @ (M.to_3x3().normalized() @ B).to_4x4()
    MG = arm.matrix_world @ arm.pose.bones['b_gun'].matrix
    for o in gun_objs:
        o.matrix_world = MG
    scene.render.filepath = os.path.join(out_dir, 'h4ref_%s_%s.png' % (name.replace(' ', '_').replace(':', '_'), frame))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scene.render.filepath)
