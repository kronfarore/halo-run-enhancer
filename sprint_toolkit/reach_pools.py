# -*- coding: utf-8 -*-
r"""Reach zone-set residency: why a correctly-placed weapon or ability does not spawn.

A Reach mission starts in Scenario zone set 0. An object whose tag bit is clear in that
zone set's pool has no resident tag for the engine to build, so its placement is inert
however perfect the placement record is. Confirmed in-game on m10 2026-09-04: the energy
sword and plasma repeater were resident only from Scenario[2] -- the set where the
Elites who carry them appear -- and neither would spawn from any placement. Setting
their bits fixed both, at every lift tried, with no rebuild.

The pools are BIT ARRAYS, one bit per tag index (or per raw page index), NOT lists of
indices. Reading them as indices makes every object look absent, working ones included.

    python reach_pools.py m10                       # what is resident at mission start
    python reach_pools.py m10 --equipment
    python reach_pools.py --audit                   # every map, everything not resident
    python reach_pools.py m10 --fix energy_sword --fix plasma_repeater --write
    python reach_pools.py m10 --fix-all --write     # every palette entry, both kinds
"""
import argparse
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                            # noqa: E402

GAME = 'Halo Reach'
SEP = chr(92)

# zone tag: every zone-set block shares one 0xA0 element (ODST's is 0x78)
ZS_ELEM = 0xA0
ZS_BLOCKS = [('Designer', 0x70), ('Global', 0x7C), ('Unattached', 0x94),
             ('DiscForbid', 0xA0), ('DiscAlways', 0xAC), ('BSP', 0xB8),
             ('BSP2', 0xC4), ('BSP3', 0xD0), ('Cine', 0xDC), ('Scenario', 0xE8)]
RAW_POOLS = (('rawReq', 0x0), ('rawOpt', 0x18), ('rawOpt2', 0x24))
TAG_POOLS = (('tagReq', 0x6C), ('tagOpt', 0x78))
# the set a mission is in when it starts; membership here is what decides spawning
START_SET = 'Scenario[0]'

ZONE_TAG_RESOURCES = 0x64
ZTR_ELEM = 0x40
ZTR_SEGMENT = 0x22
ZONE_SEGMENTS = 0x58
ZONE_RAW_PAGES = 0x34
PLAY_SEGMENTS = 0x3C
PLAY_RAW_PAGES = 0x18
OBJE_MODEL = 0x64          # weap and eqip agree
HLMT_CHILDREN = (0x0, 0x10, 0x20, 0x30)     # mode, coll, jmad, phmo


def zone_base(m):
    zt = next((t for t in m.tags if t.get('class') == 'zone'), None)
    if not zt or not zt.get('base'):
        raise SystemExit('map has no zone tag')
    return zt['base']


def zone_sets(m, zb):
    out = []
    for label, off in ZS_BLOCKS:
        b, n = HP._block_base(m, zb + off), max(0, m.i32(zb + off))
        for k in range(n) if b else []:
            out.append(('%s[%d]' % (label, k), b + k * ZS_ELEM))
    return out


def _pool(m, elem, off):
    b, n = HP._block_base(m, elem + off), m.i32(elem + off)
    return (b, n * 4) if (b and n > 0) else (None, 0)


def getbit(m, b, size, i):
    byte = i >> 3
    return byte < size and bool(m.data[b + byte] & (1 << (i & 7)))


def setbit(m, b, size, i):
    byte = i >> 3
    if byte >= size:
        return False
    m.data[b + byte] |= (1 << (i & 7))
    return True


def resource_tables(m, zb):
    """(segments, pages) blocks, from whichever tag owns them.

    A SHIPPED map leaves them to the `play` tag and reaches into shared caches; an
    Editing Kit rebuild has an empty `play` tag and inlines everything into `zone`.
    Reading only one of the two makes every object on the other kind of map look as if
    it had no geometry at all.
    """
    pt = next((t for t in m.tags if t.get('class') == 'play'), None)
    if pt and pt.get('base'):
        pb = pt['base']
        n = m.i32(pb + PLAY_SEGMENTS)
        if n and n > 0:
            return (HP._block_base(m, pb + PLAY_SEGMENTS), n,
                    HP._block_base(m, pb + PLAY_RAW_PAGES),
                    max(0, m.i32(pb + PLAY_RAW_PAGES)))
    return (HP._block_base(m, zb + ZONE_SEGMENTS), max(0, m.i32(zb + ZONE_SEGMENTS)),
            HP._block_base(m, zb + ZONE_RAW_PAGES), max(0, m.i32(zb + ZONE_RAW_PAGES)))


