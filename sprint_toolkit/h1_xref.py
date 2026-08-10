r"""Find every instruction in halo1.dll that references a given address.

This is the static replacement for x64dbg's "find what accesses this address". It
needs no debugger and no running game, and unlike a breakpoint it finds ALL the
referencing sites at once, including ones the current playthrough never executes.

How it works, and why it is exact rather than a heuristic: on x64, code reaches a
static like the score counter through RIP-relative addressing, where the encoded
32-bit displacement is `target - (address of the NEXT instruction)`. So for every
candidate position p we can compute the displacement that WOULD point at our target
and compare it with the four bytes actually there. That is a single linear pass with
no disassembly, and it cannot miss a reference. Each numeric hit is then confirmed by
disassembling backwards until an instruction lands exactly on it -- which also tells
us whether the site READS or WRITES.

    python h1_xref.py halo1.dll+1A2B3C4       # what a debugger / scorescan prints
    python h1_xref.py 0x1801A2B3C4            # a virtual address
    python h1_xref.py file:0x1234567          # a file offset
    python h1_xref.py halo1.dll+1A2B3C4 --context 6
"""
import argparse
import os
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h2_addr                                                  # noqa: E402

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo1\halo1.dll')

WRITE_HINTS = ('mov', 'add', 'sub', 'inc', 'dec', 'and', 'or', 'xor', 'lock')


def code_sections(pe):
    IMAGE_SCN_CNT_CODE = 0x00000020
    IMAGE_SCN_MEM_EXECUTE = 0x20000000
    for s in pe.sections:
        if s.Characteristics & (IMAGE_SCN_CNT_CODE | IMAGE_SCN_MEM_EXECUTE):
            yield s


def classify(ins, target, span=1):
    """Does this instruction write through the RIP-relative operand, or read it?"""
    for i, op in enumerate(ins.operands):
        if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
            hit = ins.address + ins.size + op.mem.disp
            if not (target <= hit < target + span):
                continue
            if ins.mnemonic.startswith('lea'):
                return 'ADDRESS-OF'
            # operand 0 is the destination for the usual x86 two-operand forms
            if i == 0 and any(ins.mnemonic.startswith(w) for w in WRITE_HINTS):
                return 'WRITE'
            return 'READ'
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('address', help='halo1.dll+OFFSET, a VA, or file:OFFSET')
    ap.add_argument('--dll', default=DLL)
    ap.add_argument('--calls', action='store_true',
                    help='find CALL/JMP sites reaching the address, not data refs')
    ap.add_argument('--span', type=int, default=1,
                    help='treat [address, address+span) as the target region')
    ap.add_argument('--context', type=int, default=4,
                    help='instructions of context to print around each hit')
    a = ap.parse_args(argv)

    if not os.path.exists(a.dll):
        raise SystemExit('no such file: %s' % a.dll)
    pe, base = h2_addr._pe(a.dll)
    kind, val = h2_addr.parse(a.address, base)
    target = h2_addr.off_to_va(pe, base, val) if kind == 'file' else val
    if target is None:
        raise SystemExit('could not resolve %s' % a.address)
    print('target: %s+%X   (VA 0x%X)\n' % (os.path.basename(a.dll), target - base, target))

    data = open(a.dll, 'rb').read()
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    if a.calls:
        # CALL/JMP rel32 sites, not data references. A points table is reached
        # through the FUNCTION that consumes it, so when a value arrives as an
        # argument the callers are the next thing to look at, not the data.
        found = []
        for s in code_sections(pe):
            lo, hi = s.PointerToRawData, s.PointerToRawData + s.SizeOfRawData
            sec_va = base + s.VirtualAddress
            for p in range(lo, hi - 5):
                if data[p] not in (0xE8, 0xE9):
                    continue
                rel = struct.unpack_from('<i', data, p + 1)[0]
                if sec_va + (p + 5 - lo) + rel != target:
                    continue
                va = sec_va + (p - lo)
                found.append((va, p, 'CALL' if data[p] == 0xE8 else 'JMP'))
        print('\n%d call/jmp site(s) reaching the target:\n' % len(found))
        for va, off, kindstr in found:
            print('  %-5s %s+%-9X  file:0x%X'
                  % (kindstr, os.path.basename(a.dll), va - base, off))
        return 0

    hits = []
    for s in code_sections(pe):
        name = s.Name.decode().strip('\0')
        lo = s.PointerToRawData
        hi = lo + s.SizeOfRawData
        sec_va = base + s.VirtualAddress
        print('scanning %-8s %.1f MB' % (name, (hi - lo) / 1048576))
        for p in range(lo, hi - 4):
            # VA of the byte after this displacement field
            next_va = sec_va + (p + 4 - lo)
            disp = struct.unpack_from('<i', data, p)[0]
            # a table is often reached through a pointer to the struct AROUND it, so
            # --span lets a whole region be asked about, not just one exact address
            if not (target <= next_va + disp < target + a.span):
                continue
            # numeric candidate -- confirm an instruction actually ends here
            for back in range(3, 16):
                start = p - back
                if start < lo:
                    continue
                got = list(md.disasm(data[start:start + 24], sec_va + (start - lo), 1))
                if not got:
                    continue
                ins = got[0]
                if ins.address + ins.size != next_va:
                    continue
                kindstr = classify(ins, target, a.span)
                if kindstr:
                    hits.append((ins.address, start, kindstr, ins.mnemonic, ins.op_str))
                break

    if not hits:
        print('\nno references found.')
        print('If the address came from h1_scorescan and is on the HEAP, that is\n'
              'expected -- only statics are reachable this way. Narrow to a static,\n'
              'or find the static POINTER that reaches the heap object.')
        return 0

    seen = set()
    print('\n%d reference(s):\n' % len(hits))
    for va, off, kindstr, mn, ops in sorted(hits):
        if va in seen:
            continue
        seen.add(va)
        print('  %-10s %s+%-9X  file:0x%-9X  %s %s'
              % (kindstr, os.path.basename(a.dll), va - base, off, mn, ops))
        if a.context:
            start = max(0, off - 24)
            sec = next(s for s in code_sections(pe)
                       if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData)
            sva = base + sec.VirtualAddress + (start - sec.PointerToRawData)
            for i, ins in enumerate(md.disasm(data[start:start + 24 + 32], sva)):
                if i > a.context * 2:
                    break
                mark = '  <<<' if ins.address == va else ''
                print('        0x%09X  %-20s %s %s%s'
                      % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
            print()

    writes = [h for h in hits if h[2] == 'WRITE']
    print('%d write site(s), %d read site(s), %d address-of site(s)'
          % (len(writes), sum(1 for h in hits if h[2] == 'READ'),
             sum(1 for h in hits if h[2] == 'ADDRESS-OF')))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
