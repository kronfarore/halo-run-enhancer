r"""Preflight for the Halo 2 ONLINE co-op ability test -- run on BOTH machines.

The co-op test has been wasted twice, both times on SETUP rather than on the mechanism:
  * a rebuild resets the deployed map's globals, so `ability0`/`ability1` go back to 0
    and there is nothing to fire (happened 2026-08-21 and again 2026-08-26);
  * by 2026-09-21 `halo2.dll` had gone missing altogether, so the hijacked verb was
    stock and BOTH players were inert -- which in game looks exactly like "the patch
    does not work", and is not evidence about it at all.

Neither failure shows itself in game: every one of them is a silent no-op. So check
here before booting, on each machine, and compare the two md5s ACROSS machines --
online co-op runs the scripts on both, so a mismatch means the halves disagree.

    python h2_coop_preflight.py                  # full report
    python h2_coop_preflight.py --map 03a_oldmombasa
    python h2_coop_preflight.py --fix-dll        # restore the patched dll (MCC closed)

Exit code is 0 only when every check passes.
"""
import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MCC = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection')
H2 = os.path.join(MCC, 'halo2')
DLL = os.path.join(H2, 'halo2.dll')
MAPS = os.path.join(H2, 'h2_maps_win64_dx11')

# The predicate of unit_get_enterable_by_player, file offset 0x93ED10. Comparing these
# bytes rather than a whole-file hash means an unrelated later patch elsewhere in the
# dll does not read as a failure here.
PRED = 0x93ED10
STOCK = '4883ec2883f9ff7439488b05787af700488b50'
PATCHED = '4883ec2883f9ff7440488b05787af700488b50'
OLD = '488b05b947ca008b80bc000000c1e8142401c3'

ABILITY = {0: 'none', 1: 'sprint', 2: 'overshield', 3: 'camo', 4: 'regeneration'}
# Only abilities that WRITE UNIT STATE replicate online. The others create objects or
# grant equipment, and script-created objects stay on the machine that made them --
# see the H2 online co-op script model.
OBJECT_FREE = {2, 4}


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def mcc_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    return 'mcc-win64-shipping' in out or 'mccwinstore' in out


def _pred_of(path):
    try:
        with open(path, 'rb') as f:
            f.seek(PRED)
            return f.read(19).hex()
    except OSError:
        return None


def _patched_backups():
    return [f for f in sorted(os.listdir(H2))
            if f.startswith('halo2.dll.') and _pred_of(os.path.join(H2, f)) == PATCHED]


def _restore(src):
    if mcc_running():
        print('  FAIL  MCC is RUNNING -- close it fully; the dll is locked while it runs')
        return False
    shutil.copyfile(src, DLL)
    print('  FIXED restored from %s' % os.path.basename(src))
    print('        md5 %s' % md5(DLL))
    print('        MCC must be fully RESTARTED -- the dll is mapped at process start,')
    print('        so reloading a level is not enough')
    return True


def check_dll(fix=False):
    print('halo2.dll')
    state = _pred_of(DLL) if os.path.isfile(DLL) else None
    if state == PATCHED:
        print('  ok    per-player-flashlight applied')
        print('  md5   %s' % md5(DLL))
        return True
    if state is None:
        print('  FAIL  MISSING entirely -- Halo 2 cannot even launch')
    elif state == STOCK:
        print('  FAIL  VANILLA -- the hijacked verb is stock, so BOTH players are inert')
    elif state == OLD:
        print('  FAIL  the superseded p2-vision-trigger -- player 2 is inert online')
    else:
        print('  FAIL  unrecognised bytes at 0x%X: %s' % (PRED, state))
    cands = _patched_backups()
    if cands:
        print('        patched backup available: %s' % ', '.join(cands))
        if fix:
            return _restore(os.path.join(H2, cands[0]))
        print('        re-run with --fix-dll (MCC closed), or h2_dll_patch.py --apply')
    else:
        print('        no patched backup here; apply h2_dll_patch.py --apply '
              'per-player-flashlight')
    return False


def _check_sprint_tags(path):
    """Sprint needs the TAG side too. Setting ability=1 alone hands the player an
    invisible weapon and changes nothing -- in game that is indistinguishable from the
    trigger never firing, which is exactly the kind of false negative this file exists
    to stop."""
    import h2_sprint
    import halo_patch as hp
    m = hp.open_map(path, 'Halo 2')
    scnr = hp._scnr_base(m)
    names = [n for _, _, n in h2_sprint._profiles(m, scnr)]
    profile = getattr(h2_sprint, 'SPRINT_PROFILE', 'ab_sprint')
    tok = [t for t in m.tags
           if t['class'] == 'weap' and t['name'] == h2_sprint.TOKEN]
    good = True
    if profile not in names:
        print('  FAIL  no %r starting profile -- rebuild with h2_batch.py' % profile)
        good = False
    if not tok:
        print('  FAIL  token weapon not in the map')
        good = False
    if good:
        fwd = struct.unpack_from('<f', m.data,
                                 tok[0]['base'] + h2_sprint.FWD_PENALTY)[0]
        if fwd >= 0:
            print('  FAIL  token forward penalty %.3f -- no speed bonus. Run:' % fwd)
            print('        h2_sprint.py "<map>" --mult 1.5 --profile %s' % profile)
            good = False
        else:
            print('  ok    sprint tags: %s profile, token present, forward %.3f'
                  % (profile, fwd))
    return good


def check_map(level):
    import halo_patch as hp
    path = os.path.join(MAPS, level + '.map')
    print('\n%s.map' % level)
    if not os.path.isfile(path):
        print('  FAIL  not deployed')
        return False
    m = hp.open_map(path, 'Halo 2')
    get = lambda k: hp.read_global(m, k)
    if get('fp0') is None or get('fp1') is None:
        kind = ('the OLD shared-ability script' if get('ab_kind') is not None
                else 'VANILLA (no ability script at all)')
        print('  FAIL  %s -- rebuild with h2_batch.py' % kind)
        return False
    print('  ok    edge-detecting per-player script (fp0/fp1 present)')

    a0, a1 = get('ability0'), get('ability1')
    ok = True
    for who, a in (('player 1 (ability0)', a0), ('player 2 (ability1)', a1)):
        if not a:
            print('  FAIL  %s = none. A REBUILD RESETS THIS -- re-run h2_tune.py' % who)
            ok = False
        else:
            warn = ('' if a in OBJECT_FREE else
                    '  <- creates objects; may not replicate online')
            print('  ok    %s = %s%s' % (who, ABILITY.get(a, a), warn))
    if ok and a0 == a1:
        print('  WARN  both players have the SAME ability -- use different ones or the')
        print('        test cannot tell whose trigger fired')
    if 1 in (a0 or 0, a1 or 0):
        ok = _check_sprint_tags(path) and ok
    print('  md5   %s' % md5(path))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', default='01b_spacestation')
    ap.add_argument('--fix-dll', action='store_true')
    a = ap.parse_args(argv)
    dll_ok = check_dll(a.fix_dll)
    map_ok = check_map(a.map)
    ok = dll_ok and map_ok
    print('')
    if ok:
        print('ALL CHECKS PASSED. Both machines must print the SAME two md5s.')
    else:
        print('NOT READY -- fix the FAILs above before booting.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
