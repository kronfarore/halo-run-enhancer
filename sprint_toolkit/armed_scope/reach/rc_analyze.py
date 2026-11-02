r"""Summaries from rc_<map>.json. Read-only."""
import json, os, sys, glob, collections
OUT = os.path.dirname(os.path.abspath(__file__))
S = chr(92)
leaf = lambda n: n.rsplit(S, 1)[-1] if n else n
R = {}
for f in sorted(glob.glob(os.path.join(OUT, 'rc_m*.json'))):
    d = json.load(open(f, encoding='utf-8'))
    R[d['map']] = d
print('maps', list(R))

print('\n== T1 units per species (entries/spawn/cell, cell actors, protected, shared CT, shared weap)')
for k, d in R.items():
    print(k, 'scen sets', d['nscenario_sets'], d['multi'], 'slack', [(s['n4k'], s['total'], s['max']) if s else None for s in d['slack']], 'scnr part', d['scnr_partition'])
    for sp, u in sorted(d['units'].items(), key=lambda x: -x[1].get('entries', 0)):
        print('   %-18s ent %4d spawn %3d cell %4d prot %3d | cells %3d actors %3d shCT %3d shW %3d' % (
            sp, u.get('entries', 0), u.get('spawn', 0), u.get('cell', 0), u.get('protected', 0),
            d['cells_by_species'].get(sp, 0), d['actors_by_species'].get(sp, 0),
            d['cells_shared_ct'].get(sp, 0), d['cells_shared_weapon'].get(sp, 0)))

print('\n== T1b chars')
seen = {}
for k, d in R.items():
    for c in d['chars']:
        n = c['name']
        e = seen.setdefault(n, {'maps': [], 'unit': c.get('unit'), 'jmad': c.get('jmad'), 'parents': c.get('parents')})
        e['maps'].append(k)
for n, e in sorted(seen.items(), key=lambda x: str(x[0])):
    print(leaf(n), '|', leaf(e['unit']), '|', leaf(e['jmad']), '|', [leaf(p) for p in (e['parents'] or [])[1:]], '|', len(e['maps']))

print('\n== T2 weapon palette per map: name, class, wname, sets/total, closure sets, status')
allw = collections.OrderedDict()
for k, d in R.items():
    print(k)
    for w in d['weapon_palette']:
        n = leaf(w['name'])
        print('   %-32s c3ac=%s n3b0=%s c3e0=%s n3e4=%s sets=%s glob=%s closure=%s st=%s late=%s' % (
            n, w.get('cls_3ac'), w.get('name_3b0'), w.get('cls_3e0'), w.get('name_3e4'),
            len(w.get('sets', [])), w.get('global'),
            w.get('closure_sets') if w.get('closure_sets') == 'all' else len(w.get('closure_sets', [])),
            w.get('status'), w.get('late_n')))

print('\n== T2b species residency vs weapon residency: for each map+species, sets where species resident; for each palette weapon, sets of species missing closure')
SPEC = ('grunt', 'jackal', 'skirmisher', 'elite', 'brute', 'bugger', 'engineer', 'marine', 'hunter')
for k, d in R.items():
    print(k)
    bysp = {}
    for c in d['chars']:
        s = c.get('bipd_sets') or []
        if c.get('species'):
            sets = set(c.get('sets') or []) & set(s) if s and c.get('sets') else set(c.get('sets') or s)
            bysp.setdefault(c['species'], set()).update(sets)
    for sp, ss in sorted(bysp.items()):
        if not ss or sp not in d['units']:
            continue
        rows = []
        for w in d['weapon_palette']:
            cl = w.get('closure_sets')
            have = ss if cl == 'all' else ss & set(cl or [])
            obj = ss & set(w.get('sets') or []) if not w.get('global') else ss
            rows.append((leaf(w['name']), len(obj), len(have)))
        full = sum(1 for r in rows if r[2] == len(ss))
        miss = ['%s %d/%d' % (r[0], r[2], len(ss)) for r in rows if r[2] < len(ss)]
        print('  %-16s sets %2d: full %2d of %2d; short: %s' % (sp, len(ss), full, len(rows), ', '.join(miss)))

print('\n== T3 firing')
HAND = ('assault_rifle', 'concussion_rifle', 'dmr', 'energy_sword', 'flak_cannon', 'focus_rifle', 'gravity_hammer',
        'grenade_launcher', 'magnum', 'needle_rifle', 'needler', 'plasma_launcher', 'plasma_pistol', 'plasma_repeater',
        'plasma_rifle', 'rocket_launcher', 'shotgun', 'sniper_rifle', 'spartan_laser', 'spike_rifle', 'target_laser', 'saw')
for k, d in R.items():
    g = d['firing'].get('ai' + S + 'generic', {})
    wp = {leaf(x) for x in g.get('wp', [])}
    fp = {leaf(x) for x in g.get('fp', [])}
    print(k, 'generic wp', len(g.get('wp', [])), 'fp', len(g.get('fp', [])), 'noWP', [h for h in HAND if h not in wp], 'noFP', [h for h in HAND if h not in fp], 'unresolved', [x for x in g.get('fp', []) if x.startswith('0x')][:5])
print('own entries, m70_bonus / union:')
own = collections.defaultdict(set)
for k, d in R.items():
    for c, v in d['firing'].items():
        if v['wp'] or v['fp']:
            own[c].update(leaf(x) + ('' if x in v['fp'] else '(wp)') for x in v['wp'])
            own[c].update(leaf(x) + '(fp)' for x in v['fp'] if x not in v['wp'])
for c, v in sorted(own.items()):
    if c != 'ai' + S + 'generic':
        print('  ', c, sorted(v))

print('\n== T4 graphs (m70_bonus first seen) modes/classes')
def walk(g, acc, depth=0):
    if not g:
        return
    acc.append(g)
    walk(g.get('parent'), acc, depth + 1)
G = {}
for k, d in R.items():
    for n, g in d['graphs'].items():
        G.setdefault(n, (k, g))
for n, (k, g) in sorted(G.items()):
    chain = []
    walk(g, chain)
    print(n, 'map', k, 'chain', [leaf(x['name']) for x in chain], 'flags', g.get('flags'))
    for x in chain:
        cl = collections.defaultdict(list)
        for mo, cs in x['modes'].items():
            for c, ts in cs.items():
                cl[c].append(mo + '[' + ','.join(ts) + ']')
        print('   graph', leaf(x['name']), 'modes', len(x['modes']), 'wlist', len(x['weapon_list']), x['weapon_list'][:40])
        print('    variants', x.get('variants'))
        for c, ms in sorted(cl.items()):
            print('    %-12s %s' % (c, ' '.join(ms)))

json.dump({n: g for n, (k, g) in G.items()}, open(os.path.join(OUT, 'graphs_all.json'), 'w'), default=str)
print('\n== weapon_dist')
for k, d in R.items():
    print(k, {s: v for s, v in d['weapon_dist'].items()})
    print('   spawn', d['spawn_weapon'])
