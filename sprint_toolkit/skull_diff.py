r"""skull_diff.py -- measure what a skull actually changes, by diffing live memory.

Static analysis got as far as it can: halo1.dll expands the active-skull mask (a qword
at rva 0x2B40708) into one byte per skull, and NOTHING in that DLL reads the Anger byte
-- only Bandanna and Blind have consumers. Halo 1 never shipped skulls, so the flavour
system is Bungie's own debug plumbing and MCC applies its skulls some other way. The
only way left to find out what Anger does is to watch memory with it on and off.

    python sprint_toolkit/skull_diff.py mask
        Decode the live skull mask. Run it with skulls off, then with Anger on: bit 0
        flipping is the empirical proof of the bit mapping the disassembly derived.

    python sprint_toolkit/skull_diff.py snap A1
        Snapshot halo1.dll's writable data to reports/skull_A1.bin.

    python sprint_toolkit/skull_diff.py diff A1 A2 B1
        Bytes that differ between A1 and B1 but NOT between A1 and A2. A1/A2 are two
        snapshots of the SAME condition, so what moves between them is engine noise --
        timers, RNG, AI state -- and subtracting it is what makes the result readable.

HOW TO RUN THE EXPERIMENT
    1. Start the level with NO skulls. At a quiet checkpoint:  snap A1
    2. Wait ~10s, do nothing:                                  snap A2
    3. Restart the SAME level with ANGER on, same checkpoint:   snap B1
    4. diff A1 A2 B1
Keep the two conditions as alike as possible -- same level, same checkpoint, standing
still -- or the noise mask cannot do its job.
"""
import argparse
import ctypes
import ctypes.wintypes as w
import os
import struct
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
k32 = ctypes.WinDLL('kernel32', use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

# from the disassembly: mask qword, and the bit each skull sits on
MASK_RVA = 0x2B40708
DATA_RVA, DATA_SIZE = 0x1B75000, 0x2095B58
BITS = {0: 'anger', 1: 'assassins', 2: 'bandanna', 3: 'black_eye', 4: 'blind',
        6: 'boom', 0x10: 'catch', 0x11: 'eye_patch', 0x12: 'famine', 0x13: 'feather',
        0x14: 'fog', 0x15: 'foreign', 0x16: 'ghost', 0x17: 'grunt_birthday_party',
        0x18: 'grunt_funeral', 0x19: 'iron', 0x1A: 'iwhbyd', 0x1B: 'mythic',
        0x1C: 'recession', 0x1D: 'sputnik'}


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD),
                ('th32ProcessID', w.DWORD), ('th32DefaultHeapID', ctypes.POINTER(w.ULONG)),
                ('th32ModuleID', w.DWORD), ('cntThreads', w.DWORD),
                ('th32ParentProcessID', w.DWORD), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', w.DWORD), ('szExeFile', ctypes.c_char * 260)]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('th32ModuleID', w.DWORD),
                ('th32ProcessID', w.DWORD), ('GlblcntUsage', w.DWORD),
                ('ProccntUsage', w.DWORD), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', w.DWORD), ('hModule', w.HMODULE),
                ('szModule', ctypes.c_char * 256), ('szExePath', ctypes.c_char * 260)]


