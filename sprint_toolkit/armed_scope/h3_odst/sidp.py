import sys,os,io,contextlib
TOOL=r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0,TOOL); os.chdir(TOOL)
import halo_patch as hp
with contextlib.redirect_stdout(io.StringIO()):
    m=hp.open_map(r'E:\HaloBaselines\halo3\maps\040_voi.map','Halo 3')
for s in (0xd2,0x89,0x1f4,0xC,0xEC,0x8C):
    print(hex(s),m.resolve_stringid(s))
