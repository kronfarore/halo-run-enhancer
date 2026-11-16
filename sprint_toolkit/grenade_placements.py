# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""Read-only: placed grenade pickups (scnr Equipment block) per level, from the baselines."""
import json, os, sys, collections
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL); os.chdir(TOOL)
import halo_enhancer as he, halo_patch as hp
C = dict(he.CONFIG); C.update(json.load(open('settings.json', encoding='utf-8')))
db = json.load(open('halo.json', encoding='utf-8'))
for g in (sys.argv[1:] or list(db['Missions'])):
    E = hp._MAP_EQUIPMENT[g]
    sub = C['map_game_folder'][g]
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
                k = struct_i16 = int.from_bytes(m.data[ib + i * ie:ib + i * ie + 2], 'little', signed=True)
                nm = names[k] if 0 <= k < len(names) else None
                if nm and 'grenade' in nm:
                    c[nm.split('\\')[-1]] += 1
            print('%-13s %-16s %s' % (g, mid, dict(c)), flush=True)
        except Exception as e:
            print(g, mid, 'ERR', e)
