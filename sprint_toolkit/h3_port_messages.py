r"""Give a ported weapon its OWN pickup messages, instead of taking another weapon's.

THIS REPLACES THE HIJACK. Halo 3's port takes the automag's five messages, which is free
there only because the automag never appears in Halo 3. That does not generalise: in ODST
the automag is the starting pistol, and every other candidate set belongs to a weapon that
is either in the game or is itself a future port. A port must be able to bring its own
line, and it can -- the Editing Kit has the verbs, they had simply never been used:

    tool extract-unicode-strings ui\hud\hud_messages    -> data\ui\hud\hud_messages.txt
    tool strings ui\hud                                 -> rebuilds the tag from it

The source is UTF-16 with a `[Strings]` header and one `name = "text"` per line, and an
icon inside a string is a NAMED MACRO -- `&assault_rifle`, `&energy_sword`,
`&button_action_weapon_primary`. 39 of them exist and there is no `&saw`, because the
macro table is inside `tool` and not in any tag. That does not block anything: a LITERAL
private-use character works in its place, which is what the port writes.

So the whole method is: clone the donor's lines, rename the prefix, swap its icon macro
for the port's own codepoint, re-import. Nothing is taken from any weapon, and it repeats
for every port and every game that has these verbs.

    PORT_EK=odst python h3_port_messages.py                 # show what it would add
    PORT_EK=odst python h3_port_messages.py --write         # add them and re-import
    PORT_EK=odst python h3_port_messages.py --repoint       # point the weapon at them

TESTED IN GAME 2026-09-29, AND IT HALF WORKS. The port's own prompt is right -- its
glyph on three prompts and "Picked up a SAW" on the confirmation -- so the game DOES read
the map's strings, and a port really can bring its own line. But every MCC-era icon in the
rest of the UI disappeared with it.

SOLVED 2026-09-29, and the bug was MINE, not the kit's. The first build lost the pickup
text for every weapon but the port -- no prompt on the ground, no confirmation line, while
menus, subtitles and button glyphs were untouched.

Cause: the extracted source is CRLF, and reading it in TEXT mode collapses that to LF.
Written back, `tool` saw the whole 480-line vanilla body as one malformed entry and
imported only the CRLF-terminated lines that had been appended. It said so plainly --
"imported 8 new english strings", then "not adding text for string_id 'ps_swap', no
english language text exists for it" -- and the damage was measurable in the tag: 479 of
487 entries with english offset -1, their text still in the blob with no pointer to it.
Hence empty prompts rather than missing icons.

So `source()` reads with newline='' and the writer refuses a source with mixed endings.
With that, tool reports "imported 487 new english strings" and every offset is written.

TWO WRONG TURNS ON THE WAY, both worth not repeating:
  * `extract-unicode-strings` after an import reports only the DELTA. Reading that as
    "479 strings were lost" sent me looking for damage that was not there.
  * Deleting the tag first DOES make every string new -- and throws away the eleven other
    languages. It was only ever a workaround for the line endings. Import onto the
    existing tag.

RESULT: 487 entries, every english offset valid, all languages preserved (210811 ->
236739 bytes). The port's 7 ids carry English only, so the other five languages show no
prompt for it until those lines are added to the data_XX sources too.
"""
import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402
import h3_weapon_glyph as wg                                    # noqa: E402

B = os.sep
LIST = B.join(['ui', 'hud', 'hud_messages'])
SRC = os.path.join(h3_kit.DATA, 'ui', 'hud', 'hud_messages.txt')
#: the donor whose lines are cloned, and the port's own prefix
DONOR, PORT = 'ar', 'saw'
#: the donor's icon macro, replaced by the port's literal codepoint
DONOR_ICON = '&assault_rifle'
#: what the confirmation line calls the weapon. A port owning its OWN line may be named:
#: the rule against renaming applies to a line BORROWED from a live weapon, and this is
#: not one.
DONOR_NAME, PORT_NAME = 'an Assault Rifle', 'a SAW'
AMMO_NAME = ('for Assault Rifle', 'for SAW')


def run(verb, *args):
    r = subprocess.run([h3_kit.TOOL, verb, *args], cwd=h3_kit.EK,
                       capture_output=True, text=True, errors='replace')
    return (r.stdout or '') + (r.stderr or '')


def source():
    """The extracted string source, extracting it first if it is not there."""
    if not os.path.exists(SRC):
        out = run('extract-unicode-strings', LIST)
        if not os.path.exists(SRC):
            raise SystemExit('extract-unicode-strings produced nothing:\n' + out[-800:])
    # newline='' MATTERS: the file is CRLF, and reading it in text mode
    # collapses that to LF. Written back, `tool` then sees the whole vanilla
    # body as one malformed entry, imports only the CRLF-terminated lines that
    # were appended, and leaves every pre-existing string with english offset
    # -1 -- text still in the blob, no pointer to it. In game that is every
    # weapon's pickup prompt with no text at all. Measured: 479 of 487.
    return io.open(SRC, encoding='utf-16', newline='').read()


