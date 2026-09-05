"""Read the Squads block out of a Halo 3 / ODST scenario, with each squad's
characters resolved to real `char` tag paths.

Written to answer one question -- WHICH engineer variant is the one you escort on
Data Hive and Coastal Highway -- but the squad list is the map's own cast list, so it
answers "which tag is this named character" for anything.

Layout (ODSTMCC/Halo3MCC scnr plugin, both identical here):

    scnr + SQUADS_AT           Squads, element 0x6C
        +0x00  Name                    ascii[0x20]
        +0x24  Team                    enum16 (1 Player, 2 Human, 3 Covenant, ...)
        +0x3C  Single Locations        block, element 0x90
                   +0x32  Character Type Index   int16 -> Character Palette
        +0x54  Designer Cells          block, element 0x84
                   +0x14  Character Type         block, element 0x10
                              +0xC  Character Type Index  int16
        +0x60  Templated Cells         block, element 0x84   (same shape)
    scnr + PALETTE_AT          Character Palette, element 0x10 (tagRef)
                   +0xC   datum; low 16 bits = tag row

A tag block is [count:i32][ptr:u32]; halo3_map resolves the pointer, which is what
_block_base does here via the same helper the patcher uses.

Usage:
    python sprint_toolkit/odst_squads.py l200 l300
    python sprint_toolkit/odst_squads.py --game "Halo 3" 030_outskirts
    python sprint_toolkit/odst_squads.py l200 --grep engineer
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.dirname(_HERE)
sys.path.insert(0, _TOOL)

import halo_patch as hp                                          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_vault as V                                            # noqa: E402

# Both games' scnr plugins declare these at the same offsets; kept per game anyway
# because every other ODST scenario block DID shift relative to Halo 3.
LAYOUT = {
    'Halo 3':       {'squads': 0x3B8, 'palette': 0x3E8},
    'Halo 3: ODST': {'squads': 0x3B8, 'palette': 0x3E8},
}
SQUAD_ELEM = 0x6C
SINGLE_LOC = (0x3C, 0x90, 0x32)     # block offset, element size, char-index offset
CELLS = ((0x54, 0x84), (0x60, 0x84))   # Designer Cells, Templated Cells
CELL_CHAR = (0x14, 0x10, 0xC)       # Character Type sub-block, element, index offset
PALETTE_ELEM = 0x10
PALETTE_DATUM = 0xC

TEAMS = {0: 'default', 1: 'player', 2: 'human', 3: 'covenant', 4: 'flood',
         5: 'sentinel', 6: 'heretic', 7: 'prophet', 8: 'guilty'}

MAP_FOLDER = {'Halo 3': 'halo3/maps', 'Halo 3: ODST': 'halo3odst/maps'}
SUBDIRS = {'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST']}


def _settings():
    try:
        with open(os.path.join(_TOOL, 'settings.json'), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _ascii(m, off, size):
    raw = m.data[off:off + size]
    return raw.split(b'\x00', 1)[0].decode('latin1', 'replace')


def _block(m, at):
    """(count, base) of the tag block whose [count][ptr] pair sits at `at`."""
    n = m.i32(at)
    if n <= 0:
        return 0, None
    return n, hp._block_base(m, at)


def read_squads(m, game):
    """[{name, team, characters: [char tag path, ...]}] for every squad on the map."""
    lay = LAYOUT.get(str(game).strip())
    scnr = hp._scnr_base(m)
    if not lay or scnr is None:
        return []

    # Character Palette -> tag paths, by palette index.
    pal = []
    pn, pbase = _block(m, scnr + lay['palette'])
    for i in range(pn) if pbase else []:
        row = m.u32(pbase + i * PALETTE_ELEM + PALETTE_DATUM) & 0xFFFF
        t = m.tag(row) if hasattr(m, 'tag') else None
        pal.append((t or {}).get('name') or '?row %d' % row)

    def resolve(idx):
        return pal[idx] if 0 <= idx < len(pal) else None

    out = []
    sn, sbase = _block(m, scnr + lay['squads'])
    for i in range(sn) if sbase else []:
        e = sbase + i * SQUAD_ELEM
        chars = []

        loff, lelem, lchar = SINGLE_LOC
        ln, lbase = _block(m, e + loff)
        for j in range(ln) if lbase else []:
            c = resolve(m.i16(lbase + j * lelem + lchar))
            if c and c not in chars:
                chars.append(c)

        for coff, celem in CELLS:
            cn, cbase = _block(m, e + coff)
            for j in range(cn) if cbase else []:
                toff, telem, tidx = CELL_CHAR
                tn, tbase = _block(m, cbase + j * celem + toff)
                for k in range(tn) if tbase else []:
                    c = resolve(m.i16(tbase + k * telem + tidx))
                    if c and c not in chars:
                        chars.append(c)

        out.append({'name': _ascii(m, e, 0x20),
                    'team': TEAMS.get(m.i16(e + 0x24), '?'),
                    'characters': chars})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('maps', nargs='+', help='mission ids or map basenames')
    ap.add_argument('--game', default='Halo 3: ODST')
    ap.add_argument('--grep', help='only squads whose name or characters match this')
    ap.add_argument('--by-char', action='store_true',
                    help='invert: list each character tag and the squads using it')
    args = ap.parse_args()

    cfg = _settings()
    root = cfg.get('mcc_root') or r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
    folder = MAP_FOLDER.get(args.game, '')
    for mid in args.maps:
        base = os.path.join(root, *folder.split('/'), mid + '.map')
        path = V.pristine_source(args.game, base)
        if not os.path.exists(path):
            print('%s: no such map (%s)' % (mid, path)); continue
        m = hp.open_map(path, args.game)
        squads = read_squads(m, args.game)
        print('=' * 78)
        print('%s  (%s)  %d squads' % (mid, os.path.basename(path), len(squads)))
        q = (args.grep or '').lower()
        if args.by_char:
            by = {}
            for s in squads:
                for c in s['characters']:
                    by.setdefault(c, []).append('%s[%s]' % (s['name'], s['team']))
            for c in sorted(by):
                if q and q not in c.lower() and not any(q in x.lower() for x in by[c]):
                    continue
                print('  %s' % c)
                print('      %s' % ', '.join(sorted(by[c])))
        else:
            for s in squads:
                hay = (s['name'] + ' ' + ' '.join(s['characters'])).lower()
                if q and q not in hay:
                    continue
                print('  %-40s [%-9s] %s'
                      % (s['name'], s['team'],
                         ', '.join(c.rsplit(chr(92), 1)[-1] for c in s['characters']) or '-'))


if __name__ == '__main__':
    main()
