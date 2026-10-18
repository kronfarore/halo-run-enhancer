r"""Halo 3 THIRD-person animations onto Halo 1's cyborg (the player), for a port's own class.

WHY A COPY, NOT A RETARGET (measured 2026-10-18)
------------------------------------------------
Halo 3's Master Chief (`objects\characters\masterchief\masterchief.render_model`, 51 nodes)
holds Halo 1's cyborg (`characters\cyborg\cyborg.gbxmodel`, 19 `bip01` nodes) as its core:
the same names (pelvis -> bip01 pelvis, l_thigh -> bip01 l thigh, ...), the same parents and
the same bone offsets (pelvis z 0.3944, spine 0.0374, spine1 0.074, clavicles (0.0635, 0,
+-0.0598), upper arm 0.0304, forearm 0.1086, neck 0.0861, head 0.0172, foot 0.1563) -- only
the calf (H1 0.1721, H3 0.1803) and the hand (0.1138 / 0.115) differ. The other 32 Halo 3
nodes are fingers and toes, leaves Halo 1 does not have. Both right_hand markers carry the
same rotation, so a weapon sits in the hand the same way. So every node's LOCAL rotation is
copied (conjugated: Halo 1 tags store the inverse, h1_fp_retarget), the bones keep Halo 1's
offsets, and the pelvis keeps Halo 3's, lowered per frame so the lower foot lands where
Halo 3's did on its longer calves.

Root motion: Halo 3 keeps it outside the frames (h3_fp_pose.movement). Halo 1's stock STAND
moves carry none (stand pistol move-front: dx sums to 0), its CROUCH moves do (0.9 wu a
cycle): `root_motion` lists the Halo 1 animations that get Halo 3's.

Compiled straight into the cyborg's graph with Reclaimer (compile_animation): decompiling a
stock cyborg animation and compiling it back gives the same frame info and every quaternion
within one int16 step. Halo 1 graphs hold at most 256 animations and the cyborg is at 255 --
the new ones take the free slots, then unreferenced animations (`z...` names first), then a
slot freed by pointing exact duplicates at one copy.

THE CLASS: the engine picks a weapon's CLASS by its label (the Elite's graph keeps the sword,
label `fb`, in a class `sword`), and idle / move live at class level. A port that wants its
own idle and moves gets its own class in the stances listed (`classes`), a copy of the donor
class with its label alone in it; the label leaves the donor class there.

Config: ports_h1/<weapon>.py, section 'pickable', key 'third_person':
    {'graph': H3 jmad, 'class': new class, 'from_class': donor class, 'label': weapon label,
     'stances': {H1 unit: H3 mode},
     'class_anims': {H1 class slot: H3 'mode:class:anim' (or {H1 unit: ...})},
     'type_anims': {H1 weapon-type slot: H3 animation (or {H1 unit: ...})},
     'root_motion': [H1 animation names]}

    python h1_3p_retarget.py energy_sword --list
    python h1_3p_retarget.py energy_sword --preview "crouch sword fb idle" [--frame N] [--yaw 90]
Written by h1_pickable_weapons.teach_cyborg (its --write).
"""
import argparse
import copy
import hashlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import paths  # noqa: E402
import h3_anim_decode as dec  # noqa: E402
import h3_fp_pose as P  # noqa: E402
import h3tag  # noqa: E402
import h1_fp_retarget as F  # noqa: E402
import fp_render as R  # noqa: E402
import ports_h1  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.enums import (unit_weapon_animation_names as CLASS_SLOTS,  # noqa: E402
                             unit_weapon_type_animation_names as TYPE_SLOTS)
from reclaimer.animation.jma import JmaAnimation, JmaNodeState  # noqa: E402
from reclaimer.animation.animation_compilation import compile_animation  # noqa: E402
from reclaimer.animation.animation_decompilation import (  # noqa: E402
    antr_nodes_to_jms_nodes, extract_animation)

CYBORG = r'characters\cyborg\cyborg'
# a node an animation leaves out sits at its bind transform (h1_fp_retarget.load)
H3_MODEL = r'objects\characters\masterchief\masterchief.render_model'
MAX_ANIMS = 256
LOOPING = ('idle', 'move-front', 'move-back', 'move-left', 'move-right')


