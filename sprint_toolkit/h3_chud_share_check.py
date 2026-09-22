r"""Does the ported weapon's HUD actually have its OWN data in the built map?

The cache builder deduplicates identical block data, so a tag cloned byte-for-byte can
come out of the build sharing its donor's blocks -- which is how writing the port's
magazine once moved the Assault Rifle's from 32 to 72. A clone that shares is worse than
no clone at all, because it looks independent right up until the first write.

This answers it from map data alone, with no in-game test: write a distinctive value
into the PORT's chud and read the donor's back.

    ok        the donor did not move -- the clone owns its blocks
    SHARED    the donor moved too -- the threshold must go into the tag before the build

    python h3_chud_share_check.py [--map 010_jungle]
"""
import argparse, contextlib, io, os, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 3'
FIELD = 'Low Ammo Loaded Threshold'
DONOR = B.join(['ui', 'chud', 'assault_rifle'])
PORT = B.join(['ui', 'chud', 'saw'])
PROBE = 99                      # a value neither weapon would ever ship with


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    a = ap.parse_args()
    he.load_settings()

    live = os.path.join(he.mcc_root(), 'halo3', 'maps', a.map + '.map')
    if not os.path.exists(live):
        raise SystemExit('no %s' % live)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    plugin = reg.get('chdt')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, GAME)

    if not m.find_tags('chdt', PORT):
        raise SystemExit('%s is not in %s -- build the map with the cloned chud first'
                         % (PORT, a.map))

    before = {t: m.read_first('chdt', t, FIELD, plugin, None) for t in (DONOR, PORT)}
    print('before:  donor %s = %s, port %s = %s'
          % (DONOR.rsplit(B, 1)[-1], before[DONOR], PORT.rsplit(B, 1)[-1], before[PORT]))

    # written in memory only -- the map is never saved, so this is a read-only probe
    m.apply_field('chdt', PORT, FIELD, 'set', PROBE, plugin, None, 0)
    after = {t: m.read_first('chdt', t, FIELD, plugin, None) for t in (DONOR, PORT)}
    print('probe:   donor %s = %s, port %s = %s'
          % (DONOR.rsplit(B, 1)[-1], after[DONOR], PORT.rsplit(B, 1)[-1], after[PORT]))

    if after[PORT] != PROBE:
        print('\nINCONCLUSIVE -- the write did not land on the port at all')
    elif after[DONOR] != before[DONOR]:
        print('\nSHARED -- the donor moved with it. The clone does NOT own its blocks;\n'
              'the threshold has to differ in the tag BEFORE the cache is built.')
    else:
        print('\nok -- the port owns its blocks, the threshold can be a patch-time row.')


if __name__ == '__main__':
    main()
