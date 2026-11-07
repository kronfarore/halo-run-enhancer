r"""Stop ODST / Reach / Halo 4 opening the NEXT map while you play (EXPERIMENTAL).

Halo 3's version is h3_dll_patch.py `no-next-map-prefetch` (v3), confirmed in game
2026-11-06: with it, 020 was not opened during 010, could be patched on the summary
screen, and Continue loaded it. This file carries the same patch to the other three
third-generation engines, found 2026-11-07 by matching their code against Halo 3's.

THE CHOOSER. Every frame the engine asks one routine what it should precache next.
In all four dlls it has the same shape: request `levels\shared\shared\shared`, then
`...\campaign`, then -- only once both are resident -- a branch that files the NEXT
level. Skipping that last branch is the whole patch; shared / campaign requests and
the explicit level load (which files its own request) are untouched.

  game   chooser   next-level branch                                  site (RVA)
  -----  --------  -------------------------------------------------  ----------
  H3     0x10F20C  state 0 -> 0x10F038 (MCC host, vtable +0x80);       0x10F33C
                   state 2 -> by level index                (h3_dll_patch.py)
  ODST   0x12DD10  0x10AD98 gate; state 0 -> 0x12D8F0 (the level       0x12DEBB
                   game_level_prepare named) or 0x12DADC (MCC host);
                   state 2 -> by level index
  Reach  0xAA090   state 0, campaign, game time > 800 ticks ->         0xAA282
                   0xA9E70 (next map)
  H4     0x11E66C  state flag -> 0x11E444 (MCC host, vtable +0x80)     0x11E847

ODST's own cache-slot table / request record are read by mcc_map_locks.py (ENGINES).
ODST note: its levels ALSO preload by script, `(game_level_prepare ...)` in
f_end_scene -- the enhancer's `no_level_preload` option removes that (h3_level_prepare.py).
Measured 2026-11-07 with sc120 loaded (unpatched dll, script call still present): only
sc120 / campaign / shared open, no pending request -- ODST did not prefetch mid-level
the way Halo 3 did. The summary-screen reading is the open question.

Reach / Halo 4: nobody has reported a summary-screen lock there yet; the code says the
next map is opened in game (Reach after 800 ticks), so expect Halo 3's behaviour.

Same contract as h3_dll_patch.py: exact original bytes AND the bytes in front of the
site must match, or nothing is written; first write backs the dll up to <dll>.bak.
MCC must be CLOSED to patch (the dll is mapped) and restarted afterwards.

    python next_map_prefetch.py                    # state of every game's patch
    python next_map_prefetch.py --check            # disassemble each site, before/after
    python next_map_prefetch.py --apply odst       # odst | reach | h4 (several allowed)
    python next_map_prefetch.py --revert odst
"""
import argparse
import os
import shutil
import sys

MCC = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'

PATCHES = {
    'odst': {
        'dll': os.path.join(MCC, 'halo3odst', 'halo3odst.dll'),
        'rva': 0x12DEBB,
        # `jne 0x12E070` (taken when 0x10AD98 says skip) -> `jmp 0x12E070`: both
        # next-level branches (state 0 at 0x12DEC1, state 2 at 0x12DF7B) are skipped.
        'offset': 0x0012D2BB,
        'original': bytes.fromhex('0f85af010000'),   # jne 0x12E070
        'patched': bytes.fromhex('e9b001000090'),    # jmp 0x12E070 ; nop
        'context': (0x0012D2B4, bytes.fromhex('e8dfcefdff84c0')),  # call 0x10AD98 ; test al, al
        'note': 'EXPERIMENTAL: ODST stops filing the next level (host or prepared)',
    },
    'reach': {
        'dll': os.path.join(MCC, 'haloreach', 'haloreach.dll'),
        'rva': 0xAA282,
        # `test r14b, r14b ; je 0xAA32F` -> `jmp 0xAA32F`
        'offset': 0x000A9682,
        'original': bytes.fromhex('4584f60f84a4000000'),
        'patched': bytes.fromhex('e9a800000090909090'),
        'context': (0x000A967D, bytes.fromhex('e9ad000000')),   # jmp 0xAA32F (campaign filed)
        'note': 'EXPERIMENTAL: Reach stops filing the next level after 800 ticks in game',
    },
    'h4': {
        'dll': os.path.join(MCC, 'halo4', 'halo4.dll'),
        'rva': 0x11E847,
        # `test r14b, r14b ; je 0x11E8DE` -> `jmp 0x11E8DE`
        'offset': 0x0011DC47,
        'original': bytes.fromhex('4584f60f848e000000'),
        'patched': bytes.fromhex('e99200000090909090'),
        'context': (0x0011DC42, bytes.fromhex('e997000000')),   # jmp 0x11E8DE (campaign filed)
        'note': 'EXPERIMENTAL: Halo 4 stops filing the next level (MCC host)',
    },
}


