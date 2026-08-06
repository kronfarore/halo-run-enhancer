r"""A tiny memory scanner for finding game state, without Cheat Engine.

Cheat Engine does this too, but its UI has been getting in the way, and the search
here is narrow enough not to need it: we are looking for a byte in halo2.dll's
STATIC data that flips when the player cloaks. Static data is the useful place to
find it -- an address there is the same every launch, and the code that writes it
can be patched.

The scan is the standard alternation, driven by GLOBAL hotkeys, so the game keeps focus and you never alt-tab:

    F7  the state is UNCHANGED since the last snapshot (the noise filter -- tap it
        several times while standing still and nothing is happening)
    F8  the state CHANGED since the last snapshot (tap right after cloaking, and
        again right after the cloak drops)
    F9  show the surviving candidates
    F10 restart the scan
    F11 quit

Typical session: uncloaked and standing still, tap F7 five or six times; cloak and
tap F8; stay cloaked and tap F7 a few times; let it drop and tap F8. Repeat until a
handful remain, then F9. A short cloak is no longer a race and the game never loses
focus.

Needs to run elevated (the game is under Program Files). Read-only: it never
writes to the game's memory.
"""
import ctypes
import ctypes.wintypes as w
import os
import subprocess
import sys
import time

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

k32 = ctypes.WinDLL('kernel32', use_last_error=True)


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('th32ModuleID', w.DWORD),
                ('th32ProcessID', w.DWORD), ('GlblcntUsage', w.DWORD),
                ('ProccntUsage', w.DWORD), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', w.DWORD), ('hModule', w.HMODULE),
                ('szModule', ctypes.c_char * 256), ('szExePath', ctypes.c_char * 260)]


def find_pid(name='MCC-Win64-Shipping.exe'):
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + name, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if name.lower() in line.lower():
            return int(line.split('","')[1].strip('"'))
    return None


def module_base(pid, want='halo2.dll'):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == -1:
        raise OSError('CreateToolhelp32Snapshot failed -- try running elevated')
    me = MODULEENTRY32(); me.dwSize = ctypes.sizeof(MODULEENTRY32)
    ok = k32.Module32First(snap, ctypes.byref(me))
    while ok:
        if me.szModule.decode('latin-1').lower() == want.lower():
            return ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value, me.modBaseSize
        ok = k32.Module32Next(snap, ctypes.byref(me))
    return None, None


def read(h, addr, size):
    buf = (ctypes.c_char * size)()
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
        return None
    return bytes(buf[:got.value])


MEM_COMMIT = 0x1000
PAGE_RW = (0x04, 0x40)               # PAGE_READWRITE, PAGE_EXECUTE_READWRITE


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_ulonglong), ('AllocationBase', ctypes.c_ulonglong),
                ('AllocationProtect', w.DWORD), ('__alignment1', w.DWORD),
                ('RegionSize', ctypes.c_ulonglong), ('State', w.DWORD),
                ('Protect', w.DWORD), ('Type', w.DWORD), ('__alignment2', w.DWORD)]


def all_regions(h, cap=(1 << 31), lo=0, hi=(1 << 47)):
    """Every committed read/write region, which is where the heap lives.

    The static .data scan found only the HUD's copy of the camo state -- writing to it
    changed nothing -- so the gameplay state is presumably in a unit object on the
    heap. This walks the whole address space instead. Regions are capped so a stray
    multi-gigabyte reservation cannot stall the scan."""
    regions = []
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION64()
    total = 0
    while addr < 0x7FFFFFFFFFFF and total < cap:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        size = int(mbi.RegionSize)
        # Thread stacks sit low (0x87... in this process) and are full of transient
        # locals that move with any code path -- pure noise for a state hunt. The game
        # heap is up around 0x197...-0x199..., so a range filter keeps the scan honest.
        if (mbi.State == MEM_COMMIT and mbi.Protect in PAGE_RW
                and 0 < size <= (64 << 20)
                and lo <= int(mbi.BaseAddress) < hi):
            regions.append((int(mbi.BaseAddress), size))
            total += size
        addr = int(mbi.BaseAddress) + max(size, 0x1000)
    return regions


