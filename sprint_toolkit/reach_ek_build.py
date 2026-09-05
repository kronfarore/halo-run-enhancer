# -*- coding: utf-8 -*-
r"""Build Reach campaign maps with the HREK, install them, and finish the recipe.

Building is only the first of three steps, and skipping either of the others leaves a
map that looks right and does not work:

  1. tool.exe build-cache-file levels\solo\<map>\<map> pc
  2. install over haloreach\maps\<map>.map AND refresh <map>.map.bak -- the patcher
     builds every run FROM .bak, so a stale .bak silently throws the rebuild away
  3. residency: a tag whose bit is clear in the first zone set's pool cannot be built
     by the engine at mission start, so its placement is inert. See reach_pools.py.

    python reach_ek_build.py --all                  # build + install + residency, all maps
    python reach_ek_build.py --build m20 --install m20
    python reach_ek_build.py --check                # lint placements, no building
    python reach_ek_build.py --status

The map list comes from halo.json, so only real missions are built -- HREK also
carries m05 and m70_a, which the game does not run and which are an hour of nothing.

A build takes minutes per map with long silent stretches and looks hung when it is not;
it ends with "successfully built cache file". Ten maps is roughly an hour.
"""
import argparse
import json
import os
import shutil
import subprocess
import io
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP                                          # noqa: E402
import reach_pools as RP                                         # noqa: E402

EK = r"F:\SteamLibrary\steamapps\common\HREK"
GAME = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\haloreach\maps")
SCENARIO = r"levels\solo\%s\%s"
def campaign_maps():
    """The missions halo.json actually offers, in its own order.

    HREK has scenarios the game does not run as missions -- m05 and m70_a build
    happily and are an hour of nothing. halo.json is the list that decides what the
    enhancer can be played on, so it is the list worth building.
    """
    doc = json.load(io.open(os.path.join(os.path.dirname(HERE), 'halo.json'),
                            encoding='utf-8'))
    return list(doc['Missions']['Halo Reach'])


MAPS = campaign_maps()

#: Placement Flags, Reach scnr. Create At Rest is the one that is easy to forget in
#: Sapien and hard to diagnose afterwards: without it a weapon is spawned falling
#: rather than settled, so it tumbles, sinks into the floor, or ends up somewhere the
#: player never looks -- which reads exactly like "it did not spawn".
NOT_AUTOMATICALLY = 1 << 0
NEVER_PLACED = 1 << 6
CREATE_AT_REST = 1 << 8


def build(name, platform='pc'):
    scen = SCENARIO % (name, name)
    cmd = [os.path.join(EK, 'tool.exe'), 'build-cache-file', scen, platform]
    print('  %s' % ' '.join(cmd))
    t0 = time.time()
    r = subprocess.run(cmd, cwd=EK, capture_output=True, text=True)
    out = ((r.stdout or '') + (r.stderr or '')).strip()
    if out:
        print('  ' + out[-1200:].replace('\n', '\n  '))
    built = os.path.join(EK, 'maps', name + '.map')
    ok = r.returncode == 0 and os.path.exists(built)
    print('  exit %d after %.0fs; %s'
          % (r.returncode, time.time() - t0,
             ('built %d bytes' % os.path.getsize(built)) if os.path.exists(built)
             else 'NO MAP PRODUCED'))
    return ok


def install(name, baseline=True):
    """Install the build and make it the patcher's baseline.

    apply_run patches FROM `<map>.bak` when it exists and saves over `<map>`, so a
    .bak still holding the shipped map would rebuild from vanilla on the next run and
    wipe everything the rebuild added -- silently, with no error. The rebuild IS the
    pristine state now, so .bak points at it; the shipped original is kept as
    `<map>.map.shipped`, a name apply_run never looks at.
    """
    dst = os.path.join(GAME, name + '.map')
    bak, shipped = dst + '.bak', dst + '.shipped'
    src = os.path.join(EK, 'maps', name + '.map')
    if not os.path.exists(src):
        print('  no build output at %s' % src)
        return False
    if not os.path.exists(shipped):
        origin = bak if os.path.exists(bak) else (dst if os.path.exists(dst) else None)
        if origin:
            shutil.copy2(origin, shipped)
            print('  preserved the shipped map as %s' % os.path.basename(shipped))
    try:
        shutil.copy2(src, dst)
    except PermissionError:
        print('  %s is loaded in MCC -- leave the mission and retry' % name)
        return False
    print('  installed (%d bytes)' % os.path.getsize(dst))
    if baseline:
        shutil.copy2(src, bak)
        print('  .bak refreshed, so the patcher builds runs from the rebuild')
    return True


def residency(name, write=True):
    """Make every palette entry resident at mission start."""
    argv = [name, '--both', '--fix-all'] + (['--write'] if write else [])
    try:
        RP.main(argv)
        return True
    except SystemExit as ex:
        print('  residency skipped: %s' % ex)
        return False