def entries(s, prefix):
    """{id: quoted text} for one prefix, in file order."""
    out = {}
    for line in s.split('\n'):
        m = re.match(r'^(%s_[a-z_]+) = (".*")$' % re.escape(prefix), line.rstrip('\r'))
        if m:
            out[m.group(1)] = m.group(2)
    return out


#: THE HUD WEAPON ICON, in Reach. Reach's chud draws the weapon schematic as TEXT -- a
#: text widget with font "full screen hud message font" and input string `assault_rifle`
#: -- and that id is a line in this same list, `assault_rifle = "&assault_rifle"`, which
#: tool expands to the Assault Rifle's icon glyph. So the port's HUD icon is one more
#: line, `saw = "<its glyph>"`, and the chud's input string pointed at it. The line is
#: nothing but the glyph, so it is the same in every language. Halo 3 and ODST draw the
#: schematic from a bitmap sheet and need no such line.
SCHEMATIC = h3_kit.per_kit(h3=None, odst=None, reach=('assault_rifle', 'saw'),
                           what='the string id the HUD weapon icon is drawn from')


def schematic_line(s, glyph):
    """`saw = "<glyph>"`, cloned from the donor's schematic line, or None."""
    if not SCHEMATIC:
        return None
    donor, port = SCHEMATIC
    # \r? because the source is CRLF and is read with newline='' -- see source()
    m = re.search(r'^%s = (".*")\r?$' % re.escape(donor), s, re.M)
    if not m or DONOR_ICON not in m.group(1):
        raise SystemExit('no `%s = "%s"` line to clone the HUD icon from'
                         % (donor, DONOR_ICON))
    return '%s = %s' % (port, m.group(1).replace(DONOR_ICON, chr(glyph)))


def missing_lines(s, lines):
    """The lines whose id the source does not have yet."""
    return [l for l in lines
            if not re.search(r'^%s = ' % re.escape(l.split(' = ', 1)[0]), s, re.M)]


def port_lines(s, glyph):
    """The port's own lines, cloned from the donor's."""
    out = []
    for k, v in entries(s, DONOR).items():
        text = (v.replace(DONOR_ICON, chr(glyph))
                 .replace(DONOR_NAME, PORT_NAME)
                 .replace(*AMMO_NAME))
        out.append('%s = %s' % (PORT + k[len(DONOR):], text))
    extra = schematic_line(s, glyph)
    if extra:
        out.append(extra)
    return out


#: Where the other eleven languages' sources live, beside `data`.
LANG_GLOB = 'data_*'


def lang_sources():
    """[(folder, path)] for every localized copy of the message source."""
    import glob
    out = []
    for d in sorted(glob.glob(os.path.join(h3_kit.EK, LANG_GLOB))):
        p = os.path.join(d, 'ui', 'hud', 'hud_messages.txt')
        if os.path.isdir(d) and os.path.exists(p):
            out.append((os.path.basename(d), p))
    return out


