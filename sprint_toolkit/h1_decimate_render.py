r"""Runs INSIDE Blender (background) for `h1_decimate.py preview --render` -- never run it directly.

    blender -b --factory-startup -P h1_decimate_render.py -- <dir> <name> [<name> ...]

For each <name>: <dir>\<name>.obj (model space) -> <name>_side.png (orthographic side view) and
<dir>\<name>_fp.obj (posed by the FP idle, Halo 1's FP space: eye at the origin looking +x, +z
up) -> <name>_fp.png (70 deg horizontal, 1920x1080: the view the player gets; hands not drawn).
Matcap shading: faceting shows as it would under Halo 1's per-vertex lighting.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
D, NAMES = argv[0], argv[1:]


def scene(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'MATCAP'
    sc.display.shading.studio_light = 'basic_grey.exr'
    sc.display.shading.color_type = 'SINGLE'
    sc.display.shading.single_color = (0.85, 0.86, 0.88)
    sc.view_settings.view_transform = 'Standard'
    sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.18, 0.2, 0.24)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


for n in NAMES:
    sc, cam = scene(os.path.join(D, n + '.obj'))
    pts = [o.matrix_world @ v.co for o in sc.objects if o.type == 'MESH' for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    size, centre = hi - lo, (lo + hi) / 2
    length = max(size)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = length * 1.08
    cam.location = centre + Vector((0, -1, 0)) * length * 3
    cam.rotation_euler = Vector((0, 1, 0)).to_track_quat('-Z', 'Z').to_euler()
    sc.render.resolution_x = 1240
    sc.render.resolution_y = int(1240 * max(0.35, (size.z / length) * 1.25))
    sc.render.filepath = os.path.join(D, n + '_side.png')
    bpy.ops.render.render(write_still=True)
    sc, cam = scene(os.path.join(D, n + '_fp.obj'))
    cam.data.type = 'PERSP'
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.angle = math.radians(70)
    cam.data.clip_start = 0.002
    cam.rotation_euler = Vector((1, 0, 0)).to_track_quat('-Z', 'Z').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.filepath = os.path.join(D, n + '_fp.png')
    bpy.ops.render.render(write_still=True)
