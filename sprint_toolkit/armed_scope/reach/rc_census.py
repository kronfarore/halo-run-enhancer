r"""READ-ONLY census for Reach Armed scoping. Opens E:\HaloBaselines maps in memory, never saves."""
import json, os, struct, sys, collections, time
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP
import reach_pools as rp
import enemy_count as ec

GAME = 'Halo Reach'
OUT = os.path.dirname(os.path.abspath(__file__))
BASE = r'E:\HaloBaselines\haloreach\maps'
MAPS = sys.argv[1:] or ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70', 'm70_bonus']
SEP = chr(92)


def graph_tree(m, ident, by_ident, depth=0):
    """modes -> classes -> types for one jmad + parents."""
    t = by_ident.get(ident)
    if not t or not t.get('base'):
        return None
    b = t['base']
    out = {'name': t['name'], 'modes': {}, 'flags': m.data[b + 0x10]}
    for mo in m.follow_all(b, [0x104], [0x30], 'all'):
        ml = m.resolve_stringid(m.u32(mo)) or hex(m.u32(mo))
        cls = {}
        for wc in m.follow_all(mo, [0xC], [0x38], 'all'):
            cl = m.resolve_stringid(m.u32(wc)) or hex(m.u32(wc))
            types = {}
            for wt in m.follow_all(wc, [0x8], [0x14], 'all'):
                tl = m.resolve_stringid(m.u32(wt)) or hex(m.u32(wt))
                sets = {}
                for s in m.follow_all(wt, [0x8], [0x48], 'all'):
                    sl = m.resolve_stringid(m.u32(s)) or hex(m.u32(s))
                    sets[sl] = m.i32(s + 0xC)
                types[tl] = sets
            cls[cl] = types
        out['modes'][ml] = cls
    out['mode_sids'] = [hex(m.u32(mo)) for mo in m.follow_all(b, [0x104], [0x30], 'all')]
    out['weapon_list'] = [(m.resolve_stringid(m.u32(e)), m.resolve_stringid(m.u32(e + 4)))
                          for e in m.follow_all(b, [0x140], [0x8], 'all')]
    out['variants'] = []
    for v in m.follow_all(b, [0x3C], [0x14], 'all'):
        out['variants'].append((m.resolve_stringid(m.u32(v)),
                                [(m.resolve_stringid(m.u32(a)), m.resolve_stringid(m.u32(a + 4)))
                                 for a in m.follow_all(v, [0x8], [0x8], 'all')]))
    pid = m.u32(b + 0xC)
    out['parent'] = graph_tree(m, pid, by_ident, depth + 1) if pid != 0xFFFFFFFF and depth < 6 else None
    return out


