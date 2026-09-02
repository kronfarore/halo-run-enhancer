r"""Scale the campaign metagame's PLAYER DEATH penalty, live, in every game.

WHY THIS IS NOT A MAP PATCH
---------------------------
From Halo 3 on, matg carries `Player Death Point Count` (25 in H3/ODST, 0 in Reach).
That is a tag field and could be patched into the .map -- but Halo 1 and Halo 2 have no
campaign metagame in their own dlls at all, so a map patch can never cover them, and a
map patch is baked in at patch time rather than pushed at will.

The MCC WRAPPER is the one scoring engine every game shares. It is the only binary in
the install containing `HaloScoreInfo` (the ScoreDB.XML root), and it holds the
penalties as plain float32 literals:

    ApplyPenalty(float) = +0x0044B764, five call sites --

      +0x00437ED1  PLAYER DEATH, right after `inc dword [rbx+0x148]` (the death
                   counter)                                            -25
      +0x00437F76  BETRAYAL fallback                                   -50
      +0x00494727  REVERT to checkpoint ($DIALOG_PAUSE_REVERT)         -50
      +0x00494AFE  REVERT, second site                                 -50
      +0x004477BB  betrayal via the kill path, value from ScoreDB

So one write in the running process moves the death penalty for whatever game is
loaded. That is the same trick `score_live.py` plays on the parsed ScoreDB table, and
for the same reason: MCC reads its data once and a restart per change is unusable.

WHY IT REPOINTS INSTEAD OF OVERWRITING
--------------------------------------
The -25 literal at .rdata 0x0347649C has a SECOND consumer at +0x008972AF, and the -50
at 0x034764B4 has one at +0x008972EB -- both in an unrelated routine that also
subtracts 50 and stores -25 to an object field. Overwriting the literal would move that
too, in a subsystem nobody has identified.

So nothing shared is ever written. Instead a private float is placed in the zero-filled
gap between .rdata's virtual end (rva 0x03A240EA) and .data's start (rva 0x03A25000) --
inside the module, so the rip-relative displacement always reaches -- and the 4-byte
displacement of the `movss` at the death site is repointed at it. The shared literal is
left exactly as it was, which is also what makes --restore a single 4-byte write.

THE SCALING
-----------
The penalty grows with how much the run has taken on: `base * (1 + per_round * rounds)`.
At the default 10% per round, round 10 costs 50 points instead of 25.

    python sprint_toolkit/death_penalty.py --rounds 12
    python sprint_toolkit/death_penalty.py --rounds 12 --per-round 0.25
    python sprint_toolkit/death_penalty.py --value 200      # set it outright
    python sprint_toolkit/death_penalty.py --show
    python sprint_toolkit/death_penalty.py --restore
"""
import argparse
import ctypes
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
ACCESS = (PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE
          | PROCESS_VM_OPERATION)
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04
TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10

EXE = 'MCC-Win64-Shipping.exe'

# --- the addresses, all module-relative ------------------------------------------
# The `movss xmm1, [rip+disp32]` at the player-death site. F3 0F 10 0D dd = 8 bytes,
# so the displacement is at +4 and is relative to the END of the instruction.
DEATH_SITE = 0x00437ED1
DEATH_DISP = DEATH_SITE + 4
DEATH_INSN_END = DEATH_SITE + 8
DEATH_INSN_BYTES = bytes.fromhex('f30f100d')      # verified before any write
STOCK_LITERAL = 0x0347649C                        # what it points at when untouched
STOCK_DISP = STOCK_LITERAL - DEATH_INSN_END
STOCK_VALUE = -25.0

# The zero-filled gap between .rdata's virtual end and .data's start. Chosen well
# clear of both edges; verified to read as zeros before it is claimed, so a future
# build that actually puts something there is refused rather than corrupted.
SLOT = 0x03A24F00

# --- the betrayal sign guard -----------------------------------------------------
# Betrayal looks the victim up in ScoreDB and then throws the answer away unless it is
# negative:
#
#   00437F65  0f57c0        xorps  xmm0, xmm0
#   00437F6B  0f2f00        comiss xmm0, [rax]     ; 0 vs the row
#   00437F6E  7606          jbe    0x437F76        ; 0 <= row -> hardcoded -50
#   00437F70  f30f1008      movss  xmm1, [rax]     ; else use the row
#   00437F74  eb08          jmp    0x437F7E
#   00437F76  f30f100d....  movss  xmm1, -50
#
# NOPping the jbe makes the row authoritative whatever its sign. That matters because
# ApplyPenalty ADDS its argument (`addss xmm0,[rax+0x30]` at +0x0044B800, after the
# difficulty and skull multipliers), so a POSITIVE row awards points instead of taking
# them -- which is what turns Marines into ordinary enemies once they are hostile.
BETRAY_GUARD = 0x00437F6E
BETRAY_STOCK = bytes.fromhex('7606')       # jbe +6
BETRAY_OPEN = b'\x90\x90'                  # two NOPs


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_ulong), ('cntUsage', ctypes.c_ulong),
                ('th32ProcessID', ctypes.c_ulong),
                ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                ('th32ModuleID', ctypes.c_ulong), ('cntThreads', ctypes.c_ulong),
                ('th32ParentProcessID', ctypes.c_ulong),
                ('pcPriClassBase', ctypes.c_long), ('dwFlags', ctypes.c_ulong),
                ('szExeFile', ctypes.c_char * 260)]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_ulong), ('th32ModuleID', ctypes.c_ulong),
                ('th32ProcessID', ctypes.c_ulong), ('GlblcntUsage', ctypes.c_ulong),
                ('ProccntUsage', ctypes.c_ulong), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', ctypes.c_ulong), ('hModule', ctypes.c_void_p),
                ('szModule', ctypes.c_char * 256), ('szExePath', ctypes.c_char * 260)]


