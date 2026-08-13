r"""Are a tag's raw resource BYTES actually in this map, or only referenced?

This decides whether the Kikowani starting-weapon problem is worth attacking in the
binary at all. If the rocket launcher's geometry and animation pages physically live
in sc150.map (or in an always-loaded shared cache), then everything blocking it is
bookkeeping -- a residency check the engine makes -- and defeating that check yields a
real, working weapon. If the pages are simply not there, no patch to the executable
can conjure them and the whole line is pointless.

The chain, all from the `zone` and `play` tags:

    zone Tag Resources @0x64 (elem 0x40)  -- Parent Tag @0xC, [play] Segment Index @0x22
    play Segments      @0x3C (elem 0x10)  -- Primary/Secondary Page Index, Size Index
    play Raw Pages     @0x18 (elem 0x58)  -- Shared Cache Index, Block Offset,
                                             Compressed/Uncompressed Block Size
    play External Cache References @0xC   -- which shared map a page index refers to

A page with Shared Cache Index -1 lives in this map's own raw table; otherwise it
lives in the named external cache.

    python h3_raw_residency.py sc150 --weapon rocket_launcher
    python h3_raw_residency.py sc150 --weapon rocket_launcher --weapon assault_rifle
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_zone_pools as Z                                        # noqa: E402

MAPS = Z.MAPS

ZONE_TAG_RESOURCES = 0x64
ZTR_ELEM = 0x40
ZTR_PARENT_ID = 0xC
ZTR_SEGMENT = 0x22

PLAY_EXTERNAL = 0xC
PLAY_EXT_ELEM = 0x108
PLAY_RAW_PAGES = 0x18
PLAY_PAGE_ELEM = 0x58
PLAY_SEGMENTS = 0x3C
PLAY_SEG_ELEM = 0x10


def _play_tag(m):
    return next((t for t in m.tags if t.get('class') == 'play'), None)


# The zone tag carries the same two blocks as the play tag. A shipped map leaves them
# to `play` and reaches into shared.map / campaign.map; a map built standalone by the
# Editing Kit has an EMPTY play tag and keeps everything in `zone` instead, inlined.
ZONE_RAW_PAGES = 0x34
ZONE_SEGMENTS = 0x58


def resource_tables(m):
    """(base, count) of the Segments and Raw Pages blocks, whichever tag owns them.

    Returns {'seg': (base, count), 'page': (base, count), 'owner': 'play'|'zone'}.
    """
    pt = _play_tag(m)
    if pt and pt.get('base'):
        pb = pt['base']
        return {'owner': 'play',
                'seg': (HP._block_base(m, pb + PLAY_SEGMENTS), m.i32(pb + PLAY_SEGMENTS)),
                'page': (HP._block_base(m, pb + PLAY_RAW_PAGES),
                         m.i32(pb + PLAY_RAW_PAGES))}
    zt = next((t for t in m.tags if t.get('class') == 'zone'), None)
    if not zt or not zt.get('base'):
        return {'owner': None, 'seg': (None, 0), 'page': (None, 0)}
    zb = zt['base']
    return {'owner': 'zone',
            'seg': (HP._block_base(m, zb + ZONE_SEGMENTS), m.i32(zb + ZONE_SEGMENTS)),
            'page': (HP._block_base(m, zb + ZONE_RAW_PAGES),
                     m.i32(zb + ZONE_RAW_PAGES))}


def externals(m, pb):
    n, base = m.i32(pb + PLAY_EXTERNAL), HP._block_base(m, pb + PLAY_EXTERNAL)
    out = []
    for i in range(max(0, n)) if base else []:
        raw = bytes(m.data[base + i * PLAY_EXT_ELEM:base + i * PLAY_EXT_ELEM + 0x100])
        out.append(raw.split(b'\0')[0].decode('latin-1'))
    return out


def page(m, pb, index):
    n, base = m.i32(pb + PLAY_RAW_PAGES), HP._block_base(m, pb + PLAY_RAW_PAGES)
    if not base or not (0 <= index < n):
        return None
    e = base + index * PLAY_PAGE_ELEM
    shared = struct.unpack_from('<h', m.data, e + 0x4)[0]
    off, comp, uncomp = struct.unpack_from('<III', m.data, e + 0x8)
    return {'index': index, 'shared': shared, 'offset': off,
            'compressed': comp, 'uncompressed': uncomp}


def segment(m, pb, index):
    n, base = m.i32(pb + PLAY_SEGMENTS), HP._block_base(m, pb + PLAY_SEGMENTS)
    if not base or not (0 <= index < n):
        return None
    e = base + index * PLAY_SEG_ELEM
    p, s = struct.unpack_from('<hh', m.data, e)
    return {'primary': p, 'secondary': s}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('--game', default='Halo 3: ODST', choices=sorted(MAPS))
    ap.add_argument('--bak', action='store_true')
    ap.add_argument('--weapon', action='append', default=[],
                    help='weapon basename; repeatable. Matches the whole tag family.')
    ap.add_argument('--survey', action='store_true',
                    help='every weapon in the map palette: does its render model and '
                         'first-person animation resolve to a real page?')
    a = ap.parse_args(argv)

    path = os.path.join(MAPS[a.game], a.map + '.map')
    if a.bak and os.path.isfile(path + '.bak'):
        path += '.bak'
    m = HP.open_map(path, a.game)
    zt, pt = Z._zone_tag(m), _play_tag(m)
    if not zt or not pt:
        raise SystemExit('need both a zone and a play tag')
    zb, pb = zt['base'], pt['base']
    ext = externals(m, pb)
    print('%s: %d byte(s) on disk' % (os.path.basename(path), len(m.data)))
    print('external caches: %s' % (', '.join(ext) or '(none)'))

    n = m.i32(zb + ZONE_TAG_RESOURCES)
    base = HP._block_base(m, zb + ZONE_TAG_RESOURCES)
    chunks = {}
    for i in range(max(0, n)) if base else []:
        e = base + i * ZTR_ELEM
        chunks.setdefault(m.u32(e + ZTR_PARENT_ID) & 0xFFFF, []).append(
            (i, struct.unpack_from('<h', m.data, e + ZTR_SEGMENT)[0]))

    if a.survey:
        lay = HP._MAP_WEAPONS[a.game]
        scnr = HP._scnr_base(m)
        poff, pes = lay['palette']
        pc = max(0, m.i32(scnr + poff))
        pbase = HP._block_base(m, scnr + poff)
        print('\n%-26s  model  fp-anim   (X = pages resolve, . = no page at all)'
              % 'weapon')
        for i in range(pc):
            nm = HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
            if not nm:
                continue
            short = str(nm).rsplit('\\', 1)[-1]
            got = {}
            for t in m.tags:
                tn = (t.get('name') or '')
                if short.lower() not in tn.lower():
                    continue
                first = 'fp_' in tn
                if t['class'] not in ('mode', 'jmad'):
                    continue
                for ci, seg_i in chunks.get(t['index'], []):
                    seg = segment(m, pb, seg_i)
                    ok = bool(seg and (seg['primary'] >= 0 or seg['secondary'] >= 0))
                    key = 'fp' if first else 'model'
                    got[key] = got.get(key, False) or ok
            print('  %-26s %-6s %-6s' % (short,
                                         'X' if got.get('model') else '.',
                                         'X' if got.get('fp') else '.'))
        return 0

    for want in a.weapon:
        fam = [t for t in m.tags
               if t.get('name') and want.lower() in str(t['name']).lower()]
        own, here, elsewhere, missing, bytes_here = 0, 0, 0, 0, 0
        print('\n%s: %d tag(s) in the family' % (want, len(fam)))
        for t in sorted(fam, key=lambda x: x['name'] or ''):
            for ci, seg_i in chunks.get(t['index'], []):
                own += 1
                seg = segment(m, pb, seg_i)
                if not seg:
                    missing += 1
                    continue
                for which in ('primary', 'secondary'):
                    pi = seg[which]
                    if pi < 0:
                        continue
                    pg = page(m, pb, pi)
                    if not pg:
                        missing += 1
                        continue
                    if pg['shared'] < 0:
                        here += 1
                        bytes_here += pg['compressed']
                    else:
                        elsewhere += 1
        if not own:
            print('  no raw chunks at all -- this family is pure tag data')
            continue
        print('  %d chunk(s): %d page ref(s) in THIS map (%.1f MB compressed), '
              '%d in a shared cache, %d unresolved'
              % (own, here, bytes_here / 1048576.0, elsewhere, missing))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
