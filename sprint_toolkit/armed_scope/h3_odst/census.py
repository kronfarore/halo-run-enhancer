r"""READ-ONLY census for Armed cards in H3 / ODST. Reads E: baselines, never saves.
    python census.py "Halo 3" 010_jungle [...]  -> armed_scope/out/<map>.json"""
import contextlib, io, json, os, struct, sys, collections
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.chdir(TOOL)
import halo_patch as hp
import enemy_count as ec

ROOT = {'Halo 3': r'E:\HaloBaselines\halo3\maps', 'Halo 3: ODST': r'E:\HaloBaselines\halo3odst\maps'}
H3 = dict(props=(0x174, 0xE0), fpp=(0x180, 0x1C), wflags=0x18C, wclass=0x3DC, wname=0x3E0,
          dz=(0x6E4, 0xBC), zsets=(0x58, 0x28), teamoff=0xFC)
OD = dict(props=(0x198, 0xE0), fpp=(0x1A4, 0x1C), wflags=0x19C, wclass=0x3EC, wname=0x3F0,
          dz=(0x724, 0xC8), zsets=(0x74, 0x28), teamoff=0x10C)
BS = chr(92)


def sid(m, s):
    try:
        return m.resolve_stringid(s)
    except Exception:
        return '0x%08X' % s


def tname(m, ident):
    if ident in (0xFFFFFFFF, 0):
        return None
    return hp._tag_name_by_id(m, ident)


def graph(m, base):
    """{mode: {class: {type: n_actions}}} + weapon list + parent + inheritance."""
    out = {}
    for md in m.follow_all(base, [0x5C], [0x28], 'all'):
        ml = sid(m, m.u32(md))
        cls = out.setdefault(ml, {})
        for c in m.follow_all(md, [0x4], [0x1C], 'all'):
            cl = sid(m, m.u32(c))
            ty = cls.setdefault(cl, {})
            for t in m.follow_all(c, [0x4], [0x34], 'all'):
                tl = sid(m, m.u32(t))
                # Weapon Type: Actions +0x4 (8), Overlays +0x10 (?), Death/Dmg ... count only
                ty[tl] = {'actions': m.i32(t + 4), 'overlays': m.i32(t + 0x10),
                          'death': m.i32(t + 0x1C), 'trans': m.i32(t + 0x28)}
    wl = [(sid(m, m.u32(e)), sid(m, m.u32(e + 4))) for e in m.follow_all(base, [0x8C], [8], 'all')]
    inh = [tname(m, m.u32(e + 0xC)) for e in m.follow_all(base, [0x80], [0x30], 'all')]
    return {'modes': out, 'weapon_list': wl, 'parent': tname(m, m.u32(base + 0xC)), 'inherit': inh}


