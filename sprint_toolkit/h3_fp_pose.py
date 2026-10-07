r"""Full per-node poses out of a Halo 3 kit animation graph (jmad), for retargeting.

`h3_anim_decode.py` decodes the ANIMATED tracks of an animation, which is all a retime
needs. A retarget needs every node on every frame: the static nodes live in the
animation's `default_data`, and which node each track belongs to is in the node masks.
This module puts the two together.

    [default_data][compressed_data][static masks 3 x u64][animated masks 3 x u64][uncompressed]

default_data: 32-byte header (`01 n m 01` at +0, translations at +12, scale at +16), then
n rotations as int16 x4 / 32767, m translations as float32 x3, one float32 scale.
Masks: bit i = skeleton node i; static R, T, S then animated R, T, S. Static and animated
are disjoint and together cover every node. Tracks are in node order within each mask.

Quaternions are stored (i, j, k, w); this module hands them out as (w, x, y, z).
Translations are Halo 3 world units (1 wu = 100 JMS units).

    python h3_fp_pose.py <graph.model_animation_graph> <export.xml> [--anim NAME]
"""
import argparse
import io
import math
import re
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_anim_decode as dec   # noqa: E402
import h3tag                   # noqa: E402


def skeleton_from_xml(path):
    """[(name, parent_index)] from `tool export-tag-to-xml` of the graph."""
    s = io.open(path, encoding='utf-8', errors='replace').read()
    blk = re.search(r'<block name="skeleton nodes"[^>]*>(.*?)</block>', s, re.S).group(1)
    out = []
    for m in re.finditer(r'<element index="\d+" name="[^"]*">(.*?)</element>', blk, re.S):
        body = m.group(1)
        name = re.search(r'name="name" value="([^"]*)"', body).group(1)
        par = int(re.search(r'name="parent node index" value=",(-?\d+)"', body).group(1))
        out.append((name, par))
    return out


def animations_from_xml(path):
    """[(name, type, frame_info_type, member)] in animation-block order."""
    s = io.open(path, encoding='utf-8', errors='replace').read()
    blk = s[s.find('<block name="animations"'):]
    out = []
    for m in re.finditer(r'<element index="(\d+)" name="([^"]*)">\s*<field name="name"(.*?)'
                         r'name="resource_group_member" value="(-?\d+)"', blk, re.S):
        body = m.group(3)
        typ = re.search(r'name="animation type" value="([^"]*)"', body).group(1)
        fit = re.search(r'name="frame info type" value="([^"]*)"', body).group(1)
        grp = re.search(r'name="resource_group" value="(-?\d+)"', body)
        # (group, member): members are numbered per tag resource group (h3_anim_decode)
        out.append((m.group(2), typ, fit, (int(grp.group(1)) if grp else 0, int(m.group(4)))))
    return out


def _bits(mask):
    return [i for i in range(64) if mask >> i & 1]


def poses(tag, e, nodes, animated=None):
    """Every node's local (rot (w,x,y,z), trans (x,y,z) wu, scale) on every frame.

    `animated`, if a dict, receives {'rot': set, 'trans': set, 'scale': set} of the node
    indices that have tracks -- an overlay's deltas live only in those."""
    b = tag.data[e['at']:e['at'] + e['size']]
    hdr = b[0:32]
    n, m = hdr[1], hdr[2]
    t_at = struct.unpack_from('<I', hdr, 12)[0]
    s_at = struct.unpack_from('<I', hdr, 16)[0]
    srot = [struct.unpack_from('<4h', b, 32 + 8 * k) for k in range(n)]
    srot = [(q[3] / 32767.0, q[0] / 32767.0, q[1] / 32767.0, q[2] / 32767.0) for q in srot]
    strn = [struct.unpack_from('<3f', b, t_at + 12 * k) for k in range(m)]
    sscl = struct.unpack_from('<f', b, s_at)[0]
    flags_at = e['default_data'] + e['compressed_data']
    w = struct.unpack_from('<6Q', b, flags_at)
    sR, sT, sS, aR, aT, aS = (_bits(x) for x in w)
    if len(sR) != n or len(sT) != m:
        raise ValueError('static masks %d/%d disagree with default header %d/%d'
                         % (len(sR), len(sT), n, m))
    if animated is not None:
        animated.update(rot=set(aR), trans=set(aT), scale=set(aS))
    anim = dec.read_animation(tag, dict(e, frames_at=flags_at + 48 + 32,
                                        animated=(len(aR), len(aT), len(aS))))
    N = len(nodes)
    out = []
    for f in range(e['frames']):
        rot = [None] * N
        trn = [None] * N
        scl = [sscl] * N
        for k, i in enumerate(sR):
            rot[i] = srot[k]
        for k, i in enumerate(sT):
            trn[i] = strn[k]
        for k, i in enumerate(aR):
            q = anim['rotations'][f][k]
            rot[i] = (q[3], q[0], q[1], q[2])
        for k, i in enumerate(aT):
            trn[i] = anim['translations'][f][k]
        for k, i in enumerate(aS):
            scl[i] = anim['scales'][f][k]
        out.append(list(zip(rot, trn, scl)))
    return out


def load(graph, xml):
    """(nodes, {anim name: (type, frames poses, animated node sets)})"""
    nodes = skeleton_from_xml(xml)
    mem = dec.members_from_xml(xml)
    tag = h3tag.Tag(graph)
    located = {(e['group'], e['index']): e for e in dec.blobs(tag, mem)}
    out = {}
    for name, typ, fit, member in animations_from_xml(xml):
        e = located.get(member)
        if e is None or not e['ok']:
            continue
        animated = {}
        out[name] = (typ, poses(tag, e, nodes, animated), animated)
    return nodes, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('graph')
    ap.add_argument('xml')
    ap.add_argument('--anim')
    a = ap.parse_args()
    nodes, anims = load(a.graph, a.xml)
    for name, (typ, fr, animated) in anims.items():
        if a.anim and name != a.anim:
            continue
        worst = max(abs(math.sqrt(sum(c * c for c in r)) - 1) for p in fr for r, t, s in p)
        print('%-45s %-8s %4d frames  |q|-1 max %.4f' % (name, typ, len(fr), worst))
        if a.anim:
            for (nm, par), (r, t, s) in zip(nodes, fr[0]):
                print('   %-14s par %3d  q %s  t %s  s %.3f'
                      % (nm, par, ' '.join('%+.3f' % c for c in r),
                         ' '.join('%+.4f' % c for c in t), s))


if __name__ == '__main__':
    main()