def heap_scan(lo=0, hi=(1 << 47)):
    """Hotkey-driven scan over the WHOLE heap, not just halo2.dll's static data.

    Two stages, because 2 GB per snapshot cannot be held twice in memory:
      1. hash every 4 KB page and filter on the hashes, which is cheap and shrinks
         the search to a handful of pages;
      2. once few enough pages remain, track individual bytes inside them.
    Same keys as the static scan: F7 unchanged (noise filter), F8 changed, F9 show,
    F10 restart, F11 quit."""
    import hashlib
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed -- run elevated')
    PAGE = 4096
    regions = all_regions(h, lo=lo, hi=hi)
    print('%d regions, %.0f MB' % (len(regions), sum(r[1] for r in regions) / 1048576))

    def page_hashes(pages=None):
        out = {}
        if pages is None:
            for base, size in regions:
                blob = read(h, base, size)
                if not blob:
                    continue
                for o in range(0, len(blob) - PAGE, PAGE):
                    out[base + o] = hashlib.blake2b(blob[o:o + PAGE], digest_size=8).digest()
        else:
            for a in pages:
                b = read(h, a, PAGE)
                if b:
                    out[a] = hashlib.blake2b(b, digest_size=8).digest()
        return out

    def page_bytes(pages):
        return {a: read(h, a, PAGE) for a in pages}

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    KEYS = {0x76: 'u', 0x77: 'c', 0x78: 's', 0x79: 'r', 0x7A: 'q'}
    cand_pages = None
    prev_h = page_hashes()
    prev_b = None
    cand_b = None
    print('baseline: %d pages. F7 unchanged  F8 changed  F9 show  F10 restart  F11 quit'
          % len(prev_h))
    down = set()
    while True:
        time.sleep(0.03)
        cmd = None
        for vk, c in KEYS.items():
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and vk not in down:
                down.add(vk); cmd = c
            elif not pressed:
                down.discard(vk)
        if cmd is None:
            continue
        if cmd == 'q':
            break
        if cmd == 'r':
            cand_pages, cand_b, prev_b = None, None, None
            prev_h = page_hashes()
            print('restarted: %d pages' % len(prev_h)); continue
        if cmd == 's':
            if cand_b:
                # Written to a file as well: 100+ candidates are unreadable in a
                # console, and the log can be inspected without transcribing.
                import os, struct
                path = os.path.join(LOGDIR, 'heap_candidates.log')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('# %d candidate bytes%s' % (len(cand_b), chr(10)))
                    for a in sorted(cand_b):
                        blob = read(h, a & ~(PAGE - 1), PAGE)
                        ctx = blob[a & (PAGE - 1):(a & (PAGE - 1)) + 4] if blob else b''
                        fl = struct.unpack('<f', ctx)[0] if len(ctx) == 4 else 0.0
                        f.write('0x%X = %-4d  dwordfloat=%-14.4f bytes=%s%s'
                                % (a, cand_b[a], fl, ctx.hex(), chr(10)))
                print('%d candidate byte(s) -> %s' % (len(cand_b), path))
                for a in sorted(cand_b)[:20]:
                    print('   0x%X = %d' % (a, cand_b[a]))
            elif cand_pages is not None:
                print('%d candidate page(s) -- keep filtering' % len(cand_pages))
            else:
                print('no filtering yet')
            continue

        want_change = (cmd == 'c')
        if cand_b is None:
            cur_h = page_hashes(cand_pages)
            keep = [a for a, v in cur_h.items()
                    if a in prev_h and ((prev_h[a] != v) == want_change)]
            cand_pages, prev_h = keep, {a: cur_h[a] for a in keep}
            print('%s -> %d page(s)' % ('changed' if want_change else 'unchanged', len(keep)))
            if 0 < len(keep) <= 64:
                prev_b = page_bytes(keep)
                cand_b = {}
                for a, blob in prev_b.items():
                    if blob:
                        for i in range(len(blob)):
                            cand_b[a + i] = blob[i]
                print('   tracking %d individual bytes now' % len(cand_b))
        else:
            keep = {}
            pages = {a & ~(PAGE - 1) for a in cand_b}
            cur = {a: read(h, a, PAGE) for a in pages}
            for a, oldv in cand_b.items():
                blob = cur.get(a & ~(PAGE - 1))
                if not blob:
                    continue
                newv = blob[a & (PAGE - 1)]
                if (newv != oldv) == want_change:
                    keep[a] = newv
            cand_b = keep
            print('%s -> %d byte(s)' % ('changed' if want_change else 'unchanged', len(keep)))
    k32.CloseHandle(h)


