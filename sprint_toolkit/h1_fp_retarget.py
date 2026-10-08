r"""Halo 3 first-person animations onto Halo 1's first-person arms.

WHY THIS IS A COPY, NOT A RETARGET (measured 2026-10-05)
--------------------------------------------------------
Halo 3's Master Chief FP arm skeleton (`objects\characters\masterchief\fp\fp.render_model`)
IS Halo 1's (`characters\cyborg\fp\fp.gbxmodel`): the same 37 nodes, the same parents,
and every bind position -- shoulders at y +-9.40, elbows at x 10.25, wrists at 21.14, every
knuckle -- equal to two decimals (JMS units). Names map one to one:

    base -> frame bone24     l_hand -> frame l wriste     l_middle_low -> frame l middlelow
    l_upperarm -> frame l upperarm, l_index_mid -> frame l index mid, ...

Two conventions differ, and nothing else:
  * QUATERNIONS. Halo 1 tags store the INVERSE rotation; Halo 3 stores the rotation.
    H1 = conjugate(H3). (Proof: fp_render.py draws the H1 AR idle correctly only when the
    tag's quaternions are conjugated; H3's render model and H1's gbxmodel bind rotations
    are each other's conjugates.)
  * THE CAMERA. Halo 3 animates a `camera_control` node and offsets `base` against it
    (sword idle: base at +2.86, 0, -8.0 cm, camera_control at the inverse). Halo 1's camera
    is the animation origin. So every frame is re-expressed in camera_control's frame:
    root = inverse(camera world) * base world. What the player sees relative to the
    view is kept exactly, including H3's camera shake, which becomes arm motion.

Halo 3 leaves nodes out of an animation when they sit at the bind pose (the sword idle
stores 39 of 40 rotations and only 5 translations); those come from the render models'
default transforms -- the arms' fp.render_model and the weapon's FP render model.

Weapon nodes map by a per-weapon table (`WEAPONS`, from ports_h1/<weapon>.py). The energy sword's H3 `handle` and
`blades` are Halo 1's `frame handle` and `frame blades`: Halo 3's sword descends from it.

    python h1_fp_retarget.py energy_sword --list
    python h1_fp_retarget.py energy_sword --preview first_person:idle [--frame N]
    python h1_fp_retarget.py energy_sword --write        # JMAs into HCEEK data\...\animations
"""
import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_fp_pose                       # noqa: E402
import fp_render as R                   # noqa: E402
import ports_h1                         # noqa: E402

H3EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
CACHE = os.path.join(HERE, 'out', 'h3_export')
ARMS_RM = r'objects\characters\masterchief\fp\fp.render_model'
FP_GRAPHS = r'objects\characters\masterchief\fp\weapons'

# Halo 3 node -> Halo 1 node, the arms (identical skeletons, see the docstring)
ARM_NAMES = {'base': 'frame bone24', 'l_hand': 'frame l wriste', 'r_hand': 'frame r wriste',
             'l_middle_low': 'frame l middlelow', 'r_middle_low': 'frame r middle low'}

# per weapon (ports_h1/<weapon>.py, section 'retarget'): the H3 FP graph, the H3 FP render
# model, the H1 weapon-node names, which H3 animation becomes which H1 one, and where the
# H1 tags go (keys: graph, render_model, nodes, h1_dir, h1_model[, h1_model_from], align,
# anims[, drop_nodes, view_offset, holds, grip_node, left_hand_offset(_anims), align_nodes])
WEAPONS = ports_h1.section('retarget')


def h1_arm_name(h3):
    if h3 in ARM_NAMES:
        return ARM_NAMES[h3]
    return 'frame ' + h3.replace('_', ' ')


def export_xml(rel):
    """`tool export-tag-to-xml` of a Halo 3 kit tag, cached by the tag's mtime."""
    src = os.path.join(H3EK, 'tags', rel)
    os.makedirs(CACHE, exist_ok=True)
    # keyed by the kit PATH, not the basename: generic names collide (the Spike Rifle's
    # fx\projectile.effect read the Carbine's cached one, 2026-10-08)
    out = os.path.join(CACHE, rel.replace('\\', '~').replace('/', '~') + '.xml')
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run([os.path.join(H3EK, 'tool.exe'), 'export-tag-to-xml', src, out],
                       cwd=H3EK, capture_output=True, timeout=600)
    if not os.path.exists(out):
        raise SystemExit('tool export-tag-to-xml failed for ' + rel)
    return out