def configs():
    return {k: w['third_person'] for k, w in ports_h1.section('pickable').items()
            if w.get('third_person')}


def h3_node(h1):
    return h1[len('bip01 '):].replace(' ', '_')


# ---------------------------------------------------------------- Halo 3 side

_H3 = {}


def h3_graph(graph):
    """(nodes, {anim: (type, frame info type, member blob)}, tag, events), cached."""
    if graph not in _H3:
        xml = F.export_xml(graph)
        nodes = P.skeleton_from_xml(xml)
        tag = h3tag.Tag(os.path.join(F.H3EK, 'tags', graph))
        located = {(e['group'], e['index']): e for e in dec.blobs(tag, dec.members_from_xml(xml))}
        anims = {n: (typ, fit, located.get(mem)) for n, typ, fit, mem in P.animations_from_xml(xml)}
        _H3[graph] = (nodes, anims, tag, F.frame_events(xml))
    return _H3[graph]


def h3_frames(graph, name):
    """(type, [pose per frame], [movement per frame], events)"""
    nodes, anims, tag, events = h3_graph(graph)
    typ, _fit, e = anims[name]
    if e is None or not e['ok']:
        raise SystemExit('%s: not decodable in %s' % (name, graph))
    return typ, P.poses(tag, e, nodes), P.movement(tag, e), events.get(name, [])


# ---------------------------------------------------------------- conversion

def _mul(A, B):
    return (R.qmul(A[0], B[0]), R.xform(A, B[1]))


def _world(order, parent, local):
    out = {}
    for n in order:
        p = parent[n]
        out[n] = _mul(out[p], local[n]) if p else local[n]
    return out


def h1_offsets(d):
    """{H1 node: local translation wu} -- the stock stand pistol idle's first frame (the
    bones every cyborg animation uses)."""
    A = d.animations.STEPTREE
    i = [a.name for a in A].index('stand pistol idle')
    j = extract_animation(i, d, write_jma=False)
    return {n.name: (s.pos_x / 100.0, s.pos_y / 100.0, s.pos_z / 100.0)
            for n, s in zip(j.nodes, j.frames[0])}


def convert(d, graph, h3name, root_motion):
    """One Halo 3 animation -> (type, [{H1 node: (q ROTATION convention, t wu)}] per frame,
    key frame). Halo 3 poses are rotation convention (h3_fp_pose)."""
    typ, frames, move, events = h3_frames(graph, h3name)
    h3 = h3_graph(graph)[0]
    idx = {n: i for i, (n, _p) in enumerate(h3)}
    h3_parent = {n: (h3[p][0] if p >= 0 else None) for n, p in h3}
    names = [n.name for n in d.nodes.STEPTREE]
    h1_parent = {}
    for n in d.nodes.STEPTREE:
        h1_parent[n.name] = None
    for n in d.nodes.STEPTREE:
        k = n.first_child_node_index
        while k >= 0:
            h1_parent[names[k]] = n.name
            k = d.nodes.STEPTREE[k].next_sibling_node_index
    order = []
    while len(order) < len(names):                  # parents first
        for n in names:
            if n not in order and (h1_parent[n] is None or h1_parent[n] in order):
                order.append(n)
    for n in names:
        if h3_parent[h3_node(n)] != (h3_node(h1_parent[n]) if h1_parent[n] else None):
            raise SystemExit('%s: Halo 3 parent %s, Halo 1 %s' % (n, h3_parent[h3_node(n)],
                                                                 h1_parent[n]))
    off = h1_offsets(d)
    bind = F.rm_defaults(H3_MODEL)
    root = order[0]
    feet = ('bip01 l foot', 'bip01 r foot')
    out = []
    x = y = 0.0
    for f, pose in enumerate(frames):
        h3l = {}
        for n in names:
            q, t, _s = pose[idx[h3_node(n)]]
            h3l[n] = (q if q is not None else bind[h3_node(n)][0],
                      t if t is not None else bind[h3_node(n)][1])
        h1l = {n: (h3l[n][0], h3l[n][1] if n == root else off[n]) for n in names}
        w3, w1 = _world(order, h1_parent, h3l), _world(order, h1_parent, h1l)
        dz = min(w3[n][1][2] for n in feet) - min(w1[n][1][2] for n in feet)
        q, t = h1l[root]
        t = (t[0] + x, t[1] + y, t[2] + dz)
        h1l[root] = (q, t)
        out.append(h1l)
        if move and root_motion:
            x += move[f][0]
            y += move[f][1]
    key = next((fr for ty, fr in events if 'primary' in ty), 0)
    return typ, out, key, (x, y)


