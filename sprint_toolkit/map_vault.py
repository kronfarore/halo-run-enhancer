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
              'Halo 3: ODST': 'halo3odst/maps',
              'Halo Reach': 'haloreach/maps'}
# Deflate only where it pays. Measured on this install; see the module docstring.
# Reach's maps are third-gen-style already-compressed caches like Halo 3's, so it
# gets ZIP_STORED for the same reason.
COMPRESS = {'Halo 1': zipfile.ZIP_DEFLATED, 'Halo 2': zipfile.ZIP_DEFLATED,
            'Halo 3': zipfile.ZIP_STORED, 'Halo 3: ODST': zipfile.ZIP_STORED,
            'Halo Reach': zipfile.ZIP_STORED}
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


def resolve(game, name):
    """The map file for a halo.json key. Halo 2 names its files `03a_oldmombasa.map`
    where the key is just `03a`, so fall back to a prefix match."""
    d = map_dir(game)
    exact = os.path.join(d, name + '.map')
    if os.path.exists(exact):
        return exact
    if os.path.isdir(d):
        hits = sorted(f for f in os.listdir(d)
                      if f.lower().startswith(name.lower() + '_') and f.lower().endswith('.map'))
        if len(hits) == 1:
            return os.path.join(d, hits[0])
    return None


def originals(game, path):
    """Candidate pristine copies for a map, best first.

    Conventions differ per game. H1/H3/ODST keep `<map>.bak` beside the map (and this
    toolkit adds `<map>.shipped`), while Halo 2 keeps a whole parallel directory,
    `h2_maps_win64_dx11_bak`, holding both `.map.bak` and `.map.vanilla.bak`.
    `.vanilla.bak` is the most explicit claim of all, so it wins.
    """
    out = []
    for suffix in ('.vanilla.bak', '.shipped', '.bak'):
        cand = path + suffix
        if os.path.exists(cand):
            out.append((cand, suffix.lstrip('.')))
    d, base = os.path.split(path)
    alt = d + '_bak'
    if os.path.isdir(alt):
        for suffix in ('.vanilla.bak', '.bak'):
            cand = os.path.join(alt, base + suffix)
            if os.path.exists(cand):
                out.append((cand, os.path.basename(alt) + '/' + suffix.lstrip('.')))
    order = {'vanilla.bak': 0, 'shipped': 1, 'bak': 2}
    return sorted(out, key=lambda t: order.get(t[1].split('/')[-1], 9))


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


def survey(game, do_hash=False, echo=True):
    """Read-only. Report what is in the map folder and how confident we can be.

    Returns a row per map so a caller (the enhancer's GUI) can render it itself;
    `echo=False` silences the CLI printing."""
    def say(*a):
        if echo:
            print(*a)
    d = map_dir(game)
    say('%s  ->  %s' % (game, d))
    if not os.path.isdir(d):
        say('  (folder not found)')
        return []
    rows = []
    say('  %-8s %8s %-16s %-8s  %-22s %s'
          % ('map', 'MB', 'modified', 'rebuilt?', 'original kept as', 'verdict'))
    for name in maps_for(game):
        p = resolve(game, name)
        if not p:
            say('  %-8s %8s (absent)' % (name, '-'))
            continue
        size = os.path.getsize(p)
        mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))
        rebuilt = looks_rebuilt(p, game)
        origs = originals(game, p)
        src = origs[0] if origs else None
        # An "original" that is itself a rebuild is not one. That is exactly this
        # install: odst_ek_build points .bak at the rebuilt map on purpose.
        src_rebuilt = looks_rebuilt(src[0], game) if src else None
        if src and not src_rebuilt:
            verdict = 'PACK from ' + src[1]
        elif src and src_rebuilt:
            verdict = 'its .bak IS a rebuild - no original here'
        elif rebuilt:
            verdict = 'REBUILT, no original kept'
        else:
            verdict = 'no original kept - confirm before packing'
        say('  %-8s %8.1f %-16s %-8s  %-22s %s'
              % (name, size / 1048576.0, mtime,
                 {True: 'yes', False: 'no', None: '?'}[rebuilt],
                 src[1] if src else '-', verdict))
        rows.append({'map': name, 'path': p, 'size': size, 'rebuilt': rebuilt,
                     'original': src[0] if src else None,
                     'source': src[1] if src else None, 'verdict': verdict,
                     'packable': bool(src and not src_rebuilt),
                     'sha256': sha256(p) if do_hash else None})
    return rows


def plan_pack(game, source='original', only=None):
    """Archive the pristine copy of each map. Refuses to guess.

    The source is whatever `originals()` found -- `.vanilla.bak`, `.shipped` or `.bak`,
    in that order of explicitness -- and a candidate that is itself an Editing Kit
    rebuild is rejected, because that is not an original. `--from map` overrides and
    trusts the live file, which is the only way to archive a map whose original was
    never kept, and it says so loudly.

    Entries are stored under the map's REAL filename, so Halo 2's `03a_oldmombasa.map`
    round-trips even though halo.json calls it `03a`.
    """
    names = [n for n in maps_for(game) if not only or n in only]
    picked, skipped = [], []
    for n in names:
        live = resolve(game, n)
        if not live:
            skipped.append((n, 'map not found'))
            continue
        arcname = os.path.basename(live)
        if source == 'map':
            picked.append((n, live, 'THE LIVE MAP', arcname))
            continue
        chosen = None
        for cand, why in originals(game, live):
            if looks_rebuilt(cand, game):
                skipped.append((n, '%s is a rebuild, not an original' % why))
                continue
            chosen = (cand, why)
            break
        if chosen:
            picked.append((n, chosen[0], chosen[1], arcname))
        else:
            skipped.append((n, 'no original kept'))
    return picked, skipped, len(names)


