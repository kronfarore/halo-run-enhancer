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
    halo2      U+E13D SAW, U+E13E Assault Rifle -- the eight English HUD fonts in
               halo2\h2_fonts (one font per FILE, no package: the _h2_* functions; the
               records carry their payloads; header +0x10 raised to the captured value)
               -- added 2026-10-21 by the H2 AR pilot; restoring stock gives the live
               fonts BYTE FOR BYTE. `--capture --game halo2` after a new H2 port glyph.

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
    python port_glyphs.py --check              validator: missing glyphs / capture not run
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


# --- HALO 2 (the AR pilot, 2026-10-21) --------------------------------------------------
# Halo 2 keeps one font per FILE in `halo2\h2_fonts\` (no package; h2_font.py decoded it):
#   0x200 header (+0x0C glyph count), 0x400 the character map -- one u32 per codepoint,
#   0x10000 of them, value = glyph index, the value that FILLS it = "nothing" (per font) --
#   0x40400 the glyph table, 16 bytes a glyph (u16 advance, size, w, h, x, y; u32 absolute
#   payload offset), then the payloads. A port adds a glyph the way h2_font_add.py does: a
#   record at the end of the table (every payload offset +16), its payload at the end of the
#   file, its codepoint's slot, the count + 1. Standard library only: a frozen enhancer needs
#   nothing new. The eight English fonts that draw HUD text carry the ports' pickup icons
#   (U+E13D the SAW, U+E13E the Assault Rifle ...; h2_port_glyph.py drew them).
H2_FONTS = ('conduit-9', 'conduit-12', 'conduit-13', 'fixedsys-9',
            'handel_gothic-11', 'handel_gothic-13', 'handel_gothic-24', 'MSLCD-14')
H2_STOCK = r'E:\HaloBackups\h2_fonts'
_H2_HEADER, _H2_CHARMAP, _H2_CODEPOINTS, _H2_RECORD = 0x200, 0x400, 0x10000, 16
_H2_GLYPHS = _H2_CHARMAP + _H2_CODEPOINTS * 4
#: header +0x10, u16: raised by `tool replace-font-char` for a big glyph (stock conduit-12 7592,
#: MSLCD-14 1480 -> 10029 in every font once the 160x62 port icons went in) -- most likely the
#: largest-glyph buffer the engine allocates. A restore raises it to the captured live value
_H2_BUFFER = _H2_HEADER + 0x10


def _h2_blank(d):
    counts = {}
    for cp in range(0, _H2_CODEPOINTS, 7):
        v = struct.unpack_from('<I', d, _H2_CHARMAP + cp * 4)[0]
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _h2_glyphs(d):
    """{codepoint: (record without its offset (12 bytes), payload)} of every mapped glyph."""
    none = _h2_blank(d)
    out = {}
    for cp in range(_H2_CODEPOINTS):
        i = struct.unpack_from('<I', d, _H2_CHARMAP + cp * 4)[0]
        if i == none:
            continue
        at = _H2_GLYPHS + i * _H2_RECORD
        rec = d[at:at + 12]
        size = struct.unpack_from('<H', d, at + 2)[0]
        off = struct.unpack_from('<I', d, at + 12)[0]
        out[cp] = (bytes(rec), bytes(d[off:off + size]))
    return out


def _h2_add(d, cp, rec12, pay):
    """`d` with `cp` mapped to a NEW glyph (h2_font_add.add's layout, the real payload)."""
    count = struct.unpack_from('<I', d, _H2_HEADER + 0x0C)[0]
    table_end = _H2_GLYPHS + count * _H2_RECORD
    if struct.unpack_from('<I', d, _H2_GLYPHS + 12)[0] != table_end:
        raise ValueError('the payloads do not start where the table ends')
    rec = bytearray(rec12)
    struct.pack_into('<H', rec, 2, len(pay))
    out = bytearray(d[:table_end]) + rec + struct.pack('<I', len(d) + _H2_RECORD) \
        + d[table_end:] + pay
    for i in range(count):
        at = _H2_GLYPHS + i * _H2_RECORD + 12
        struct.pack_into('<I', out, at, struct.unpack_from('<I', out, at)[0] + _H2_RECORD)
    struct.pack_into('<I', out, _H2_CHARMAP + cp * 4, count)
    struct.pack_into('<I', out, _H2_HEADER + 0x0C, count + 1)
    return bytes(out)