def _continuous(frames):
    prev = None
    out = []
    for fr in frames:
        if prev is not None:
            fr = {n: ((tuple(-c for c in q) if sum(a * b for a, b in zip(q, prev[n][0])) < 0
                       else q), t) for n, (q, t) in fr.items()}
        out.append(fr)
        prev = fr
    return out


def jma_for(d, h1name, typ, frames, loop, motion):
    """The JmaAnimation Halo 1's compiler takes: one frame more than the animation keeps (a
    loop ends on its first frame moved on by a cycle's root motion, a one-shot on its last)."""
    names = [n.name for n in d.nodes.STEPTREE]
    root = names[0]
    if loop:
        q, t = frames[0][root]
        end = dict(frames[0], **{root: (q, (t[0] + motion[0], t[1] + motion[1], t[2]))})
    else:
        end = frames[-1]
    frames = _continuous(frames + [end])
    a0 = d.animations.STEPTREE[[a.name for a in d.animations.STEPTREE].index('stand pistol idle')]
    base = typ == 'base'
    j = JmaAnimation(h1name, a0.node_list_checksum, 'base' if base else 'replacement',
                     'dx_dy' if base else 'none', False,
                     antr_nodes_to_jms_nodes(d.nodes.STEPTREE))
    for fr in frames:
        st = []
        for n in names:
            q, t = fr[n]
            q = R.qconj(q)                                  # Halo 1 stores the inverse
            st.append(JmaNodeState(t[0] * 100, t[1] * 100, t[2] * 100, q[1], q[2], q[3], q[0], 1.0))
        j.frames.append(st)
    if base:
        j.calculate_root_node_info()
    j.calculate_animation_flags()
    return j


# ---------------------------------------------------------------- the graph

def _anim_refs(d):
    """Every `animation` index holder in the graph (slot structs) + the next-animation chains."""
    def blk(b):
        return list(b.STEPTREE)
    out = []
    for o in d.objects.STEPTREE:
        out.append(o)
    for u in d.units.STEPTREE:
        out += blk(u.animations)
        for wc in u.weapons.STEPTREE:
            out += blk(wc.animations)
            for wt in wc.weapon_types.STEPTREE:
                out += blk(wt.animations)
    for grp in (d.weapons, d.vehicles, d.devices, d.fp_animations):
        for e in grp.STEPTREE:
            if hasattr(e, 'animations'):
                out += blk(e.animations)
    out += blk(d.unit_damages)
    return out


def referenced(d):
    used = {r.animation for r in _anim_refs(d)}
    used |= {a.next_animation for a in d.animations.STEPTREE}
    return used


def free_slots(d, n, keep=()):
    """n animation indices the new animations may take: appended while the graph is under
    256, then unreferenced ones (`z` names first), then duplicates folded onto one copy."""
    A = d.animations.STEPTREE
    out = list(range(len(A), min(MAX_ANIMS, len(A) + n)))
    used = referenced(d) | set(keep)
    spare = sorted((i for i in range(len(A)) if i not in used),
                   key=lambda i: (not A[i].name.startswith('z'), i))
    out += spare[:n - len(out)]
    if len(out) < n:
        seen = {}
        for i, a in enumerate(A):
            h = hashlib.sha1(bytes(a.frame_data.data) + bytes(a.default_data.data)
                             + bytes(a.frame_info.data)).hexdigest()
            sig = (h, a.type.data, a.frame_info_type.data, a.frame_count, a.sound,
                   a.sound_frame_index, a.key_frame_index, a.loop_frame_index,
                   int(a.flags.data), a.next_animation)
            if sig in seen and i not in keep and len(out) < n:
                first = seen[sig]
                for r in _anim_refs(d):
                    if r.animation == i:
                        r.animation = first
                print('   %r folded onto its duplicate %r (slot freed)' % (a.name, A[first].name))
                out.append(i)
            else:
                seen.setdefault(sig, i)
    if len(out) < n:
        raise SystemExit('cyborg graph: %d animation slot(s) needed, %d free' % (n, len(out)))
    return out


