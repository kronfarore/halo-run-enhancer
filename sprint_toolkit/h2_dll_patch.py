r"""Binary patches for halo2.dll, with verify-before-write and a backup.

Each entry records the exact original bytes and refuses to write unless it finds
them, so a game update or a different install is rejected rather than corrupted.
--revert restores. MCC must be fully CLOSED to patch, and fully RESTARTED for a
patch to take effect: the dll is mapped at process start, so reloading a level is
not enough.

THE ARBITER CAMO FIX -- apply BOTH `no-camo-grant` and `no-arbiter-camo`
Verified in-game 2026-08-06: the Arbiter no longer cloaks, and the camo POWERUP
(and therefore the Run Enhancer camo ability) still works.

How it works. Camo state is a FLOAT at unit+0x2FC (0.0 visible, 1.0 fully cloaked,
ramped by the engine -- that is the fade). The ramp direction is bit 3 of the unit
flags at unit+0x138. TWO sites set that bit, which is why patching either one alone
did nothing:
  * +8F1A90, in a function taking (player index, on/off) with three callers -- a
    hardware breakpoint on unit+0x138 with the condition "value == 0xB" caught the
    Arbiter's cloak here;
  * +8FDE55, inside the per-frame camo updater at +8FDDA0, which re-asserts the bit
    every frame after its own permission chain.
NOP both and the bit is never set for him. The powerup survives because it drives
camo through its own path rather than these.

Found by disassembling the `player_active_camouflage_on` script function
(+789190 -> +69AA30): the only code whose sole job is to read camo state, which gave
up the object table, the handle-resolution arithmetic and the +0x2FC offset at once.
`h2_memscan.py --unit` reproduces the whole chain from static pointers.

Usage:
    python h2_dll_patch.py --list
    python h2_dll_patch.py --apply no-camo-grant
    python h2_dll_patch.py --apply no-arbiter-camo
    python h2_dll_patch.py --revert no-arbiter-camo
"""
import argparse
import os
import shutil

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo2\halo2.dll')