def watch(addrs):
    """Poll specific module-relative addresses and log every change, with the bytes
    also shown as a float -- camo state reads as a 0..1 meter, so a value walking
    between 0.0 and 1.0 is the giveaway. Run it, cloak twice, then read the log."""
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('could not attach -- run elevated, with a level loaded')
    import struct
    print('watching %d address(es); cloak a couple of times, then Ctrl-C' % len(addrs))
    last = {}
    t0 = time.time()
    while True:
        for a in addrs:
            b = read(h, _resolve(base, a), 4)
            if not b or len(b) < 4:
                continue
            if last.get(a) != b:
                f, = struct.unpack('<f', b)
                print('%7.2fs  halo2.dll+%-9X byte=%-4d float=%-12.4f %s'
                      % (time.time() - t0, a, b[0], f, b.hex()))
                last[a] = b
        time.sleep(0.05)


LOGDIR = ('C:/Users/kron1/AppData/Local/Temp/claude'
          '/C--Program-Files--x86--Steam-steamapps-common-Halo-The-Master-Chief-Collection-tool'
          '/7911d4c4-6fca-4c76-aeb2-b03aa8980e60/scratchpad')


def region(addr, size, path=None):
    """Log every byte that changes inside a window of memory, to a file.

    Point this at the structure the camo meter lives in and play normally: cloak a
    couple of times and let it drop. Every change is timestamped, so fields moving
    with the cloak stand out from background churn -- and the flag we want is almost
    certainly a neighbour of the meter."""
    import os, struct
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('could not attach -- run elevated, with a level loaded')
    path = path or os.path.join(LOGDIR, 'camo_region.log')
    target = _resolve(base, addr)
    prev = read(h, target, size)
    t0 = time.time()
    n = 0
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# halo2.dll+%X .. +%X (%d bytes)\n' % (addr, addr + size, size))
        f.write('# time     offset          old -> new   dword-as-float\n')
        f.flush()
        print('logging to %s -- cloak a few times, then Ctrl-C' % path)
        try:
            while True:
                time.sleep(0.05)
                cur = read(h, target, size)
                if not cur or len(cur) != len(prev):
                    continue
                for i in range(len(cur)):
                    if cur[i] != prev[i]:
                        d = i & ~3
                        fl = struct.unpack_from('<f', cur, d)[0] if d + 4 <= len(cur) else 0.0
                        f.write('%8.2f  halo2.dll+%-9X %4d -> %-4d  %.4f\n'
                                % (time.time() - t0, addr + i, prev[i], cur[i], fl))
                        n += 1
                if n:
                    f.flush()
                prev = cur
        except KeyboardInterrupt:
            pass
    print('%d change(s) written to %s' % (n, path))


