r"""Put the weapon ports' pickup/HUD glyphs into MCC's LIVE icon font packages -- on any
machine.

WHY: Halo 3, ODST, Reach and Halo 4 draw their weapon pictograms from loose files beside
the maps, `<game>\maps\fonts\font_package_icon[_x2|_x3|_x4].bin`. A ported weapon's lines
carry the port's own private-use character, so the packages must hold its glyph. A map
rebuild never touches them -- but a Steam update or "verify" restores the stock files,
and a co-op partner's install never had the glyphs. This puts them back.

WHAT IT CARRIES: `port_glyphs.json`, beside this file -- the finished glyph RECORDS
(already encoded), one per package, captured from the packages the port tools wrote and
proven in game. No kit, Blender, mesh or source art is needed at run time; only the
standard library and h3_font_repack.py (sprint_toolkit), which rebuilds a package around
added glyphs and rewrites its block index.

    halo3      U+E06A font 2   SAW            x1 x2 x3
    halo3odst  U+E04A font 3   SAW            x1 x2 x3
    haloreach  U+E052 font 3   SAW            x1 x2 x3
    halo4      U+E1F6 font 2   Focus Rifle    x1 x2 x3 x4

SAFETY: a package is only written when every glyph is missing or identical; a different
glyph at a port's code point is reported and left alone. Every rebuilt package must pass
the index check and read back with the added records before it replaces the live file
(written to a temp file, then swapped in). The original is copied first (backup_dir, or
`<name>.port_glyphs_stock` beside it).

Measured 2026-10-03: from the stock packages, adding the stored records reproduces the
live Halo 4 packages BYTE FOR BYTE; for Halo 3 / ODST / Reach (whose glyphs were placed
by the older tools) the same glyph set and font headers, the blocks ordered differently
-- the repacked layout is the one proven in game by the growth test.

FOR THE ENHANCER (patch time, one call per game):
    import port_glyphs
    rows = port_glyphs.ensure('halo4', mcc_root())       # rows like the patcher's
A frozen build needs, in halo_enhancer.spec: pathex=['sprint_toolkit'],
hiddenimports=['h3_font_repack', 'port_glyphs'], datas += [('port_glyphs.json', '.')].

COMMAND LINE (cmd.exe):
    python port_glyphs.py                      report every game
    python port_glyphs.py --write              add the missing glyphs
    python port_glyphs.py --game halo4 --write
    python port_glyphs.py --capture            DEV: re-read the glyphs from this machine's
                                               live packages against the stock backups on E:
"""
import argparse
import base64
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(HERE, 'sprint_toolkit'), getattr(sys, '_MEIPASS', '')):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)
import h3_font_repack as fr                                       # noqa: E402

DATA = 'port_glyphs.json'
#: per game: block size, glyph record header size, packages
GAMES = {
    'halo3': (0xC000, 16, ('font_package_icon.bin', 'font_package_icon_x2.bin',
                           'font_package_icon_x3.bin')),
    'halo3odst': (0xC000, 16, ('font_package_icon.bin', 'font_package_icon_x2.bin',
                               'font_package_icon_x3.bin')),
    'haloreach': (0xC000, 16, ('font_package_icon.bin', 'font_package_icon_x2.bin',
                               'font_package_icon_x3.bin')),
    'halo4': (0x10000, 12, ('font_package_icon.bin', 'font_package_icon_x2.bin',
                            'font_package_icon_x3.bin', 'font_package_icon_x4.bin')),
}
#: DEV only (--capture): the stock packages backed up before any port glyph went in
STOCK = {'halo3': r'E:\HaloBackups\h3_live_fonts', 'halo3odst': r'E:\HaloBackups\odst_live_fonts',
         'haloreach': r'E:\HaloBackups\reach_live_fonts', 'halo4': r'E:\HaloBackups\h4_live_fonts'}
PORT_NAMES = {'halo3': 'SAW', 'halo3odst': 'SAW', 'haloreach': 'SAW', 'halo4': 'Focus Rifle'}


def _data_path():
    for d in (HERE, getattr(sys, '_MEIPASS', '')):
        p = os.path.join(d, DATA)
        if d and os.path.exists(p):
            return p
    return os.path.join(HERE, DATA)


def load():
    with open(_data_path(), encoding='utf-8') as f:
        return json.load(f)


def _payload(rec, hdr):
    """(payload, (w, h)) of a glyph record: Halo 3-family header u32 advance, u32 size,
    u16 w, u16 h, ...; Halo 4's u16 advance, u16 size, u16 w, u16 h, ..."""
    if hdr == 16:
        n = struct.unpack_from('<I', rec, 4)[0]
        w, h = struct.unpack_from('<HH', rec, 8)
    else:
        n, w, h = struct.unpack_from('<HHH', rec, 2)
    return rec[hdr:hdr + n], (w, h)


def _with_block(block, fn, *a):
    """h3_font_repack works on a module-wide block size: set it for one call."""
    old = fr.BLOCK
    fr.BLOCK = block
    try:
        return fn(*a)
    finally:
        fr.BLOCK = old


def _add(d, glyphs, block, hdr):
    def go():
        out = d
        for g in glyphs:
            pay, box = _payload(g['rec'], hdr)
            out = fr.repack(out, add=[(g['cp'], g['font'], g['rec'])])
            out = fr.font_header_add(out, g['cp'], g['font'], pay, box)
        ok = fr.check_index(out)[0]
        got = {(c, f): r for c, f, r, _s in fr.entries(out)[1]}
        for g in glyphs:
            r = got.get((g['cp'], g['font']))
            if r is None or r[:len(g['rec'])] != g['rec']:
                ok = False
        return out, ok
    return _with_block(block, go)


