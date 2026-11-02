"""Per level: units per species, weapon arrays, weapon palette, residency per zone set."""
from lib import *
import re, h4_census as hc, h4_pools as P
L = hp._BETRAYAL[GAME]; TS = hp._TS_LAYOUT[GAME]
WNAME = [(p.replace('/', S), n) for p, n in hc.WEAPONS]


def wcard(tag):
    t = str(tag or '')
    for p, n in WNAME:
        if p in t:
            return n
    return None


def sp(n):
    return ec.species(n) if n else None


out = {}
only = sys.argv[1:] or [a for a, _b in LEVELS]
for mid, title in LEVELS:
    if mid not in only:
        continue
    t0 = time.time()
    m = op(mid)
    scnr = hp._scnr_base(m)
    chars = palette(m, scnr, 0x444, 0x10, 0xC)
    weaps = palette(m, scnr, 0x1BC, 0x10, 0xC)
    R = {'title': title, 'chars': [leaf(c) for c in chars], 'weapons': [leaf(w) for w in weaps],
         'weap_paths': weaps}
    units = hp._ts_units(m, GAME, scnr, L, TS, None, chars)
    tally = collections.defaultdict(collections.Counter)
    for u in units:
        c = u['char']
        s = sp(chars[c]) if c is not None and 0 <= c < len(chars) else 'none'
        tally[s][u['kind'] + ('_prot' if u['protected'] else '')] += 1
    R['ts_units'] = {k: dict(v) for k, v in tally.items()}
    # own walk
    sq_tot = both = ptr_same = cont_same = 0
    arr = collections.Counter()
    per = collections.defaultdict(collections.Counter)
    wuse = collections.defaultdict(collections.Counter)
    defaults = collections.Counter()
    for sq in block(m, scnr + 0x3F0, 0x6C):
        sq_tot += 1
        d, t = block(m, sq + 0x54, 0x64), block(m, sq + 0x60, 0x64)
        if d and t:
            both += 1
            if m.u32(sq + 0x58) == m.u32(sq + 0x64):
                ptr_same += 1
            if len(d) == len(t) and all(bytes(m.data[a:a + 0x64]) == bytes(m.data[b:b + 0x64]) for a, b in zip(d, t)):
                cont_same += 1
        use = t or d
        for sp_ in block(m, sq + 0x3C, 0x7C):
            c, w, w2, v = i16(m, sp_ + 0x2E), i16(m, sp_ + 0x30), i16(m, sp_ + 0x32), i16(m, sp_ + 0x36)
            s = sp(chars[c]) if 0 <= c < len(chars) else 'inherit'
            per[s]['spawn'] += 1
            if v >= 0:
                per[s]['spawn_veh'] += 1
            if w < 0:
                per[s]['spawn_w-1'] += 1
            if w2 >= 0:
                per[s]['spawn_w2'] += 1
            if 0 <= w < len(weaps):
                wuse[s][leaf(weaps[w])] += 1
        for off, cells in ((0x54, d), (0x60, t)):
            for cell in cells:
                for fo in (0xC, 0x18, 0x24, 0x30):
                    if m.i32(cell + fo) > 0:
                        arr[(fo, m.u32(cell + fo + 4))] += 1
        for cell in use:
            cts = block(m, cell + 0xC, 8)
            w1 = block(m, cell + 0x18, 8)
            w2 = block(m, cell + 0x24, 8)
            cnt = i16(m, cell + 0x8)
            veh = i16(m, cell + 0x3E)
            cidx = [i16(m, x + 4) for x in cts]
            s = sp(chars[cidx[0]]) if cidx and 0 <= cidx[0] < len(chars) else 'nochar'
            per[s]['cell'] += 1
            per[s]['cell_count'] += max(0, cnt)
            if veh >= 0:
                per[s]['cell_veh'] += 1
            if not w1:
                per[s]['cell_noW1'] += 1
                per[s]['cell_noW1_count'] += max(0, cnt)
            for x in w1:
                wi = i16(m, x + 4)
                per[s]['cell_w' if wi >= 0 else 'cell_w-1'] += 1
                if 0 <= wi < len(weaps):
                    wuse[s][leaf(weaps[wi])] += max(1, cnt)
            if w2:
                per[s]['cell_W2'] += 1
    R['squads'] = sq_tot; R['both_cells'] = both; R['twin_ptr_same'] = ptr_same; R['twin_bytes_same'] = cont_same
    shared = collections.Counter()
    for (fo, p), n in arr.items():
        shared[(hex(fo), 'shared' if n > 1 else 'own')] += 1
    R['array_ptrs'] = {'%s %s' % k: v for k, v in shared.items()}
    R['array_max_users'] = {hex(fo): max([n for (f, p), n in arr.items() if f == fo] or [0]) for fo in (0xC, 0x18, 0x24, 0x30)}
    R['per'] = {k: dict(v) for k, v in per.items()}
    R['wuse'] = {k: v.most_common() for k, v in wuse.items()}
    # squad templates
    R['sqtm'] = len(list(m.find_tags('sqtm', '*')))
    R['sqtm_cells'] = None
    # placement + dz_enhancer
    R['placed'] = sorted(P.placed_names(m))
    try:
        it, why = hp.h4_enhancer_items(m, GAME, 'weapons')
    except Exception as e:
        it, why = None, repr(e)
    R['dz_items'] = sorted(leaf(x) for x in it) if it else None
    R['dz_why'] = why
    k = hp.h4_designer_zone(m)
    R['dz_index'] = k
    zb = P.zone_base(m)
    sets = P.zone_sets(m, zb)
    # scenario zone sets
    zn = max(0, m.i32(scnr + P.SCNR_ZONE_SETS))
    zsb = hp._block_base(m, scnr + P.SCNR_ZONE_SETS)
    R['zone_sets'] = zn
    dzon = 0
    live = []
    for j in range(zn):
        e = zsb + j * P.SCNR_ZS_ELEM
        nm = bytes(m.data[e + 4:e + 0x104]).split(b'\0')[0].decode('latin1')
        flags = m.u32(e + P.SCNR_DESIGNER_FLAGS) | struct.unpack_from('<Q', m.data, e + P.SCNR_DESIGNER_FLAGS + 4)[0]
        if k is not None and flags & (1 << k):
            dzon += 1
        live.append((nm, P.start_sets(m, j), bool(k is not None and flags & (1 << k))))
    R['dz_zone_sets_on'] = dzon
    R['zone_names'] = [(a, c) for a, b, c in live]
    by = dict(sets)
    masks = []
    for nm, labs, _z in live:
        ms = None
        for lab in labs:
            el = by.get(lab)
            if el is None:
                continue
            for off in P.TAG_POOLS:
                b, size = P._pool(m, el, off)
                if b:
                    v = int.from_bytes(bytes(m.data[b:b + size]), 'little')
                    ms = v if ms is None else ms | v
        masks.append(ms or 0)
    pool_any = 0
    for lab, el in sets:
        for off in P.TAG_POOLS:
            b, size = P._pool(m, el, off)
            if b:
                pool_any |= int.from_bytes(bytes(m.data[b:b + size]), 'little')
    clo = P.Closure(m, zb)
    by_name = {}
    for t in m.tags:
        by_name.setdefault((t.get('class'), t.get('name')), t)

    def nsets(ti):
        return sum(1 for x in masks if (x >> ti) & 1)
    res = {}
    allc = [t for t in m.tags if t.get('class') == 'weap']
    idents = {}
    for i, w in enumerate(weaps):
        if not w:
            continue
        t = by_name.get(('weap', w))
        if t is None:
            res[leaf(w)] = {'absent': True}
            continue
        tags, _pg = clo.of(t['ident'])
        track = [c['index'] for c in tags if (pool_any >> c['index']) & 1]
        mk = (1 << track[0]) if track else 0
        full = 0
        for j, x in enumerate(masks):
            if all((x >> ti) & 1 for ti in track):
                full += 1
        res[leaf(w)] = {'card': wcard(w), 'weap_sets': nsets(t['index']), 'full_sets': full,
                        'closure': len(tags), 'tracked': len(track),
                        'late_at_0': sum(1 for ti in track if not (masks[0] >> ti) & 1) if masks else None,
                        'weap_at0': bool((masks[0] >> t['index']) & 1) if masks else None}
    R['weap_res'] = res
    # character residency, species vs weapon gaps
    cres = {}
    bipd_of = {}
    cmask = {}
    for c in chars:
        if not c:
            continue
        ct = by_name.get(('char', c))
        if ct is None:
            continue
        u = ref(m, ct['base'] + 0x14)
        p = ref(m, ct['base'] + 0x4)
        bipd_of[leaf(c)] = (leaf(u), leaf(p))
        ut = by_name.get(('bipd', u))
        cm = [j for j, x in enumerate(masks) if (x >> ct['index']) & 1]
        bm = [j for j, x in enumerate(masks) if ut and (x >> ut['index']) & 1]
        cres[leaf(c)] = {'char_sets': len(cm), 'bipd_sets': len(bm), 'unit': leaf(u), 'parent': leaf(p)}
        cmask[leaf(c)] = bm or cm
    R['char_res'] = cres
    gaps = {}
    for w, r in res.items():
        t = by_name.get(('weap', next((x for x in weaps if leaf(x) == w), None)))
        if not t or not r.get('card'):
            continue
        tags, _pg = clo.of(t['ident'])
        track = [c['index'] for c in tags if (pool_any >> c['index']) & 1]
        for cn in ('storm_grunt', 'storm_jackal', 'storm_elite', 'storm_knight', 'storm_pawn', 'storm_bishop', 'storm_marine'):
            cs = cmask.get(cn)
            if cs is None:
                continue
            miss = [j for j in cs if not all((masks[j] >> ti) & 1 for ti in track)]
            if miss:
                gaps.setdefault(w, {})[cn] = len(miss)
    R['gaps'] = gaps
    R['char_sets_n'] = {k: len(v) for k, v in cmask.items()}
    # slack: >=0x1000 zero runs inside partitions
    runs = []
    for la, psz, fb in m.partitions:
        if fb is None or not psz or fb + psz > len(m.data):
            continue
        for mo in re.finditer(rb'\x00{4096,}', bytes(m.data[fb:fb + psz])):
            runs.append(mo.end() - mo.start())
    R['slack_runs'] = len(runs); R['slack_total'] = sum(runs); R['slack_max'] = max(runs or [0])
    R['secs'] = time.time() - t0
    with open(os.path.join(OUT, 'census_%s.json' % mid), 'w') as fh:
        json.dump(R, fh, indent=1, default=str)
    print(mid, 'ok', round(R['secs']))
    del m
