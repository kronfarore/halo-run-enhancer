r"""Read-only: find code using given strings in H3EK sapien.exe; dump disassembly around it,
annotating lea-to-string. python xref.py "<needle>" [before] [after]"""
import re, struct, sys
import pefile, capstone
P = r'F:\SteamLibrary\steamapps\common\H3EK\sapien.exe'
pe = pefile.PE(P, fast_load=True)
d = open(P, 'rb').read()
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b'\0').decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
def off2rva(o):
    for n, va, vs, pr, sz in secs:
        if pr <= o < pr + sz:
            return va + o - pr
def rva2off(r):
    for n, va, vs, pr, sz in secs:
        if va <= r < va + sz:
            return pr + r - va
text = next(s for s in secs if s[0] == '.text')
T = d[text[3]:text[3] + text[4]]
trva = text[1]


def cstr(rva):
    o = rva2off(rva)
    if o is None:
        return None
    e = d.find(b'\0', o, o + 300)
    s = d[o:e]
    if len(s) >= 4 and all(32 <= c < 127 for c in s):
        return s.decode()


def xrefs(rva):
    out = []
    for m in re.finditer(rb'[\x48\x4C]\x8D[\x05\x0D\x15\x1D\x25\x2D\x35\x3D]', T):
        i = m.start()
        disp = struct.unpack_from('<i', T, i + 3)[0]
        if trva + i + 7 + disp == rva:
            out.append(trva + i)
    return out


def dump(rva, before, after):
    # find a start by decoding linearly from before; resync by trying offsets
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    start = rva - before
    o = start - trva
    best = None
    for k in range(0, 16):
        ok = False
        for ins in md.disasm(T[o + k:o + k + before + 16], trva + o + k):
            if ins.address == rva:
                ok = True; break
        if ok:
            best = k; break
    for ins in md.disasm(T[o + (best or 0):o + before + after], trva + o + (best or 0)):
        note = ''
        mo = re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]', ins.op_str)
        if mo:
            t = ins.address + ins.size + (int(mo.group(2), 16) * (1 if mo.group(1) == '+' else -1))
            s = cstr(t)
            note = '   ; "%s"' % s if s else '   ; rva %x' % t
        print('%x: %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, note))


needle = sys.argv[1].encode()
before = int(sys.argv[2]) if len(sys.argv) > 2 else 200
after = int(sys.argv[3]) if len(sys.argv) > 3 else 60
for m in re.finditer(re.escape(needle), d):
    o = m.start()
    s = d.rfind(b'\0', 0, o) + 1
    r = off2rva(s)
    print('string', d[s:d.find(b'\0', o)][:100], hex(r) if r else None)
    for x in xrefs(r) if r else []:
        print('--- xref', hex(x))
        dump(x, before, after)
