r"""HALO 4 tags (H4EK) read in the SHAPES the Halo 3 readers return -- the `h4:` source of the Halo 1
port pipeline, beside `reach:` (reach_tags.py). Written for the Storm Rifle, the wave-C pilot
(2026-10-13).

A port config names a Halo 4 tag with the prefix `h4:` (`h4:objects\weapons\rifle\
storm_assault_carbine\storm_assault_carbine.render_model`); a path without a prefix is Halo 3's.

H4EK's `tool export-tag-to-xml` (ABSOLUTE paths, cwd = the kit) writes HALO 3-SHAPED XML
(`<block name=..>` wrappers, `path,group` references), so the render-model reader (h4_rm, which
h3_rm_to_jms already uses for Halo 3), rm_defaults, frame_events and h3_sprite_box read it as is.
The export cache is out\h4_export (shared with h3_weapon_values --kit h4).

ANIMATIONS ARE COMPRESSED-ONLY (unlike Reach's): a member's data sizes hold one codec stream
(`animated_node_flags`) plus the node masks; no default data, no float copy. They are decoded by
Foundry in Blender (h4_fp_dump.py: the graph on the arms + its weapon bones, every bone's
armature-space matrix per frame) and turned into Halo locals here. CALIBRATED on
storm_fp_solo's bind (2026-10-13): Blender's armature space = Halo model space turned -90 deg
about z and x3.048 (feet per world unit x 10 / ...: measured, every bone), and Foundry's
per-bone axis convention after that is the IDENTITY (all 80 arm bones within 2e-6) -- so
halo = G^T * blender, translations / 3.048. Foundry samples frame 0..N (N + 1 frames, the last
closing the loop): the first N are kept (Halo 3's count).

THE ARMS ARE NOT HALO 1's (80 bones; shoulders +-7.05 vs +-9.40 cm, upper arm 9.15 vs 10.25,
forearm 11.67 vs 10.89; bind arms out to the side). Bones run along local -y (left) / +y
(right) where Halo 1's run along +x: ARM_AXES maps a Halo 4 bone's rotation into Halo 1's local
axes (measured from the finger layout: index up / thumb inward), and h1_fp_retarget RE-SOLVES
the arms on Halo 1's bone lengths (two-bone IK to Halo 4's wrists, the elbows in Halo 4's arm
plane) instead of copying them.

    python h4_tags.py --list objects\characters\storm_fp\weapons\rifle\fp_assault_carbine\storm_fp_assault_carbine.model_animation_graph
"""
import argparse
import io
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

H4EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H4EK')
CACHE = os.path.join(HERE, 'out', 'h4_export')     # shared with h3_weapon_values --kit h4
DUMPS = os.path.join(HERE, 'out', 'h4_fp')         # h4_fp_dump.py's output
BLENDER = r'F:\Tools\blender-5.2.2-windows-x64\blender.exe'
PREFIX = 'h4:'
ARMS_RM = r'objects\characters\storm_fp\storm_fp_solo.render_model'
#: Blender armature space = G * Halo model space (rows), x UNIT
G = ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
UNIT = 3.048

#: Halo 4 bone -> the Halo 3 / Reach name h1_fp_retarget maps to Halo 1 (h1_arm_name). The
#: weapon bones keep their names (a config's `nodes`); helpers, fixups, twist and armour bones
#: and the pinky metacarpal (`pinky0`) are dropped by the config (`drop_nodes`).
_FINGER = {'1': 'low', '2': 'mid', '3': 'tip'}


def h3_name(n):
    if not n.startswith('b_'):
        return n
    b = n[2:]
    m = re.match(r'([lr])_(index|middle|ring|pinky|thumb)([123])$', b)
    if m:
        side, f, k = m.groups()
        return '%s_%s_%s' % (side, f, _FINGER[k])
    return b


#: Halo 4 world rotation * A = Halo 1 world rotation, per side: Halo 1's local x (along the bone)
#: = Halo 4's -y (left) / +y (right), local z (index side up) = -z / +z, local y = -x (both).
#: (w, x, y, z). The base: the inverse of Halo 4's bind base in camera space (90 deg about x).
ARM_AXES = {'l': (0.0, math.sqrt(0.5), -math.sqrt(0.5), 0.0),
            'r': (math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)),
            'base': (math.sqrt(0.5), -math.sqrt(0.5), 0.0, 0.0)}


def is_h4(rel):
    return isinstance(rel, str) and rel.startswith(PREFIX)


def strip(rel):
    return rel[len(PREFIX):] if is_h4(rel) else rel


def tag_path(rel):
    return os.path.join(H4EK, 'tags', strip(rel))


def export_xml(rel):
    """`tool export-tag-to-xml` of an H4EK tag (absolute paths), cached by the tag's mtime; the
    cache file's path (h1_fp_retarget.export_xml's contract)."""
    rel = strip(rel)
    src = tag_path(rel)
    if not os.path.isfile(src):
        raise SystemExit('no H4EK tag ' + rel)
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, rel.replace('\\', '~').replace('/', '~') + '.xml')
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml', src, out],
                       cwd=H4EK, capture_output=True, timeout=600)
    if not os.path.exists(out):
        raise SystemExit('H4EK tool export-tag-to-xml failed for ' + rel)
    return out


