import json
S = chr(92)
ORDER = ['010_jungle', '020_base', '030_outskirts', '040_voi', '050_floodvoi', '070_waste', '100_citadel', '110_hc', '120_halo',
         'h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300']
for n in ORDER:
    r = json.load(open('out/%s.json' % n))
    z = r['zone']
    zs = z['zone_sets']
    wr = z.get('weap_res', {})
    alln = None
    for a in zs:
        alln = a[2] if alln is None else alln & a[2]
    pal = sorted({p for p in r['weapon_palette'] if p})
    res = {}
    gaps = {}
    for p in pal:
        c = wr.get(p, {})
        m = c.get('mode', {})
        if not m:
            continue
        leaf = p.rsplit(S, 1)[-1]
        if 'R' in m.get('glob', []):
            res[leaf] = len(zs); continue
        bits = {int(x[:-1]) for x in m.get('dz', []) if x[-1] in 'RD'}
        ok = sum(1 for a in zs if any((a[2] >> b) & 1 for b in bits))
        res[leaf] = ok
        if ok < len(zs):
            gaps[leaf] = ok
    print('%-14s zone sets %-2d zones-required-by-all mask 0x%X; palette models in all zone sets: %d of %d; gaps %s' % (
        n, len(zs), alln or 0, len(res) - len(gaps), len(res), gaps))
