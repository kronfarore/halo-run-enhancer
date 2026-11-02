import json
r=json.load(open('out/020_base.json')); print(r['zone']['designer_zones'],[(hex(a[2]),hex(a[3])) for a in r['zone']['zone_sets']])
for k,v in list(r['zone']['weap_res'].items()):
    if any(w in k for w in ('spike_rifle','brute_shot','gravity_hammer','assault_rifle\')): print(k,v.get('mode'))
