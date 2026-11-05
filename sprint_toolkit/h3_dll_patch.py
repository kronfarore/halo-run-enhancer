r"""Binary patches for halo3.dll, with verify-before-write and a backup.

Same contract as odst_dll_patch.py / h2_dll_patch.py: every entry records the exact
original bytes and refuses to write unless it finds them, so a game update or a
different install is rejected rather than corrupted. --revert restores. MCC must be
fully CLOSED to patch (it maps the dll) and RESTARTED afterwards.

THE SUMMARY-SCREEN LOCK -- `no-next-map-prefetch` (EXPERIMENTAL, unbooted)

Halo 1 and 2 maps can be patched on the post-game summary screen; Halo 3's next map
cannot (user, 2026-11-05) -- it stays locked until it has been started and quit.
Measured live with mcc_map_locks.py while PLAYING 010: 020_base.map is already open,
three read-only handles that share read only, its 16 KB header read and nothing more.
No Halo 3 level script asks for it (h3_level_prepare.py: no game_level_prepare in any
of the nine), so the engine opens it on its own. Traced in halo3.dll (RVAs, image base
0x180000000):

    cache-file slot table      .data 0x20BA420, 0x4018 bytes a slot:
                               +0 handle, +8 the 16 KB header, +0x1E8 path,
                               +0x4008 u32, +0x4010 second handle.
                               Live with 010 running: slot 1 shared, 2 campaign,
                               15 010_jungle, 16 020_base.
    open_slot(slot, name)      0xDAFCC  -- path, both handles, header read + checks
    close_slot(slot)           0xDBC70  -- closes both handles, wipes the header
    startup                    0xDAED8 / 0xDAEFC open slots 0-2 and 3-14
    level load                 0xA65BE: find the map by name in the slots; if it is
                               not there, open_slot(15, name) -- the menu-start path
    PREFETCH                   0xDB2A4, called from the per-frame cache-file update
                               0xDABEC: picks a free slot in 15..0x18 that neither
                               current level uses, close_slot()s it and open_slot()s
                               the NEXT map into it (0xDB762). That is 020 in slot 16.
                               (MCC's port of the Xbox 360 copy-to-HDD read-ahead.)

V1 (below, the precache WORKER) WAS WRONG -- booted 2026-11-05: starting 010 from the
menu showed "Validating" and fell back to the main menu. The worker serves ONE pending
request (name 0x2127004, priority 0x2127104, filed by request_precache 0xDB364), and
every map goes through it, including the level being STARTED:

    0x10F52C  explicit level load: files a request for the level to start, then
              loops until it is in a slot (the "Validating" wait) -- v1 starved it
    0x10F470  automatic precache, every frame, via the chooser 0x10F20C:
                shared (priority 4) if not in a slot, else campaign (3), else
                [rsi] == 0 -> 0x10F038, else
                [rsi] == 2 (r14b, IN GAME) -> ids from 0xA5544, name from 0x2C0950,
                priority 0: THE NEXT LEVEL -- 020 while 010 plays
              ([rsi] = byte at the pointer in .data 0xA46A08)

V2 (`no-next-map-prefetch`) skips only that last branch:

    0x10F34C  45 84 F6           test r14b, r14b
    0x10F34F  0F 84 98000000     je   0x10F3ED     ; not in game -> no request
              E9 99000000 90     jmp  0x10F3ED     ; PATCHED: never in game either

r14b is set at 0x10F2AC and read only there. Everything else keeps working: shared,
campaign, the [rsi] == 0 branch and the explicit level load.

The v1 patch, for the record -- the first instruction of the worker's slot search:

    0xDB6E8  74 25          je  0xDB70F      ; nothing prefetched yet -> straight in
    0xDB70B  3B C3          cmp eax, ebx
    0xDB70D  75 72          jne 0xDB781      ; already prefetched -> done
    0xDB70F  BF 0F000000    mov edi, 0xF     ; the slot search starts at 15
             E9 6D000000    jmp 0xDB781      ; PATCHED: never open a next map

The block has exactly those two entries (the je and the fall-through; no rel32 branch
anywhere in .text lands inside 0xDB70F..0xDB781), so patching the branch at 0xDB70D
alone would NOT do it -- the usual case, nothing prefetched yet, comes in by the je.
0xDB781 only wipes the name buffer and restores registers from the stack. The lines
above the block still close a stale prefetch slot, so nothing is left half-open.
With no prefetch the level load finds no slot by name and opens the map into slot 15:
the same path as starting a level from the menu, which is what works today after
"start the next map, quit out". THE RISK, untested: if the summary screen's Continue
waits for a prefetch to finish, it would hang -- revert and restart MCC.

Usage:
    python h3_dll_patch.py --list
    python h3_dll_patch.py --apply no-next-map-prefetch
    python h3_dll_patch.py --revert no-next-map-prefetch
"""
import argparse
import os
import shutil
import sys

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo3\halo3.dll')