def rm_defaults(rel):
    """{node: (q (w,x,y,z), t wu)} bind transforms of an H4EK render model (names as the
    graph loader names them: h3_name)."""
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
        out[h3_name(m.group(1))] = ((q[3], q[0], q[1], q[2]), t)
    return out


def _mat_quat(m):
    """(w, x, y, z) of a 3x3 rotation (rows)."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = (0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = ((m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s)
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    q = tuple(c / n for c in q)
    return q if q[0] >= 0 else tuple(-c for c in q)


def _halo_world(flat):
    """A Blender armature-space 4x4 (row-major list) -> Halo world (3x3 rows, t wu)."""
    m = [flat[0:3], flat[4:7], flat[8:11]]
    t = (flat[3], flat[7], flat[11])
    gt = [[G[c][r] for c in range(3)] for r in range(3)]                      # G^T
    rot = [[sum(gt[r][k] * m[k][c] for k in range(3)) for c in range(3)] for r in range(3)]
    for c in range(3):                                                        # strip scale
        n = math.sqrt(sum(rot[r][c] ** 2 for r in range(3))) or 1.0
        for r in range(3):
            rot[r][c] /= n
    pos = tuple(sum(gt[r][k] * t[k] for k in range(3)) / UNIT for r in range(3))
    return rot, pos


def _local(pw, cw):
    """Local (q, t) of child world cw relative to parent world pw (3x3 rows, t)."""
    pr, pt = pw
    cr, ct = cw
    prt = [[pr[c][r] for c in range(3)] for r in range(3)]
    rot = [[sum(prt[r][k] * cr[k][c] for k in range(3)) for c in range(3)] for r in range(3)]
    d = tuple(ct[k] - pt[k] for k in range(3))
    t = tuple(sum(prt[r][k] * d[k] for k in range(3)) for r in range(3))
    return _mat_quat(rot), t


def _qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def _qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def _qrot(q, v):
    return _qmul(_qmul(q, (0.0,) + tuple(v)), _qconj(q))[1:]


def axes_of(name):
    """ARM_AXES entry for a node (h3_name): the base, a side's arm / hand / finger, else none."""
    if name == 'base':
        return ARM_AXES['base']
    side = name.split('_')[0]
    if side in ('l', 'r') and name.split('_')[1] in ('upperarm', 'forearm', 'hand', 'thumb',
                                                     'index', 'middle', 'ring', 'pinky'):
        return ARM_AXES[side]
    return (1.0, 0.0, 0.0, 0.0)


def overlay_deltas(nodes, frames):
    """A Halo 4 OVERLAY as Halo 3-style DELTAS in Halo 1's local axes. Foundry imports an overlay
    as a full pose stacked on a base animation (look / moving frame 0 == idle frame 0, every
    node): the delta of frame f = inverse(frame 0) * frame f per node -- rotation in the node's
    own frame, translation in its parent's -- then turned into Halo 1's axes (axes_of: A_n^-1 *
    d * A_n for a rotation, A_p^-1 for a translation). Frame 0 is the overlay's zero delta."""
    ref = frames[0]
    out = []
    for fr in frames:
        row = []
        for i, ((n, p), (q, t, s)) in enumerate(zip(nodes, fr)):
            qr, tr = ref[i][0], ref[i][1]
            an = axes_of(n)
            ap = axes_of(nodes[p][0]) if p >= 0 else (1.0, 0.0, 0.0, 0.0)
            d = _qmul(_qconj(qr), q)
            d = _qmul(_qmul(_qconj(an), d), an)
            dt = _qrot(_qconj(ap), tuple(a - b for a, b in zip(t, tr)))
            row.append((d, dt, s))
        out.append(row)
    return out


def dump_path(rel):
    return os.path.join(DUMPS, os.path.splitext(os.path.basename(strip(rel)))[0] + '.json')


def graph_types(rel):
    """{anim name: (animation type, frame count)} from the graph's export."""
    s = io.open(export_xml(rel), encoding='utf-8', errors='replace').read()
    blk = s[s.find('<block name="animations"'):]
    out = {}
    for m in re.finditer(r'<element index="\d+" name="([^"]*)">\s*<field name="name".*?'
                         r'name="frame count" value="(\d+)".*?name="animation type" value="([^"]*)"',
                         blk, re.S):
        out.setdefault(m.group(1), (m.group(3), int(m.group(2))))
    return out


