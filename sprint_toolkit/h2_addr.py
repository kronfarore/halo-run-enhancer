r"""Translate a runtime address into a halo2.dll file offset and disassemble it.

For the round trip with a debugger: Cheat Engine and x64dbg report code as
`halo2.dll+6EF401` (module-relative). The dll's preferred image base is
0x180000000, so a module-relative offset is just VA - 0x180000000, and the file
offset comes from the section table. This does that conversion in both directions
and prints the surrounding instructions, so a finding from a live session can be
turned into a patch site without hand arithmetic.

    python h2_addr.py halo2.dll+6EF401     # what a debugger prints
    python h2_addr.py 0x1806EF401          # a virtual address
    python h2_addr.py file:0x6EE801        # a file offset
    python h2_addr.py halo2.dll+6EF401 --before 8 --count 24
"""
import argparse
import os
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo2\halo2.dll')


def _pe(path):
    pe = pefile.PE(path, fast_load=True)
    return pe, pe.OPTIONAL_HEADER.ImageBase


def va_to_off(pe, base, va):
    rva = va - base
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress), s.Name.decode().strip('\0')
    return None, None


def off_to_va(pe, base, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return base + s.VirtualAddress + (off - s.PointerToRawData)
    return None


def parse(arg, base):
    """Accept `halo2.dll+6EF401`, a bare VA, or `file:0x...`."""
    a = arg.strip().lower()
    if a.startswith('file:'):
        return ('file', int(a[5:], 0))
    if '+' in a:                       # module-relative, as debuggers print it
        return ('va', base + int(a.split('+', 1)[1], 16))
    v = int(a, 0)
    return ('va', v if v >= base else base + v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('address', help='halo2.dll+OFFSET, a VA, or file:OFFSET')
    ap.add_argument('--dll', default=DLL)
    ap.add_argument('--before', type=int, default=16, help='bytes of context before')
    ap.add_argument('--count', type=int, default=20, help='instructions to print')
    a = ap.parse_args(argv)

    if not os.path.exists(a.dll):
        raise SystemExit('no such file: %s' % a.dll)
    pe, base = _pe(a.dll)
    kind, val = parse(a.address, base)
    if kind == 'file':
        off, va = val, off_to_va(pe, base, val)
        sec = va_to_off(pe, base, va)[1] if va else None
    else:
        va = val
        off, sec = va_to_off(pe, base, va)
    if off is None:
        raise SystemExit('address 0x%X is not in a mapped section' % va)

    print('module-relative : halo2.dll+%X' % (va - base))
    print('virtual address : 0x%09X' % va)
    print('file offset     : 0x%X   (section %s)' % (off, sec))
    print('patch tool      : add an entry to h2_dll_patch.py with offset 0x%X' % off)
    print()

    d = open(a.dll, 'rb').read()
    # Back up a little and let the decoder resync; x86 is self-synchronising in
    # practice, but the first instruction or two may be nonsense.
    start = max(0, off - a.before)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for i, ins in enumerate(md.disasm(d[start:start + a.before + 96], off_to_va(pe, base, start))):
        mark = '  <<< HERE' if ins.address == va else ''
        print('  0x%09X  %-24s %s %s%s'
              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
        if i >= a.count:
            break


if __name__ == '__main__':
    main()
