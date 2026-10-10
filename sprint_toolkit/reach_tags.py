r"""HALO REACH tags (HREK) read in the SHAPES the Halo 3 readers return -- so the Halo 1 port
pipeline (h3_rm_to_jms, h1_fp_retarget, h1_h3_weapon_model) takes a Reach source with no
second code path. Written for the DMR, the wave-B pilot (2026-10-10).

A port config names a Reach tag with the prefix `reach:` (`reach:objects\weapons\rifle\
dmr\dmr.render_model`); `is_reach` / `strip` test and remove it. A path without the prefix
is Halo 3's, read exactly as before.

HREK's `tool export-tag-to-xml` (ABSOLUTE paths, cwd = the kit) writes FLAT XML, and none of
the Halo 3 parsers can read it:
  * a block is `<field name=X type="block"/>` followed by its `<element>`s as SIBLINGS (Halo 3
    wraps them in `<block name=X>`); a struct's fields follow it as siblings too;
  * a block index is the target element's NAME (or NONE), not `,<index>`;
  * a tag reference is the BASENAME only (`dmr_bullet`); `find_tag` resolves it.

ANIMATIONS ARE NOT COMPRESSED-ONLY (the DMR's route research, 2026-10-10; it corrects
PORTING "REACH STEP 9"). The member's `data sizes` are the blob's sections in ORDER, with
the export's labels shifted by one:

    label (export)         really
    static_node_flags      default data (Halo 3's: 32-byte header, n int16 rotations, m
                           float translations, scale)
    animated_node_flags    codec-3 compressed copy (int16 quaternions)
    movement_data          static node masks, 3 x u64
    pill_offset_data       animated node masks, 3 x u64
    default_data           (0)
    uncompressed_data      12 bytes a frame, all zero in fp_dmr (root motion slot)
    compressed_data        a FULL codec-2 float copy, Halo 3's uncompressed layout (32-byte
                           header, node-major float32 rotations / translations / scales)
    blend_screen_data      ...

So a Reach FP pose = Halo 3's: static from the default data, animated from the codec-2 copy
(h3_anim_decode.read_animation). Checked on all 25 fp_dmr animations: masks = header
counts, unit quaternions, codec 3 and codec 2 agree within 0.042 deg.

    python reach_tags.py --pose objects\characters\spartans\fp\weapons\rifle\fp_dmr\fp_dmr.model_animation_graph
"""
import argparse
import io
import math
import os
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_anim_decode as dec   # noqa: E402
import h3tag                   # noqa: E402

HREK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HREK')
CACHE = os.path.join(HERE, 'out', 'reach_export')    # shared with h3_weapon_values --kit reach
PREFIX = 'reach:'
ARMS_RM = r'objects\characters\spartans\fp\fp.render_model'


def is_reach(rel):
    return isinstance(rel, str) and rel.startswith(PREFIX)


def strip(rel):
    return rel[len(PREFIX):] if is_reach(rel) else rel


def tag_path(rel):
    return os.path.join(HREK, 'tags', strip(rel))


def export_xml(rel):
    """`tool export-tag-to-xml` of an HREK tag (absolute paths), cached by the tag's mtime."""
    rel = strip(rel)
    src = tag_path(rel)
    if not os.path.isfile(src):
        raise SystemExit('no HREK tag ' + rel)
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, rel.replace('\\', '~').replace('/', '~') + '.xml')
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run([os.path.join(HREK, 'tool.exe'), 'export-tag-to-xml', src, out],
                       cwd=HREK, capture_output=True, timeout=600)
    if not os.path.exists(out):
        raise SystemExit('HREK tool export-tag-to-xml failed for ' + rel)
    return out


_INDEX = {}


