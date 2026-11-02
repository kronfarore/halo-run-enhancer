from lib import *
t = time.time()
m = op('m10_crash')
print('open', time.time() - t)
scnr = hp._scnr_base(m)
rows, name_at = sid_tools(m)
print(len(rows), 'strings; voted offset', getattr(m, '_h4_sid_off', None))
w = palette(m, scnr, 0x1BC, 0x10, 0xC)
print('weapons', [leaf(x) for x in w])
c = palette(m, scnr, 0x444, 0x10, 0xC)
print('chars', [leaf(x) for x in c])
for nm, b in list(m.find_tags('weap', '*'))[:6]:
    a, bb = m.u32(b + 0x4B4), m.u32(b + 0x4B8)
    print(leaf(nm), hex(a), hex(bb), sid_name(m, name_at, a), sid_name(m, name_at, bb), name_at.get((a & 0x1FFFF) + 6841), name_at.get((bb & 0x1FFFF) + 6841))
jm = [(n, b) for n, b in m.find_tags('jmad', '*') if 'storm_grunt' in str(n).lower()]
print(jm[:6])
for n, b in jm[:2]:
    print(n, 'parent', ref(m, b), 'modes n', m.i32(b + 0x13C), 'weapon list', m.i32(b + 0x178))
    for md in block(m, b + 0x13C, 0x30)[:6]:
        s = m.u32(md)
        print('  mode', hex(s), sid_name(m, name_at, s), name_at.get((s & 0x1FFFF) + 6841))
        for wc in block(m, md + 0xC, 0x38)[:6]:
            s2 = m.u32(wc)
            print('     class', hex(s2), sid_name(m, name_at, s2), name_at.get((s2 & 0x1FFFF) + 6841))
