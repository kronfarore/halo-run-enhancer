r"""Which TAGS does each zone set actually load? Read straight out of the `zone` tag.

The Kikowani starting-weapon wall kept coming back to streaming, but every earlier
argument about it was inference from placements. This reads the authority. The `zone`
tag (cache file resource gestalt) carries a `Designer Zonesets` block, and each zone
set holds a `Required Tag Pool`: a bit array over the map's whole tag listing, one bit
per tag, set when that tag is loaded for that zone set. So "can this level put a
rocket launcher in the player's hands at load" is a bit lookup, not a playtest.

    python h3_zone_pools.py sc150 --weapons
    python h3_zone_pools.py sc150 --tag rocket_launcher
    python h3_zone_pools.py sc150 --sets            # sizes and names only
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402

MAPS = {
    'Halo 3: ODST': (r"C:\Program Files (x86)\Steam\steamapps\common"
                     r"\Halo The Master Chief Collection\halo3odst\maps"),
    'Halo 3': (r"C:\Program Files (x86)\Steam\steamapps\common"
               r"\Halo The Master Chief Collection\halo3\maps"),
}

# zone tag: the zone-set blocks all share one 0x78 element layout.
DESIGNER_ZONESETS = 0x70
GLOBAL_ZONESET = 0x7C
UNATTACHED_ZONESET = 0x94
ZS_ELEM = 0x78
ZS_NAME = 0x44
ZS_REQUIRED_TAG_POOL = 0x54      # tagblock of 4-byte words, one bit per tag
ZS_REQUIRED_RAW_POOL = 0x0


def _zone_tag(m):
    for t in m.tags:
        if t.get('class') == 'zone':
            return t
    return None


def _pool(m, elem, off):
    """The bit array at `off` in a zone-set element, as a list of 32-bit words."""
    n = m.i32(elem + off)
    base = HP._block_base(m, elem + off)
    if not base or n <= 0:
        return []
    return [m.u32(base + i * 4) for i in range(n)]


def _has(words, index):
    w, b = divmod(index, 32)
    return w < len(words) and bool(words[w] & (1 << b))


def zonesets(m, zone_base):
    """(label, element offset) for every zone set in the tag, designer sets first."""
    out = []
    n = m.i32(zone_base + DESIGNER_ZONESETS)
    base = HP._block_base(m, zone_base + DESIGNER_ZONESETS)
    for i in range(max(0, n)) if base else []:
        e = base + i * ZS_ELEM
        sid = m.u32(e + ZS_NAME)
        name = None
        try:
            name = m.resolve_stringid(sid)
        except Exception:
            pass
        out.append(('designer[%d] %s' % (i, name or '0x%08X' % sid), e))
    for label, off in (('GLOBAL', GLOBAL_ZONESET), ('UNATTACHED', UNATTACHED_ZONESET)):
        n = m.i32(zone_base + off)
        base = HP._block_base(m, zone_base + off)
        for i in range(max(0, n)) if base else []:
            out.append(('%s[%d]' % (label, i), base + i * ZS_ELEM))
    return out


def _write_pool(m, elem, off, words):
    base = HP._block_base(m, elem + off)
    for i, w in enumerate(words):
        struct.pack_into('<I', m.data, base + i * 4, w)


def load_always(m, zone_base, want):
    """Make `want` resident for the whole level by folding a zone set that already
    carries it into GLOBAL.

    GLOBAL is the set the engine keeps loaded everywhere, and on sc150 it holds
    exactly three player weapons -- assault_rifle, smg_silenced, automag -- which is
    exactly the set that can be granted as a starting weapon. Everything else lives
    in a designer set (loaded only in its part of the level) or in UNATTACHED.

    A weapon needs its whole tag family, not just the `weap` tag, so rather than try
    to compute a dependency closure this ORs in the ENTIRE zone set that carries it:
    that set already contains every tag and every raw chunk the weapon needs, because
    the level streams it successfully somewhere. Blunt, but complete and verifiable.

    Returns a report dict.
    """
    sets = zonesets(m, zone_base)
    labels = [lab for lab, _ in sets]
    gi = next((i for i, lab in enumerate(labels) if lab.startswith('GLOBAL')), None)
    if gi is None:
        return {'ok': False, 'reason': 'no GLOBAL zone set'}
    row = next((t['index'] for t in m.tags
                if t.get('class') == 'weap' and t.get('name')
                and str(t['name']).rsplit('\\', 1)[-1].lower() == want.lower()), None)
    if row is None:
        return {'ok': False, 'reason': '%s has no weap tag in this map' % want}

    pools = [_pool(m, e, ZS_REQUIRED_TAG_POOL) for _, e in sets]
    if _has(pools[gi], row):
        return {'ok': True, 'reason': 'already in GLOBAL', 'weapon': want, 'row': row}
    donors = [i for i, w in enumerate(pools) if i != gi and _has(w, row)]
    if not donors:
        return {'ok': False, 'weapon': want, 'row': row,
                'reason': 'in NO zone set at all -- its resources are not in this map, '
                          'so it cannot be loaded here by any bit flip'}

    gelem = sets[gi][1]
    added_t = added_r = 0
    for src in donors:
        selem = sets[src][1]
        for off in (ZS_REQUIRED_TAG_POOL, ZS_REQUIRED_RAW_POOL):
            dst = _pool(m, gelem, off)
            donor = _pool(m, selem, off)
            if not dst or not donor:
                continue
            n = min(len(dst), len(donor))
            gained = 0
            for i in range(n):
                merged = dst[i] | donor[i]
                gained += bin(merged & ~dst[i]).count('1')
                dst[i] = merged
            _write_pool(m, gelem, off, dst[:n])
            if off == ZS_REQUIRED_TAG_POOL:
                added_t += gained
            else:
                added_r += gained
    return {'ok': True, 'weapon': want, 'row': row,
            'donors': [labels[i] for i in donors],
            'tags_added': added_t, 'raw_added': added_r}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('--game', default='Halo 3: ODST', choices=sorted(MAPS))
    ap.add_argument('--bak', action='store_true', help='read the vanilla .map.bak')
    ap.add_argument('--weapons', action='store_true',
                    help='every weap tag, and which zone sets require it')
    ap.add_argument('--tag', help='substring: report this tag across all zone sets')
    ap.add_argument('--sets', action='store_true', help='just the zone-set inventory')
    ap.add_argument('--load-always', metavar='WEAPON', action='append', default=[],
                    help='fold a zone set that carries this weapon into GLOBAL, so it '
                         'is resident everywhere. Repeatable. Writes the map.')
    a = ap.parse_args(argv)

    path = os.path.join(MAPS[a.game], a.map + '.map')
    if a.bak and os.path.isfile(path + '.bak'):
        path += '.bak'
    m = HP.open_map(path, a.game)
    zt = _zone_tag(m)
    if not zt:
        raise SystemExit('no zone tag in %s' % a.map)
    zb = zt['base']
    sets = zonesets(m, zb)
    pools = [(label, _pool(m, e, ZS_REQUIRED_TAG_POOL)) for label, e in sets]
    print('%s: %d tags, %d zone set(s)' % (a.map, len(m.tags), len(sets)))
    for (label, e), (_, words) in zip(sets, pools):
        raw = _pool(m, e, ZS_REQUIRED_RAW_POOL)
        tags_on = sum(bin(w).count('1') for w in words)
        raw_on = sum(bin(w).count('1') for w in raw)
        print('  %-34s tags=%4d/%-5d raw=%4d' % (label, tags_on, len(words) * 32, raw_on))
    if a.load_always:
        if a.bak:
            raise SystemExit('refusing to write the .bak baseline; drop --bak')
        for want in a.load_always:
            r = load_always(m, zb, want)
            print('  load-always %-18s %s' % (want, r))
        m.save(path)
        after = [(lab, _pool(m, e, ZS_REQUIRED_TAG_POOL)) for lab, e in zonesets(m, zb)]
        for lab, w in after:
            if lab.startswith('GLOBAL'):
                print('  GLOBAL now loads %d tag(s)' % sum(bin(x).count('1') for x in w))
        print('  saved %s' % path)
        return 0
    if a.sets:
        return 0

    def report(t):
        marks = ''.join('X' if _has(w, t['index']) else '.' for _, w in pools)
        print('  %-4s %-52s row %5d  %s'
              % (t['class'], (t['name'] or '')[-52:], t['index'], marks))

    print('\n  columns, in order: %s' % ', '.join(label for label, _ in pools))
    if a.weapons:
        print('\nweap tags:')
        for t in sorted(m.tags, key=lambda x: x['name'] or ''):
            if t['class'] == 'weap':
                report(t)
    if a.tag:
        need = a.tag.lower()
        print('\ntags matching %r:' % a.tag)
        for t in sorted(m.tags, key=lambda x: (x['class'] or '', x['name'] or '')):
            if need in (t['name'] or '').lower():
                report(t)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
