# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""Read-only: Equipment Flags of every placed grenade pickup, all campaign maps (baselines)."""
import json, os, sys, collections, struct
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL); os.chdir(TOOL)
import halo_enhancer as he, halo_patch as hp
C = dict(he.CONFIG); C.update(json.load(open('settings.json', encoding='utf-8')))
db = json.load(open('halo.json', encoding='utf-8'))
EQF = {'Halo 1': 34, 'Halo 2': 52, 'Halo 3': 84, 'Halo 3: ODST': 84, 'Halo Reach': 88, 'Halo 4': 156}
for g in (sys.argv[1:] or list(db['Missions'])):
    E = hp._MAP_EQUIPMENT[g]
    sub = C['map_game_folder'][g]
    tot = collections.Counter()
    for mid in db['Missions'][g]:
        live = hp.default_map_path(C['mcc_root'], sub, mid)
        bl = hp.baseline_path(live, C.get('baseline_root'), sub)
        try:
            m = hp.open_map(bl if os.path.isfile(bl) else live, g)
            sb = hp._scnr_base(m)
            po, pe = E['palette']
            pn = m.i32(sb + po)
            pb = hp._block_base(m, sb + po) if pn > 0 else None
            names = [hp._tag_name_by_id(m, m.u32(pb + i * pe + E['pal_id_at'])) for i in range(max(0, pn))]
            io, ie = E['items']
            n = m.i32(sb + io)
            ib = hp._block_base(m, sb + io) if n > 0 else None
            c = collections.Counter()
            for i in range(max(0, n)):
                e = ib + i * ie
                k = struct.unpack_from('<h', m.data, e)[0]
                nm = names[k] if 0 <= k < len(names) else None
                if nm and 'grenade' in nm:
                    fl = struct.unpack_from('<H' if g == 'Halo 1' else '<I', m.data, e + EQF[g])[0]
                    c[(nm.split(chr(92))[-1], 'accel' if fl & 4 else 'still', fl)] += 1
            tot.update(c)
            print('%-13s %-16s %s' % (g, mid, dict(c)), flush=True)
        except Exception as ex:
            print(g, mid, 'ERR', ex, flush=True)
    print('== %s TOTAL %s' % (g, dict(tot)), flush=True)
