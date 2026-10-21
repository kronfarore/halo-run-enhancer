r"""Step 7 of a Halo 2 port: a bitmap widget of the port's HUD turned into ANOTHER widget -- its
bitmap, shader and fields taken from a Bungie widget -- without inserting a block element.

Written for the Flamethrower (S1, boot 1, 2026-10-21: 'only the ammo meter, no heat meter'): its HUD
is the BR's clone, and Halo 2 draws heat with plain bitmap widgets whose input is `WEAPON heat`
(the Plasma Rifle's `heat_meter_*`, `heat_background_*` on `WEAPON time on overheat`). The BR's
HUD carries seven scope widgets a non-zooming port blanks (h2_port_scope.py); two of them become
the heat meter and its background.

A widget names a bitmap and a shader that several blanked widgets share, so a reference is moved by
the widget it belongs to: its index among the references with that path, counted in widget order
(tool exports them in element order) -- and only when the widget does not name the target yet, so a
re-run changes nothing. Fields go through h2_tagfield; a field still reading 0 is placed from a
non-zero neighbour of the same widget (h2_port_numbers.pin).

The config's `hud_widgets` section:
    hud       the port's HUD (kit-relative, with extension)
    widgets   [{'name': widget, 'bitmap': tag, 'shader': tag,
                'fields': [(field, value[, (anchor field, byte delta)]), ...]}]

    python h2_port_hud_widgets.py <key> [--write]
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_port_numbers  # noqa: E402
import h2_tagfield as tf  # noqa: E402
import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402

H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
BLOCK = 'bitmap widgets'


def widgets(tag):
    """[(index, name, bitmap, shader)] of every bitmap widget, in element order."""
    out = os.path.join(os.environ.get('TEMP', '.'), '_hud_widgets_%d.xml' % os.getpid())
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml', os.path.abspath(tag), out],
                   cwd=H2EK, capture_output=True, text=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    os.remove(out)
    seg = x[x.index('<block name="bitmap widgets"'):]
    if '<block name="text widgets"' in seg:
        seg = seg[:seg.index('<block name="text widgets"')]
    parts = re.split(r'<element index="(\d+)"[^>]*>', seg)
    rows = []
    for k in range(1, len(parts) - 1, 2):
        b = parts[k + 1]
        nm = re.search(r'string id">([^<]*)<', b)
        bm = re.search(r'type="bitm">([^<]*)<', b)
        sh = re.search(r'type="shad">([^<]*)<', b)
        rows.append((int(parts[k]), nm.group(1) if nm else '', bm.group(1) if bm else '',
                     sh.group(1) if sh else ''))
    return rows


def move(tag, cls, rows, col, idx, new):
    """Repoint widget `idx`'s reference (column `col` of `rows`) to `new`, by its order among the
    widgets naming the same path."""
    old = rows[idx][col]
    if old == new:
        print('   %-24s %s already %s' % (rows[idx][1], cls, new.split('\\')[-1]))
        return False
    nth = sum(1 for r in rows if r[0] < rows[idx][0] and r[col] == old)
    # the reference list also carries the TEXT widgets' and other blocks' refs AFTER the bitmap
    # widgets; identical paths before this widget can only be bitmap widgets (element order).
    # NOT h2_tagref.set_reference(nth=): with eight identical paths it accepted a pooled-copy /
    # record pairing whose REFERENCE LIST was right while the tag no longer loaded ('convert old
    # to new field set failed', boot-1 fixes, 2026-10-21). Every pairing is checked here against
    # the whole export: the intended reference list AND every field row unchanged
    before = h2_tagref.references(tag)
    hits = [i for i, r in enumerate(before) if r == (cls, old)]
    want = list(before)
    want[hits[nth]] = (cls, new)
    rows_before = [r[4] for r in tf.read_all(tf.export(tag))]
    original = open(tag, 'rb').read()
    for j in range(len(h2_tagref.pooled(original, old))):
        for rec in h2_tagref.candidates(original, cls, len(old)):
            open(tag, 'wb').write(h2_tagref.retarget_one(original, cls, old, new, j, rec))
            if h2_tagref.references(tag) != want:
                continue
            x = tf.export(tag)
            if x and [r[4] for r in tf.read_all(x)] == rows_before:
                print('   %-24s %s %s -> %s (copy %d, record 0x%X; every field unchanged)'
                      % (rows[idx][1], cls, old.split('\\')[-1], new.split('\\')[-1], j, rec))
                return True
    open(tag, 'wb').write(original)
    raise SystemExit('%s: no pairing moved only widget %d\'s %s; restored'
                     % (os.path.basename(tag), rows[idx][0], cls))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    c = ports_h2.get(a.key, 'hud_widgets')
    hud = os.path.join(TAGS, c['hud'])
    for w in c['widgets']:
        rows = widgets(hud)
        idx = next(i for i, r in enumerate(rows) if r[1] == w['name'])
        print('%s (widget %d): %s / %s' % (w['name'], rows[idx][0], rows[idx][2].split('\\')[-1],
                                            rows[idx][3].split('\\')[-1]))
        if not a.write:
            continue
        if w.get('bitmap') and move(hud, 'bitm', rows, 2, idx, w['bitmap']):
            rows = widgets(hud)
        if w.get('shader'):
            move(hud, 'shad', rows, 3, idx, w['shader'])
        for f in w.get('fields', ()):
            field, value = f[0], f[1]
            if len(f) > 2:
                h2_port_numbers.pin(hud, field, BLOCK, rows[idx][0], 0, *f[2])
            tf.set_field(hud, field, value, BLOCK, rows[idx][0], 0)
    if not a.write:
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main()