def rm_defaults(rel):
    """{node: (q (w,x,y,z), t wu)} bind transforms of a Halo 3 render model."""
    s = io.open(export_xml(rel), encoding='utf-8', errors='replace').read()
    blk = s[s.find('<block name="nodes"'):]
    blk = blk[:blk.find('</block>')]
    out = {}
    for m in re.finditer(r'<element index="\d+" name="([^"]*)">(.*?)</element>', blk, re.S):
        b = m.group(2)
        t = tuple(float(x) for x in
                  re.search(r'default translation" value="([^"]*)"', b).group(1).split(','))
        q = tuple(float(x) for x in
                  re.search(r'default rotation" value="([^"]*)"', b).group(1).split(','))
        out[m.group(1)] = ((q[3], q[0], q[1], q[2]), t)
    return out


def frame_events(xml):
    """{anim name: [(event type, frame)]} -- the primary keyframe of a melee is here."""
    s = io.open(xml, encoding='utf-8', errors='replace').read()
    blk = s[s.find('<block name="animations"'):]
    out = {}
    for m in re.finditer(r'<element index="\d+" name="([^"]*)">\s*<field name="name"(.*?)'
                         r'<block name="sound events"', blk, re.S):
        evs = re.findall(r'name="type" value="([^"]*)".*?name="frame" value="(-?\d+)"',
                         m.group(2), re.S)
        out[m.group(1)] = [(t, int(f)) for t, f in evs]
    return out


def load(weapon):
    """(h3 nodes [(name, parent)], {anim: (type, frames)}, defaults, events)."""
    w = WEAPONS[weapon]
    xml = export_xml(w['graph'])
    nodes, anims = h3_fp_pose.load(os.path.join(H3EK, 'tags', w['graph']), xml)
    defaults = dict(rm_defaults(ARMS_RM))
    defaults.update(rm_defaults(w['render_model']))
    return nodes, anims, defaults, frame_events(xml)


def h1_skeleton(weapon, h3_nodes):
    """Halo 1 (names, parents) for the weapon's FP animation tag, in the order HCEEK's
    tool sorts them: by depth, then by name (matches every stock H1 FP graph checked --
    the plasma cannon's `frame gun` sits between `frame r wriste` and `frame l index low`).
    camera_control is dropped (folded into the root), and so are `drop_nodes`."""
    wmap = WEAPONS[weapon]['nodes']
    names, parents = [], []
    for n, p in h3_nodes:
        if _skip(weapon, n):
            continue
        names.append(wmap.get(n) or h1_arm_name(n))
        parents.append(None if p < 0 else (wmap.get(h3_nodes[p][0])
                                           or h1_arm_name(h3_nodes[p][0])))
    depth = {}
    for n, p in zip(names, parents):
        depth[n] = 0 if p is None else depth[p] + 1
    order = sorted(range(len(names)), key=lambda i: (depth[names[i]], names[i]))
    return [names[i] for i in order], [parents[i] for i in order]


IDENTITY = ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def _mul(A, B):
    """Transform product A * B, both (q, t) in rotation convention."""
    return (R.qmul(A[0], B[0]), R.xform(A, B[1]))


def ensure_model(weapon):
    """Build the FP model when it is a scaled copy of a world model (`h1_model_from`)."""
    w = WEAPONS[weapon]
    if w.get('h1_model_from'):
        import h1_scaled_model
        src, k = w['h1_model_from']
        h1_scaled_model.scale_model(src, w['h1_model'], k)
    return w['h1_model']


def h1_bind(weapon):
    """{H1 weapon node: WORLD bind (q, t)} of the Halo 1 model the port shows in first
    person, rotation convention. Its geometry is in that model's space."""
    names, parents, bind, _ = R.load_model(ensure_model(weapon))
    return R.compose(names, parents, bind)


