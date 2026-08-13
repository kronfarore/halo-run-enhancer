r"""Archive the pristine campaign maps out of the game folders, per game.

Why: a modded install accumulates copies. One ODST level was costing ~1.9 GB across
five files, and the maps themselves are 3.4 GB per game before any rebuild. The vault
consolidates the ORIGINALS into one archive per game and gets them out of the loop, so
each map folder holds only what the game and the patcher actually need.

Compression is worth measuring rather than assuming, because it varies enormously:

    Halo 1 vanilla (b30)      196 MB   ->  21%   (stored uncompressed in the map)
    ODST vanilla (sc150)      225 MB   ->  89%   (raw pages already deflated)
    ODST rebuilt (sc150)      407 MB   ->  97%

So H1 deflates ~5x and H3/ODST barely move. `--pack` picks per game accordingly: the
win for H3/ODST is consolidation, not size.

THE SAFETY PROBLEM, and why nothing is packed without being asked twice.
A modified map archived as if it were pristine is the one unrecoverable mistake here --
the archive would then be the "original" everything else restores from. This tool
cannot tell a modified map from a stock one by inspection alone, so it does not try:

  * `--survey` is READ-ONLY and reports everything that bears on the question: size,
    mtime, whether a `.shipped` original was preserved, and whether the map looks
    REBUILT (an Editing Kit build has an EMPTY `play` tag, which is a structural
    marker, not a guess).
  * `--pack` takes its bytes from `<map>.shipped` by default -- that file is the
    preserved original by construction. A map with no `.shipped` is SKIPPED unless
    `--from map` is given explicitly, and then only with `--yes`.

The map list comes from halo.json `Missions[game]`, so the vault can never drift from
what the patcher actually touches.

    python map_vault.py --survey "Halo 3: ODST"
    python map_vault.py --pack "Halo 1" --yes
    python map_vault.py --verify "Halo 1"
    python map_vault.py --unpack "Halo 1" [--only b30] [--to-shipped]
"""
import argparse
import hashlib
import json
import os
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402

ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection")
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.path.join(TOOL, 'vault')
HALO_JSON = os.path.join(TOOL, 'halo.json')

# Same mapping the enhancer uses (CONFIG['map_game_folder']).
MAP_FOLDER = {'Halo 1': 'halo1/maps',
              'Halo 2': 'halo2/h2_maps_win64_dx11',
              'Halo 3': 'halo3/maps',
              'Halo 3: ODST': 'halo3odst/maps'}
# Deflate only where it pays. Measured on this install; see the module docstring.
COMPRESS = {'Halo 1': zipfile.ZIP_DEFLATED, 'Halo 2': zipfile.ZIP_DEFLATED,
            'Halo 3': zipfile.ZIP_STORED, 'Halo 3: ODST': zipfile.ZIP_STORED}
MANIFEST = '_manifest.json'


def maps_for(game):
    """Campaign map basenames from halo.json -- the patcher's own list."""
    with open(HALO_JSON, encoding='utf-8') as f:
        missions = json.load(f)['Missions']
    if game not in missions:
        raise SystemExit('no Missions entry for %r (have: %s)'
                         % (game, ', '.join(missions)))
    return sorted(missions[game])


def map_dir(game):
    return os.path.join(ROOT, MAP_FOLDER[game].replace('/', os.sep))


def sha256(path, cap=None):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
            if cap and f.tell() >= cap:
                break
    return h.hexdigest()


def looks_rebuilt(path, game):
    """True if this is an Editing Kit build rather than a shipped map.

    A standalone build inlines what a shipped map reaches for in shared.map /
    campaign.map, and leaves the `play` tag EMPTY. That is a structural fact about the
    file, so it separates rebuilds from originals without guessing. Only meaningful
    for the third-generation games; returns None when it cannot tell.
    """
    if game not in ('Halo 3', 'Halo 3: ODST'):
        return None
    try:
        m = HP.open_map(path, game)
        play = next((t for t in m.tags if t.get('class') == 'play'), None)
        return play is not None and not play.get('base')
    except Exception:
        return None


def survey(game, do_hash=False):
    """Read-only. Report what is in the map folder and how confident we can be."""
    d = map_dir(game)
    print('%s  ->  %s' % (game, d))
    if not os.path.isdir(d):
        print('  (folder not found)')
        return []
    rows = []
    print('  %-10s %10s  %-16s %-9s %-8s %s'
          % ('map', 'MB', 'modified', 'shipped?', 'rebuilt?', 'verdict'))
    for name in maps_for(game):
        p = os.path.join(d, name + '.map')
        if not os.path.exists(p):
            print('  %-10s %10s  %s' % (name, '-', '(absent)'))
            continue
        size = os.path.getsize(p)
        mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))
        shipped = os.path.exists(p + '.shipped')
        rebuilt = looks_rebuilt(p, game)
        if shipped:
            verdict = 'PACK .shipped'
        elif rebuilt:
            verdict = 'REBUILT - no original kept'
        else:
            verdict = 'unverified - confirm before packing'
        print('  %-10s %10.1f  %-16s %-9s %-8s %s'
              % (name, size / 1048576.0, mtime, 'yes' if shipped else 'no',
                 {True: 'yes', False: 'no', None: '?'}[rebuilt], verdict))
        rows.append({'map': name, 'path': p, 'size': size, 'shipped': shipped,
                     'rebuilt': rebuilt,
                     'sha256': sha256(p) if do_hash else None})
    return rows