PATCHES = {
    'force-envy-on': {
        'offset': 0x006EF088,          # VA 0x1806EFC88, inside the skull-table clear
        # mov [rip+0xf02961], rbx  -- zeroes skulls 0..7 (table starts at 0x1815F25F0)
        'original': bytes.fromhex('48891d' '6129f000'),
        # mov byte [rip+0xf02961], 1 -- same length, same displacement, so it now SETS
        # arbiter_envy instead of clearing. Diagnostic only: if a Chief level starts
        # cloaking on the flashlight button, then (a) dll patches do take effect at
        # runtime and (b) that byte is what enables camo.
        'patched': bytes.fromhex('c605' '6129f000' '01'),
        'note': 'DIAGNOSTIC: forces the Envy skull on -- Chief should cloak',
    },
    'force-blind-on': {
        'offset': 0x006EF088,          # same site as force-envy-on
        'original': bytes.fromhex('48891d' '6129f000'),
        # mov byte [rip+0xf02967], 1 -> skull index 6 (Blind) at 0x1815F25F6.
        # Blind removes the HUD, so this is an unambiguous answer to "do dll patches
        # reach the running game at all?" -- unlike camo, nothing else can mask it.
        'patched': bytes.fromhex('c605' '6729f000' '01'),
        'note': 'DIAGNOSTIC: forces Blind on -- the HUD should vanish',
    },
    'force-all-skulls': {
        'offset': 0x006EE801,          # VA 0x1806EF401, the skull setter's store
        # mov byte [rbx + rcx], dil  -- skulls[index] = value, the authoritative path
        'original': bytes.fromhex('40883c0b'),
        # mov byte [rbx + rcx], 1 -- same length. Every skull the game sets becomes ON.
        # Blunt, but it proves whether patching the SETTER sticks, where patching the
        # clear did not: the clear runs first and the real skull states overwrite it.
        'patched': bytes.fromhex('c6040b01'),
        'note': 'DIAGNOSTIC: every skull switches on (Blind, Envy, ...)',
    },
    # DEAD END, kept as a record: 0x8F52D7 (VA 0x1808F5ED7) forces the `je` in front
    # of the +8F5EDE camo-off call. Tested in-game -- no effect. That call is not what
    # cuts the cloak; the real limit is the tick timer below.

    'camo-duration-unlimited': {
        'offset': 0x8F0C1D,            # VA 0x1808F181D, the tail of +8F17E0
        # THE 4-SECOND RULE. camo_set(player, ON) at +8F19B0 stamps a tick countdown
        # into unit+0x30A (state lives at unit+0x308: 0 off, 1 on, 2 fading out) and
        # +8F17E0 is what computes it -- one caller, +8F1A7C, so the whole function
        # belongs to camo and can be rewritten safely:
        #     call +6A5E70          ; difficulty
        #     sub ecx, 2 / je       ; 2 Heroic  -> 0.75
        #     cmp ecx, 1 / jne      ; 3 Legendary -> 0.50, else Easy/Normal -> 1.00
        #     mulss xmm6, 8.0       ; base cloak = EIGHT seconds
        #     jmp +706710           ; seconds -> ticks, round(v * 30)
        # 8 x 0.5 = 4 seconds on Legendary, exactly the cut we measured. The three
        # constants are shared 35/732/47 ways across the dll, so they cannot be
        # retuned -- the tail gets replaced instead, returning a fixed tick count:
        #     movaps xmm6, [rsp+0x20]   ; xmm6 is callee-saved, still must be restored
        #     add rsp, 0x38
        #     mov eax, 0x7530           ; 30000 ticks = 1000 s (unit+0x30A is a word,
        #     ret                       ;   so the ceiling is 32767)
        # The engine timer then never fires and the powerup's own duration governs,
        # as it already does for Chief.
        'original': bytes.fromhex('0f28c6' '0f28742420' '4883c438' 'e9e24ee1ff'),
        'patched': bytes.fromhex('0f28742420' '4883c438' 'b830750000' 'c3' '9090'),
        'note': "Arbiter cloak no longer cut to 4s (TEST: Chief camo must still expire)",
    },
    'camo-no-difficulty-scale': {
        'offset': 0x8F0BF6,            # VA 0x1808F17F6, inside +8F17E0
        # The conservative half-measure: keep the 8-second engine cloak but drop the
        # difficulty scaling, so Legendary gets the same 8s as Normal instead of 4s.
        # `movsx ecx, ax` (the difficulty result) becomes a jump straight to the
        # multiply, leaving xmm6 at its initialised 1.0.
        #   0x1808F17F8 + 0x1D = 0x1808F1815, the `mulss xmm6, 8.0`
        'original': bytes.fromhex('0fbfc8'),
        'patched': bytes.fromhex('eb1d' '90'),
        'note': 'ALTERNATIVE to camo-duration-unlimited: 8s cloak on every difficulty',
    },
    'no-camo-grant': {
        'offset': 0x8F0E90,            # VA 0x1808F1A90
        # `or dword ptr [rbx + 0x138], 8` -- the OTHER site that sets the camo bit,
        # inside a function taking (player index, on/off) with three callers. Patching
        # +8FDE55 (the per-frame re-assert) did NOT stop the Arbiter, so his camo is
        # granted through here instead. Test what this breaks: if the Arbiter stops
        # cloaking and the powerup ABILITY still works, this is the right site; if the
        # ability breaks too, both paths share it and the fix has to be conditional.
        'original': bytes.fromhex('838b3801000008'),
        'patched': bytes.fromhex('90' * 7),
        'note': 'Arbiter camo fix, PART 1 of 2 (apply with no-arbiter-camo)',
    },
    'no-arbiter-camo': {
        'offset': 0x8FD255,            # VA 0x1808FDE55  (VA - 0x180000C00 = file offset)
        # `or dword ptr [rdi + 0x138], 8`
        #
        # Camo state is a FLOAT at unit+0x2FC (0.0 visible, 1.0 cloaked; the engine
        # ramps between them). Bit 3 of the unit flags at unit+0x138 chooses the ramp
        # direction, and the per-frame updater at halo2.dll+8FDDA0 RE-ASSERTS that bit
        # here, every frame, after its own permission chain -- which is what keeps the
        # Arbiter cloaked. NOPing it leaves him visible.
        #
        # The POWERUP grant is a SEPARATE site (+8F1A90, in a function taking a player
        # index and an on/off flag, three callers), so the camo ABILITY still works.
        'original': bytes.fromhex('838f3801000008'),
        'patched': bytes.fromhex('90' * 7),
        'note': "Arbiter camo fix, PART 2 of 2 (apply with no-camo-grant)",
    },
}


def _read(path):
    with open(path, 'rb') as f:
        return bytearray(f.read())


def status(path=DLL):
    d = _read(path)
    for name, p in PATCHES.items():
        cur = bytes(d[p['offset']:p['offset'] + len(p['original'])])
        state = ('APPLIED' if cur == p['patched'] else
                 'not applied' if cur == p['original'] else 'UNRECOGNISED')
        print('  %-18s %-14s %s' % (name, state, p['note']))
        if state == 'UNRECOGNISED':
            print('    expected %s or %s, found %s'
                  % (p['original'].hex(), p['patched'].hex(), cur.hex()))


def apply(name, revert=False, path=DLL):
    p = PATCHES[name]
    want = p['patched'] if revert else p['original']
    make = p['original'] if revert else p['patched']
    d = _read(path)
    cur = bytes(d[p['offset']:p['offset'] + len(want)])
    if cur == make:
        print('%s is already %s' % (name, 'reverted' if revert else 'applied'))
        return
    if cur != want:
        raise SystemExit('refusing to write: bytes at 0x%X are %s, expected %s. '
                         'Is this a different halo2.dll?' % (p['offset'], cur.hex(), want.hex()))
    bak = path + '.prepatch.bak'
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
        print('backed up -> %s' % os.path.basename(bak))
    d[p['offset']:p['offset'] + len(make)] = make
    with open(path, 'wb') as f:
        f.write(bytes(d))
    print('%s %s at 0x%X (%s -> %s)'
          % ('reverted' if revert else 'applied', name, p['offset'], cur.hex(), make.hex()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dll', default=DLL)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--apply')
    ap.add_argument('--revert')
    a = ap.parse_args(argv)
    if a.apply:
        apply(a.apply, False, a.dll)
    elif a.revert:
        apply(a.revert, True, a.dll)
    else:
        status(a.dll)


if __name__ == '__main__':
    main()
