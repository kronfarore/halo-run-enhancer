r"""Halo 1: an overheat drops the zoom, and no re-zoom while venting, as in Halo 2-4.

No stock Halo 1 weapon both zooms and overheats, so the engine never unzooms on an
overheat; the Beam Rifle port (and any battery weapon a run gives zoom to) stayed
scoped through the vent. Both patches are ENGINE-WIDE: keyed on the overheat, not on a
weapon, so every heat weapon a local player holds is covered -- stock, ported or given
zoom levels by a card. Stock heat weapons never zoom, so for them nothing changes.
Research: PORTING.md, "the Beam Rifle, wave A4 -- leaving the zoom on overheat".
(rva below = image base 0x180000000; MCC halo1.dll of 2026-06-22.)

A  'unzoom' -- CONFIRMED in game 2026-10-08. The first-person weapon event handler
   +0xB2A3F0 unzooms the player for events 9/10/0x12/0x13 (the reloads). The overheat
   (heat >= the tag's overheated threshold) sends event 0xF (0x10 for one variant),
   which fell through. Widened in place so 0xF..0x13 unzoom (0x11 has its own `je`
   before it, so it is untouched):
     +0xB2A462  8D 42 EE   lea eax,[rdx-0x12]   ->  8D 42 F1   lea eax,[rdx-0x0F]
     +0xB2A465  41 3B C7   cmp eax,r15d (=1)    ->  83 F8 04   cmp eax,4

B  'no_rezoom' -- CONFIRMED in game 2026-10-08. Only together with A. Next-zoom +0xB770B8 (every zoom-in press and
   wheel step) keeps the current level when +0xB76A88 says the weapon cannot zoom. Its
   call at +0xB7710D now goes to a 76-byte cave in the .text slack (+0x1750180, zeros in
   the stock file, mapped executable with the section) that calls the original check
   and ALSO says "cannot" while the weapon's overheated bit is set: weapon object
   +0x1F8 bit 0, set by the weapon tick +0xB74E6C when heat reaches the overheated
   threshold and cleared when it falls below the recovery threshold -- i.e. the vent.
   Zooming OUT stays possible. The handle -> object resolution copies +0xB770B8's own
   (table ptr at +0x1C42248, data base at +0x2D9CDF8).

Both halves, whatever state MCC is in -- `sync(unzoom, no_rezoom)`:
  LIVE  MCC running with halo1.dll loaded: written into the process (death_penalty's
        attach/read/write). Takes effect at once, until MCC exits.
  FILE  halo1.dll on disk, so every later MCC start has it. MCC closed: written in
        place. MCC running: the loaded dll cannot be opened for writing, but it CAN be
        renamed -- the patched copy is put in its place and the loaded original is
        renamed to halo1.dll.inuse-<time>, deleted by the next sync once MCC has let go.
Every site is verified (stock bytes + context) before any write, live and file; a dll
that does not hold them (an MCC update) is refused, never guessed at. Caves are filled
before their jump points at them, and the jump is taken out before a cave is cleared.
A Steam update or verify restores the stock dll -- the next patch puts it back. The
first file write keeps halo1.dll.prepatch.bak. In co-op BOTH machines need it (the
options travel with the run's options snapshot).

    python sprint_toolkit/h1_overheat_unzoom.py --show
    python sprint_toolkit/h1_overheat_unzoom.py --on              # A and B
    python sprint_toolkit/h1_overheat_unzoom.py --on --no-b       # A only
    python sprint_toolkit/h1_overheat_unzoom.py --off
    python sprint_toolkit/h1_overheat_unzoom.py --show --dll <copy of halo1.dll>
"""
import argparse
import glob
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402  (attach/read/write helpers)

H = bytes.fromhex

DLL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', 'halo1', 'halo1.dll'))
TEXT_FILE_DELTA = 0xC00   # .text: file offset = rva - 0xC00 (both sites and the cave)
NAME = 'Overheat drops the zoom'

# ---- B's cave ---------------------------------------------------------------------
CAVE = 0x1750180          # .text slack: VirtualSize ends at +0x1750171, raw at +0x1750200
CALL_SITE = 0xB7710D      # call +0xB76A88 inside next-zoom +0xB770B8
CAN_ZOOM_CHECK = 0xB76A88
OBJ_TABLE_PTR = 0x1C42248
OBJ_DATA_PTR = 0x2D9CDF8


def _rel(next_ip, target):
    return struct.pack('<i', target - next_ip)


