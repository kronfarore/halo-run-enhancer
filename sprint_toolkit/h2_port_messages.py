r"""Give the Halo 2 port its OWN pickup messages, instead of borrowing the GPMG's.

The Halo 2 port was built on the cut `gpmg`, and it took that weapon's seven message ids
with it. That is a borrow, not a gift: the GPMG is meant to be restored one day, so
`h2_saw_messages.py` could only BLANK the three lines naming it -- the port says nothing
at all when you pick it up. This replaces that. See `PORTING.md`, "Step 8, the text".

H2EK has the same round trip as the Halo 3 kits, with a different import verb:

    tool extract-unicode-strings ui\hud\hud_messages   -> data\ui\hud\hud_messages.txt
    tool new-strings ui\hud                            -> rebuilds the tag from it

THE PREFIX IS FOUR CHARACTERS ON PURPOSE. Halo 2 packs these ids into a POOL with no
terminators -- `...gpmg_pickupgpmg_swapgpmg_picked_up...` -- with the lengths held
elsewhere, which is the same trap `h2_tagref` documents for tag paths: shorten one string
and every later one slides out from under its own offset. `saw2_*` is exactly as long as
`gpmg_*`, so repointing the weapon is a pure in-place byte overwrite with no length
bookkeeping at all, and nothing can desynchronise. It reads as "the SAW in Halo 2", which
is what it is.

The icon macro the GPMG uses is `&sentinel_grenade_weapon`, which is also why the old
method had to guess: that codepoint (0xE128) appears in TWO complete sets of prompts and
nothing in the file says which set is the cut weapon's. Owning our own lines removes the
guess -- the port's glyph is 0xE13D, added by `h2_saw_glyph.py`.

    python h2_port_messages.py                 # show what it would add
    python h2_port_messages.py --write         # add them, all languages, and import
    python h2_port_messages.py --repoint       # point saw.weapon at them
"""
import argparse
import glob
import io
import os
import re
import shutil
import subprocess
import sys

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
TOOL = os.path.join(EK, 'tool.exe')
LIST = B.join(['ui', 'hud', 'hud_messages'])
SRC = os.path.join(EK, 'data', 'ui', 'hud', 'hud_messages.txt')
TAG = os.path.join(EK, 'tags', LIST + '.multilingual_unicode_string_list')
WEAPON = os.path.join(EK, 'tags', 'objects', 'weapons', 'rifle', 'saw', 'saw.weapon')

DONOR, PORT = 'gpmg', 'saw2'          # SAME LENGTH -- see the module docstring
DONOR_ICON = '&sentinel_grenade_weapon'
GLYPH = 0xE13D                        # h2_saw_glyph.py
DONOR_NAME, PORT_NAME = 'GPMG', 'SAW'


def run(verb, *args):
    r = subprocess.run([TOOL, verb, *args], cwd=EK, capture_output=True, text=True,
                       errors='replace')
    return (r.stdout or '') + (r.stderr or '')


def read(path):
    # newline='' MATTERS: the source is CRLF, and text mode collapses it to LF. Written
    # back, tool reads the whole vanilla body as one malformed entry and imports only the
    # appended lines, leaving every pre-existing string unreachable. See PORTING.md.
    return io.open(path, encoding='utf-16', newline='').read()


def entries(s, prefix):
    return dict(re.findall(r'^(%s_[a-z_]+) = (".*")\r?$' % re.escape(prefix), s, re.M))


def port_lines(s, english=None):
    out = []
    for k, v in entries(s, DONOR).items():
        name = PORT + k[len(DONOR):]
        if DONOR_ICON in v:
            out.append('%s = %s' % (name, v.replace(DONOR_ICON, chr(GLYPH))))
        elif english and name in english:
            out.append('%s = %s' % (name, english[name]))
        else:
            out.append('%s = %s' % (name, v.replace(DONOR_NAME, PORT_NAME)))
    return out


def append(path, lines):
    s = read(path)
    if entries(s, PORT):
        return False
    eol = '\r\n'
    body = s.rstrip(eol) + eol + eol.join(lines) + eol
    if body.count('\n') != body.count(eol):
        raise SystemExit('%s: mixed line endings' % path)
    io.open(path, 'w', encoding='utf-16', newline='').write(body)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--repoint', action='store_true')
    a = ap.parse_args()

    if not os.path.exists(SRC):
        run('extract-unicode-strings', LIST)
    if not os.path.exists(SRC):
        raise SystemExit('extract-unicode-strings produced no %s' % SRC)
    s = read(SRC)
    lines = port_lines(s)
    if not lines:
        raise SystemExit('no %s_* lines to clone' % DONOR)
    print('%d line(s) cloned from %s_*, icon -> U+%04X' % (len(lines), DONOR, GLYPH))
    for l in lines:
        print('   %s' % l.replace(chr(GLYPH), '<glyph>')[:98])
    print('\nid lengths match the donor (H2 pools them, so they must): %s'
          % all(len(l.split(' = ')[0]) == len(DONOR) + len(l.split(' = ')[0]) - len(PORT)
                for l in lines))

    if a.write:
        if not os.path.exists(TAG + '.before_saw'):
            shutil.copy2(TAG, TAG + '.before_saw')
            print('kept the shipped list as %s' % os.path.basename(TAG) + '.before_saw')
        before = os.path.getsize(TAG)
        english = dict(l.split(' = ', 1) for l in lines)
        append(SRC, lines)
        for d in sorted(glob.glob(os.path.join(EK, 'data_*'))):
            lp = os.path.join(d, 'ui', 'hud', 'hud_messages.txt')
            if not os.path.exists(lp):
                continue
            got = port_lines(read(lp), english)
            print('   %-10s %s' % (os.path.basename(d),
                                   '+%d line(s)' % len(got) if append(lp, got)
                                   else 'already has them'))
        out = run('new-strings', B.join(['ui', 'hud']))
        for line in out.splitlines():
            if any(w in line for w in ('WARNING', 'ERROR', 'imported')):
                print('   %s' % line.strip()[:110])
        d = io.open(TAG, 'rb').read()
        missing = [l.split(' = ')[0] for l in lines if l.split(' = ')[0].encode() not in d]
        print('   %s: %d -> %d bytes, %d of %d ids present'
              % (os.path.basename(TAG), before, len(d), len(lines) - len(missing), len(lines)))
        if missing:
            raise SystemExit('these did not make it in: %s' % missing)

    if a.repoint:
        d = bytearray(io.open(WEAPON, 'rb').read())
        before = len(d)
        n = 0
        for k in sorted(entries(s, DONOR)):
            new = (PORT + k[len(DONOR):]).encode()
            old = k.encode()
            if len(old) != len(new):
                raise SystemExit('%s and %s differ in length; H2 pools these' % (k, new))
            if old in d:
                d = bytearray(d.replace(old, new))
                n += 1
                print('   %-20s -> %s' % (k, new.decode()))
        if len(d) != before:
            raise SystemExit('the weapon changed length -- not an in-place overwrite')
        if n:
            shutil.copy2(WEAPON, WEAPON + '.before_messages')
            io.open(WEAPON, 'wb').write(bytes(d))
            print('   renamed %d, wrote %s (%d bytes, unchanged)'
                  % (n, os.path.basename(WEAPON), len(d)))
        else:
            print('   nothing to repoint')

    if not (a.write or a.repoint):
        print('\n(dry run -- pass --write, then --repoint)')


if __name__ == '__main__':
    main()