def _h2_ensure(mcc_root, write=True, backup_dir=None, data=None):
    data = data or load()
    spec = data.get('games', {}).get('halo2') or {}
    rows = []
    for name in H2_FONTS:
        want = spec.get(name) or []
        if not want:
            continue
        row = {'effect': 'port glyph', 'field': 'halo2 %s' % name}
        path = os.path.join(mcc_root, 'halo2', 'h2_fonts', name)
        if not os.path.exists(path):
            rows.append(dict(row, ok=True, skip=True, reason='font not installed'))
            continue
        try:
            d = open(path, 'rb').read()
            have = _h2_glyphs(d)
        except Exception as e:
            rows.append(dict(row, ok=False, reason='unreadable font: %s' % e))
            continue
        missing, clash = [], []
        for g in want:
            rec, pay = base64.b64decode(g['record']), base64.b64decode(g['payload'])
            got = have.get(g['cp'])
            if got is None:
                missing.append((g, rec, pay))
            elif (got[0][:2] + got[0][4:], got[1]) != (rec[:2] + rec[4:], pay):
                clash.append('U+%04X' % g['cp'])
        if clash:
            rows.append(dict(row, ok=False, reason='a different glyph already sits at %s; '
                             'left alone' % ', '.join(clash)))
            continue
        if not missing:
            rows.append(dict(row, ok=True, skip=True, reason='glyphs present'))
            continue
        labels = ', '.join('U+%04X %s' % (g['cp'], g.get('port', '')) for g, _r, _p in missing)
        try:
            out = d
            for g, rec, pay in missing:
                out = _h2_add(out, g['cp'], rec, pay)
            want_buf = (spec.get('_buffer') or {}).get(name)
            if want_buf and struct.unpack_from('<H', out, _H2_BUFFER)[0] < want_buf:
                out = bytearray(out)
                struct.pack_into('<H', out, _H2_BUFFER, want_buf)
                out = bytes(out)
            back = _h2_glyphs(out)
            ok = all(back.get(g['cp'], (b'', b''))[1] == pay for g, _r, pay in missing) and \
                all(back.get(c) == v for c, v in have.items())
        except Exception as e:
            rows.append(dict(row, ok=False, reason='could not add: %s' % e))
            continue
        if not ok:
            rows.append(dict(row, ok=False, reason='the rebuilt font failed its read-back; left alone'))
            continue
        if write:
            keep = (os.path.join(backup_dir, 'halo2', name) if backup_dir
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


def _h2_capture(mcc_root, port_names=None):
    """DEV: Halo 2's port glyphs = what the live fonts map beyond the stock backups (E:),
    in live glyph-index order. Proven: stock + the records gives the live font -- byte for
    byte, else the same glyph set with every payload equal."""
    spec, buf = {}, {}
    for name in H2_FONTS:
        live = open(os.path.join(mcc_root, 'halo2', 'h2_fonts', name), 'rb').read()
        buf[name] = struct.unpack_from('<H', live, _H2_BUFFER)[0]
        stock = open(os.path.join(H2_STOCK, name), 'rb').read()
        lg, sg = _h2_glyphs(live), _h2_glyphs(stock)
        if any(c in lg and lg[c] != sg[c] for c in sg):
            raise SystemExit('halo2 %s: a STOCK glyph differs from the backup' % name)
        none = _h2_blank(live)
        added = sorted((c for c in lg if c not in sg),
                       key=lambda c: struct.unpack_from('<I', live, _H2_CHARMAP + c * 4)[0])
        glyphs = [{'cp': c, 'port': (port_names or {}).get(c, ''),
                   'record': base64.b64encode(lg[c][0]).decode(),
                   'payload': base64.b64encode(lg[c][1]).decode()} for c in added]
        rebuilt = stock
        for c in added:
            rebuilt = _h2_add(rebuilt, c, lg[c][0], lg[c][1])
        if struct.unpack_from('<H', rebuilt, _H2_BUFFER)[0] < buf[name]:
            rebuilt = bytearray(rebuilt)
            struct.pack_into('<H', rebuilt, _H2_BUFFER, buf[name])
            rebuilt = bytes(rebuilt)
        same = _h2_glyphs(rebuilt) == lg and _h2_blank(rebuilt) == none
        print('%-10s %-26s %s  rebuilt from stock: %s%s' % (
            'halo2', name, ', '.join('U+%04X' % c for c in added) or '-',
            'same glyphs' if same else 'MISMATCH', ', byte for byte' if rebuilt == live else ''))
        if not same:
            raise SystemExit('capture refused: halo2 %s does not rebuild' % name)
        spec[name] = glyphs
    spec['_buffer'] = buf
    return spec


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
    if game == 'halo2':
        return _h2_ensure(mcc_root, write=write, backup_dir=backup_dir, data=data)
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


def problems(mcc_root, data=None):
    """Validator: what is wrong with the port glyphs on this machine, as messages.
      * every machine: a live package lacks a glyph port_glyphs.json carries (a Steam
        update / verify restored the stock file, or the patch never ran here);
      * the DEV machine (stock backups on E: present): a live package holds a port glyph
        the json lacks -- a new port's glyph that `--capture` was not run for."""
    data = data or load()
    out = []
    for r in _h2_ensure(mcc_root, write=False, data=data):
        if not r.get('ok'):
            out.append('glyph %s: %s' % (r['field'], r.get('reason')))
        elif not r.get('skip'):
            out.append('glyph %s: missing %s -- run `python port_glyphs.py --write` '
                       '(or patch)' % (r['field'], r['old'].replace('without ', '')))
    if os.path.isdir(H2_STOCK):
        known = {name: {g['cp'] for g in (data.get('games', {}).get('halo2') or {}).get(name, [])}
                 for name in H2_FONTS}
        for name in H2_FONTS:
            live_p = os.path.join(mcc_root, 'halo2', 'h2_fonts', name)
            stock_p = os.path.join(H2_STOCK, name)
            if not (os.path.exists(live_p) and os.path.exists(stock_p)):
                continue
            try:
                extra = sorted(set(_h2_glyphs(open(live_p, 'rb').read()))
                               - set(_h2_glyphs(open(stock_p, 'rb').read())) - known[name])
            except Exception:
                continue
            if extra:
                out.append('glyph halo2 %s: U+%s in the live font but not in port_glyphs.json '
                           '-- run `python port_glyphs.py --capture --game halo2` and commit the json'
                           % (name, ', U+'.join('%04X' % c for c in extra)))
    for game, (block, _hdr, names) in GAMES.items():
        for r in ensure(game, mcc_root, write=False, data=data):
            if not r.get('ok'):
                out.append('glyph %s: %s' % (r['field'], r.get('reason')))
            elif not r.get('skip'):
                out.append('glyph %s: missing %s -- run `python port_glyphs.py --write` '
                           '(or patch)' % (r['field'], r['old'].replace('without ', '')))
        stock_dir = STOCK.get(game)
        if not stock_dir or not os.path.isdir(stock_dir):
            continue
        spec = data.get('games', {}).get(game, {})
        for name in names:
            live_p = os.path.join(mcc_root, game, 'maps', 'fonts', name)
            stock_p = os.path.join(stock_dir, name)
            if not (os.path.exists(live_p) and os.path.exists(stock_p)):
                continue
            try:
                live = _present(open(live_p, 'rb').read(), block)
                stock = _present(open(stock_p, 'rb').read(), block)
            except (SystemExit, Exception):
                continue
            known = {(g['cp'], g['font']) for g in spec.get(name, [])}
            extra = sorted(set(live) - set(stock) - known)
            if extra:
                out.append('glyph %s %s: U+%s in the live package but not in port_glyphs.json '
                           '-- run `python port_glyphs.py --capture` and commit the json'
                           % (game, name, ', U+'.join('%04X' % c for c, _f in extra)))
    return out


def capture(mcc_root, games=None):
    """DEV: the port glyphs = what this machine's live packages hold beyond the stock
    backups. Also proves them: stock + records must give the live glyph set and headers.
    `games`: capture only those (the others kept as the json has them)."""
    try:
        out = load()
    except Exception:
        out = {'version': 1, 'games': {}}
    out.setdefault('games', {})
    if games is None or 'halo2' in games:
        names = {}
        try:
            sys.path.insert(0, os.path.join(HERE, 'sprint_toolkit'))
            import ports_h2
            names = {p['reservations']['glyph']: p['name'] for _k, p in ports_h2.all_ports()
                     if (p.get('reservations') or {}).get('glyph')}
        except Exception:
            pass
        out['games']['halo2'] = _h2_capture(mcc_root, names)
    for game, (block, hdr, names) in GAMES.items():
        if games is not None and game not in games:
            continue
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
    ap.add_argument('--game', choices=sorted(GAMES) + ['halo2'])
    ap.add_argument('--mcc', default=os.path.dirname(HERE), help='MCC install folder')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--backup-dir')
    ap.add_argument('--capture', action='store_true')
    ap.add_argument('--check', action='store_true', help='validator: list problems, exit 1 if any')
    a = ap.parse_args()
    if a.capture:
        capture(a.mcc, [a.game] if a.game else None)
        return
    if a.check:
        found = problems(a.mcc)
        for pr in found:
            print(' ', pr)
        print('%d glyph problem(s)' % len(found))
        sys.exit(1 if found else 0)
    for game in ([a.game] if a.game else sorted(GAMES) + ['halo2']):
        for r in ensure(game, a.mcc, write=a.write, backup_dir=a.backup_dir):
            state = 'skip' if r.get('skip') else ('ok' if r['ok'] else 'FAIL')
            print('%-5s %-36s %s' % (state, r['field'], r.get('reason') or
                                     '%s -> %s' % (r.get('old'), r.get('new'))))
    if not a.write:
        print('(report only -- pass --write to add missing glyphs)')


if __name__ == '__main__':
    main()
