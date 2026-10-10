r"""Halo 1: no FIRE while a MELEE plays, for weapons whose TAG opts in (weapon flags bit 31).

The Gravity Hammer and the restored Energy Sword attack on the fire button (a trigger firing
an invisible strike). Halo 1 blocks a trigger during a player melee only for 3/4 of it: the
biped melee (+0xBAF258) starts the replacement animation 'melee' (unit +0x284 = 7) and a timer
(unit +0x512) = 3/4 of the first-person melee's frame count; while that timer runs, the unit
update (+0xAFD5D1..) sets the weapon control word's 'cannot fire' bit (weapon +0x1FA, 0x10).
The last quarter of the swing could fire -- the slam / lunge with no swing (measured with
h1_melee_fire_probe.py: hammer blocked 30 of 36 ticks, sword 19 of 26). The timer also gates
the NEXT melee, so it stays stock: melee spam is unchanged.
Research: PORTING.md, "no FIRE during a MELEE". (rva at image base 0x180000000; MCC halo1.dll
of 2026-06-22.)

U  the unit update's `mov edx,[rbp+0x88]` (the control word handed to the weapon, +0xAFD688)
   -> a cave that also sets bit 0x80 while the unit's replacement animation is the melee
   (unit +0x284 == 7). Bit 0x80 of the word is read nowhere in stock.
W  the weapon tick's `movzx r8d, word [rbx+0x1FA]` (+0xB7515A, r15 = the weapon tag) -> a cave
   that turns 0x80 into 0x10 (both triggers off) when the weapon tag has flag bit 31
   (weap +0x308 bit 31; only unreleased digsite tags use bits 16+, and halo1.dll reads none
   of them). Stock weapons never carry it, so for them nothing changes.
The melee animation that times it is the THIRD-person one: a port whose 3P melee is shorter
than its FP melee gets its own (h1_pickable_weapons.third_person_melee_as_fp). Opt-in: the
port config's 'melee_blocks_fire': True sets the tag bit and that animation.

The caves (50 bytes) sit in the .text slack after the overheat-unzoom cave (+0x17501CC,
zeros in the stock file). Same LIVE / FILE handling as h1_overheat_unzoom.py: every site is
verified (stock bytes + context) before a write; caves go in before the calls that use them
and the calls come out before the caves are cleared; a loaded dll is swapped by rename.

    python sprint_toolkit/h1_melee_blocks_fire.py --show
    python sprint_toolkit/h1_melee_blocks_fire.py --on           # live + file
    python sprint_toolkit/h1_melee_blocks_fire.py --on --live    # the running MCC only
    python sprint_toolkit/h1_melee_blocks_fire.py --off          # back to stock (--restore)
"""
import argparse
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
from h1_overheat_unzoom import (DLL, TEXT_FILE_DELTA, _classify, _cleanup_inuse,  # noqa: E402
                                _file_reader, _write_file)

H = bytes.fromhex
NAME = 'Melee blocks the fire button (opted-in weapons)'
TAG_FLAG_BIT = 31             # weap +0x308 flags; the byte tested is +0x30B, mask 0x80
CAVE_W = 0x17501CC            # .text slack: the overheat cave ends here, raw data at +0x1750200
SITE_W = 0xB7515A             # weapon tick: movzx r8d, word [rbx+0x1FA]
SITE_U = 0xAFD688             # unit update: mov edx, [rbp+0x88]


def _rel(next_ip, target):
    return struct.pack('<i', target - next_ip)


CAVE_W_CODE = (H('440fb783fa010000')      # movzx r8d, word [rbx+0x1FA]  (the replaced one)
               + H('41f6c080')            # test r8b, 0x80        melee animation playing?
               + H('740e')                # je ret
               + H('41f6870b03000080')    # test byte [r15+0x30B], 0x80   tag flag bit 31
               + H('7404')                # je ret
               + H('4180c810')            # or r8b, 0x10          = cannot fire
               + H('c3'))
CAVE_U = CAVE_W + len(CAVE_W_CODE)
CAVE_U_CODE = (H('8b9588000000')          # mov edx, [rbp+0x88]  (the replaced one)
               + H('4380bc3cb802000007')  # cmp byte [r12+r15+0x2B8], 7  (unit +0x284 = melee)
               + H('7503')                # jne ret
               + H('80ca80')              # or dl, 0x80
               + H('c3'))
assert CAVE_U + len(CAVE_U_CODE) <= 0x1750200

