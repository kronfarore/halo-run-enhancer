r"""Install a map built by the Editing Kit into the game, and optionally make it the
baseline the patcher rebuilds from.

The patcher always restores from the baseline before applying a run, so a port that lives
only in the live map is erased by the next patch. `--baseline` copies the built map into
the baseline store as well, which is how a ported weapon survives -- the port-bearing map
BECOMES the pristine one. The vanilla map is kept beside it the first time, so this stays
reversible.

    python h3_install_saw.py --status
    python h3_install_saw.py --install 010_jungle [--baseline]
    python h3_install_saw.py --restore 010_jungle
"""
import argparse, os, shutil, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
EK_MAPS = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK', 'maps')
GAME = 'Halo 3'


def paths(mission):
    live = os.path.join(he.mcc_root(), 'halo3', 'maps', mission + '.map')
    base = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', mission), GAME)
    built = os.path.join(EK_MAPS, mission + '.map')
    return live, base, built


def mb(p):
    return '%.0f MB' % (os.path.getsize(p) / 1e6) if os.path.exists(p) else 'missing'


def status(mission):
    live, base, built = paths(mission)
    print('%-12s built %-12s live %-12s baseline %s' % (mission, mb(built), mb(live), mb(base)))
    vanilla = base + '.vanilla'
    if os.path.exists(vanilla):
        print('%-12s vanilla baseline kept at %s (%s)' % ('', vanilla, mb(vanilla)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install')
    ap.add_argument('--restore')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    a = ap.parse_args()
    he.load_settings()

    if a.status:
        status('010_jungle')
        return
    if a.restore:
        live, base, _built = paths(a.restore)
        vanilla = base + '.vanilla'
        if os.path.exists(vanilla):
            shutil.copy2(vanilla, base)
            print('baseline restored from %s' % vanilla)
        shutil.copy2(base, live)
        print('live map restored from the baseline')
        return

    mission = a.install
    live, base, built = paths(mission)
    if not os.path.exists(built):
        raise SystemExit('no built map at ' + built)
    print('built    %s  %s' % (built, mb(built)))
    shutil.copy2(built, live)
    print('installed -> %s' % live)
    if a.baseline:
        vanilla = base + '.vanilla'
        if not os.path.exists(vanilla):
            shutil.copy2(base, vanilla)      # keep the real vanilla once
            print('kept the vanilla baseline at %s' % vanilla)
        shutil.copy2(built, base)
        print('baseline is now the built map -> %s' % base)
    else:
        print('NOTE: the baseline is still vanilla, so the next patch will erase the port.')


if __name__ == '__main__':
    main()
