import sys,os,json,re
T=r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0,os.path.join(T,'sprint_toolkit'));sys.path.insert(0,T)
import ttk_common as t
v=t.flatten('H4EK',r'ai\generic.character')
print(len(v))
ks=[k for k in v if 'weapon' in k.lower() and ('tag' in str(v[k][0]).lower() or 'weapon' == k.rsplit('/',1)[-1])]
print(ks[:8])
wp={};fp={}
for k,(ty,val) in v.items():
    kl=k.lower()
    if kl.endswith('/weapon') or kl.endswith('/weapon/name'):
        if kl.startswith('weapons properties'): wp[k]=val
        if kl.startswith('firing pattern properties'): fp[k]=val
        if kl.startswith('extreme'): fp[k]=val
json.dump({'wp':wp,'fp':fp},open('kit_generic.json','w'),indent=0)
print(len(wp),len(fp)); print(list(wp.items())[:4]); print(list(fp.items())[:4])