def _class(u, name):
    return next((wc for wc in u.weapons.STEPTREE if wc.name == name), None)


def _slot(names, s):
    return names.index(s)


def install(d, cfg):
    """The port's own class in each stance, its Halo 3 animations compiled into free slots."""
    A = d.animations.STEPTREE
    units = {u.label: u for u in d.units.STEPTREE}
    jobs = {}                       # H1 animation name -> (H3 name, loop, template index)
    wiring = []                     # (unit, 'class' | 'type', slot, H1 name)

    def want(unit, kind, slot, h3name, template):
        if kind == 'class':
            h1name = '%s %s %s' % (unit, cfg['class'], slot)
        else:
            h1name = '%s %s %s %s' % (unit, cfg['class'], cfg['label'], slot)
        same = [k for k, v in jobs.items() if v[0] == h3name]
        if same:                                    # one Halo 3 animation, one Halo 1 copy
            h1name = same[0]
        else:
            jobs[h1name] = (h3name, slot in LOOPING, template)
        wiring.append((unit, kind, slot, h1name))

    for unit in cfg['stances']:
        donor = _class(units[unit], cfg['from_class'])
        for slot, src in cfg['class_anims'].items():
            src = src[unit] if isinstance(src, dict) else src
            if src:
                tpl = donor.animations.STEPTREE[_slot(CLASS_SLOTS, slot)].animation
                want(unit, 'class', slot, src, tpl)
        fb = next(wt for wc in (donor, _class(units[unit], cfg['class'])) if wc
                  for wt in wc.weapon_types.STEPTREE if wt.label == cfg['label'])
        for slot, src in cfg['type_anims'].items():
            src = src[unit] if isinstance(src, dict) else src
            tpl = fb.animations.STEPTREE[_slot(TYPE_SLOTS, 'melee')].animation
            want(unit, 'type', slot, src, tpl)

    # the class: a copy of the donor, the label alone in it, the label out of the donor
    for unit in cfg['stances']:
        u = units[unit]
        donor = _class(u, cfg['from_class'])
        types = donor.weapon_types.STEPTREE
        k = next((i for i, wt in enumerate(types) if wt.label == cfg['label']), None)
        own = _class(u, cfg['class'])
        if k is None:                               # already moved (a tag written before)
            continue
        if own is None:
            u.weapons.STEPTREE.append(copy.deepcopy(donor))
            own = u.weapons.STEPTREE[-1]
            own.name = cfg['class']
        while own.ik_points.STEPTREE:
            own.ik_points.STEPTREE.pop()
        mine = copy.deepcopy(types[k])
        while own.weapon_types.STEPTREE:
            own.weapon_types.STEPTREE.pop()
        own.weapon_types.STEPTREE.append(mine)
        types.pop(k)

    keep = {v[2] for v in jobs.values()}
    by_name = {a.name: i for i, a in enumerate(A)}
    todo = [h for h in jobs if h not in by_name]
    slots = dict(zip(todo, free_slots(d, len(todo), keep)))
    slots.update({h: by_name[h] for h in jobs if h in by_name})
    for h1name, (h3name, loop, tpl) in jobs.items():
        typ, frames, key, motion = convert(d, cfg['graph'], h3name, h1name in cfg.get('root_motion', ()))
        j = jma_for(d, h1name, typ, frames, loop, motion)
        i = slots[h1name]
        blk = copy.deepcopy(A[tpl])
        err = compile_animation(blk, j)
        if err:
            raise SystemExit('%s: %s' % (h1name, err))
        blk.sound = -1
        blk.sound_frame_index = 0
        blk.key_frame_index = 0          # every stock cyborg 3P melee / fire: 0 (the FP one times it)
        blk.second_key_frame_index = 0
        blk.loop_frame_index = 0
        blk.first_permutation_index = i
        blk.chance_to_play = 1.0
        if i == len(A):
            A.append(blk)
        else:
            old = A[i].name
            A[i] = blk
            if old != h1name:
                print('   slot #%d %r -> %r' % (i, old, h1name))
        print('   #%d %-28s <- %-32s %-11s %3d fr key %d%s' % (
            i, h1name, h3name, typ, blk.frame_count, blk.key_frame_index,
            '  root motion %.3f wu' % math.hypot(*motion) if any(motion) else ''))
    for unit, kind, slot, h1name in wiring:
        own = _class(units[unit], cfg['class'])
        if kind == 'class':
            own.animations.STEPTREE[_slot(CLASS_SLOTS, slot)].animation = slots[h1name]
        else:
            wt = own.weapon_types.STEPTREE[0]
            wt.animations.STEPTREE[_slot(TYPE_SLOTS, slot)].animation = slots[h1name]
    for unit in cfg['stances']:
        own = _class(units[unit], cfg['class'])
        print('   %s/%s %s: %s' % (unit, own.name, own.weapon_types.STEPTREE[0].label, ', '.join(
            '%s=%s' % (CLASS_SLOTS[k], A[s.animation].name)
            for k, s in enumerate(own.animations.STEPTREE) if s.animation >= 0
            and CLASS_SLOTS[k] in cfg['class_anims'])))
    print('cyborg graph: %d animations' % len(A))


