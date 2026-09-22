r"""What every Halo 3 weapon says when you are standing over it, and where that comes from.

The pickup prompt -- BOTH its text and its icon -- comes from the weapon tag's
`pickup message`, which is a STRING ID, not an enum and not the icon codepoint. The
Assault Rifle's is `ar_pickup`, the SMG's `smg_pickup`. A port cloned from the Assault
Rifle inherits `ar_pickup` and therefore says "Assault Rifle" with the Assault Rifle's
icon, however its own icon field is set.

That is why `private use font icon` did nothing: it was proved irrelevant by setting it
to the gravity hammer's codepoint and seeing no change in game. The glyph lives inside
the pickup STRING.

These fields do not exist in the Assembly plugin at all, which is why they were invisible
for so long -- `tool export-tag-to-xml` names them and Assembly does not. Reach for the
tag's own definitions before concluding a field is absent.

    python h3_pickup_messages.py
"""
import os, re, subprocess, sys, tempfile

EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
TOOL = os.path.join(EK, 'tool.exe')
WEAPONS = os.path.join(EK, 'tags', 'objects', 'weapons')
FIELDS = ('pickup message', 'pickup message (dual)', 'swap message',
          'swap message (dual)', 'private use font icon')


def read(tag_path, scratch):
    out = os.path.join(scratch, 'w.xml')
    subprocess.run([TOOL, 'export-tag-to-xml', tag_path, out], cwd=EK,
                   capture_output=True)
    if not os.path.exists(out):
        return {}
    s = open(out, encoding='utf-8', errors='replace').read()
    got = {}
    for m in re.finditer(r'<field name="([^"]*)" value="([^"]*)" type="([^"]*)"', s):
        if m.group(1) in FIELDS and m.group(1) not in got:
            got[m.group(1)] = m.group(2)
    return got


def main():
    scratch = tempfile.mkdtemp()
    rows = []
    for root, _dirs, files in os.walk(WEAPONS):
        for f in sorted(files):
            if not f.endswith('.weapon'):
                continue
            got = read(os.path.join(root, f), scratch)
            if got:
                rows.append((f[:-len('.weapon')], got))
    print('%-30s %-18s %-18s %s'
          % ('weapon', 'pickup message', 'swap message', 'font icon'))
    for name, g in sorted(rows):
        print('%-30s %-18s %-18s %s'
              % (name[:30], g.get('pickup message', '-') or '(none)',
                 g.get('swap message', '-') or '(none)',
                 g.get('private use font icon', '-')))
    used = sorted({g.get('pickup message') for _n, g in rows if g.get('pickup message')})
    print('\n%d weapon(s); %d distinct pickup message(s):\n   %s'
          % (len(rows), len(used), ' '.join(used)))


if __name__ == '__main__':
    main()
