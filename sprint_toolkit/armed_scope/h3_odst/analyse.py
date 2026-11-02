r"""Tabulate census JSON: units, palette, firing, residency."""
import json, glob, os, sys, collections
S = chr(92)
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
d = json.load(open(os.path.join(TOOL, 'halo.json'), encoding='utf8'))
ORDER3 = ['010_jungle', '020_base', '030_outskirts', '040_voi', '050_floodvoi', '070_waste', '100_citadel', '110_hc', '120_halo']
ORDERO = ['h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300']
MID = lambda n: n.split('_')[0]
OV = {'Magnum': 'objects\\weapons\\pistol\\automag\\automag',
      'Auto Magnum': 'objects\\weapons\\pistol\\automag\\automag',
      'SMG': 'objects\\weapons\\rifle\\smg_silenced\\smg_silenced',
      'Silenced SMG': 'objects\\weapons\\rifle\\smg_silenced\\smg_silenced',
      'Plasma Rifle': 'objects\\weapons\\rifle\\plasma_rifle_red\\plasma_rifle_red'}


def tagmap(game):
    out = {}
    for w, wd in d['Player Modifiers']['Specific Weapon Modifier'].items():
        for _c, c in wd.items():
            if not isinstance(c, dict):
                continue
            t = c.get('tag')
            if isinstance(t, dict):
                t = t.get(game) or t.get('Halo 3')
            if isinstance(t, str) and t.startswith('weap '):
                out.setdefault(w, t.split(' & ')[0].split(' ', 1)[1])
                break
    return out


FAM = [('Grunt', ('grunt',)), ('Jackal', ('jackal',)), ('Brute', ('brute',)), ('Elite', ('elite',)),
       ('Dervish', ('dervish',)), ('Bugger', ('bugger',)), ('Hunter', ('hunter',)),
       ('Engineer', ('engineer',)), ('Marine', ('marine', 'odst', 'civilian', 'johnson', 'miranda')),
       ('Flood Combat', ('floodcombat', 'flood_combat', 'combat')), ('Flood Carrier', ('carrier',)),
       ('Flood Infection', ('infection',)), ('Flood Pure', ('pure', 'ranged', 'tank', 'stalker')),
       ('Sentinel', ('sentinel', 'guilty', 'monitor'))]


def fam(c):
    l = c.lower().rsplit(S, 1)[-1]
    p = c.lower()
    if 'flood' in p:
        for f, w in FAM[-5:]:
            if any(x in l for x in w):
                return f
        return 'Flood other'
    if 'brute_stalker' in l:
        return 'Brute'
    for f, w in FAM:
        if any(x in p for x in w):
            return f
    return 'other:' + l


for game, order in (('Halo 3', ORDER3), ('Halo 3: ODST', ORDERO)):
    print('\n########', game)
    tm = tagmap(game); tm['Magnum'] = tm.get('Pistol') or tm.get('Magnum')
    M = d['Missions'][game]
    fam_tot = collections.defaultdict(lambda: collections.Counter())
    for n in order:
        p = 'out/%s.json' % n
        if not os.path.exists(p):
            print('missing', n); continue
        r = json.load(open(p))
        mid = MID(n)
        fc = collections.defaultdict(collections.Counter)
        for c, v in r['units'].items():
            f = fam(c)
            for k, x in v.items():
                fc[f][k] += x
            fam_tot[f]['levels'] += 1
        src = r['h3']['actors'] if 'h3' in r else r['odst']['cell_actors']
        ac = collections.Counter()
        for c, x in src.items():
            ac[fam(c)] += x
        print('\n==', n, r['size'] // 2**20, 'MB  pal', len(r['weapon_palette']), 'char pal', len(r['char_palette']))
        for f in sorted(fc):
            v = fc[f]
            print('  %-16s entries %-4d protected %-4d actors %-4d %s' % (
                f, v['entries'], v['protected'], ac.get(f, 0),
                {k: x for k, x in v.items() if k.startswith('kind')}))
        if 'odst' in r:
            o = r['odst']
            print('  cells: elements', o['cell_elements'], 'refs', o['cell_refs'], 'share', json.dumps(o['share']))
            print('  spawn weap', o['spawn_weapon'], 'cells without weapon array', {k.rsplit(S, 1)[-1]: v for k, v in o['cells_no_w1'].items()},
                  'multi w1 cells', o['cells_w1_multi'], 'spawn variants', o['spawn_variants'])
        else:
            print('  ', r['h3']['ft_weapon'], r['h3']['loc_weap'], 'variants', r['h3']['loc_variants'])
        # pool vs palette
        pool = list(M[mid].get('weapons', [])) if mid in M else []
        tur = list(M[mid].get('turrets', [])) if mid in M else []
        pal = {str(x).lower() for x in r['weapon_palette'] if x}
        tags = {k.lower() for k in r['weap_tags']}
        miss_p, miss_t = [], []
        for w in pool + tur + ['SAW']:
            t = (OV.get(w) if game != 'Halo 3' and w in OV else None) or tm.get(w)
            if t is None:
                miss_t.append(w + '(?tag)'); continue
            if t.lower() not in tags:
                miss_t.append(w)
            elif t.lower() not in pal:
                miss_p.append(w)
        print('  pool %d+%d: tag absent %s | tag present not in palette %s' % (len(pool), len(tur), miss_t, miss_p))
        # generic
        gen = r['chars'].get('ai' + S + 'generic', {})
        gp = {str(x).lower() for x in gen.get('props', []) if x}
        gf = {str(x).lower() for x in gen.get('fpp', []) if x}
        nofire = []
        for w in pool + tur + ['SAW']:
            t = (OV.get(w) if game != 'Halo 3' and w in OV else None) or tm.get(w)
            if t and t.lower() in tags:
                a, b = t.lower() in gp, t.lower() in gf
                if not (a and b):
                    nofire.append('%s[%s%s]' % (w, 'P' if a else '-', 'F' if b else '-'))
        print('  ai\\generic: props', len(gen.get('props', [])), 'fpp', len(gen.get('fpp', [])), 'missing', nofire)
    print('\nfamilies', {k: dict(v) for k, v in fam_tot.items()})
