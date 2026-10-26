r"""Step 9 for a HALO 3 source: the source's OWN first-person animations, both species, imported
into Halo 2 with Bungie's own tool (`tool fp-model-animations`) -- no donor graph, no retime.
Written for the Assault Rifle, the wave-A pilot (2026-10-20); the donor route (clone + retime,
the SAW's) stays h2_port_animations.py.

WHY A COPY WORKS (H2_PORT_PLAN 0.4, measured): Halo 3's masterchief AND dervish FP arm skeletons
ARE Halo 2's -- the same names, parents and bind poses (0.0002 units at most) -- and Halo 2's FP
graphs carry the same `camera_control` node Halo 3's do. So every node's pose is taken as it is.

THE SOURCE FORMAT (read off Bungie's own files in H2EK data\digsite\...\fp_battle_rifle\
animations, e.g. `first-person reload-empty.JMM`, version 16394):

    16394 / node-list checksum / frame count / frame rate / actor count 1 / actor name
    node count, then per node: name, parent index (Bungie names arms `b_<name>`, weapon nodes
    `frame_<name>`, `b_camera_control`)
    per frame, per node: translation (x y z), rotation (i j k w), scale

  * transforms are ABSOLUTE, in model space (Bungie's frame: base -> l_upperarm is 9.40 apart,
    l_upperarm -> l_forearm 10.25 -- the bone lengths only hold composed), the rotation in the
    same convention as a JMS bind (l_forearm - l_upperarm = R(l_upperarm) * (10.251, 0, 0));
  * the tool DROPS THE LAST FRAME (Bungie's reload-empty: 73 in the file, 72 in the digsite
    graph; melee 45 -> 44): a looping animation gets frame 0 appended, a one-shot its last frame
    repeated (Halo 1's rule, h1_fp_retarget);
  * the extension is the type: .jmm base (no movement), .jmo overlay, .jmr replacement; the file
    name is the animation name with ':' -> ' ' and '_' -> '-' (`first-person reload-empty`).

OVERLAYS (moving, overlays, pitch_and_turn): Halo 3 stores an overlay's DELTAS in its animated
tracks only (h1_fp_retarget.overlay_frames). Halo 2's .jmo is absolute frames whose difference to
the FIRST (reference) frame is the overlay. So the reference = a base pose (the idle's frame 0)
and each frame = that pose with the delta applied to the animated tracks (rotation q_ref*q_delta,
translation t_ref + t_delta, both in the parent's frame), composed into model space. An
OBSERVATION until seen in game: whether Halo 2 composes the delta in the same order.

Section `fp_anims` of ports_h2/<key>.py:
    species     {species: {'graph': H3EK graph tag, 'arms_rm': H3EK arms render model (the
                 binds of nodes an animation leaves out), 'arms': H2 arms JMS (copied into
                 <source>\arms\render), 'source': kit-relative folder the graph is built in}}
    weapon_rm   the H3EK FP weapon render model (its nodes' binds)
    weapon_dir  kit-relative folder holding render\<fp>.jms (the FP weapon model, step 1)
    anims       [Halo 3 animation names] (default: every one the graph has but `skip`)
    skip        [Halo 3 animation names left out]
    looping     [Halo 3 names whose end wraps to frame 0]
    rename      {Halo 3 name: Halo 2 name}
    drop_ik     [species] -- after the import, the graph's single-wield (class `any`) IK entries
                removed (h2_graph_teach.drop_ik: a seed's two-handed left-hand grip; the Spiker)
    rest_left_arm  {'species', 'pose': (animation, frame), 'blend': {animation: frames}} -- the
                left arm held out of view in single-wield animations (rest_left_arm; the Spiker)
    root_identity  the weapon root node whose bind h2_port_geometry `fp_root_identity` made
                identity -- its frames re-expressed (reroot; the Spike Rifle's dual left gun)

    species.seed  a Bungie Halo 2 graph the port's is seeded from (tool_import: its blend screen,
                  sound references and same-name animations' events survive the import)

    python h2_port_fp_anims.py <key> [--species masterchief] [--write] [--import [--reseed]]
                               [--only NAME]
"""
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h1_fp_retarget  # noqa: E402  (export_xml)
import h3_fp_pose  # noqa: E402
import ports_h2  # noqa: E402

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
H3EK = h1_fp_retarget.H3EK
UNITS = 100.0
ARM_NODES = None          # every H3 node that is not a weapon node and not camera_control


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def qrot(q, v):
    w, x, y, z = q
    p = qmul(qmul(q, (0.0, v[0], v[1], v[2])), (w, -x, -y, -z))
    return p[1:]


def qnorm(q):
    s = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / s for c in q)


def compose(nodes, local):
    """[(q, t wu)] model space from parent-relative locals ((w,x,y,z), t)."""
    out = [None] * len(nodes)
    for i, (_n, p) in enumerate(nodes):
        q, t = local[i]
        if p < 0:
            out[i] = (qnorm(q), tuple(t))
        else:
            pq, pt = out[p]
            d = qrot(pq, t)
            out[i] = (qnorm(qmul(pq, q)), (pt[0] + d[0], pt[1] + d[1], pt[2] + d[2]))
    return out


def jma_name(n, weapon_nodes):
    if n in weapon_nodes:
        return 'frame_' + n
    return 'b_' + n


def file_name(h3name, rename):
    name = rename.get(h3name, h3name)
    return name.replace('_', '-').replace(':', ' ')


DEFAULTS = {}      # {node: ((w,x,y,z), t wu)} the render models' binds (build() fills it)