def tag_resources(m, zb):
    """parent tag index -> [segment index]"""
    b = HP._block_base(m, zb + ZONE_TAG_RESOURCES)
    n = max(0, m.i32(zb + ZONE_TAG_RESOURCES))
    res = {}
    for i in range(n) if b else []:
        e = b + i * ZTR_ELEM
        res.setdefault(m.u32(e + 0xC) & 0xFFFF, []).append(
            struct.unpack_from('<h', m.data, e + ZTR_SEGMENT)[0])
    return res


def chain_of(m, zb, ident, res):
    """Every tag an object needs, plus the raw pages behind its model.

    Returns (tag indices, page indices), or None when the tag is not in this map.
    """
    t = next((x for x in m.tags if x.get('ident') == ident), None)
    if not t or not t.get('base'):
        return None
    tags = [t['index']]
    pages = set()
    mdl = m.u32(t['base'] + OBJE_MODEL + 0xC)
    mt = next((x for x in m.tags if x.get('ident') == mdl), None)
    if mt and mt.get('base'):
        tags.append(mt['index'])
        seg_b, seg_n, _pb, _pn = resource_tables(m, zb)
        for off in HLMT_CHILDREN:
            cid = m.u32(mt['base'] + off + 0xC)
            ct = next((x for x in m.tags if x.get('ident') == cid), None)
            if not ct:
                continue
            tags.append(ct['index'])
            for sg in res.get(cid & 0xFFFF, []):
                if seg_b and 0 <= sg < seg_n:
                    p, s = struct.unpack_from('<hh', m.data, seg_b + sg * 0x10)
                    for x in (p, s):
                        if x > 0:
                            pages.add(x)
    return tags, pages


def palette(m, scnr, kind):
    lay = (HP._MAP_WEAPONS if kind == 'weapons' else HP._MAP_EQUIPMENT)[GAME]
    off, es = lay['palette']
    b, n = HP._block_base(m, scnr + off), max(0, m.i32(scnr + off))
    out = []
    for i in range(n) if b else []:
        ident = m.u32(b + i * es + lay['pal_id_at'])
        nm = HP._tag_name_by_id(m, ident)
        if nm:
            out.append((str(nm).split(SEP)[-1], ident))
    return out


def resident_in(m, sets, tag_index):
    hits = []
    for label, elem in sets:
        for _, off in TAG_POOLS:
            b, size = _pool(m, elem, off)
            if b and getbit(m, b, size, tag_index):
                hits.append(label)
                break
    return hits


def survey(m, scnr, zb, sets, kinds, res):
    rows = []
    for kind in kinds:
        for nm, ident in palette(m, scnr, kind):
            ch = chain_of(m, zb, ident, res)
            if ch is None:
                rows.append((kind, nm, ident, None, [], set()))
                continue
            tags, pages = ch
            rows.append((kind, nm, ident, tags, resident_in(m, sets, tags[0]), pages))
    return rows


def apply_fix(m, zb, sets, res, target_ident, donor_tags, donor_pages):
    """Give a target the residency a donor already has. Returns bits written."""
    ch = chain_of(m, zb, target_ident, res)
    if ch is None:
        return 0
    ttags, tpages = ch
    n = 0
    for _label, elem in sets:
        for _, off in TAG_POOLS:
            b, size = _pool(m, elem, off)
            if not b or not getbit(m, b, size, donor_tags[0]):
                continue                       # donor not resident here either
            for ti in ttags:
                if not getbit(m, b, size, ti) and setbit(m, b, size, ti):
                    n += 1
        for _, off in RAW_POOLS:
            b, size = _pool(m, elem, off)
            if not b or not any(getbit(m, b, size, p) for p in donor_pages):
                continue
            for p in tpages:
                if not getbit(m, b, size, p) and setbit(m, b, size, p):
                    n += 1
    return n


def pick_donor(rows, kind):
    """A palette entry of the same kind that IS resident at mission start."""
    for k, nm, _ident, tags, hits, pages in rows:
        if k == kind and tags and START_SET in hits:
            return nm, tags, pages
    return None, None, None


