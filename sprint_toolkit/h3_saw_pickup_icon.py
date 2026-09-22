r"""Give the Halo 3 SAW its own pickup prompt, icon and all.

HOW THE PROMPT ACTUALLY WORKS, which took three wrong guesses to pin down:

The weapon tag has `pickup message` and `swap message`, and they are STRING IDs -- not
enums, not the icon codepoint. Assembly's plugin does not expose them at all, which is
why they stayed invisible; `tool export-tag-to-xml` names them and Assembly does not.

The string they name lives in ui\hud\hud_messages and reads, for the Assault Rifle:

    ar_pickup   "Hold  to pick up\r\n"
    ar_swap     "Hold  to swap for\r\n"

so the ICON IS A CHARACTER INSIDE THE STRING --  is the Assault Rifle's glyph --
and there is no weapon name in the prompt at all. A port cloned from the Assault Rifle
inherits `ar_pickup` and therefore shows the Assault Rifle's icon whatever its own
`private use font icon` says. That field was ruled out in game by setting it to the
gravity hammer's codepoint and seeing no change; it is used somewhere else.

THE FIX, in two cheap edits:
  * the weapon's two string ids move to a message nothing in the Halo 3 campaign uses.
    `am_pickup` / `am_swap` belong to the automag, which is an ODST weapon -- and
    'ar_pickup' and 'am_pickup' are the same length, so it is an in-place rename.
  * that message's trailing glyph becomes the port's. U+E144 and U+E128 are both three
    bytes in UTF-8, so nothing in the string blob moves and no offset has to change.

Hijacking a shared string is a real trade: the automag's own prompt changes wherever it
appears. It does not appear in the Halo 3 campaign, so this is confined to ODST, which
has its own maps and its own copy.

    python h3_saw_pickup_icon.py                 # show what it would do
    python h3_saw_pickup_icon.py --write [--glyph 0xE128]
"""
import argparse, io, os, re, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
TAGS = os.path.join(EK, 'tags')
TOOL = os.path.join(EK, 'tool.exe')
SAW = os.path.join(TAGS, 'objects', 'weapons', 'rifle', 'saw', 'saw.weapon')
UNIC = os.path.join(TAGS, 'ui', 'hud', 'hud_messages.multilingual_unicode_string_list')
#: the Assault Rifle's, which the port inherited -> the automag's, which Halo 3 never uses
MOVE = {'ar_pickup': 'am_pickup', 'ar_swap': 'am_swap'}
DEFAULT_GLYPH = 0xE128          # unclaimed by any Halo 3 or ODST weapon, 123x39
AUTOMAG_GLYPH = 0xE144


def strings(scratch):
    """{string id: english offset} from the message list."""
    out = os.path.join(scratch, 'hud_msgs.xml')
    if not os.path.exists(out):
        subprocess.run([TOOL, 'export-tag-to-xml', UNIC, out], cwd=EK,
                       capture_output=True)
    s = io.open(out, encoding='utf-8', errors='replace').read()
    got = {}
    for m in re.finditer(r'<element index="\d+" name="([^"]*)">(.*?)</element>', s, re.S):
        off = re.search(r'name="english offset" value="(-?\d+)"', m.group(2))
        if off:
            got[m.group(1)] = int(off.group(1))
    return got


def blob(tag):
    n = max((x for x in tag.nodes() if x.marker == 'tgda'), key=lambda x: x.length)
    return n.payload_at, n.length


def read_string(tag, at, off):
    d = tag.data
    end = bytes(d).find(b'\0', at + off)
    return bytes(d[at + off:end]).decode('utf-8', 'replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--glyph', type=lambda v: int(v, 0), default=DEFAULT_GLYPH)
    ap.add_argument('--scratch', default=os.environ.get('TEMP', '.'))
    a = ap.parse_args()

    w = h3tag.Tag(SAW)
    have = [p for _o, g, p in w.references()]
    print('weapon: %s' % os.path.basename(SAW))
    u = h3tag.Tag(UNIC)
    at, _n = blob(u)
    offs = strings(a.scratch)
    for src, dst in MOVE.items():
        print('   %-10s -> %-10s   %r -> %r'
              % (src, dst,
                 read_string(u, at, offs[src]) if src in offs else '?',
                 read_string(u, at, offs[dst]) if dst in offs else '?'))
    print('   glyph in the hijacked message: U+%04X -> U+%04X'
          % (AUTOMAG_GLYPH, a.glyph))

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    # 1. the weapon's two string ids
    moved = 0
    for src, dst in MOVE.items():
        moved += w.rename_stringid(src, dst)
    ok, cov, tot = w.check()
    print('\nweapon: renamed %d string id(s); parses %s (%d/%d)' % (moved, ok, cov, tot))
    if not ok:
        raise SystemExit('weapon tag not saved')
    w.save(SAW)

    # 2. the glyph inside the hijacked message -- same length in UTF-8, so in place
    old, new = chr(AUTOMAG_GLYPH).encode('utf-8'), chr(a.glyph).encode('utf-8')
    if len(old) != len(new):
        raise SystemExit('glyphs differ in UTF-8 length; the blob would have to move')
    hits = 0
    for sid in MOVE.values():
        off = offs.get(sid)
        if off is None or off < 0:
            continue
        text = read_string(u, at, off).encode('utf-8')
        if old not in text:
            print('   %s does not carry U+%04X -- left alone' % (sid, AUTOMAG_GLYPH))
            continue
        start = at + off + text.index(old)
        u.data[start:start + len(old)] = new
        hits += 1
    ok, cov, tot = u.check()
    print('messages: %d glyph(s) swapped; parses %s (%d/%d)' % (hits, ok, cov, tot))
    if not ok:
        raise SystemExit('string list not saved')
    u.save(UNIC)
    print('wrote %s\nwrote %s' % (SAW, UNIC))


if __name__ == '__main__':
    main()
