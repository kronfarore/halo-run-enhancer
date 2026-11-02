import json, os, collections
S = chr(92)
L = lambda v: str(v).rsplit(S, 1)[-1] if v else None
LV = ['m10_crash', 'm020', 'm30_cryptum', 'm60_rescue', 'm40_invasion', 'm70_liftoff', 'm80_delta', 'm90_sacrifice']
GR = {}
WEAP = {}
stab = collections.defaultdict(set)
for mid in LV:
    d = json.load(open('../graph_%s.json' % mid))
    for k, v in d['weapons'].items():
        if v['card']:
            WEAP[(v['card'], L(k))] = (v['class'], v['name'])
    for bn, r in d['graphs'].items():
        g = r.get('graph')
        if not g:
            continue
        b = L(bn)
        key = json.dumps({m: {c: sorted(t) for c, t in cl.items()} for m, cl in g.items()}, sort_keys=True)
        stab[b].add(key)
        GR.setdefault(b, (g, mid, r.get('n_modes'), r.get('bipd_weapons')))
print('graph shape per level identical?', {b: len(v) for b, v in stab.items()})
sp = [b for b in ('storm_grunt', 'storm_jackal', 'storm_elite_ai', 'storm_knight', 'storm_pawn', 'storm_bishop', 'storm_marine', 'storm_spartan_ai', 'storm_spartan', 'storm_hunter') if b in GR]
print('bipeds', sorted(GR))
wl = {'storm_elite_ai': {'pr', 'spr'}, 'storm_knight': {'rl', 'pr', 'spr'}}
seen = set()
print('%-20s %-8s %-4s ' % ('weapon', 'class', 'name') + ' '.join('%-10s' % s[6:16] for s in sp))
for (card, tag), (c, n) in sorted(WEAP.items()):
    if (card, c, n) in seen or 'npc' in tag or 'pawnhead' in tag:
        continue
    seen.add((card, c, n))
    row = []
    for s in sp:
        g = GR[s][0].get('combat', {})
        cl = g.get(c)
        if cl is None:
            alt = [x for x, t in g.items() if n in t]
            row.append('wl?' + alt[0] if alt else 'NOCLS')
        elif n in cl:
            row.append('type')
        elif 'any' in cl:
            row.append('any')
        else:
            row.append('NOTYPE')
    print('%-20s %-8s %-4s ' % (card[:20], c, n) + ' '.join('%-10s' % x for x in row))
print()
for s in sp:
    g = GR[s][0]
    nonseat = {m: list(cl) for m, cl in g.items() if len(cl) > 1 or list(cl) != ['any']}
    print(s, 'from', GR[s][1], 'modes', GR[s][2], 'bipdW', [L(x) for x in GR[s][3]])
    print('   modes with class beyond any:', nonseat)
print()
for mid in LV:
    c = json.load(open('../census_%s.json' % mid))
    keep = {}
    for k in ('grunt', 'jackal', 'elite', 'knight', 'pawn', 'bishop', 'marine', 'spartans_ai'):
        v = c['per'].get(k)
        if v:
            keep[k] = '%d+%d' % (v.get('spawn', 0), v.get('cell_count', 0))
    v = c['per'].get('inherit', {})
    keep['inherit'] = v.get('spawn', 0)
    t = c['ts_units']
    prot = sum(v.get('spawn_prot', 0) + v.get('cell_prot', 0) for k, v in t.items() if k in ('grunt', 'jackal', 'elite', 'knight', 'marine', 'spartans_ai'))
    tot = sum(sum(x for y, x in v.items()) for k, v in t.items() if k in ('grunt', 'jackal', 'elite', 'knight', 'marine', 'spartans_ai'))
    print(mid, keep, 'tsunits armable', tot, 'prot(veh/script)', prot, 'both-cell squads', c['both_cells'], '/', c['squads'], 'array users', c['array_max_users'], 'dz', c['dz_zone_sets_on'], '/', c['zone_sets'], 'slack KB', c['slack_total'] // 1024, 'gaps', len(c['gaps']), 'badres', sum(1 for v in c['weap_res'].values() if v.get('full_sets') != c['zone_sets']))
