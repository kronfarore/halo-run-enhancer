r"""Locate the HaloScript function table in halo3odst.dll, and the code behind a
named script function.

This is the same anchor that cracked the Halo 2 camo problem: a script function whose
job is exactly the operation you care about gives you its implementation for free, and
from there the data layout and any guard clauses fall out.

The one that matters here is `unit_add_equipment <unit> <starting_profile> <boolean>`
-- the engine's own "apply a starting profile to a unit". Kikowani's starting weapons
fail inside that operation, so its evaluator is where the refusal lives.

Halo's table is an array of pointers to function definitions; a definition holds a
return type, a pointer to the name string, then the parse and evaluate routines. The
name string is the way in: find its VA, find the qword pointing at it, and the
definition is at hand.

    python odst_hs_table.py --find unit_add_equipment
    python odst_hs_table.py --find unit_add_equipment --disasm 120
    python odst_hs_table.py --table                  # sanity: dump the first entries
"""
import argparse
import struct

import pefile

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo3odst\halo3odst.dll')


class Image:
    def __init__(self, path=DLL):
        self.path = path
        self.pe = pefile.PE(path, fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.data = open(path, 'rb').read()
        self.sections = [(s.VirtualAddress, s.Misc_VirtualSize,
                          s.PointerToRawData, s.SizeOfRawData,
                          s.Name.rstrip(b'\0').decode('latin-1'))
                         for s in self.pe.sections]

    def off2va(self, off):
        for rva, vsize, praw, sraw, _ in self.sections:
            if praw <= off < praw + sraw:
                return self.base + rva + (off - praw)
        return None

    def va2off(self, va):
        rva = va - self.base
        for r, vsize, praw, sraw, _ in self.sections:
            if r <= rva < r + max(vsize, sraw):
                o = praw + (rva - r)
                return o if o < len(self.data) else None
        return None

    def section_of(self, off):
        for rva, vsize, praw, sraw, name in self.sections:
            if praw <= off < praw + sraw:
                return name
        return '?'

    def find_qword_refs(self, value, limit=32):
        """Every file offset holding this 8-byte little-endian value."""
        needle = struct.pack('<Q', value)
        out, i = [], self.data.find(needle)
        while i >= 0 and len(out) < limit:
            out.append(i)
            i = self.data.find(needle, i + 1)
        return out

    def find_dword_refs(self, value, limit=32):
        needle = struct.pack('<I', value)
        out, i = [], self.data.find(needle)
        while i >= 0 and len(out) < limit:
            out.append(i)
            i = self.data.find(needle, i + 1)
        return out


def find_name(img, name):
    """File offsets of the exact NUL-terminated string `name`."""
    needle = name.encode() + b'\0'
    out, i = [], img.data.find(needle)
    while i >= 0:
        if i == 0 or img.data[i - 1] in (0, 0x20):
            out.append(i)
        i = img.data.find(needle, i + 1)
    return out


def disasm(img, va, count=60, stop=True):
    import capstone
    off = img.va2off(va)
    if off is None:
        return ['<va 0x%X not mapped>' % va]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = False
    out = []
    for ins in md.disasm(img.data[off:off + count * 15], va):
        out.append('  0x%X  %-24s %s' % (ins.address, ins.mnemonic, ins.op_str))
        if len(out) >= count:
            break
        if stop and ins.mnemonic in ('ret', 'jmp') and len(out) > 4:
            out.append('  ---')
            break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dll', default=DLL)
    ap.add_argument('--find', help='script function name to locate')
    ap.add_argument('--disasm', type=int, default=0,
                    help='disassemble this many instructions at each candidate')
    ap.add_argument('--table', action='store_true')
    ap.add_argument('--at', help='disassemble at this VA (hex), e.g. 0x1802192B0')
    ap.add_argument('--count', type=int, default=80)
    ap.add_argument('--raw', action='store_true',
                    help='keep disassembling past jmp/ret instead of stopping')
    a = ap.parse_args(argv)

    if a.at:
        img = Image(a.dll)
        for line in disasm(img, int(a.at, 16), a.count, stop=not a.raw):
            print(line)
        return 0

    img = Image(a.dll)
    print('%s  base 0x%X  %d section(s)' % (a.dll.rsplit('\\', 1)[-1], img.base,
                                            len(img.sections)))
    for rva, vsize, praw, sraw, name in img.sections:
        print('  %-8s rva 0x%08X size 0x%08X  raw 0x%08X' % (name, rva, vsize, praw))

    if not a.find:
        return 0

    offs = find_name(img, a.find)
    print('\n"%s": %d string occurrence(s)' % (a.find, len(offs)))
    for off in offs:
        va = img.off2va(off)
        print('  file 0x%08X  va 0x%X  section %s' % (off, va or 0, img.section_of(off)))
        if va is None:
            continue
        refs = img.find_qword_refs(va)
        print('    %d qword reference(s) to it' % len(refs))
        for r in refs:
            rva = img.off2va(r)
            # A Halo hs_function_definition puts the name pointer a little way in;
            # the routine pointers follow it. Show the neighbourhood as qwords.
            words = struct.unpack_from('<8Q', img.data, max(0, r - 16))
            print('      def @file 0x%08X va 0x%X  [%s]'
                  % (r, rva or 0, ' '.join('0x%X' % w for w in words[:6])))
            if a.disasm:
                for w in words:
                    o = img.va2off(w) if w else None
                    if o is not None and img.section_of(o) == '.text':
                        print('      -> code at 0x%X' % w)
                        for line in disasm(img, w, a.disasm):
                            print('    ' + line)
                        break
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
