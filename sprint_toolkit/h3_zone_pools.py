r"""Read the `zone` tag's zone-set pools. READING is useful; WRITING them does not work.

DEAD LEAD -- do not retry --load-always without a new idea about what the bits mean.
Two in-game attempts on sc150, both failures:
  --whole-donor (+2400 tags in GLOBAL) -> black screen after the intro cutscene
  narrow family fold (+79 tags, +60 raw chunks) -> FATAL ERROR on load
The narrow fold failing harder than the blunt one says the problem is not fold size;
it is that these bits do not mean what the plugin comment says, or that flipping them
without updating the `play` page/segment tables is inherently invalid.

The TAG pool's bit mapping is separately known to be unsound: the scenario tag, every
sbsp, and the brute biped have no bit set in any pool of any zone set, yet all of them
obviously load. sc150's shotgun likewise has no bit anywhere and is present at its
spawn in vanilla. Only the RAW chunk mapping is exact -- `Tag Resources` @0x64 names
each chunk's Parent Tag -- so chunks_by_tag() is trustworthy and the pool bits are not.

Which TAGS does each zone set claim to load? Read straight out of the `zone` tag.

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
ZS_OPTIONAL_TAG_POOL = 0x60      # reading Required alone is NOT enough -- sc150's
                                 # shotgun renders in vanilla with its Required bit
                                 # clear, so residency is Required OR Optional
ZS_REQUIRED_RAW_POOL = 0x0
ZS_OPTIONAL_RAW_POOL = 0x18
ZS_OPTIONAL_RAW_POOL2 = 0x24
TAG_POOLS = (('req', ZS_REQUIRED_TAG_POOL), ('opt', ZS_OPTIONAL_TAG_POOL))
RAW_POOLS = (('req', ZS_REQUIRED_RAW_POOL), ('opt', ZS_OPTIONAL_RAW_POOL),
             ('opt2', ZS_OPTIONAL_RAW_POOL2))


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


TAG_RESOURCES = 0x64             # zone tag's own chunk table; RAW pool bits index it
TR_ELEM = 0x40


def chunks_by_tag(m, zone_base):
    """{tag row: [chunk index]} from the zone tag's Tag Resources block.

    This mapping is exact -- every chunk names its Parent Tag -- unlike the TAG pool,
    whose bit-to-tag mapping is NOT established. Sanity checks fail on it: the
    scenario, every sbsp, and the brute biped have no bit set in any pool, yet all of
    them plainly load. Treat tag-pool readings as a lead, never as proof.
    """
    n = m.i32(zone_base + TAG_RESOURCES)
    base = HP._block_base(m, zone_base + TAG_RESOURCES)
    out = {}
    for i in range(max(0, n)) if base else []:
        out.setdefault(m.u32(base + i * TR_ELEM + 0xC) & 0xFFFF, []).append(i)
    return out


PLAY_SEGMENTS = 0x3C
PLAY_SEG_ELEM = 0x10


def _play_base(m):
    t = next((t for t in m.tags if t.get('class') == 'play'), None)
    return t['base'] if t else None


def unresolved_tags(m, zone_base):
    """Tag rows that own at least one chunk whose segment names no page.

    Marking such a tag resident tells the engine to load a chunk that has no bytes
    behind it. That is the difference between the run that worked and the runs that
    did not: the successful one left those tags alone.
    """
    # A map built standalone by the Editing Kit keeps Segments in the `zone` tag, not
    # `play`, so ask for whichever owns them -- otherwise every tag looks unresolved
    # and --only-resolved would refuse to mark anything resident.
    import h3_raw_residency as _R
    sbase, scount = _R.resource_tables(m)['seg']
    n = m.i32(zone_base + TAG_RESOURCES)
    base = HP._block_base(m, zone_base + TAG_RESOURCES)
    bad = set()
    for i in range(max(0, n)) if base else []:
        e = base + i * TR_ELEM
        seg = struct.unpack_from('<h', m.data, e + 0x22)[0]
        ok = False
        if sbase and 0 <= seg < scount:
            p, s = struct.unpack_from('<hh', m.data, sbase + seg * PLAY_SEG_ELEM)
            ok = p >= 0 or s >= 0
        if not ok:
            bad.add(m.u32(e + 0xC) & 0xFFFF)
    return bad


def load_always(m, zone_base, want, whole_donor=False, only_resolved=False,
                classes=None, cls='weap'):
    """Try to make `want` resident everywhere by setting its bits in GLOBAL.

    Default is a NARROW fold: only the weapon's own tag family (every tag whose path
    contains the weapon's basename -- Bungie files a weapon's model, animations,
    first-person set, projectile, sounds and shaders under its own folder) plus
    exactly the raw chunks those tags own.

    `whole_donor` is the original blunt version, which ORed an entire donor zone set
    in. On sc150 that added 2400 tags and left the map on a black screen after the
    intro, so the size of the fold is implicated: the narrow one adds ~90.

    NOTE the semantics here are NOT confirmed. The tag pool's bit mapping does not
    survive sanity checks, so a failure of this function is as likely to mean "wrong
    table" as "not enough bits".
    """
    sets = zonesets(m, zone_base)
    labels = [lab for lab, _ in sets]
    gi = next((i for i, lab in enumerate(labels) if lab.startswith('GLOBAL')), None)
    if gi is None:
        return {'ok': False, 'reason': 'no GLOBAL zone set'}
    # `cls` because equipment needs exactly the same treatment as weapons: an eqip tag
    # whose residency bit is clear is refused by object_new just the same, which is why
    # a prepared map would place grenades and nothing else.
    row = next((t['index'] for t in m.tags
                if t.get('class') == cls and t.get('name')
                and str(t['name']).rsplit('\\', 1)[-1].lower() == want.lower()), None)
    if row is None:
        return {'ok': False, 'reason': '%s has no %s tag in this map' % (want, cls)}
    gelem = sets[gi][1]

    if whole_donor:
        pools = [_pool(m, e, ZS_REQUIRED_TAG_POOL) for _, e in sets]
        donors = [i for i, w in enumerate(pools) if i != gi and _has(w, row)]
        if not donors:
            return {'ok': False, 'weapon': want, 'reason': 'no donor zone set'}
        added_t = added_r = 0
        for src in donors:
            for off in (ZS_REQUIRED_TAG_POOL, ZS_REQUIRED_RAW_POOL):
                dst, donor = _pool(m, gelem, off), _pool(m, sets[src][1], off)
                if not dst or not donor:
                    continue
                n = min(len(dst), len(donor))
                gained = sum(bin(donor[i] & ~dst[i]).count('1') for i in range(n))
                for i in range(n):
                    dst[i] |= donor[i]
                _write_pool(m, gelem, off, dst[:n])
                added_t += gained if off == ZS_REQUIRED_TAG_POOL else 0
                added_r += gained if off == ZS_REQUIRED_RAW_POOL else 0
        return {'ok': True, 'weapon': want, 'mode': 'whole-donor',
                'donors': [labels[i] for i in donors],
                'tags_added': added_t, 'raw_added': added_r}

    family = [t['index'] for t in m.tags
              if t.get('name') and want.lower() in str(t['name']).lower()
              and (not classes or (t.get('class') or '').strip() in classes)]
    dropped = 0
    if only_resolved:
        bad = unresolved_tags(m, zone_base)
        before = len(family)
        family = [r for r in family if r not in bad]
        dropped = before - len(family)
    owned = chunks_by_tag(m, zone_base)
    chunk_ids = [c for r in family for c in owned.get(r, [])]

    tags = _pool(m, gelem, ZS_REQUIRED_TAG_POOL)
    raws = _pool(m, gelem, ZS_REQUIRED_RAW_POOL)
    added_t = added_r = 0
    for r in family:
        w, b = divmod(r, 32)
        if w < len(tags) and not (tags[w] & (1 << b)):
            tags[w] |= 1 << b
            added_t += 1
    for c in chunk_ids:
        w, b = divmod(c, 32)
        if w < len(raws) and not (raws[w] & (1 << b)):
            raws[w] |= 1 << b
            added_r += 1
    _write_pool(m, gelem, ZS_REQUIRED_TAG_POOL, tags)
    _write_pool(m, gelem, ZS_REQUIRED_RAW_POOL, raws)
    return {'ok': True, 'weapon': want, 'mode': 'narrow', 'family': len(family),
            'left_unresolved': dropped, 'chunks': len(chunk_ids),
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
                         'is resident everywhere. Repeatable. Writes the map. '
                         'KNOWN BROKEN -- see the module docstring; needs --i-know.')
    ap.add_argument('--all-weapons', action='store_true',
                    help='mark EVERY weapon in the scenario palette resident, so any '
                         'of them can be granted or placed. Only sound on a rebuilt '
                         'map, where every chunk resolves.')
    ap.add_argument('--classes', help='comma list of tag classes to fold, e.g. '
                    'weap,hlmt,mode,coll,phmo,jmad,proj -- folding a whole weapon '
                    'family black-screened the map, so bisect with this')
    ap.add_argument('--i-know', action='store_true',
                    help='acknowledge that --load-always has failed in-game twice')
    ap.add_argument('--only-resolved', action='store_true',
                    help='do not mark resident any tag that owns a chunk with no page '
                         'behind it -- the engine would try to load nothing')
    ap.add_argument('--whole-donor', action='store_true',
                    help='the blunt fold: OR an entire donor zone set into GLOBAL. On '
                         'sc150 this black-screened the map after the intro.')
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
    if a.all_weapons:
        lay = HP._MAP_WEAPONS[a.game]
        scnr = HP._scnr_base(m)
        poff, pes = lay['palette']
        pc = max(0, m.i32(scnr + poff))
        pbase = HP._block_base(m, scnr + poff)
        for i in range(pc):
            nm = HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
            if nm:
                a.load_always.append(str(nm).rsplit('\\', 1)[-1])
        print('  palette gives %d weapon(s)' % pc)

    if a.load_always:
        if a.bak:
            raise SystemExit('refusing to write the .bak baseline; drop --bak')
        if not a.i_know:
            raise SystemExit(
                '--load-always has failed in-game twice (black screen, then a fatal\n'
                'error on load). The zone-set bits do not mean what they appear to.\n'
                'Read the module docstring; pass --i-know to try anyway.')
        for want in a.load_always:
            r = load_always(m, zb, want, whole_donor=a.whole_donor,
                            only_resolved=a.only_resolved,
                            classes=set(a.classes.split(',')) if a.classes else None)
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
