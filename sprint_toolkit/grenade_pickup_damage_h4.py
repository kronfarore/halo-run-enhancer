# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""H4 m40 (Reclaimer): placed equipment by palette entry; the grenade pickup models' root
damage sections + responses (flags, thresholds) and Old Damage Info sections."""
import os, struct, sys, collections, contextlib, io
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [TOOL]; os.chdir(TOOL)
import halo_patch as hp
G = 'Halo 4'; BS = chr(92)
with contextlib.redirect_stdout(io.StringIO()):
    m = hp.open_map(sys.argv[1], G)
f32 = lambda o: struct.unpack_from('<f', m.data, o)[0]
i16 = lambda o: struct.unpack_from('<h', m.data, o)[0]
leaf = lambda s: (s or '-').split(BS)[-1]
base = hp._scnr_base(m)
pal = [hp._tag_name_by_id(m, m.u32(e + 0xC)) for e in m.follow_all(base, [0x1A4], [0x10], 'all')]
c = collections.Counter()
for e in m.follow_all(base, [0x198], [0x154], 'all'):
    t = i16(e)
    c[(leaf(pal[t]) if 0 <= t < len(pal) else t, hex(m.u32(e + 4)))] += 1
for k, v in sorted(c.items(), key=str):
    if 'grenade' in str(k[0]) or 'drain' in str(k[0]):
        print('placed %3d  %s flags %s' % (v, k[0], k[1]))
for p, t in m.find_tags('eqip', '*grenade*'):
    print('eqip', leaf(p), 'obj flags %#x' % m.u32(t + 4))
for name in sys.argv[2:]:
    for p, t in m.find_tags('hlmt', '*' + name):
        print('\nhlmt', leaf(p), 'root flags %#x vit %.3g' % (m.u32(t + 0x100), f32(t + 0x104)))
        for s in m.follow_all(t, [0x114], [180], 'all'):
            print('  root section flags %#x vit%% %.3g' % (m.u32(s + 4), f32(s + 8)))
            for r in m.follow_all(s, [0x84], [180], 'all'):
                print('    resp flags %#x flags2 %#x thr %.3g total %.3g delay %.3g custom %d' % (
                    m.u32(r), m.u32(r + 4), f32(r + 0xC), f32(r + 0xA8), f32(r + 0x7C), i16(r + 0x76)))
        for e in m.follow_all(t, [0xF4], [184], 'all'):
            print('  old flags %#x vit %.3g' % (m.u32(e), f32(e + 0x14)))
            for s in m.follow_all(e, [0x78], [44], 'all'):
                print('    old section flags %#x vit%% %.3g' % (m.u32(s + 4), f32(s + 8)))
                for r in m.follow_all(s, [0xC], [152], 'all'):
                    print('      resp type %d flags %#x thr %.3g' % (i16(r), m.u32(r + 8), f32(r + 0x10)))
