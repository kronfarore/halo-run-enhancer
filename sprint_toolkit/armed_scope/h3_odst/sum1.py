import json,glob,collections
S=chr(92)
ORD=['010_jungle','020_base','030_outskirts','040_voi','050_floodvoi','070_waste','100_citadel','110_hc','120_halo']
t=collections.Counter()
for n in ORD:
    r=json.load(open('out/%s.json'%n))
    print(n,'ft weap',r['h3']['ft_weapon'],'loc',r['h3']['loc_weap'])
for n in ORD:
    r=json.load(open('out/%s.json'%n))
    for k,v in r['units'].items():
        l=k.rsplit(S,1)[-1]
        if any(w in k for w in ('flood','jackal')):
            pass
r=json.load(open('out/100_citadel.json'))
print({k.rsplit(S,1)[-1]:v for k,v in r['unit_weapons'].items() if 'flood' in k or 'elite' in k})
r=json.load(open('out/050_floodvoi.json'))
print({k.rsplit(S,1)[-1]:v for k,v in r['unit_weapons'].items() if 'flood' in k or 'elite' in k})
print(r['h3']['actors'])
