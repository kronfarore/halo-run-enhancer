r"""Replay the sapien gate on the dumped graphs: lookup(mode, class, type, 'idle') with the 8 'any'
fallbacks, Weapon List class override. A = exact class+type row, c = class row with type any,
f = only through class any, - = refused."""
import json, sys, glob, os
LAB = {'0x310': 'missile', '0x311': 'support?', '0x312': 'rifle', '0x313': 'pistol', '0x314': 'sword', '0x2669': 'hammer',
       '0x429': 'ball', '0x5CE': 'ar', '0x5D2': 'br', '0x410': 'smg'}
S = chr(92)
SPEC = ['brute', 'grunt', 'jackal', 'elite', 'bugger', 'marine', 'marine_female', 'odst', 'floodcombat_elite', 'floodcombat_human', 'flood', 'engineer', 'sentinel', 'hunter', 'pure', 'ranged', 'tank', 'stalker', 'carrier', 'infection']


def lab(x):
    return LAB.get(x, x)


def has(g, mode, cl, ty, act='idle'):
    for m_ in (mode, 'any'):
        M = g['modes'].get(m_)
        if not M:
            continue
        for c in (cl, 'any'):
            C = M.get(c)
            if not C:
                continue
            for t in (ty, 'any'):
                T = C.get(t)
                if T and act in T:
                    return (m_, c, t)
    return None


def verdict(g, mode, wc, wn):
    wl = dict(tuple(x) for x in g['weapon_list'])
    cl = wc
    ov = wl.get(wn)
    if ov and ov != 'any' and wc != '0x1F4':
        cl = ov
    r = has(g, mode, cl, wn)
    if not r:
        return '-', cl
    if r[1] == 'any':
        return 'f', cl
    if r[2] == 'any':
        return 'c', cl
    return 'A', cl


for f in sorted(glob.glob('graphs/*.json')):
    R = json.load(open(f))
    W = R.pop('__weap__')
    print('\n=====', os.path.basename(f))
    pool = {}
    for p, (c, n, fl) in W.items():
        lo = p.lower()
        if lo.startswith('objects' + S + 'weapons' + S) and 'multiplayer' not in lo and 'grenade' not in lo and 'integrated' not in lo:
            pool[p.rsplit(S, 1)[-1]] = (c, n, fl)
    for p, g in sorted(R.items()):
        leaf = p.rsplit(S, 1)[-1]
        if 'ambient' in p or 'cortana' in p or 'lipsync' in p or not g['modes']:
            continue
        print('\n#', p, 'parent', g['parent'], 'modes', len(g['modes']), 'WL', len(g['weapon_list']))
        print('  WL', [(a, lab(b)) for a, b in g['weapon_list']])
        for mo in ('any', 'combat', 'patrol', 'crouch', 'flee', 'berserk', 'armored'):
            M = g['modes'].get(mo)
            if M:
                print('  %-8s' % mo, {lab(c): sorted(t for t in ty) for c, ty in M.items()})
        for mo in ('combat', 'patrol', 'crouch', 'flee'):
            if mo not in g['modes']:
                continue
            row = []
            for w, (c, n, fl) in sorted(pool.items()):
                v, cl = verdict(g, mo, c, n)
                row.append('%s:%s' % (w[:14], v))
            print('  %s |' % mo, ' '.join(row))
print('\nweapons')
for w, x in sorted(pool.items()):
    print(' ', w, lab(x[0]), x[1], hex(x[2]), 'dual' if x[2] & (1 << 16) else '', 'dualonly' if x[2] & (1 << 17) else '')