def find_pid(name=b'MCC-Win64-Shipping.exe'):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32First(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == name.lower():
            return e.th32ProcessID
        ok = k32.Process32Next(snap, ctypes.byref(e))
    return None


def module_base(pid, name=b'halo1.dll'):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    m = MODULEENTRY32()
    m.dwSize = ctypes.sizeof(m)
    ok = k32.Module32First(snap, ctypes.byref(m))
    while ok:
        if m.szModule.lower() == name.lower():
            return ctypes.cast(m.modBaseAddr, ctypes.c_void_p).value, m.modBaseSize
        ok = k32.Module32Next(snap, ctypes.byref(m))
    return None, None


def read(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf,
                                 ctypes.c_size_t(size), ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def attach():
    pid = find_pid()
    if not pid:
        print('MCC-Win64-Shipping.exe is not running.')
        return None, None
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print('OpenProcess failed (%d). Try running this elevated.'
              % ctypes.get_last_error())
        return None, None
    base, size = module_base(pid)
    if not base:
        print('halo1.dll is not loaded -- start Halo 1 (a campaign level) first.')
        return None, None
    print('pid %d, halo1.dll at 0x%X (%.1f MB)' % (pid, base, size / 1048576.0))
    return h, base


# the expanded per-skull bytes, and the guard the expander tests before filling them.
# Both stay zero at the menu: the skull state is built at LEVEL LOAD, so any check has
# to be made in-level, not from the main menu.
FLAG_LO, FLAG_HI = 0x1C421B9, 0x1C421D5
FLAG_NAMES = {0x1C421C9: 'blind', 0x1C421CE: 'anger', 0x1C421D5: 'masterblaster'}
GUARD_RVA = 0x2B406C5


def show_mask(h, base):
    raw = read(h, base + MASK_RVA, 8)
    if raw is None:
        print('could not read the mask')
        return
    v = struct.unpack('<Q', raw)[0]
    print('\nskull mask = 0x%016X' % v)
    on = [BITS.get(b, 'bit %d' % b) for b in range(64) if v >> b & 1]
    print('active: %s' % (', '.join(on) if on else '(none)'))
    print('ANGER (bit 0) is %s' % ('ON' if v & 1 else 'off'))
    blob = read(h, base + FLAG_LO, FLAG_HI - FLAG_LO + 1)
    guard = read(h, base + GUARD_RVA, 4)
    if blob is not None:
        setb = [FLAG_NAMES.get(FLAG_LO + i, 'byte +%d' % i)
                for i, c in enumerate(blob) if c]
        print('expanded flags: %s' % (', '.join(setb) if setb else 'none set'))
        print('   raw %s' % blob.hex())
    if guard:
        g = struct.unpack('<I', guard)[0]
        print('expander guard = %d%s' % (g, '   (0 = no level loaded yet)'
                                         if g == 0 else ''))


def snap(h, base, tag):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'skull_%s.bin' % tag)
    chunks, addr, end = [], base + DATA_RVA, base + DATA_RVA + DATA_SIZE
    step = 1 << 20
    while addr < end:
        got = read(h, addr, min(step, end - addr))
        chunks.append(got if got else b'\x00' * min(step, end - addr))
        addr += step
    blob = b''.join(chunks)
    raw = read(h, base + MASK_RVA, 8)
    mask = struct.unpack('<Q', raw)[0] if raw else 0
    with open(path, 'wb') as f:
        f.write(struct.pack('<QQ', mask, len(blob)) + blob)
    print('snapshot %s: %.1f MB, mask 0x%X (anger %s)'
          % (tag, len(blob) / 1048576.0, mask, 'ON' if mask & 1 else 'off'))


def load(tag):
    path = os.path.join(OUT, 'skull_%s.bin' % tag)
    with open(path, 'rb') as f:
        mask, n = struct.unpack('<QQ', f.read(16))
        return mask, f.read(n)


def diff(a1, a2, b1, limit):
    m1, d1 = load(a1)
    m2, d2 = load(a2)
    m3, d3 = load(b1)
    print('%s mask 0x%X, %s mask 0x%X, %s mask 0x%X' % (a1, m1, a2, m2, b1, m3))
    if (m1 & 1) or (m2 & 1):
        print('WARNING: the baseline snapshots already have Anger ON')
    if not (m3 & 1):
        print('WARNING: the test snapshot does NOT have Anger on -- nothing to find')
    n = min(len(d1), len(d2), len(d3))
    noise = bytearray(n)
    for i in range(n):
        if d1[i] != d2[i]:
            noise[i] = 1
    hits = [i for i in range(n) if d1[i] != d3[i] and not noise[i]]
    print('\n%d byte(s) differ between %s and %s, %d of them are engine noise'
          % (sum(1 for i in range(n) if d1[i] != d3[i]), a1, b1, sum(noise)))
    print('%d stable difference(s)' % len(hits))
    # group into runs and show as floats where plausible
    runs, cur = [], None
    for i in hits:
        if cur and i == cur[1] + 1:
            cur[1] = i
        else:
            cur = [i, i]
            runs.append(cur)
    print('%d run(s); first %d:' % (len(runs), min(limit, len(runs))))
    for s, e in runs[:limit]:
        rva = DATA_RVA + s
        old = d1[s:e + 1]
        new = d3[s:e + 1]
        extra = ''
        if e - s + 1 >= 4:
            try:
                fo = struct.unpack_from('<f', d1, s & ~3)[0]
                fn = struct.unpack_from('<f', d3, s & ~3)[0]
                if abs(fo) < 1e9 and abs(fn) < 1e9:
                    extra = '   float %.4f -> %.4f' % (fo, fn)
            except Exception:
                pass
        print('   rva 0x%08X  %-24s -> %-24s%s'
              % (rva, old[:12].hex(), new[:12].hex(), extra))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=('mask', 'snap', 'diff'))
    ap.add_argument('tags', nargs='*')
    ap.add_argument('--limit', type=int, default=40)
    a = ap.parse_args()
    if a.mode == 'diff':
        if len(a.tags) != 3:
            print('diff needs three snapshot tags: baseline, baseline-again, test')
            return 2
        diff(a.tags[0], a.tags[1], a.tags[2], a.limit)
        return 0
    h, base = attach()
    if not h:
        return 1
    if a.mode == 'mask':
        show_mask(h, base)
    else:
        if not a.tags:
            print('snap needs a tag, e.g. "snap A1"')
            return 2
        snap(h, base, a.tags[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
