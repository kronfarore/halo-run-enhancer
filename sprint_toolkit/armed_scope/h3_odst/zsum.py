import json, glob, os
S = chr(92)
ORDER = ['010_jungle', '020_base', '030_outskirts', '040_voi', '050_floodvoi', '070_waste', '100_citadel', '110_hc', '120_halo',
         'h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300']
for n in ORDER:
    r = json.load(open('out/%s.json' % n))
    z = r['zone']
    dz = z.get('designer_zones', [])
    en = dz.index('dz_enhancer') if 'dz_enhancer' in dz else None
    zs = z['zone_sets']
    full = sum(1 for a in zs if en is not None and (a[2] >> en) & 1)
    forb = sum(1 for a in zs if en is not None and (a[3] >> en) & 1)
    wr = z.get('weap_res', {})
    pal = sorted({p for p in r['weapon_palette'] if p})
    good, part, none_ = [], [], []
    for p in pal:
        c = wr.get(p, {})
        m = c.get('mode', {})
        lst = m.get('dz', []); g = m.get('glob', [])
        leaf = p.rsplit(S, 1)[-1]
        if not m:
            none_.append(leaf + '(no mode)')
        elif en is not None and any(x.startswith(str(en)) and x[-1] in 'RD' for x in lst) or 'R' in g:
            good.append(leaf)
        elif lst or g:
            part.append('%s[%s|%s]' % (leaf, ','.join(lst[:6]), ','.join(g)))
        else:
            none_.append(leaf + '(chunks %s)' % m.get('chunks'))
    print('%-14s dz %-40s zonesets %-3d enh-req %-3d forb %d palette %d: whole-level %d partial %d none %d' % (
        n, ','.join(str(q) for q in dz)[:40], len(zs), full, forb, len(pal), len(good), len(part), len(none_)))
    if part or none_:
        print('    partial', ' '.join(part)[:600])
        print('    none   ', ' '.join(none_)[:400])
