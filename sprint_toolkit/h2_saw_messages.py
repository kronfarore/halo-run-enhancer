r"""Step 8: stop the Halo 2 port calling itself a GPMG.

MCC does not take HUD text from the map. It reads `data\UI\Localization\<LANG>_Halo2.bin`,
a loose file next to the game -- the same discovery that made the Halo 3 pickup prompt
unfixable from the tag side (see `mcc-localization-overrides-tags`). Being loose is the
good news: this needs no rebuild and shows on the next load.

**These lines are BORROWED, not owned.** The GPMG is a cut weapon that is meant to be
restored one day, so its three lines belong to it and not to the port. The rule
(`PORTING.md`, step 8) is therefore: a line that would have to be borrowed is **blanked**,
never reworded, because a reworded line leaves the real weapon wrong for the rest of the
game. The lines that carry a SYMBOL rather than a name -- the pickup prompt is
`<button> to pick up <glyph>` -- already read correctly for any weapon and are left alone.

    Picked up a GPMG                 ->  (spaces)
    Picked up <n> round for GPMG     ->  (spaces)
    Picked up <n> rounds for GPMG    ->  (spaces)

So the port says nothing when picked up, which costs nothing: the prompt carries the icon,
and that is the part that identifies a weapon.

**The file's length must never change.** Its index is a table of (hash, offset) pairs --
7506 of them in the English file, the offsets monotonic -- so moving one byte moves every
string after it out from under its own offset. A shortened line is therefore padded back
to length with **SPACES, never NULs**: a NUL ends the string early and everything after it
becomes a new entry, which is how 21 phantom entries once turned Halo 3's assault rifle
pickup line into "CARNAGE REPORT".

Every language gets the same treatment, because the game picks the file, not the player.
Only the classic `_Halo2` files are touched; `_Halo2A` is Anniversary and unreachable from
a classic rebuild.

    python h2_saw_messages.py              # what it would change
    python h2_saw_messages.py --write
    python h2_saw_messages.py --restore
"""
import argparse
import glob
import os
import shutil
import struct

B = os.sep
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCC = os.path.dirname(TOOL)
LOC = os.path.join(MCC, 'data', 'UI', 'Localization')
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'mcc_localization')
MAGIC = 0x90CE6B7A

#: The weapon whose lines these are. Every line naming it is blanked, not reworded.
WAS = 'GPMG'


def sections(data):
    """(table start, table size) of the language section -- what must not move."""
    if struct.unpack_from('<I', data, 0)[0] != MAGIC:
        raise ValueError('not a localization file')
    size = struct.unpack_from('<I', data, 0x78)[0]
    return 0x7C, size


def strings(data):
    """Every NUL terminated run after the index, as (offset, bytes).

    The count of these is the invariant that matters: a patch that changes it has split
    or merged an entry, and every offset after the damage points at the wrong text.
    """
    start, size = sections(data)
    out, i = [], start + size
    while i < len(data):
        end = data.find(b'\0', i)
        if end < 0:
            break
        out.append((i, data[i:end]))
        i = end + 1
    return out


def rewrite(data):
    """The same bytes with every line naming the donor blanked, same length, spaces."""
    out = bytearray(data)
    changed = []
    for at, raw in strings(data):
        if WAS.encode('latin-1') not in raw:
            continue
        out[at:at + len(raw)] = b' ' * len(raw)
        changed.append((raw.decode('utf-8', 'replace'), ''))
    return bytes(out), changed


def check(before, after):
    """Refuse anything that moved a byte or changed how many strings there are."""
    if len(before) != len(after):
        raise ValueError('file length changed, %d -> %d' % (len(before), len(after)))
    a, b = strings(before), strings(after)
    if len(a) != len(b):
        raise ValueError('entry count changed, %d -> %d -- a NUL got written'
                         % (len(a), len(b)))
    if [x[0] for x in a] != [x[0] for x in b]:
        raise ValueError('an entry moved; every offset after it is now wrong')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(LOC, '*_Halo2.bin')))
    if not files:
        raise SystemExit('no classic Halo 2 localization files in %s' % LOC)
    os.makedirs(BACKUP, exist_ok=True)

    for path in files:
        name = os.path.basename(path)
        keep = os.path.join(BACKUP, name)
        if a.restore:
            if os.path.exists(keep):
                shutil.copy(keep, path)
                print('   restored %s' % name)
            continue

        before = open(path, 'rb').read()
        after, changed = rewrite(before)
        if not changed:
            print('   %-16s nothing to change' % name)
            continue
        check(before, after)
        print('   %-16s %d line(s)' % (name, len(changed)))
        for was, _now in changed:
            print('        %-42s -> (blank)' % was.strip())
        if a.write:
            if not os.path.exists(keep):
                shutil.copy(path, keep)
            open(path, 'wb').write(after)

    if not a.write and not a.restore:
        print('nothing written; pass --write')


if __name__ == '__main__':
    main()