def corrections(weapon, defaults, h3_nodes):
    """{H3 weapon node: C} with world_H1 = world_H3 * C.

    'same_space' (the sword): Halo 1's model and Halo 3's FP model share one model space
    -- the blade runs along +x to 0.35 in both -- and only the PIVOTS differ (H3 `blades`
    at 0.118 along x from the handle, H1's at 0.008 up z). So C = inverse(H3 bind world)
    * (H1 bind world): the H1 geometry lands exactly where H3's would have been.
    `align_nodes` entries are hand-placed corrections, for a weapon whose H1 model was
    never built to H3's proportions."""
    w = WEAPONS[weapon]
    out = {}
    if w.get('align') == 'same_space':
        h3w = {}
        for n, p in h3_nodes:                       # H3 weapon bind, its own model space
            if n not in w['nodes']:
                continue
            pn = h3_nodes[p][0] if p >= 0 else None
            h3w[n] = _mul(h3w[pn], defaults[n]) if pn in h3w else defaults[n]
        hb = h1_bind(weapon)
        for n, h1n in w['nodes'].items():
            out[n] = _mul(R.inverse(h3w[n]), hb[h1n])
    out.update(w.get('align_nodes', {}))
    return out


def _skip(weapon, n):
    """camera_control (folded into the root) and weapon nodes Halo 1's model lacks."""
    return n == 'camera_control' or n in WEAPONS[weapon].get('drop_nodes', ())


def _h1(weapon, n):
    return WEAPONS[weapon]['nodes'].get(n) or h1_arm_name(n)


def _vsub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _vlen(a):
    return sum(x * x for x in a) ** 0.5


def _rot_between(u, v):
    """Shortest rotation (w,x,y,z) taking direction u onto direction v."""
    lu, lv = _vlen(u) or 1.0, _vlen(v) or 1.0
    u = tuple(x / lu for x in u)
    v = tuple(x / lv for x in v)
    c = sum(x * y for x, y in zip(u, v))
    ax = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    q = (1.0 + c,) + ax
    n = _vlen(q) or 1.0
    return tuple(x / n for x in q)


def _move_left_hand(world, h3_nodes, grip, grip_node, ref, extra=(0.0, 0.0, 0.0)):
    """Two-bone IK: the left wrist moved by `grip` = (offset in the gun's space, wu;
    full-strength radius; zero radius), elbow kept in its own plane, hand orientation and
    fingers unchanged. Used where Halo 1's model is not Halo 3's shape, so H3's hand would
    sink into it. The offset fades out as the hand leaves the gun (reloads)."""
    offset, r_full, r_zero = grip
    S, E, W = (world[n][1] for n in ('l_upperarm', 'l_forearm', 'l_hand'))
    G = world[grip_node]
    local = R.xform(R.inverse(G), W)                       # the wrist in gun space
    d = _vlen(_vsub(local, ref))
    k = 1.0 if d <= r_full else max(0.0, 1.0 - (d - r_full) / (r_zero - r_full))
    if k <= 0.0 and not any(extra):
        return
    T = R.xform(G, tuple(a + k * b + e for a, b, e in zip(local, offset, extra)))
    a, b = _vlen(_vsub(E, S)), _vlen(_vsub(W, E))
    st = _vsub(T, S)
    c = min(_vlen(st), a + b - 1e-6)
    u = tuple(x / (_vlen(st) or 1.0) for x in st)
    cos_a = max(-1.0, min(1.0, (a * a + c * c - b * b) / (2 * a * c)))
    se = _vsub(E, S)
    perp = _vsub(se, tuple(sum(p * q for p, q in zip(se, u)) * x for x in u))
    pv = tuple(x / (_vlen(perp) or 1.0) for x in perp)
    sin_a = (1.0 - cos_a * cos_a) ** 0.5
    E2 = tuple(s + a * (cos_a * uu + sin_a * vv) for s, uu, vv in zip(S, u, pv))
    W2 = tuple(s + c * uu for s, uu in zip(S, u))
    r1 = _rot_between(se, _vsub(E2, S))
    qu, tu = world['l_upperarm']
    world['l_upperarm'] = (R.qmul(r1, qu), tu)
    qf, tf = world['l_forearm']
    fe = R.qrot(r1, _vsub(W, E))
    r2 = _rot_between(fe, _vsub(W2, E2))
    world['l_forearm'] = (R.qmul(r2, R.qmul(r1, qf)), E2)
    shift = _vsub(W2, W)
    kids = {'l_hand'}
    for n, p in h3_nodes:                                   # the hand and its fingers
        if p >= 0 and h3_nodes[p][0] in kids:
            kids.add(n)
    for n in kids:
        q, t = world[n]
        world[n] = (q, tuple(x + y for x, y in zip(t, shift)))