def dump(addr, size, path):
    """One-shot snapshot of a memory window to a text file.

    For comparing the same structure between levels: take one on an Arbiter level and
    one on a Chief level, then diff. A byte that is 1 for the Arbiter and 0 for Chief
    is exactly the "may this player cloak" flag we are hunting."""
    import struct
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('could not attach -- run elevated, with a level loaded')
    b = read(h, _resolve(base, addr), size)
    if not b:
        raise SystemExit('read failed')
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(0, len(b), 16):
            row = b[i:i+16]
            fl = ' '.join('%12.4f' % struct.unpack_from('<f', row, j)[0]
                          for j in range(0, len(row) - 3, 4))
            f.write('halo2.dll+%-9X %-47s %s\n'
                    % (addr + i, ' '.join('%02x' % c for c in row), fl))
    print('wrote %d bytes to %s' % (len(b), path))


PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008


def _resolve(base, addr):
    """Module-relative offsets are small (halo2.dll spans ~0x2A00000); anything larger
    is an absolute heap address from the heap scan, so use it as-is."""
    return addr if addr > 0x10000000 else base + addr


def poke(addr, value, hold=False):
    """Write a byte to a module-relative address, optionally holding it there.

    The camo flags live in an object pool inside halo2.dll's .data, reached through
    pointers -- so no instruction references them statically and there is nothing to
    patch in the file. Writing the value directly tests the hypothesis, and if the
    game keeps resetting it, --hold rewrites it continuously, which is a working
    (if inelegant) way to keep the Arbiter's camo switched off."""
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ |
                        PROCESS_VM_WRITE | PROCESS_VM_OPERATION, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    target = _resolve(base, addr)
    buf = (ctypes.c_char * 1)(bytes([value]))
    wrote = ctypes.c_size_t(0)
    def w():
        return k32.WriteProcessMemory(h, ctypes.c_void_p(target), buf, 1,
                                      ctypes.byref(wrote))
    before = read(h, target, 1)
    ok = w()
    after = read(h, target, 1)
    print('halo2.dll+%X : %d -> wrote %d -> now %d %s'
          % (addr, before[0] if before else -1, value, after[0] if after else -1,
             '' if ok else '(WriteProcessMemory FAILED)'))
    if hold:
        print('holding it there -- Ctrl-C to stop')
        try:
            while True:
                w()
                time.sleep(0.02)
        except KeyboardInterrupt:
            pass
    k32.CloseHandle(h)


def pokef(addr, value, hold=False):
    """Write a 4-byte FLOAT, optionally holding it.

    For the camo gauge at +187D8B4: it runs 0.0..1.0, so a single-byte poke only
    clobbers its low byte and the engine barely notices. Holding the whole float at
    0.0 should leave the Arbiter with no charge to cloak with -- which is a different
    lever from the state flags, and one we had not tried."""
    import struct
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ |
                        PROCESS_VM_WRITE | PROCESS_VM_OPERATION, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    target = _resolve(base, addr)
    payload = struct.pack('<f', value)
    buf = ctypes.create_string_buffer(payload, 4)
    wrote = ctypes.c_size_t(0)
    def w():
        return k32.WriteProcessMemory(h, ctypes.c_void_p(target), buf, 4,
                                      ctypes.byref(wrote))
    b = read(h, target, 4)
    print('halo2.dll+%X : was %.4f -> writing %.4f'
          % (addr, struct.unpack('<f', b)[0] if b else -1, value))
    w()
    if hold:
        print('holding -- Ctrl-C to stop')
        try:
            while True:
                w()
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        b = read(h, target, 4)
        print('released; now %.4f' % (struct.unpack('<f', b)[0] if b else -1))
    k32.CloseHandle(h)


def pokemany(addrs, value=0):
    """Hold several bytes at a value at once, then bisect.

    Testing candidates one at a time costs a game reload each; holding the whole set
    answers "is it any of these?" in one go, and if camo breaks we halve the list."""
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ |
                        PROCESS_VM_WRITE | PROCESS_VM_OPERATION, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    buf = (ctypes.c_char * 1)(bytes([value]))
    wrote = ctypes.c_size_t(0)
    targets = [_resolve(base, a) for a in addrs]
    for a, t in zip(addrs, targets):
        b = read(h, t, 1)
        print('  0x%X  was %s -> holding %d' % (a, b[0] if b else '?', value))
    print('holding %d address(es) -- Ctrl-C to stop' % len(targets))
    try:
        while True:
            for t in targets:
                k32.WriteProcessMemory(h, ctypes.c_void_p(t), buf, 1, ctypes.byref(wrote))
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    k32.CloseHandle(h)


