r"""Compare Player Starting Profiles across every ODST (and optionally H3) level.

Kikowani looks structurally odd -- 16 profiles named "buck"/"a" instead of the usual
"player starting profile_N" -- and the whole starting-weapon wall might be a property
of that shape rather than of the weapon tags. This prints the shape of every level's
profile block side by side so "sc150 is weird" can be checked instead of assumed.

    python odst_profile_scan.py
    python odst_profile_scan.py --game "Halo 3"
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                         # noqa: E402

ROOTS = {
    'Halo 3: ODST': (r"C:\Program Files (x86)\Steam\steamapps\common"
                     r"\Halo The Master Chief Collection\halo3odst\maps"),
    'Halo 3': (r"C:\Program Files (x86)\Steam\steamapps\common"
               r"\Halo The Master Chief Collection\halo3\maps"),
}
SKIP = {'mainmenu', 'shared', 'campaign_shared', 'single_player_shared', 'ui'}
PROFILE_BLOCK = 0x25C          # scnr Player Starting Profile, confirmed below
PROFILE_ELEM = 0x58


def _profile_block(m, reg):
    plug = reg.get('scnr')
    bf = (plug.find('Starting Health Damage', 'Player Starting Profile')
          or plug.find('Starting Health Modifier', 'Player Starting Profile'))
    if not bf:
        return None
    return bf['block_offsets'][-1], bf['block_sizes'][-1]


def _short(name):
    return str(name).rsplit('\\', 1)[-1] if name else None


def scan(path, game, reg):
    m = HP.open_map(path, game)
    scnr = HP._scnr_base(m)
    boff, esize = _profile_block(m, reg)
    n = max(0, m.i32(scnr + boff))
    base = HP._block_base(m, scnr + boff)
    rows = []
    for i in range(n) if base else []:
        e = base + i * esize
        nm = m._cstr(e)
        prim = _short(HP._tag_name_by_id(m, m.u32(e + 0x28 + 0xC)))
        sec = _short(HP._tag_name_by_id(m, m.u32(e + 0x3C + 0xC)))
        pl, pt = struct.unpack_from('<hh', m.data, e + 0x38)
        sl, st = struct.unpack_from('<hh', m.data, e + 0x4C)
        rows.append((i, nm, prim, pl, pt, sec, sl, st))
    # every weapon the level stocks in its palette, for context
    lay = HP._MAP_WEAPONS[game]
    poff, pes = lay['palette']
    pn = max(0, m.i32(scnr + poff))
    pbase = HP._block_base(m, scnr + poff)
    pal = [_short(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)))
           for i in range(pn)] if pbase else []
    return rows, [p for p in pal if p]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default='Halo 3: ODST', choices=sorted(ROOTS))
    ap.add_argument('--verbose', action='store_true', help='every row, not just distinct')
    ap.add_argument('--bak', action='store_true',
                    help='read the .map.bak baselines -- the live .map files are patched')
    a = ap.parse_args(argv)

    reg = HP.PluginRegistry(
        r"F:\SteamLibrary\steamapps\common\HCEEK"
        r"\Assembly-1-2023-11-29-1702446457\Plugins",
        ['ODSTMCC', 'ODST'] if a.game == 'Halo 3: ODST' else ['Halo3MCC', 'Halo3'])

    root = ROOTS[a.game]
    for f in sorted(os.listdir(root)):
        if not f.endswith('.map') or f[:-4].lower() in SKIP:
            continue
        path = os.path.join(root, f)
        if a.bak:
            path = V.pristine_source(a.game, path)
        try:
            rows, pal = scan(path, a.game, reg)
        except Exception as ex:
            print('%-12s  !! %s' % (f[:-4], ex))
            continue
        names = sorted({r[1] for r in rows})
        prims = sorted({r[2] for r in rows if r[2]})
        secs = sorted({r[3 + 2] for r in rows if r[5]})
        print('%-10s %2d profiles  names=%-34s' % (f[:-4], len(rows), ','.join(names)[:34]))
        print('%12s primary=%s' % ('', ', '.join(prims) or '(none)'))
        print('%12s secondary=%s' % ('', ', '.join(secs) or '(none)'))
        print('%12s palette(%d)=%s' % ('', len(pal), ', '.join(sorted(set(pal)))))
        if a.verbose:
            for r in rows:
                print('%14s[%2d] %-8s %-18s %2d/%-3d  %-18s %2d/%d'
                      % ('', r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
        print('')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
