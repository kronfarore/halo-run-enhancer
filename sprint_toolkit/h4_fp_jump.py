r"""Find the frame JUMPS in a Halo 4 first-person animation graph.

The Focus Rifle port borrows the Beam Rifle's fp graph, and at the end of overheating the
whole first-person view -- both arms and the rifle -- jerks right for about two frames
and snaps back (user's slow-motion video, boot 11: frames 4-5 of 14 at 30 fps). The
Beam Rifle never overheats in normal Halo 4 play, so these animations are never seen.

This loads the graph in Blender through Foundry (H4EK project), on the fp arms
(storm_fp_solo.render_model, 80 bones) plus the graph's own weapon bones (14: b_gun under
b_r_hand, the vents and flaps under b_gun), and measures, per frame, where both hands
and b_gun sit RELATIVE TO b_camera_control -- a jump of the whole view is movement
against the camera. It reports
  * frames inside one animation that move far more than their neighbours, and
  * the hand-off between animations that play in sequence (the last frame of one
    against the first of the next), e.g. overheated -> o_h_exit.

    blender --background --python h4_fp_jump.py [-- <graph tag path>]
"""
import importlib
import os
import re
import subprocess
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
TAGS = os.path.join(H4EK, 'tags')
ARMS = r'objects\characters\storm_fp\storm_fp_solo.render_model'
GRAPH = (r'objects\characters\storm_fp\weapons\rifle\fp_beam_rifle'
         r'\storm_fp_beam_rifle.model_animation_graph')
WATCH = ('b_r_hand', 'b_l_hand', 'b_gun')
CAMERA = 'b_camera_control'
#: animations that play in sequence around overheating
CHAINS = [('overheating', 'o_h_exit'), ('overheating', 'overheated'), ('overheated', 'o_h_exit'), ('o_h_exit', 'idle'),
          ('fire_1', 'overheating'), ('vent_enter', 'vent_loop'), ('vent_loop', 'vent_exit'),
          ('vent_exit', 'idle')]

for _mod in ('.utils', '.tools.shader_reader', '.managed_blam.connected_material',
             '.tools.node_tree_arrange'):
    setattr(importlib.import_module(KEY + _mod), 'arrange', lambda tree: None)


def imp(rel, **kw):
    path = os.path.join(TAGS, rel)
    return bpy.ops.nwo.foundry_import(filepath=path, directory=os.path.dirname(path),
                                      files=[{'name': os.path.basename(path)}], **kw)


def graph_weapon_bones(rel):
    out = os.path.join(H4EK, 'fpjump.xml')
    subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.join(TAGS, rel), out], cwd=H4EK, capture_output=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    os.remove(out)
    els = re.findall(r'<element index="(\d+)" name="([^"]+)">((?:(?!</element>).)*?'
                     r'parent node index" value="[^"]*?(-?\d+)")', x, re.S)
    nodes = [(n, int(p)) for _i, n, _b, p in els]
    return len(nodes), [(n, nodes[p][0]) for n, p in nodes if p >= 0], nodes


def build_rig(rel):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    imp(ARMS, build_blender_materials=False)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and len(o.data.bones))
    n, pairs, _nodes = graph_weapon_bones(rel)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    for name, parent in pairs:
        if name in eb:
            continue
        ref = eb[parent]
        b = eb.new(name)
        b.head = ref.head.copy()
        b.tail = ref.head + (ref.tail - ref.head).normalized() * 0.05
        b.parent = ref
    bpy.ops.object.mode_set(mode='OBJECT')
    if len(arm.data.bones) != n:
        raise SystemExit('rig has %d bones, the graph %d' % (len(arm.data.bones), n))
    # FOUNDRY'S GRAPH IMPORT REWRITES THE SOURCE GRAPH'S frame_event_list -- measured on
    # the Beam Rifle's: 32,491 bytes shipped, 30,376 after an import. That is a SHIPPED
    # tag the real Beam Rifle uses, so it is kept byte for byte and put back.
    events = os.path.join(TAGS, os.path.splitext(rel)[0] + '.frame_event_list')
    kept = open(events, 'rb').read() if os.path.exists(events) else None
    try:
        imp(rel, graph_import_animations=True, reuse_armature=True)
    finally:
        if kept is not None:
            open(events, 'wb').write(kept)
    return arm


