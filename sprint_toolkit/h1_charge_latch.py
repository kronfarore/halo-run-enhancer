r"""Halo 1: a CHARGE trigger must be RELEASED before it charges again (weapon flags bit 30).

The Railgun (C7) and the Spartan Laser (A8) use the fuel rod's one trigger: charging time > 0,
overcharged action 'discharge', charge hold 0. How Halo 1 runs it (halo1.dll of 2026-06-22, rva at
image base 0x180000000; weapon tick +0xB74E6C, trigger state = weapon +0x228 + 0x2C a trigger:
+0x228 idle ticks, +0x229 STATE, +0x22A timer, +0x22C flags word, +0x238 the held-trigger ramp):

  state 0 idle    trigger down + ready (+0xB77C20) -> start +0xB77D48
  start           charging time > 0: if the ramp +0x238 > 0 (the trigger was ALREADY down on
                  the tick before) FIRE (+0xB78DE8, which clears flags bit 0) -- then state 2
  state 2 charge  timer = charging time; up early -> idle (nothing fires)
  state 3 charged timer = hold (0 here) -> +0xB78C68 -> 'discharge' +0xB78B64 -> idle, ramp 0
So the discharge itself fires nothing: the charged slug comes ~3 ticks later when the idle
trigger, still held, re-enters the start -- which fires AND begins the next charge at once
(measured 2026-10-16, out/weapon_state_probe.jsonl 'railgun boot 4': the slug's tick shows
state 2 again). Flags bit 0 = 'up since the last shot' (set on every tick the trigger is up);
'does not repeat automatically' waits for it in +0xB77C20 -- but only for a weapon whose
+0x1C0 bit 1 is set (= held by a PLAYER, item pickup +0xBDD12A), never for AI.

THE PATCH (opt-in per tag: weapon flags bit 30 = weap +0x308, byte +0x30B mask 0x40 -- the
melee patch owns bit 31; halo1.dll reads no bit above 15 of that word). In the start routine,
for an opted-in weapon whose trigger has NOT been up since its last shot (flags bit 0 clear):
  S1 +0xB77E5D  (charging time > 0, before the ramp-fire)  -> return: no fire, no charge
  S2 +0xB77EF4  (after the ramp-fire, before 'state 2')     -> return: the shot, no new charge
Held: one slug, then the trigger rests until it is let go; let go + press = a fresh charge.
For AI the same (the stock latch skips AI): one slug a burst, the next burst charges again
because an AI lets go between bursts. Stock weapons (bit 30 clear) run the stock code.
Caves in int3 padding (vetted: after a ret, no .pdata, no reloc; .text slack is full):
  CHECK_A +0x139A5AB (21)  mov r9,[rsp+0x28] ; test byte [r9+0x30B],0x40 ; jnz +1 ; ret ;
                           jmp CHECK_B          (r9 = the weapon tag, = S1's replaced load)
  CHECK_B +0x139AA3C (20)  test byte [rdi+rsi+0x22C],1 ; jz +1 ; ret ;
                           add rsp,8 ; jmp +0xB77FA0 (the start routine's epilogue)
  STUB2   +0x139A203 (13)  movsxd rax,[r15+0x34] ; lea rdx,[rdi+0x34] ; jmp CHECK_A
                           (S2's replaced 8 bytes)
r9 is dead at S2 and IS S1's load; flags are rewritten after both sites; no stack use beyond
the call's own slot. LIVE + FILE like h1_supercombine_count.py. In co-op BOTH machines need it.

    python sprint_toolkit/h1_charge_latch.py --show
    python sprint_toolkit/h1_charge_latch.py --on           # live + file
    python sprint_toolkit/h1_charge_latch.py --on --live    # the running MCC only
    python sprint_toolkit/h1_charge_latch.py --off          # back to stock (--restore)
TEST helper (the opt-in is TAG data, read live from the loaded map):
    python sprint_toolkit/h1_charge_latch.py --flag                     # list charge weapons
    python sprint_toolkit/h1_charge_latch.py --flag <weap path> on|off
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
from h1_melee_blocks_fire import _live  # noqa: E402
from h1_overheat_unzoom import DLL  # noqa: E402
import h1_supercombine_count as sc  # noqa: E402  (generic site sync / file / live helpers)

H = bytes.fromhex
NAME = 'Charge weapons wait for the trigger to be released'
FLAG_BYTE = 0x30B             # weap tag: weapon flags (+0x308) bit 30
FLAG_MASK = 0x40

S1 = 0xB77E5D                 # mov r9,[rsp+0x20]                       (5)
S2 = 0xB77EF4                 # movsxd rax,[r15+0x34] ; lea rdx,[rdi+0x34] (8)
EPILOGUE = 0xB77FA0
CHECK_A = 0x139A5AB           # int3 padding, 21 bytes after a ret
CHECK_B = 0x139AA3C           # int3 padding, 20 bytes after a ret
STUB2 = 0x139A203             # int3 padding, 13 bytes after a ret


def _rel(next_ip, target):
    return struct.pack('<i', target - next_ip)


CODE_A = (H('4c8b4c2428')                 # mov r9, [rsp+0x28]      the tag (S1's load, +8)
          + H('41f6810b03000040')         # test byte [r9+0x30B], 0x40   opted in?
          + H('7501') + H('c3')           # jnz +1 ; ret            no: stock
          + H('e9') + _rel(CHECK_A + 21, CHECK_B))
CODE_B = (H('f684372c02000001')           # test byte [rdi+rsi+0x22C], 1  up since the shot?
          + H('7401') + H('c3')           # jz +1 ; ret             yes: go on
          + H('4883c408')                 # add rsp, 8              no: leave the start routine
          + H('e9') + _rel(CHECK_B + 20, EPILOGUE))
CODE_STUB2 = (H('49634734') + H('488d5734')   # the replaced S2 instructions
              + H('e9') + _rel(STUB2 + 13, CHECK_A))
assert (len(CODE_A), len(CODE_B), len(CODE_STUB2)) == (21, 20, 13)

# (rva, context before, stock, patched, context after) -- in "on" order: caves first
SITES = [
    (CHECK_A, H('c3'), b'\xcc' * 21, CODE_A, b''),
    (CHECK_B, H('c3'), b'\xcc' * 20, CODE_B, b''),
    (STUB2, H('c3'), b'\xcc' * 13, CODE_STUB2, b''),
    (S1, H('0f86eb000000'), H('4c8b4c2420'), H('e8') + _rel(S1 + 5, CHECK_A),
     H('41f78108030000')),
    (S2, H('2c020000'), H('49634734488d5734'), H('e8') + _rel(S2 + 5, STUB2) + H('909090'),
     H('f3410f104648')),
]


def file_state(path=DLL):
    return sc.file_state(path, SITES)


def sync(on, path=DLL, quiet=True, live_only=False):
    """The enhancer's call shape (h1_supercombine_count.sync): live AND file; never raises."""
    return sc.sync(on, path, quiet, live_only, SITES, NAME)


