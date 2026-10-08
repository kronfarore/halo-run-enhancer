r"""List the SCREEN FLASH of every Halo 1 damage_effect (jpt!) in the HCEEK tags.

Halo 1 has one flash per damage effect: jpt! +0x24 Type, +0x26 Priority, +0x34 Duration,
+0x38 Fade Function, +0x44 Maximum Intensity, +0x4C Color (ARGB floats). Assembly's
Halo1MCC plugin names them Type / Priority / Duration (nth 0 -- 'Duration' occurs five
times in jpt!) / Fade Function / Maximum Intensity / Color. No other Halo 1 tag carries a
player-damage flash: cyborg coll's damage effects are effe tags (decals, no jpt! part),
matg has none. See sprint_toolkit/H1_SCREEN_FLASH.md for what the engine does with them.

    python h1_screen_flash_scan.py                 # weapons\ vehicles\ characters\ globals\ effects\
    python h1_screen_flash_scan.py --all           # also digsite\ levels\ scenery\
    python h1_screen_flash_scan.py --json out.json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402

TAGS = r'F:\SteamLibrary\steamapps\common\HCEEK\tags'
DEFAULT_ROOTS = ('weapons', 'vehicles', 'characters', 'globals', 'effects')


def scan(tags=TAGS, roots=DEFAULT_ROOTS):
    rows = []
    for root, _d, files in os.walk(tags):
        for f in files:
            if not f.endswith('.damage_effect'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, tags)[:-len('.damage_effect')]
            if roots and not rel.split(os.sep)[0] in roots:
                continue
            t = jpt__def.build(filepath=p).data.tagdata
            sf, c = t.screen_flash, t.screen_flash.tint_lower_bound
            rows.append(dict(
                tag=rel, type=sf.type.enum_name, priority=sf.priority.enum_name,
                duration=round(sf.duration, 4), fade=sf.fade_function.enum_name,
                max_intensity=round(sf.maximum_intensity, 4),
                argb=[round(x, 3) for x in (c.a, c.r, c.g, c.b)],
                category=t.damage.category.enum_name))
    return sorted(rows, key=lambda r: r['tag'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json')
    a = ap.parse_args()
    rows = scan(roots=None if a.all else DEFAULT_ROOTS)
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as fh:
            json.dump(rows, fh, indent=1)
    for r in rows:
        if r['type'] == 'none' and not r['duration']:
            continue  # trigger / response / shock-wave tags: no flash
        print('%-52s %-7s %-6s %4.1fs %-9s I %-4s ARGB %s %s' % (
            r['tag'][:52], r['type'], r['priority'], r['duration'], r['fade'],
            r['max_intensity'], r['argb'], r['category']))


if __name__ == '__main__':
    main()
