import json,sys
S=chr(92)
r=json.load(open('graphs/010_jungle.json'))
for p,g in r.items():
    print(p,'parent',g['parent'],'modes',len(g['modes']),'WL',len(g['weapon_list']))
    print('  WL',g['weapon_list'][:40])
    for mo in ('any','combat','flee','crouch','patrol','stand'):
        if mo in g['modes']:
            print('  ',mo,{c:{t:('idle' in a) for t,a in ty.items()} for c,ty in g['modes'][mo].items()})
    print('  allmodes',list(g['modes'].keys()))
