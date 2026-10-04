r"""Rebuild every Halo 2 campaign level from the editing kit and ship it.

For each level (all 13 except 01b_spacestation, which is reserved for another test --
--include-01b adds it):
  1. h2_batch's four stages: ability plumbing into the scenario tag, the level's script
     stubs, tool rebuild-scenario-scripts, tool build-cache-file (win64, compress)
  2. check the build: fresh, and carrying the ability pickups (ab_camo0/1); report the
     enhancer markers and the SAW (a level without markers still ships -- they are
     placed level by level)
  3. ship it as the patcher's BASELINE (halo_patch.baseline_path: the Baselines folder
     from settings.json, else the sibling .bak). The baseline it replaces is kept as ONE
     previous generation in E:\HaloBackups\ek-build-h2\previous.
  4. ship it into MCC (halo2\h2_maps_win64_dx11\<level>.map) -- unpatched; the next
     patch from the enhancer rebuilds the run on top of the new baseline.

A level that fails to build or check is NOT shipped; the others still are.

    python h2_rebuild_all.py                    all levels but 01b
    python h2_rebuild_all.py --maps 03a,03b     some of them (short or full names)
    python h2_rebuild_all.py --include-01b      01b as well
    python h2_rebuild_all.py --no-ship          build + check only
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import h2_batch  # noqa: E402
import halo_patch  # noqa: E402

MCC = os.path.dirname(ROOT)
SUBDIR = os.path.join('halo2', 'h2_maps_win64_dx11')
LIVE = os.path.join(MCC, SUBDIR)
PREVIOUS = os.path.join('E:' + os.sep, 'HaloBackups', 'ek-build-h2', 'previous')
RESERVED = {'01b_spacestation'}          # another test owns it (memory: do not test on 01b)
NAMES = (0x48, 0x24)                     # scnr Object Names


def baseline_root():
    try:
        with open(os.path.join(ROOT, 'settings.json'), encoding='utf-8') as f:
            return (json.load(f).get('baseline_root') or '').strip()
    except (OSError, ValueError):
        return ''


def steam_update_pending():
    """Steam deletes modded maps while an MCC update is pending -- don't ship then."""
    return os.path.isdir(os.path.join(MCC, '..', '..', 'downloading', '976730'))


def object_names(m):
    s = halo_patch._scnr_base(m)
    n, b = m.i32(s + NAMES[0]), halo_patch._block_base(m, s + NAMES[0])
    return {bytes(m.data[b + i * NAMES[1]:b + i * NAMES[1] + 0x20]).split(b'\0')[0]
            .decode('latin-1') for i in range(n if b else 0)}


def check(path):
    m = halo_patch.open_map(path, 'Halo 2')
    names = object_names(m)
    camo = {'ab_camo0', 'ab_camo1'} <= names
    markers = sorted(k for k in halo_patch.reach_named_markers(m, 'Halo 2'))
    try:                                  # the port's own weapon tag (weapon_ports catalog)
        import weapon_ports
        saw_path = weapon_ports.weap_path(weapon_ports.port_for('Halo 2', 'SAW'))
    except Exception:
        saw_path = None
    saw = bool(saw_path) and any(t.get('class') == 'weap' and t.get('name') == saw_path
                                 for t in m.tags)
    note = 'ability pickups %s, markers %s, SAW %s' % (
        'yes' if camo else 'NO', '+'.join(x[-1] for x in markers) or 'none',
        'yes' if saw else 'no')
    problem = None if camo else 'no ab_camo0/1 pickups -- the ability plumbing did not land'
    return note, problem


def build(level, logdir):
    for stage, fn in (('tag', h2_batch.apply_tag), ('script', h2_batch.install_stub)):
        ok, msg = fn(level, verbose=False)
        if not ok:
            return None, '%s: %s' % (stage, msg)
    for stage, fn in (('scripts', h2_batch.rebuild_scripts), ('build', h2_batch.build_cache)):
        ok, msg = fn(level, logdir)
        if not ok:
            return None, '%s: %s (log in %s)' % (stage, msg, logdir)
    return os.path.join(h2_batch.MAPS_OUT, level + '.map'), msg


def ship(level, built, root):
    live = os.path.join(LIVE, level + '.map')
    base = halo_patch.baseline_path(live, root or None, SUBDIR)
    if os.path.exists(base):
        os.makedirs(PREVIOUS, exist_ok=True)
        shutil.copy2(base, os.path.join(PREVIOUS, level + '.map'))
    os.makedirs(os.path.dirname(base), exist_ok=True)
    shutil.copy2(built, base)
    shutil.copy2(built, live)
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', default='', help='comma list; short (03a) or full names')
    ap.add_argument('--include-01b', action='store_true', help='rebuild 01b_spacestation too')
    ap.add_argument('--no-ship', action='store_true', help='build and check only')
    ap.add_argument('--logdir', default=os.path.join(HERE, 'out', 'h2logs'))
    a = ap.parse_args()
    sel = [s.strip() for s in a.maps.split(',') if s.strip()]
    levels = [h2_batch.BY_SHORT.get(s, s) for s in sel] if sel else [l for _, l in h2_batch.LEVELS]
    if not a.include_01b:
        skipped = [l for l in levels if l in RESERVED]
        levels = [l for l in levels if l not in RESERVED]
        if skipped:
            print('Skipping %s (reserved for another test; --include-01b to rebuild it)'
                  % ', '.join(skipped))

    root = baseline_root()
    if root and not os.path.isdir(os.path.splitdrive(root)[0] + os.sep):
        sys.exit('Baselines folder %s is on a drive that is not connected.' % root)
    if not a.no_ship and steam_update_pending():
        sys.exit('A Steam update of MCC is pending -- it would delete the shipped maps. '
                 'Let it finish first.')
    os.makedirs(a.logdir, exist_ok=True)
    print('Building %d Halo 2 level(s). Baselines: %s' % (len(levels), root or 'sibling .bak files'))

    ok, failed = [], []
    for level in levels:
        t0 = time.time()
        print('\n[%s] building (tag, scripts, cache)...' % level, flush=True)
        built, msg = build(level, a.logdir)
        if not built:
            print('  FAILED', msg)
            failed.append(level)
            continue
        note, problem = check(built)
        print('  built in %.0fs (%s) -- %s' % (time.time() - t0, msg, note))
        if problem:
            print('  NOT SHIPPED:', problem)
            failed.append(level)
            continue
        if not a.no_ship:
            base = ship(level, built, root)
            print('  shipped -> %s and %s' % (base, SUBDIR))
        ok.append(level)

    print('\nDONE: %d ok (%s), %d failed (%s)' % (len(ok), ' '.join(ok) or '-',
                                                 len(failed), ' '.join(failed) or '-'))
    if not a.no_ship and ok:
        print('Previous baselines kept in %s. Patch a run in the enhancer to apply it '
              'on top of the new maps.' % PREVIOUS)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
