r"""Halo 4 port, step 1: bring a weapon's MODEL from another kit into H4EK through Foundry.

Two Blender processes, because Foundry binds ONE kit's ManagedBlam per process and needs a
restart to switch (its own project chooser says so):

    blender --background --python h4_foundry_port.py -- --import    # in the SOURCE kit
    python h4_port_materials.py --write                              # H4 materials (step 2)
    blender --background --python h4_foundry_port.py -- --export    # in H4EK

--import  reads the source weapon's .model tag -- render, markers, collision, physics --
          into Blender and saves H4EK\data\<port>\<name>.blend. Foundry names an asset
          after the FOLDER its .blend sits in, so the folder is the weapon's name.
--export  opens that .blend as a Halo 4 asset, points every Blender material at the port's
          own .material tag (h4_port_materials.py), and exports: render_model,
          collision_model, physics_model and model land in H4EK\tags\<port>.

MEASURED on the Reach Focus Rifle (2026-09-30): the import brings 19,233 render vertices
with all 8 materials, a 26-vertex collision and an 8-vertex physics hull, the full
14-node skeleton (b_gun plus the charge cylinders, arm joints and barrels) and every
marker; the export writes all four tags with 0 errors. Without step 2 every surface is
`shaders\invalid` -- H4EK has no legacy shader definitions to convert from.

BACKGROUND MODE. Foundry lays material node trees out with `arrange`, which divides by the
UI scale -- 0 without a window -- and the import dies with a ZeroDivisionError. The layout
is cosmetic, so it is replaced with a no-op in every module that imported it. Foundry's
files are not touched. `allow_tool_patches` must be OFF (foundry_setup.py).

Foundry also writes a .scenery beside the model; the port does not use it and it is
discarded, as in the Reach SAW port.
"""
import importlib
import os
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
for _mod in ('.utils', '.tools.shader_reader', '.managed_blam.connected_material',
             '.tools.node_tree_arrange'):
    setattr(importlib.import_module(KEY + _mod), 'arrange', lambda tree: None)

SOURCE_EK = r'F:\SteamLibrary\steamapps\common\HREK'
SOURCE_PROJECT_CORINTH = False
H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
PORT = r'objects\weapons\rifle\focus_rifle'
NAME = 'focus_rifle'
SOURCE_MODEL = os.path.join(SOURCE_EK, 'tags', PORT, NAME + '.model')
BLEND = os.path.join(H4EK, 'data', PORT, NAME + '.blend')
MATERIAL_DIR = PORT + r'\shaders'


def prefs():
    p = bpy.context.preferences.addons[KEY].preferences
    if p.allow_tool_patches:
        raise SystemExit('Foundry allow_tool_patches is ON -- run foundry_setup.py -- --fix')
    return p


def project(corinth):
    names = [pr.name for pr in prefs().projects if pr.corinth == corinth]
    if not names:
        raise SystemExit('no %s project in Foundry -- foundry_setup.py -- --add <kit>'
                         % ('Halo 4' if corinth else 'source'))
    return names[0]


def do_import():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.context.scene.nwo.scene_project = project(SOURCE_PROJECT_CORINTH)
    res = bpy.ops.nwo.foundry_import(
        filepath=SOURCE_MODEL, directory=os.path.dirname(SOURCE_MODEL),
        files=[{'name': os.path.basename(SOURCE_MODEL)}],
        tag_render=True, tag_markers=True, tag_collision=True, tag_physics=True,
        tag_animation=False, build_blender_materials=True)
    print('import', res)
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            print('   mesh %-24s %6d verts  %s' % (ob.name, len(ob.data.vertices),
                                                  [m.name for m in ob.data.materials]))
        elif ob.type == 'ARMATURE':
            print('   armature %d bones' % len(ob.data.bones))
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print('saved', BLEND)


def add_default_variant():
    """Give the .model a `default` variant: region `default`, permutation `default`.

    Foundry's export writes a model with ZERO variants. Every Bungie weapon has one (the
    Beam Rifle: one variant, one region, one permutation, all `default`). Without it the
    world object still draws -- the ground model was fine -- but the FIRST-PERSON weapon
    did not, while still casting a shadow, and neither did the beam effect hanging off
    its markers; the beam's damage landed (second boot, 2026-10-01). The runtime indices
    are compiled by tool at build time.
    """
    mb = importlib.import_module(KEY + '.managed_blam')

    class T(mb.Tag):
        pass

    with T(path=os.path.join(H4EK, 'tags', PORT, NAME + '.model')) as t:
        variants = t.tag.SelectField('variants')
        if variants.Elements.Count:
            print('model already has %d variant(s)' % variants.Elements.Count)
            return
        v = variants.AddElement()
        v.SelectField('name').SetStringData('default')
        r = v.SelectField('regions').AddElement()
        r.SelectField('region name').SetStringData('default')
        p = r.SelectField('permutations').AddElement()
        p.SelectField('permutation name').SetStringData('default')
        t.tag_has_changes = True
        print('model: default variant added (region default, permutation default)')


def do_export():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    nwo = bpy.context.scene.nwo
    nwo.scene_project = project(True)
    nwo.asset_type = 'model'
    missing = []
    for m in bpy.data.materials:
        if m.name in ('Collision', 'Physics') or not m.nwo.shader_path:
            continue
        own = MATERIAL_DIR + '\\' + m.name + '.material'
        if not os.path.exists(os.path.join(H4EK, 'tags', own)):
            missing.append(own)
            continue
        m.nwo.shader_path = own
        print('   %-26s -> %s' % (m.name, own))
    if missing:
        raise SystemExit('no H4 material for %s -- run h4_port_materials.py --write first'
                         % missing)
    # DRAW DISTANCE. The Reach import carries Reach's per-face "Draw Distance Mid", which
    # exports as part flag "Draw Cull Distance Medium" (16) on the render model's parts.
    # Halo 4 applies it to the FIRST-PERSON weapon too: first boot, the fp model was
    # invisible while still casting a shadow, and the Beam Rifle's body parts carry no
    # cull flag. Reset to normal.
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            for fp in ob.data.nwo.face_props:
                if fp.type == 'draw_distance' and fp.draw_distance != 'normal':
                    print('   %s: face prop %r draw distance %s -> normal'
                          % (ob.name, fp.name, fp.draw_distance))
                    fp.draw_distance = 'normal'
    bpy.ops.wm.save_mainfile()
    print('export', bpy.ops.nwo.export_scene())
    add_default_variant()
    scenery = os.path.join(H4EK, 'tags', PORT, NAME + '.scenery')
    if os.path.exists(scenery):
        os.remove(scenery)
        print('discarded', scenery)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if '--import' in argv:
        do_import()
    if '--export' in argv:
        do_export()