def retarget_frame(h3_nodes, pose, defaults, weapon, corr, grip_ref=None,
                   extra=(0.0, 0.0, 0.0)):
    """One Halo 3 BASE frame -> {H1 name: (q in Halo 1 TAG convention, t wu)} LOCAL.

    Solved in world space: every H3 node's world transform, re-expressed relative to
    camera_control, weapon nodes multiplied by their bind correction, then each H1 node's
    local = inverse(H1 parent world) * world. For the arms that reproduces H3's locals."""
    local = {}
    for (n, p), (q, t, s) in zip(h3_nodes, pose):
        dq, dt = defaults.get(n, IDENTITY)
        local[n] = (q if q is not None else dq, t if t is not None else dt)
    world = {}
    for n, p in h3_nodes:
        world[n] = _mul(world[h3_nodes[p][0]], local[n]) if p >= 0 else local[n]
    cam = world.get('camera_control')
    if cam is not None:
        icam = R.inverse(cam)
        world = {n: _mul(icam, W) for n, W in world.items()}
    off = WEAPONS[weapon].get('view_offset')
    if off:                                                  # the whole rig, view space (wu)
        world = {n: (W[0], tuple(W[1][k] + off[k] for k in range(3))) for n, W in world.items()}
    for n, C in corr.items():
        world[n] = _mul(world[n], C)
    grip = WEAPONS[weapon].get('left_hand_offset')
    if grip and grip_ref is not None:
        _move_left_hand(world, h3_nodes, grip, WEAPONS[weapon]['grip_node'], grip_ref, extra)
    if grip_ref is None and grip:                           # asked for the reference only
        return R.xform(R.inverse(world[WEAPONS[weapon]['grip_node']]), world['l_hand'][1])
    out = {}
    for n, p in h3_nodes:
        if _skip(weapon, n):
            continue
        W = world[n] if p < 0 else _mul(R.inverse(world[h3_nodes[p][0]]), world[n])
        out[_h1(weapon, n)] = (R.qconj(W[0]), tuple(W[1]))   # H1 stores the inverse rotation
    return out


def overlay_frames(h3_nodes, frames, animated, weapon):
    """An H3 OVERLAY -> H1 overlay frames: the reference frame first, then one per H3 frame.

    Both games keep an overlay's deltas only in the ANIMATED tracks (the roundtrip of the
    Oddball's moving/overlays through Reclaimer + HCEEK tool is exact, and a static track
    in them -- `frame r upperarm` at -0.094 -- cannot be a delta). So animated tracks pass
    through (rotation conjugated), the reference frame is identity/zero for them, and
    static tracks hold their first value throughout. camera_control is dropped.
    NOT YET SEEN IN GAME: the composition order of an H1 overlay delta is assumed to be
    the same as Halo 3's; the deltas are small, so a wrong order is a small error."""
    first = {}
    out = []
    for pose in frames:
        fr = {}
        for i, ((n, p), (q, t, s)) in enumerate(zip(h3_nodes, pose)):
            if _skip(weapon, n):
                continue
            if out and i not in animated['rot']:
                q = first[n][0]
            if out and i not in animated['trans']:
                t = first[n][1]
            fr[n] = (q if q is not None else IDENTITY[0],
                     tuple(t) if t is not None else (0.0, 0.0, 0.0))
        if not out:
            first = dict(fr)
        out.append({_h1(weapon, n): (R.qconj(q), t) for n, (q, t) in fr.items()})
    ref = {}
    for i, (n, p) in enumerate(h3_nodes):
        if _skip(weapon, n):
            continue
        q, t = out[0][_h1(weapon, n)]
        ref[_h1(weapon, n)] = (IDENTITY[0] if i in animated['rot'] else q,
                               (0.0, 0.0, 0.0) if i in animated['trans'] else t)
    return [ref] + out


def retarget(weapon, anim_name, nodes=None, anims=None, defaults=None):
    """(type, [ {H1 node: (q tag convention, t wu)} per frame ])"""
    if nodes is None:
        nodes, anims, defaults, _ = load(weapon)
    typ, frames, animated = anims[anim_name]
    if typ == 'overlay':
        return typ, overlay_frames(nodes, frames, animated, weapon)
    corr = corrections(weapon, defaults, nodes)
    ref = None
    if WEAPONS[weapon].get('left_hand_offset'):
        # where the left wrist rests on the gun: the idle's first frame, before any IK
        ref = retarget_frame(nodes, anims['first_person:idle'][1][0], defaults, weapon, corr)
    extra = WEAPONS[weapon].get('left_hand_offset_anims', {}).get(anim_name, (0.0, 0.0, 0.0))
    return typ, [retarget_frame(nodes, f, defaults, weapon, corr, ref, extra) for f in frames]