def load_graph(rel):
    """(nodes [(name, parent index)], {anim: (type, frames, animated)}, events) -- reach_tags.
    load_graph's shape. A frame = [(q (w,x,y,z), t wu, None)] LOCAL per node, Halo convention.
    Needs the Blender dump (h4_fp_dump.py); the command is printed when it is missing."""
    import h1_fp_retarget
    path = dump_path(rel)
    if not os.path.exists(path):
        raise SystemExit('no Halo 4 FP dump %s -- run:\n  "%s" --background --python "%s" -- "%s"'
                         % (path, BLENDER, os.path.join(HERE, 'h4_fp_dump.py'), strip(rel)))
    d = json.load(io.open(path, encoding='utf-8'))
    bones, parents = d['bones'], d['parents']
    idx = {b: i for i, b in enumerate(bones)}
    nodes = [(h3_name(b), idx[p] if p else -1) for b, p in zip(bones, parents)]
    types = graph_types(rel)
    anims = {}
    for name, a in d['anims'].items():
        gname = name.replace(' ', ':')
        typ, count = types.get(gname, ('base', len(a['frames']) - 1))
        frames = []
        for fr in a['frames'][:count]:
            world = [_halo_world(m) for m in fr]
            frames.append([(_local(world[idx[p]], w) if p else (_mat_quat(w[0]), w[1])) + (None,)
                           for w, p in zip(world, parents)])
        if typ == 'overlay':
            frames = overlay_deltas(nodes, frames)
        animated = {'rot': set(), 'trans': set(), 'scale': set()}
        for i in range(len(bones)):
            q0, t0 = frames[0][i][0], frames[0][i][1]
            for f in frames[1:]:
                if max(abs(a - b) for a, b in zip(f[i][0], q0)) > 1e-4:
                    animated['rot'].add(i)
                if max(abs(a - b) for a, b in zip(f[i][1], t0)) > 1e-5:
                    animated['trans'].add(i)
        anims[gname] = (typ, frames, animated)
    events = h1_fp_retarget.frame_events(export_xml(rel))
    return nodes, anims, events


def bitmap_images(rel):
    """Every image of an H4EK bitmap tag (`rel` with .bitmap), top mip each, in order.

    MEASURED (the Storm Rifle's covglyph = 10 digits, buildup = 7 heat stages, overheat = 2):
    the tag keeps ALL images as ONE pixel blob -- each image's mip chain in turn -- right after a
    u32 of the blob's total size, and the blob ends exactly where the next `lbgt` chunk starts.
    That end check picks the size marker (a size value also occurs in headers and in pixel data);
    h4_bitmap's 'quietest decode' picked a blank image of a multi-image tag."""
    import h4_bitmap
    from PIL import Image
    import struct
    s = io.open(export_xml(rel), encoding='utf-8', errors='replace').read()
    b = s[s.find('<block name="bitmaps"'):]
    specs = []
    for m in re.finditer(r'<element index="\d+"[^>]*>(.*?)</element>', b, re.S):
        g = lambda k: re.search(r'name="%s" value="([^"]*)"' % k, m.group(1))   # noqa: E731
        if g('width') is None:
            continue
        mips = int(g('mipmap count').group(1)) + 1 if g('mipmap count') else 1
        specs.append((int(g('width').group(1)), int(g('height').group(1)), g('format').group(1), mips))
    blob = open(tag_path(rel), 'rb').read()
    sizes = [h4_bitmap.chain_size(w, h, f, n) for w, h, f, n in specs]
    total = sum(sizes)
    start = None
    for extra in (0, 8, 16, 4, 12):
        key = struct.pack('<I', total + extra)
        i = blob.find(key)
        while i != -1:
            end = i + 4 + total
            if end == len(blob) or blob[end:end + 4] == b'lbgt':
                start = i + 4
                break
            i = blob.find(key, i + 1)
        if start is not None:
            break
    if start is None:                            # the old search, image 0 only
        w, h, f, n = specs[0]
        return [h4_bitmap.decode(tag_path(rel), w, h, f, n)]
    out, at = [], start
    for (w, h, f, n), size in zip(specs, sizes):
        top = blob[at:at + h4_bitmap.chain_size(w, h, f, 1)]
        if f in h4_bitmap.FOURCC:
            img = h4_bitmap._top(top, 0, w, h, f).convert('RGBA')
        else:
            img = Image.frombytes('RGBA', (w, h), top, 'raw', 'BGRA')
        out.append(img)
        at += size
    return out


def decode_bitmap(rel, index=0):
    """`rel` WITH its .bitmap extension: (RGBA image `index` (top mip), sprite boxes) of an H4EK
    bitmap -- h3_hud_art.decode's shape (the export is Halo 3-shaped)."""
    import h3_sprite_box
    rel = strip(rel)
    return bitmap_images(rel)[index], h3_sprite_box.sprites(export_xml(rel))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', help='an FP graph: animations, types, frames, animated nodes')
    a = ap.parse_args()
    if a.list:
        nodes, anims, events = load_graph(a.list)
        for n, (typ, fr, an) in sorted(anims.items()):
            print('%-44s %-8s %4d frames  rot %2d trans %2d  %s' % (n, typ, len(fr), len(an['rot']),
                                                                    len(an['trans']), events.get(n, '')))
        print(len(nodes), 'nodes:', ' '.join(n for n, _p in nodes))


if __name__ == '__main__':
    main()
