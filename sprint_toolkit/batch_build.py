"""Batch-build the Halo 1 sprint mod: all 10 campaign maps, both versions.

  classic_all       every player weapon + equipment, CLASSIC graphics, self-contained
                    (--resources none, so it never reads the remastered bitmaps.map)
  remastered_alien  alien weapons only + equipment, REMASTERED graphics (shared maps)

For each version and map it: inserts sprint_profile + the weapon/equipment palette
from a PRISTINE scenario, builds with tool.exe, tunes (enables sprint at --speed),
and collects the finished .map into out\\<version>\\. It does NOT touch the game's
halo1\\maps — these outputs are what the mod packager will bundle.

Usage:
  python batch_build.py                 # both versions, all 10 maps
  python batch_build.py --version classic_all
  python batch_build.py --maps b30,b40 --speed 160
  python batch_build.py --out D:\\sprintmod
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: E402  (install paths — edit paths.py)
import h1_loosetag as L  # noqa: E402

HCEEK = paths.HCEEK
SCNR_XML = paths.SCNR_XML
TOOL = paths.TOOL_EXE
TUNE = os.path.join(HERE, 'sprint_tune.py')

MAPS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

# Both versions build SELF-CONTAINED (resources='none'): it avoids the shared
# bitmaps.map mismatch that broke the UI, and a self-contained REMASTERED build
# renders correctly in BOTH the remastered and classic in-game views (verified on
# a10). The classic_all set must be classic (human weapons force it); the
# remastered_alien set is remastered so players keep the HD graphics toggle.
VERSIONS = {
    'classic_all': dict(graphics='classic', resources='none',
                        weapons=L.HUMAN_WEAPONS + L.ALIEN_WEAPONS, equipment=L.EQUIPMENT),
    'remastered_alien': dict(graphics='remastered', resources='none',
                             weapons=L.ALIEN_WEAPONS, equipment=L.EQUIPMENT),
}


def pristine_source(scn):
    """Path to a pristine scenario to insert from. Prefer the .presprint backup;
    else the current scenario if it has no sprint_profile yet (then snapshot it as
    .presprint for reproducibility). A scenario that already carries sprint_profile
    but has no backup (Guerilla-edited b30) is used as-is; the inserts are idempotent."""
    pre = scn + '.presprint'
    if os.path.exists(pre):
        return pre
    data = open(scn, 'rb').read()
    if 'sprint_profile' not in L.profile_names(bytearray(data), SCNR_XML):
        shutil.copy2(scn, pre)          # pristine -> snapshot it
        return pre
    return scn                          # already has sprint (b30); idempotent inserts handle it


def build_one(mp, cfg, outdir, speed):
    scn = os.path.join(HCEEK, 'tags', 'levels', mp, mp + '.scenario')
    if not os.path.isfile(scn):
        return False, 'no scenario'
    data = bytearray(open(pristine_source(scn), 'rb').read())
    L.add_sprint(data, SCNR_XML)
    L.add_palette_entries(data, SCNR_XML, L.PALETTE_OFF, b'weap', cfg['weapons'])
    L.add_palette_entries(data, SCNR_XML, L.EQUIP_PALETTE_OFF, b'eqip', cfg['equipment'])
    open(scn, 'wb').write(data)

    r = subprocess.run([TOOL, 'build-cache-file', 'levels\\%s\\%s' % (mp, mp),
                        cfg['graphics'], cfg['resources'], '1'], cwd=HCEEK,
                       capture_output=True, text=True)
    if 'successfully built' not in (r.stdout or ''):
        return False, 'build failed'

    built = os.path.join(HCEEK, 'maps', mp + '.map')
    # sprint_tune tunes FROM a <map>.map.bak baseline it creates and reuses. A stale
    # .bak from the other version would overwrite THIS fresh build — delete it so the
    # baseline is re-taken from the map we just built.
    if os.path.exists(built + '.bak'):
        os.remove(built + '.bak')
    t = subprocess.run([sys.executable, TUNE, built, '--mult', '%g' % (speed / 100.0),
                        '--enable'], capture_output=True, text=True)
    if 'sprint_enabled -> true' not in (t.stdout or ''):
        return False, 'tune failed'

    os.makedirs(outdir, exist_ok=True)
    shutil.copy2(built, os.path.join(outdir, mp + '.map'))
    return True, '%.1f MB' % (os.path.getsize(built) / 1e6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', choices=list(VERSIONS) + ['both'], default='both')
    ap.add_argument('--maps', default='', help='comma list; default all 10')
    ap.add_argument('--speed', type=int, default=150)
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()

    versions = list(VERSIONS) if a.version == 'both' else [a.version]
    maps = [m.strip() for m in a.maps.split(',') if m.strip()] or MAPS

    grand_ok = grand_fail = 0
    for ver in versions:
        cfg = VERSIONS[ver]
        outdir = os.path.join(a.out, ver)
        print('\n=== %s  ->  %s  (%s, %s, %d weapons)' %
              (ver, outdir, cfg['graphics'], cfg['resources'], len(cfg['weapons'])))
        for mp in maps:
            t0 = time.time()
            ok, msg = build_one(mp, cfg, outdir, a.speed)
            print('  %-5s %-4s %-14s %5.0fs' % (mp, 'OK' if ok else 'FAIL', msg, time.time() - t0))
            grand_ok += ok
            grand_fail += not ok

    print('\nDONE: %d built, %d failed. Output under %s' % (grand_ok, grand_fail, a.out))
    if grand_fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