LOOPING = ('first-person idle', 'first-person posing', 'first-person moving')


def write_jmas(weapon, only=None):
    """Every mapped animation as a JMA into HCEEK data\\<h1_dir>\\animations.

    Halo 1's tool drops the LAST frame of a base animation (Reclaimer's decompiler appends
    a copy of frame 0, and the roundtrip is exact), so a looping animation gets frame 0
    appended and a one-shot gets its last frame repeated. Overlays carry their reference
    frame first, which the tool also drops."""
    from reclaimer.animation.jma import JmaAnimation, JmaNodeState, write_jma
    from reclaimer.model.jms import JmsNode
    w = WEAPONS[weapon]
    ensure_model(weapon)
    nodes, anims, defaults, _ = load(weapon)
    names, parents = h1_skeleton(weapon, nodes)
    idx = {n: i for i, n in enumerate(names)}
    jnodes = []
    for i, (n, p) in enumerate(zip(names, parents)):
        kids = [j for j, q in enumerate(parents) if q == n]
        sib = [j for j, q in enumerate(parents) if p is not None and q == p and j > i]
        jnodes.append(JmsNode(n, kids[0] if kids else -1, sib[0] if sib else -1,
                              parent_index=idx[p] if p is not None else -1))
    out_dir = os.path.join(HCEEK, 'data', w['h1_dir'], 'animations')
    written = []
    jobs = list(w['anims'].items())
    jobs += [(h3name, h1name) for h1name, (h3name, _n) in w.get('holds', {}).items()]
    for h3name, h1name in jobs:
        if only and h1name not in only and h3name not in only:
            continue
        typ, frames = retarget(weapon, h3name, nodes, anims, defaults)
        if h1name in w.get('holds', {}):           # a still: the source's LAST frame held
            frames = [frames[-1]] * w['holds'][h1name][1]
        if typ != 'overlay':
            frames = frames + [frames[0] if h1name in LOOPING else frames[-1]]
        states = [[JmaNodeState(t[0] * 100, t[1] * 100, t[2] * 100,
                                q[1], q[2], q[3], q[0], 1.0)
                   for q, t in (fr[n] for n in names)] for fr in frames]
        jma = JmaAnimation(h1name, 0, 'overlay' if typ == 'overlay' else 'base', 'none',
                           False, jnodes, states)
        path = os.path.join(out_dir, h1name + ('.jmo' if typ == 'overlay' else '.jmm'))
        write_jma(path, jma)
        written.append((path, len(frames)))
    return written


def preview(weapon, anim_name, frame, out):
    nodes, anims, defaults, _ = load(weapon)
    typ, frames = retarget(weapon, anim_name, nodes, anims, defaults)
    names, parents = h1_skeleton(weapon, nodes)
    world = R.compose(names, parents, frames[min(frame, len(frames) - 1)])
    groups = [R.posed_tris(R.load_model(R.HANDS), world, (200, 170, 120)),
              R.posed_tris(R.load_model(ensure_model(weapon)), world, (110, 200, 230))]
    R.render(groups, out, title='%s %s frame %d/%d (%s)' % (weapon, anim_name, frame,
                                                             len(frames), typ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('weapon', choices=sorted(WEAPONS))
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--preview')
    ap.add_argument('--frame', type=int, default=0)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'retarget.png'))
    a = ap.parse_args()
    if a.list:
        nodes, anims, defaults, events = load(a.weapon)
        for n, (typ, fr, animated) in anims.items():
            print('%-45s %-8s %4d  %s  -> %s' % (n, typ, len(fr), events.get(n, ''),
                                                  WEAPONS[a.weapon]['anims'].get(n, '-')))
        print(h1_skeleton(a.weapon, nodes))
    if a.preview:
        print(preview(a.weapon, a.preview, a.frame, a.out))
    if a.write:
        for path, n in write_jmas(a.weapon):
            print('%4d frames  %s' % (n, path))


if __name__ == '__main__':
    main()


