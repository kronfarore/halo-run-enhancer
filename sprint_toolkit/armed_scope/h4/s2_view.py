import json, os, sys, collections
S = chr(92)
L = lambda v: str(v).rsplit(S, 1)[-1] if v else None
LEVELS = ['m10_crash', 'm020', 'm30_cryptum', 'm60_rescue', 'm40_invasion', 'm70_liftoff', 'm80_delta', 'm90_sacrifice']
SEATS = ('_', )
for mid in LEVELS:
    p = '../graph_%s.json' % mid
    if not os.path.exists(p):
        continue
    d = json.load(open(p))
    print('=====', mid, d['title'], 'chars', d['all_chars'])
    W = d['weapons']
    print(' pool weapons class/name:', sorted({(L(k), v['class'], v['name'], v['card']) for k, v in W.items() if v['card'] and v['in_pal']}, key=str))
    print(' sibs', list(d['graph_siblings'].items())[:3], len(d['graph_siblings']))
    for bn, r in d['graphs'].items():
        g = r.get('graph') or {}
        print(' --', L(bn), 'jmad', L(r.get('jmad')), 'parent', L(r.get('parent')), 'modes', r.get('n_modes'), 'wl', r.get('weapon_list'), 'anims', r.get('anims'), 'inh', r.get('inherit_new'), r.get('inherit_old'), 'bipdW', [L(x) for x in r.get('bipd_weapons', [])])
        # non-seat modes: those with action sets beyond seat-names
        allc = collections.Counter()
        for md, cl in g.items():
            for c in cl:
                allc[c] += 1
        print('    classes (modes):', dict(allc))
        for md in ('combat', 'crouch', 'flee', 'patrol', 'alert', 'stand', 'asleep', 'sprint', 'berserk', 'unarmed'):
            if md in g:
                print('    %-8s' % md, {c: {t: len(s) for t, s in tp.items()} for c, tp in g[md].items()})