def check(name):
    """Report placements that will not behave, without touching anything.

    Create At Rest is the flag worth naming: a placement without it is dropped rather
    than set down. Shipped maps leave it clear all over the place -- vanilla m50 has 55
    such placements -- so a raw count is noise. What matters is the NOT AUTOMATICALLY
    ones, because those are the marker-style placements the patcher switches on at
    positions nobody has watched an object land in. Those are the ones to name.
    """
    path = os.path.join(GAME, name + '.map')
    if not os.path.exists(path):
        print('  %-10s (no map)' % name)
        return
    m = HP.open_map(path, 'Halo Reach')
    try:
        scnr = HP._scnr_base(m)
    except Exception as ex:
        print('  %-10s unreadable (%s)' % (name, ex))
        return
    sep = chr(92)
    total = restless = marker_restless = 0
    names = []
    for kind, lay in (('weapons', HP._MAP_WEAPONS['Halo Reach']),
                      ('equipment', HP._MAP_EQUIPMENT['Halo Reach'])):
        off, es = lay['items' if kind == 'equipment' else 'weapons']
        poff, pes = lay['palette']
        pb = HP._block_base(m, scnr + poff)
        pal = [str(HP._tag_name_by_id(m, m.u32(pb + i * pes + lay['pal_id_at'])))
               .split(sep)[-1] for i in range(max(0, m.i32(scnr + poff)))]
        b, n = HP._block_base(m, scnr + off), max(0, m.i32(scnr + off))
        for i in range(n) if b else []:
            e = b + i * es
            fl = struct.unpack_from('<I', m.data, e + 0x4)[0]
            if fl & NEVER_PLACED:
                continue
            total += 1
            if fl & CREATE_AT_REST:
                continue
            restless += 1
            if not (fl & NOT_AUTOMATICALLY):
                continue            # vanilla leaves it clear constantly; not our work
            marker_restless += 1
            pi = struct.unpack_from('<h', m.data, e)[0]
            nm = pal[pi] if 0 <= pi < len(pal) else '?'
            if nm not in names:
                names.append(nm)
    print('  %-10s %3d placement(s), %3d without Create At Rest, %3d of those '
          'marker-style%s'
          % (name, total, restless, marker_restless,
             ('  ' + ', '.join(names[:8]) + (' ...' if len(names) > 8 else ''))
             if names else ''))


def status(name):
    for label, path in (('game    ', os.path.join(GAME, name + '.map')),
                        ('baseline', os.path.join(GAME, name + '.map.bak')),
                        ('shipped ', os.path.join(GAME, name + '.map.shipped')),
                        ('EK build', os.path.join(EK, 'maps', name + '.map'))):
        print('  %-8s %s' % (label, ('%d bytes' % os.path.getsize(path))
                             if os.path.exists(path) else '(absent)'))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', action='store_true',
                    help='build, install and set residency for every halo.json mission')
    ap.add_argument('--maps', help='comma-separated subset for --all/--check/--status')
    ap.add_argument('--build', action='append', default=[], metavar='MAP')
    ap.add_argument('--install', action='append', default=[], metavar='MAP')
    ap.add_argument('--residency', action='append', default=[], metavar='MAP')
    ap.add_argument('--check', action='store_true',
                    help='lint installed maps for placements without Create At Rest')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--no-residency', action='store_true',
                    help='with --all, build and install only')
    ap.add_argument('--dry-run', action='store_true',
                    help='say what --all would do, build nothing')
    a = ap.parse_args(argv)

    picked = [x.strip() for x in a.maps.split(',')] if a.maps else MAPS
    bad = [x for x in picked if x not in MAPS]
    if bad:
        raise SystemExit('unknown map(s): %s' % ', '.join(bad))

    if a.status:
        for name in picked:
            print('%s' % name)
            status(name)
        return 0
    if a.check:
        print('placements missing Create At Rest -- they are dropped, not set down.')
        print('Vanilla script-spawned placements lack it too (untouched m50 has 53),')
        print('so read the marker-style column only for maps you have edited.')
        for name in picked:
            check(name)
        return 0

    if a.all:
        if a.dry_run:
            print('would build, install%s: %s'
                  % ('' if a.no_residency else ' and set residency for',
                     ', '.join(picked)))
            return 0
        done, failed = [], []
        t0 = time.time()
        for k, name in enumerate(picked, 1):
            print()
            print('=== [%d/%d] %s' % (k, len(picked), name))
            if not build(name):
                failed.append(name)
                continue
            if not install(name):
                failed.append(name)
                continue
            if not a.no_residency:
                residency(name)
            check(name)
            done.append(name)
        print()
        print('%d built and installed, %d failed, %.0f min total'
              % (len(done), len(failed), (time.time() - t0) / 60.0))
        if failed:
            print('failed: %s' % ', '.join(failed))
        return 1 if failed else 0

    for name in a.build:
        print('=== build %s' % name)
        build(name)
    for name in a.install:
        print('=== install %s' % name)
        install(name)
    for name in a.residency:
        print('=== residency %s' % name)
        residency(name)
    if not (a.build or a.install or a.residency):
        ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
