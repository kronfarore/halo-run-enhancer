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

#: The PROMPT is the line we keep, because it carries a SYMBOL rather than a name and so
#: reads correctly for any weapon. The cut GPMG's prompts use 0xE128 -- and so does a live
#: weapon: that codepoint appears in exactly TWO complete sets of the four prompts (pick
#: up, swap for, take ally's, switch to) where every other weapon has one. One set is the
#: GPMG's and one is not, and nothing in the file says which, so a set is moved and the
#: game is asked. Both codepoints are three bytes of UTF-8, so the file does not move.
PROMPT_GLYPH = 0xE128
PORT_GLYPH = 0xE13D



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


def prompt_sets(data, glyph=None):
    """The prompts carrying `glyph`, split into the two complete sets they form.

    Every other weapon's glyph appears in ONE set of four -- pick up, swap for, take
    ally's, switch to. This one appears in two, which is what says a live weapon and the
    cut donor share it. They are told apart by nothing but which came first in the file,
    so both are offered and the game decides.
    """
    glyph = chr(glyph if glyph is not None else PROMPT_GLYPH).encode('utf-8')
    kinds = (b'to pick up', b'to swap for', b"take ally's", b'to switch to')
    seen = {k: [] for k in kinds}
    for at, raw in strings(data):
        if glyph not in raw:
            continue
        for k in kinds:
            if k in raw:
                seen[k].append(at)
                break
    return ({k: v[0] for k, v in seen.items() if v},
            {k: v[1] for k, v in seen.items() if len(v) > 1})


#: Which of the two sets each prompt belongs to, settled one look at a time. They are NOT
#: one weapon per set: the ground pickup is the donor's in set A, and the ally trade is
#: not -- so the two weapons' prompts are interleaved in the file and only the game can
#: say which is which.
CHOICE = {'to pick up': 'a',        # confirmed in game: the SAW's icon appears
          "take ally's": 'b',       # set A showed no change, so it is the other one
          'to swap for': 'a',       # untested
          'to switch to': 'a'}      # untested


def repoint(data, choice=None, old=None, new=None):
    """Move the chosen prompt of each kind onto the port's glyph, and only that one."""
    old = old if old is not None else PROMPT_GLYPH
    new = new if new is not None else PORT_GLYPH
    choice = choice or CHOICE
    first, second = prompt_sets(data, old)
    out = bytearray(data)
    done = []
    for kind, which in choice.items():
        key = kind.encode()
        want = (first if which == 'a' else second).get(key)
        if want is None:
            continue
        raw = next(r for o, r in strings(data) if o == want)
        edited = raw.replace(chr(old).encode('utf-8'), chr(new).encode('utf-8'))
        if len(edited) != len(raw):
            raise ValueError('the glyphs differ in length; the file would move')
        out[want:want + len(raw)] = edited
        done.append((kind, which, want))
    return bytes(out), done


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