def find_pid(name=EXE.encode()):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32()
    e.dwSize = ctypes.sizeof(e)
    found = None
    if k32.Process32First(snap, ctypes.byref(e)):
        while True:
            if e.szExeFile.lower() == name.lower():
                found = e.th32ProcessID
                break
            if not k32.Process32Next(snap, ctypes.byref(e)):
                break
    k32.CloseHandle(snap)
    return found


def module_base(pid, name=EXE.encode()):
    """Where the image is loaded. ASLR moves it every launch, so nothing may be
    hardcoded as an absolute address -- everything here is an RVA plus this."""
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == -1:
        return None
    e = MODULEENTRY32()
    e.dwSize = ctypes.sizeof(e)
    base = None
    if k32.Module32First(snap, ctypes.byref(e)):
        while True:
            if e.szModule.lower() == name.lower():
                base = ctypes.cast(e.modBaseAddr, ctypes.c_void_p).value
                break
            if not k32.Module32Next(snap, ctypes.byref(e)):
                break
    k32.CloseHandle(snap)
    return base


def read(h, addr, size):
    buf = (ctypes.c_char * size)()
    n = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size,
                                 ctypes.byref(n)):
        return None
    return bytes(buf[:n.value])


def write(h, addr, blob, protect=PAGE_EXECUTE_READWRITE):
    """Write with the page temporarily made writable, then put the protection back.

    Leaving a code page writable is exactly the kind of thing that makes a later crash
    impossible to explain, so the old protection is always restored."""
    old = ctypes.c_ulong(0)
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(blob), protect,
                                ctypes.byref(old)):
        return False, 'VirtualProtectEx failed (%d)' % ctypes.get_last_error()
    n = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(addr), blob, len(blob),
                                ctypes.byref(n))
    back = ctypes.c_ulong(0)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(blob), old.value,
                         ctypes.byref(back))
    if not ok or n.value != len(blob):
        return False, 'WriteProcessMemory failed (%d)' % ctypes.get_last_error()
    return True, None


def penalty_for(rounds, per_round=0.10, base=abs(STOCK_VALUE)):
    """base * (1 + per_round * rounds), as a POSITIVE magnitude.

    Rounds, not effects: an effect is one card, and a round is one draft the player
    accepted, which is what "how much has this run taken on" actually means."""
    return float(base) * (1.0 + float(per_round) * max(0, int(rounds)))


def attach():
    pid = find_pid()
    if not pid:
        return None, None, None, 'MCC is not running (no %s)' % EXE
    base = module_base(pid)
    if not base:
        return None, None, None, 'could not find the %s module in pid %d' % (EXE, pid)
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        return None, None, None, ('OpenProcess failed (%d) -- run this elevated'
                                  % ctypes.get_last_error())
    return h, base, pid, None


def state(h, base):
    """(current penalty, where it is read from, the raw displacement)."""
    raw = read(h, base + DEATH_DISP, 4)
    if raw is None:
        return None, None, None
    disp = struct.unpack('<i', raw)[0]
    at = DEATH_INSN_END + disp
    val = read(h, base + at, 4)
    return (struct.unpack('<f', val)[0] if val else None), at, disp


def apply(h, base, value):
    """Point the death site at our own float and set it. Returns (ok, message)."""
    insn = read(h, base + DEATH_SITE, 4)
    if insn != DEATH_INSN_BYTES:
        return False, ('the death site does not look like the expected '
                       '`movss xmm1,[rip+d32]` (found %s) -- this MCC build differs, '
                       'refusing to write' % (insn.hex() if insn else '?'))
    cur = read(h, base + SLOT, 4)
    _, at, _ = state(h, base)
    if cur is None:
        return False, 'could not read the scratch slot at rva 0x%08X' % SLOT
    if cur != b'\0\0\0\0' and at != SLOT:
        return False, ('the scratch slot at rva 0x%08X is not zero (%s) -- this build '
                       'uses it, refusing to write' % (SLOT, cur.hex()))
    # The value first, so the instruction is never pointed at a slot that has not been
    # initialised: if the second write failed the site would read whatever was there.
    ok, err = write(h, base + SLOT, struct.pack('<f', -abs(value)), PAGE_READWRITE)
    if not ok:
        return False, 'writing the float: %s' % err
    if at != SLOT:
        ok, err = write(h, base + DEATH_DISP,
                        struct.pack('<i', SLOT - DEATH_INSN_END))
        if not ok:
            return False, 'repointing the instruction: %s' % err
    return True, None


