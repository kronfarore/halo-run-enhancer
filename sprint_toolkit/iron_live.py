r"""Force the IRON skull on, live, in whichever game the run is playing.

Iron: in co-op any death reverts every player to the last checkpoint; solo, a death
restarts the mission. MCC's skulls are code-side globals (see the memory note on
"ice cream flavors"), so Iron cannot be a map edit. This patches the running game dll
the same way death_penalty.py patches the wrapper: fixed RVAs, the stock bytes verified
before every write, and refusing to touch anything it does not recognise.

MCC loads all six game dlls at start, so the patch can go in from the menu. It then
holds through every level load, checkpoint revert and mission restart until restored or
until MCC exits. In co-op BOTH machines have to apply it.

Per game (rva, image base 0x180000000; found 2026-10-05, untested in game):

  Halo 1   the two Iron consumers read the flag through an indexed accessor (iron =
           flavour index 1). Each tests it with a `je` that is NOPed so the branch is
           always taken as if Iron were on:
             +0xAD2379  player-death handler (sets the loss flags)
             +0xAC512B  game-lost timer: iron && solo -> restart, else revert
  Halo 2   the forced-Iron functions are the only Iron consumers (same code as
           h2_dll_patch's coop-no-forced-iron, which this composes with):
             +0x6A5D50  co-op respawn allowed -> never
             +0x6A74C3  co-op loss = ANY player dead (not all)
             +0x6A757D  solo loss -> restart the mission
  Halo 3   every primary-skull read goes through one getter; it now ORs Iron (bit 0)
  ODST     into the campaign value. Outside campaign it returns the raw field rather
           than 0 -- harmless while a campaign run is being played.
  Reach    the load-time copy of the skull mask into game globals jumps to a 14-byte
  Halo 4   cave in the .text slack that ORs Iron (bit 0) into it. Takes effect at the
           NEXT level load (start or restart the mission after applying).

    python sprint_toolkit/iron_live.py --show
    python sprint_toolkit/iron_live.py --game "Halo 3" --on
    python sprint_toolkit/iron_live.py --off            # restore every game
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402  (attach/read/write helpers)

H = bytes.fromhex


def _cave(site, cave, load):
    """Site: `mov rax,[reg+disp32]` (7 bytes) -> jmp cave; nop; nop.
    Cave: the same load, `or al,1`, jmp back to site+7."""
    jmp_to = H('e9') + struct.pack('<i', cave - (site + 5)) + H('9090')
    body = load + H('0c01')
    back = H('e9') + struct.pack('<i', (site + 7) - (cave + len(body) + 5))
    return [(cave, bytes(len(body) + 5), body + back),     # cave first, site last
            (site, load, jmp_to)]


GAMES = {
    'Halo 1': ('halo1.dll', [
        (0xAD2379, H('7417'), H('9090')),
        (0xAC512B, H('7410'), H('9090')),
    ]),
    'Halo 2': ('halo2.dll', [
        (0x6A5D50, H('751e'), H('eb1e')),
        (0x6A74C3, H('7517'), H('eb17')),
        (0x6A757D, H('7407'), H('9090')),
    ]),
    'Halo 3': ('halo3.dll', [
        (0xEFFF9, H('75088b8290fb0000eb0233c0'), H('8b8290fb000075020c019090')),
    ]),
    'Halo 3: ODST': ('halo3odst.dll', [
        (0x10AE51, H('75088b8218fb0000eb0233c0'), H('8b8218fb000075020c019090')),
    ]),
    'Halo Reach': ('haloreach.dll', _cave(0x57231, 0x91DD10, H('488b85d8010000'))),
    'Halo 4': ('halo4.dll', _cave(0x99CA9, 0xB79C10, H('488b8608ce0100'))),
}


def _module(pid, dll):
    return dp.module_base(pid, dll.encode())


def state(h, base, game):
    """'off', 'on', 'partial' or 'unknown' (bytes this module does not recognise)."""
    seen = set()
    for rva, stock, patched in GAMES[game][1]:
        cur = dp.read(h, base + rva, len(stock))
        seen.add('on' if cur == patched else 'off' if cur == stock else 'unknown')
    if 'unknown' in seen:
        return 'unknown'
    return seen.pop() if len(seen) == 1 else 'partial'


def _set(h, base, game, on):
    sites = GAMES[game][1]
    st = state(h, base, game)
    want = 'on' if on else 'off'
    if st == want:
        return True, 'already ' + want
    if st == 'unknown':
        return False, ('%s does not hold the expected bytes at the Iron sites -- this '
                       'MCC build differs, refusing to write' % GAMES[game][0])
    # On: in table order (a cave is filled before its jump points at it).
    # Off: reversed (the jump is taken out before its cave is cleared).
    for rva, stock, patched in (sites if on else reversed(sites)):
        ok, err = dp.write(h, base + rva, patched if on else stock)
        if not ok:
            return False, '%s +0x%X: %s' % (GAMES[game][0], rva, err)
    return True, None


def sync(on_game=None):
    """One call for the GUI. Iron on in `on_game` (None: in none), off everywhere else,
    so a run that drops the skull or moves to another game puts the last one back.
    Returns result rows; never raises."""
    row = {'tag': 'MCC process', 'effect': 'Iron', 'field': 'Iron skull (game dll)'}
    pid = dp.find_pid()
    if not pid:
        if on_game:
            return [{**row, 'ok': False, 'reason': 'MCC is not running'}]
        return []
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    if not h:
        return [{**row, 'ok': False, 'reason': 'OpenProcess failed -- run elevated'}]
    out = []
    try:
        for game, (dll, _sites) in GAMES.items():
            base = _module(pid, dll)
            if not base:
                continue
            on = game == on_game
            before = state(h, base, game)
            if not on and before == 'off':
                continue                              # nothing of ours there
            ok, err = _set(h, base, game, on)
            out.append({**row, 'field': 'Iron skull (%s)' % dll, 'ok': ok,
                        'old': before, 'new': ('on' if on else 'off') if ok else None,
                        'reason': err if not ok else None})
        if on_game and not any(r['field'].endswith('(%s)' % GAMES[on_game][0]) for r in out):
            out.append({**row, 'ok': False,
                        'reason': '%s is not loaded in MCC' % GAMES[on_game][0]})
    finally:
        dp.k32.CloseHandle(h)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', choices=list(GAMES))
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', action='store_true')
    g.add_argument('--show', action='store_true')
    a = ap.parse_args(argv)
    if a.on and not a.game:
        ap.error('--on needs --game')
    if a.on or a.off:
        for r in sync(a.game if a.on else None) or [{'field': '-', 'ok': True,
                                                     'new': 'nothing to restore'}]:
            print('%-28s %s %s' % (r['field'], 'OK ' if r['ok'] else 'FAIL',
                                   r.get('new') or r.get('reason')))
        return
    pid = dp.find_pid()
    if not pid:
        print('MCC is not running')
        return
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    try:
        for game, (dll, _s) in GAMES.items():
            base = _module(pid, dll)
            print('%-14s %s' % (game, state(h, base, game) if base else 'not loaded'))
    finally:
        dp.k32.CloseHandle(h)


if __name__ == '__main__':
    main()
