import json
d = json.load(open('kit_generic.json'))
S = chr(92)


def L(v):
    return v.split(',')[0].rsplit(S, 1)[-1]


wp = [L(v) for k, v in d['wp'].items()]
fp = [L(v) for k, v in d['fp'].items() if k.startswith('firing')]
xp = [L(v) for k, v in d['fp'].items() if k.startswith('extreme')]
print(len(wp), len(fp), len(xp))
print('WP', sorted(wp))
print('FP-WP', sorted(set(fp) - set(wp)))
print('WP-FP', sorted(set(wp) - set(fp)))
print('XP', sorted(xp)[:60])
