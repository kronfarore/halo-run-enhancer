import sys
sys.path.insert(0, '..')
from lib import *
O = open('s2b_%s.txt' % sys.argv[1], 'w')


def P(*a):
    print(*a, file=O, flush=True)


def lab(m, a):
    s = m.u32(a)
    return (m.resolve_stringid(s) or hex(s)) if s else ''


mid = sys.argv[1]
m = op(mid)
scnr = hp._scnr_base(m)
chars = palette(m, scnr, 0x444, 0x10, 0xC)
weaps = palette(m, scnr, 0x1BC, 0x10, 0xC)
P('## weapons: class name flags sec barrels')
for nm, b in sorted(m.find_tags('weap', '*')):
    n = str(nm)
    if 'weapons' + S not in n:
        continue
    fl, sec = m.u32(b + 0x2A0), m.u32(b + 0x2A4)
    bits = [x for x, i in (('support', 8), ('prevCrouch', 13), ('dual', 17), ('meleeOnly', 19), ('noGren', 3), ('noMelee', 4), ('aiMeleeDmg', 10), ('noPlayer', 23)) if fl >> i & 1]
    P('%-46s %-8s %-6s pal=%d %s' % (leaf(n), lab(m, b + 0x4B4), lab(m, b + 0x4B8), n in weaps, ','.join(bits)))
P('## cells naming a char + weapon')
for si, sq in enumerate(block(m, scnr + 0x3F0, 0x6C)):
    name = bytes(m.data[sq:sq + 0x20]).split(b'\0')[0].decode('latin1')
    for lb, off in (('T', 0x60), ('D', 0x54)):
        for ci, cell in enumerate(block(m, sq + off, 0x64)):
            cts = [(leaf(chars[i16(m, x + 4)]) if 0 <= i16(m, x + 4) < len(chars) else None, struct.unpack_from('<f', m.data, x)[0], m.u32(x)) for x in block(m, cell + 0xC, 8)]
            ws = [(leaf(weaps[i16(m, x + 4)]) if 0 <= i16(m, x + 4) < len(weaps) else None, struct.unpack_from('<f', m.data, x)[0], hex(m.u32(x))) for x in block(m, cell + 0x18, 8)]
            if len(ws) > 1 or len(cts) > 1:
                P(name, lb, ci, 'count', i16(m, cell + 8), 'chars', [(a, round(b, 2)) for a, b, _c in cts], 'w', [(a, round(b, 2), c) for a, b, c in ws], 'wptr', hex(m.u32(cell + 0x1C)))
P('## graphs')
bip = dict(m.find_tags('bipd', '*'))
for bn, bb in bip.items():
    if not any(x in str(bn) for x in ('storm_grunt', 'storm_jackal', 'storm_elite_ai', 'storm_knight', 'storm_pawn', 'storm_bishop', 'storm_marine', 'storm_spartan')):
        continue
    hl = ref(m, bb + 0x64)
    hb = dict(m.find_tags('hlmt', hl)).get(hl)
    jn = ref(m, hb + 0x20)
    jb = dict(m.find_tags('jmad', jn)).get(jn)
    if jb is None:
        continue
    wl = [(lab(m, e), lab(m, e + 4)) for e in block(m, jb + 0x178, 8)]
    P('--', leaf(bn), 'modes', m.i32(jb + 0x13C), 'wl', wl, 'modes_ptr', hex(m.u32(jb + 0x140)))
    for md in block(m, jb + 0x13C, 0x30):
        ml = lab(m, md)
        if ml not in ('combat', 'crouch', 'flee', 'patrol', 'berserk', 'stunned', 'fallen', 'alert'):
            continue
        for wc in block(m, md + 0xC, 0x38):
            cl = lab(m, wc)
            ik = [(lab(m, e), lab(m, e + 4)) for e in block(m, wc + 0x14, 8)]
            for wt in block(m, wc + 0x8, 0x14):
                tl = lab(m, wt)
                for st in block(m, wt + 0x8, 0x48):
                    acts = [lab(m, a) for a in block(m, st + 0xC, 0xC)]
                    ov = [lab(m, a) for a in block(m, st + 0x18, 0xC)]
                    f = [x for x in ov + acts if 'fire' in x or 'aim' in x or 'reload' in x]
                    P('  %-7s %-8s %-5s %-5s a=%-3d o=%-3d %s ik=%s' % (ml, cl, tl, lab(m, st), len(acts), len(ov), f[:10], ik[:3]))