def _cave_code(at=CAVE):
    b = bytearray()
    b += H('53')                                              # push rbx
    b += H('8bd9')                                            # mov ebx, ecx (handle)
    b += H('4883ec20')                                        # sub rsp, 0x20
    b += H('e8') + _rel(at + len(b) + 5, CAN_ZOOM_CHECK)      # call the original check
    b += H('4883c420')                                        # add rsp, 0x20
    b += H('84c0')                                            # test al, al
    jnz = len(b); b += H('7500')                              # jnz done
    b += H('0fb7d3')                                          # movzx edx, bx
    b += H('488d1452')                                        # lea rdx, [rdx+rdx*2]
    b += H('4c8b05') + _rel(at + len(b) + 7, OBJ_TABLE_PTR)   # mov r8, [table]
    b += H('49634034')                                        # movsxd rax, [r8+0x34]
    b += H('4901c0')                                          # add r8, rax
    b += H('4963449008')                                      # movsxd rax, [r8+rdx*4+8]
    b += H('83f8ff')                                          # cmp eax, -1
    je = len(b); b += H('7400')                               # je zero
    b += H('4c8b05') + _rel(at + len(b) + 7, OBJ_DATA_PTR)    # mov r8, [data]
    b += H('41f684002c02000001')          # test byte [r8+rax+0x22C], 1 (object +0x1F8)
    b += H('0f95c0')                                          # setnz al
    jmp = len(b); b += H('eb00')                              # jmp done
    zero = len(b); b += H('31c0')                             # xor eax, eax
    done = len(b); b += H('5b')                               # pop rbx
    b += H('c3')                                              # ret
    b[jnz + 1] = done - (jnz + 2)
    b[je + 1] = zero - (je + 2)
    b[jmp + 1] = done - (jmp + 2)
    return bytes(b)


_CAVE = _cave_code()

# (rva, context before, stock, patched, context after) -- in "on" order
PATCHES = {
    'unzoom': [
        (0xB2A462, H('83fa117440'), H('8d42ee413bc7'), H('8d42f183f804'), H('775d')),
    ],
    'no_rezoom': [
        # cave first; context = the last function's ret at +0x1750170, then slack
        (CAVE, H('c3') + bytes(CAVE - 0x1750171), bytes(len(_CAVE)), _CAVE, b''),
        (CALL_SITE, H('418bcb488bf8'), H('e8') + _rel(CALL_SITE + 5, CAN_ZOOM_CHECK),
         H('e8') + _rel(CALL_SITE + 5, CAVE), H('84c0')),
    ],
}
ORDER = ('unzoom', 'no_rezoom')
LABEL = {'unzoom': 'overheat unzooms', 'no_rezoom': 'no re-zoom while venting'}


def _classify(read, sites):
    """read(rva, n) -> bytes. 'off' / 'on' / 'partial' / 'unknown'."""
    seen = set()
    for rva, pre, stock, patched, post in sites:
        w = read(rva - len(pre), len(pre) + len(stock) + len(post)) or b''
        if (len(w) != len(pre) + len(stock) + len(post) or w[:len(pre)] != pre
                or w[len(w) - len(post):] != post):
            return 'unknown'
        site = w[len(pre):len(pre) + len(stock)]
        seen.add('on' if site == patched else 'off' if site == stock else 'unknown')
    if 'unknown' in seen:
        return 'unknown'
    return seen.pop() if len(seen) == 1 else 'partial'


def _wanted(unzoom, no_rezoom):
    return {'unzoom': bool(unzoom), 'no_rezoom': bool(unzoom and no_rezoom)}


def _writes(states, want):
    """[(rva, bytes)] in a safe order: B off before A off, A on before B on; inside a
    patch, sites in table order to switch on and reversed to switch off."""
    out = []
    for key in reversed(ORDER):                       # switching off
        if not want[key] and states[key] in ('on', 'partial'):
            out += [(r, st) for r, _p, st, _pt, _po in reversed(PATCHES[key])]
    for key in ORDER:                                 # switching on
        if want[key] and states[key] in ('off', 'partial'):
            out += [(r, pt) for r, _p, _st, pt, _po in PATCHES[key]]
    return out


# ---- file ----------------------------------------------------------------------------

def _file_reader(path):
    with open(path, 'rb') as f:
        data = f.read()
    return lambda rva, n: data[rva - TEXT_FILE_DELTA:rva - TEXT_FILE_DELTA + n]


def file_states(path=DLL):
    if not os.path.exists(path):
        return {k: 'missing' for k in ORDER}
    rd = _file_reader(path)
    return {k: _classify(rd, PATCHES[k]) for k in ORDER}


def _cleanup_inuse(path=DLL):
    """Delete originals a running MCC held at the last swap, once it has let go."""
    for old in glob.glob(glob.escape(path) + '.inuse-*'):
        try:
            os.remove(old)
        except OSError:
            pass                                # still mapped by MCC: next time


def _write_file(path, writes):
    with open(path, 'r+b') as f:
        for rva, blob in writes:
            f.seek(rva - TEXT_FILE_DELTA)
            f.write(blob)