def restore(h, base):
    ok, err = write(h, base + DEATH_DISP, struct.pack('<i', STOCK_DISP))
    return (True, None) if ok else (False, err)


def betrayal_state(h, base):
    """'stock' / 'open' / 'unknown', plus the raw bytes."""
    raw = read(h, base + BETRAY_GUARD, 2)
    if raw is None:
        return 'unreadable', None
    return ({BETRAY_STOCK: 'stock', BETRAY_OPEN: 'open'}.get(raw, 'unknown'), raw)


def betrayal_open(h, base):
    """Let a POSITIVE ScoreDB row through, so betraying a Marine can pay out."""
    what, raw = betrayal_state(h, base)
    if what == 'open':
        return True, 'already open'
    if what != 'stock':
        return False, ('the guard at rva 0x%08X reads %s, not the expected %s -- this '
                       'MCC build differs, refusing to write'
                       % (BETRAY_GUARD, raw.hex() if raw else '?', BETRAY_STOCK.hex()))
    ok, err = write(h, base + BETRAY_GUARD, BETRAY_OPEN)
    return (True, None) if ok else (False, err)


def betrayal_restore(h, base):
    ok, err = write(h, base + BETRAY_GUARD, BETRAY_STOCK)
    return (True, None) if ok else (False, err)


def push(rounds=None, per_round=0.10, value=None):
    """One call for the GUI: attach, set, verify, detach. Never raises."""
    h, base, pid, err = attach()
    if err:
        return {'ok': False, 'reason': err}
    try:
        want = float(value) if value is not None else penalty_for(rounds or 0, per_round)
        before, _, _ = state(h, base)
        ok, err = apply(h, base, want)
        if not ok:
            return {'ok': False, 'reason': err}
        after, at, _ = state(h, base)
        if after is None or abs(abs(after) - want) > 0.01:
            return {'ok': False, 'reason': 'readback disagrees (%s vs %s)'
                                           % (after, -want)}
        return {'ok': True, 'pid': pid, 'old': before, 'new': after,
                'rva': at, 'rounds': rounds, 'per_round': per_round}
    finally:
        k32.CloseHandle(h)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rounds', type=int, help='rounds the run has taken')
    ap.add_argument('--per-round', type=float, default=0.10,
                    help='fraction added per round (default 0.10 = +10%%)')
    ap.add_argument('--value', type=float, help='set the penalty outright')
    ap.add_argument('--show', action='store_true', help='read it and stop')
    ap.add_argument('--restore', action='store_true', help='put the stock -25 back')
    ap.add_argument('--betrayal', choices=('open', 'restore'),
                    help="'open' NOPs the sign guard so a POSITIVE ScoreDB row is "
                         "honoured (betraying a Marine can then pay out); 'restore' "
                         "puts the stock jbe back")
    args = ap.parse_args(argv)

    h, base, pid, err = attach()
    if err:
        print(err)
        return 1
    try:
        val, at, disp = state(h, base)
        origin = ('stock literal' if at == STOCK_LITERAL
                  else 'our slot' if at == SLOT else 'unknown')
        bstate, braw = betrayal_state(h, base)
        print('%s  pid %d  base 0x%X' % (EXE, pid, base))
        print('  player death penalty  %s   (reads rva 0x%08X, %s)'
              % (val, at, origin))
        print('  betrayal sign guard   %s   (%s at rva 0x%08X)'
              % (bstate, braw.hex() if braw else '?', BETRAY_GUARD))
        if args.betrayal:
            if args.betrayal == 'open':
                ok, err = betrayal_open(h, base)
            else:
                ok, err = betrayal_restore(h, base)
            print('  betrayal guard -> %s: %s'
                  % (args.betrayal, 'ok' if ok else 'FAILED: %s' % err))
            print('  now %s' % betrayal_state(h, base)[0])
            if not (args.show or args.restore or args.rounds is not None
                    or args.value is not None):
                return 0 if ok else 1
        if args.show:
            return 0
        if args.restore:
            ok, err = restore(h, base)
            ok2, err2 = betrayal_restore(h, base)
            print('  death penalty restored' if ok else '  restore failed: %s' % err)
            print('  betrayal guard restored' if ok2 else
                  '  guard restore failed: %s' % err2)
            return 0 if (ok and ok2) else 1
        if args.value is None and args.rounds is None:
            ap.error('need --rounds, --value, --show or --restore')
        want = (args.value if args.value is not None
                else penalty_for(args.rounds, args.per_round))
        ok, err = apply(h, base, want)
        if not ok:
            print('  FAILED: %s' % err)
            return 1
        now, at, _ = state(h, base)
        if args.rounds is not None and args.value is None:
            print('  %d round(s) x %+.0f%% -> penalty %g' % (args.rounds,
                                                            args.per_round * 100, want))
        print('  now %s   (reads rva 0x%08X)' % (now, at))
        return 0
    finally:
        k32.CloseHandle(h)


if __name__ == '__main__':
    sys.exit(main())
