"""Per level: weapon class/name labels, per-species graph (mode > class > type), firing entries."""
from lib import *
import h4_census as hc
WNAME = [(p.replace('/', S), n) for p, n in hc.WEAPONS]


def wcard(tag):
    t = str(tag or '')
    for p, n in WNAME:
        if p in t:
            return n
    return None


def lab(m, a):
    s = m.u32(a)
    if not s:
        return ''
    return m.resolve_stringid(s) or hex(s)


def graph(m, b):
    G = {}
    for md in block(m, b + 0x13C, 0x30):
        ml = lab(m, md)
        cls = {}
        for wc in block(m, md + 0xC, 0x38):
            cl = lab(m, wc)
            types = {}
            for wt in block(m, wc + 0x8, 0x14):
                tl = lab(m, wt)
                sets = {}
                for st in block(m, wt + 0x8, 0x48):
                    sl = lab(m, st)
                    acts = [lab(m, a) for a in block(m, st + 0xC, 0xC)]
                    sets[sl] = acts
                types[tl] = sets
            cls[cl] = types
        G[ml] = cls
    return G


only = sys.argv[1:] or [a for a, _b in LEVELS]
for mid, title in LEVELS:
    if mid not in only:
        continue
    m = op(mid)
    R = {'title': title}
    scnr = hp._scnr_base(m)
    chars = palette(m, scnr, 0x444, 0x10, 0xC)
    weaps = palette(m, scnr, 0x1BC, 0x10, 0xC)
    # weapon labels + flags
    W = {}
    for nm, b in m.find_tags('weap', '*'):
        W[nm] = {'class': lab(m, b + 0x4B4), 'name': lab(m, b + 0x4B8), 'card': wcard(nm),
                 'in_pal': nm in weaps}
    R['weapons'] = W
    # bipds used
    allch = dict(m.find_tags('char', '*'))
    R['all_chars'] = len(allch)
    seen = {}
    for c in chars + [n for n in allch if any(x in str(n).lower() for x in ('marine', 'spartans_ai', 'pawn', 'bishop', 'knight'))]:
        if not c or c not in allch:
            continue
        b = allch[c]
        x, u = c, None
        for _ in range(6):
            u = ref(m, allch[x] + 0x14) if x in allch else None
            if u:
                break
            x = ref(m, allch[x] + 0x4) if x in allch else None
        seen[c] = u
    R['char_unit'] = seen
    bipds = dict(m.find_tags('bipd', '*'))
    G = {}
    gptr = {}
    for bn in sorted({v for v in seen.values() if v}):
        bb = bipds.get(bn)
        if bb is None:
            continue
        hl = ref(m, bb + 0x64)
        hb = dict(m.find_tags('hlmt', hl)).get(hl) if hl else None
        jn = ref(m, hb + 0x20) if hb is not None else None
        jb = dict(m.find_tags('jmad', jn)).get(jn) if jn else None
        rec = {'hlmt': hl, 'jmad': jn}
        dw = []
        for e in block(m, bb + 0x4F8, 0xA8):
            dw.append(ref(m, e))
        rec['bipd_weapons'] = dw
        if jb is not None:
            rec['parent'] = ref(m, jb)
            rec['n_modes'] = m.i32(jb + 0x13C)
            rec['modes_ptr'] = hex(m.u32(jb + 0x140))
            rec['weapon_list'] = m.i32(jb + 0x178)
            rec['anims'] = m.i32(jb + 0x9C)
            rec['inherit_new'] = m.i32(jb + 0x16C)
            rec['inherit_old'] = m.i32(jb + 0x160)
            rec['graph'] = graph(m, jb)
        G[bn] = rec
    R['graphs'] = G
    # siblings like storm_grunt15
    sib = {}
    for n, b in m.find_tags('jmad', '*'):
        p = ref(m, b)
        if p and leaf(n).startswith(leaf(p)) and leaf(n) != leaf(p):
            sib[n] = {'parent': p, 'n_modes': m.i32(b + 0x13C), 'modes_ptr': hex(m.u32(b + 0x140)),
                      'anims': m.i32(b + 0x9C), 'anims_ptr': hex(m.u32(b + 0xA0))}
    R['graph_siblings'] = sib
    # firing data
    F = {}
    for n, b in allch.items():
        p = ref(m, b + 0x4)
        wp = [(ref(m, e + 4), e) for e in block(m, b + 0x204, 0xCC)]
        fp = [(ref(m, e), m.i32(e + 0x10)) for e in block(m, b + 0x210, 0x1C)]
        xp = [ref(m, e) for e in block(m, b + 0x21C, 0x1C)]
        gp = block(m, b + 0x6C, 0x5C)
        F[n] = {'parent': p, 'unit': ref(m, b + 0x14),
                'wp': [w for w, _e in wp], 'fp': [[w, k] for w, k in fp], 'xp': xp,
                'init': [ref(m, g + 0x2C) for g in gp], 'init2': [ref(m, g + 0x3C) for g in gp],
                'wpn_ptr': hex(m.u32(b + 0x208)),
                'backup': [ref(m, e + 0x48) for e in block(m, b + 0x168, 0x58)],
                'zerk': [ref(m, e + 0x60) for e in block(m, b + 0x144, 0xB8)],
                }
    R['fire'] = F
    with open(os.path.join(OUT, 'graph_%s.json' % mid), 'w') as fh:
        json.dump(R, fh, indent=0, default=str)
    print(mid, 'ok')
    del m
