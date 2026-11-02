import json, os, re, sys, collections
T = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
S = chr(92)
L = lambda v: str(v).rsplit(S, 1)[-1] if v else None
LV = [('m10_crash', 'Dawn'), ('m020', 'Requiem'), ('m30_cryptum', 'Forerunner'), ('m60_rescue', 'Infinity'), ('m40_invasion', 'Reclaimer'), ('m70_liftoff', 'Shutdown'), ('m80_delta', 'Composer'), ('m90_sacrifice', 'Midnight')]
H = json.load(open(os.path.join(T, 'halo.json'), encoding='utf8'))['Missions']['Halo 4']
pool_all = set()
for mid, _t in LV:
    pool_all |= set(H[mid]['weapons'])
print('pool cards', sorted(pool_all))
rows = {}
for mid, t in LV:
    gp, cp = '../graph_%s.json' % mid, '../census_%s.json' % mid
    if not (os.path.exists(gp) and os.path.exists(cp)):
        print('missing', mid)
        continue
    g, c = json.load(open(gp)), json.load(open(cp))
    gen = next(v for k, v in g['fire'].items() if k.lower().endswith('ai' + S + 'generic'))
    wp = {L(x) for x in gen['wp'] if x}
    fp = {L(a) for a, _k in gen['fp'] if a}
    pal = {x for x in c['weapons'] if x}
    cards = collections.defaultdict(list)
    for w, r in c['weap_res'].items():
        if r.get('card'):
            cards[r['card']].append(w)
    print('==', mid, t, 'halo.json', len(H[mid]['weapons']), 'pal', len(pal), 'cards in pal', len(cards))
    print('  in halo.json not in palette:', sorted(set(H[mid]['weapons']) - set(cards)))
    print('  palette cards not in halo.json list:', sorted(set(cards) - set(H[mid]['weapons'])))
    nofire = {}
    for card, tags in sorted(cards.items()):
        st = [(x, x in wp, x in fp) for x in tags]
        if not any(a and b for _x, a, b in st):
            nofire[card] = st
    print('  cards w/o a full ai\\generic entry:', nofire)
    print('  variants', {k: v for k, v in cards.items() if len(v) > 1})
    print('  focus rifle pal', any('focus' in x for x in pal), 'weap in map', [k for k in g['weapons'] if 'focus' in k][:2])
    print('  gen null', sum(1 for x in gen['wp'] if not x), 'of', len(gen['wp']))
