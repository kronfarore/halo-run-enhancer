r"""Patch the strings MCC actually shows, which are NOT the ones in the map.

This is the piece that made the pickup prompt unfixable from the tag side. Halo 3's
`ui\hud\hud_messages` tag can be edited, rebuilt into the map and verified present --
"Picked up SAW" really is in 010_jungle.map, and U+E144 really is gone from it -- and the
game will still say "Picked up an Automag" and still draw the automag's icon, because
MCC does not read the map's copy at all.

It reads **data\UI\Localization\<LANG>_Halo3.bin**, a loose file next to the game, one
per language. That is the source of truth for every HUD message, and because the ICON is
a character inside the message (see `h3_saw_pickup_icon`), the pickup icon comes from
there too. Nothing in the map, the tags or the font package can override it.

Being loose is the good news: a change here needs NO map rebuild and shows up on the
next load.

FORMAT. 16-byte header -- magic 0x90ce6b7a, then the payload size twice, then zero --
followed by NUL-terminated UTF-8 strings packed back to back with a little padding, and
an index elsewhere that points at each string's START. So a string may be SHORTENED in
place (write it short, terminate, leave the freed bytes as NUL) but the file must never
change length or every offset after it moves. That invariant is checked before saving.

    python h3_mcc_localization.py                 # what it would change, all languages
    python h3_mcc_localization.py --write
    python h3_mcc_localization.py --restore
"""
import argparse, io, os, re, shutil, struct, sys

B = os.sep
MCC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(MCC)
LOC = os.path.join(ROOT, 'data', 'UI', 'Localization')
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'mcc_localization')
MAGIC = 0x90CE6B7A
DONOR_GLYPH = 0xE144           # the automag's icon
DONOR_NAME = b'Automag'


def strings_at(d, at):
    """The whole NUL-terminated string that the byte at `at` belongs to."""
    s = at
    while s > 0 and d[s - 1] != 0:
        s -= 1
    e = d.find(b'\0', at)
    return s, e


def patch(d, glyph, name):
    """Returns (data, glyphs swapped, names rewritten, articles fixed)."""
    d = bytearray(d)
    old, new = chr(DONOR_GLYPH).encode('utf-8'), chr(glyph).encode('utf-8')
    if len(old) != len(new):
        raise SystemExit('glyphs differ in UTF-8 length')
    g = 0
    i = 0
    while True:
        i = bytes(d).find(old, i)
        if i < 0:
            break
        d[i:i + len(old)] = new
        g += 1
        i += len(new)

    call = name.encode('utf-8')
    if len(call) > len(DONOR_NAME):
        raise SystemExit('%r is longer than %r' % (name, DONOR_NAME.decode()))
    n = a = 0
    while True:
        i = bytes(d).find(DONOR_NAME)
        if i < 0:
            break
        s, e = strings_at(bytes(d), i)
        if not name:
            # BLANK, WHICH MEANS SPACES. The confirmation line ("Picked up an Automag"
            # and its two ammo variants) is the only per-port TEXT, and a port does not
            # need one -- the prompts carry the icon, which is what matters. So the whole
            # line is blanked rather than renamed, and nothing has to be written per port.
            #
            # It cannot be blanked by terminating it early: the index is ordinal, so the
            # freed bytes would become empty entries and renumber every string after
            # them. A line of spaces keeps the entry, the offsets and the length, and
            # shows as nothing.
            text = b''
        else:
            text = bytes(d[s:e]).replace(DONOR_NAME, call)
            if name[:1].upper() not in 'AEIOU' and b'an ' + call in text:
                text = text.replace(b'an ' + call, b'a ' + call)
                a += 1
        # PAD WITH SPACES, NEVER WITH NUL.
        #
        # The file is indexed by ORDINAL -- the Nth NUL-terminated string -- not only by
        # byte offset. Filling the bytes freed by a shorter name with NUL therefore does
        # not "leave dead space", it invents extra EMPTY ENTRIES: rewriting five strings
        # added 21 of them and shifted every entry after index 2126, so the Assault
        # Rifle's pickup line came out as "CARNAGE REPORT" and the icon line as a
        # service-tag error. Spaces keep the byte length, the entry count and every
        # offset identical, and are invisible at the end of a line.
        d[s:e] = text + b' ' * (e - s - len(text))
        n += 1
    return bytes(d), g, n, a


def entries(b):
    """The start offset of every NUL-terminated string, which is how they are indexed."""
    out, i, size = [], 16, len(b)
    while i < size:
        e = b.find(b'\0', i)
        if e < 0:
            break
        out.append(i)
        i = e + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glyph', type=lambda v: int(v, 0), default=0xE128)
    ap.add_argument('--name', default='',
                    help="what the port calls itself; EMPTY (the default) "
                         "blanks the confirmation line instead of renaming it")
    ap.add_argument('--game', default='Halo3')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()

    files = sorted(f for f in os.listdir(LOC) if f.endswith('_%s.bin' % a.game))
    if not files:
        raise SystemExit('no <LANG>_%s.bin in %s' % (a.game, LOC))

    if a.restore:
        for f in files:
            src = os.path.join(BACKUP, f)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(LOC, f))
                print('restored %s' % f)
        return

    print('%-18s %-8s %-8s %-8s %s' % ('file', 'glyphs', 'names', 'articles', 'size'))
    for f in files:
        p = os.path.join(LOC, f)
        d = io.open(p, 'rb').read()
        magic = struct.unpack_from('<I', d, 0)[0]
        if magic != MAGIC:
            print('%-18s skipped, magic %#x' % (f, magic))
            continue
        out, g, n, art = patch(d, a.glyph, a.name)
        # THE CHECK THAT WOULD HAVE CAUGHT IT. Same length is not enough: the index is
        # ordinal, so the ENTRY LIST has to come back identical too, offset for offset.
        if len(out) != len(d):
            raise SystemExit('%s: length changed, every offset after it would move' % f)
        before, after = entries(d), entries(out)
        if before != after:
            k = next((j for j in range(min(len(before), len(after)))
                      if before[j] != after[j]), min(len(before), len(after)))
            raise SystemExit('%s: entry list changed (%d -> %d entries, first moved at '
                             'index %d) -- every string after it would be misindexed'
                             % (f, len(before), len(after), k))
        print('%-18s %-8d %-8d %-8d %d bytes, %d entries intact%s'
              % (f, g, n, art, len(out), len(after),
                 '' if (g or n) else '   (nothing to do)'))
        if a.write and (g or n or art):
            if not os.path.exists(os.path.join(BACKUP, f)):
                os.makedirs(BACKUP, exist_ok=True)
                shutil.copyfile(p, os.path.join(BACKUP, f))
            io.open(p, 'wb').write(out)

    print('\n%s' % ('written -- loose files, so no map rebuild' if a.write
                    else '(dry run -- pass --write)'))


if __name__ == '__main__':
    main()
