r"""Read-only static helpers for halo2.dll (or any MCC game dll): the tools the player-supercombine hunt used
(h2_supercombine_players.py, 2026-11-16/17) -- kept so the two sites can be re-found after an MCC update.

    python h2_dll_dis.py dis 905D12 [--before 0x60] [--after 0x40]   disassemble around an RVA (>> marks it)
    python h2_dll_dis.py calls 884DC0 6A6410                          every E8 call / E9 jmp to these RVAs
    python h2_dll_dis.py disp 880000 950000 0x114 0x11c               instructions using [reg + DISP] in a range
    python h2_dll_dis.py start 90645E                                 the function start (the int3 padding above)
    ... --dll <path>  another dll (default halo2.dll)

`disp` decodes back from each 4-byte match, so it cannot desync the way a linear sweep does (a linear
capstone sweep missed +0x92260F). Callers by RIP-relative reference: h1_xref.py --dll.
"""
import argparse
import re
import struct

import capstone

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo2\halo2.dll')


def load(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    n = struct.unpack_from('<H', d, pe + 6)[0]
    opt = struct.unpack_from('<H', d, pe + 20)[0]
    secs, text = [], None
    for i in range(n):
        o = pe + 24 + opt + i * 40
        vs, va, rs, raw = struct.unpack_from('<IIII', d, o + 8)
        secs.append((va, max(vs, rs), raw))
        if d[o:o + 8].rstrip(b'\0') == b'.text':
            text = (va, rs, raw)
    return d, secs, text


def file_off(secs, rva):
    for va, size, raw in secs:
        if va <= rva < va + size:
            return raw + rva - va
    raise SystemExit('RVA +%X is in no section' % rva)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('what', choices=('dis', 'calls', 'disp', 'start'))
    ap.add_argument('args', nargs='+')
    ap.add_argument('--before', default='0x60')
    ap.add_argument('--after', default='0x60')
    ap.add_argument('--dll', default=DLL)
    a = ap.parse_args(argv)
    d, secs, (tva, trs, traw) = load(a.dll)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    h = lambda s: int(s, 16)
    if a.what == 'dis':
        rva, before, after = h(a.args[0]), int(a.before, 0), int(a.after, 0)
        fo = file_off(secs, rva - before)
        for ins in md.disasm(d[fo:fo + before + after], rva - before):
            if ins.mnemonic == 'int3':
                continue
            print('%s +%X  %-24s %s %s' % ('>>' if ins.address == rva else '  ', ins.address, ins.bytes.hex(),
                                            ins.mnemonic, ins.op_str))
    elif a.what == 'calls':
        targets = {h(x) for x in a.args}
        code = d[traw:traw + trs]
        for i in range(len(code) - 5):
            if code[i] in (0xE8, 0xE9):
                dst = tva + i + 5 + struct.unpack_from('<i', code, i + 1)[0]
                if dst in targets:
                    print('%s +%X -> +%X' % ('call' if code[i] == 0xE8 else 'jmp ', tva + i, dst))
    elif a.what == 'disp':
        lo, hi = h(a.args[0]), h(a.args[1])
        for disp in a.args[2:]:
            v = int(disp, 0)
            want = '+ %s]' % hex(v)
            blob = d[traw + lo - tva: traw + hi - tva]
            for m in re.finditer(re.escape(struct.pack('<I', v)), blob):
                at = lo + m.start()
                for back in range(2, 7):
                    ins = next(md.disasm(d[traw + at - back - tva: traw + at - back - tva + 15], at - back), None)
                    if ins and want in ins.op_str and ins.size >= back + 4:
                        print('+%X  %s %s' % (ins.address, ins.mnemonic, ins.op_str))
                        break
    else:
        r = h(a.args[0])
        while not (d[file_off(secs, r) - 1] == 0xCC and d[file_off(secs, r) - 2] == 0xCC):
            r -= 1
        print('+%X' % r)


if __name__ == '__main__':
    main()