def localized_lines(path, glyph, english):
    """The port's lines for ONE language.

    THE SPLIT IS THE ICON, and it falls out of the data rather than being imposed: the
    four PROMPT lines carry `&assault_rifle` and name no weapon, so the localized text can
    be cloned verbatim with only the icon swapped -- correct in every language, no
    translation involved. `picked_up` and the two ammo lines DO name the weapon, and there
    is no way to substitute a name into a translated sentence safely: the differing span
    between two weapons' confirmation lines comes out as "'assau", "n Assault", or a
    partial Chinese word. Those three take the ENGLISH line instead, which is a correct
    sentence rather than a mangled one -- and "SAW" is not translated anyway.
    """
    s = io.open(path, encoding='utf-16', newline='').read()
    out, localized, fell_back = [], 0, 0
    for k, v in entries(s, DONOR).items():
        name = PORT + k[len(DONOR):]
        if DONOR_ICON in v:
            out.append('%s = %s' % (name, v.replace(DONOR_ICON, chr(glyph))))
            localized += 1
        elif name in english:
            out.append('%s = %s' % (name, english[name]))
            fell_back += 1
    extra = schematic_line(s, glyph)
    if extra:
        out.append(extra)
        localized += 1
    return out, localized, fell_back


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--glyph', type=lambda v: int(v, 0), default=wg.GLYPH)
    ap.add_argument('--write', action='store_true',
                    help='add the lines and re-import the string list')
    ap.add_argument('--languages', action='store_true',
                    help="write the port's lines into the other languages' sources too")
    ap.add_argument('--repoint', action='store_true',
                    help="point the port's weapon tag at them")
    a = ap.parse_args()
    print(h3_kit.banner())

    s = source()
    have = entries(s, PORT)
    lines = port_lines(s, a.glyph)
    if not lines:
        raise SystemExit('no %s_* lines to clone from' % DONOR)
    print('   %d line(s) cloned from %s_*, icon -> U+%04X%s'
          % (len(lines), DONOR, a.glyph, '  (already present)' if have else ''))
    for l in lines:
        print('      %s' % l.replace(chr(a.glyph), '<glyph>')[:96])

    if a.write:
        # BY ID, not all-or-nothing. This used to skip the file whenever ANY port line was
        # already there, so a line added to the port later -- Reach's HUD icon string --
        # would never have landed, in English or in any language, and nothing said so.
        new = missing_lines(s, lines)
        if new:
            body = s.rstrip('\r\n') + '\r\n' + '\r\n'.join(new) + '\r\n'
            io.open(SRC, 'w', encoding='utf-16', newline='').write(body)
            print('   english: +%d line(s): %s' % (len(new), [l.split(' = ')[0] for l in new]))
        tag = os.path.join(h3_kit.TAGS, LIST + '.multilingual_unicode_string_list')
        keep = tag + '.before_saw'
        import shutil
        if not os.path.exists(keep):
            shutil.copy2(tag, keep)
            print('   kept the shipped list as %s' % os.path.basename(keep))
        before = os.path.getsize(tag)
        # The tag is NOT removed. Deleting it does make every string "new", but it also
        # throws away the eleven other languages, and it was only ever a workaround for
        # the line-ending bug above -- with CRLF preserved, tool reports "imported 487
        # new english strings" against the existing tag and every offset is written.
        out = run('strings', B.join(['ui', 'hud']))
        if a.languages:
            english = dict(l.split(' = ', 1) for l in lines)
            for folder, lp in lang_sources():
                ls = io.open(lp, encoding='utf-16', newline='').read()
                add, loc, fell = localized_lines(lp, a.glyph, english)
                add = missing_lines(ls, add)
                if not add:
                    print('      %-10s already has them' % folder)
                    continue
                eol = '\r\n'
                body = ls.rstrip(eol) + eol + eol.join(add) + eol
                if body.count('\n') != body.count(eol):
                    raise SystemExit('%s: mixed line endings' % folder)
                io.open(lp, 'w', encoding='utf-16', newline='').write(body)
                print('      %-10s +%d line(s): %d localized, %d English fallback'
                      % (folder, len(add), loc, fell))
            out += run('strings-localized', B.join(['ui', 'hud']))

        for line in out.splitlines():
            if 'WARNING' in line or 'ERROR' in line or 'english' in line:
                print('      %s' % line.strip()[:110])
        d = io.open(tag, 'rb').read()
        missing = [l.split(' = ')[0] for l in lines if l.split(' = ')[0].encode() not in d]
        print('   %s: %d -> %d bytes, %d of %d ids present'
              % (os.path.basename(tag), before, len(d), len(lines) - len(missing), len(lines)))
        if missing:
            raise SystemExit('these did not make it in: %s' % missing)

    if a.repoint:
        wp = os.path.join(h3_kit.TAGS, h3_kit.SAW_WEAPON + '.weapon')
        t = h3tag.Tag(wp)
        ok, cov, tot = t.check()
        print('\n   %s parses %s (%d/%d)' % (os.path.basename(wp), ok, cov, tot))
        n = 0
        for k in sorted(entries(s, DONOR)):
            new = PORT + k[len(DONOR):]
            # The Halo 3 port was built by HIJACKING the automag's ids, so the tag there
            # carries am_* and not ar_*. Rename whichever donor prefix is actually in it,
            # so the same command converts a hijacking port to an owning one.
            for pre in (DONOR, 'am'):
                cur = pre + k[len(DONOR):]
                if cur.encode() in bytes(t.data):
                    k = cur
                    break
            # LENGTH CHANGES here (ar_pickup 9 -> saw_pickup 10), so this cannot be the
            # in-place byte swap Halo 3 uses: rename_stringid grows the chunk and every
            # ancestor with it.
            got = t.rename_stringid(k, new)
            if got:
                print('      %-18s -> %-18s %d reference(s)' % (k, new, got))
                n += got
        ok, cov, tot = t.check()
        print('   renamed %d, parses %s (%d/%d)' % (n, ok, cov, tot))
        if not ok:
            raise SystemExit('not saved: the tag no longer spans its file')
        if n:
            t.save(wp)
            print('   wrote %s' % os.path.basename(wp))

    if not (a.write or a.repoint):
        print('\n(dry run -- pass --write, then --repoint)')


if __name__ == '__main__':
    main()