def _read(p):
    with open(p['dll'], 'rb') as f:
        return f.read()


def _context_ok(data, p):
    co, cb = p['context']
    return bytes(data[co:co + len(cb)]) == cb


def state(name):
    p = PATCHES[name]
    if not os.path.exists(p['dll']):
        return 'no dll'
    data = _read(p)
    if not _context_ok(data, p):
        return 'unknown'
    f = bytes(data[p['offset']:p['offset'] + len(p['original'])])
    return 'applied' if f == p['patched'] else 'clean' if f == p['original'] else 'unknown'


def apply(name, revert=False):
    p = PATCHES[name]
    want, give = (p['patched'], p['original']) if revert else (p['original'], p['patched'])
    data = _read(p)
    if not _context_ok(data, p):
        print('  %s: REFUSING -- the code around 0x%08X is not the build this was made '
              'for (a game update?)' % (name, p['offset']))
        return False
    found = bytes(data[p['offset']:p['offset'] + len(want)])
    if found == give:
        print('  %s: already %s' % (name, 'reverted' if revert else 'applied'))
        return True
    if found != want:
        print('  %s: REFUSING -- expected %s at 0x%08X, found %s'
              % (name, want.hex(), p['offset'], found.hex()))
        return False
    bak = p['dll'] + '.bak'
    if not os.path.exists(bak):
        shutil.copy2(p['dll'], bak)
        print('  backed up to %s' % bak)
    try:
        with open(p['dll'], 'r+b') as f:
            f.seek(p['offset'])
            f.write(give)
    except PermissionError:
        print('  %s: the dll is in use -- close MCC completely and run this again' % name)
        return False
    print('  %s: %s at 0x%08X (%s -> %s)' % (name, 'reverted' if revert else 'applied',
                                             p['offset'], want.hex(), give.hex()))
    return True


def check():
    """Disassemble each site as it is on disk and as the patch would make it."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for name, p in PATCHES.items():
        if not os.path.exists(p['dll']):
            print('%s: no dll' % name)
            continue
        data = _read(p)
        print('%s  %s  (%s, context %s)' % (name, os.path.basename(p['dll']),
                                            state(name), 'ok' if _context_ok(data, p) else 'BAD'))
        co = p['context'][0]
        end = p['offset'] + len(p['original'])
        for label, body in (('now', data[co:end]),
                            ('patched', data[co:p['offset']] + p['patched'])):
            rva0 = p['rva'] - (p['offset'] - co)
            ins = ['%x %s %s' % (i.address, i.mnemonic, i.op_str)
                   for i in md.disasm(bytes(body), rva0)]
            print('   %-8s %s' % (label, ' | '.join(ins)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', nargs='+', default=[], choices=sorted(PATCHES))
    ap.add_argument('--revert', nargs='+', default=[], choices=sorted(PATCHES))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    if a.check:
        check()
        return 0
    ok = True
    for n in a.apply:
        ok &= apply(n)
    for n in a.revert:
        ok &= apply(n, revert=True)
    for name, p in PATCHES.items():
        print('  %-6s %-8s %s' % (name, state(name).upper(), p['note']))
    if a.apply or a.revert:
        print('\nMCC must be fully restarted for this to take effect.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
