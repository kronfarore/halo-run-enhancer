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

THE OUTRO-SKIP GATE (second site, found 2026-11-09: with only the prefetch site, Reach
m10's ending cutscene could not be skipped). One routine per engine answers "may the
player skip this cinematic now?" (H3 0x189030, ODST 0x1BA384, Reach 0xD359C, H4
0x12D24C). A skippable cinematic that is NOT the level's ending one is skippable at
once; an ENDING one (cinematic globals +0x2E H3/ODST, +0x22 Reach, +0x32 H4) only once
the next map the MCC host names has finished precaching (state 2/3 from 0x10F748 /
0x12E478 / 0xAA7F0 / 0x11ED74). With the prefetch branch skipped that map is never
requested, so the ending cutscene never became skippable. The second site jumps over
that test: ending cutscenes are skippable like any other, and the level end loads the
next map itself. Halo 3's outro-skip site is h3_dll_patch.py `outro-skip`.

Measured: ODST (2026-11-07/09) and Reach (2026-11-09) do NOT open the next map
mid-level; both open it when the level ends, so it is locked on the summary screen.
Halo 4 UNPATCHED (2026-11-10, m10_crash -> m020): m020 is never opened, neither mid-level
nor on the summary, and an exclusive read/write open of m020 succeeds there -- Halo 4
needs NO patch; its sites stay here unapplied.
ODST's and Reach's cache slots are read by mcc_map_locks.py (ENGINES).
ODST note: its levels ALSO preload by script, `(game_level_prepare ...)` in
f_end_scene -- the enhancer's `no_level_preload` option removes that (h3_level_prepare.py).

Same contract as h3_dll_patch.py: exact original bytes AND the bytes in front of EVERY
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
        'note': 'EXPERIMENTAL: ODST stops filing the next level (host or prepared)',
        'sites': [{
            'label': 'prefetch',
            'rva': 0x12DEBB,
            # `jne 0x12E070` (taken when 0x10AD98 says skip) -> `jmp 0x12E070`: both
            # next-level branches (state 0 at 0x12DEC1, state 2 at 0x12DF7B) are skipped.
            'offset': 0x0012D2BB,
            'original': bytes.fromhex('0f85af010000'),   # jne 0x12E070
            'patched': bytes.fromhex('e9b001000090'),    # jmp 0x12E070 ; nop
            'context': (0x0012D2B4, bytes.fromhex('e8dfcefdff84c0')),  # call 0x10AD98 ; test al, al
        }, {
            'label': 'outro-skip',
            'rva': 0x1BA3C1,
            'offset': 0x001B97C1,
            'original': bytes.fromhex('7448'),           # je 0x1BA40B (not an ending: skippable)
            'patched': bytes.fromhex('eb48'),            # jmp 0x1BA40B
            'context': (0x001B97B8, bytes.fromhex('80792e00bb01000000')),  # cmp [rcx+0x2E],0 ; mov ebx,1
        }],
    },
    'reach': {
        'dll': os.path.join(MCC, 'haloreach', 'haloreach.dll'),
        'note': 'EXPERIMENTAL: Reach stops filing the next level after 800 ticks in game',
        'sites': [{
            'label': 'prefetch',
            'rva': 0xAA282,
            # `test r14b, r14b ; je 0xAA32F` -> `jmp 0xAA32F`
            'offset': 0x000A9682,
            'original': bytes.fromhex('4584f60f84a4000000'),
            'patched': bytes.fromhex('e9a800000090909090'),
            'context': (0x000A967D, bytes.fromhex('e9ad000000')),   # jmp 0xAA32F (campaign filed)
        }, {
            'label': 'outro-skip',
            'rva': 0xD35EB,
            'offset': 0x000D29EB,
            'original': bytes.fromhex('744a'),           # je 0xD3637
            'patched': bytes.fromhex('eb4a'),            # jmp 0xD3637
            'context': (0x000D29E2, bytes.fromhex('80792200bb01000000')),  # cmp [rcx+0x22],0 ; mov ebx,1
        }],
    },
    'h4': {
        'dll': os.path.join(MCC, 'halo4', 'halo4.dll'),
        'note': 'EXPERIMENTAL: Halo 4 stops filing the next level (MCC host)',
        'sites': [{
            'label': 'prefetch',
            'rva': 0x11E847,
            # `test r14b, r14b ; je 0x11E8DE` -> `jmp 0x11E8DE`
            'offset': 0x0011DC47,
            'original': bytes.fromhex('4584f60f848e000000'),
            'patched': bytes.fromhex('e99200000090909090'),
            'context': (0x0011DC42, bytes.fromhex('e997000000')),   # jmp 0x11E8DE (campaign filed)
        }, {
            'label': 'outro-skip',
            'rva': 0x12D2E9,
            # H4 works out the other conditions first (bl), then tests the ending flag
            'offset': 0x0012C6E9,
            'original': bytes.fromhex('747e'),           # je 0x12D369 (not an ending: keep bl)
            'patched': bytes.fromhex('eb7e'),            # jmp 0x12D369
            'context': (0x0012C6E5, bytes.fromhex('807d3200')),     # cmp byte [rbp+0x32], 0
        }],
    },
}