def find_tag(base, ext, near=None):
    """A basename reference -> the kit-relative path (no extension) of <base>.<ext>, the one
    sharing the longest folder prefix with `near` (the referencing tag) first."""
    if not base:
        return None
    if '\\' in base:
        return base
    root = os.path.join(HREK, 'tags')
    if not _INDEX:
        for d, _ds, fs in os.walk(root):
            for f in fs:
                b, e = os.path.splitext(f)
                _INDEX.setdefault((b.lower(), e[1:].lower()), []).append(
                    os.path.relpath(os.path.join(d, b), root))
    hits = _INDEX.get((base.lower(), (ext or '').lower()), [])
    if not hits:
        return None
    nb = strip(near or '').lower().split('\\')[:-1]

    def shared(h):
        a, n = h.lower().split('\\')[:-1], 0
        while n < min(len(a), len(nb)) and a[n] == nb[n]:
            n += 1
        return -n
    return sorted(hits, key=shared)[0]


# ---- the flat XML -------------------------------------------------------------------------

def tree(path):
    txt = io.open(path, encoding='utf-8', errors='replace').read()
    txt = re.sub(r'value="<([^"<>]*)>"', 'value="[unavailable]"', txt)
    # garbage element names in the Needle Rifle chud: control characters (not legal XML)
    # dropped, and a NAME holding a quote (`""p`) escaped, line-wise
    txt = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', txt)
    txt = re.sub(r'(<element index="\d+" name=")(.*)(">)$',
                 lambda m: m.group(1) + m.group(2).replace('"', '&quot;') + m.group(3), txt,
                 flags=re.M)
    return ET.fromstring(txt)


def blocks(el):
    """{block name: [element, ...]} of el's direct children (a block field is followed by
    its elements; any other field ends the run)."""
    out, cur = {}, None
    for c in el:
        if c.tag == 'field':
            cur = c.get('name') if c.get('type') == 'block' else None
            if cur is not None:
                out.setdefault(cur, [])
        elif c.tag == 'element' and cur is not None:
            out[cur].append(c)
    return out


def f(el, name):
    x = el.find("field[@name='%s']" % name)
    return x.get('value') if x is not None else None


def vec(s):
    return tuple(float(v) for v in s.split(',')) if s else ()


# ---- render models ------------------------------------------------------------------------

