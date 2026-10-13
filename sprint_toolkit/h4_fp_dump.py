r"""Halo 4 first-person graph -> per-frame bone matrices (JSON), the DECODE half of an `h4:` FP
source (the Storm Rifle, wave C1, 2026-10-13).

Halo 4 graphs are COMPRESSED-ONLY (the member's sections hold one codec stream; Reach's full float
copy is not there -- see h4_tags.py), so they are decoded the way the H4 port kit did: Foundry
(H4EK project) imports the graph onto the first-person arms plus the graph's own weapon bones
(h4_fp_jump.build_rig), and Blender is sampled frame by frame. This writes, per animation, every
bone's ARMATURE-SPACE matrix per frame and each bone's REST matrix; h4_tags.load_graph turns them
into Halo-convention local transforms (calibrated against the render models' bind poses, so
Foundry's bone-axis conventions drop out).

    blender --background --python h4_fp_dump.py -- <graph tag path> [<out.json>]

Default out: out\h4_fp\<graph basename>.json. h4_fp_jump.build_rig puts back the graph's
frame_event_list (Foundry's import rewrites it); nothing else in H4EK is written.
"""
import importlib.util
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('h4_fp_jump', os.path.join(HERE, 'h4_fp_jump.py'))
jump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jump)


def flat(m):
    return [round(m[r][c], 7) for r in range(4) for c in range(4)]


def main(rel, out):
    # FOUNDRY'S IMPORT drops a stray copy of the graph's events beside its folder, the separator
    # lost (`fp_assault_carbinestorm_fp_assault_carbine.model_animation_graph`, 31 KB; the H4 kit's
    # earlier runs left `fp_beam_riflestorm_...` / `fp_focus_riflefp_...`): removed when it is new
    src = os.path.join(jump.TAGS, rel)
    stray = os.path.dirname(src) + os.path.basename(src)
    had = os.path.exists(stray)
    arm = jump.build_rig(rel)
    if not had and os.path.exists(stray):
        os.remove(stray)
        print('removed Foundry stray', stray)
    bones = [b.name for b in arm.data.bones]
    data = {'graph': rel, 'bones': bones,
            'parents': [b.parent.name if b.parent else None for b in arm.data.bones],
            'rest': {b.name: flat(b.matrix_local) for b in arm.data.bones},
            'object': flat(arm.matrix_world), 'anims': {}}
    arm.animation_data_create()
    for anim in bpy.context.scene.nwo.animations:
        act = anim.action_tracks[0].action if anim.action_tracks else None
        arm.animation_data.action = act
        frames = []
        for f in range(int(anim.frame_start), int(anim.frame_end) + 1):
            bpy.context.scene.frame_set(f)
            frames.append([flat(arm.pose.bones[b].matrix) for b in bones])
        data['anims'][anim.name] = {'start': int(anim.frame_start), 'end': int(anim.frame_end),
                                    'type': getattr(anim, 'animation_type', ''),
                                    'frames': frames}
        print('DUMP %-40s %d frames' % (anim.name, len(frames)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)
    print('wrote', out, len(data['anims']), 'animations', len(bones), 'bones')


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    rel = argv[0] if argv else jump.GRAPH
    out = argv[1] if len(argv) > 1 else os.path.join(
        HERE, 'out', 'h4_fp', os.path.splitext(os.path.basename(rel))[0] + '.json')
    main(rel, out)
