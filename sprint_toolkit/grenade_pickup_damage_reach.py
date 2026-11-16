# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""Reach m60 grenade pickups: eqip -> hlmt, the hlmt's TWO damage layouts (Old Damage Info
+0xC0 and the root damage fields / Damage Sections +0xE0) with their instant responses."""
import os, struct, sys, contextlib, io
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [TOOL, os.path.join(TOOL, 'sprint_toolkit')]
os.chdir(TOOL)
import halo_patch as hp

G = 'Halo Reach'
BS = chr(92)
src = sys.argv[1] if len(sys.argv) > 1 else r'E:\HaloBaselines\haloreach\maps\m60.map'
with contextlib.redirect_stdout(io.StringIO()):
    m = hp.open_map(src, G)
f32 = lambda o: struct.unpack_from('<f', m.data, o)[0]
for p, t in m.find_tags('eqip', '*grenade*'):
    print('eqip', p, '-> hlmt', hp._tag_name_by_id(m, m.u32(t + 0x64 + 12)))
for p, t in m.find_tags('hlmt', '*grenade*'):
    print('\nhlmt', p.split(BS)[-1], 'root flags %#x vit %.3g' % (m.u32(t + 0xCC), f32(t + 0xD0)))
    for e in m.follow_all(t, [0xC0], [268], 'all'):
        print('  old @%x flags %#x vit %.3g' % (e, m.u32(e), f32(e + 0x28)))
        for s in m.follow_all(e, [0xCC], [68], 'all'):
            for r in m.follow_all(s, [0xC], [144], 'all'):
                print('    old section @%x resp flags %#x thr %.3g' % (s, m.u32(r + 8), f32(r + 0xC)))
    for s in m.follow_all(t, [0xE0], [192], 'all'):
        print('  root section @%x flags %#x vit%% %.3g' % (s, m.u32(s + 4), f32(s + 8)))
        for r in m.follow_all(s, [0x84], [176], 'all'):
            fl = m.u32(r)
            print('    resp flags %#x%s thr %.3g' % (fl, ' (causes sp detonation)' if fl >> 19 & 1 else '',
                                                    f32(r + 8)))