def load_render_model(path):
    """HREK render_model export -> the dict h4_rm.load returns (nodes, markers, materials,
    regions, compression, meshes), so h3_rm_to_jms.convert runs on it unchanged."""
    root = tree(path)
    B = blocks(root)
    nodes = B.get('nodes', [])
    names = [f(n, 'name') for n in nodes]

    def idx(v):
        return -1 if v in (None, 'NONE', '') else (names.index(v) if v in names else int(v))
    out = {'nodes': [], 'markers': [], 'materials': [], 'meshes': [], 'regions': []}
    for n in nodes:
        out['nodes'].append({'name': f(n, 'name'), 'parent': idx(f(n, 'parent node')),
                             'pos': vec(f(n, 'default translation')),
                             'rot': vec(f(n, 'default rotation'))})
    for g in B.get('marker groups', []):
        for m in blocks(g).get('markers', []):
            out['markers'].append({'name': f(g, 'name'), 'node': int(f(m, 'node index')),
                                   'pos': vec(f(m, 'translation')), 'rot': vec(f(m, 'rotation')),
                                   'region': f(m, 'region index'),
                                   'perm': f(m, 'permutation index')})
    mats = B.get('materials', [])
    matnames = [f(m, 'render method') for m in mats]
    out['materials'] = matnames
    for r in B.get('regions', []):
        out['regions'].append((f(r, 'name'), [(f(p, 'name'), f(p, 'mesh index'), f(p, 'mesh count'))
                                              for p in blocks(r).get('permutations', [])]))
    # `render geometry` is a struct: its blocks follow it as siblings (uniquely named)
    kids = list(root)
    start = kids.index(root.find("field[@name='render geometry']"))
    G, cur = {}, None
    for c in kids[start + 1:]:
        if c.tag == 'field' and c.get('type') == 'block':
            cur = c.get('name')
            G.setdefault(cur, [])
        elif c.tag == 'element' and cur:
            G[cur].append(c)
        elif c.tag == 'field':
            cur = None
    ci = G.get('compression info', [])
    out['compression'] = {'pos0': vec(f(ci[0], 'position bounds 0')),
                          'pos1': vec(f(ci[0], 'position bounds 1')),
                          'uv0': vec(f(ci[0], 'texcoord bounds 0')),
                          'uv1': vec(f(ci[0], 'texcoord bounds 1'))}
    temps = G.get('per mesh temporary', [])
    for mi, me in enumerate(G.get('meshes', [])):
        mb = blocks(me)
        parts = [{'material': (matnames.index(f(p, 'render method index'))
                               if f(p, 'render method index') in matnames else -1),
                  'start': int(f(p, 'index start')), 'count': int(f(p, 'index count')),
                  'flags': f(p, 'part flags'), 'name': p.get('name')}
                 for p in mb.get('parts', [])]
        mesh = {'parts': parts, 'index_type': f(me, 'index buffer type'),
                'vertex_type': f(me, 'vertex type'), 'rigid': f(me, 'rigid node index'),
                'verts': [], 'indices': []}
        if mi < len(temps):
            tb = blocks(temps[mi])
            for v in tb.get('raw vertices', []):
                ni = [int(x.get('value')) for x in v.iter('field') if x.get('name') == 'node index']
                nw = [float(x.get('value')) for x in v.iter('field') if x.get('name') == 'node weight']
                mesh['verts'].append({'pos': vec(f(v, 'position')), 'uv': vec(f(v, 'texcoord')),
                                      'n': vec(f(v, 'normal')), 'nodes': ni, 'w': nw})
            mesh['indices'] = [int(f(i, 'word')) & 0xFFFF for i in tb.get('raw indices', [])]
        out['meshes'].append(mesh)
    return out


def rm_defaults(rel):
    """{node: (q (w,x,y,z), t wu)} bind transforms (h1_fp_retarget.rm_defaults' shape)."""
    out = {}
    for n in blocks(tree(export_xml(rel))).get('nodes', []):
        t = vec(f(n, 'default translation'))
        q = vec(f(n, 'default rotation'))
        out[f(n, 'name')] = ((q[3], q[0], q[1], q[2]), t)
    return out


# ---- animation graphs ---------------------------------------------------------------------

def _graph(root):
    """The graph's definitions / content are structs: their blocks are top-level siblings."""
    return blocks(root)


def skeleton(root):
    """[(name, parent index)] -- h3_fp_pose.skeleton_from_xml's shape."""
    sk = _graph(root).get('skeleton nodes', [])
    names = [f(n, 'name') for n in sk]
    return [(nm, names.index(f(n, 'parent node index'))
             if f(n, 'parent node index') not in (None, 'NONE') else -1)
            for nm, n in zip(names, sk)]


def animations(root):
    """[(name, type, frame info type, (group, member), frames, events)] in block order."""
    out = []
    for a in _graph(root).get('animations', []):
        sh = blocks(a).get('shared animation data', [])
        if not sh:
            continue
        s = sh[0]
        sb = blocks(s)
        evs = [(f(e, 'type'), int(f(e, 'frame'))) for e in sb.get('frame events', [])]
        out.append((f(a, 'name'), f(s, 'animation type'), f(s, 'frame info type'),
                    (int(f(s, 'resource_group')), int(f(s, 'resource_group_member'))),
                    int(f(s, 'frame count')), evs))
    return out


SECTIONS = ('static_node_flags', 'animated_node_flags', 'movement_data', 'pill_offset_data',
            'default_data', 'uncompressed_data', 'compressed_data', 'blend_screen_data',
            'object_space_offset_data', 'ik_chain_event_data', 'ik_chain_control_data',
            'ik_chain_proxy_data', 'ik_chain_pole_vector_data', 'uncompressed_object_space_data',
            'fik_anchor_data', 'uncompressed_object_space_node_flags', 'compressed_event_curve')


