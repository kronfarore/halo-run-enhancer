import sys,os,io,contextlib,struct,json
TOOL=r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0,TOOL); os.chdir(TOOL)
import halo_patch as hp
with contextlib.redirect_stdout(io.StringIO()):
    m=hp.open_map(sys.argv[2],sys.argv[1])
m._locate_stringids()
print('cnt',m.str_tbl_count,'strip',m._sid_strip)
raw=set()
out={}
for p,bb in m.find_tags('weap','*'):
    wc=m.u32(bb+(0x3DC if sys.argv[1]=='Halo 3' else 0x3EC)); wn=m.u32(bb+(0x3E0 if sys.argv[1]=='Halo 3' else 0x3F0))
    out[p.rsplit(chr(92),1)[-1]]=(hex(wc),m.resolve_stringid(wc),hex(wn),m.resolve_stringid(wn))
    raw.add(wc)
print(out)
for r in sorted(raw):
    ns=(r>>16)&0xff; i=r&0xffff
    print(hex(r),ns,i)
    for st in sorted({0x4BB,0x4C3,0x550,0x55A,0xABA,0xACA,0xB4C,0xB5C,0xBA2,0xBB2,0xBC2,0xBEF,0xBFF,0xC0E,0xC38,0xC47,0xC4C,0xC5B,0xBDB,0xBEE,0xC76,0xC89,0xCCE,0xCE1,0xD1A,0xD2F,0xD7E,0xD96,0xDD8,0xE24,0xE73,0xE8B}):
        s=m._string_at(m._sid_strip+st+i-1) if m._sid_strip+st+i-1<m.str_tbl_count else None
        if s and len(s)<12: print('   ',hex(st),s)
    break