def run(game, name):
    L = H3 if game == 'Halo 3' else OD
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(os.path.join(ROOT[game], name + '.map'), game)
    R = {'map': name, 'game': game, 'size': len(m.data)}
    scnr = hp._scnr_base(m)
    lay, ts = hp._BETRAYAL[game], hp._TS_LAYOUT[game]
    poff, pel = lay['palette']
    pal = m.follow_all(scnr, [poff], [pel], 'all')
    ids = [m.u32(e + lay['pal_id_at']) for e in pal]
    names = [tname(m, i) for i in ids]
    R['char_palette'] = names
    friends, char_team = hp._player_friends(m, game, names, ids)
    R['friends'] = sorted(map(str, friends)); R['char_team'] = [str(x) for x in char_team]

    # weapon palette + placements
    w = hp._MAP_WEAPONS[game]
    wp = m.follow_all(scnr, [w['palette'][0]], [w['palette'][1]], 'all')
    wnames = [tname(m, m.u32(e + w['pal_id_at'])) for e in wp]
    R['weapon_palette'] = wnames
    place = collections.Counter()
    for e in m.follow_all(scnr, [w['weapons'][0]], [w['weapons'][1]], 'all'):
        place[struct.unpack_from('<h', m.data, e)[0]] += 1
    R['placements'] = {str(k): v for k, v in place.items()}

    # weap tags
    wt = {}
    for p, b in m.find_tags('weap', '*'):
        fl = m.u32(b + L['wflags'])
        wt[p] = {'class': sid(m, m.u32(b + L['wclass'])), 'name': sid(m, m.u32(b + L['wname'])),
                 'flags': fl, 'dual': bool(fl & (1 << 16)), 'dual_only': bool(fl & (1 << 17))}
    R['weap_tags'] = wt

    # chars: own props / fpp, parent, unit
    ch = {}
    for p, b in m.find_tags('char', '*'):
        pr = [tname(m, m.u32(e + 4 + 0xC)) for e in m.follow_all(b, [L['props'][0]], [L['props'][1]], 'all')]
        inner = [m.i32(e + 0xC4) for e in m.follow_all(b, [L['props'][0]], [L['props'][1]], 'all')]
        fp = [tname(m, m.u32(e + 0xC)) for e in m.follow_all(b, [L['fpp'][0]], [L['fpp'][1]], 'all')]
        ch[p] = {'props': pr, 'inner': inner, 'fpp': fp, 'parent': tname(m, m.u32(b + 0x4 + 0xC)),
                 'unit': tname(m, m.u32(b + 0x14 + 0xC))}
    R['chars'] = ch

    # graphs: character bipeds
    R['graphs'] = {}
    for p, b in m.find_tags('jmad', '*'):
        lo = p.lower()
        if 'characters' + BS in lo and BS + 'fp' not in lo:
            R['graphs'][p] = graph(m, b)

    # units
    units = hp._ts_units(m, game, scnr, lay, ts, None, names)
    rows = collections.defaultdict(lambda: collections.Counter())
    weaps = collections.defaultdict(collections.Counter)
    for u in units:
        c = u['char']
        cn = names[c] if c is not None and 0 <= c < len(names) else None
        k = cn or '?'
        r = rows[k]
        r['entries'] += 1
        r['kind_' + u['kind']] += 1
        if u['protected']:
            r['protected'] += 1
        if u['kind'] == 'cell':
            arr = u['weap_at']
            r['cell_noweap'] += 0 if arr else 1
            vs = [struct.unpack_from('<h', m.data, a)[0] for a in arr]
            for v in vs:
                weaps[k][wnames[v].rsplit(BS, 1)[-1] if 0 <= v < len(wnames) else str(v)] += 1
        else:
            v = struct.unpack_from('<h', m.data, u['weap_at'][0])[0]
            weaps[k][('%s:' % u['kind']) + (wnames[v].rsplit(BS, 1)[-1] if 0 <= v < len(wnames) else str(v))] += 1
    R['units'] = {k: dict(v) for k, v in rows.items()}
    R['unit_weapons'] = {k: dict(v) for k, v in weaps.items()}

    # counts + location char overrides
    if game == 'Halo 3':
        soff, sel = lay['squads']
        ftn = collections.Counter(); act = collections.Counter(); ftw = collections.Counter()
        locn = collections.Counter(); locw = collections.Counter(); locvar = collections.Counter()
        locown = collections.Counter(); ftchar = collections.Counter()
        for sq in m.follow_all(scnr, [soff], [sel], 'all'):
            for ft in m.follow_all(sq, [0x30], [0x60], 'all'):
                c = struct.unpack_from('<h', m.data, ft + 8)[0]
                n = struct.unpack_from('<h', m.data, ft + 4)[0]
                k = names[c] if 0 <= c < len(names) else None
                ftn[k or 'none'] += 1
                act[k or 'none'] += n
                fw = struct.unpack_from('<h', m.data, ft + 0xA)[0]
                ftw['weap>=0' if fw >= 0 else 'weap-1'] += 1
                for loc in m.follow_all(ft, [0x54], [0x88], 'all'):
                    lc = struct.unpack_from('<h', m.data, loc + 0x28)[0]
                    lw = struct.unpack_from('<h', m.data, loc + 0x2A)[0]
                    va = m.u32(loc + 0x38)
                    locn[k or 'none'] += 1
                    if lc >= 0:
                        locown['loc_own_char'] += 1
                    if lw >= 0:
                        locw[('own' if lc >= 0 else 'inh') + '_weap>=0'] += 1
                    else:
                        locw[('own' if lc >= 0 else 'inh') + '_weap-1'] += 1
                    if va:
                        lk = names[lc] if 0 <= lc < len(names) else k
                        locvar['%s|%s' % ((lk or '?').rsplit(BS, 1)[-1], sid(m, va))] += 1
        R['h3'] = dict(fireteams=dict(ftn), actors=dict(act), ft_weapon=dict(ftw), locs=dict(locn),
                       loc_weap=dict(locw), loc_own=dict(locown), loc_variants=dict(locvar))
    else:
        cells = {}
        refs = {'char': collections.defaultdict(set), 'w1': collections.defaultdict(set),
                'w2': collections.defaultdict(set)}
        soff, sel = lay['squads']
        sq_n = 0; spv = collections.Counter(); spw = collections.Counter(); spvar = collections.Counter()
        act = collections.Counter(); w1zero = collections.Counter(); w1multi = 0
        uniq = {}
        for sq in m.follow_all(scnr, [soff], [sel], 'all'):
            sq_n += 1
            for sp in m.follow_all(sq, [0x3C], [0x90], 'all'):
                c = struct.unpack_from('<h', m.data, sp + 0x32)[0]
                wv = struct.unpack_from('<h', m.data, sp + 0x34)[0]
                k = (names[c] if 0 <= c < len(names) else 'cellchar')
                spv[(k or '?')] += 1
                spw['weap>=0' if wv >= 0 else 'weap-1'] += 1
                va = m.u32(sp + 0x44)
                if va:
                    spvar['%s|%s' % ((k or '?').rsplit(BS, 1)[-1], sid(m, va))] += 1
            for off in (0x54, 0x60):
                for cell in m.follow_all(sq, [off], [0x84], 'all'):
                    uniq[cell] = uniq.get(cell, 0) + 1
                    chars = []
                    for ct in m.follow_all(cell, [0x14], [0x10], 'all'):
                        c = struct.unpack_from('<h', m.data, ct + 0xC)[0]
                        chars.append(names[c] if 0 <= c < len(names) else None)
                    n = m.i32(cell + 0x20)
                    if n == 0:
                        for x in set(chars):
                            w1zero[x or '?'] += 1
                    if n > 1:
                        w1multi += 1
                    for key, fo in (('char', 0x14), ('w1', 0x20), ('w2', 0x2C)):
                        if m.i32(cell + fo) > 0:
                            refs[key][m.u32(cell + fo + 4)].add(cell)
                    cells[cell] = chars
                    if off == 0x54 or True:
                        for x in set(chars):
                            pass
        # share stats per distinct cell element
        shr = {}
        for key in refs:
            blocks = refs[key]
            shared = sum(1 for v in blocks.values() if len(v) > 1)
            mixed = 0
            for v in blocks.values():
                sp_ = {ec.species(x) for c in v for x in cells[c] if x}
                if len(sp_) > 1:
                    mixed += 1
            shr[key] = dict(blocks=len(blocks), shared_blocks=shared, mixed_species=mixed,
                            max_users=max([len(v) for v in blocks.values()] or [0]),
                            cells_on_shared=sum(len(v) for v in blocks.values() if len(v) > 1))
        ccount = collections.Counter()
        for cell, chars in cells.items():
            n = struct.unpack_from('<h', m.data, cell + 0x10)[0]
            for x in set(chars):
                ccount[x or '?'] += n
        R['odst'] = dict(squads=sq_n, cell_elements=len(cells), cell_refs=sum(uniq.values()),
                         share=shr, spawns=dict(spv), spawn_weapon=dict(spw), spawn_variants=dict(spvar),
                         cell_actors=dict(ccount), cells_no_w1=dict(w1zero), cells_w1_multi=w1multi)

    # zones
    z = next((t for t in m.tags if t.get('class') == 'zone'), None)
    zb = z.get('base') if z else None
    R['zone'] = {}
    dzs = []
    for e in m.follow_all(scnr, [L['dz'][0]], [L['dz'][1]], 'all'):
        dzs.append(sid(m, m.u32(e)))
    R['zone']['designer_zones'] = dzs
    zs = []
    for e in m.follow_all(scnr, [L['zsets'][0]], [L['zsets'][1]], 'all'):
        zs.append((sid(m, m.u32(e)), m.u32(e + 0xC), m.u32(e + 0x10), m.u32(e + 0x14)))
    R['zone']['zone_sets'] = zs
    if zb:
        import h3_zone_pools as Z
        owned = Z.chunks_by_tag(m, zb)
        rowname = {t['index']: (t.get('class'), t.get('name')) for t in m.tags}
        # Designer Zone Manifests bits -> per weapon raw resources
        dzm = m.follow_all(zb, [0x70], [0x78], 'all')
        glob = m.follow_all(zb, [0x7C], [0x78], 'all')
        def bits(e):
            out = {}
            for lab, off in (('R', 0), ('D', 0xC), ('O', 0x18), ('S', 0x24)):
                b = hp._block_base(m, e + off)
                n = m.i32(e + off)
                out[lab] = [m.u32(b + i * 4) for i in range(n)] if b and n > 0 else []
            return out
        dzb = [bits(e) for e in dzm]
        gb = [bits(e) for e in glob]
        def inb(words, i):
            q, r = divmod(i, 32)
            return q < len(words) and bool(words[q] & (1 << r))
        # families for each weap tag: hlmt->mode, and jmad
        wres = {}
        for t in m.tags:
            if t.get('class') != 'weap' or not t.get('name'):
                continue
            b = t['base']
            hl = m.u32(b + 0x34 + 0xC)
            row = hl & 0xFFFF
            fam = {}
            hlname = rowname.get(row, (None, None))
            hb = next((x['base'] for x in m.tags if x['index'] == row), None)
            rows_ = {}
            if hb:
                for lab, off in (('mode', 0x0), ('coll', 0x10), ('jmad', 0x20), ('phmo', 0x30)):
                    r = m.u32(hb + off + 0xC)
                    if r != 0xFFFFFFFF:
                        rows_[lab] = r & 0xFFFF
            cell = {}
            for lab, r in rows_.items():
                chunks = owned.get(r, [])
                where = []
                for i, zb_ in enumerate(dzb):
                    for mode_, w_ in zb_.items():
                        if any(inb(w_, c) for c in chunks):
                            where.append('%d%s' % (i, mode_))
                g = []
                for zb_ in gb:
                    for mode_, w_ in zb_.items():
                        if any(inb(w_, c) for c in chunks):
                            g.append(mode_)
                cell[lab] = dict(chunks=len(chunks), dz=where, glob=g)
            wres[t['name']] = cell
        R['zone']['weap_res'] = wres
        R['zone']['n_dzm'] = len(dzm)
        R['zone']['n_global'] = len(glob)
    json.dump(R, open(os.path.join(OUT, name + '.json'), 'w'), indent=0)
    print(name, 'ok', len(units), 'units', flush=True)


if __name__ == '__main__':
    g = sys.argv[1]
    for n in sys.argv[2:]:
        run(g, n)