def members(root):
    """[{'group', 'index', 'frames', 'size', 'sizes'}] in group, member order (the shape
    h3_anim_decode.blobs matches against the tag's tgst chunks)."""
    out = []
    for g, grp in enumerate(blocks(root).get('tag resource groups', [])):
        # the pageable resource is a struct: group_members follows as a sibling block
        for i, m in enumerate(blocks(grp).get('group_members', [])):
            sizes = [int(f(m, k) or 0) for k in SECTIONS]
            out.append({'group': g, 'index': i, 'frames': int(f(m, 'frame count')),
                        'size': sum(sizes), 'sizes': sizes})
    return out


def _bits(mask):
    return [i for i in range(64) if mask >> i & 1]


def poses(tag, e, nodes, animated=None):
    """h3_fp_pose.poses for a Reach member: every node's local (rot (w,x,y,z), trans wu,
    scale) on every frame, from the default data + the codec-2 float copy."""
    b = tag.data[e['at']:e['at'] + e['size']]
    d0, c0, sm, am, _z, mv, u0 = e['sizes'][:7]
    n, m = b[1], b[2]
    t_at = struct.unpack_from('<I', b, 12)[0]
    s_at = struct.unpack_from('<I', b, 16)[0]
    srot = [struct.unpack_from('<4h', b, 32 + 8 * k) for k in range(n)]
    srot = [(q[3] / 32767.0, q[0] / 32767.0, q[1] / 32767.0, q[2] / 32767.0) for q in srot]
    strn = [struct.unpack_from('<3f', b, t_at + 12 * k) for k in range(m)]
    sscl = struct.unpack_from('<f', b, s_at)[0]
    flags_at = d0 + c0
    sR, sT, sS, aR, aT, aS = (_bits(x) for x in struct.unpack_from('<6Q', b, flags_at))
    if len(sR) != n or len(sT) != m:
        raise ValueError('static masks %d/%d disagree with default header %d/%d'
                         % (len(sR), len(sT), n, m))
    unc = flags_at + sm + am + mv
    if b[unc] != 2:
        raise ValueError('Reach codec-2 copy expected at +%d, codec %d' % (unc, b[unc]))
    if animated is not None:
        animated.update(rot=set(aR), trans=set(aT), scale=set(aS))
    anim = dec.read_animation(tag, dict(e, frames_at=unc + 32,
                                        animated=(len(aR), len(aT), len(aS))))
    N = len(nodes)
    out = []
    for fr in range(e['frames']):
        rot, trn, scl = [None] * N, [None] * N, [sscl] * N
        for k, i in enumerate(sR):
            rot[i] = srot[k]
        for k, i in enumerate(sT):
            trn[i] = strn[k]
        for k, i in enumerate(aR):
            q = anim['rotations'][fr][k]
            rot[i] = (q[3], q[0], q[1], q[2])
        for k, i in enumerate(aT):
            trn[i] = anim['translations'][fr][k]
        for k, i in enumerate(aS):
            scl[i] = anim['scales'][fr][k]
        out.append(list(zip(rot, trn, scl)))
    return out


def load_graph(rel):
    """(nodes, {anim: (type, frames poses, animated)}, {anim: [(event type, frame)]}) --
    h3_fp_pose.load + h1_fp_retarget.frame_events for a Reach graph."""
    root = tree(export_xml(rel))
    nodes = skeleton(root)
    tag = h3tag.Tag(tag_path(rel))
    located = {(e['group'], e['index']): e for e in dec.blobs(tag, members(root))}
    out, events = {}, {}
    for name, typ, _fit, member, frames, evs in animations(root):
        e = located.get(member)
        if e is None or not e['ok']:
            continue
        animated = {}
        out[name] = (typ, poses(tag, e, nodes, animated), animated)
        events[name] = evs
    return nodes, out, events


