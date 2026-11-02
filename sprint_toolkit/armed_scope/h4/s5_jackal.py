import sys
sys.path.insert(0, '..')
from lib import *
out = open('s5.txt', 'w')


def P(*a):
    print(*a, file=out, flush=True)


for mid in ('m10_crash', 'm80_delta'):
    m = op(mid)
    scnr = hp._scnr_base(m)
    chars = palette(m, scnr, 0x444, 0x10, 0xC)
    weaps = palette(m, scnr, 0x1BC, 0x10, 0xC)
    w2, var = collections.Counter(), collections.Counter()
    for sq in block(m, scnr + 0x3F0, 0x6C):
        for s_ in block(m, sq + 0x3C, 0x7C):
            c, w, x, av = i16(m, s_ + 0x2E), i16(m, s_ + 0x30), i16(m, s_ + 0x32), m.u32(s_ + 0x40)
            cn = leaf(chars[c]) if 0 <= c < len(chars) else None
            if x >= 0:
                w2[(cn, leaf(weaps[w]) if w >= 0 else None, leaf(weaps[x]))] += 1
            if 'jackal' in str(cn) or av:
                var[(cn, m.resolve_stringid(av) if av else '', leaf(weaps[w]) if 0 <= w < len(weaps) else None)] += 1
        for off in (0x54, 0x60):
            for cell in block(m, sq + off, 0x64):
                for e in block(m, cell + 0x24, 8):
                    xi = i16(m, e + 4)
                    cc = [leaf(chars[i16(m, q + 4)]) for q in block(m, cell + 0xC, 8) if 0 <= i16(m, q + 4) < len(chars)]
                    w2[('cell' + hex(off), tuple(cc), leaf(weaps[xi]) if 0 <= xi < len(weaps) else xi)] += 1
    P('==', mid)
    P('secondaries', w2.most_common())
    P('variants', var.most_common(30))
    ch = dict(m.find_tags('char', '*'))
    for n, b in ch.items():
        if 'jackal' in str(n) and 'stimuli' not in str(n):
            vs = [m.resolve_stringid(m.u32(e)) if m.u32(e) else '' for e in block(m, b + 0x54, 0x18)]
            P(leaf(n), 'char variants', vs)
    bips = dict(m.find_tags('bipd', '*'))
    for bn, bb in bips.items():
        if 'storm_jackal' not in str(bn):
            continue
        hl = ref(m, bb + 0x64)
        hb = dict(m.find_tags('hlmt', hl)).get(hl)
        P(leaf(bn), 'hlmt', leaf(hl), 'bipd weapons', [(leaf(ref(m, e)), m.u32(e + 0x14)) for e in block(m, bb + 0x4F8, 0xA8)])
        import tagrefs, assembly_plugins
        sp = tagrefs._spec(assembly_plugins.plugins_dir(), 'Halo4MCC', 'hlmt')
        by = {t['ident']: t for t in m.tags if t.get('ident') is not None}
        for path, d in tagrefs.refs_of(m, hb, sp):
            t = by.get(d)
            if t and t['class'] in ('weap', 'eqip', 'scen', 'crea', 'bipd') or 'hield' in str(t and t.get('name')):
                P('   hlmt ref', path, t['class'], leaf(t['name']))
    del m
