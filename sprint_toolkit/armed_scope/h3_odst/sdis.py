import sys
sys.argv=[sys.argv[0]]+sys.argv[1:]
src=open('xref.py').read().split("needle = sys.argv[1]")[0]
exec(src)
a=int(sys.argv[1],16); n=int(sys.argv[2],16)
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
o=a-trva
for ins in md.disasm(T[o:o+n],a):
    note=''
    mo=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',ins.op_str)
    if mo:
        t=ins.address+ins.size+(int(mo.group(2),16)*(1 if mo.group(1)=='+' else -1))
        s=cstr(t); note='   ; "%s"'%s if s else ''
    print('%x: %-8s %s%s'%(ins.address,ins.mnemonic,ins.op_str,note))