def _present(d, block):
    return _with_block(block, lambda: {(c, f): r for c, f, r, _s in fr.entries(d)[1]})


def ensure(game, mcc_root, write=True, backup_dir=None, data=None):
    """Make `game`'s live icon packages carry every port glyph. Returns patcher-style rows
    ({'effect', 'field', 'ok', 'skip', 'old', 'new', 'reason'}); never raises for a bad
    package -- it reports it and leaves the file alone."""
    data = data or load()
    if game not in GAMES or game not in data.get('games', {}):
        return []
    block, hdr, names = GAMES[game]
    spec = data['games'][game]
    rows = []
    for name in names:
        row = {'effect': 'port glyph', 'field': '%s %s' % (game, name)}
        want = [dict(g, rec=base64.b64decode(g['record'])) for g in spec.get(name, [])]
        if not want:
            continue
        path = os.path.join(mcc_root, game, 'maps', 'fonts', name)
        if not os.path.exists(path):
            rows.append(dict(row, ok=True, skip=True, reason='package not installed'))
            continue
        try:
            d = open(path, 'rb').read()
            have = _present(d, block)
        except (SystemExit, Exception) as e:
            rows.append(dict(row, ok=False, reason='unreadable package: %s' % e))
            continue
        missing, clash = [], []
        for g in want:
            r = have.get((g['cp'], g['font']))
            if r is None:
                missing.append(g)
            elif r[:len(g['rec'])] != g['rec']:
                clash.append('U+%04X' % g['cp'])
        if clash:
            rows.append(dict(row, ok=False, reason='a different glyph already sits at %s; '
                             'left alone' % ', '.join(clash)))
            continue
        if not missing:
            rows.append(dict(row, ok=True, skip=True, reason='glyphs present'))
            continue
        labels = ', '.join('U+%04X %s' % (g['cp'], g.get('port', '')) for g in missing)
        try:
            out, ok = _add(d, missing, block, hdr)
        except (SystemExit, Exception) as e:
            rows.append(dict(row, ok=False, reason='could not rebuild: %s' % e))
            continue
        if not ok:
            rows.append(dict(row, ok=False, reason='rebuilt package failed its check; left alone'))
            continue
        if write:
            keep = (os.path.join(backup_dir, game, name) if backup_dir
                    else path + '.port_glyphs_stock')
            if not os.path.exists(keep):
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copyfile(path, keep)
            tmp = path + '.port_glyphs_tmp'
            with open(tmp, 'wb') as f:
                f.write(out)
            os.replace(tmp, path)
        rows.append(dict(row, ok=True, old='without %s' % labels,
                         new='%s added%s' % (labels, '' if write else ' (dry run)')))
    return rows


def capture(mcc_root):
    """DEV: the port glyphs = what this machine's live packages hold beyond the stock
    backups. Also proves them: stock + records must give the live glyph set and headers."""
    out = {'version': 1, 'games': {}}
    for game, (block, hdr, names) in GAMES.items():
        spec = {}
        for name in names:
            live = open(os.path.join(mcc_root, game, 'maps', 'fonts', name), 'rb').read()
            stock = open(os.path.join(STOCK[game], name), 'rb').read()
            le, se = _present(live, block), _present(stock, block)
            if any(k in le and le[k] != se[k] for k in se):
                raise SystemExit('%s %s: a STOCK glyph differs from the backup' % (game, name))
            added = sorted(set(le) - set(se))
            glyphs = [{'cp': c, 'font': f, 'port': PORT_NAMES[game],
                       'record': base64.b64encode(le[(c, f)]).decode()} for c, f in added]
            rebuilt, ok = _add(stock, [dict(g, rec=le[(g['cp'], g['font'])]) for g in glyphs],
                               block, hdr)
            same = (_present(rebuilt, block) == le and
                    _with_block(block, fr.index_at, rebuilt) == _with_block(block, fr.index_at, live)
                    and rebuilt[:_with_block(block, fr.index_at, live)]
                    == live[:_with_block(block, fr.index_at, live)])
            print('%-10s %-26s %s  rebuilt from stock: %s%s' % (
                game, name, ', '.join('U+%04X f%d' % (g['cp'], g['font']) for g in glyphs) or '-',
                'same glyphs + headers' if same and ok else 'MISMATCH',
                ', byte for byte' if rebuilt == live else ''))
            if not (same and ok):
                raise SystemExit('capture refused: %s %s does not rebuild' % (game, name))
            spec[name] = glyphs
        out['games'][game] = spec
    with open(os.path.join(HERE, DATA), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    print('wrote', os.path.join(HERE, DATA))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', choices=sorted(GAMES))
    ap.add_argument('--mcc', default=os.path.dirname(HERE), help='MCC install folder')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--backup-dir')
    ap.add_argument('--capture', action='store_true')
    a = ap.parse_args()
    if a.capture:
        capture(a.mcc)
        return
    for game in ([a.game] if a.game else sorted(GAMES)):
        for r in ensure(game, a.mcc, write=a.write, backup_dir=a.backup_dir):
            state = 'skip' if r.get('skip') else ('ok' if r['ok'] else 'FAIL')
            print('%-5s %-36s %s' % (state, r['field'], r.get('reason') or
                                     '%s -> %s' % (r.get('old'), r.get('new'))))
    if not a.write:
        print('(report only -- pass --write to add missing glyphs)')


if __name__ == '__main__':
    main()
