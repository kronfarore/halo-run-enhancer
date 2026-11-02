import json, re, collections
S = chr(92)
txt = open('analysis.txt').read()
cur = None; game = None
T = {'Halo 3': collections.defaultdict(collections.Counter), 'Halo 3: ODST': collections.defaultdict(collections.Counter)}
for line in txt.splitlines():
    if line.startswith('########'):
        game = line[9:].strip()
    m = re.match(r'  (\S.*?)\s+entries (\d+)\s+protected (\d+)\s+actors (\d+)', line)
    if m:
        f = m.group(1)
        c = T[game][f]
        c['levels'] += 1; c['entries'] += int(m.group(2)); c['prot'] += int(m.group(3)); c['actors'] += int(m.group(4))
for g, t in T.items():
    print(g)
    for f, c in sorted(t.items(), key=lambda kv: -kv[1]['entries']):
        print('  %-18s levels %-2d entries %-5d script/vehicle %-5d actors %d' % (f, c['levels'], c['entries'], c['prot'], c['actors']))
ORD = ['h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300']
A = collections.Counter()
for n in ORD:
    r = json.load(open('out/%s.json' % n))
    o = r['odst']
    s = o['share']['w1']
    A['cells'] += o['cell_elements']; A['refs'] += o['cell_refs']; A['w1blocks'] += s['blocks']; A['w1shared'] += s['shared_blocks']
    A['w1mixed'] += s['mixed_species']; A['cells_on_shared'] += s['cells_on_shared']
    A['spawn_w'] += o['spawn_weapon'].get('weap>=0', 0); A['spawn_n'] += o['spawn_weapon'].get('weap-1', 0)
    print(n, 'cells', o['cell_elements'], 'w1 blocks', s['blocks'], 'shared', s['shared_blocks'], 'mixed', s['mixed_species'], 'cells on shared', s['cells_on_shared'],
          'no w1', sum(v for k, v in o['cells_no_w1'].items() if 'hunter' not in k and 'engineer' not in k))
print(dict(A))
r = json.load(open('out/020_base.json'))
print(r['zone']['designer_zones'], [(hex(a[2]), hex(a[3])) for a in r['zone']['zone_sets']])
