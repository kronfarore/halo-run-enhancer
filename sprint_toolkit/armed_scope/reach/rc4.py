r"""READ-ONLY fourth pass: bits a weapon->species residency fix would need (counted, nothing written),
hlmt variant children (shield), who spawns with what. Never saves, never mutates m.data."""
import os, struct, sys, collections
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP
import reach_pools as rp
import assembly_plugins, tagrefs
GAME = 'Halo Reach'
S = chr(92)
leaf = lambda n: n.rsplit(S, 1)[-1] if n else n
name = sys.argv[1]
m = HP.open_map(r'E:\HaloBaselines\haloreach\maps\%s.map' % name, GAME)
rp.bind(m, GAME)
by = {t['ident']: t for t in m.tags if t.get('ident') is not None}
pd = assembly_plugins.plugins_dir()
spec_h = tagrefs._spec(pd, 'ReachMCC', 'hlmt') or tagrefs._spec(pd, 'Reach', 'hlmt')
for t in m.tags:
    if t.get('class') == 'hlmt' and t['name'].lower().endswith(S + 'jackal'):
        for path, d in tagrefs.refs_of(m, t['base'], spec_h):
            x = by.get(d)
            if x and x['class'] == 'weap':
                print('hlmt jackal ref', path, x['name'])
scnr = HP._scnr_base(m)
zb = rp.zone_base(m)
sets = rp.zone_sets(m, zb)
res = rp.tag_resources(m, zb)
scen = [(l, e) for l, e in sets if l.startswith('Scenario')]
# weapon palette
wp = m.follow_all(scnr, [0x168], [0x10], 'all')
pal = m.follow_all(scnr, [0x3EC], [0x10], 'all')
names = [HP._tag_name_by_id(m, m.u32(e + 0xC)) for e in pal]
ids = [m.u32(e + 0xC) for e in pal]
# species sets: grunt
def sets_of(ident):
    t = by.get(ident)
    c, uid = t, 0xFFFFFFFF
    for _ in range(8):
        u = m.u32(c['base'] + 0x14 + 0xC)
        if u != 0xFFFFFFFF:
            uid = u
            break
        c = by.get(m.u32(c['base'] + 0x4 + 0xC))
        if not c or not c.get('base'):
            break
    return uid
tot = {}
for key in ('grunt', 'jackal', 'elite', 'marine', 'brute'):
    donors = [i for i, n in zip(ids, names) if n and n.endswith(S + ('trooper' if key == 'marine' else key))]
    if not donors:
        continue
    uid = sets_of(donors[0])
    ch = rp.chain_of(m, zb, uid, res)
    dtags, dpages = ch
    w = {l for l, e in scen if any(rp.getbit(m, *rp._pool(m, e, off), dtags[0]) for _, off in rp.TAG_POOLS if rp._pool(m, e, off)[0])}
    for e in wp:
        ident = m.u32(e + 0xC)
        c2 = rp.chain_of(m, zb, ident, res)
        if not c2:
            continue
        tt, pp = c2
        tt = [ti for ti in tt if rp.resident_in(m, sets, ti)]
        bits = rawb = 0
        for label, elem in sets:
            for _, off in rp.TAG_POOLS:
                b, size = rp._pool(m, elem, off)
                if not b or not rp.getbit(m, b, size, dtags[0]):
                    continue
                bits += sum(1 for ti in tt if not rp.getbit(m, b, size, ti))
            for _, off in rp.RAW_POOLS:
                b, size = rp._pool(m, elem, off)
                if not b or not any(rp.getbit(m, b, size, p) for p in dpages):
                    continue
                rawb += sum(1 for p in pp if not rp.getbit(m, b, size, p))
        if bits or rawb:
            print(key, leaf(by[ident]['name']), 'closure', len(tt), 'pages', len(pp), 'tag bits', bits, 'raw bits', rawb)
            tot[leaf(by[ident]['name'])] = max(tot.get(leaf(by[ident]['name']), 0), bits)
print('max per weapon', tot)
wn = [leaf(HP._tag_name_by_id(m, m.u32(e + 0xC))) for e in wp]
i16 = lambda o: struct.unpack_from('<h', m.data, o)[0]
c1 = collections.defaultdict(collections.Counter)
own, none = 0, 0
for sq in m.follow_all(scnr, [0x398], [0x6C], 'all'):
    dc = m.follow_all(sq, [0x54], [0x6C], 'all')
    tc = m.follow_all(sq, [0x60], [0x6C], 'all')
    for cell in dc + tc:
        for ct in m.follow_all(cell, [0x14], [0x10], 'all'):
            c = i16(ct + 0xC)
            if 0 <= c < len(names) and any(x in names[c] for x in ('jackal', 'skirm')):
                ws = m.follow_all(cell, [0x20], [0x10], 'all')
                for w in ws or [None]:
                    v = i16(w + 0xC) if w else -9
                    c1[leaf(names[c])][wn[v] if 0 <= v < len(wn) else str(v)] += 1
    for sp in m.follow_all(sq, [0x3C], [0x7C], 'all'):
        if i16(sp + 0x34) >= 0:
            own += 1
        else:
            none += 1
print('jackal-family cell weapons', {k: dict(v) for k, v in c1.items()})
print('spawn points with own weapon', own, 'without', none)
