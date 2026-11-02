r"""Character graphs with action labels. Read only. python graphs.py game map map..."""
import contextlib, io, json, os, sys
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphs')
os.makedirs(OUT, exist_ok=True)
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL); os.chdir(TOOL)
import halo_patch as hp
ROOT = {'Halo 3': r'E:\HaloBaselines\halo3\maps', 'Halo 3: ODST': r'E:\HaloBaselines\halo3odst\maps'}
BS = chr(92)


def sid(m, s):
    try:
        r = m.resolve_stringid(s)
    except Exception:
        r = None
    return r if r else '0x%X' % s


g = sys.argv[1]
for name in sys.argv[2:]:
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(os.path.join(ROOT[g], name + '.map'), g)
    out = {}
    for p, b in m.find_tags('jmad', '*'):
        lo = p.lower()
        if 'characters' + BS not in lo or 'cinematics' in lo or 'lipsync' in lo or BS + 'fp' in lo:
            continue
        modes = {}
        for md in m.follow_all(b, [0x5C], [0x28], 'all'):
            ml = sid(m, m.u32(md))
            cl_ = modes.setdefault(ml, {})
            for c in m.follow_all(md, [0x4], [0x1C], 'all'):
                cl = sid(m, m.u32(c))
                ty = cl_.setdefault(cl, {})
                for t in m.follow_all(c, [0x4], [0x34], 'all'):
                    tl = sid(m, m.u32(t))
                    acts = [sid(m, m.u32(a)) for a in m.follow_all(t, [0x4], [0x8], 'all')]
                    ty[tl] = acts
        wl = [(sid(m, m.u32(e)), sid(m, m.u32(e + 4))) for e in m.follow_all(b, [0x8C], [8], 'all')]
        par = m.u32(b + 0xC)
        out[p] = {'modes': modes, 'weapon_list': wl,
                  'parent': hp._tag_name_by_id(m, par) if par != 0xFFFFFFFF else None,
                  'sizes': {'modes_at': m.u32(b + 0x5C + 4), 'wl_at': m.u32(b + 0x8C + 4), 'wl_n': m.i32(b + 0x8C)}}
    co, no, fo = (0x3DC, 0x3E0, 0x18C) if g == 'Halo 3' else (0x3EC, 0x3F0, 0x19C)
    out['__weap__'] = {p: (sid(m, m.u32(b + co)), sid(m, m.u32(b + no)), m.u32(b + fo))
                       for p, b in m.find_tags('weap', '*')}
    json.dump(out, open(os.path.join(OUT, name + '.json'), 'w'), indent=0)
    print(name, len(out), flush=True)
