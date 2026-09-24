r"""Take the scope HUD off a port whose donor could zoom.

A Halo 2 HUD cloned from a zooming weapon carries seven widgets the port has no use for:
`scope_mask`, the four bracket crosshairs (`left/right/top/bottom_crosshair`), the `2x`
magnification label and the `distance_meter`. All seven draw from
`ui\hud\bitmaps\new_hud\scope_masks\<donor>_scope_mask`.

**They looked inert and they are not.** Every one is gated on `[Y] unit flags` = *unit is
zoomed*, and the port's `magnification levels` is 0, so by the tag's own logic none of them
can ever be drawn -- which is exactly the argument that was made, and in game the bracket
art was still there. Whatever the engine really does with those gates, the only reliable
answer is to give the widgets nothing to draw.

So the port gets a blank bitmap -- one transparent image -- and every scope reference in
its HUD points at that instead, with all three sequence indices on each of the seven
widgets set to 0 so none of them can ask for a sprite that is not there. The widgets
survive in the tag, drawing nothing, which needs no structural edit to a loose tag and is
verifiable: tool.exe re-exports the widget list and every scope widget must name the blank.

    python h2_saw_scope.py [--write]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagfield
import h2_tagref
from PIL import Image

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
REL = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'scope_masks'])
DONOR = B.join([REL, 'battle_rifle_scope_mask'])
NAME = 'saw_blank'
PORT = B.join([REL, NAME])
HUD = os.path.join(TAGS, 'ui', 'hud', 'saw.new_hud_definition')
TEMP = os.environ.get('TEMP', '.')

#: the widgets a non-zooming weapon has no use for
SCOPE = ('scope_mask', 'left_crosshair', 'right_crosshair', 'bottom_crosshair',
         'top_crosshair', '2x', 'distance_meter')
SIZE = (8, 8)


def widgets(tag):
    """(index, name, bitmap, [sequence indices]) for every bitmap widget."""
    out = os.path.join(TEMP, '_scope_hud.xml')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.abspath(tag), out], cwd=H2EK, capture_output=True, text=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    seg = x[x.index('<block name="bitmap widgets"'):]
    if '<block name="text widgets"' in seg:
        seg = seg[:seg.index('<block name="text widgets"')]
    parts = re.split(r'<element index="(\d+)"[^>]*>', seg)
    rows = []
    for k in range(1, len(parts) - 1, 2):
        b = parts[k + 1]
        nm = re.search(r'string id">([^<]+)<', b)
        ref = re.search(r'type="bitm">([^<]+)<', b)
        sq = re.findall(r'name="(fullscreen|halfscreen|quarterscreen) sequence index"'
                        r'[^>]*>(-?\d+)', b)
        if nm and ref:
            rows.append((int(parts[k]), nm.group(1), ref.group(1),
                         [int(v) for _f, v in sq]))
    return rows


def blank():
    """A bitmap with nothing in it, for a widget that must not draw."""
    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, NAME + '.tif')
    Image.new('RGBA', SIZE, (0, 0, 0, 0)).save(tif, compression=None)
    dest = os.path.join(TAGS, PORT + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, DONOR + '.bitmap'), dest)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', REL],
                       cwd=H2EK, capture_output=True, text=True)
    for line in ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10)).split(chr(10)):
        line = ' '.join(line.split())
        if NAME in line or 'bitmap created' in line:
            print('   | %s' % line)
    return os.path.exists(dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    before = widgets(HUD)
    targets = [r for r in before if r[1] in SCOPE]
    print('scope widgets in the port HUD:')
    for idx, name, ref, sq in targets:
        print('   %2d %-18s %-28s %s' % (idx, name, ref.split(B)[-1], sq))
    if not a.write:
        print('(dry run -- pass --write)')
        return

    blank()
    have = h2_tagref.references(HUD)
    if ('bitm', DONOR) in have:
        h2_tagref.set_reference(HUD, 'bitm', DONOR, PORT, every=True)
    else:
        print('   the HUD already names no donor scope mask')

    for idx, name, _ref, _sq in targets:
        for field in ('fullscreen', 'halfscreen', 'quarterscreen'):
            key = field + ' sequence index'
            now = h2_tagfield.get(HUD, key, 'bitmap widgets', idx)
            if now and int(now[0]) == 0:
                continue
            h2_tagfield.set_field(HUD, key, 0, 'bitmap widgets', idx)

    print('after:')
    for idx, name, ref, sq in widgets(HUD):
        print('   %2d %-18s %-28s %s' % (idx, name, ref.split(B)[-1], sq))


if __name__ == '__main__':
    main()