def _read(p):
    with open(p['dll'], 'rb') as f:
        return f.read()


def _context_ok(data, s):
    co, cb = s['context']
    return bytes(data[co:co + len(cb)]) == cb


def _site_state(data, s):
    if not _context_ok(data, s):
        return 'unknown'
    f = bytes(data[s['offset']:s['offset'] + len(s['original'])])
    return 'applied' if f == s['patched'] else 'clean' if f == s['original'] else 'unknown'


def site_states(name):
    p = PATCHES[name]
    if not os.path.exists(p['dll']):
        return None
    data = _read(p)
    return [(s['label'], _site_state(data, s)) for s in p['sites']]


def state(name):
    ss = site_states(name)
    if ss is None:
        return 'no dll'
    st = {v for _, v in ss}
    if len(st) == 1:
        return st.pop()
    if 'unknown' in st:
        return 'unknown'
    return 'partial (%s)' % ', '.join('%s %s' % kv for kv in ss)


def apply(name, revert=False):
    """All sites or none: every site is checked before any byte is written."""
    p = PATCHES[name]
    data = _read(p)
    todo = []
    for s in p['sites']:
        want, give = (s['patched'], s['original']) if revert else (s['original'], s['patched'])
        if not _context_ok(data, s):
            print('  %s %s: REFUSING -- the code around 0x%08X is not the build this was '
                  'made for (a game update?)' % (name, s['label'], s['offset']))
            return False
        found = bytes(data[s['offset']:s['offset'] + len(want)])
        if found == give:
            print('  %s %s: already %s' % (name, s['label'], 'reverted' if revert else 'applied'))
            continue
        if found != want:
            print('  %s %s: REFUSING -- expected %s at 0x%08X, found %s'
                  % (name, s['label'], want.hex(), s['offset'], found.hex()))
            return False
        todo.append((s, want, give))
    if not todo:
        return True
    bak = p['dll'] + '.bak'
    if not os.path.exists(bak):
        shutil.copy2(p['dll'], bak)
        print('  backed up to %s' % bak)
    try:
        with open(p['dll'], 'r+b') as f:
            for s, _, give in todo:
                f.seek(s['offset'])
                f.write(give)
    except PermissionError:
        print('  %s: the dll is in use -- close MCC completely and run this again' % name)
        return False
    for s, want, give in todo:
        print('  %s %s: %s at 0x%08X (%s -> %s)' % (name, s['label'],
              'reverted' if revert else 'applied', s['offset'], want.hex(), give.hex()))
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
        print('%s  %s  (%s)' % (name, os.path.basename(p['dll']), state(name)))
        for s in p['sites']:
            print('  %s  (context %s)' % (s['label'], 'ok' if _context_ok(data, s) else 'BAD'))
            co = s['context'][0]
            end = s['offset'] + len(s['original'])
            for label, body in (('now', data[co:end]),
                                ('patched', data[co:s['offset']] + s['patched'])):
                rva0 = s['rva'] - (s['offset'] - co)
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
