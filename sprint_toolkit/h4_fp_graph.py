r"""Halo 4 port, step 9: the port's OWN first-person graph, with the overheat jerk fixed.

THE JERK (user's slow-motion video, boot 11): at the end of overheating the whole first-
person view -- both arms and the rifle -- shifts right for about two frames and snaps back.
Measured by h4_fp_jump.py on the Beam Rifle's graph, hands and gun relative to the camera:

    overheating -> o_h_exit     0.0010   (Bungie authored these two to join)
    overheating -> overheated   0.0353   (~35x a normal step of the hold)
    overheated  -> o_h_exit     0.0350
    all six are BASE animations, no overlays -- the measure is not an artifact

So `overheated`, the hold between them, is DISPLACED from both neighbours, and no frame of
o_h_exit matches it (closest 0.031): trimming frames could not fix it. The Beam Rifle never
overheats in normal Halo 4 play, so nobody saw it. Here `overheated` is rewritten as a
still hold of `overheating`'s final pose, same length: both hand-offs become ~0.001.

OWN GRAPH, because the Beam Rifle uses fp_beam_rifle too. Seeded with a copy of it before
export -- Foundry exporting into an EXISTING graph merges and keeps the events and sounds
inline (the Reach retime's lesson); its asset is named after the .blend's folder:

    objects\characters\storm_fp\weapons\rifle\fp_focus_rifle\fp_focus_rifle

h4_make_port_weapon.py points the weapon's first-person animations at it.

    blender --background --python h4_fp_graph.py [-- --write]
"""
import importlib.util
import os
import shutil
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('h4_fp_jump', os.path.join(HERE, 'h4_fp_jump.py'))
jump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jump)

H4EK = jump.H4EK
TAGS = jump.TAGS
SOURCE = jump.GRAPH
OWN_REL = r'objects\characters\storm_fp\weapons\rifle\fp_focus_rifle\fp_focus_rifle'
OWN = OWN_REL + '.model_animation_graph'
HOLD_FROM, HOLD_INTO = 'overheating', 'overheated'


def action_of(anim):
    return anim.action_tracks[0].action if anim.action_tracks else None


def hold_final_pose(src_anim, dst_anim):
    """Every channel of dst = src's value at its LAST frame, on every key."""
    src, dst = action_of(src_anim), action_of(dst_anim)
    last = src_anim.frame_end
    srcs = {(fc.data_path, fc.array_index): fc for fc in jump_fcurves(src)}
    changed = missing = 0
    for fc in jump_fcurves(dst):
        s = srcs.get((fc.data_path, fc.array_index))
        if s is None:
            missing += 1
            continue
        v = s.evaluate(last)
        for k in fc.keyframe_points:
            k.co.y = v
            k.handle_left.y = v
            k.handle_right.y = v
        fc.update()
        changed += 1
    return changed, missing


def jump_fcurves(action):
    if getattr(action, 'fcurves', None):
        yield from action.fcurves
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def main(write):
    arm = jump.build_rig(SOURCE)
    anims = {a.name.replace('first_person ', '').replace('first_person:', ''): a
             for a in bpy.context.scene.nwo.animations}
    changed, missing = hold_final_pose(anims[HOLD_FROM], anims[HOLD_INTO])
    print('%s rewritten as a hold of %s\'s last frame: %d channels (%d without a source)'
          % (HOLD_INTO, HOLD_FROM, changed, missing))
    samples = {n: jump.sample(arm, anims[n]) for n in (HOLD_FROM, HOLD_INTO, 'o_h_exit')}
    for a, b in ((HOLD_FROM, HOLD_INTO), (HOLD_INTO, 'o_h_exit')):
        last, first = samples[a][-1][1], samples[b][0][1]
        print('handoff %-12s -> %-10s %.4f' % (a, b, max((first[k] - last[k]).length
                                                       for k in jump.WATCH)))
    if not write:
        print('(dry run -- pass --write)')
        return
    sc = bpy.context.scene.nwo
    sc.asset_type = 'animation'
    for a in sc.animations:
        a.export_this = True
    out = os.path.join(TAGS, OWN)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        shutil.copyfile(os.path.join(TAGS, SOURCE), out)
        print('seeded %s from %s' % (OWN_REL, SOURCE))
    blend = os.path.join(H4EK, 'data', OWN_REL + '.blend')
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print('export', bpy.ops.nwo.export_scene())
    # THE EVENTS stay the shipped ones. Foundry's round trip wrote a SMALLER event list
    # (25,224 bytes against the shipped 32,491) -- events lost on the way. No animation's
    # timing changed (overheated is the same length), so the Beam Rifle's own shipped list
    # (72 sound references, 40 per-animation event sets) is exactly right; build_rig keeps
    # that file byte for byte through the import.
    shutil.copyfile(os.path.join(TAGS, os.path.splitext(SOURCE)[0] + '.frame_event_list'),
                    os.path.join(TAGS, OWN_REL + '.frame_event_list'))
    print('events: the shipped frame_event_list copied as the port\'s own')


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main('--write' in argv)
