import sys,os,re
T=r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit'
sys.path.insert(0,T)
import ttk_common as t
for kit in ('H3EK','H3ODSTEK'):
    v=t.flatten(kit,'ai'+chr(92)+'generic.character')
    print(kit,len(v))
    for k,(ty,val) in v.items():
        if k.endswith('/weapon') and ('weapons properties' in k or 'firing pattern properties' in k):
            print(k[:40],val)