def map_names():
    """The missions halo.json lists, in its own order.

    Globbing the map folder for m<digits> both invented work and skipped a mission:
    m05 and m70_a are HREK scenarios the game never runs, while m70_bonus was dropped
    because its name is not all digits -- so --audit quietly reported on nine of ten
    missions and looked complete.
    """
    import json
    tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(tool, 'halo.json'), encoding='utf-8') as f:
        return list(json.load(f)['Missions'][GAME])


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map', nargs='?', default='m10')
    ap.add_argument('--equipment', action='store_true', help='abilities instead of weapons')
    ap.add_argument('--both', action='store_true', help='weapons and abilities')
    ap.add_argument('--audit', action='store_true',
                    help='every campaign map: what is not resident at mission start')
    ap.add_argument('--fix', action='append', default=[], metavar='NAME')
    ap.add_argument('--fix-all', action='store_true',
                    help='every palette entry not resident at mission start')
    ap.add_argument('--donor', help='borrow residency from this palette entry')
    ap.add_argument('--write', action='store_true', help='save; otherwise a dry run')
    a = ap.parse_args(argv)

    kinds = ['weapons', 'equipment'] if (a.both or a.audit) else (
        ['equipment'] if a.equipment else ['weapons'])
    names = map_names() if a.audit else [a.map]

    for name in names:
        # Everything up to the scenario base is per-map and can fail per-map: --audit
        # walks every mission, so one unreadable map must not take the sweep down.
        # V.resolve returns None for a map that is not installed, and _scnr_base
        # RETURNS None for a map with no scnr tag rather than raising -- neither is an
        # exception, so neither is caught by an except alone.
        path = V.resolve(GAME, name)
        if not path:
            print('%-5s skipped (not installed)' % name)
            continue
        try:
            m = HP.open_map(path, GAME)
            scnr = HP._scnr_base(m)
        except Exception as ex:
            print('%-5s skipped (%s)' % (name, ex))
            continue
        if scnr is None:
            print('%-5s skipped (no scenario tag)' % name)
            continue
        zb = zone_base(m)
        sets = zone_sets(m, zb)
        res = tag_resources(m, zb)
        rows = survey(m, scnr, zb, sets, kinds, res)

        if a.audit:
            bad = [(k, nm) for k, nm, _i, tags, hits, _p in rows
                   if tags and START_SET not in hits]
            miss = [nm for _k, nm, _i, tags, _h, _p in rows if tags is None]
            print('%-5s %2d palette entries, %d NOT resident at start%s'
                  % (name, len(rows), len(bad),
                     (', %d tag missing' % len(miss)) if miss else ''))
            for k, nm in bad:
                print('        %-10s %s' % (k, nm))
            continue

        if not (a.fix or a.fix_all):
            print('%s: %d zone sets, %d tags' % (name, len(sets), len(m.tags)))
            print('%-10s %-26s %-9s %s' % ('kind', 'name', 'at start', 'resident in'))
            for k, nm, _i, tags, hits, _p in rows:
                if tags is None:
                    print('%-10s %-26s %-9s tag not in this map' % (k, nm, '-'))
                    continue
                print('%-10s %-26s %-9s %d set(s)'
                      % (k, nm, 'YES' if START_SET in hits else 'no', len(hits)))
            continue

        wanted = ([nm for _k, nm, _i, tags, hits, _p in rows
                   if tags and START_SET not in hits] if a.fix_all else list(a.fix))
        if not wanted:
            print('%s: nothing to fix' % name)
            continue
        total = 0
        for nm in wanted:
            row = next((r for r in rows if r[1] == nm), None)
            if row is None:
                print('  %-24s no palette entry' % nm)
                continue
            kind, _nm, ident, tags, _hits, _pages = row
            if tags is None:
                print('  %-24s tag not in this map' % nm)
                continue
            if a.donor:
                d = next((r for r in rows if r[1] == a.donor), None)
                dnm, dtags, dpages = (a.donor, d[3], d[5]) if d else (None, None, None)
            else:
                dnm, dtags, dpages = pick_donor(rows, kind)
            if not dtags:
                print('  %-24s no donor resident at start' % nm)
                continue
            n = apply_fix(m, zb, sets, res, ident, dtags, dpages)
            total += n
            print('  %-24s <- %-20s %4d bit(s)' % (nm, dnm, n))
        if a.write and total:
            m.save(path)
            print('%s: wrote %d bit(s)' % (path, total))
        elif total:
            print('dry run; pass --write to save (%d bit(s))' % total)
        else:
            print('nothing to write')


if __name__ == '__main__':
    main()
