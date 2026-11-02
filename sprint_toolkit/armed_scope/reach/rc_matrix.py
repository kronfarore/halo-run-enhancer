r"""species x weapon animation matrix from rc_<map>.json graphs. Read-only."""
import json, os, glob, collections
OUT = os.path.dirname(os.path.abspath(__file__))
S = chr(92)
leaf = lambda n: n.rsplit(S, 1)[-1] if n else n
G, W = {}, {}
for f in sorted(glob.glob(os.path.join(OUT, 'rc_m*.json'))):
    d = json.load(open(f, encoding='utf-8'))
    for n, g in d['graphs'].items():
        G.setdefault(leaf(n), g)
    for w in d['weapon_palette']:
        W.setdefault(leaf(w['name']), (w.get('cls_3ac'), w.get('name_3b0')))
print('graphs', sorted(G))
print('weapons', W)
print({k: (g.get('parent') or {}).get('name') for k, g in G.items()})
ORDER = ['magnum', 'plasma_pistol', 'needler', 'plasma_rifle', 'target_laser', 'assault_rifle', 'dmr', 'sniper_rifle',
         'shotgun', 'grenade_launcher', 'needle_rifle', 'focus_rifle', 'plasma_repeater', 'concussion_rifle', 'spike_rifle',
         'rocket_launcher', 'flak_cannon', 'plasma_launcher', 'spartan_laser', 'energy_sword', 'gravity_hammer',
         'machinegun_turret', 'plasma_turret', 'saw']
for gn in ('grunt', 'jackal', 'elite_ai', 'brute', 'bugger', 'engineer', 'marine', 'hunter'):
    g = G.get(gn)
    if not g:
        print('NO GRAPH', gn)
        continue
    print('\n', gn, 'modes', len(g['modes']), 'weapon_list', g['weapon_list'], 'variants', g.get('variants'))
    modes = g['modes']
    interesting = [m for m in ('combat', 'crouch', 'flee', 'patrol', 'panic', 'shield', 'shield_crouch', 'murm', 'stunned', 'berserk', 'flaming', 'sprint', 'flight', 'overcharged_jitter') if m in modes]
    allc = sorted({c for cs in modes.values() for c in cs})
    print(' classes:', {c: sum(1 for m in modes.values() if c in m) for c in allc})
    for m in interesting:
        print('  %-20s' % m, {c: list(t) for c, t in modes[m].items()})
    print('  weapon        class/type   ' + ' '.join('%-8s' % m[:8] for m in interesting))
    wl = dict(map(tuple, g['weapon_list'])) if g['weapon_list'] else {}
    for w in ORDER:
        if w not in W:
            continue
        c, t = W[w]
        c2 = wl.get(t, c)
        row = []
        for m in interesting:
            cs = modes[m]
            if c2 in cs:
                ts = cs[c2]
                row.append('T' if t in ts else ('a' if 'any' in ts else 'x'))
            elif 'any' in cs:
                row.append('-')
            else:
                row.append('.')
        print('  %-14s %-8s %-4s %s' % (w, c2, t, ' '.join('%-8s' % r for r in row)))
print('\nlegend: T own type; a class+any; x class but no matching type and no any; - no class, mode has class any; . nothing')