def file_set(want, path=DLL):
    """(ok, message). Writes in place, or swaps the file when MCC holds it."""
    _cleanup_inuse(path)
    states = file_states(path)
    bad = [k for k in ORDER if states[k] in ('missing', 'unknown') and
           (want[k] or states[k] == 'missing')]
    if bad:
        if states[bad[0]] == 'missing':
            return False, '%s not found' % path
        return False, ('halo1.dll does not hold the expected bytes for "%s" -- this MCC '
                       'build differs, refusing to write' % LABEL[bad[0]])
    writes = _writes(states, want)
    if not writes:
        return True, 'already as wanted'
    bak = path + '.prepatch.bak'
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
    try:
        _write_file(path, writes)
        return True, 'written in place'
    except PermissionError:
        pass                                    # loaded by MCC: swap instead
    new = path + '.new'
    shutil.copyfile(path, new)
    _write_file(new, writes)
    got = file_states(new)
    if any(got[k] != ('on' if want[k] else 'off') for k in ORDER):
        os.remove(new)
        return False, 'the patched copy did not verify'
    held = '%s.inuse-%d' % (path, int(time.time()))
    try:
        os.rename(path, held)
    except OSError as e:
        os.remove(new)
        return False, 'MCC holds halo1.dll and it could not be renamed: %s' % e
    try:
        os.rename(new, path)
    except OSError as e:
        os.rename(held, path)                   # put the original back
        return False, 'could not put the patched halo1.dll in place: %s' % e
    return True, 'swapped in while MCC runs (applies at its next start)'


# ---- live ----------------------------------------------------------------------------

def live_states(h, base):
    rd = lambda rva, n: dp.read(h, base + rva, n)               # noqa: E731
    return {k: _classify(rd, PATCHES[k]) for k in ORDER}


def live_set(h, base, want):
    states = live_states(h, base)
    bad = [k for k in ORDER if states[k] == 'unknown' and want[k]]
    if bad:
        return False, ('the running halo1.dll does not hold the expected bytes for "%s" '
                       '-- this MCC build differs, refusing to write' % LABEL[bad[0]])
    for rva, blob in _writes(states, want):
        ok, err = dp.write(h, base + rva, blob)
        if not ok:
            return False, '+0x%X: %s' % (rva, err)
    return True, None


# ---- both ----------------------------------------------------------------------------

def _summary(states):
    return ', '.join('%s %s' % (LABEL[k], states[k]) for k in ORDER)


def sync(unzoom, no_rezoom=True, path=DLL, quiet=True):
    """One call for the GUI: the patches on (or back to stock) in the running MCC AND
    in halo1.dll on disk. B only ever goes in with A. Result rows; never raises.
    quiet: no rows for halves already as wanted, so a patch with nothing to change
    stays out of the summary."""
    want = _wanted(unzoom, no_rezoom)
    target = {k: 'on' if want[k] else 'off' for k in ORDER}
    row = {'tag': 'halo1.dll', 'effect': NAME}
    out = []

    def add(field, ok, old, msg):
        if quiet and ok and old == target:
            return
        out.append({**row, 'field': field, 'ok': ok,
                    'old': _summary(old) if old else None,
                    'new': _summary(target) if ok else None,
                    'reason': None if ok else msg, **({'note': msg} if ok else {})})

    pid = dp.find_pid()
    if pid:
        h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
        if not h:
            add('running MCC', False, None, 'OpenProcess failed -- run elevated')
        else:
            try:
                base = dp.module_base(pid, b'halo1.dll')
                if base:
                    old = live_states(h, base)
                    ok, err = live_set(h, base, want)
                    add('running MCC', ok, old, err)
            finally:
                dp.k32.CloseHandle(h)
    try:
        old = file_states(path)
        ok, msg = file_set(want, path)
        add('halo1.dll file', ok, old, msg)
    except Exception as e:                      # never fatal to a map patch
        add('halo1.dll file', False, None, str(e))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', action='store_true')
    g.add_argument('--show', action='store_true')
    ap.add_argument('--no-b', action='store_true', help='with --on: A only, B off')
    ap.add_argument('--dll', default=DLL, help='a halo1.dll to act on (default: MCC\'s)')
    a = ap.parse_args(argv)
    if a.on or a.off:
        for r in sync(a.on, not a.no_b, a.dll, quiet=False):
            print('%-16s %s %s' % (r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                   r.get('note') or r.get('reason') or r.get('new')))
        return
    print('file  %s  (%s)' % (_summary(file_states(a.dll)), a.dll))
    pid = dp.find_pid()
    if not pid:
        print('live  MCC is not running')
        return
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    try:
        base = dp.module_base(pid, b'halo1.dll')
        print('live  %s' % (_summary(live_states(h, base)) if base
                            else 'halo1.dll not loaded'))
    finally:
        dp.k32.CloseHandle(h)


if __name__ == '__main__':
    main()
