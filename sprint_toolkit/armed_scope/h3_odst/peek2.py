import json, glob, os, sys
S = chr(92)
for f in sorted(glob.glob('out/*.json')):
    r = json.load(open(f))
    z = r['zone']
    print('==', r['map'], 'dz', z.get('designer_zones'), 'n_dzm', z.get('n_dzm'), 'global', z.get('n_global'))
    zs = z['zone_sets']
    print('  zone sets', len(zs), 'req', sorted({a[2] for a in zs}), 'forb', sorted({a[3] for a in zs}))
    pal = [p for p in r['weapon_palette'] if p]
    print('  palette', len(r['weapon_palette']), 'weap tags', len(r['weap_tags']))
    wr = z.get('weap_res', {})
    idx = {n: i for i, n in enumerate(z.get('designer_zones', []))}
    en = idx.get('dz_enhancer')
    for p in sorted(set(pal)):
        leaf = p.rsplit(S, 1)[-1]
        c = wr.get(p)
        if c is None:
            print('   ', leaf, 'NO WEAP TAG DATA'); continue
        m = c.get('mode', {}); j = c.get('jmad', {})
        print('    %-26s mode chunks %-3s dz %-30s glob %-14s | jmad %-3s %s' % (
            leaf, m.get('chunks'), ','.join(m.get('dz', []))[:30], ','.join(m.get('glob', [])),
            j.get('chunks'), ','.join(j.get('dz', []))[:24]))
    if len(sys.argv) > 1:
        break
