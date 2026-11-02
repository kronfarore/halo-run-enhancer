import json, sys
S = chr(92)
r = json.load(open('species/%s.json' % sys.argv[1]))
for u, x in r['models'].items():
    if any(w in u for w in sys.argv[2:]):
        print(u, 'default', x['default_variant'], 'model', x['model'])
        print('  unit weapons', {k: v for k, v in x['unit_weapons'].items() if any(v)})
        for v in x['variants']:
            print('  var', v['name'], 'objs', [(a, b, str(c).rsplit(S, 1)[-1]) for a, b, c in v['objects']], 'regions', [q for q in v['regions'] if 'shield' in str(q).lower()])
for c, x in r['chars'].items():
    if any(w in c for w in sys.argv[2:]):
        print(c.rsplit(S, 1)[-1], 'retreat', x['retreat'], 'charge', x['charge'], 'flags', [hex(f) for f in x['flags']], 'unit', str(x['unit']).rsplit(S, 1)[-1])
