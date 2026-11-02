import json, sys
S = chr(92)
L = lambda v: str(v).rsplit(S, 1)[-1] if v else None
mid = sys.argv[1] if len(sys.argv) > 1 else 'm10_crash'
d = json.load(open('../graph_%s.json' % mid))
for bn, r in d['graphs'].items():
    g = r.get('graph') or {}
    if not any(x in bn for x in ('grunt', 'jackal', 'elite_ai', 'knight', 'pawn', 'bishop', 'marine', 'spartan')):
        continue
    print('--', L(bn))
    for md in ('combat', 'crouch', 'flee'):
        for c, tp in g.get(md, {}).items():
            for t, s in tp.items():
                for st, a in s.items():
                    fire = [x for x in a if x.startswith('fire')]
                    print('  %-7s %-8s %-5s %-10s n=%-3d fire=%s %s' % (md, c, t, st, len(a), fire[:3], ','.join(a[:9])))
print('sibs storm', {L(k): v for k, v in d['graph_siblings'].items() if 'storm_grunt' in k or 'storm_jackal' in k or 'storm_elite' in k})
F = d['fire']
g = next(v for k, v in F.items() if k.endswith(S + 'generic') or k == 'ai' + S + 'generic')
print('generic wp', len(g['wp']), 'null', sum(1 for w in g['wp'] if not w), 'fp', len(g['fp']), 'nullfp', sum(1 for w, k in g['fp'] if not w))
for k, v in F.items():
    if v['wp'] or v['fp'] or v['init'] or any(v['init2']) or v['backup'] or v['zerk']:
        print(L(k), 'par', L(v['parent']), 'unit', L(v['unit']), 'wp', [L(x) for x in v['wp']][:6] if 'generic' not in k else len(v['wp']), 'fp', [(L(a), b) for a, b in v['fp']][:6] if 'generic' not in k else len(v['fp']), 'init', [L(x) for x in v['init']], [L(x) for x in v['init2']], 'backup', [L(x) for x in v['backup']], 'zerk', [L(x) for x in v['zerk']])