def sample(arm, anim):
    """[(frame, {bone: position relative to the camera bone})] for one animation."""
    act = anim.action_tracks[0].action if anim.action_tracks else None
    arm.animation_data_create()
    arm.animation_data.action = act
    out = []
    cam = arm.pose.bones[CAMERA]
    for f in range(int(anim.frame_start), int(anim.frame_end) + 1):
        bpy.context.scene.frame_set(f)
        inv = (arm.matrix_world @ cam.matrix).inverted()
        out.append((f, {b: inv @ (arm.matrix_world @ arm.pose.bones[b].head) for b in WATCH}))
    return out


def spikes(frames):
    """Frames that leave their path and come back: |p(f-1) - 2 p(f) + p(f+1)| -- the
    distance from a frame to the midpoint of its neighbours. Fast but smooth motion (a
    melee swing) scores low; a one- or two-frame jerk out and back scores high."""
    out = []
    for (fa, a), (fb, b), (fc, c) in zip(frames, frames[1:], frames[2:]):
        d = max((b[k] - (a[k] + c[k]) * 0.5).length for k in WATCH)
        out.append((fb, d))
    if not out:
        return [], 0
    typical = sorted(d for _f, d in out)[len(out) // 2] or 1e-6
    return [(f, d, d / typical) for f, d in out if d > 0.01 and d / typical > 8], typical


def jumps(frames):
    steps = []
    for (fa, a), (fb, b) in zip(frames, frames[1:]):
        steps.append((fb, max((b[k] - a[k]).length for k in WATCH)))
    if not steps:
        return [], 0
    typical = sorted(s for _f, s in steps)[len(steps) // 2] or 1e-6
    return [(f, s, s / typical) for f, s in steps if s > 0.01 and s / typical > 4], typical


def main(rel):
    arm = build_rig(rel)
    anims = {a.name.replace('first_person ', '').replace('first_person:', ''): a
             for a in bpy.context.scene.nwo.animations}
    print('ANIMS %d: %s' % (len(anims), sorted(anims)))
    for name in ('idle', 'fire_1', 'overheating', 'overheated', 'o_h_exit', 'vent_loop'):
        if name in anims:
            a = anims[name]
            print('TYPE %-12s %s' % (name, {k: str(getattr(a, k)) for k in dir(a)
                  if any(w in k for w in ('type', 'overlay', 'frame_info', 'mode', 'state'))
                  and not k.startswith('_') and not callable(getattr(a, k))}))
    samples = {}
    for name, anim in sorted(anims.items()):
        s = sample(arm, anim)
        samples[name] = s
        hits, typical = spikes(s)
        print('ANIM %-26s frames %4d  typical step %.4f%s'
              % (name, len(s), typical,
                 ''.join('\n     SPIKE at frame %d: %.4f off the midpoint of its neighbours (%.0fx typical)' % h for h in hits)))
    if '--detail' in sys.argv:
        name = sys.argv[sys.argv.index('--detail') + 1]
        fr = samples[name]
        print('DETAIL %s: frame, step, off-midpoint, per bone dx dy dz of the step' % name)
        for i in range(1, len(fr) - 1):
            (fa, a), (fb, b), (fc, c) = fr[i - 1], fr[i], fr[i + 1]
            step = max((b[k] - a[k]).length for k in WATCH)
            spike = max((b[k] - (a[k] + c[k]) * 0.5).length for k in WATCH)
            dv = b['b_gun'] - a['b_gun']
            print('DETAIL %3d  step %.4f  spike %.4f  gun d=(%+.4f %+.4f %+.4f)'
                  % (fb, step, spike, dv.x, dv.y, dv.z))
    for name in ('overheated', 'vent_loop', 'idle'):
        if name in samples and samples[name]:
            first, last = samples[name][0][1], samples[name][-1][1]
            print('LOOPSEAM %-12s last->first %.4f' % (name, max((first[k] - last[k]).length
                                                                 for k in WATCH)))
    for a, b in CHAINS:
        if a in samples and b in samples and samples[a] and samples[b]:
            last, first = samples[a][-1][1], samples[b][0][1]
            gap = max((first[k] - last[k]).length for k in WATCH)
            dist = [(max((fr[k] - last[k]).length for k in WATCH), f)
                    for f, fr in samples[b]]
            best = min(dist)
            print('HANDOFF %-14s -> %-14s %.4f   closest frame of %s: %d (%.4f), first frames %s'
                  % (a, b, gap, b, best[1], best[0],
                     ' '.join('%.3f' % d for d, _f in dist[:8])))


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main(argv[0] if argv and not argv[0].startswith('--') else GRAPH)
