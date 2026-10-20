r"""Every Halo 1 port PLACED (pickable) around a level's enhancer markers -- a look-at-them-all test
copy of a SHIPPED map (the user, 2026-10-19: d40 after the 16 Reach / Halo 4 ports went back to
full detail). No rebuild: the enhancer's own placer (`halo_patch._apply_spawn_weapons_h1`, the
'Starting weapons' path) rings the ports around `enhancer_marker1` and `enhancer_marker2`, half
at each, flags 0 (spawn with the level), full magazines, 0.3 wu up; written to
HCEEK\maps\all_ports_test\<level>.map and staged live (h1_port_test_map.stage; the live map is
backed up, `python h1_port_test_map.py --restore <level> --force` puts it back).

    python h1_all_ports_test_map.py --level d40 [--radius 1.0] [--no-stage]

A KIT build instead of the shipped map (the ammo meters, 2026-10-20: 19 ports' HUDs changed, so the
shipped map shows the old ones): build it with `h1_rebuild_all.py --maps a30 --no-ship` first, then
    python h1_all_ports_test_map.py --level a30 --source kit --keys smg,dmr,...
`--source` kit = HCEEK\maps\<level>.map (or a map path); `--keys` = only these ports, whatever
their status (a port in rework is left out otherwise).
"""
import argparse
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import paths  # noqa: E402
import ports_h1  # noqa: E402

GAME = 'Halo 1'
OWNER = 'all_ports_test'
STANDALONE = {'saw': r'weapons\saw\saw'}      # built before the configs had a pickable section


def weapon_tags(keys=None):
    out = []
    for key, P in ports_h1.all_ports():
        if keys is not None:
            if key not in keys:
                continue
        elif P.get('status') != 'done':
            continue
        w = (P.get('pickable') or {}).get('weapon') or STANDALONE.get(key)
        if w:
            out.append((key, w))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', default='d40')
    ap.add_argument('--radius', type=float, default=1.0)
    ap.add_argument('--no-stage', action='store_true')
    ap.add_argument('--source', help="'kit' (the kit's own build of the level, h1_rebuild_all --no-ship) or a map path")
    ap.add_argument('--keys', help='comma list of port keys, any status (default: every done port)')
    a = ap.parse_args()
    cwd = os.getcwd()
    os.chdir(TOOL)
    import halo_enhancer as he
    import halo_patch as hp
    he.load_settings()
    if a.source:
        src = (os.path.join(paths.HCEEK, 'maps', a.level + '.map') if a.source == 'kit'
               else os.path.abspath(os.path.join(cwd, a.source)))
    else:
        src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo1', a.level), GAME)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    os.chdir(cwd)
    print('%s from %s; markers: %s' % (a.level, src, hp.reach_named_markers(m, GAME)))
    keys = a.keys.split(',') if a.keys else None
    tags = weapon_tags(keys)
    if keys and len(tags) != len(keys):
        raise SystemExit('unknown or unplaceable key(s): %s' % sorted(set(keys) - {k for k, _t in tags}))
    half = (len(tags) + 1) // 2
    groups = [[t for _k, t in tags[:half]], [t for _k, t in tags[half:]]]
    res = hp._apply_spawn_weapons(m, GAME, {'groups': groups, 'radius': a.radius}, reg)
    bad = [r for r in res if not r.get('ok')]
    for r in res:
        print('   %-24s %s' % (r.get('field'), r.get('new') if r.get('ok') else 'FAILED: ' + r.get('reason', '')))
    if bad:
        raise SystemExit('%d port(s) not placed' % len(bad))
    out_dir = os.path.join(paths.HCEEK, 'maps', 'all_ports_test')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, a.level + '.map')
    m.save(out)
    print('%d ports placed (%d at marker1, %d at marker2, radius %.1f wu) -> %s'
          % (len(res), len(groups[0]), len(groups[1]), a.radius, out))
    if not a.no_stage:
        import h1_port_test_map
        h1_port_test_map.stage(a.level, out, 'ALL PORTS PLACED %s (%d at the enhancer markers)'
                               % (a.level, len(res)), owner=OWNER)


if __name__ == '__main__':
    main()
