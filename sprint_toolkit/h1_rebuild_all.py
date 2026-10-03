r"""Rebuild every Halo 1 campaign map from the editing kit and ship it.

For each level (all 10 by default):
  1. tool build-cache-file levels\<m>\<m> classic none 1   (self-contained classic)
  2. check the build: "successfully built", a fresh HCEEK\maps\<m>.map, and what it
     carries -- the 20 enemy-weapon slots, the sprint/ability weapon, the SAW.
     A level with fewer than 20 slots is not shipped (--allow-missing-slots).
  3. ship it as the patcher's BASELINE (halo_patch.baseline_path: the Baselines
     folder from settings.json, else the sibling .bak). The baseline it replaces is
     kept as ONE previous generation in E:\HaloBackups\ek-build-h1\previous.
  4. ship it into MCC (halo1\maps\<m>.map) -- unpatched; the next patch from the
     enhancer rebuilds the run on top of the new baseline.

global_scripts.hsc is synced with sprint.hsc first (install_script), as every
toolkit build does. A level that fails to build or check is NOT shipped; the
others still are. The scenarios are built as they are -- nothing is inserted.

    python h1_rebuild_all.py                 all 10 levels
    python h1_rebuild_all.py --maps a10,b30  some of them
    python h1_rebuild_all.py --no-ship       build + check only
    python h1_rebuild_all.py --allow-missing-slots
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import paths  # noqa: E402
import install_script  # noqa: E402
import halo_patch  # noqa: E402

MAPS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
MCC = os.path.dirname(ROOT)
LIVE = os.path.join(MCC, 'halo1', 'maps')
SUBDIR = os.path.join('halo1', 'maps')
PREVIOUS = os.path.join('E:' + os.sep, 'HaloBackups', 'ek-build-h1', 'previous')
SLOTS = 'characters\\enhancer\\slot*'
SLOT_COUNT = 20
SAW = 'weapons\\saw\\saw'


def baseline_root():
    try:
        with open(os.path.join(ROOT, 'settings.json'), encoding='utf-8') as f:
            return (json.load(f).get('baseline_root') or '').strip()
    except (OSError, ValueError):
        return ''


def steam_update_pending():
    """Steam deletes modded maps while an MCC update is pending -- don't ship then."""
    return os.path.isdir(os.path.join(MCC, '..', '..', 'downloading', '976730'))


def build(mp):
    t0 = time.time()
    r = subprocess.run([paths.TOOL_EXE, 'build-cache-file', 'levels\\%s\\%s' % (mp, mp),
                        'classic', 'none', '1'], cwd=paths.HCEEK,
                       capture_output=True, text=True, errors='replace')
    out = os.path.join(paths.HCEEK, 'maps', mp + '.map')
    if 'successfully built' not in (r.stdout or ''):
        text = (r.stdout or '') + (r.stderr or '')
        if 'actor_palette_block' in text:
            # tool APPENDS every child scenario's Actor Palette to the parent's, no
            # de-duplication, and the merged block holds 64. c20/d20's _cinema children
            # carry an unused near-copy of the palette (0 encounters) -- empty it.
            return None, ('build failed: Actor Palette over 64 entries. The build adds each '
                          'child scenario\'s palette (e.g. levels\\%s\\%s_cinema) to this '
                          'one -- empty the unused child palette in Guerilla.' % (mp, mp))
        tail = [l for l in text.strip().splitlines() if l.strip() and '?????' not in l][-6:]
        return None, 'build failed:\n      ' + '\n      '.join(tail)
    if not os.path.isfile(out) or os.path.getmtime(out) < t0 - 2:
        return None, 'tool reported success but %s is not fresh' % out
    return out, '%.0fs' % (time.time() - t0)


def check(path, allow_missing_slots=False):
    m = halo_patch.open_map(path, 'Halo 1')
    slots = len(m.find_tags('actv', SLOTS))
    sprint = bool(m.find_tags('weap', halo_patch._SPRINT_WEAP))
    saw = bool(m.find_tags('weap', SAW))
    note = '%2d slots, sprint %s, SAW %s' % (slots, 'yes' if sprint else 'NO',
                                             'yes' if saw else 'no')
    problem = None
    if not sprint:
        problem = 'no sprint weapon -- not a toolkit scenario?'
    elif slots < SLOT_COUNT and not allow_missing_slots:
        problem = ('%d of %d enemy-weapon slots -- add the rest to the Actor Palette in '
                   'Guerilla (or ship anyway with --allow-missing-slots)' % (slots, SLOT_COUNT))
    return note, problem


def ship(mp, built, root):
    live = os.path.join(LIVE, mp + '.map')
    base = halo_patch.baseline_path(live, root or None, SUBDIR)
    if os.path.exists(base):
        os.makedirs(PREVIOUS, exist_ok=True)
        shutil.copy2(base, os.path.join(PREVIOUS, mp + '.map'))
    os.makedirs(os.path.dirname(base), exist_ok=True)
    shutil.copy2(built, base)
    shutil.copy2(built, live)
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', default='', help='comma list; default all 10')
    ap.add_argument('--no-ship', action='store_true', help='build and check only')
    ap.add_argument('--allow-missing-slots', action='store_true',
                    help='ship a level with fewer than 20 enemy-weapon slots')
    a = ap.parse_args()
    maps = [x.strip() for x in a.maps.split(',') if x.strip()] or MAPS

    root = baseline_root()
    if root and not os.path.isdir(os.path.splitdrive(root)[0] + os.sep):
        sys.exit('Baselines folder %s is on a drive that is not connected.' % root)
    if not a.no_ship and steam_update_pending():
        sys.exit('A Steam update of MCC is pending -- it would delete the shipped maps. '
                 'Let it finish first.')
    install_script.install(paths.GLOBAL_SCRIPTS)
    print('Building %d level(s), classic, self-contained. Baselines: %s'
          % (len(maps), root or 'sibling .bak files'))

    ok, failed = [], []
    for mp in maps:
        print('\n[%s] building...' % mp, flush=True)
        built, msg = build(mp)
        if not built:
            print('  FAILED', msg)
            failed.append(mp)
            continue
        note, problem = check(built, a.allow_missing_slots)
        print('  built in %s -- %s' % (msg, note))
        if problem:
            print('  NOT SHIPPED:', problem)
            failed.append(mp)
            continue
        if not a.no_ship:
            base = ship(mp, built, root)
            print('  shipped -> %s and halo1\\maps' % base)
        ok.append(mp)

    print('\nDONE: %d ok (%s), %d failed (%s)' % (len(ok), ' '.join(ok) or '-',
                                                 len(failed), ' '.join(failed) or '-'))
    if not a.no_ship and ok:
        print('Previous baselines kept in %s. Patch a run in the enhancer to apply it '
              'on top of the new maps.' % PREVIOUS)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