# ---------------------------------------------------------------- preview

def preview(d, name, frame, yaw, out, weapon=None):
    """The cyborg (and the weapon on its right hand marker) posed by one compiled animation."""
    A = d.animations.STEPTREE
    j = extract_animation([a.name for a in A].index(name), d, write_jma=False)
    st = j.frames[min(frame, len(j.frames) - 1)]
    local = {n.name: ((s.rot_w, s.rot_i, s.rot_j, s.rot_k),
                      (s.pos_x / 100.0, s.pos_y / 100.0, s.pos_z / 100.0))
             for n, s in zip(j.nodes, st)}
    model = R.load_model(CYBORG)
    names, parents = model[0], model[1]
    world = R.compose(names, parents, local)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    view = ((math.cos(math.radians(yaw) / 2), 0.0, 0.0, math.sin(math.radians(yaw) / 2)),
            (1.6, 0.0, -0.35))
    groups = [R.posed_tris(model, {n: _mul(view, W) for n, W in world.items()}, (120, 160, 110))]
    if weapon:
        from reclaimer.hek.defs.mod2 import mod2_def
        md = mod2_def.build(filepath=os.path.join(R.TAGS, CYBORG + '.gbxmodel')).data.tagdata
        mk = None
        for rg in md.regions.STEPTREE:
            for pm in rg.permutations.STEPTREE:
                for m in pm.local_markers.STEPTREE:
                    if m.name == 'right hand':
                        mk = m
        mq = R.qconj((mk.rotation.w, mk.rotation.i, mk.rotation.j, mk.rotation.k))
        hand = _mul(world[names[mk.node_index]],
                    (mq, (mk.translation.x, mk.translation.y, mk.translation.z)))
        wm = R.load_model(weapon)
        wb = R.compose(wm[0], wm[1], wm[2])
        groups.append(R.posed_tris(wm, {n: _mul(view, _mul(hand, W)) for n, W in wb.items()},
                                   (110, 200, 230)))
    R.render(groups, out, title='%s frame %d/%d yaw %d' % (name, frame, len(j.frames), yaw))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('weapon', choices=sorted(configs()))
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--preview')
    ap.add_argument('--frame', type=int, default=0)
    ap.add_argument('--yaw', type=float, default=180.0)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'retarget_3p.png'))
    ap.add_argument('--stock', action='store_true', help='preview the tag as it is')
    a = ap.parse_args()
    cfg = configs()[a.weapon]
    p = os.path.join(paths.HCEEK, 'tags', CYBORG + '.model_animations')
    d = antr_def.build(filepath=p).data.tagdata
    if a.list:
        _n, anims, _t, _e = h3_graph(cfg['graph'])
        for n, (typ, fit, e) in anims.items():
            if (':%s:' % cfg['h3_class']) in n:
                print('%-40s %-11s %-10s %s fr' % (n, typ, fit, e and e['frames']))
        return
    if not a.stock:
        install(d, cfg)             # in memory: the tag is written by h1_pickable_weapons
    if a.preview:
        w = ports_h1.section('pickable')[a.weapon]
        print(preview(d, a.preview, a.frame, a.yaw, a.out, w.get('weapon')))


if __name__ == '__main__':
    main()