# ---- bitmaps ------------------------------------------------------------------------------

def decode_bitmap(rel):
    """`rel` WITH its .bitmap extension (h3_hud_art.decode's argument). (RGBA image of the top mip, sprite boxes [(l, r, t, b, reg x, reg y)] per sequence) of
    an HREK bitmap -- h3_hud_art.decode's shape. Pixels = the tag's LARGEST tgda chunk (as
    Halo 3's), linear, top mip first: a8r8g8b8 as B, G, R, A; a8 alpha; dxt / dxn blocks."""
    import h4_bitmap
    from PIL import Image
    rel = strip(rel)
    root = tree(export_xml(rel))
    bm = blocks(root).get('bitmaps', [])
    if not bm:
        raise SystemExit('%s: no bitmaps' % rel)
    w, h, fmt = int(f(bm[0], 'width')), int(f(bm[0], 'height')), f(bm[0], 'format')
    tag = h3tag.Tag(tag_path(rel))
    nd = max((x for x in tag.nodes() if x.marker == 'tgda'), key=lambda x: x.length)
    blob = bytes(tag.data[nd.payload_at:nd.payload_at + nd.length])
    if fmt == 'a8r8g8b8':
        img = Image.frombytes('RGBA', (w, h), blob[:w * h * 4], 'raw', 'BGRA')
    elif fmt in ('a8', 'y8', 'ay8'):
        a = Image.frombytes('L', (w, h), blob[:w * h])
        if fmt == 'a8':
            img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
            img.putalpha(a)
        else:
            img = Image.merge('RGBA', (a, a, a, a if fmt == 'ay8' else Image.new('L', (w, h), 255)))
    elif fmt in h4_bitmap.FOURCC:
        size = h4_bitmap.chain_size(w, h, fmt, 1)
        hdr = (b'DDS ' + struct.pack('<7I', 124, 0x1007, h, w, size, 0, 1) + bytes(44)
               + struct.pack('<2I', 32, 0x4) + h4_bitmap.FOURCC[fmt]
               + struct.pack('<5I', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0))
        img = Image.open(io.BytesIO(hdr + blob[:size]))
        img.load()
        img = img.convert('RGBA')
    else:
        raise SystemExit('%s: format %s not handled' % (rel, fmt))
    boxes = []
    for sq in blocks(root).get('sequences', []):
        sp = blocks(sq).get('sprites', [])
        if sp:
            r = vec(f(sp[0], 'registration point'))
            boxes.append((float(f(sp[0], 'left')), float(f(sp[0], 'right')),
                          float(f(sp[0], 'top')), float(f(sp[0], 'bottom')), r[0], r[1]))
        else:
            boxes.append((0.0, 1.0, 0.0, 1.0, 0.5, 0.5))
    return img, boxes


def px_per_unit(rel):
    """Chud pixels a unit of a Reach bitmap: 'bitmap is double sized' 2, 'triple sized' 3
    (`more flags`; used by the chud for 4K assets), else 1."""
    flags = ' '.join(f(b, 'more flags') or '' for b in blocks(tree(export_xml(strip(rel)))).get('bitmaps', []))
    return 3.0 if 'triple sized' in flags else 2.0 if 'double sized' in flags else 1.0


# ---- chud ---------------------------------------------------------------------------------

#: Reach state conditions -> Halo 3's `unit zoom state` bits (h1_h3_scope.zoom_only: bit 0 =
#: unzoomed); a widget with no zoom condition is drawn in every zoom state (0)
ZOOM_BITS = {'unzoomed': 1, 'zoom lvl 1': 2, 'zoom lvl 2': 4}


