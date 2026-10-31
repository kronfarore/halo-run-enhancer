r"""Ship a built Halo 3 map: the kit's cache file becomes the enhancer's baseline and the
live map, with the fixes the kit does not hold yet.

`existing_baseline` reads E:\HaloBaselines before the sibling `.bak`, so a map copied over
`halo3\maps` and its `.bak` alone is undone by the next patch (010's root copy kept the
2026-10-04 build that way). This writes all of them from one source.

NOT_AUTOMATICALLY: enhancer placements saved in Sapien without `Not Automatically`, which
would show up on a normal run. Temporary, until the kit's scenario carries the flag (user,
2026-10-31). The placements are only touched if they still look like that (flags 0, no
folder), so an index that moved fails instead of hiding a stock weapon.

    python h3_ship_map.py --map 110_hc
    python h3_ship_map.py --map 110_hc --no-live      (baseline only: a level holds the map)
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import struct
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as hp          # noqa: E402

H3EK_MAPS = r'F:\SteamLibrary\steamapps\common\H3EK\maps'
LIVE_MAPS = os.path.join(os.path.dirname(TOOL), 'halo3', 'maps')
SUBDIR = os.path.join('halo3', 'maps')
NOT_AUTOMATICALLY = {'110_hc': range(117, 128)}
FLAGS, FOLDER = 0x4, 0x42
NOT_AUTO_BIT = 1


def baseline_root():
    with open(os.path.join(TOOL, 'settings.json'), encoding='utf-8') as f:
        return json.load(f).get('baseline_root')


def fix_placements(m, name):
    """Set Not Automatically on the map's listed weapon placements; how many changed."""
    which = NOT_AUTOMATICALLY.get(name, ())
    if not which:
        return 0
    woff, wes = hp._MAP_WEAPONS['Halo 3']['weapons']
    scnr = hp._scnr_base(m)
    base = hp._block_base(m, scnr + woff)
    for i in which:
        e = base + i * wes
        flags = struct.unpack_from('<I', m.data, e + FLAGS)[0]
        folder = struct.unpack_from('<h', m.data, e + FOLDER)[0]
        if flags != 0 or folder != -1:
            raise SystemExit('%s placement %d is not an enhancer placement (flags %#x, '
                             'folder %d): the list is out of date' % (name, i, flags, folder))
        struct.pack_into('<I', m.data, e + FLAGS, flags | NOT_AUTO_BIT)
    return len(which)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--no-live', action='store_true')
    a = ap.parse_args()
    built = os.path.join(H3EK_MAPS, a.map + '.map')
    live = os.path.join(LIVE_MAPS, a.map + '.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(built, 'Halo 3')
    print('%s: %d placement(s) set Not Automatically' % (a.map, fix_placements(m, a.map)))
    base = hp.baseline_path(live, baseline_root(), SUBDIR)
    m.save(base)
    print('baseline ->', base)
    sibling = live + '.bak'
    if os.path.exists(sibling):
        shutil.copy2(base, sibling)
        print('sibling  ->', sibling)
    if not a.no_live:
        shutil.copy2(base, live)
        print('live     ->', live)


if __name__ == '__main__':
    main()
