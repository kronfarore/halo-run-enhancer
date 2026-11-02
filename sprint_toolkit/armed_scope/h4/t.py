import sys,time
sys.path.insert(0,'..')
sys.path.insert(0,'.')
from lib import *
t=time.time(); m=op('m10_crash'); print('open',time.time()-t, type(m.data), len(m.data), flush=True)
t=time.time(); x=list(m.find_tags('jmad','*')); print('find',time.time()-t,len(x),flush=True)
b=[v for n,v in x if str(n).endswith('storm_grunt')][0]
t=time.time(); y=block(m,b+0x13C,0x30); print('blk',time.time()-t,flush=True)
t=time.time()
for md in y[:5]: m.resolve_stringid(m.u32(md))
print('sid5',time.time()-t,flush=True)
t=time.time()
for i in range(2000): hp._tag_name_by_id(m,m.u32(b+0xC)|0)
print('tagname2000',time.time()-t,flush=True)
