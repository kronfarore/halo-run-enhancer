# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""H3 grenade pickups: which hlmt each eqip uses, and that hlmt's New Damage Info --
flags, vitality, damage sections, instant responses (flags, threshold, new state)."""
import os, struct, sys, contextlib, io
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [TOOL, os.path.join(TOOL, 'sprint_toolkit')]
os.chdir(TOOL)
import halo_patch as hp

BS = chr(92)
src = sys.argv[1] if len(sys.argv) > 1 else r'E:\HaloBaselines\halo3\maps\100_citadel.map'
with contextlib.redirect_stdout(io.StringIO()):
    m = hp.open_map(src, 'Halo 3')
f32 = lambda o: struct.unpack_from('<f', m.data, o)[0]
RESP = ['kills object', 'inhibits melee', 'inhibits weapon', 'inhibits walking', 'forces drop weapon',
        'kills primary', 'kills secondary', 'destroys object', 'dmg primary', 'dmg secondary',
        'lt', 'mt', 'lrt', 'mrt', 'le', 'me', 'kills object (no player solo)', 'causes detonation',
        'fires on creation', 'kills variants', 'force unattached', 'fires under threshold',
        'triggers special death', 'only on special death', 'only not on special death',
        'buckles giants', 'causes sp detonation']
for p, t in m.find_tags('eqip', '*grenade*'):
    hid = m.u32(t + 0x34 + 12)
    hn = hp._tag_name_by_id(m, hid)
    print('eqip', p.split(BS)[-1], '-> hlmt', hn)
for p, t in m.find_tags('hlmt', '*grenade*'):
    for e in m.follow_all(t, [0x88], [164], 'all'):
        print('\nhlmt', p.split(BS)[-1], 'NDI @%x flags %#x vit %.3g shield %.3g' % (
            e, m.u32(e), f32(e + 0xC), f32(e + 0x20)))
        for si, s in enumerate(m.follow_all(e, [0x68], [44], 'all')):
            print('  section %d @%x name %s flags %#x vit%% %.3g' % (
                si, s, hex(m.u32(s)), m.u32(s + 4), f32(s + 8)))
            for ri, r in enumerate(m.follow_all(s, [0xC], [136], 'all')):
                fl = m.u32(r + 8)
                names = [RESP[b] if b < len(RESP) else 'bit%d' % b for b in range(32) if fl >> b & 1]
                print('    resp %d type %d flags %#x %s thr %.3g newstate %d total %.3g' % (
                    ri, struct.unpack_from('<H', m.data, r)[0], fl, names, f32(r + 0xC),
                    struct.unpack_from('<H', m.data, r + 0x44)[0], f32(r + 0x84)))