def pack(game, source='shipped', only=None, yes=False):
    d, out = map_dir(game), os.path.join(VAULT, game.replace(':', '').replace(' ', '_') + '.zip')
    os.makedirs(VAULT, exist_ok=True)
    names = [n for n in maps_for(game) if not only or n in only]
    picked, skipped = [], []
    for n in names:
        live = os.path.join(d, n + '.map')
        ship = live + '.shipped'
        if os.path.exists(ship):
            picked.append((n, ship, 'shipped'))
        elif source == 'map' and os.path.exists(live):
            picked.append((n, live, 'live map'))
        else:
            skipped.append(n)
    print('%s -> %s' % (game, out))
    for n, p, why in picked:
        print('  will pack %-10s from the %s (%.1f MB)' % (n, why, os.path.getsize(p) / 1048576.0))
    for n in skipped:
        print('  SKIP %-10s (no .shipped original; pass --from map --yes to trust the '
              'live file)' % n)
    if not picked:
        raise SystemExit('nothing to pack')
    if not yes:
        print('\n  dry run -- nothing written. Re-run with --yes.')
        return
    if any(why == 'live map' for _, _, why in picked):
        print('\n  NOTE: packing live maps as originals. If any of them is modified, '
              'the archive is wrong and there is no second copy to fall back on.')
    man = {'game': game, 'created': time.strftime('%Y-%m-%d %H:%M:%S'), 'entries': {}}
    comp = COMPRESS.get(game, zipfile.ZIP_STORED)
    with zipfile.ZipFile(out, 'w', compression=comp, allowZip64=True) as z:
        for n, p, why in picked:
            digest = sha256(p)
            man['entries'][n] = {'sha256': digest, 'size': os.path.getsize(p),
                                 'source': why}
            z.write(p, n + '.map')
            print('  packed %-10s %s' % (n, digest[:16]))
        z.writestr(MANIFEST, json.dumps(man, indent=2))
    print('  wrote %.1f MB (%s)' % (os.path.getsize(out) / 1048576.0,
                                    'deflated' if comp == zipfile.ZIP_DEFLATED else 'stored'))


def _open(game):
    out = os.path.join(VAULT, game.replace(':', '').replace(' ', '_') + '.zip')
    if not os.path.exists(out):
        raise SystemExit('no vault at %s' % out)
    return out


def verify(game):
    out = _open(game)
    with zipfile.ZipFile(out) as z:
        man = json.loads(z.read(MANIFEST))
        print('%s  created %s' % (out, man['created']))
        bad = 0
        for n, meta in sorted(man['entries'].items()):
            h = hashlib.sha256()
            with z.open(n + '.map') as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
            ok = h.hexdigest() == meta['sha256']
            bad += not ok
            print('  %-10s %s' % (n, 'ok' if ok else 'CORRUPT'))
        print('  %d entr(ies), %d corrupt' % (len(man['entries']), bad))
        return bad == 0


def unpack(game, only=None, to_shipped=False):
    out, d = _open(game), map_dir(game)
    with zipfile.ZipFile(out) as z:
        man = json.loads(z.read(MANIFEST))
        for n in sorted(man['entries']):
            if only and n not in only:
                continue
            dst = os.path.join(d, n + '.map' + ('.shipped' if to_shipped else ''))
            with z.open(n + '.map') as f, open(dst, 'wb') as g:
                while True:
                    b = f.read(1 << 20)
                    if not b:
                        break
                    g.write(b)
            print('  restored %s -> %s' % (n, os.path.basename(dst)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--survey', metavar='GAME')
    ap.add_argument('--pack', metavar='GAME')
    ap.add_argument('--verify', metavar='GAME')
    ap.add_argument('--unpack', metavar='GAME')
    ap.add_argument('--from', dest='source', default='shipped', choices=('shipped', 'map'),
                    help='where a pack takes its bytes; "map" trusts the live file')
    ap.add_argument('--only', help='comma list of map basenames')
    ap.add_argument('--to-shipped', action='store_true',
                    help='unpack to <map>.shipped instead of over the live map')
    ap.add_argument('--hash', action='store_true', help='survey also hashes each map')
    ap.add_argument('--yes', action='store_true', help='actually write the archive')
    a = ap.parse_args(argv)
    only = set(a.only.split(',')) if a.only else None
    if a.survey:
        survey(a.survey, a.hash)
    if a.pack:
        pack(a.pack, a.source, only, a.yes)
    if a.verify:
        verify(a.verify)
    if a.unpack:
        unpack(a.unpack, only, a.to_shipped)
    if not any((a.survey, a.pack, a.verify, a.unpack)):
        ap.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
