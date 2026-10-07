r"""Prove a tag edit changed ONLY what it meant to: snapshot a kit tag's XML export before,
diff it after. Every field write of the 2026-10-05 field audit was checked this way (it
caught a signature that wrote "AOE core radius" instead of the damage lower bound).

    python kit_tag_diff.py <kit> snap <tag> [<tag> ...]     before the edit
    python kit_tag_diff.py <kit> diff <tag> [<tag> ...]     after: the changed lines only

<kit> is the editing kit's folder name (H3EK, H3ODSTEK, HREK, H4EK, H2EK); tags are
paths under its tags\ folder, with extension. Snapshots live in %TEMP%\kit_tag_diff_<kit>.
Halo 1 (HCEEK) has no XML export -- compare port_field_audit.flatten('HCEEK', tag) there.
"""
import difflib
import os
import subprocess
import sys

STEAM = r'F:\SteamLibrary\steamapps\common'


def export(kit, tag):
    ek = os.path.join(STEAM, kit)
    out = os.path.join(ek, 'temp', '_kit_tag_diff.xml')       # ABSOLUTE both (H2EK's rule)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(ek, 'tool.exe'), 'export-tag-to-xml',
                    os.path.join(ek, 'tags', tag), out], cwd=ek, capture_output=True)
    if not os.path.exists(out):
        raise SystemExit('could not export %s from %s' % (tag, kit))
    return open(out, encoding='utf-8', errors='replace').read().splitlines()


def h1_lines(tag, filepath=None):
    """Halo 1 (HCEEK has no XML export): every leaf field as 'path = value', through
    port_field_audit.flatten_h1 (Reclaimer)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import port_field_audit
    vals = port_field_audit.flatten_h1(tag, filepath)
    return ['%s = %s' % (k, v[1]) for k, v in vals.items()]


def main():
    # HCEEK also: `against <tags root>` diffs each tag with its copy under another tags
    # tree -- a BACKUP (port_backup.py's shared\), when no snapshot was taken before
    if len(sys.argv) < 4 or sys.argv[2] not in ('snap', 'diff', 'against'):
        raise SystemExit(__doc__)
    kit, mode, tags = sys.argv[1], sys.argv[2], sys.argv[3:]
    if mode == 'against':
        root, tags = tags[0], tags[1:]
        for t in tags:
            old = h1_lines(t, os.path.join(root, t)) if kit == 'HCEEK' else None
            if old is None:
                raise SystemExit('against: HCEEK only')
            d = [l for l in difflib.unified_diff(old, h1_lines(t), lineterm='', n=0)
                 if l[:1] in '+-' and l[:3] not in ('+++', '---')]
            print('== %s (%d changed line(s))' % (t, len(d)))
            print('\n'.join(d) if d else '   (no change)')
        return
    snapdir = os.path.join(os.environ.get('TEMP', '.'), 'kit_tag_diff_' + kit)
    os.makedirs(snapdir, exist_ok=True)
    for t in tags:
        lines = h1_lines(t) if kit == 'HCEEK' else export(kit, t)
        snap = os.path.join(snapdir, t.replace('\\', '_').replace('/', '_') + '.xml')
        if mode == 'snap':
            open(snap, 'w', encoding='utf-8').write('\n'.join(lines))
            print('snap %s (%d lines)' % (t, len(lines)))
            continue
        old = open(snap, encoding='utf-8').read().splitlines()
        d = [l for l in difflib.unified_diff(old, lines, lineterm='', n=0)
             if l[:1] in '+-' and l[:3] not in ('+++', '---')]
        print('== %s' % t)
        print('\n'.join(d) if d else '   (no change)')


if __name__ == '__main__':
    main()
