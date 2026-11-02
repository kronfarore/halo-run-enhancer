r"""READ-ONLY second pass: secondary weapons, variants, backup weapons, shield. Never saves."""
import json, os, struct, sys, collections
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP
import enemy_count as ec
GAME = 'Halo Reach'
S = chr(92)
leaf = lambda n: n.rsplit(S, 1)[-1] if n else n
OUT = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]
m = HP.open_map(r'E:\HaloBaselines\haloreach\maps\%s.map' % name, GAME)
by = {t['ident']: t for t in m.tags if t.get('ident') is not None}
scnr = HP._scnr_base(m)
lay = HP._BETRAYAL[GAME]
pal = m.follow_all(scnr, [0x3EC], [0x10], 'all')
names = [HP._tag_name_by_id(m, m.u32(e + 0xC)) for e in pal]
wl = HP._MAP_WEAPONS[GAME]
wp = m.follow_all(scnr, [0x168], [0x10], 'all')
wn = [leaf(HP._tag_name_by_id(m, m.u32(e + 0xC))) for e in wp]
i16 = lambda o: struct.unpack_from('<h', m.data, o)[0]
W = lambda w: wn[w] if 0 <= w < len(wn) else str(w)
sec = collections.defaultdict(collections.Counter)
pri = collections.defaultdict(collections.Counter)
sp_var = collections.Counter()
sp_inh = collections.Counter()
for sq in m.follow_all(scnr, [0x398], [0x6C], 'all'):
    cells = {}
    allc = m.follow_all(sq, [0x54], [0x6C], 'all') + m.follow_all(sq, [0x60], [0x6C], 'all')
    for cell in allc:
        ch = {leaf(names[i16(c + 0xC)]) for c in m.follow_all(cell, [0x14], [0x10], 'all') if 0 <= i16(c + 0xC) < len(names)}
        for c in ch:
            for w in m.follow_all(cell, [0x20], [0x10], 'all'):
                pri[c][W(i16(w + 0xC))] += 1
            for w in m.follow_all(cell, [0x2C], [0x10], 'all'):
                sec[c][W(i16(w + 0xC))] += 1
    dcells = m.follow_all(sq, [0x54], [0x6C], 'all')
    for sp in m.follow_all(sq, [0x3C], [0x7C], 'all'):
        ci, c = i16(sp + 0x10), i16(sp + 0x32)
        v = m.u32(sp + 0x44)
        cn = leaf(names[c]) if 0 <= c < len(names) else None
        if cn is None and 0 <= ci < len(dcells):
            cts = m.follow_all(dcells[ci], [0x14], [0x10], 'all')
            cn = '/'.join(sorted({leaf(names[i16(x + 0xC)]) for x in cts if 0 <= i16(x + 0xC) < len(names)})) + '(cell)'
        sp_inh[(cn, W(i16(sp + 0x34)), W(i16(sp + 0x36)), m.resolve_stringid(v) if v else None)] += 1
print('cell primary', {k: dict(v) for k, v in pri.items() if 'jackal' in k or 'skirm' in k or 'brute' in k or 'engineer' in k or 'bugger' in k})
print('cell secondary', {k: dict(v) for k, v in sec.items()})
print('spawn (char, w1, w2, actor variant) count')
for k, n in sorted(sp_inh.items(), key=lambda x: str(x[0])):
    if k[3] or k[2] != '-1' or (k[0] and ('jackal' in k[0] or 'skirm' in k[0])):
        print('  ', k, n)
print('weap tags in map not in palette:', [leaf(t['name']) for t in m.tags if t.get('class') == 'weap' and leaf(t['name']) not in wn])
# variants
for t in m.tags:
    if t.get('class') == 'char' and t.get('base') and any(x in t['name'] for x in ('jackal', 'skirmisher', 'grunt\\ai\\grunt', 'brute\\ai\\brute', 'bugger', 'engineer', 'marine', 'trooper')):
        b = t['base']
        vs = [(m.resolve_stringid(m.u32(e)), i16(e + 4)) for e in m.follow_all(b, [0x54], [0x18], 'all')]
        # Retreat props Backup Weapon: find via block offset
        print('char', leaf(t['name']), 'variants', vs, 'unit', leaf(by.get(m.u32(b + 0x20), {}).get('name')))
for t in m.tags:
    if t.get('class') == 'hlmt' and t.get('base') and any(x in t['name'].lower() for x in ('jackal', 'skirm', 'characters\\grunt', 'characters\\brute', 'bugger', 'engineer')):
        b = t['base']
        vs = [m.resolve_stringid(m.u32(e)) for e in m.follow_all(b, [0x84], [0x38], 'all')]
        print('hlmt', leaf(t['name']), vs)
