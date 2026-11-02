import json,sys
S=chr(92)
R=json.load(open('graphs/%s.json'%sys.argv[1]))
for p,g in R.items():
    if p=='__weap__' or not any(k in p for k in sys.argv[2:]): continue
    print('#',p,'modes',len(g['modes']))
    for mo in ('combat','crouch'):
        M=g['modes'].get(mo,{})
        print(' ',mo,{c:{t:len(a) for t,a in ty.items()} for c,ty in M.items()})
    M=g['modes'].get('combat',{})
    for c in M:
        for t,a in M[c].items():
            if t in ('any','ar','0x5CE','rl','br','0x5D2') and c in('0x312','rifle','0x310','missile'):
                print('   ',c,t,sorted(a)[:44])
