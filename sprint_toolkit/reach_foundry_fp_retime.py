r"""Retime the Reach SAW's first-person reload and ready -- step 9 -- through Foundry.

Run INSIDE the portable Blender on F: with the Foundry extension:

    blender --background --python reach_foundry_fp_retime.py -- spartans [--write]
    blender --background --python reach_foundry_fp_retime.py -- elite    [--write]
    blender --background --python reach_foundry_fp_retime.py -- elite    --events   (events only)

WHY FOUNDRY. Halo 3 stores first-person frames RAW, so `h3_saw_animations.py` retimes
them with arithmetic. Reach COMPRESSES them: on every one of the SAW graph's members
`default_data` is 0 and the frames are in the compressed block, which `h3_anim_decode`
cannot read. Foundry decodes Reach animations through the kit's own ManagedBlam, so the
retime happens in Blender and goes back out through the sidecar, like step 1.

THE RIG. A first-person graph animates the ARMS and the WEAPON together -- 52 nodes for
the Spartan, 46 for the Elite, the last five being the weapon's b_ nodes with b_gun under
r_hand. Foundry imports the arms render model as an armature WITHOUT those five, and
with no matching armature in the scene it imports no animation at all ("No armature
found"). So the arms come in first and the weapon bones are added from the graph's own
skeleton list. Foundry's WEAPON importer, which would build this, crashes in background
mode while turning the weapon's functions into node trees.

THE EXPORT REBUILDS THE GRAPH from what the scene holds: exporting one animation leaves a
graph of one. So ALL of them are exported and only three are changed. Verified with an
unmodified round trip into a scratch copy: 25 animations, the mode, the skeleton, 9 sound
and 2 effect references, the weapon IK, and every frame count and frame event came back
identical, 0 errors.

THE RETIME. The Halo 4 SAW's own counts, as in Halo 3 (see h3_saw_animations.TARGET):
reload_full and reload_empty 128, ready 24. Foundry's frames are 1-based and run from 1 to
count + 1, and a frame EVENT sits at tag frame + 1. Keys, their handles and the events are
all scaled about frame 1, so the reload sound, the primary keyframe and "allow
interruption" move with the motion instead of firing at the old times. Built LONG on
purpose: the patcher can only shorten an animation, so the balance multiplier works
downward from here.

The graph is backed up beside itself before it is replaced.
"""
import os
import re
import shutil
import subprocess
import sys

import bpy

EK = r'F:\SteamLibrary\steamapps\common\HREK'
TAGS = os.path.join(EK, 'tags')
SAW_FP = r'objects\weapons\rifle\saw\fp'
KEY = 'bl_ext.user_default.io_scene_foundry'
TARGET = {'first_person reload_full': 128, 'first_person reload_empty': 128,
          'first_person ready': 24}
ARMS = {'spartans': r'objects\characters\spartans\fp\fp.render_model',
        'elite': r'objects\characters\elite\fp\fp.render_model'}


def graph_rel(species):
    return SAW_FP + '\\fp_saw_' + species + '.model_animation_graph'