# (rva, context before, stock, patched, context after) -- in "on" order
SITES = [
    (CAVE_W, b'', bytes(len(CAVE_W_CODE)), CAVE_W_CODE, b''),
    (CAVE_U, b'', bytes(len(CAVE_U_CODE)), CAVE_U_CODE, b''),
    (SITE_W, H('e8d91900004533d2'), H('440fb783fa010000'),
     H('e8') + _rel(SITE_W + 5, CAVE_W) + H('909090'), H('4584c6753b')),
    (SITE_U, H('410fbe10e854860000'), H('8b9588000000'),
     H('e8') + _rel(SITE_U + 5, CAVE_U) + H('90'), H('8bc80f28d6')),
]


def _writes(state, want):
    if want and state in ('off', 'partial'):
        return [(r, pt) for r, _p, _st, pt, _po in SITES]
    if not want and state in ('on', 'partial'):
        return [(r, st) for r, _p, st, _pt, _po in reversed(SITES)]
    return []


def file_state(path=DLL):
    return _classify(_file_reader(path), SITES) if os.path.exists(path) else 'missing'


def file_set(want, path=DLL):
    """(ok, message). In place, or the swap by rename while MCC holds the dll."""
    _cleanup_inuse(path)
    state = file_state(path)
    if state == 'missing':
        return False, '%s not found' % path
    if state == 'unknown':
        return False, ('halo1.dll does not hold the expected bytes -- this MCC build '
                       'differs, refusing to write')
    writes = _writes(state, want)
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
    if file_state(new) != ('on' if want else 'off'):
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
        os.rename(held, path)
        return False, 'could not put the patched halo1.dll in place: %s' % e
    return True, 'swapped in while MCC runs (applies at its next start)'


def live_state(h, base):
    return _classify(lambda rva, n: dp.read(h, base + rva, n), SITES)


def live_set(h, base, want):
    state = live_state(h, base)
    if state == 'unknown':
        return False, ('the running halo1.dll does not hold the expected bytes -- this MCC '
                       'build differs, refusing to write')
    for rva, blob in _writes(state, want):
        ok, err = dp.write(h, base + rva, blob)
        if not ok:
            return False, '+0x%X: %s' % (rva, err)
    return True, None


def _live(fn):
    """fn(h, base) on the running MCC; None when MCC / halo1.dll is not there."""
    pid = dp.find_pid()
    if not pid:
        return None
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    if not h:
        return (False, 'OpenProcess failed -- run elevated')
    try:
        base = dp.module_base(pid, b'halo1.dll')
        return fn(h, base) if base else None
    finally:
        dp.k32.CloseHandle(h)


def sync(on, path=DLL, quiet=True, live_only=False):
    """One call for the GUI (h1_overheat_unzoom.sync's shape): the patch on (or back to
    stock) in the running MCC AND in halo1.dll on disk. Result rows; never raises."""
    target = 'on' if on else 'off'
    row = {'tag': 'halo1.dll', 'effect': NAME}
    out = []

    def add(field, ok, old, msg):
        if quiet and ok and old == target:
            return
        out.append({**row, 'field': field, 'ok': ok, 'old': old,
                    'new': target if ok else None,
                    'reason': None if ok else msg, **({'note': msg} if ok else {})})

    def live(h, base):
        old = live_state(h, base)
        ok, err = live_set(h, base, on)
        add('running MCC', ok, old, err)
    try:
        # the running MCC only when acting on ITS dll (not on a --dll copy)
        r = _live(live) if os.path.normcase(os.path.abspath(path)) == os.path.normcase(DLL)             else None
        if isinstance(r, tuple):
            add('running MCC', False, None, r[1])
    except Exception as e:                      # never fatal to a map patch
        add('running MCC', False, None, str(e))
    if not live_only:
        try:
            old = file_state(path)
            ok, msg = file_set(on, path)
            add('halo1.dll file', ok, old, msg)
        except Exception as e:
            add('halo1.dll file', False, None, str(e))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', '--restore', dest='off', action='store_true')
    g.add_argument('--show', action='store_true')
    ap.add_argument('--live', action='store_true', help='the running MCC only, not the file')
    ap.add_argument('--dll', default=DLL, help='a halo1.dll to act on (default: MCC\'s)')
    a = ap.parse_args(argv)
    if a.on or a.off:
        for r in sync(a.on, a.dll, quiet=False, live_only=a.live):
            print('%-16s %s %s' % (r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                   r.get('note') or r.get('reason') or r.get('new')))
        return
    print('file  %s  (%s)' % (file_state(a.dll), a.dll))
    r = _live(lambda h, base: live_state(h, base))
    print('live  %s' % (r if r else 'MCC / halo1.dll not running'))


if __name__ == '__main__':
    main()
