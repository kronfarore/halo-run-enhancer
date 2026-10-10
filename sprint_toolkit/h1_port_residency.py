r"""Residency of every Halo 1 port on the BUILT maps (the batch rebuild's first check,
H1_PORT_PLAN.md "Definition of done": palette entry + resident-only placement in all ten
scenarios, checked on the built maps).

Per map and port: the weapon tag is in the map AND every catalog `requires` tag (the
enhancer counts a port as present only then), and the scenario's weapons palette names it.
Ports come from ports_h1 (every config with a 'pickable' section, plus the SAW).

    python h1_port_residency.py                      # the deployed maps (halo1\maps)
    python h1_port_residency.py --dir F:\...\HCEEK\maps
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import paths  # noqa: E402
import ports_h1  # noqa: E402
import halo_patch  # noqa: E402
import h1_enemy_test_map as E  # noqa: E402

MAPS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']


def palette_offset():
    """scnr 'Weapon Palette' block offset, read from the Halo1 plugin."""
    import re
    s = open(paths.SCNR_XML, encoding='utf-8', errors='replace').read()
    m = re.search(r'<tagblock name="Weapon Palette" offset="(0x[0-9A-Fa-f]+)"', s)
    if not m:
        raise SystemExit('no Weapon Palette block in ' + paths.SCNR_XML)
    return int(m.group(1), 16)


def ports():
    cat = {e['weapon']: e for e in json.load(open(os.path.join(ROOT, 'weapon_ports_catalog.json'),
                                                  encoding='utf-8')).get('Halo 1', [])}
    out = []
    for key, p in ports_h1.all_ports():
        w = (p.get('pickable') or {}).get('weapon')
        if key == 'saw':
            w = r'weapons\saw\saw'
        if not w:
            continue
        req = [r.split(' ', 1) for r in cat.get(p['name'], {}).get('requires', [])]
        out.append((key, p['name'], w, req))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(paths.MCC, 'halo1', 'maps'))
    a = ap.parse_args()
    pal_off = palette_offset()
    pl = ports()
    bad = 0
    print('%-6s %s' % ('map', '  '.join(k[:6] for k, *_ in pl)))
    for mp in MAPS:
        m = halo_patch.open_map(os.path.join(a.dir, mp + '.map'), 'Halo 1')
        names = {v[0]: k[1].lower() for k, v in E.tag_ids(m).items()}
        scnr = [v for k, v in m.tags.items() if k[0] == 'scnr'][0]
        cnt, ptr = struct.unpack_from('<II', m.data, scnr + pal_off)
        arr = (ptr - m.magic) & 0xFFFFFFFF
        pal = {names.get(struct.unpack_from('<I', m.data, arr + i * 0x30 + 12)[0], '')
               for i in range(cnt)}
        row = []
        for key, name, w, req in pl:
            have_w = ('weap', w) in m.tags or any(k == ('weap', w) for k in m.tags)
            have_r = all((c, t) in m.tags for c, t in req)
            in_pal = w.lower() in pal
            ok = have_w and have_r and in_pal
            bad += not ok
            row.append('ok    ' if ok else ('%s%s%s   ' % ('W' if not have_w else '-',
                                                             'R' if not have_r else '-',
                                                             'P' if not in_pal else '-'))[:6])
        print('%-6s %s' % (mp, '  '.join(row)))
    print('\n%d port x map pair(s) missing (W = weapon tag, R = a requires tag, P = palette)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