def main():
    for name in MAPS:
        T0 = time.time()
        path = os.path.join(BASE, name + '.map')
        print('open', name, flush=True)
        m = HP.open_map(path, GAME)
        print('opened', time.time() - T0, flush=True)
        rp.bind(m, GAME)
        scnr = HP._scnr_base(m)
        zb = rp.zone_base(m)
        sets = rp.zone_sets(m, zb)
        res = rp.tag_resources(m, zb)
        by_ident = {t['ident']: t for t in m.tags if t.get('ident') is not None}
        lay = HP._BETRAYAL[GAME]
        ts = HP._TS_LAYOUT[GAME]
        poff, pel = lay['palette']
        pal = m.follow_all(scnr, [poff], [pel], 'all')
        ids = [m.u32(e + lay['pal_id_at']) for e in pal]
        names = [HP._tag_name_by_id(m, i) if i != 0xFFFFFFFF else None for i in ids]
        units = HP._ts_units(m, GAME, scnr, lay, ts)
        print('units', len(units), time.time() - T0, flush=True)

        chars = []
        for ci, (i, n) in enumerate(zip(ids, names)):
            t = by_ident.get(i)
            rec = {'i': ci, 'name': n, 'species': ec.species(n) if n else None}
            if t and t.get('base'):
                c, uid, parents = t, 0xFFFFFFFF, []
                for _ in range(8):
                    parents.append(c['name'])
                    u = m.u32(c['base'] + 0x14 + 0xC)
                    if u != 0xFFFFFFFF and uid == 0xFFFFFFFF:
                        uid = u
                    p = m.u32(c['base'] + 0x4 + 0xC)
                    c = by_ident.get(p)
                    if not c or not c.get('base'):
                        break
                rec['parents'] = parents
                ut = by_ident.get(uid)
                rec['unit'] = ut['name'] if ut else None
                if ut and ut.get('base'):
                    hid = m.u32(ut['base'] + 0x64 + 0xC)
                    ht = by_ident.get(hid)
                    rec['model'] = ht['name'] if ht else None
                    if ht and ht.get('base'):
                        jid = m.u32(ht['base'] + 0x20 + 0xC)
                        jt = by_ident.get(jid)
                        rec['jmad'] = jt['name'] if jt else None
                        rec['jmad_id'] = jid
                w = rp.resident_in(m, sets, t['index'])
                rec['sets'] = [x for x in w if x.startswith('Scenario')]
                rec['global'] = any(x.startswith('Global') for x in w)
                if ut:
                    w2 = rp.resident_in(m, sets, ut['index'])
                    rec['bipd_sets'] = [x for x in w2 if x.startswith('Scenario')]
                    rec['bipd_global'] = any(x.startswith('Global') for x in w2)
            chars.append(rec)

        tal = collections.defaultdict(collections.Counter)
        refs, wrefs = collections.Counter(), collections.Counter()
        seen_cells = set()
        spawn_w = collections.defaultdict(collections.Counter)
        for u in units:
            c = u.get('char')
            nm = names[c] if c is not None and 0 <= c < len(names) else None
            sp = ec.species(nm) if nm else 'none'
            k = tal[sp]
            k['entries'] += 1
            k[u['kind']] += 1
            if u['protected']:
                k['protected'] += 1
            if u['kind'] == 'cell':
                cell = u['cell']
                if cell not in seen_cells:
                    seen_cells.add(cell)
                    refs[m.u32(cell + 0x14 + 4)] += 1
                    wrefs[m.u32(cell + 0x20 + 4)] += 1
            else:
                spawn_w[sp][struct.unpack_from('<h', m.data, u['weap_at'][0])[0]] += 1
        print('cells', len(seen_cells), time.time() - T0, flush=True)
        shared, sh_weap, cnt, multi = (collections.Counter() for _ in range(4))
        actors = collections.Counter()
        wdist = collections.defaultdict(collections.Counter)
        for cell in seen_cells:
            cts = m.follow_all(cell, [0x14], [0x10], 'all')
            idx = [struct.unpack_from('<h', m.data, ct + 0xC)[0] for ct in cts]
            sps = {ec.species(names[i] or '') for i in idx if 0 <= i < len(names)}
            for sp in sps:
                cnt[sp] += 1
                actors[sp] += struct.unpack_from('<h', m.data, cell + 0x10)[0]
                if refs[m.u32(cell + 0x14 + 4)] > 1:
                    shared[sp] += 1
                if wrefs[m.u32(cell + 0x20 + 4)] > 1:
                    sh_weap[sp] += 1
            ws = m.follow_all(cell, [0x20], [0x10], 'all')
            if len(ws) > 1:
                multi['cells_multi_weapon'] += 1
            if not ws:
                multi['cells_no_weapon_block'] += 1
            for w in ws:
                v = struct.unpack_from('<h', m.data, w + 0xC)[0]
                for sp in sps:
                    wdist[sp][v] += 1
        multi['cells'] = len(seen_cells)
        multi['distinct_ct_blocks'] = len(refs)
        multi['distinct_weapon_blocks'] = len(wrefs)
        print('wpal', time.time() - T0, flush=True)
        wl = HP._MAP_WEAPONS[GAME]
        wpal = m.follow_all(scnr, [wl['palette'][0]], [wl['palette'][1]], 'all')
        wnames, weaps = [], []
        for i, e in enumerate(wpal):
            ident = m.u32(e + wl['pal_id_at'])
            t = by_ident.get(ident)
            nm = t['name'] if t else None
            wnames.append(nm)
            r = {'i': i, 'name': nm}
            if t and t.get('base'):
                b = t['base']
                r['cls_3ac'] = m.resolve_stringid(m.u32(b + 0x3AC))
                r['name_3b0'] = m.resolve_stringid(m.u32(b + 0x3B0))
                r['cls_3e0'] = m.resolve_stringid(m.u32(b + 0x3E0))
                r['name_3e4'] = m.resolve_stringid(m.u32(b + 0x3E4))
                ch = rp.chain_of(m, zb, ident, res)
                tags = ch[0]
                hits = rp.resident_in(m, sets, tags[0])
                r['sets'] = [x for x in hits if x.startswith('Scenario')]
                r['global'] = any(x.startswith('Global') for x in hits)
                st, late = rp.status(m, sets, tags)
                r['status'] = st
                r['late_n'] = len(late)
                allok = None
                for ti in tags:
                    h = set(rp.resident_in(m, sets, ti))
                    if any(x.startswith('Global') for x in h) or not h:
                        continue
                    h = {x for x in h if x.startswith('Scenario')}
                    allok = h if allok is None else allok & h
                r['closure_sets'] = sorted(allok) if allok is not None else 'all'
                r['closure_n'] = len(tags)
            weaps.append(r)
        nscen = sum(1 for l, _ in sets if l.startswith('Scenario'))
        print('graphs', time.time() - T0, flush=True)
        graphs = {}
        for c in chars:
            jid = c.get('jmad_id')
            if jid and c.get('jmad') and c['jmad'] not in graphs:
                graphs[c['jmad']] = graph_tree(m, jid, by_ident)
        firing = {}
        for t in [t for t in m.tags if t.get('class') == 'char' and t.get('base')]:
            b = t['base']
            wp, fp = [], []
            for e in m.follow_all(b, [0x1EC], [0xC4], 'all'):
                d = m.u32(e + 0x4 + 0xC)
                tt = by_ident.get(d)
                wp.append(tt['name'] if tt else hex(d))
            for e in m.follow_all(b, [0x1F8], [0x1C], 'all'):
                d = m.u32(e + 0xC)
                tt = by_ident.get(d)
                fp.append(tt['name'] if tt else hex(d))
            par = by_ident.get(m.u32(b + 0x10))
            firing[t['name']] = {'wp': wp, 'fp': fp, 'parent': par['name'] if par else None}
        allweap = [t['name'] for t in m.tags if t.get('class') == 'weap']
        print('slack', time.time() - T0, flush=True)
        slack = []
        d = m.data
        for la, psz, fb in m.partitions:
            if fb is None or psz <= 0:
                slack.append(None)
                continue
            seg = bytes(d[fb:fb + psz])
            runs, i, n = [], 0, len(seg)
            while True:
                j = seg.find(b'\0' * 4096, i)
                if j < 0:
                    break
                k = j + 4096
                while k < n and seg[k] == 0:
                    k += 1
                runs.append(k - j)
                i = k
            slack.append({'size': psz, 'n4k': len(runs), 'total': sum(runs),
                          'max': max(runs) if runs else 0})
        rec = {'map': name, 'nscenario_sets': nscen, 'chars': chars,
               'units': {k: dict(v) for k, v in tal.items()},
               'cells_by_species': dict(cnt), 'actors_by_species': dict(actors),
               'cells_shared_ct': dict(shared), 'cells_shared_weapon': dict(sh_weap),
               'multi': dict(multi), 'weapon_palette': weaps,
               'weapon_dist': {k: {(wnames[w].rsplit(SEP, 1)[-1] if 0 <= w < len(wnames) and wnames[w]
                                    else str(w)): n for w, n in v.items()} for k, v in wdist.items()},
               'spawn_weapon': {k: {(wnames[w].rsplit(SEP, 1)[-1] if 0 <= w < len(wnames) and wnames[w]
                                     else str(w)): n for w, n in v.items()} for k, v in spawn_w.items()},
               'graphs': graphs, 'firing': firing, 'all_weap': allweap, 'slack': slack,
               'scnr_partition': next((i for i, (la, psz, fb) in enumerate(m.partitions)
                                       if fb is not None and fb <= scnr < fb + psz), None)}
        with open(os.path.join(OUT, 'rc_%s.json' % name), 'w', encoding='utf-8') as f:
            json.dump(rec, f, indent=0, default=str)
        print(name, 'done units', sum(v['entries'] for v in tal.values()), 'wpal', len(weaps),
              'chars', len(chars), 'sets', nscen, time.time() - T0, flush=True)
        del m


if __name__ == '__main__':
    main()