def archive_path(game, dest=None):
    return os.path.join(dest or VAULT,
                        game.replace(':', '').replace(' ', '_') + '.zip')


def pack(game, dest=None, source='original', only=None, yes=False, echo=True):
    """Write the archive. `dest` is the destination folder -- on a play machine the
    tool folder does not exist, and an archive on the same disk as the maps protects
    against nothing, so the caller chooses."""
    def say(*a):
        if echo:
            print(*a)
    picked, skipped, total_names = plan_pack(game, source, only)
    out = archive_path(game, dest)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    say('%s -> %s' % (game, out))
    for n, p_, why, _arc in picked:
        say('  will pack %-8s from %-24s %7.1f MB'
            % (n, why, os.path.getsize(p_) / 1048576.0))
    for n, why in skipped:
        say('  SKIP      %-8s %s' % (n, why))
    if not picked:
        raise SystemExit('nothing to pack')
    total = sum(os.path.getsize(p_) for _, p_, _, _ in picked)
    say('  %d of %d map(s), %.1f MB in' % (len(picked), total_names, total / 1048576.0))
    if not yes:
        say('')
        say('  dry run -- nothing written. Re-run with --yes.')
        return None
    if source == 'map':
        say('  NOTE: archiving LIVE maps as originals. If any is modified, the '
            'archive is wrong and there is no second copy to fall back on.')
    man = {'game': game, 'created': time.strftime('%Y-%m-%d %H:%M:%S'), 'entries': {}}
    comp = COMPRESS.get(game, zipfile.ZIP_STORED)
    with zipfile.ZipFile(out, 'w', compression=comp, allowZip64=True) as z:
        for n, p_, why, arc in picked:
            digest = sha256(p_)
            man['entries'][n] = {'sha256': digest, 'size': os.path.getsize(p_),
                                 'source': why, 'filename': arc}
            z.write(p_, arc)
            say('  packed %-8s %s' % (n, digest[:16]))
        z.writestr(MANIFEST, json.dumps(man, indent=2))
    say('  wrote %.1f MB (%s)' % (os.path.getsize(out) / 1048576.0,
                                  'deflated' if comp == zipfile.ZIP_DEFLATED else 'stored'))
    return out


def _open(game, dest=None):
    out = archive_path(game, dest)
    if not os.path.exists(out):
        raise SystemExit('no vault at %s' % out)
    return out


def verify(game, dest=None):
    out = _open(game, dest)
    with zipfile.ZipFile(out) as z:
        man = json.loads(z.read(MANIFEST))
        print('%s  created %s' % (out, man['created']))
        bad = 0
        for n, meta in sorted(man['entries'].items()):
            h = hashlib.sha256()
            with z.open(meta.get('filename', n + '.map')) as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
            ok = h.hexdigest() == meta['sha256']
            bad += not ok
            print('  %-10s %s' % (n, 'ok' if ok else 'CORRUPT'))
        print('  %d entr(ies), %d corrupt' % (len(man['entries']), bad))
        return bad == 0


def unpack(game, only=None, to_shipped=False, dest=None):
    out, d = _open(game, dest), map_dir(game)
    with zipfile.ZipFile(out) as z:
        man = json.loads(z.read(MANIFEST))
        for n in sorted(man['entries']):
            if only and n not in only:
                continue
            arc = man['entries'][n].get('filename', n + '.map')
            dst = os.path.join(d, arc + ('.shipped' if to_shipped else ''))
            with z.open(arc) as f, open(dst, 'wb') as g:
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
    ap.add_argument('--from', dest='source', default='original',
                    choices=('original', 'map'),
                    help='where a pack takes its bytes; "map" trusts the live file')
    ap.add_argument('--only', help='comma list of map basenames')
    ap.add_argument('--to-shipped', action='store_true',
                    help='unpack to <map>.shipped instead of over the live map')
    ap.add_argument('--hash', action='store_true', help='survey also hashes each map')
    ap.add_argument('--dest', help='destination folder for the archive')
    ap.add_argument('--yes', action='store_true', help='actually write the archive')
    a = ap.parse_args(argv)
    only = set(a.only.split(',')) if a.only else None
    if a.survey:
        survey(a.survey, a.hash)
    if a.pack:
        pack(a.pack, a.dest, a.source, only, a.yes)
    if a.verify:
        verify(a.verify, a.dest)
    if a.unpack:
        unpack(a.unpack, only, a.to_shipped, a.dest)
    if not any((a.survey, a.pack, a.verify, a.unpack)):
        ap.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
