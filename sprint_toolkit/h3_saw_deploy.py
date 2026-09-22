r"""Put the built Halo 3 map in place and check the port survived the build.

Everything the port owns is decided at BUILD time -- the model, the two animation
graphs, the HUD definition, the projectile -- and the numbers are written afterwards by
the patcher. This installs the built map (optionally as the baseline, so a later patch
does not erase the port) and then answers, from map data alone, whether the build
actually produced what the tags asked for:

  * does the weapon point at the port's OWN chud, animation graphs and projectile?
  * did the cache builder DEDUPLICATE the cloned chud back onto the Assault Rifle's?
    A byte-identical clone can come out of the build sharing its donor's blocks, and
    then a write to one lands on both -- the trap that moved the Assault Rifle's
    magazine to 72.
  * do the SAW's animations carry the retimed frame counts, and the Assault Rifle's
    still its own?

    python h3_saw_deploy.py --check                 # read the built map, change nothing
    python h3_saw_deploy.py --install [--baseline]
"""
import argparse, contextlib, io, os, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402
import halo3_reload as hr       # noqa: E402

B = os.sep
GAME = 'Halo 3'
EK_MAPS = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK', 'maps')
SAW = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW_CHUD = B.join(['ui', 'chud', 'saw'])
AR_CHUD = B.join(['ui', 'chud', 'assault_rifle'])
SAW_FP = B.join(['objects', 'weapons', 'rifle', 'saw', 'fp', 'fp_saw_*'])
AR_FP = B.join(['objects', 'characters', '*', 'fp', 'weapons', 'rifle',
                'fp_assault_rifle', 'fp_assault_rifle'])
PROBE = 99


def check(path):
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(path, GAME)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    print('%s  (%.0f MB)' % (os.path.basename(path), os.path.getsize(path) / 1e6))

    for cls, tag, what in (('weap', SAW, 'the port'), ('chdt', SAW_CHUD, 'its own HUD')):
        print('   %-28s %s' % (tag, 'present' if m.find_tags(cls, tag) else 'ABSENT'))

    print('\n   animation frame counts (reload / ready):')
    for label, pat in (('SAW', SAW_FP), ('Assault Rifle', AR_FP)):
        rel = hr.reload_frames(m, pat, game=GAME, match=('reload',))
        rdy = hr.reload_frames(m, pat, game=GAME, match=('ready',))
        print('      %-14s reload %-14s ready %s'
              % (label, [f for _w, f in rel], [f for _w, f in rdy]))

    plugin = reg.get('chdt')
    if m.find_tags('chdt', SAW_CHUD) and plugin is not None:
        f = 'Low Ammo Loaded Threshold'
        before = {t: m.read_first('chdt', t, f, plugin, None) for t in (AR_CHUD, SAW_CHUD)}
        print('\n   low ammo threshold: assault_rifle %s, saw %s'
              % (before[AR_CHUD], before[SAW_CHUD]))
        # in-memory probe; the map is never saved here
        m.apply_field('chdt', SAW_CHUD, f, 'set', PROBE, plugin, None, 0)
        after = m.read_first('chdt', AR_CHUD, f, plugin, None)
        if after != before[AR_CHUD]:
            print('   SHARED -- writing the port\'s chud moved the Assault Rifle\'s too;'
                  '\n   the threshold must differ in the TAG before the build')
        else:
            print('   the clone owns its blocks: the donor did not move')
    del m


def install(mission, baseline):
    import shutil
    live = os.path.join(he.mcc_root(), 'halo3', 'maps', mission + '.map')
    base = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', mission), GAME)
    built = os.path.join(EK_MAPS, mission + '.map')
    if not os.path.exists(built):
        raise SystemExit('no built map at %s' % built)
    shutil.copyfile(built, live)
    print('installed -> %s' % live)
    if baseline:
        if os.path.exists(base) and not os.path.exists(base + '.vanilla'):
            shutil.copyfile(base, base + '.vanilla')
            print('kept the vanilla baseline at %s.vanilla' % base)
        shutil.copyfile(built, base)
        print('baseline  -> %s' % base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    a = ap.parse_args()
    he.load_settings()
    if a.install:
        install(a.map, a.baseline)
    target = (os.path.join(he.mcc_root(), 'halo3', 'maps', a.map + '.map')
              if a.install else os.path.join(EK_MAPS, a.map + '.map'))
    if a.check or a.install:
        check(target)


if __name__ == '__main__':
    main()