def live_flags(h, base, weap=None, on=None):
    """Rows (path, opted in, charging time of trigger 0) of the loaded weap tags that charge;
    with `weap` and `on`, sets / clears that tag's bit 30 first."""
    rows = []
    for path, addr in sc.live_projectiles(h, base, b'weap'):
        if weap and path.lower() != weap.lower():
            continue
        if on is not None:
            b = dp.read(h, addr + FLAG_BYTE, 1)[0]
            b = (b | FLAG_MASK) if on else (b & ~FLAG_MASK)
            ok, err = dp.write(h, addr + FLAG_BYTE, bytes([b]), 0x04)
            if not ok:
                raise SystemExit('write failed: %s' % err)
        count, ptr = struct.unpack('<ii', dp.read(h, addr + 0x4FC, 8))
        vb, db = sc._q(h, base + sc.VBASE_PTR), sc._q(h, base + sc.DBASE_PTR)
        charge = 0.0
        if count > 0 and ptr:
            charge = struct.unpack('<f', dp.read(h, ptr - vb + db + 0x48, 4))[0]
        opted = bool(dp.read(h, addr + FLAG_BYTE, 1)[0] & FLAG_MASK)
        if weap or charge > 0 or opted:
            rows.append((path, opted, charge))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', '--restore', dest='off', action='store_true')
    g.add_argument('--show', action='store_true')
    g.add_argument('--flag', nargs='*', metavar=('WEAP', 'ON|OFF'),
                   help='list the loaded charge weapons and their opt-in, or set one (live)')
    ap.add_argument('--live', action='store_true', help='the running MCC only, not the file')
    ap.add_argument('--dll', default=DLL, help='a halo1.dll to act on (default: MCC\'s)')
    a = ap.parse_args(argv)
    if a.on or a.off:
        for r in sync(a.on, a.dll, quiet=False, live_only=a.live):
            print('%-16s %s %s' % (r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                   r.get('note') or r.get('reason') or r.get('new')))
        return
    if a.flag is not None:
        weap = a.flag[0] if a.flag else None
        on = None if len(a.flag) < 2 else a.flag[1].lower() in ('on', '1', 'true')
        r = _live(lambda h, base: live_flags(h, base, weap, on))
        if r is None:
            print('MCC / halo1.dll not running')
        elif isinstance(r, tuple):
            print(r[1])
        elif not r:
            print('no such weap tag loaded (or no level loaded)')
        for p, opted, charge in r or []:
            print('%-55s charge %.2f s  release-latch %s' % (p, charge, 'ON' if opted else 'off'))
        return
    print('file  %s  (%s)' % (file_state(a.dll), a.dll))
    r = _live(lambda h, base: sc.live_state(h, base, SITES))
    print('live  %s' % (r if r else 'MCC / halo1.dll not running'))


if __name__ == '__main__':
    main()
