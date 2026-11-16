# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""Every Halo 4 map: placed grenade-like pickups (equipment placements whose eqip path holds
'grenade'), split by whether the map's gggl grenade list names that eqip (= pickable as a
grenade), plus crate / scenery variant children that are such eqip tags."""
import os, struct, sys, json, collections, contextlib, io, glob
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [TOOL]; os.chdir(TOOL)
import halo_enhancer as he, halo_patch as hp
C = dict(he.CONFIG); C.update(json.load(open('settings.json', encoding='utf-8')))
G = 'Halo 4'; BS = chr(92)
leaf = lambda s: (s or '-').split(BS)[-1]
MISSIONS = json.load(open('halo.json', encoding='utf-8'))['Missions']['Halo 4']
live_dir = os.path.join(C['mcc_root'], 'halo4', 'maps')
for live in sorted(glob.glob(os.path.join(live_dir, '*.map'))):
    name = os.path.basename(live)
    if name[:-4] not in MISSIONS:
        continue
    src = hp.existing_baseline(live, C.get('baseline_root'), 'halo4/maps') or live
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            m = hp.open_map(src, G)
    except Exception as ex:
        print('%-22s OPEN FAILED %s' % (name, ex), flush=True)
        continue
    sb = hp._scnr_base(m)
    gl = set()
    for _p, t in m.find_tags('gggl', 'globals' + BS + 'grenade_list'):
        for e in m.follow_all(t, [0x0], [120], 'all'):
            for o in (0x38, 0x58):
                n = hp._tag_name_by_id(m, m.u32(e + o + 0xC))
                if n:
                    gl.add(n.lower())
    pal = [hp._tag_name_by_id(m, m.u32(e + 0xC)) or '' for e in m.follow_all(sb, [0x1A4], [0x10], 'all')]
    cnt = collections.Counter()
    where = collections.defaultdict(list)
    for i, e in enumerate(m.follow_all(sb, [0x198], [0x154], 'all')):
        t = struct.unpack_from('<h', m.data, e)[0]
        p = pal[t] if 0 <= t < len(pal) else ''
        if 'grenade' in p.lower():
            k = (leaf(p), p.lower() in gl)
            cnt[k] += 1
            if not k[1]:
                where[k[0]].append('#%d (%.0f %.0f %.0f)' % ((i,) + struct.unpack_from('<3f', m.data, e + 8)))
    rack = collections.Counter()
    for kind, (off, es, poff, vn) in (('crate', (0x638, 0x178, 0x644, 0x9C)), ('scenery', (0x150, 0x17C, 0x15C, 0x9C))):
        cp = [hp._tag_name_by_id(m, m.u32(e + 0xC)) for e in m.follow_all(sb, [poff], [0x10], 'all')]
        cache = {}
        for e in m.follow_all(sb, [off], [es], 'all'):
            t = struct.unpack_from('<h', m.data, e)[0]
            if not (0 <= t < len(cp)) or not cp[t]:
                continue
            key = (cp[t], m.u32(e + vn))
            if key not in cache:
                kids = []
                bt = m.find_tags('bloc' if kind == 'crate' else 'scen', cp[t])
                if bt:
                    h = hp._tag_name_by_id(m, m.u32(bt[0][1] + 0x64 + 0xC))
                    ht = m.find_tags('hlmt', h) if h else []
                    if ht:
                        for v in m.follow_all(ht[0][1], [0xC4], [0x6C], 'all'):
                            if m.u32(v) == key[1]:
                                kids = [hp._tag_name_by_id(m, m.u32(o + 0x10 + 0xC)) or '' for o in m.follow_all(v, [0x30], [0x24], 'all')]
                cache[key] = [k for k in kids if 'grenade' in k.lower()]
            for k in cache[key]:
                rack[(kind, leaf(k), k.lower() in gl)] += 1
    print('%-22s %s' % (name, os.path.dirname(src)), flush=True)
    print('    grenade list:', sorted(leaf(x) for x in gl))
    for (n, ok), v in sorted(cnt.items()):
        print('    placed %3d  %-28s %s' % (v, n, 'pickable' if ok else 'NOT in the grenade list'))
    for n, ws in where.items():
        print('       ', n, 'at', ', '.join(ws))
    for (kind, n, ok), v in sorted(rack.items()):
        print('    %s child %3d  %-28s %s' % (kind, v, n, 'pickable' if ok else 'NOT in the grenade list'))
