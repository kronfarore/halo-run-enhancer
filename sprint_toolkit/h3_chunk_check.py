r"""Does a tag's raw geometry actually resolve in this map?

The ported SAW's world model renders where the scenario PLACES it but not when the weapon
is dropped, and a bisect proved the model TAG is fine. Placement and runtime differ in
whether the geometry has to be streamed in, so this asks the authority: the `zone` tag's
Tag Resources name each chunk's parent tag and the segment behind it, and a segment whose
page index is -1 has no bytes behind it.

A standalone rebuilt map keeps Segments and Raw Pages in `zone` (0x58 / 0x34) rather than
`play`, which is why h3_raw_residency crashes on one -- it reaches for the play tag's
external cache list first.

    python h3_chunk_check.py [map] [--game "Halo 3"] [substring ...]
"""
import argparse, contextlib, io, os, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
ZONE_TAG_RESOURCES, TAGRES_ELEM = 0x64, 0x40
TAGRES_PARENT, TAGRES_SEGMENT = 0xC, 0x22
ZONE_SEGMENTS, ZONE_SEG_ELEM = 0x58, 0x10
ZONE_RAW_PAGES, ZONE_PAGE_ELEM = 0x34, 0x58


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map', nargs='?', default='010_jungle')
    ap.add_argument('--game', default='Halo 3')
    ap.add_argument('needles', nargs='*', default=['saw', 'assault_rifle'])
    a = ap.parse_args()
    he.load_settings()
    folder = {'Halo 3': 'halo3'}.get(a.game, 'halo3')
    live = os.path.join(he.mcc_root(), folder, 'maps', a.map + '.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, a.game)

    zone = next((t for t in m.tags if t.get('class') == 'zone'), None)
    if not zone or not zone.get('base'):
        raise SystemExit('no zone tag')
    zb = zone['base']
    n_res = m.i32(zb + ZONE_TAG_RESOURCES)
    res_base = hp._block_base(m, zb + ZONE_TAG_RESOURCES)
    n_seg = m.i32(zb + ZONE_SEGMENTS)
    seg_base = hp._block_base(m, zb + ZONE_SEGMENTS) if n_seg else None
    n_page = m.i32(zb + ZONE_RAW_PAGES)
    print('%s: %d tag resource(s), %d segment(s), %d raw page(s)'
          % (a.map, n_res, n_seg, n_page))

    by_tag = {}
    for i in range(n_res):
        e = res_base + i * TAGRES_ELEM
        parent = m.u32(e + TAGRES_PARENT)
        seg = struct.unpack_from('<h', m.data, e + TAGRES_SEGMENT)[0]
        by_tag.setdefault(parent & 0xFFFF, []).append(seg)

    rows = []
    for t in m.tags:
        name = t.get('name') or ''
        if not any(nd in name for nd in a.needles) or 'sawtooth' in name:
            continue
        segs = by_tag.get(t['index'] & 0xFFFF, [])
        good = bad = 0
        for s in segs:
            if s < 0 or seg_base is None or s >= n_seg:
                bad += 1
                continue
            se = seg_base + s * ZONE_SEG_ELEM
            primary = struct.unpack_from('<h', m.data, se)[0]
            secondary = struct.unpack_from('<h', m.data, se + 2)[0]
            if primary < 0 and secondary < 0:
                bad += 1
            else:
                good += 1
        if segs:
            rows.append((t.get('class'), name, len(segs), good, bad))
    print('\n%-5s %-62s %-7s %-7s %s' % ('class', 'tag', 'chunks', 'backed', 'empty'))
    for cls, name, n, good, bad in sorted(rows, key=lambda r: r[1]):
        flag = '' if bad == 0 else '   <== %d chunk(s) with no page' % bad
        print('%-5s %-62s %-7d %-7d %d%s' % (cls, name[-62:], n, good, bad, flag))


if __name__ == '__main__':
    main()
