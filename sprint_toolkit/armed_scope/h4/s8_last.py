import sys
sys.path.insert(0, '..')
from lib import *
g = json.load(open('../graph_m40_invasion.json'))
sib = g['graph_siblings']
for k in ('storm_grunt', 'storm_jackal', 'storm_elite_ai', 'storm_knight', 'storm_marine'):
    print(k, 'siblings', [(leaf(n), v['n_modes'], v['anims']) for n, v in sib.items() if leaf(v['parent']) == k])
c = json.load(open(os.path.join(TOOL, 'weapon_ports_catalog.json'), encoding='utf8'))
print('H4 ports', [p['weapon'] for p in c['Halo 4']])
for mid in ('m30_cryptum', 'm60_rescue', 'm70_liftoff'):
    d = json.load(open('../graph_%s.json' % mid))
    print(mid, {leaf(k): (v['class'], v['name']) for k, v in d['weapons'].items() if v.get('card') in ('Incineration Cannon', 'Rocket Launcher')})
    r = [v for k, v in d['graphs'].items() if 'spartans_ai' in k]
    if r:
        gg = r[0]['graph']
        print('spartans_ai combat', {cl: sorted(t) for cl, t in gg.get('combat', {}).items()}, 'flee', list(gg.get('flee', {})), 'bipdW', r[0]['bipd_weapons'])
m = op('m40_invasion')
scnr = hp._scnr_base(m)
chars = palette(m, scnr, 0x444, 0x10, 0xC)
weaps = palette(m, scnr, 0x1BC, 0x10, 0xC)
for sq in block(m, scnr + 0x3F0, 0x6C):
    for s_ in block(m, sq + 0x3C, 0x7C):
        ci, w, av = i16(m, s_ + 0x2E), i16(m, s_ + 0x30), m.u32(s_ + 0x40)
        if 0 <= ci < len(chars) and leaf(chars[ci]) == 'storm_jackal' and w >= 0 and 'carbine' in leaf(weaps[w]):
            print('jackal carbine', bytes(m.data[sq:sq + 0x20]).split(b'\0')[0], 'variant', m.resolve_stringid(av) if av else '')
gb = dict(m.find_tags('char', 'ai' + S + 'generic')).get('ai' + S + 'generic')
rows = block(m, gb + 0x204, 0xCC)
nul = [i for i, e in enumerate(rows) if not ref(m, e + 4)]
print('null rows', len(nul), 'first', nul[:6])
e = rows[nul[0]]
print('null row max range/min', struct.unpack_from('<ffff', m.data, e + 0x14), 'class ref fields', hex(m.u32(e + 4)), hex(m.u32(e + 0x10)))
fr = block(m, gb + 0x210, 0x1C)
nf = [i for i, e in enumerate(fr) if not ref(m, e)]
e = fr[nf[0]]
print('null pattern', len(nf), 'patterns', m.i32(e + 0x10), hex(m.u32(e + 0x14)))
print('generic wp index live', [(i, leaf(ref(m, x + 4))) for i, x in enumerate(rows) if ref(m, x + 4) and 'storm_' in leaf(ref(m, x + 4))][:12])
# sqtm referenced? squad template ref field
print('squad +? template refs', sum(1 for n, b in m.find_tags('sqtm', '*')))
