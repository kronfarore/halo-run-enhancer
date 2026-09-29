r"""How many ports there are to do, read off the weapon spreadsheet rather than guessed.

`Halo Weapons Spreadsheet (CE - Infinite).ods` is a weapon x game presence matrix, and
its answer is not in the text: the cells are almost all EMPTY and the state is the cell's
BACKGROUND COLOUR, keyed by a legend in the last column.

    #38761d present     #cc0000 absent      #93c47d MP only
    #351c75 unknown     #b45f06 unusable

A weapon can only be ported FROM somewhere, so the universe is the weapons that exist in
at least one of the six MCC games -- not the whole sheet, which also carries Halo 5 and
Infinite weapons that exist in no MCC kit at all and cannot be sourced.

"MP only" counts as HAS IT. If the tags are in the game, a campaign appearance is a
placement and a residency problem, not a port: no geometry, no shaders, no animations.
That is a different and much shorter job, and lumping the two together overstates the
work.

    python port_matrix.py             # the totals
    python port_matrix.py --full      # the whole matrix
    python port_matrix.py --game "Halo 3"      # what one game is missing
"""
import argparse
import os
import zipfile
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
SHEET = os.path.join(TOOL, 'Halo Weapons Spreadsheet (CE - Infinite).ods')

S = 'urn:oasis:names:tc:opendocument:xmlns:style:1.0'
T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
TX = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'

STATE = {'#38761d': 'present', '#cc0000': 'absent', '#93c47d': 'mp only',
         '#351c75': 'unknown', '#b45f06': 'unusable'}
GAMES = ['Halo: CE', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo: Reach', 'Halo 4']
#: the two states that mean "the game already has this weapon's tags"
HAS = ('present', 'mp only')


def _styles(z):
    out = {}
    for part in ('content.xml', 'styles.xml'):
        root = ET.fromstring(z.read(part))
        for st in root.iter('{%s}style' % S):
            name = st.get('{%s}name' % S)
            for pr in st.iter('{%s}table-cell-properties' % S):
                for k, v in pr.attrib.items():
                    if k.endswith('background-color'):
                        out[name] = v
    return out


def matrix(path=SHEET):
    """{weapon: {game: state}} straight out of the spreadsheet's cell colours."""
    z = zipfile.ZipFile(path)
    colors = _styles(z)
    rows = []
    for tr in ET.fromstring(z.read('content.xml')).iter('{%s}table-row' % T):
        cells = []
        for tc in tr.findall('{%s}table-cell' % T):
            rep = int(tc.get('{%s}number-columns-repeated' % T, 1))
            txt = ' '.join(''.join(p.itertext()) for p in tc.iter('{%s}p' % TX)).strip()
            # a repeat count of 1000 on the trailing blank columns is normal; cap it
            cells.extend([(txt, colors.get(tc.get('{%s}style-name' % T), ''))]
                         * min(rep, 14))
        rows.append(cells)
    out = {}
    for r in rows[1:]:
        if len(r) < 3 or not r[1][0] or r[1][0] == 'Key':
            continue
        st = {g: STATE.get(r[2 + i][1], '?')
              for i, g in enumerate(GAMES) if 2 + i < len(r)}
        if any(v != '?' for v in st.values()):
            out[r[1][0]] = st
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--game')
    a = ap.parse_args()
    if not os.path.exists(SHEET):
        raise SystemExit('no spreadsheet at %s' % SHEET)
    mat = matrix()
    source = [n for n, s in mat.items() if any(s.get(g) in HAS for g in GAMES)]
    nowhere = sorted(n for n in mat if n not in source)

    if a.full:
        w = max(len(n) for n in mat)
        print('%-*s %s' % (w, '', ' '.join('%-9s' % g[:9] for g in GAMES)))
        for n, s in mat.items():
            print('%-*s %s' % (w, n, ' '.join('%-9s' % s.get(g, '?')[:9] for g in GAMES)))
        print()

    if a.game:
        g = next((x for x in GAMES if x.lower() == a.game.lower()), None)
        if not g:
            raise SystemExit('unknown game %r -- one of %s' % (a.game, GAMES))
        gap = sorted(n for n in source if mat[n].get(g) not in HAS)
        print('%s is missing %d of the %d sourceable weapons:' % (g, len(gap), len(source)))
        for n in gap:
            froms = [x.replace('Halo: ', '').replace('Halo ', '')
                     for x in GAMES if mat[n].get(x) in HAS]
            print('   %-28s from %s' % (n, ', '.join(froms)))
        return

    print('%d weapons in the sheet' % len(mat))
    print('%d SOURCEABLE -- they exist in at least one MCC game' % len(source))
    print('%d exist in no MCC game and cannot be ported from anywhere:' % len(nowhere))
    print('   %s' % ', '.join(nowhere))
    print()
    print('%-14s %6s %6s' % ('game', 'has', 'GAP'))
    total = 0
    for g in GAMES:
        gap = sum(1 for n in source if mat[n].get(g) not in HAS)
        total += gap
        print('%-14s %6d %6d' % (g, len(source) - gap, gap))
    print('%-14s %6s %6d' % ('', '', total))
    print()
    print('%d port jobs to fill every gap in all six games.' % total)
    spread = {}
    for n in source:
        spread[sum(1 for g in GAMES if mat[n].get(g) in HAS)] = \
            spread.get(sum(1 for g in GAMES if mat[n].get(g) in HAS), 0) + 1
    print('\nhow many games each sourceable weapon is already in:')
    for k in sorted(spread):
        print('   in %d game(s): %2d weapon(s)%s'
              % (k, spread[k], '   <- one source, five targets each' if k == 1 else ''))


if __name__ == '__main__':
    main()
