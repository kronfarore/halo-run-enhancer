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


def build_h1(key, species, only=None, write=True):
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
    cfg = ports_h2.get(key, 'fp_anims')
    sp = cfg['species'][species]
    elite, order = jms_binds(sp['arms'])
    chief, _ = jms_binds(cfg['chief_arms'])
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
        nodes, frames, typ = h1_frames(cfg['antr'], h1name)
        if opt.get('then'):
            _n2, more, _t = h1_frames(cfg['antr'], opt['then'])
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
                    li = dict(zip(keys, f))[nm][0]
                    delta = qmul((cq[0], -cq[1], -cq[2], -cq[3]), li)
                    q = qnorm(qmul(eq, delta))
                    pq, pt = dict(zip(names_h2, fr))[par]
                    d = qrot(pq, et)
                    fr.append((qnorm(qmul(pq, q)), (pt[0] + d[0], pt[1] + d[1], pt[2] + d[2])))
            rows.append(fr)
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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    key = argv[0]
    cfg = ports_h2.get(key, 'fp_anims')
    want = [argv[argv.index('--species') + 1]] if '--species' in argv else list(cfg['species'])
    only = [argv[argv.index('--only') + 1]] if '--only' in argv else None
    for species in want:
        nodes, rows = (build_h1 if cfg.get('kind') == 'h1' else build)(key, species, only,
                                                                      write='--write' in argv)
        print('%s: %d nodes, %d animations%s' % (species, len(nodes), len(rows),
                                                  ' written' if '--write' in argv else ''))
        for h3name, typ, n, m, fn in rows:
            print('   %-34s %-11s %3d frames -> %3d in %s' % (h3name, typ, n, m, fn))
        if '--import' in argv:
            tool_import(cfg, species, reseed='--reseed' in argv)


if __name__ == '__main__':
    main()
