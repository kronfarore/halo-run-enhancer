import bpy, os

T = r'F:\SteamLibrary\steamapps\common\HREK\tags'
ARMS = os.path.join(T, r'objects\characters\spartans\fp\fp.render_model')
GRAPH = os.path.join(T, r'objects\weapons\rifle\saw\fp\fp_saw_spartans.model_animation_graph')

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

def imp(path, **kw):
    return bpy.ops.nwo.foundry_import(filepath=path, directory=os.path.dirname(path),
                                      files=[{'name': os.path.basename(path)}], **kw)

print('arms', imp(ARMS, build_blender_materials=False))
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
print('armatures', [(a.name, len(a.data.bones)) for a in arms])
if arms:
    bpy.ops.object.select_all(action='DESELECT')
    arms[0].select_set(True)
    bpy.context.view_layer.objects.active = arms[0]
    print('graph', imp(GRAPH, graph_import_animations=True, reuse_armature=True))
acts = [(a.name, a.frame_range[:]) for a in bpy.data.actions]
print('ACTIONS', len(acts))
for n, fr in acts:
    if any(k in n for k in ('reload', 'ready', 'put_away')):
        print('ACTION %-44s %.0f..%.0f' % (n, fr[0], fr[1]))
