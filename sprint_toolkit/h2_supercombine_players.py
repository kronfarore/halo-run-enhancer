r"""Halo 2: needles SUPERCOMBINE on the player in campaign (halo2.dll, one 2-byte patch) -- the twin of
Halo 1's option h1_supercombine_players (memory h1-supercombine-count-dll).

WHAT HALO 2 DOES (found 2026-11-16, read-only disassembly; the Needle Rifle port, user: stock Needlers never
combine on the player either):
  * +0x9040C0 is the attach count: a needle that sticks walks its parent's children, counts the needles of
    its own tag (skipping ones already marked +0x130 bit 0x40), and when the count passes the projectile's
    `super det. projectile count` (proj +0xE6) marks the new needle +0x130 |= 0x80. The projectile update
    (+0x922718) detonates a marked needle as the supercombine.
  * The collision response calls it at +0x9054AF -- behind a gate at +0x90547D:
        call +0x884DC0      ; campaign (game options +0xC == 4) AND the object is a PLAYER's unit (+0xD4 != -1)
        test al, al
        jne  +0x9054B6      ; -> the count is skipped: a player's needles never combine
    The needles still stick (that happens before); only the count is skipped. +0x884DC0 has 20 other
    callers, so the gate is lifted at THIS call site only: the jne becomes two NOPs.
  * SITE 2 -- the one that actually stops the blast (2026-11-17, h2_stuck_needle_probe.py: with site 1
    alone the player's 8th Needler / 3rd Needle Rifle needle WAS marked, exactly as on an Elite, and
    nothing exploded). The detonation routine +0x905AD0 counts the parent's uncounted needles of the
    same tag; above `super det. projectile count` it would go super -- unless
        cmp dword ptr [parent + 0x140], -1   ; the unit's PLAYER datum (set on the player biped only)
        call +0x6A6310                       ; game options +8 == 1: campaign
        jne  +0x905F57                       ; -> plain detonation, no supercombine
    at +0x905D02..+0x905D12. The 6-byte jne becomes NOPs.

    python h2_supercombine_players.py show
    python h2_supercombine_players.py on|off       the running MCC (if halo2.dll is loaded) AND the file
    python h2_supercombine_players.py on --live    the running MCC only (a test; gone at restart)
"""
import argparse
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import death_penalty as dp  # noqa: E402

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo2\halo2.dll')
BACKUP_DIR = os.path.join('E:' + os.sep, 'HaloBackups', 'dll')
NAME = 'Needles supercombine on the player in campaign (Halo 2)'
# (rva, bytes before, stock, patched, bytes after) -- the context must match or nothing is written
SITES = [(0x905484, bytes.fromhex('84c0'), bytes.fromhex('7530'), bytes.fromhex('9090'), bytes.fromhex('833e04')),
         (0x905D12, bytes.fromhex('84c0'), bytes.fromhex('0f853f020000'), bytes.fromhex('909090909090'),
          bytes.fromhex('488b05'))]


def _sections(data):
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    n = struct.unpack_from('<H', data, pe + 6)[0]
    opt = struct.unpack_from('<H', data, pe + 20)[0]
    out = []
    for i in range(n):
        o = pe + 24 + opt + i * 40
        vsize, va, rsize, raw = struct.unpack_from('<IIII', data, o + 8)
        out.append((va, max(vsize, rsize), raw))
    return out


def _file_off(data, rva):
    for va, size, raw in _sections(data):
        if va <= rva < va + size:
            return raw + rva - va
    raise ValueError('rva +0x%X is in no section' % rva)


def _classify(read):
    """read(rva, n) -> bytes; 'off' / 'on' / 'partial' / 'unknown'."""
    seen = set()
    for rva, pre, stock, patched, post in SITES:
        w = read(rva - len(pre), len(pre) + len(stock) + len(post)) or b''
        if len(w) != len(pre) + len(stock) + len(post) or not w.startswith(pre) or not w.endswith(post):
            return 'unknown'
        site = w[len(pre):len(pre) + len(stock)]
        seen.add('on' if site == patched else 'off' if site == stock else 'unknown')
    if 'unknown' in seen:
        return 'unknown'
    return seen.pop() if len(seen) == 1 else 'partial'


def file_state(path=DLL):
    if not os.path.exists(path):
        return 'missing'
    data = open(path, 'rb').read()
    return _classify(lambda rva, n: data[_file_off(data, rva):_file_off(data, rva) + n])


def _writes(state, on):
    if on and state in ('off', 'partial'):
        return [(rva, patched) for rva, _p, _s, patched, _a in SITES]
    if not on and state in ('on', 'partial'):
        return [(rva, stock) for rva, _p, stock, _pt, _a in SITES]
    return []


def file_set(on, path=DLL):
    """(ok, message). In place; when a running MCC maps the file, it is renamed aside and rewritten."""
    state = file_state(path)
    if state in ('missing', 'unknown'):
        return False, 'halo2.dll is %s -- this MCC build differs, refusing to write' % state
    writes = _writes(state, on)
    if not writes:
        return True, 'file already %s' % ('on' if on else 'off')
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bak = os.path.join(BACKUP_DIR, 'halo2.dll.before_supercombine_players')
    if state == 'off' and not os.path.exists(bak):
        shutil.copy2(path, bak)
    data = bytearray(open(path, 'rb').read())
    for rva, blob in writes:
        o = _file_off(data, rva)
        data[o:o + len(blob)] = blob
    try:
        open(path, 'r+b').write(bytes(data))
    except PermissionError:
        aside = '%s.inuse-%d' % (path, int(time.time()))
        os.rename(path, aside)               # a mapped dll may be renamed, not rewritten
        open(path, 'wb').write(bytes(data))
    return True, 'file %s (backup %s)' % ('on' if on else 'off', bak)


def _live(fn):
    pid = dp.find_pid()
    if not pid:
        return None
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    if not h:
        return (False, 'OpenProcess failed -- run elevated')
    try:
        base = dp.module_base(pid, b'halo2.dll')
        return fn(h, base) if base else None
    finally:
        dp.k32.CloseHandle(h)


def live_state(h, base):
    return _classify(lambda rva, n: dp.read(h, base + rva, n))


def live_set(on):
    def go(h, base):
        state = live_state(h, base)
        if state == 'unknown':
            return False, 'the running halo2.dll holds other bytes -- refusing'
        for rva, blob in _writes(state, on):
            ok, err = dp.write(h, base + rva, blob)
            if not ok:
                return False, '+0x%X: %s' % (rva, err)
        return True, 'running MCC %s (was %s)' % ('on' if on else 'off', state)
    r = _live(go)
    return r if r is not None else (True, 'halo2.dll not loaded in a running MCC')


def sync(on, live_only=False):
    """The GUI's call: the running MCC and the file. [(ok, message)]."""
    out = [live_set(on)]
    if not live_only:
        out.append(file_set(on))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('what', choices=('show', 'on', 'off'))
    ap.add_argument('--live', action='store_true', help='the running MCC only')
    a = ap.parse_args(argv)
    if a.what == 'show':
        print('file:', file_state())
        r = _live(lambda h, base: live_state(h, base))
        print('running MCC:', r if r is not None else 'halo2.dll not loaded')
        return
    for ok, msg in sync(a.what == 'on', a.live):
        print(('ok    ' if ok else 'FAILED ') + msg)


if __name__ == '__main__':
    main()
