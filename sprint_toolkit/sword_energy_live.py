r"""Energy sword drain per kill, live, in Halo 2, Halo 3, ODST and Reach.

WHY THIS IS A MEMORY PATCH
--------------------------
Halo 4 keeps the sword's cost per kill in the weapon tag (`Per Kill Or Hit Aging
Amount`). The four older games do not: it is hardcoded in each game's dll. MCC loads
ALL SIX game dlls at startup and keeps the files locked for as long as it runs
(measured 2026-09-17: every game dll mapped and `PermissionError` on open), so a file
patch would need MCC closed. Written into the loaded module instead, it takes effect
at the next kill -- the same footing as death_penalty.py and score_live.py.

WHAT IS PATCHED (module-relative, current MCC build)
----------------------------------------------------
The kill routine loads a base cost and divides it by 10 before ageing the weapon:

    Halo 2   movss xmm1,[1.0]  8ebd06 / 0.25 at 8ebd2c   divss xmm1,[10.0]  8ebd34
    Halo 3   movss xmm1,[1.0]  3649bf / 0.25 at 3649fa   divss xmm1,[10.0]  364a02
    ODST     movss xmm1,[1.0]  3aad43 / 0.25 at 3aad7e   divss xmm1,[10.0]  3aad86
    Reach    movss xmm1,[0.1]  4e31a2   (flat 0.1, no divide, no Flood/Sentinel case)

0.25 is used when the victim's Default Team is Flood or Sentinel (Halo 3 and ODST only
in campaign, Halo 2 always), so those kills cost a quarter.

Every one of those constants is SHARED -- read by 100 to 1900 other instructions in
the same dll -- so nothing shared is written. A private float is placed in the unused
tail of .rdata (past its virtual size, still inside its last mapped page, zero before
it is claimed) and the ONE instruction's rip-relative displacement is repointed at it:

    Halo 2 / 3 / ODST   the divss reads 1 / amount, so a normal kill costs `amount` and
                        a Flood/Sentinel kill still costs a quarter of that
    Reach               the movss reads `amount` directly

Instruction bytes are verified before every write and before restore, so a different
MCC build is refused rather than corrupted. The write is lost when MCC closes; the next
patch with MCC open writes it again.

    python sprint_toolkit/sword_energy_live.py --show
    python sprint_toolkit/sword_energy_live.py --game "Halo 3" --amount 0.05
    python sprint_toolkit/sword_energy_live.py --game "Halo 3" --restore
"""
import argparse
import ctypes
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp                                        # noqa: E402

STOCK_AMOUNT = 0.1   # a normal kill in every one of these games

# game: (module, instruction rva, expected 8 bytes, stock constant rva, slot rva, kind)
SITES = {
    'Halo 2': ('halo2.dll', 0x8EBD34, 'f30f5e0d086d3400', 0xC32A44, 0xDF7FC0, 'div'),
    'Halo 3': ('halo3.dll', 0x364A02, 'f30f5e0db2284e00', 0x8472BC, 0x89AFC0, 'div'),
    'Halo 3: ODST': ('halo3odst.dll', 0x3AAD86, 'f30f5e0d8ee94d00', 0x88971C, 0x8DEFC0,
                     'div'),
    'Halo Reach': ('haloreach.dll', 0x4E31A2, 'f30f100d427a5a00', 0xA8ABEC, 0xAF9FC0,
                   'load'),
}
INSN_LEN = 8          # F3 0F xx 0D dd dd dd dd -- displacement at +4, relative to +8


def attach(game):
    site = SITES.get(game)
    if not site:
        return None, None, None, 'no hardcoded sword drain in %s' % game
    pid = dp.find_pid()
    if not pid:
        return None, None, None, 'MCC is not running (no %s)' % dp.EXE
    base = dp.module_base(pid, site[0].encode())
    if not base:
        return None, None, None, '%s is not loaded in pid %d' % (site[0], pid)
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    if not h:
        return None, None, None, ('OpenProcess failed (%d) -- run this elevated'
                                  % ctypes.get_last_error())
    return h, base, site, None


def state(h, base, site):
    """(amount per normal kill now in effect, 'stock'|'ours'|'unknown', target rva)."""
    _mod, rva, _b, stock, slot, kind = site
    raw = dp.read(h, base + rva + 4, 4)
    if raw is None:
        return None, 'unreadable', None
    at = rva + INSN_LEN + struct.unpack('<i', raw)[0]
    val = dp.read(h, base + at, 4)
    v = struct.unpack('<f', val)[0] if val else None
    amount = None
    if v is not None:
        amount = (1.0 / v if v else float('inf')) if kind == 'div' else v
    where = 'stock' if at == stock else 'ours' if at == slot else 'unknown'
    return amount, where, at


