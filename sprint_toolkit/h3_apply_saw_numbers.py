r"""Write the ported SAW's numbers into the installed Halo 3 map.

This is the patcher's own weapon-port pass (halo_patch.apply_weapon_ports) run on its
own, so the weapon can be tried in game before a full run is set up. It reads the Halo 3
entry of weapon_ports_catalog.json, so what lands here is exactly what a patched run
would apply.

    python h3_apply_saw_numbers.py [--map 010_jungle] [--dry-run]
"""
import argparse, contextlib, io, os, shutil, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402
import weapon_ports             # noqa: E402

B = os.sep
GAME = 'Halo 3'
SAW = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
BULLET = B.join(['objects', 'weapons', 'rifle', 'saw', 'projectiles',
                 'saw_bullet_h4_original_numbers'])
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
AR_BULLET = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'projectiles',
                    'assault_rifle_bullet'])
SHOW = [('weap', SAW, 'Rounds Loaded Maximum', 'Magazines', 0),
        ('weap', SAW, 'Rounds Per Second', 'Barrels', 0),
        ('weap', SAW, 'Error Angle', 'Barrels', 1),
        ('proj', BULLET, 'Initial Velocity', None, 0),
        ('proj', BULLET, 'Maximum Range', None, 0),
        ('weap', AR, 'Rounds Loaded Maximum', 'Magazines', 0),
        ('proj', AR_BULLET, 'Initial Velocity', None, 0)]


def snap(m, reg):
    out = []
    for cls, tag, field, block, nth in SHOW:
        try:
            v = m.read_first(cls, tag, field, reg.get(cls), block, nth=nth)
        except Exception as e:
            v = 'ERR %s' % e
        out.append(('%s %s' % (tag.rsplit(B, 1)[-1][:22], field), v))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--keep', action='store_true',
                    help='do NOT restore from the baseline first (values will compound)')
    ap.add_argument('--no-balance', action='store_true',
                    help="write the port's OWN Halo 4 numbers instead of the balanced "
                         "ones -- the same thing the run option does")
    a = ap.parse_args()
    he.load_settings()
    live = os.path.join(he.mcc_root(), 'halo3', 'maps', a.map + '.map')
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    cfg = dict(he.CONFIG)
    if a.no_balance:
        cfg['weapon_ports_balance'] = False
    ports = weapon_ports.active_ports(GAME, cfg)
    if not ports:
        raise SystemExit('no active Halo 3 ports in the catalog')
    print('ports: %s  (%s)' % ([p['weapon'] for p in ports],
                               'Halo 4 originals' if a.no_balance else 'balanced'))
    # RESTORE FIRST, like a real run does. Without this the pass compounds on whatever
    # the last one left behind, and the animation scaling is not idempotent: applying
    # balanced (128 -> 109) and then the Halo 4 originals left the reload at 109, because
    # "originals" scales nothing and there was nothing to undo. That reads as the port
    # ignoring the setting, and would have cost an in-game test to notice.
    if not a.keep:
        base = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', a.map), GAME)
        if os.path.exists(base):
            shutil.copyfile(base, live)
            print('restored from the baseline first')
        else:
            print('NO BASELINE -- values may compound on the last run')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, GAME)
    before = snap(m, reg)
    for r in hp.apply_weapon_ports(m, GAME, reg, ports):
        print('   %-18s %-14s %-16s -> %s%s'
              % (r.get('effect'), r.get('tag'), r.get('field'),
                 r.get('new') or r.get('reason'),
                 '' if r.get('ok') else '   [NOT OK]'))
    after = snap(m, reg)
    print('\n%-44s %-14s %s' % ('field', 'before', 'after'))
    for (f, x), (_f, y) in zip(before, after):
        fmt = lambda v: ('%.4g' % v) if isinstance(v, (int, float)) else str(v)
        print('%-44s %-14s %s%s' % (f, fmt(x), fmt(y), '' if x == y else '   <-'))
    if not a.dry_run:
        m.save(live)
        print('\nsaved %s' % live)


if __name__ == '__main__':
    main()