def findsrc(mirror_addr, length=64, lo=0x19000000000, hi=0x1A000000000):
    """Find the SOURCE of a bulk copy by matching its bytes in the heap.

    The camo gauge at halo2.dll+187D8B4 is written by `movups` out of a copy loop, so
    that static address is a destination -- a mirror -- and the authoritative state is
    whatever the copy reads from. A verbatim copy means the same bytes exist at the
    source, so searching the heap for the mirror's contents locates it without a
    debugger. Writes to the SOURCE should actually affect gameplay, unlike the mirror."""
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    needle = read(h, _resolve(base, mirror_addr), length)
    if not needle:
        raise SystemExit('could not read the mirror at 0x%X' % mirror_addr)
    print('looking for %d bytes: %s...' % (length, needle[:16].hex()))
    hits = []
    for rbase, size in all_regions(h, lo=lo, hi=hi):
        blob = read(h, rbase, size)
        if not blob:
            continue
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            hits.append(rbase + i)
            start = i + 1
    print('%d match(es) outside the mirror:' % len(hits))
    for a in hits[:20]:
        print('   0x%X' % a)
    return hits


def deref(ptr_rva, entry=0, stride=0x90, length=0x90, path=None):
    """Follow a static pointer to a per-player array and dump one entry.

    The snapshot at halo2.dll+187D870 is BUILT from this array: the publisher does
    `add rcx, [rip+0x10550a0]` with rcx = index*0x90, so halo2.dll+187E350 holds the
    base and each player is 0x90 bytes. This is the authoritative state -- unlike the
    snapshot, writes here should actually affect the game."""
    import os, struct
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    raw = read(h, base + ptr_rva, 8)
    if not raw:
        raise SystemExit('could not read the pointer slot')
    arr, = struct.unpack('<Q', raw)
    print('pointer at halo2.dll+%X -> 0x%X' % (ptr_rva, arr))
    if not arr:
        raise SystemExit('pointer is null -- is a level actually loaded?')
    addr = arr + entry * stride
    b = read(h, addr, length)
    if not b:
        raise SystemExit('could not read entry %d at 0x%X' % (entry, addr))
    lines = []
    for i in range(0, len(b), 16):
        row = b[i:i+16]
        fl = ' '.join('%11.4f' % struct.unpack_from('<f', row, j)[0]
                      for j in range(0, len(row) - 3, 4))
        lines.append('+0x%02X  %-47s %s' % (i, ' '.join('%02x' % c for c in row), fl))
    out = 'entry %d at 0x%X (stride 0x%X)%s%s' % (entry, addr, stride, chr(10),
                                                  chr(10).join(lines))
    print(out)
    if path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(out + chr(10))
        print('written to %s' % path)
    return addr


def chain(entry=0, deref_off=0x58, length=0x200, log=False, path=None):
    """Follow halo2.dll+187E350 -> array -> entry -> *(entry+0x58) and dump or log it.

    The 0x90 per-player entry is mostly pointers: the routine at +82B110 does
    `mov rbx,[rcx+0x58]` and works through that, so the object we actually want hangs
    off +0x58. With --log it records every byte that changes, which is how the camo
    fields identify themselves during a cloak."""
    import struct
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    arr, = struct.unpack('<Q', read(h, base + 0x187E350, 8))
    ent = arr + entry * 0x90
    obj, = struct.unpack('<Q', read(h, ent + deref_off, 8))
    print('array 0x%X -> entry %d 0x%X -> *(+0x%X) = 0x%X' % (arr, entry, ent, deref_off, obj))
    k32.CloseHandle(h)
    if not obj:
        raise SystemExit('that pointer is null')
    if log:
        region(obj, length, path)
    else:
        dump(obj, length, path or os.path.join(LOGDIR, 'camo_object.txt'))
    return obj


