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

THE MECHANISM, measured rather than guessed: adding entries makes MCC stop using
`<LANG>_<Game>.bin` for this string list and fall back to the map wholesale. 62 icon
codepoints exist in the .bin and in NO map string -- E034..E046 (skull descriptions),
E100..E10C (the menu "Select / Back / Friends" hints), E066, E06A, E080 and more -- all
strings MCC added on top of Bungie's 480. The map is a SUBSET, so falling back to it
loses every one of them. Our E04A survives because it is in the map.

Neither the string tag nor the font packages are damaged, and both were checked before
blaming anything: the tag still holds every vanilla line ("Picked up an Assault Rifle" is
there, "Hold " went 168 -> 202 occurrences) and all three font packages validate at 323
entries with every glyph header matching its table, across all five fonts.
(`extract-unicode-strings` reporting only 8 entries afterwards is the extractor printing
the DELTA, not evidence of loss -- that misread cost a detour.)

SO THE CHOICE IS:
  * crack the .bin's index and put the port's strings THERE, which keeps MCC's own
    strings authoritative. Its 16-byte header declares the payload twice with no slack,
    and the tag's string offsets do NOT index it (4% of 468 land on a string start), so
    this is a real reversing job on the container's second header at 0x40; or
  * give the map every string the .bin has, which needs the ids MCC used for its 62
    extra icons -- and those ids exist nowhere in the map, so they cannot be recovered
    from it; or
  * accept the donor's icon on the prompt, which is where Halo 3 and Halo 1 already are.

DO NOT simply revert to hijacking a set on this evidence: the hijack has the same
problem in reverse (the .bin wins, so the text never changes) and it does not generalise.
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
    return io.open(SRC, encoding='utf-16').read()


def entries(s, prefix):
    """{id: quoted text} for one prefix, in file order."""
    out = {}
    for line in s.split('\n'):
        m = re.match(r'^(%s_[a-z_]+) = (".*")$' % re.escape(prefix), line.rstrip('\r'))
        if m:
            out[m.group(1)] = m.group(2)
    return out


def port_lines(s, glyph):
    """The port's own lines, cloned from the donor's."""
    out = []
    for k, v in entries(s, DONOR).items():
        text = (v.replace(DONOR_ICON, chr(glyph))
                 .replace(DONOR_NAME, PORT_NAME)
                 .replace(*AMMO_NAME))
        out.append('%s = %s' % (PORT + k[len(DONOR):], text))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--glyph', type=lambda v: int(v, 0), default=wg.GLYPH)
    ap.add_argument('--write', action='store_true',
                    help='add the lines and re-import the string list')
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
        if not have:
            body = s.rstrip('\r\n') + '\r\n' + '\r\n'.join(lines) + '\r\n'
            io.open(SRC, 'w', encoding='utf-16', newline='').write(body)
        tag = os.path.join(h3_kit.TAGS, LIST + '.multilingual_unicode_string_list')
        keep = tag + '.before_saw'
        if not os.path.exists(keep):
            import shutil
            shutil.copy2(tag, keep)
            print('   kept the shipped list as %s' % os.path.basename(keep))
        before = os.path.getsize(tag)
        out = run('strings', B.join(['ui', 'hud']))
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
