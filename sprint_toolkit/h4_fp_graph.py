r"""Halo 4 port, step 9: the port's OWN first-person graph.

NOW (boot 26): a BYTE COPY of the shipped Beam Rifle graph, plus ONE fix -- the
`overheating` loop frame index (set_loop_frames, the real cause of the overheat pop).
THE FOUNDRY RE-EXPORT BELOW CAUSED THE RETICLE DRIFT ("drifts while looking around, always
right, recentres when still; more the further I zoom"): every per-animation flag and
timing matched Bungie's, but the round trip re-encoded every animation's data, and the
reticle follows the first-person rig. Proven in the built map: the port pointed at
Bungie's graph (h4_map_poke.py --graph-back) -> drift gone; that graph with only the
loop-frame fix (--on-beam-graph --loop-frame 16=58) -> no pop, no jerk, no drift. The
smoothing / shift / dropped animations below were side-tracks of the pop hunt: kept for
reference behind --foundry, not used.

    blender --background --python h4_fp_graph.py [-- --write]            (the copy)
    blender --background --python h4_fp_graph.py -- --foundry [--write]  (old route)

THE OLD ROUTE'S HISTORY:

THE JERK (user's slow-motion video, boot 11): during the overheat the whole first-person
view -- both arms and the rifle -- shifts right for about two frames and comes back.

FIRST THEORY, WRONG (boot 12): h4_fp_jump.py found the `overheated` hold displaced 0.035
from both neighbours (overheating -> overheated, overheated -> o_h_exit, where
overheating -> o_h_exit joins at 0.001). Rewriting that hold as a still pose removed the
mismatch -- and the jerk stayed, now followed by a FREEZE (the still hold). The order
"jerk, then freeze" put the jerk BEFORE the hold, inside `overheating`; the user's
heat-meter timing ("shortly after halfway") agreed.

THE USER'S JERK (boot 13: "within the overheated animation when the heat is vented"):
`overheated` itself is clean (loop seam 0.0009), but it sits 0.035 off both neighbours,
and o_h_exit starts while heat still drains -- the hand-off is the jerk. `overheated` is
now SHIFTED as a whole to meet overheating's end (its motion kept; the still hold froze
it), which closes both joins (0.0000 / 0.0009, verified on the exported graph).

ALSO THE JOLT: h4_fp_jump.py --detail overheating -- frames 27-37 a deliberate fine shake,
then frame 44 kicks 0.0205, ~10x its neighbours, and 45-49 drift back. Frames 44-46 are
replaced by a straight line from frame 43 to 47 (worst spike there 0.0144 -> 0.0035);
every other frame stays Bungie's. The Beam Rifle never overheats in normal play, so nobody
saw it.

OWN GRAPH, because the Beam Rifle uses fp_beam_rifle too. Seeded with a copy of it before
export (Foundry exporting into an EXISTING graph merges); the asset is named after the
.blend's folder:

    objects\characters\storm_fp\weapons\rifle\fp_focus_rifle\fp_focus_rifle

and the SHIPPED frame_event_list is copied in after export (Foundry's round trip lost
events). h4_make_port_weapon.py points the weapon's first-person animations at it.

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
def action_of(anim):
    return anim.action_tracks[0].action if anim.action_tracks else None


def jump_fcurves(action):
    if getattr(action, 'fcurves', None):
        yield from action.fcurves
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


#: THE JOLT (boot 13: the jerk is INSIDE `overheating`, before the hold -- with the hold
#: frozen the order was jerk THEN freeze). h4_fp_jump.py --detail overheating: frames 27-37
#: are a deliberate fine shake (+-0.005 alternating), then frame 44 kicks 0.0205 -- ~10x
#: its neighbours (gun +0.009/-0.017) -- and 45-49 drift back. Frames 44-46 are replaced
#: by a straight line from frame 43 to 47; every other frame stays Bungie's.
SMOOTH_ANIM, SMOOTH_FROM, SMOOTH_TO = 'overheating', 43, 47


def smooth(anim, f0, f1):
    """Keys strictly between f0 and f1 -> the straight line between the values at f0, f1."""
    changed = 0
    for fc in jump_fcurves(action_of(anim)):
        v0, v1 = fc.evaluate(f0), fc.evaluate(f1)
        for k in fc.keyframe_points:
            if f0 < k.co.x < f1:
                t = (k.co.x - f0) / float(f1 - f0)
                v = v0 + (v1 - v0) * t
                dy = v - k.co.y
                k.co.y = v
                k.handle_left.y += dy
                k.handle_right.y += dy
                changed += 1
        fc.update()
    return changed


#: THE JERK THE USER SEES (boot 13, user: "within the overheated animation when the heat
#: is vented"): `overheated` itself is clean (loop seam 0.0009, steps <= 0.0019), but it
#: sits displaced 0.035 from BOTH neighbours, and o_h_exit starts while heat still drains.
#: overheating -> o_h_exit join at 0.001, so `overheated` is SHIFTED as a whole: every
#: channel + (overheating's last value - overheated's first value). Its own motion is
#: kept (the still-hold of boot 12 froze it); both joins close.
SHIFT_FROM, SHIFT_INTO = 'overheating', 'overheated'


def shift_to_join(src_anim, dst_anim):
    src, dst = action_of(src_anim), action_of(dst_anim)
    srcs = {(fc.data_path, fc.array_index): fc for fc in jump_fcurves(src)}
    changed = 0
    for fc in jump_fcurves(dst):
        sfc = srcs.get((fc.data_path, fc.array_index))
        if sfc is None or not len(fc.keyframe_points):
            continue
        delta = sfc.evaluate(src_anim.frame_end) - fc.evaluate(dst_anim.frame_start)
        for k in fc.keyframe_points:
            k.co.y += delta
            k.handle_left.y += delta
            k.handle_right.y += delta
        fc.update()
        changed += 1
    return changed


#: THE ONE-FRAME POP at ~half heat (user's video, frame 56 of 124: both hands + rifle
#: shifted for one frame) is NOT in the animation data. Diagnostic (boot 15): with the
#: PLASMA PISTOL's fp graph the pop is GONE. The Beam Rifle graph differs by a VENT set
#: (vent_enter / vent_loop / vent_exit) the Plasma Pistol's lacks, and vent_enter's second
#: frame steps 0.058 -- a mid-vent switch into it shows as exactly one odd frame. Left
#: OUT of the port's graph (the export rebuilds the graph from what is exported).
DROP = ('vent_enter', 'vent_loop', 'vent_exit',
        'flaps', 'barrel_spin', 'accelration_screens')
#: boot 16: the pop SURVIVED dropping the vent set, and dropping o_h_exit was a mistake
#: (the Plasma Pistol HAS o_h_exit -- an earlier name filter missed it; restored). What the
#: port graph has and the Plasma Pistol's does not, by name: three OVERLAYS -- flaps (1
#: frame), barrel_spin (21), accelration_screens (9) -- the Beam Rifle's flaps and barrel,
#: blended on top by weapon functions. The port's weapon (Sentinel base) exports `heat` as
#: blend_weight and blend_weight_barrel, so heat drives them: a weight crossing a threshold
#: mid-vent on a one-frame overlay = a one-frame pop at ~half heat. The Focus Rifle has no
#: flaps or spinning barrel; all three are left out.
#: THE SHAKE (user, boot 15: reduce it): overheating frames 27-37 alternate +-0.005 every
#: frame -- the Beam Rifle's heat vibration, not the Focus Rifle's. Damped by a centred
#: moving average (window 5) over frames 26..38: the alternation cancels, the slower
#: underlying motion stays.
DAMP_ANIM, DAMP_FROM, DAMP_TO, DAMP_WINDOW = 'overheating', 26, 38, 5


def damp(anim, f0, f1, window):
    half = window // 2
    changed = 0
    for fc in jump_fcurves(action_of(anim)):
        orig = {f: fc.evaluate(f) for f in range(f0 - half, f1 + half + 1)}
        for k in fc.keyframe_points:
            f = int(round(k.co.x))
            if f0 <= f <= f1:
                v = sum(orig[f + i] for i in range(-half, half + 1)) / window
                dy = v - k.co.y
                k.co.y = v
                k.handle_left.y += dy
                k.handle_right.y += dy
                changed += 1
        fc.update()
    return changed


def worst_spike(arm, anim, lo, hi):
    fr = [x for x in jump.sample(arm, anim) if lo - 1 <= x[0] <= hi + 1]
    best = (0, None)
    for (fa, a), (fb, b), (fc, c) in zip(fr, fr[1:], fr[2:]):
        d = max((b[k] - (a[k] + c[k]) * 0.5).length for k in jump.WATCH)
        best = max(best, (d, fb))
    return best


def copy_graph(write):
    """The port's graph = the shipped Beam Rifle graph byte for byte, its own event list
    a copy of the shipped one, then the loop-frame fix."""
    out = os.path.join(TAGS, OWN)
    if not write:
        print('would copy %s -> %s and set %s' % (SOURCE, OWN_REL, LOOP_FRAMES))
        print('(dry run -- pass --write)')
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copyfile(os.path.join(TAGS, SOURCE), out)
    shutil.copyfile(os.path.join(TAGS, os.path.splitext(SOURCE)[0] + '.frame_event_list'),
                    os.path.join(TAGS, OWN_REL + '.frame_event_list'))
    print('graph: %s = a byte copy of %s (+ its frame_event_list)' % (OWN_REL, SOURCE))
    set_loop_frames()
    print('FPGRAPH OK')


def main(write):
    arm = jump.build_rig(SOURCE)
    anims = {a.name.replace('first_person ', '').replace('first_person:', ''): a
             for a in bpy.context.scene.nwo.animations}
    a = anims[SMOOTH_ANIM]
    before = worst_spike(arm, a, SMOOTH_FROM - 3, SMOOTH_TO + 3)
    n = smooth(a, SMOOTH_FROM, SMOOTH_TO)
    after = worst_spike(arm, a, SMOOTH_FROM - 3, SMOOTH_TO + 3)
    print('%s frames %d..%d smoothed (%d keys): worst spike %.4f at %s -> %.4f at %s'
          % (SMOOTH_ANIM, SMOOTH_FROM + 1, SMOOTH_TO - 1, n, before[0], before[1],
             after[0], after[1]))
    def shake(anim):
        fr = [x for x in jump.sample(arm, anim) if DAMP_FROM <= x[0] <= DAMP_TO]
        return max(max((b[k] - (a[k] + c[k]) * 0.5).length for k in jump.WATCH)
                   for (_x, a), (_y, b), (_z, c) in zip(fr, fr[1:], fr[2:]))
    # (boot 16: the shake the user meant was WHILE FIRING, not this one -- the overheat
    # shake is Bungie's and stays; damp() is kept for a firing animation if needed)
    c = shift_to_join(anims[SHIFT_FROM], anims[SHIFT_INTO])
    print('%s shifted to join %s: %d channels' % (SHIFT_INTO, SHIFT_FROM, c))
    sm = {n: jump.sample(arm, anims[n]) for n in (SHIFT_FROM, SHIFT_INTO, 'o_h_exit')}
    for x, y in ((SHIFT_FROM, SHIFT_INTO), (SHIFT_INTO, 'o_h_exit'), (SHIFT_INTO, SHIFT_INTO)):
        last, first = sm[x][-1][1], sm[y][0][1]
        print('join %-12s -> %-10s %.4f' % (x, y, max((first[k] - last[k]).length
                                                     for k in jump.WATCH)))
    if not write:
        print('(dry run -- pass --write)')
        return
    sc = bpy.context.scene.nwo
    sc.asset_type = 'animation'
    dropped = []
    for a in sc.animations:
        short = a.name.replace('first_person ', '').replace('first_person:', '')
        a.export_this = short not in DROP
        if not a.export_this:
            dropped.append(short)
    print('left out of the port graph: %s' % dropped)
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
    set_loop_frames()


#: THE POP, FOUND (boot 19, by in-map bisection with h4_map_poke.py): `overheating`'s LOOP
#: FRAME INDEX was 0. When it finishes, the engine wraps to the loop frame and shows it for
#: ONE frame before the next state -- frame 0 is the PRE-overheat pose, both hands
#: elsewhere: the whole-rig pop "right before the idle", ~half heat. The Plasma Pistol's
#: (no pop) is 16. Set to the LAST frame, a wrap lands on the pose the arms are already in:
#: pop gone in game. Everything else tried before was not it (vent set, overlays,
#: o_h_exit, the still hold, the aim flag) -- see PORTING.md.
LOOP_FRAMES = {'first_person:overheating': 'last'}


def set_loop_frames():
    mb = jump.importlib.import_module(jump.KEY + '.managed_blam')

    class T(mb.Tag):
        pass

    with T(path=os.path.join(TAGS, OWN)) as t:
        anims = t.tag.SelectField('Struct:definitions[0]/Block:animations')
        for i in range(anims.Elements.Count):
            e = anims.Elements[i]
            name = e.Fields[0].GetStringData()
            if name not in LOOP_FRAMES:
                continue
            shared = e.SelectField('shared animation data').Elements[0]
            frames = int(shared.SelectField('frame count').GetStringData())
            want = frames - 1 if LOOP_FRAMES[name] == 'last' else int(LOOP_FRAMES[name])
            f = e.SelectField('loop frame index')
            was = f.GetStringData()
            f.SetStringData(str(want))
            print('%s loop frame index %s -> %s (of %d frames)' % (name, was, f.GetStringData(), frames))
        t.tag_has_changes = True


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if '--foundry' in argv:
        main('--write' in argv)
    else:
        copy_graph('--write' in argv)