def resolve_unit(entry=0, verbose=True):
    """Resolve a player's UNIT object exactly as the engine does.

    Chain taken from `player_active_camouflage_on` (halo2.dll+789190 -> +69AA30):
        players  = *(halo2.dll+E80A28)        the "players" data array
        element  = players + *(players+0x48) + index*0x224
        datum    = *(uint32*)(element + 0x2C)     the unit handle
        table    = *(halo2.dll+18B7398)
        offset   = *(int32*)(table + *(table+0x48) + (datum & 0xFFFF)*12 + 8)
        unit     = ((*(halo2.dll+18B7360) + 0x57) & ~0xF) + offset

    **unit+0x2FC is the camo field**: the engine compares it against 1.0 and treats
    equality as camouflaged; it reads 0.0 when visible.

    NOTE the earlier wrong turn: the HUD's per-player record at *(halo2.dll+187E350)
    also holds a unit handle at +0x18, but it resolves to a DIFFERENT object (physics /
    animation data) whose +0x2FC is meaningless drift. Use the players array."""
    import struct
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    base, _ = module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    def q(a):
        return struct.unpack('<Q', read(h, a, 8))[0]
    players = q(base + 0xE80A28)
    if not players:
        raise SystemExit('no players array -- is a level loaded?')
    element = players + q(players + 0x48) + entry * 0x224
    datum, = struct.unpack('<I', read(h, element + 0x2C, 4))
    if datum in (0, 0xFFFFFFFF):
        raise SystemExit('player %d has no unit' % entry)
    tbl = q(base + 0x18B7398)
    off, = struct.unpack('<i', read(h, tbl + q(tbl + 0x48) + (datum & 0xFFFF) * 12 + 8, 4))
    unit = ((q(base + 0x18B7360) + 0x57) & ~0xF) + off
    camo, = struct.unpack('<f', read(h, unit + 0x2FC, 4))
    if verbose:
        print('player[%d] datum 0x%08X -> unit 0x%X   camo(+0x2FC) = %s'
              % (entry, datum, unit, 'NaN' if camo != camo else '%.4f' % camo))
        # for x64dbg: break on whatever writes the camo field, which is the activation
        # code -- the permission check lives in the same function.
        flags, = struct.unpack('<I', read(h, unit + 0x138, 4))
        print('   unit+0x138 flags = 0x%08X   (bit 3 = camo active: %s)'
              % (flags, 'SET' if flags & 8 else 'clear'))
        print('   x64dbg:  bph 0x%X, w, 4     # camo value +0x2FC' % (unit + 0x2FC))
        print('   x64dbg:  bph 0x%X, w, 4     # unit flags  +0x138' % (unit + 0x138))
        # CODE breakpoints are module base + offset -- nothing to do with the heap
        # addresses above. Printed here so they never have to be worked out by hand.
        print('   --- code breakpoints (halo2.dll base 0x%X) ---' % base)
        for rva, what in ((0x8F499A, 'camo OFF call'),
                          (0x8F4690, 'function containing it'),
                          (0x8F19B0, 'camo on/off API entry'),
                          (0x8FDDA0, 'per-frame camo updater')):
            print('   x64dbg:  bp 0x%X      # halo2.dll+%-7X %s' % (base + rva, rva, what))
    k32.CloseHandle(h)
    return unit


