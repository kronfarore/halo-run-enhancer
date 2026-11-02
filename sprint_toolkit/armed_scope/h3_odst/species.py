r"""Per character: unit weapons, model variants (objects), default variant, retreat backup weapon,
berserk weapon, general flags, slack. Read only."""
import contextlib, io, json, os, re, sys, struct
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'species')
os.makedirs(OUT, exist_ok=True)
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL); os.chdir(TOOL)
import halo_patch as hp
ROOT = {'Halo 3': r'E:\HaloBaselines\halo3\maps', 'Halo 3: ODST': r'E:\HaloBaselines\halo3odst\maps'}
BS = chr(92)


def sid(m, s):
    try:
        return m.resolve_stringid(s)
    except Exception:
        return '0x%08X' % s


def tn(m, i):
    return hp._tag_name_by_id(m, i) if i not in (0, 0xFFFFFFFF) else None


g = sys.argv[1]
ubase = {'Halo 3': (0x24C, 0x30), 'Halo 3: ODST': (0x25C, 0x30)}[g]
for name in sys.argv[2:]:
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(os.path.join(ROOT[g], name + '.map'), g)
    out = {'chars': {}, 'models': {}}
    seen = set()
    for p, b in m.find_tags('char', '*'):
        lo = p.lower()
        rt = [(tn(m, m.u32(e + 0x48 + 0xC))) for e in m.follow_all(b, [0x108], [0x58], 'all')]
        ch = [(tn(m, m.u32(e + 0x4C + 0xC))) for e in m.follow_all(b, [0xE4], [0x7C], 'all')]
        gp = [m.u32(e) for e in m.follow_all(b, [0x6C], [0x1C], 'all')]
        un = tn(m, m.u32(b + 0x14 + 0xC))
        out['chars'][p] = dict(retreat=rt, charge=ch, flags=gp, unit=un)
        if un and un not in seen:
            seen.add(un)
            fb = m.find_tags('bipd', un)
            if fb:
                bb = fb[0][1]
                mod = tn(m, m.u32(bb + 0x34 + 0xC))
                dv = sid(m, m.u32(bb + 0x30))
                # unit weapons: scan block offset for the two games
                wk = {}
                for off in (0x24C, 0x25C, 0x268, 0x274):
                    wk[hex(off)] = [tn(m, m.u32(e + 0xC)) for e in m.follow_all(bb, [off], [0x10], 'all')][:4]
                vs = []
                mb = m.find_tags('hlmt', mod) if mod else []
                if mb:
                    hb = mb[0][1]
                    for v in m.follow_all(hb, [0x64], [0x30], 'all'):
                        objs = [(sid(m, m.u32(o)), sid(m, m.u32(o + 4)), tn(m, m.u32(o + 0xC + 0xC)))
                                for o in m.follow_all(v, [0x20], [0x1C], 'all')]
                        regs = []
                        for r in m.follow_all(v, [0x14], [0x14], 'all'):
                            pe = [sid(m, m.u32(q)) for q in m.follow_all(r, [0x8], [0x18], 'all')]
                            regs.append((sid(m, m.u32(r)), pe[:3]))
                        vs.append(dict(name=sid(m, m.u32(v)), objects=objs, regions=regs))
                out['models'][un] = dict(model=mod, default_variant=dv, unit_weapons=wk, variants=vs)
    # slack: zero runs inside partitions
    runs = []
    for la, psz, fb in m.partitions:
        if fb is None or not psz or fb + psz > len(m.data):
            continue
        for mo in re.finditer(rb'\x00{4096,}', bytes(m.data[fb:fb + psz])):
            st = fb + mo.start()
            aligned = (st + 15) & ~15
            if m.off2data(aligned):
                runs.append(mo.end() - mo.start())
    runs.sort(reverse=True)
    out['slack'] = dict(n=len(runs), top=runs[:6], total=sum(runs), n8k=sum(1 for r in runs if r >= 8192),
                        total8k=sum(r for r in runs if r >= 8192))
    json.dump(out, open(os.path.join(OUT, name + '.json'), 'w'), indent=0)
    print(name, 'ok', out['slack'], flush=True)