def weapon_bones(species):
    """[(bone, parent)] for the graph's b_ nodes, read from the graph itself."""
    out = os.path.join(EK, 'temp', 'retime_%s.xml' % species)
    subprocess.run([os.path.join(EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.join(TAGS, graph_rel(species)), out], cwd=EK, capture_output=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    n = int(re.search(r'name="skeleton nodes" value="(\d+)"', x).group(1))
    els = re.findall(r'<element index="\d+" name="([^"]+)">(.*?)</element>',
                     x[x.find('name="skeleton nodes"'):], re.S)[:n]
    return n, [(name, re.search(r'"parent node index" value="([^"]*)"', body).group(1))
               for name, body in els if name.startswith('b_')]


def imp(rel, **kw):
    path = os.path.join(TAGS, rel)
    return bpy.ops.nwo.foundry_import(filepath=path, directory=os.path.dirname(path),
                                      files=[{'name': os.path.basename(path)}], **kw)


def fcurves(action):
    if getattr(action, 'fcurves', None):
        yield from action.fcurves
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def scale(anim, target):
    old = anim.frame_end - anim.frame_start
    f = float(target) / old
    at = lambda x: anim.frame_start + (x - anim.frame_start) * f       # noqa: E731
    action = anim.action_tracks[0].action
    keys = 0
    for fc in fcurves(action):
        for k in fc.keyframe_points:
            k.co.x = at(k.co.x)
            k.handle_left.x = at(k.handle_left.x)
            k.handle_right.x = at(k.handle_right.x)
            keys += 1
        fc.update()
    moved = []
    for ev in anim.animation_events:
        was = ev.frame_frame
        ev.frame_frame = int(round(at(ev.frame_frame)))
        ev.frame_range = ev.frame_frame
        moved.append((ev.frame_name, was - 1, ev.frame_frame - 1))
    anim.frame_end = anim.frame_start + target
    return old, keys, moved


def main(species, write):
    p = bpy.context.preferences.addons[KEY].preferences
    if p.allow_tool_patches:
        raise SystemExit('Foundry allow_tool_patches is ON -- refusing')
    n_nodes, bones = weapon_bones(species)
    print('%s: graph has %d nodes, weapon bones %s' % (species, n_nodes, bones))

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    imp(ARMS[species], build_blender_materials=False)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and len(o.data.bones))
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    for name, parent in bones:
        ref = eb[parent]
        b = eb.new(name)
        b.head = ref.head.copy()
        b.tail = ref.head + (ref.tail - ref.head).normalized() * 0.05
        b.roll = ref.roll
        b.parent = ref
    bpy.ops.object.mode_set(mode='OBJECT')
    if len(arm.data.bones) != n_nodes:
        raise SystemExit('rig has %d bones, the graph %d' % (len(arm.data.bones), n_nodes))
    imp(graph_rel(species), graph_import_animations=True, reuse_armature=True)

    sc = bpy.context.scene.nwo
    sc.asset_type = 'animation'
    print('%d animations imported' % len(sc.animations))
    for anim in sc.animations:
        anim.export_this = True
        if anim.name in TARGET:
            old, keys, moved = scale(anim, TARGET[anim.name])
            print('   %-28s %3d -> %3d frames, %d keys; events %s'
                  % (anim.name, old, TARGET[anim.name], keys, moved))
    missing = set(TARGET) - {a.name for a in sc.animations}
    if missing:
        raise SystemExit('not in the graph: %s' % sorted(missing))

    if not write:
        print('\n(dry run -- pass --write)')
        return
    # WHERE IT LANDS. Foundry names the asset after the FOLDER the .blend sits in and
    # writes <folder>\<folder name>.model_animation_graph -- two species saved side by
    # side in saw\fp both came out as saw\fp\fp, the second overwriting the first. So
    # each species gets its own folder, and the weapon is repointed to it.
    #
    # AND IT IS SEEDED FIRST. Exported into an EXISTING graph, tool import merges: the
    # round trip kept every frame event and sound reference inline. Exported into
    # nothing, it builds a fresh graph and puts the events in a separate frame_event_list
    # -- measured: 128/128/24 frames right, 0 sound references in the graph.
    src = os.path.join(TAGS, graph_rel(species))
    out_rel = new_graph_rel(species)
    out = os.path.join(TAGS, out_rel + '.model_animation_graph')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        shutil.copyfile(src, out)
        print('seeded %s from the original graph' % out_rel)
    blend = os.path.join(EK, 'data', out_rel + '.blend')
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print('export', bpy.ops.nwo.export_scene())
    fix_events(species)


EVENT_BLOCKS = ('frame events', 'sound events', 'effect events', 'dialogue events')


def fix_events(species):
    """Scale the INLINE event frames of the retimed animations, through ManagedBlam.

    Exporting into the seeded graph merges, and the merge KEEPS the seeded graph's inline
    events: measured after the first --write, reload_full was 128 frames with its primary
    keyframe still at 34, allow interruption at 52 and the mag-slam effect at 40 -- the
    old times, so the reload would complete at a quarter of the motion. The events Foundry
    scaled went only to the side frame_event_list.

    The new frames are computed from the ORIGINAL graph's values (frame * new / old, the
    same scaling as the keys), so running this again cannot compound.
    """
    from bl_ext.user_default.io_scene_foundry.managed_blam.animation import AnimationTag

    def events(rel):
        out = {}
        with AnimationTag(path=rel) as t:
            for a in t.get_animations():
                name = str(a.name.name if hasattr(a.name, 'name') else a.name)
                name = a.element.Fields[0].GetStringData()
                key = name.replace(':', ' ')
                if key not in TARGET:
                    continue
                got = {}
                for blk in EVENT_BLOCKS:
                    try:
                        els = a.shared_element.SelectField(blk).Elements
                    except Exception:
                        continue
                    got[blk] = [int(e.SelectField('frame').GetStringData()) for e in els]
                out[key] = (int(a.frame_count), got)
        return out

    old = events(graph_rel(species))
    new_rel = new_graph_rel(species) + '.model_animation_graph'
    with AnimationTag(path=new_rel) as t:
        for a in t.get_animations():
            key = a.element.Fields[0].GetStringData().replace(':', ' ')
            if key not in TARGET:
                continue
            count, was = old[key]
            if int(a.frame_count) != TARGET[key]:
                raise SystemExit('%s is %s frames, expected %d' % (key, a.frame_count, TARGET[key]))
            for blk, frames in was.items():
                els = a.shared_element.SelectField(blk).Elements
                if els.Count != len(frames):
                    raise SystemExit('%s %s: %d events, the original has %d'
                                     % (key, blk, els.Count, len(frames)))
                moved = []
                for e, f in zip(els, frames):
                    now = min(TARGET[key] - 1, int(round(f * TARGET[key] / float(count))))
                    e.SelectField('frame').SetStringData(str(now))
                    moved.append((f, now))
                print('   %-28s %-15s %s' % (key, blk, moved))
        t.tag_has_changes = True


def new_graph_rel(species):
    name = 'fp_saw_' + species
    return 'objects\\weapons\\rifle\\saw\\%s\\%s' % (name, name)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    species = next((a for a in argv if a in ARMS), None)
    if not species:
        raise SystemExit('which species? spartans or elite')
    if '--events' in argv:
        fix_events(species)
    else:
        main(species, '--write' in argv)