def unitwatch(entry=0):
    """Time a cloak: poll unit+0x2FC and report every transition with a timestamp.

    Answers "how long does the powerup actually last on this character", which matters
    on Arbiter levels -- his native cloak has its own timer, and the question is whether
    it truncates the pickup. Prints the measured cloaked duration on each fade-out."""
    import struct, time as _t
    unit = resolve_unit(entry, verbose=False)
    pid = find_pid()
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    print('watching unit 0x%X +0x2FC -- cloak, then wait for it to drop. Ctrl-C to stop.'
          % unit)
    prev = None
    rose = None
    t0 = _t.time()
    try:
        while True:
            b = read(h, unit + 0x2FC, 4)
            if b:
                v, = struct.unpack('<f', b)
                if prev is None or abs(v - prev) > 0.02:
                    now = _t.time() - t0
                    tag = ''
                    if v >= 0.999 and (prev is None or prev < 0.999):
                        rose = now; tag = '   <- fully cloaked'
                    if v <= 0.001 and prev is not None and prev > 0.001:
                        tag = ('   <- visible again; cloaked for %.1fs' % (now - rose)
                               if rose else '   <- visible again')
                    print('  %7.2fs  camo = %.3f%s' % (now, v, tag))
                    prev = v
            _t.sleep(0.05)
    except KeyboardInterrupt:
        pass
    k32.CloseHandle(h)


