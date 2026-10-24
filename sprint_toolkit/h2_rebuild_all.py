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

WEAPON PORTS (H2_PORT_PLAN.md, 2026-10-20): the whole run holds the H2 kit lock; a port whose
ports_h2 config is not 'done' is NEUTRALISED in a SHIPPING build (its palette entry renamed to a
stock weapon for the build in the weapons resource AND the scenario's own palette copy; any other
kit reference -- the AI resource, ai\generic -- becomes a same-length stock path; all put back
after -- h2_port_residency.neutralise / neutralise_refs), so an in-progress port never ships;
--no-ship builds keep every port. Each built level reports how many done ports are resident (their weapon tags in
the map); a done port missing fails the level, and so does a not-done port still in a shipping build.

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
import h2_port_residency  # noqa: E402
import halo_patch  # noqa: E402
import kit_lock  # noqa: E402
import ports_h2  # noqa: E402

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


def check(path, shipping=True):
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
    weaps = {t.get('name') for t in m.tags if t.get('class') == 'weap'}
    want = [(k, h2_port_residency.weapon_path(p)) for k, p in ports_h2.all_ports()
            if p.get('status') == 'done' or not shipping]
    missing = [k for k, w in want if w not in weaps]
    leaked = [w.split(chr(92))[-1] for w in busy_ports() if w in weaps] if shipping else []
    note = 'ability pickups %s, markers %s, SAW %s, ports %d/%d resident' % (
        'yes' if camo else 'NO', '+'.join(x[-1] for x in markers) or 'none',
        'yes' if saw else 'no', len(want) - len(missing), len(want))
    problem = None if camo else 'no ab_camo0/1 pickups -- the ability plumbing did not land'
    if missing and not problem:
        problem = 'port(s) not resident: %s' % ', '.join(missing)
    if leaked and not problem:
        problem = ('not-done port(s) still built in: %s -- some tag other than the weapons '
                   'palettes references them' % ', '.join(leaked))
    return note, problem


def busy_ports():
    return [h2_port_residency.weapon_path(p) for _k, p in ports_h2.all_ports()
            if p.get('status') != 'done']


def neutralise_busy(level):
    """Rename every not-done port's palette entry for a SHIPPING build -- in the weapons resource
    AND in the scenario's own copy of the palette (tool loads every tag that copy names before
    stomping it, so a port left there is built in anyway: h2_port_residency.weapon_palette).
    Returns {path: original bytes} to put back ({} when there was nothing to do)."""
    busy = busy_ports()
    keep, gone, stuck = {}, set(), set()
    R = h2_port_residency
    files = ([(R.resource(level), False), (R.scenario(level), True)]
             + [(f, None) for f in R.ai_resources(level) + [R.GENERIC_CHARACTER]])
    for path, in_scenario in files:
        if not busy or not os.path.exists(path):
            continue
        original = open(path, 'rb').read()
        data = bytearray(original)
        hit = ([p for _i, p in R.neutralise(data, busy, in_scenario=in_scenario)]
               if in_scenario is not None else [])
        # any other reference (AI resource weapon list, ai\generic's weapon properties):
        # a same-length stock stand-in; one with none is left for check() to refuse
        more, left = R.neutralise_refs(data, busy)
        hit += more
        stuck.update(left)
        if hit:
            open(path, 'wb').write(bytes(data))
            keep[path] = original
            gone.update(hit)
    if gone:
        print('  left out of the shipping build (not done): %s'
              % ', '.join(sorted(p.split(chr(92))[-1] for p in gone)))
    if stuck:
        print('  could NOT neutralise (no same-length stock stand-in): %s'
              % ', '.join(sorted(p.split(chr(92))[-1] for p in stuck)))
    return keep


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
    with kit_lock.script('h2_rebuild_all', kit='h2'):
        _main()


def _main():
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
        keep = {} if a.no_ship else neutralise_busy(level)
        try:
            built, msg = build(level, a.logdir)
        finally:
            for path, original in keep.items():
                open(path, 'wb').write(original)
        if not built:
            print('  FAILED', msg)
            failed.append(level)
            continue
        note, problem = check(built, shipping=not a.no_ship)
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
