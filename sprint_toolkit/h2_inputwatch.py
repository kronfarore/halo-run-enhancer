r"""Watch the Halo 2 per-player action bitfield live, to see WHICH slot a button
press actually moves.

The p2-vision-trigger dll patch rests on one assumption: that `[0x1815E40D0]` is an
array with stride 0xB8 indexed by player, so element 0 is player 1 and element 1 is
player 2. Everything else about the patch is verified statically -- the readers, the
single caller, the 19 bytes -- but that assumption cannot be checked without the game
running and two people pressing buttons.

This checks it. Run it with a co-op level loaded and have ONE player at a time hold
the flashlight button. The slot whose bit 20 lights up is the slot that player owns.

    python h2_inputwatch.py                 # follow bit 20 (vision trigger) on 4 slots
    python h2_inputwatch.py --bits          # every bit that moves, not just bit 20
    python h2_inputwatch.py --slots 2 --raw # dump the raw dwords too

Read-only: it never writes to the game's memory. Needs to run elevated, like the rest
of h2_memscan.

Reading it against the SOURCE OF TRUTH matters here: the script sees the array only
through the hijacked verb, so a script that misbehaves cannot tell you whether the
input read is wrong or the ability dispatch is wrong. This separates the two.
"""
import argparse
import ctypes
import struct
import sys
import time

import h2_memscan as M

PTR_RVA = 0x15E40D0          # halo2.dll+15E40D0 holds the pointer to the array
STRIDE = 0xB8                # from the writer at +6BFDD3: imul rcx, player_index, 0xB8
FIELD = 4                    # the action bitfield sits at +4 in each entry
VISION_TRIGGER = 20          # bit 20 -- what player_action_test_vision_trigger reads


def _attach():
    pid = M.find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    base, _ = M.module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    return h, base


def watch(slots=4, bits=False, raw=False, hz=20):
    h, base = _attach()
    print('halo2.dll at 0x%X, pointer slot +%X, stride 0x%X, bit %d'
          % (base, PTR_RVA, STRIDE, VISION_TRIGGER))
    print('Hold the flashlight button, ONE player at a time. Ctrl-C to stop.\n')
    seen = [0] * slots            # every bit ever set, per slot
    last = None
    while True:
        p = M.read(h, base + PTR_RVA, 8)
        if not p:
            time.sleep(0.5)
            continue
        arr, = struct.unpack('<Q', p)
        if not arr:
            print('\rpointer is null -- no level loaded    ', end='')
            time.sleep(0.5)
            continue
        vals = []
        for i in range(slots):
            b = M.read(h, arr + i * STRIDE + FIELD, 4)
            vals.append(struct.unpack('<I', b)[0] if b else 0)
        for i, v in enumerate(vals):
            seen[i] |= v
        cur = tuple((v >> VISION_TRIGGER) & 1 for v in vals)
        line = '  '.join('slot%d %s' % (i, 'HELD' if c else ' .  ')
                         for i, c in enumerate(cur))
        if raw or bits:
            line += '   ' + ' '.join('%08X' % v for v in vals)
        if cur != last:
            print('\r%-100s' % line)
            last = cur
        else:
            print('\r%-100s' % line, end='')
        time.sleep(1.0 / hz)


def summary(slots=4):
    """One-shot: which slots are even live? A slot that is always zero across a whole
    session is either unused or not where that player's input lands."""
    h, base = _attach()
    arr, = struct.unpack('<Q', M.read(h, base + PTR_RVA, 8))
    if not arr:
        raise SystemExit('pointer is null -- is a level loaded?')
    print('array at 0x%X' % arr)
    for i in range(slots):
        b = M.read(h, arr + i * STRIDE, STRIDE)
        if not b:
            print('  slot%d  unreadable' % i)
            continue
        v = struct.unpack_from('<I', b, FIELD)[0]
        nz = sum(1 for c in b if c)
        print('  slot%d @0x%X  field=%08X  bit%d=%d  (%d/%d bytes non-zero)'
              % (i, arr + i * STRIDE, v, VISION_TRIGGER,
                 (v >> VISION_TRIGGER) & 1, nz, STRIDE))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--slots', type=int, default=4)
    ap.add_argument('--bits', action='store_true', help='show the raw bitfields')
    ap.add_argument('--raw', action='store_true')
    ap.add_argument('--summary', action='store_true', help='one shot, no polling')
    ap.add_argument('--hz', type=int, default=20)
    a = ap.parse_args(argv)
    if a.summary:
        return summary(a.slots)
    try:
        watch(a.slots, a.bits, a.raw, a.hz)
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    sys.exit(main() or 0)