def _verify(h, base, site):
    _mod, rva, expect, stock, slot, _k = site
    insn = dp.read(h, base + rva, INSN_LEN)
    if insn is None:
        return 'could not read the instruction'
    # the displacement may already be ours; compare the opcode half, then the target
    if insn[:4] != bytes.fromhex(expect)[:4]:
        return ('the drain instruction does not match (found %s, expected %s) -- this MCC '
                'build differs, refusing to write' % (insn.hex(), expect))
    _a, where, at = state(h, base, site)
    if where == 'unknown':
        return ('the instruction points at rva 0x%X, neither the stock constant nor our '
                'slot -- refusing to write' % at)
    return None


def apply(h, base, site, amount):
    err = _verify(h, base, site)
    if err:
        return False, err
    _mod, rva, _e, _stock, slot, kind = site
    _a, where, _at = state(h, base, site)
    if where != 'ours':
        cur = dp.read(h, base + slot, 4)
        if cur != b'\0\0\0\0':
            return False, ('the scratch slot at rva 0x%X is not zero (%s) -- this build '
                           'uses it, refusing to write' % (slot, cur.hex() if cur else '?'))
    amount = max(0.0, float(amount))
    if kind == 'div':
        slotval = (1.0 / amount) if amount > 0 else float('inf')   # x / inf = 0
    else:
        slotval = amount
    # value first, so the instruction never points at an uninitialised slot
    ok, err = dp.write(h, base + slot, struct.pack('<f', slotval), dp.PAGE_READWRITE)
    if not ok:
        return False, 'writing the float: %s' % err
    if where != 'ours':
        ok, err = dp.write(h, base + rva + 4, struct.pack('<i', slot - (rva + INSN_LEN)))
        if not ok:
            return False, 'repointing the instruction: %s' % err
    return True, None


def restore(h, base, site):
    err = _verify(h, base, site)
    if err:
        return False, err
    _mod, rva, _e, stock, slot, _k = site
    _a, where, _at = state(h, base, site)
    if where != 'stock':
        ok, err = dp.write(h, base + rva + 4, struct.pack('<i', stock - (rva + INSN_LEN)))
        if not ok:
            return False, err
    # Clear our float too, or the next apply finds a non-zero slot and (rightly) refuses
    # to claim it. The slot is only ever ours: apply() claimed it when it read zero.
    if dp.read(h, base + slot, 4) != bytes(4):
        ok, err = dp.write(h, base + slot, bytes(4), dp.PAGE_READWRITE)
        if not ok:
            return False, 'clearing the slot: %s' % err
    return True, ('already stock' if where == 'stock' else None)


def push(game, amount=None):
    """Set (amount) or restore (None) for one game. Never raises; returns a dict."""
    h, base, site, err = attach(game)
    if err:
        return {'ok': False, 'reason': err}
    try:
        before, where, _ = state(h, base, site)
        if amount is None:
            ok, e = restore(h, base, site)
        else:
            ok, e = apply(h, base, site, amount)
        if not ok:
            return {'ok': False, 'reason': e}
        after, where2, _ = state(h, base, site)
        return {'ok': True, 'old': before, 'new': after, 'was': where, 'now': where2}
    finally:
        dp.k32.CloseHandle(h)


def is_patched(game):
    h, base, site, err = attach(game)
    if err:
        return None
    try:
        return state(h, base, site)[1] == 'ours'
    finally:
        dp.k32.CloseHandle(h)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', choices=sorted(SITES))
    ap.add_argument('--amount', type=float, help='energy per normal kill (stock 0.1)')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args(argv)
    games = [a.game] if a.game else sorted(SITES)
    rc = 0
    for g in games:
        if a.show or (a.amount is None and not a.restore):
            h, base, site, err = attach(g)
            if err:
                print('%-13s %s' % (g, err))
                continue
            try:
                amt, where, at = state(h, base, site)
                print('%-13s %s  per kill %s  (reads rva 0x%X, %s)'
                      % (g, site[0], None if amt is None else round(amt, 5), at, where))
            finally:
                dp.k32.CloseHandle(h)
            continue
        res = push(g, None if a.restore else a.amount)
        print('%-13s %s' % (g, res))
        rc |= 0 if res.get('ok') else 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