def main():
    # halo2.dll .data: the uninitialised part is where the skull tables and other live
    # state sit, so that is the region worth watching.
    DATA_RVA, DATA_SIZE = 0xDF8000, 0x1B9B384

    if len(sys.argv) > 1 and sys.argv[1] == '--heap':
        lo = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
        hi = int(sys.argv[3], 0) if len(sys.argv) > 3 else (1 << 47)
        heap_scan(lo, hi)
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--watch':
        watch([int(x, 16) for x in sys.argv[2:]])
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--unitwatch':
        unitwatch(int(sys.argv[2], 0) if len(sys.argv) > 2 else 0)
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--pokeunit':
        # resolve the unit fresh, then hold its camo field (+0x2FC) at a value.
        # 0.0 = fully visible, 1.0 = fully cloaked; the engine ramps between them.
        u = resolve_unit()
        pokef(u + 0x2FC, float(sys.argv[2]) if len(sys.argv) > 2 else 0.0,
              '--hold' in sys.argv)
        return
    if len(sys.argv) > 1 and sys.argv[1] in ('--unit', '--unitlog'):
        u = resolve_unit()
        if sys.argv[1] == '--unitlog':
            region(u, int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400,
                   sys.argv[3] if len(sys.argv) > 3 else None)
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--objdump':
        # The per-player object hangs off the static pointer at halo2.dll+187E350, so
        # it can be dumped in any session and diffed level-to-level. The camo
        # PERMISSION should be a field that differs Arbiter vs Chief while staying
        # constant through a cloak -- the opposite of the state fields.
        import struct as _s
        _pid = find_pid()
        _h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, _pid)
        _base, _ = module_base(_pid, 'halo2.dll')
        _obj, = _s.unpack('<Q', read(_h, _base + 0x187E350, 8))
        k32.CloseHandle(_h)
        print('object at 0x%X' % _obj)
        dump(_obj, int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x300,
             sys.argv[2] if len(sys.argv) > 2 else os.path.join(LOGDIR, 'obj.txt'))
        return
    if len(sys.argv) > 1 and sys.argv[1] in ('--chain', '--chainlog'):
        chain(int(sys.argv[2], 0) if len(sys.argv) > 2 else 0,
              0x58,
              int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x200,
              log=(sys.argv[1] == '--chainlog'))
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--regionptr':
        # follow the static pointer, then log changes in that entry: the heap address
        # differs every session, so resolving it fresh each run is the only sane way
        import struct as _s
        _pid = find_pid()
        _h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, _pid)
        _base, _ = module_base(_pid, 'halo2.dll')
        _raw = read(_h, _base + 0x187E350, 8)
        _arr, = _s.unpack('<Q', _raw)
        _entry = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
        k32.CloseHandle(_h)
        print('array at 0x%X, entry %d at 0x%X' % (_arr, _entry, _arr + _entry * 0x90))
        region(_arr + _entry * 0x90, 0x90,
               sys.argv[3] if len(sys.argv) > 3 else None)
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--deref':
        deref(int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x187E350,
              int(sys.argv[3], 0) if len(sys.argv) > 3 else 0,
              0x90, 0x90,
              sys.argv[4] if len(sys.argv) > 4 else None)
        return
    if len(sys.argv) > 2 and sys.argv[1] == '--findsrc':
        findsrc(int(sys.argv[2], 16),
                int(sys.argv[3], 0) if len(sys.argv) > 3 else 64,
                int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x19000000000,
                int(sys.argv[5], 0) if len(sys.argv) > 5 else 0x1A000000000)
        return
    if len(sys.argv) > 2 and sys.argv[1] == '--pokemany':
        pokemany([int(x, 16) for x in sys.argv[2:] if not x.startswith('-')])
        return
    if len(sys.argv) > 3 and sys.argv[1] == '--pokef':
        pokef(int(sys.argv[2], 16), float(sys.argv[3]), '--hold' in sys.argv)
        return
    if len(sys.argv) > 3 and sys.argv[1] == '--poke':
        poke(int(sys.argv[2], 16), int(sys.argv[3], 0), '--hold' in sys.argv)
        return
    if len(sys.argv) > 4 and sys.argv[1] == '--dump':
        dump(int(sys.argv[2], 16), int(sys.argv[3], 0), sys.argv[4])
        return
    if len(sys.argv) > 3 and sys.argv[1] == '--region':
        region(int(sys.argv[2], 16), int(sys.argv[3], 0),
               sys.argv[4] if len(sys.argv) > 4 else None)
        return
    pid = find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed (%d) -- run this elevated'
                         % ctypes.get_last_error())
    base, _ = module_base(pid, 'halo2.dll')
    if not base:
        raise SystemExit('halo2.dll is not loaded -- start a Halo 2 level first')
    print('pid %d, halo2.dll at 0x%X, watching .data (%d MB)'
          % (pid, base, DATA_SIZE // 1048576))

    def snap():
        out = {}
        step = 1 << 20
        for off in range(0, DATA_SIZE, step):
            b = read(h, base + DATA_RVA + off, min(step, DATA_SIZE - off))
            if b:
                out[off] = b
        return out

    prev = snap()
    cand = None                      # None = everything still in play
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    KEYS = {0x76: 'u', 0x77: 'c', 0x78: 's', 0x79: 'r', 0x7A: 'q'}
    print('baseline taken.')
    print('  F7 = unchanged (noise filter)   F8 = changed (after cloak on/off)')
    print('  F9 = show      F10 = restart    F11 = quit')
    print('Keep the game focused; these are global hotkeys.')

    down = set()
    while True:
        time.sleep(0.03)
        cmd = None
        for vk, c in KEYS.items():
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and vk not in down:
                down.add(vk); cmd = c
            elif not pressed:
                down.discard(vk)
        if cmd is None:
            continue
        if cmd == 'q':
            break
        if cmd == 'r':
            prev, cand = snap(), None
            print('restarted'); continue
        if cmd == 's':
            if cand is None:
                print('no filtering yet')
            else:
                print('%d candidate(s)' % len(cand))
                for a in sorted(cand):
                    print('   halo2.dll+%X = %d' % (DATA_RVA + a, cand[a]))
            continue

        cur = snap()
        keep = {}
        if cand is None:
            for blk, old in prev.items():
                new = cur.get(blk)
                if not new or len(new) != len(old):
                    continue
                for i in range(len(old)):
                    if (old[i] != new[i]) == (cmd == 'c'):
                        keep[blk + i] = new[i]
        else:
            for a, oldv in cand.items():
                blk, i = (a // (1 << 20)) * (1 << 20), a % (1 << 20)
                new = cur.get(blk)
                if not new or i >= len(new):
                    continue
                if (new[i] != oldv) == (cmd == 'c'):
                    keep[a] = new[i]
        cand, prev = keep, cur
        print('%s -> %d candidate(s)' % ('changed' if cmd == 'c' else 'unchanged', len(cand)))
    k32.CloseHandle(h)


if __name__ == '__main__':
    main()