def _state_zoom(el):
    """The zoom bits of a widget's / collection's ACTIVE state (any OR'ed zoom condition)."""
    z = 0
    for st in blocks(el).get('state data', []):
        for grp in blocks(st).get('Active State', []):
            for c in blocks(grp).get('OR', []):
                z |= ZOOM_BITS.get(f(c, 'condition'), 0)
    return z


def _place(el):
    """(anchor, origin, offset, scale) of the FULLSCREEN placement: the element with no window
    state (Reach lists halfscreen / quarterscreen variants beside it)."""
    pl = [p for p in blocks(el).get('placement data', []) if not f(p, 'window state')]
    if not pl:
        return None
    p = pl[0]
    return (f(p, 'anchor type'), vec(f(p, 'widget origin')), vec(f(p, 'origin offset')),
            vec(f(p, 'widget scale')))


def chud_widgets(chud):
    """[(name, fields)] of every bitmap widget of a Reach chud_definition, in
    h1_h3_scope.widgets' shape (bitmap as a `reach:` path, zoom as Halo 3's bits, the
    fullscreen placement; `parent` anchors resolved onto the collection's placement)."""
    root = tree(export_xml(strip(chud) + '.chud_definition'))
    out = []
    for coll in blocks(root).get('widget collections', []):
        cz = _state_zoom(coll)
        cp = _place(coll) or ('crosshair', (0.0, 0.0), (0.0, 0.0), (1.0, 1.0))
        for wd in blocks(coll).get('bitmap widgets', []):
            pl = _place(wd)
            if pl is None:
                continue
            anchor, origin, offset, scale = pl
            if anchor == 'parent':
                anchor = cp[0]
                offset = (offset[0] + cp[2][0], offset[1] + cp[2][1])
            rd = blocks(wd).get('render data', [])
            an = blocks(wd).get('animation data', [])
            active = None
            if an:
                m = re.search(r"'animation', '([^']*)'", str([(c.get('name'), c.get('value')) for c in an[0]]))
                active = m.group(1) if m else None
            flags = set(x.strip() for x in (f(wd, 'flags') or '').split(',') if x.strip())
            bm = find_tag(f(wd, 'bitmap'), 'bitmap', strip(chud))
            col = f(rd[0], 'custom color A') if rd else None
            out.append((wd.get('name'), {
                'bitmap': PREFIX + bm if bm else None,
                'sequence': int(f(wd, 'sequence index') or 0),
                'anchor': anchor, 'origin': origin, 'offset': offset, 'scale': scale,
                'zoom': _state_zoom(wd) or cz, 'window': 0,
                # Halo 3's check: colour '0' = drawn black (a mask can only darken)
                'color': '0' if col in (None, '0,0,0,0') else col,
                'flags': flags, 'shader': f(rd[0], 'shader type') if rd else None,
                'active': active, 'collection': coll.get('name'),
                'px_per_unit': px_per_unit(bm + '.bitmap') if bm else 1.0}))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pose', help='an HREK graph: list its animations, check every quaternion')
    ap.add_argument('--rm', help='an HREK render model: nodes, markers, materials, counts')
    a = ap.parse_args()
    if a.pose:
        nodes, anims, events = load_graph(a.pose)
        print(len(nodes), 'nodes')
        for name, (typ, fr, _an) in anims.items():
            worst = max(abs(math.sqrt(sum(c * c for c in r)) - 1) for p in fr for r, t, s in p
                        if r is not None)
            print('%-45s %-8s %4d frames  |q|-1 max %.5f  %s' % (name, typ, len(fr), worst,
                                                              events.get(name, '')))
    if a.rm:
        rm = load_render_model(export_xml(a.rm))
        print('nodes', [(n['name'], n['parent']) for n in rm['nodes']])
        for mk in rm['markers']:
            print('marker %-24s node %d pos %s' % (mk['name'], mk['node'], mk['pos']))
        print('materials', rm['materials'])
        print('meshes', [(len(m['verts']), len(m['indices']), len(m['parts'])) for m in rm['meshes']])


if __name__ == '__main__':
    main()