def locals_of(nodes, pose):
    """Halo 3 leaves a node OUT of an animation when it sits at its bind pose (a track is
    None): it comes from the render models' default transform -- the arms' fp.render_model
    and the weapon's FP render model (h1_fp_retarget.retarget_frame's rule)."""
    out = []
    for (n, _p), (r, t, _s) in zip(nodes, pose):
        dq, dt = DEFAULTS.get(n, ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        out.append((r if r is not None else dq, tuple(t) if t is not None else dt))
    return out


def base_frames(nodes, frames, looping):
    out = [compose(nodes, locals_of(nodes, p)) for p in frames]
    return out + [out[0] if looping else out[-1]]


def overlay_frames(nodes, frames, animated, ref_pose):
    """The reference (a base pose), then each frame = the reference with the overlay's animated
    deltas applied in the parent's frame (module docstring)."""
    ref = locals_of(nodes, ref_pose)
    out = [compose(nodes, ref)]
    for pose in frames:
        loc = list(ref)
        for i, (r, t, _s) in enumerate(pose):
            q0, t0 = ref[i]
            q, tt = q0, t0
            if i in animated.get('rot', ()) and r is not None:
                q = qnorm(qmul(q0, r))
            if i in animated.get('trans', ()) and t is not None:
                tt = (t0[0] + t[0], t0[1] + t[1], t0[2] + t[2])
            loc[i] = (q, tt)
        out.append(compose(nodes, loc))
    return out


def reroot(nodes, frames, name):
    """`root_identity` (the Spike Rifle, boot 1): the weapon root's bind is identity in the JMS
    (h2_port_geometry fp_root_identity), so its absolute frames become G(t) x G_bind^-1 x
    G_identity = (q(t) * conj(q_bind), t(t)) -- the mesh lands exactly where it did."""
    i = [n for n, _p in nodes].index(name)
    qb = DEFAULTS[name][0]
    inv = (qb[0], -qb[1], -qb[2], -qb[3])
    out = []
    for fr in frames:
        fr = list(fr)
        q, t = fr[i]
        fr[i] = (qnorm(qmul(q, inv)), t)
        out.append(fr)
    return out


def write_jma(path, nodes, names, frames):
    lines = ['16394', '0', str(len(frames)), '30.0000000000', '1', 'unnamedActor', str(len(nodes))]
    for (n, p), nm in zip(nodes, names):
        lines += [nm, str(p)]
    f = lambda v: '%.10f' % v  # noqa: E731
    for fr in frames:
        for q, t in fr:
            w, x, y, z = q
            lines.append('\t'.join(f(c * UNITS) for c in t))
            lines.append('\t'.join(f(c) for c in (x, y, z, w)))
            lines.append(f(1.0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='latin-1', newline='') as fh:
        fh.write('\r\n'.join(lines) + '\r\n')


def slerp(a, b, w):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        return qnorm(tuple(x + (y - x) * w for x, y in zip(a, b)))
    th = math.acos(d)
    s = math.sin(th)
    return tuple((math.sin((1 - w) * th) * x + math.sin(w * th) * y) / s for x, y in zip(a, b))


def rest_left_arm(nodes, anims, rest):
    """`rest_left_arm` {'species': [...], 'pose': (animation, frame), 'blend': {animation: frames}}
    (the Spike Rifle, boot 4 on 05b): Halo 3's CHIEF single-wield Spiker animations park the left hand
    UNDER the gun (Halo 3 does not show it there); Halo 2 draws it, poking into the weapon. The
    Arbiter's own animator keeps that hand low, out of view, except for the reload and the grenade
    throw -- so the Chief gets the same: every left-arm node ('l_*') of every SINGLE-wield animation
    holds the `pose` frame's local transforms; the `blend` animations keep Halo 3's left-arm motion,
    eased in from the pose and back over that many frames; overlays stop moving the left arm. Dual
    animations ('first_person:dual:') are untouched."""
    left = [i for i, (n, _p) in enumerate(nodes) if n.startswith('l_')]
    pa, pf = rest['pose']
    pose = locals_of(nodes, anims[pa][1][pf])
    for name, (typ, frames, animated) in anims.items():
        if name.startswith('first_person:dual:'):
            continue
        if typ == 'overlay':
            for k in ('rot', 'trans'):
                if k in animated:
                    animated[k] = set(animated[k]) - set(left)
            continue
        n = rest.get('blend', {}).get(name)
        new = []
        for f, fr in enumerate(frames):
            fr = list(fr)
            w = 0.0
            if n:
                w = min(1.0, f / float(n), (len(frames) - 1 - f) / float(n))
                w = w * w * (3 - 2 * w)                     # smoothstep
            for i in left:
                q, t = pose[i]
                r, tt, s = fr[i]
                if w > 0 and r is not None:
                    q = slerp(q, r, w)
                if w > 0 and tt is not None:
                    t = tuple(a + (b - a) * w for a, b in zip(t, tt))
                fr[i] = (q, t, s)
            new.append(fr)
        frames[:] = new


FE_COUNT, SE_COUNT = 0x4C, 0x58     # a tool-imported graph's 124-byte animation element


def source_events(cfg, species):
    """`source_events` {'sounds': {Halo 3 sound basename: the graph's sound reference basename, or
    None = dropped}} (the Spike Rifle, 2026-10-22: the frame and sound events were the SMG seed's --
    sounds a frame late, the dual reloads silent, no melee / reload / throw keyframes): every
    animation's FRAME and SOUND events rewritten from the Halo 3 graph's own (types by name:
    primary / secondary keyframe, allow interruption -- Halo 2's enum carries Halo 3's names).

    LAYOUT (measured on both species' graphs): the element (124 bytes, tool's import) holds the
    frame events block at +0x4C and the sound events block at +0x58 (count, 2 pointers); in the data
    region each animation's pooled name is followed by its blob and ONE 'sdpa' struct descriptor
    (16 bytes), and then its event chunks in field order: frame events ('dfbt', v0, n, 4: type,
    frame) and sound events (n, 8: sound reference, frame, marker string id -- empty: nothing pooled).
    Each animation's two chunks are replaced (last first, so earlier offsets hold) and its counts set.
    Proved: tool's export reads every row outside the event blocks unchanged and the events as
    written; else the graph is restored."""
    import re
    import h2_tagfield as tf
    sp = cfg['species'][species]
    path = graph_path(sp)
    x = tf.export(path)
    refs = [r.rsplit('\\', 1)[-1] for r in re.findall(
        r'<tag_reference name="sound" type="snd!">([^<]*)<',
        x[x.find('<block name="sound references"'):x.find('<block name="animations"')])]
    names = re.findall(r'<element index="\d+">\s*<field name="name" type="string id">([^<]*)<',
                       x[x.find('<block name="animations"'):])
    if cfg.get('kind') == 'h4':
        want = h4_events(cfg, refs)
    else:
        want = h3_events(cfg, sp, refs)
    write_events(path, x, names, want)


def h4_events(cfg, refs):
    """kind 'h4' `source_events` {'cues': {Halo 2 animation: [(sound, frame)]}} (the SAW rework,
    2026-10-23): FRAME events from the Halo 4 graph's .frame_event_list (primary / secondary keyframe,
    allow interruption; a type listed twice -- Halo 4's melee_strike_1 has primary keyframes at 4 and
    5 -- keeps its first frame), onto every Halo 2 animation `map` makes of it. SOUND events are the
    config's: the SAW's foley mixes fold Halo 4's several cues of an animation into ONE sound at
    frame 0 (saw_port_sounds). A cue names the graph's sound reference by basename, either the port's
    own or the seed's that `sounds` `graph_sounds` repoints to it (the events may be written before
    the sounds step)."""
    import re
    import h4_tags
    fel = os.path.splitext(cfg['retarget']['graph'])[0] + '.frame_event_list'
    s = open(h4_tags.export_xml(fel), encoding='utf-8', errors='replace').read()
    types = {'primary keyframe': 0, 'secondary keyframe': 1, 'left foot': 2, 'right foot': 3,
             'allow interruption': 4}
    events = {}
    parts = re.split(r'<field name="animation name" value="(first_person:[^"]*)" type="string id"/>'
                     r'\s*<field name="animation frame count"', s)
    for nm, body in zip(parts[1::2], parts[2::2]):
        ae = body[:body.find('<block name="sound events"')]
        first = {}
        for f, t in re.findall(r'name="frame" value="(-?\d+)".*?name="type" value="([^"]*)"', ae, re.S):
            if t in types:
                first[types[t]] = min(int(f), first.get(types[t], int(f)))
        events[nm] = sorted(((t, f) for t, f in first.items()), key=lambda e: (e[1], e[0]))
    alias = {}
    for donor, own in ports_h2.get(cfg['_key'], 'sounds').get('graph_sounds', ()):
        alias.setdefault(own, []).append(donor)
    want = {}
    for row in cfg['map']:
        h4name, h2name = row[:2]
        se = []
        for snd, f in cfg.get('source_events', {}).get('cues', {}).get(h2name, ()):
            hit = [n for n in [snd] + alias.get(snd, []) if n in refs]
            if not hit:
                raise SystemExit('%s: no sound reference %s (graph: %s)' % (h2name, snd, refs))
            se.append((refs.index(hit[0]), f))
        want[h2name] = (events.get(h4name, []), se)
    return want


def h3_events(cfg, sp, refs):
    import re
    # Halo 3's events
    h3x = open(h1_fp_retarget.export_xml(sp['graph']), encoding='utf-8', errors='replace').read()
    h3refs = [r.rsplit('\\', 1)[-1] for r in re.findall(
        r'name="sound" value="([^"]*),snd!"',
        h3x[h3x.find('<block name="sound references"'):h3x.find('<block name="effect references"')])]
    rename = cfg.get('rename', {})
    types = {'primary_keyframe': 0, 'secondary_keyframe': 1, 'left_foot': 2, 'right_foot': 3,
             'allow_interruption': 4}
    want = {}
    for part in re.split(r'<element index="\d+" name="first_person', h3x[h3x.find('<block name="animations"'):])[1:]:
        name = 'first_person' + part[:part.find('"')]
        name = rename.get(name, name)
        fe = [(types[t], int(f)) for t, f in re.findall(
            r'name="type" value="([^"]*)" type="short enum"/>\s*<field name="frame" value="(-?\d+)"', part)]
        se = []
        for i, f in re.findall(r'name="sound" value=",(-?\d+)" type="short block index"/>\s*'
                               r'<field name="frame" value="(-?\d+)"', part):
            target = cfg['source_events']['sounds'].get(h3refs[int(i)]) if int(i) >= 0 else None
            if target is not None:
                se.append((refs.index(target), int(f)))
        want[name] = (fe, se)
    return want


def write_events(path, x, names, want):
    import re
    import struct
    import h2_tagfield as tf
    import h2_anim
    d = bytearray(open(path, 'rb').read())
    original = bytes(d)
    ch, n, es = h2_anim.animations_chunk(bytes(d))
    if es != 124:
        raise SystemExit('%s: %d-byte animation elements; the event offsets are mapped for 124'
                         % (os.path.basename(path), es))
    base = ch + 16
    pos, at = [], base + n * es
    for nm in names:
        i = bytes(d).find(nm.encode('latin-1'), at)
        pos.append(i)
        at = i + len(nm)
    rows_before = tf.read_all(x)
    changed = []
    for k in reversed(range(n)):
        nm = names[k]
        if nm not in want:
            continue
        e = base + k * es
        end = pos[k + 1] if k + 1 < n else len(d)
        s = bytes(d).find(b'sdpa', pos[k], end)
        at = s + 16
        old_end = at
        fe_n, se_n = struct.unpack_from('<I', d, e + FE_COUNT)[0], struct.unpack_from('<I', d, e + SE_COUNT)[0]
        for cnt, size in ((fe_n, 4), (se_n, 8)):
            if cnt:
                if d[old_end:old_end + 4] != b'dfbt' or struct.unpack_from('<II', d, old_end + 8) != (cnt, size):
                    raise SystemExit('%s: unexpected event chunk at 0x%X' % (nm, old_end))
                body = old_end + 16 + cnt * size
                if size == 8:       # marker name strings pooled after the elements
                    body += sum(d[old_end + 16 + j * 8 + 7] for j in range(cnt))
                old_end = body
        fe, se = want[nm]
        new = b''
        if fe:
            new += b'dfbt' + struct.pack('<III', 0, len(fe), 4) + b''.join(struct.pack('<hh', t, f) for t, f in fe)
        if se:
            new += b'dfbt' + struct.pack('<III', 0, len(se), 8) + b''.join(struct.pack('<hhI', r, f, 0) for r, f in se)
        if d[at:old_end] == new and (fe_n, se_n) == (len(fe), len(se)):
            continue
        d[at:old_end] = new
        struct.pack_into('<I', d, e + FE_COUNT, len(fe))
        struct.pack_into('<I', d, e + SE_COUNT, len(se))
        changed.append(nm)
    if not changed:
        print('   %s: events already the source\'s' % os.path.basename(path))
        return
    open(path, 'wb').write(bytes(d))
    after = tf.export(path)
    ok = bool(after)
    if ok:
        strip = lambda xx: re.sub(r'<block name="(frame|sound) events">.*?</block>', '', xx, flags=re.S)
        ok = tf.read_all(strip(after)) == tf.read_all(strip(x))
        for nm in changed:
            part = after[after.find('>%s<' % nm) + 1:]
            nxt = part.find('<field name="name" type="string id">')
            part = part[:nxt if nxt >= 0 else len(part)]
            got_fe = [(int(t.split(',')[0]), int(f)) for t, f in re.findall(
                r'<field name="type" type="[^"]*">([^<]*)</field>\s*<field name="frame" type="short integer">(-?\d+)<', part)]
            got_se = [(int(i), int(f)) for i, f in re.findall(
                r'type="sound" index="(-?\d+)">[^<]*</block_index>\s*<field name="frame" type="short integer">(-?\d+)<', part)]
            if (got_fe, got_se) != want[nm]:
                ok = False
                print('   %s: tool reads %s, wanted %s' % (nm, (got_fe, got_se), want[nm]))
    if not ok:
        open(path, 'wb').write(original)
        raise SystemExit('%s: the events did not read back as written -- restored' % os.path.basename(path))
    print('   %s: the source\'s events in %d animations (%+d bytes); every other row unchanged'
          % (os.path.basename(path), len(changed), len(d) - len(original)))


def build(key, species, only=None, write=True):
    cfg = ports_h2.get(key, 'fp_anims')
    sp = cfg['species'][species]
    xml = h1_fp_retarget.export_xml(sp['graph'])
    nodes, anims = h3_fp_pose.load(os.path.join(H3EK, 'tags', sp['graph']), xml)
    DEFAULTS.clear()
    DEFAULTS.update(h1_fp_retarget.rm_defaults(sp['arms_rm']))
    DEFAULTS.update(h1_fp_retarget.rm_defaults(cfg['weapon_rm']))
    weapon_nodes = set(cfg['weapon_nodes'])
    names = [jma_name(n, weapon_nodes) for n, _p in nodes]
    src = os.path.join(H2EK, 'data', sp['source'], 'animations')
    if write and not only and os.path.isdir(src):
        shutil.rmtree(src)
    rest = cfg.get('rest_left_arm') or {}
    if species in rest.get('species', ()):
        rest_left_arm(nodes, anims, rest)
    ref_pose = anims[cfg.get('overlay_reference', 'first_person:idle')][1][0]
    rename = cfg.get('rename', {})
    out = []
    for h3name, (typ, frames, animated) in sorted(anims.items()):
        if h3name in cfg.get('skip', ()) or (only and h3name not in only):
            continue
        if typ == 'overlay':
            fr, ext = overlay_frames(nodes, frames, animated, ref_pose), '.jmo'
        elif typ == 'replacement':
            fr, ext = base_frames(nodes, frames, h3name in cfg.get('looping', ())), '.jmr'
        else:
            fr, ext = base_frames(nodes, frames, h3name in cfg.get('looping', ())), '.jmm'
        if cfg.get('root_identity'):
            fr = reroot(nodes, fr, cfg['root_identity'])
        path = os.path.join(src, file_name(h3name, rename) + ext)
        if write:
            write_jma(path, nodes, names, fr)
        out.append((h3name, typ, len(frames), len(fr), os.path.basename(path)))
    return nodes, out


def h1_key(name):
    """A Halo 1 FP node name -> Halo 2's graph name (`frame l wriste` -> l_hand, `frame bone24` ->
    base; weapon nodes `frame gun` -> gun). Checked on the cyborg arms: 37/37 = Bungie's fp_arms."""
    s = name.lower().replace('frame ', '')
    s = s[2:] if s.startswith('b_') else s
    return s.replace(' ', '_').replace('bone24', 'base').replace('wriste', 'hand').replace('middlelow', 'middle_low')


def jms_binds(path):
    """{graph name: (parent name or None, (q (w,x,y,z), t wu) LOCAL)} of a Halo 2 JMS (model-space
    binds, JMS rotation convention) -- the parent's inverse taken out."""
    import h2_jms
    m = h2_jms.read(path)
    names = [h1_key(n.name) for n in m.nodes]
    world = [((n.rot[3], n.rot[0], n.rot[1], n.rot[2]), tuple(c / UNITS for c in n.pos)) for n in m.nodes]
    out = {}
    for i, n in enumerate(m.nodes):
        q, t = world[i]
        if n.parent < 0:
            out[names[i]] = (None, (q, t))
            continue
        pq, pt = world[n.parent]
        pi = (pq[0], -pq[1], -pq[2], -pq[3])
        out[names[i]] = (names[n.parent], (qnorm(qmul(pi, q)),
                                           qrot(pi, (t[0] - pt[0], t[1] - pt[1], t[2] - pt[2]))))
    return out, names


CHIEF_W, ELITE_W, ELITE_AXIS = {}, {}, {}


def bone_axes(binds):
    """{finger node: unit vector along the bone in its OWN frame} -- toward its child's bind (a tip:
    its parent's axis, the segment continuing)."""
    kids = {}
    for nm, (par, _qt) in binds.items():
        if par:
            kids.setdefault(par, []).append(nm)
    out = {}
    for nm in binds:
        if _is_finger(nm) and kids.get(nm):
            t = binds[kids[nm][0]][1][1]
            n = math.sqrt(sum(c * c for c in t)) or 1.0
            out[nm] = tuple(c / n for c in t)
    for nm, (par, (q, _t)) in binds.items():
        if _is_finger(nm) and nm not in out and par in out:
            # the parent's axis expressed in this node's frame
            out[nm] = qrot((q[0], -q[1], -q[2], -q[3]), out[par])
    return out


def _seg_next(nm):
    side, f, seg = nm.split('_')
    nxt = {'low': 'mid', 'mid': 'tip'}.get(seg)
    return '%s_%s_%s' % (side, f, nxt) if nxt else None


def chief_dir(world, nm):
    """The Chief finger segment's model-space direction: this joint -> the next (a tip: its parent's
    joint -> this one, the segment continuing)."""
    nxt = _seg_next(nm)
    if nxt and nxt in world:
        a, b = world[nm][1], world[nxt][1]
    else:
        side, f, _seg = nm.split('_')
        a, b = world['%s_%s_mid' % (side, f)][1], world[nm][1]
    return tuple(y - x for x, y in zip(a, b))


def _rot_between(u, v):
    lu = math.sqrt(sum(x * x for x in u)) or 1.0
    lv = math.sqrt(sum(x * x for x in v)) or 1.0
    u = tuple(x / lu for x in u)
    v = tuple(x / lv for x in v)
    c = sum(x * y for x, y in zip(u, v))
    ax = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return qnorm((1.0 + c,) + ax)


def jms_world(path):
    """{graph name: model-space bind rotation (w,x,y,z)} of a Halo 2 JMS (its nodes are absolute)."""
    import h2_jms
    return {h1_key(n.name): (n.rot[3], n.rot[0], n.rot[1], n.rot[2]) for n in h2_jms.read(path).nodes}


def h1_frames(antr_rel, anim):
    """[(H1 node name, parent index)], [[(q (w,x,y,z) Halo 3 convention, t wu)] LOCAL per frame] of
    one Halo 1 animation, through Reclaimer -- its JMA is the SOURCE form (N + 1 frames: tool drops
    the last, Halo 1's and Halo 2's rule); Halo 1's stored inverse rotation conjugated."""
    import port_env  # noqa: F401
    from reclaimer.hek.defs.antr import antr_def
    from reclaimer.animation.animation_decompilation import extract_animation
    path = os.path.join(os.path.dirname(H2EK), 'HCEEK', 'tags', antr_rel + '.model_animations')
    d = antr_def.build(filepath=path).data.tagdata
    names = [a.name for a in d.animations.STEPTREE]
    jma = extract_animation(names.index(anim), d, write_jma=False)
    nodes = [(n.name, n.parent_index if n.parent_index != i else -1) for i, n in enumerate(jma.nodes)]
    frames = [[((s.rot_w, -s.rot_i, -s.rot_j, -s.rot_k), (s.pos_x / UNITS, s.pos_y / UNITS, s.pos_z / UNITS))
               for s in f] for f in jma.frames]
    return nodes, frames, d.animations.STEPTREE[names.index(anim)].type.enum_name


_H4 = {}


def h4_frames(cfg, anim):
    """kind 'h4' (the SAW rework, 2026-10-23): one HALO 4 FP animation in h1_frames' shape. Halo 4's
    arms are not Halo 2's (H2_PORT_PLAN 0.4), but Halo 1's are Halo 2's masterchief -- so Halo 1's
    proven Halo 4 route does the arms: the Foundry dump (h4_fp_dump.py -> h4_tags.load_graph) and
    h1_fp_retarget's re-solve (_resolve_arms: Halo 4's wrists, Halo 1's bone lengths), its output in
    Halo 1's FP space -- which build_h1 already writes as Halo 2 frames. Section `retarget` = an
    h1_fp_retarget WEAPONS entry (graph, render_model, nodes, drop_nodes[, hand_offset(_anims),
    view_offset(_anims), ...]); no `align`: the FP JMS is the Halo 4 render model in its own space.
    A base animation gets its last frame repeated (tool drops it); an OVERLAY (Halo 1's form: a
    reference + per-frame deltas) becomes absolute frames -- `overlay_reference`'s frame 0 with each
    animated track's delta applied (the kind 'h3' rule)."""
    import h1_fp_retarget as R1
    w = 'h2:' + cfg['retarget']['graph']
    # a species' own `retarget` keys over the shared ones (04a boot 3: the Elite's bigger left hand sank
    # into the drum on the Chief's wrist -- the Dervish's `hand_offset` moves its wrist, the arm re-solved)
    R1.WEAPONS[w] = dict(cfg['retarget'], **cfg.get('_species_retarget', {}))
    if w not in _H4:
        _H4[w] = R1.load(w)
    nodes, anims, defaults, _ev = _H4[w]
    names, parents = R1.h1_skeleton(w, nodes)
    idx = {n: i for i, n in enumerate(names)}
    jn = [(n, idx[p] if p is not None else -1) for n, p in zip(names, parents)]
    typ, frames = R1.retarget(w, anim, nodes, anims, defaults)
    if typ == 'overlay':
        _t, base = R1.retarget(w, cfg.get('overlay_reference', 'first_person:idle'), nodes, anims, defaults)
        ref = base[0]
        animated = anims[anim][2]
        rot = {R1._h1(w, nodes[i][0]) for i in animated['rot']}
        tr = {R1._h1(w, nodes[i][0]) for i in animated['trans']}
        out = [ref]
        for d in frames[1:]:
            # tag convention (conjugated): conj(q_ref * delta) = delta_tag * q_ref_tag
            out.append({n: (qnorm(qmul(d[n][0], q)) if n in rot else q,
                            tuple(a + b for a, b in zip(t, d[n][1])) if n in tr else t)
                        for n, (q, t) in ((n, v[:2]) for n, v in ref.items())})
        frames = out
    else:
        frames = frames + [frames[-1]]
    rows = [[((q[0], -q[1], -q[2], -q[3]), tuple(t)) for q, t in (fr[n][:2] for n in names)]
            for fr in frames]
    return jn, rows, typ


def _source_frames(cfg, name):
    return h4_frames(cfg, name) if cfg.get('kind') == 'h4' else h1_frames(cfg['antr'], name)


def _continuous(rows):
    """Every node's quaternion in the hemisphere of the frame before (kind 'h4': Halo 4's locals come
    out of rotation matrices with w >= 0 -- h1_fp_retarget._continuous, the Storm Rifle's boot 2)."""
    out = [list(rows[0])]
    for fr in rows[1:]:
        out.append([((tuple(-c for c in q) if sum(a * b for a, b in zip(q, p[0])) < 0 else q), t)
                    for (q, t), p in zip(fr, out[-1])])
    return out


def build_h1(key, species, only=None, write=True, cfg_override=None):
    """kind 'h1' (the Flamethrower, S1, 2026-10-21): Halo 1's OWN FP animations as Halo 2 source
    animations. Halo 1's FP arms ARE Halo 2's masterchief and Halo 1's view is the animation origin,
    which is where Bungie's own H2 sources keep `b_camera_control` (identity, digsite fp_battle_rifle)
    -- so each Halo 1 frame composed into model space IS the Halo 2 frame; camera_control is written
    at identity. Nodes in the H2 arms JMS's order, then the weapon nodes, then camera_control.

    DERVISH (`repose`, the user's pick at step 0): the arm chain is the Chief's (shoulders, upper arm,
    forearm and wrist lengths equal), so base / arms / hands take the Chief's model-space frames; each
    Elite FINGER (thumb, index, ring, pinky: no middle) takes the Chief finger's CURL -- its local
    rotation relative to the Chief's bind -- on the Elite's own bind (local = elite bind x (chief bind^-1
    x chief local)), translation the Elite's bind.

    Section `fp_anims` (kind 'h1'): antr (HCEEK FP animation tag), map [(H1 animation, H2 name[,
    {'loop': True} | {'then': H1 animation, 'frames': n} (append frames of another, looped, until n) |
    {'reverse': True, 'frames': n} (sampled backwards: a put_away from the ready)])], weapon_nodes (H2
    names), species {name: {'arms' (H2 arms JMS), 'source', 'seed', 'repose'}}, chief_arms (the
    masterchief JMS: the Chief's bind for the curl)."""
    cfg = dict(cfg_override or ports_h2.get(key, 'fp_anims'), _key=key)
    sp = cfg['species'][species]
    elite, order = jms_binds(sp['arms'])
    chief, _ = jms_binds(cfg['chief_arms'])
    cfg = dict(cfg, _species_retarget=sp.get('retarget', {}))
    CHIEF_W.clear()
    ELITE_W.clear()
    ELITE_AXIS.clear()
    if sp.get('repose') in ('direction', 'points'):
        ELITE_AXIS.update(bone_axes(elite))
    if sp.get('repose') == 'world':
        CHIEF_W.update(jms_world(cfg['chief_arms']))
        ELITE_W.update(jms_world(sp['arms']))
    weapon_nodes = list(cfg['weapon_nodes'])
    names_h2 = order + weapon_nodes + ['camera_control']
    parents = {}
    src = os.path.join(H2EK, 'data', sp['source'], 'animations')
    if write and not only and os.path.isdir(src):
        shutil.rmtree(src)
    out = []
    for row in cfg['map']:
        h1name, h2name = row[:2]
        opt = row[2] if len(row) > 2 else {}
        if only and h2name not in only:
            continue
        nodes, frames, typ = _source_frames(cfg, h1name)
        if opt.get('then'):
            _n2, more, _t = _source_frames(cfg, opt['then'])
            body, k = list(frames[:-1]), 0
            while len(body) < opt['frames']:
                body.append(more[k % (len(more) - 1)])
                k += 1
            frames = body + [body[-1]]
        if opt.get('reverse'):
            n = opt['frames']
            idx = [round((len(frames) - 1) * (1 - i / float(n - 1))) for i in range(n)]
            frames = [frames[i] for i in idx] + [frames[idx[-1]]]
        if opt.get('loop'):
            frames = frames[:-1] + [frames[0]]
        keys = [h1_key(n) for n, _p in nodes]
        h1_nodes = [(n, p) for n, p in nodes]
        rows = []
        for f in frames:
            world = dict(zip(keys, compose(h1_nodes, f)))
            fr = []
            for nm in names_h2:
                if nm == 'camera_control':
                    fr.append(((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
                elif nm in world and (species == 'masterchief' or not sp.get('repose')
                                      or not _is_finger(nm)):
                    fr.append(world[nm])
                else:
                    # an Elite finger: the Chief's curl on the Elite's bind, under its parent's frame
                    par, (eq, et) = elite[nm]
                    cpar, (cq, _ct) = chief[nm]
                    pq, pt = dict(zip(names_h2, fr))[par]
                    d = qrot(pq, et)
                    if sp.get('repose') == 'points' and _seg_next(nm) and _seg_next(nm) in world:
                        # `repose` 'points' (04a boot 3, user: 'the fingers phase into the weapon'): the
                        # Elite's fingers are LONGER than the Chief's, so the Chief's directions push the
                        # tips through the grip -- each segment aims at the Chief's NEXT JOINT instead
                        # (a longer finger reaching the same points curls tighter, along the Chief's
                        # path round the grip); a tip keeps the direction rule
                        q0 = qnorm(qmul(pq, eq))
                        here = (pt[0] + d[0], pt[1] + d[1], pt[2] + d[2])
                        aim = tuple(b - a for a, b in zip(here, world[_seg_next(nm)][1]))
                        fr.append((qnorm(qmul(_rot_between(qrot(q0, ELITE_AXIS[nm]), aim), q0)), here))
                        continue
                    if sp.get('repose') in ('direction', 'points'):
                        # `repose` 'direction' (the SAW rework, 04a boot 2: the idle's LEFT fingers stood
                        # up off the fore-grip with 'world'): the Elite segment starts RIGID on its solved
                        # parent (its own bind) and turns by the smallest rotation that points it along
                        # the Chief's segment in model space (this joint -> the next; a tip along the
                        # Chief tip's direction from its parent) -- h1_fp_retarget's fingers by direction
                        q0 = qnorm(qmul(pq, eq))
                        fr.append((qnorm(qmul(_rot_between(qrot(q0, ELITE_AXIS[nm]), chief_dir(world, nm)), q0)),
                                   (pt[0] + d[0], pt[1] + d[1], pt[2] + d[2])))
                        continue
                    if sp.get('repose') == 'world':
                        # `repose` 'world' (the SAW rework, boot on 04a: 'strangely large fingers' --
                        # Halo 4's re-solved finger turns are far from the bind, and the two hands'
                        # bind frames differ, so a LOCAL curl lands elsewhere on the Elite): the
                        # Chief finger's turn from its own bind IN MODEL SPACE, on the Elite's bind
                        cw, cb, eb = world[nm][0], CHIEF_W[nm], ELITE_W[nm]
                        fr.append((qnorm(qmul(qmul(cw, (cb[0], -cb[1], -cb[2], -cb[3])), eb)),
                                   (pt[0] + d[0], pt[1] + d[1], pt[2] + d[2])))
                        continue
                    li = dict(zip(keys, f))[nm][0]
                    delta = qmul((cq[0], -cq[1], -cq[2], -cq[3]), li)
                    q = qnorm(qmul(eq, delta))
                    fr.append((qnorm(qmul(pq, q)), (pt[0] + d[0], pt[1] + d[1], pt[2] + d[2])))
            rows.append(fr)
        _LAST_ROWS[h2name] = rows
        hold = sp.get('hold_fingers')
        if hold and h2name in hold['anims']:
            rows = hold_fingers(rows, names_h2, elite, hold, cfg, species)
        if cfg.get('kind') == 'h4':
            rows = _continuous(rows)
        for nm in names_h2:
            if nm == 'camera_control':
                parents[nm] = 0
            elif nm in elite and species != 'masterchief':
                parents[nm] = names_h2.index(elite[nm][0]) if elite[nm][0] else -1
            else:
                par = dict((h1_key(n), (h1_key(nodes[p][0]) if p >= 0 else None)) for n, p in nodes).get(nm)
                parents[nm] = names_h2.index(par) if par else -1
        ext = '.jmo' if typ == 'overlay' else '.jmm'
        path = os.path.join(src, file_name(h2name, {}) + ext)
        if write:
            jnodes = [(nm, parents[nm]) for nm in names_h2]
            write_jma(path, jnodes, [jma_name(nm, set(weapon_nodes)) for nm in names_h2], rows)
        out.append((h1name + ' -> ' + h2name, typ, len(frames) - 1, len(rows), os.path.basename(path)))
    return [(n, parents.get(n, -1)) for n in names_h2], out


def hold_fingers(rows, names, binds, hold, cfg, species):
    """`hold_fingers` {'side': 'l', 'anims': [...], 'pose': (animation, frame)} (the SAW rework's Dervish,
    04a boot 5, user: 'keep the idle finger grip' -- the Elite's four-digit hand cannot mirror the
    Chief's five-finger flex in the fidgets): every finger node of that side keeps its LOCAL transform
    (relative to its parent) from the pose frame; the hand and arm still move as the animation does."""
    key = (species, hold['pose'])
    if key not in _HELD:
        anim, f = hold['pose']
        sub = dict(cfg, map=[r for r in cfg['map'] if r[1] == anim][:1])
        _n, _out = build_h1(cfg['_key'], species, write=False, cfg_override=sub)
        _HELD[key] = _LAST_ROWS[anim][f]
    ref = dict(zip(names, _HELD[key]))
    out = []
    for fr in rows:
        cur = dict(zip(names, fr))
        for nm in names:
            if not (_is_finger(nm) and nm.startswith(hold['side'] + '_')):
                continue
            par = binds[nm][0]
            pq, pt = ref[par]
            q, t = ref[nm]
            inv = (pq[0], -pq[1], -pq[2], -pq[3])
            lq = qmul(inv, q)
            lt = qrot(inv, tuple(a - b for a, b in zip(t, pt)))
            cq, ct = cur[par]
            d = qrot(cq, lt)
            cur[nm] = (qnorm(qmul(cq, lq)), tuple(a + b for a, b in zip(ct, d)))
        out.append([cur[n] for n in names])
    return out


_HELD, _LAST_ROWS = {}, {}


def _is_finger(nm):
    return any(f in nm for f in ('thumb', 'index', 'middle', 'ring', 'pinky'))


def stage_arms(cfg, species):
    """The character directory tool wants: <source>\\arms\\render\\<arms>.jms (a copy of Bungie's
    own arms JMS, `tool extract-render-data` output)."""
    sp = cfg['species'][species]
    d = os.path.join(H2EK, 'data', sp['source'], 'arms', 'render')
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, os.path.basename(sp['arms']))
    shutil.copy(sp['arms'], dest)
    return os.path.join(sp['source'], 'arms')


def graph_path(sp):
    return os.path.join(H2EK, 'tags', sp['source'], os.path.basename(sp['source'])
                        + '.model_animation_graph')


def tool_import(cfg, species, reseed=False):
    """`tool fp-model-animations` into a graph SEEDED from a Bungie graph (`seed`): an import over
    an existing tag 'restores old animation graph data' -- its BLEND SCREEN (pitch_and_turn's
    yaw / pitch per frame; a from-scratch graph has none), its sound references and the frame /
    sound events of every animation whose NAME matches -- and drops the seed's animations the
    source does not have. A from-scratch tag also reported 'post-processing graph failed'
    (the AR, 2026-10-20; a second import over it was clean), so a new tag is imported twice."""
    sp = cfg['species'][species]
    arms = stage_arms(cfg, species)
    dest = graph_path(sp)
    fresh = not os.path.exists(dest)
    if sp.get('seed') and (reseed or fresh):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy(os.path.join(H2EK, 'tags', sp['seed'] + '.model_animation_graph'), dest)
        print('   seeded %s from %s' % (os.path.basename(dest), sp['seed']))
        fresh = False
    args = [os.path.join(H2EK, 'tool.exe'), 'fp-model-animations', sp['source'], arms,
            cfg['weapon_dir']] + list(cfg.get('tool_flags', ()))
    for attempt in range(2 if fresh else 1):
        print('   tool %s' % ' '.join(args[1:]))
        p = subprocess.run(args, cwd=H2EK, capture_output=True, text=True, errors='replace',
                           timeout=900)
        text = ((p.stdout or '') + (p.stderr or '')).replace('\r', '\n')
        for line in text.split('\n'):
            line = line.strip()
            if line and '%' not in line and not line.startswith('###'):
                print('   | ' + line)
    return text


def clear_verify(cfg, species):
    """`clear_verify` (the Flamethrower, boot 2: 'overheat animation plays, but no sound'): tool's
    import flags every animation whose length changed 'verify sound events' (production flags 2) --
    the seed's events stay but await a designer's check; Bungie's shipped graphs carry 0. Cleared."""
    import h2_tagfield as tf
    g = graph_path(cfg['species'][species])
    rows = tf.read_all(tf.export(g))
    for r in rows:
        if r[0] == 'animations' and r[2] == 'production flags' and tf._numbers(r[4]) and \
                int(tf._numbers(r[4])[0]) & 2:
            tf.set_field(g, 'production flags', int(tf._numbers(r[4])[0]) & ~2, 'animations', int(r[1]))


def set_weights(cfg, species):
    """`weights` {animation: weight} (the SAW rework, 04a boot 5, user: 'only one of the fidgets ever
    played'): the import keeps a SEED animation's weight for the same name and gives a new name the
    default 0.0001 -- the SMG seed has posing var0 / var1, so Halo 4's var2 was all but never picked
    (Halo 2 chooses a variant by weight); the AR's Dervish fidget read 0. Written by the element
    layout (a weight reading 0 cannot be probed): the real at +28 of the tool's 124-byte animation
    element (measured on the AR's Chief graph); every write proved by tool's export (that one row
    moved, else the graph is restored)."""
    import re
    import struct
    import h2_anim
    import h2_tagfield as tf
    g = graph_path(cfg['species'][species])
    x = tf.export(g)
    names = re.findall(r'<element index="\d+">\s*<field name="name" type="string id">([^<]*)<',
                       x.split('<block name="animations"', 1)[1])
    d = bytearray(open(g, 'rb').read())
    original = bytes(d)
    ch, _n, es = h2_anim.animations_chunk(bytes(d))
    if es != 124:
        raise SystemExit('%s: %d-byte animation elements; the weight offset is mapped for 124' % (g, es))
    want = {names.index(nm): float(w) for nm, w in cfg['weights'].items() if nm in names}
    for k, w in want.items():
        struct.pack_into('<f', d, ch + 16 + k * es + 28, w)
    if bytes(d) == original:
        return
    before = tf.read_all(x)
    open(g, 'wb').write(bytes(d))
    after = tf.read_all(tf.export(g))
    moved = [(a, b) for a, b in zip(before, after) if a != b]
    ok = len(before) == len(after) and all(
        b[0] == 'animations' and b[2] == 'weight' and b[1] in want and
        abs(float(b[4]) - want[b[1]]) < 1e-5 for _a, b in moved)
    if not ok:
        open(g, 'wb').write(original)
        raise SystemExit('%s: the weights did not read back alone -- restored' % os.path.basename(g))
    for _a, b in moved:
        print('   %s: %s weight -> %s' % (os.path.basename(g), names[b[1]], b[4]))


def clear_sound_ref_flags(cfg, species):
    """`clear_sound_ref_flags` (the SAW rework, boot 2 on 03a: 'the later reload parts, one melee and
    the fidget are mute'): each element of a graph's SOUND REFERENCES carries flags -- 'first-person
    only', 'left arm only', 'right arm only' -- and an SMG seed's dual-wield slots are left / right arm
    only: a single-wield weapon never plays them. Every flag cleared (Bungie's single-wield slots: 0)."""
    import h2_tagfield as tf
    g = graph_path(cfg['species'][species])
    for r in tf.read_all(tf.export(g)):
        if r[0] == 'sound references' and r[2] == 'flags' and tf._numbers(r[4]) and int(tf._numbers(r[4])[0]):
            tf.set_field(g, 'flags', 0, 'sound references', int(r[1]))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    key = argv[0]
    cfg = ports_h2.get(key, 'fp_anims')
    want = [argv[argv.index('--species') + 1]] if '--species' in argv else list(cfg['species'])
    only = [argv[argv.index('--only') + 1]] if '--only' in argv else None
    for species in want:
        nodes, rows = (build_h1 if cfg.get('kind') in ('h1', 'h4') else build)(key, species, only,
                                                                      write='--write' in argv)
        print('%s: %d nodes, %d animations%s' % (species, len(nodes), len(rows),
                                                  ' written' if '--write' in argv else ''))
        for h3name, typ, n, m, fn in rows:
            print('   %-34s %-11s %3d frames -> %3d in %s' % (h3name, typ, n, m, fn))
        if '--import' in argv:
            tool_import(cfg, species, reseed='--reseed' in argv)
            if cfg.get('clear_verify'):
                clear_verify(cfg, species)
            if cfg.get('source_events'):
                source_events(dict(cfg, _key=key), species)
            if cfg.get('clear_sound_ref_flags'):
                clear_sound_ref_flags(cfg, species)
            if cfg.get('weights'):
                set_weights(cfg, species)
            if species in cfg.get('drop_ik', ()):
                # the seed's single-wield IK (Bungie's SMG: the Chief's left hand gripping the
                # weapon's left_hand marker) dropped -- the Spiker is one-handed (boot 5)
                import h2_graph_teach
                h2_graph_teach.drop_ik(graph_path(cfg['species'][species]), write=True)


if __name__ == '__main__':
    main()