PATCHES = {
    'no-next-map-prefetch': {
        # v2. RVA 0x10F34F, in the automatic precache chooser 0x10F20C (see V2 below):
        # `je 0x10F3ED` after `test r14b, r14b` (r14b = game state byte == 2, in game,
        # read nowhere else) -> always jump, so the chooser never files the NEXT
        # level. The explicit level load and the shared/campaign requests are untouched.
        'offset': 0x0010E74F,
        'original': bytes.fromhex('0f8498000000'),   # je  0x10F3ED
        'patched': bytes.fromhex('e99900000090'),    # jmp 0x10F3ED ; nop
        'context': (0x0010E74C, bytes.fromhex('4584f6')),   # test r14b, r14b
        'note': 'EXPERIMENTAL v2: Halo 3 stops opening the next level while you play, '
                'so it can be patched on the summary screen',
    },
    'v1-worker-skip-BROKEN': {
        # v1, booted 2026-11-05 and FAILED: starting 010 from the menu showed
        # "Validating" and fell back to the main menu. Kept only so --revert can undo it.
        'offset': 0x000DAB0F,          # RVA 0xDB70F, in the precache WORKER
        'original': bytes.fromhex('bf0f000000'),   # mov edi, 0xF
        'patched': bytes.fromhex('e96d000000'),    # jmp 0xDB781
        # the bytes in front of it (cmp eax, ebx; jne 0xDB781), checked too, so a
        # shifted build is refused even if the five bytes happened to match
        'context': (0x000DAB0B, bytes.fromhex('3bc37572')),
        'note': 'BROKEN v1 (levels fail to load) -- revert it',
        'revert_only': True,
    },
}


def _found(data, p):
    o, n = p['offset'], len(p['original'])
    return bytes(data[o:o + n])


def _context_ok(data, p):
    co, cb = p.get('context', (None, b''))
    return co is None or bytes(data[co:co + len(cb)]) == cb


def state(name, dll=DLL):
    """'applied', 'clean' or 'unknown' for one patch, read from the dll on disk."""
    p = PATCHES[name]
    with open(dll, 'rb') as f:
        data = f.read()
    if not _context_ok(data, p):
        return 'unknown'
    f = _found(data, p)
    return 'applied' if f == p['patched'] else 'clean' if f == p['original'] else 'unknown'


def apply(name, revert=False, dll=DLL):
    p = PATCHES[name]
    if p.get('revert_only') and not revert:
        print('  %s: refusing to apply -- it is kept only to be reverted' % name)
        return False
    want = p['patched'] if revert else p['original']
    give = p['original'] if revert else p['patched']
    with open(dll, 'rb') as f:
        data = bytearray(f.read())
    found = _found(data, p)
    if not _context_ok(data, p):
        print('  %s: REFUSING -- the code around 0x%08X is not the build this was made '
              'for (a game update?)' % (name, p['offset']))
        return False
    if found == give:
        print('  %s: already %s' % (name, 'reverted' if revert else 'applied'))
        return True
    if found != want:
        print('  %s: REFUSING -- expected %s at 0x%08X, found %s'
              % (name, want.hex(), p['offset'], found.hex()))
        return False
    bak = dll + '.bak'
    if not os.path.exists(bak):
        shutil.copy2(dll, bak)
        print('  backed up to %s' % os.path.basename(bak))
    data[p['offset']:p['offset'] + len(give)] = give
    try:
        with open(dll, 'r+b') as f:
            f.seek(p['offset'])
            f.write(give)
    except PermissionError:
        print('  %s: the dll is in use -- close MCC completely and run this again' % name)
        return False
    print('  %s: %s at 0x%08X (%s -> %s)'
          % (name, 'reverted' if revert else 'applied', p['offset'],
             want.hex(), give.hex()))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dll', default=DLL)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--apply', action='append', default=[])
    ap.add_argument('--revert', action='append', default=[])
    a = ap.parse_args(argv)

    if not os.path.exists(a.dll):
        raise SystemExit('not found: %s' % a.dll)
    if a.list or not (a.apply or a.revert):
        print('halo3.dll (%d bytes)' % os.path.getsize(a.dll))
        for name, p in PATCHES.items():
            print('  %-22s %-8s %s' % (name, state(name, a.dll).upper(), p['note']))
        return 0
    ok = True
    for n in a.apply:
        ok &= apply(n, False, a.dll)
    for n in a.revert:
        ok &= apply(n, True, a.dll)
    print('\nMCC must be fully restarted for this to take effect.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
