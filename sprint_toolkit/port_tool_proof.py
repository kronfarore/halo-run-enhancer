r"""THE WHOLE BYTE-IDENTICAL PROOF for a shared-tool change, in one run (the Needle Rifle,
wave B2, 2026-10-10/11: run twice; port_sha_snapshot.py's steps, automated):

  1. back up every file the pipeline writes (port_sha_snapshot.ROOTS) to E:\HaloBackups\<name>
  2. snap <tag>_pre
  3. the changed tools put back to their state at git revision --rev, regen (the wave-A --write
     chain for every built port), snap <tag>_old; the working-copy tools restored (always)
  4. regen with the working-copy tools, snap <tag>_new
  5. diff old new -- the PROOF (only BITMAP header lines allowed; an FP animation tag reported
     CHANGED is checked with h1_antr_diff.py, the known content-equal noise)
  6. restore pre from the backup, snap <tag>_restored, diff pre restored (must be 0)

    python port_tool_proof.py --rev 1550381 --tools h1_h3_weapon_model.py h1_pickable_weapons.py \
        --backup h1_<port>_presnap_<date> --tag nr2 [--exclude needle_rifle]

The port being built (--exclude, default: none) stays out of the regen: the proof is about the
ports built BEFORE the change. Never run another --write while it runs (the kit is rewritten,
then restored). Takes ~20 minutes (two regens of every port).
A reticle-only change (h1_add_reticle) is proven faster by h1_reticle_proof.py.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_sha_snapshot as ps  # noqa: E402
import ports_h1  # noqa: E402


def run(*cmd, ok=(0,)):
    print('>', ' '.join(cmd), flush=True)
    t = time.time()
    r = subprocess.run([sys.executable] + list(cmd), cwd=HERE, capture_output=True, text=True, errors='replace')
    print(r.stdout[-3000:], r.stderr[-3000:], 'rc', r.returncode, '%.0fs' % (time.time() - t), flush=True)
    if r.returncode not in ok:
        raise SystemExit('failed: %s' % ' '.join(cmd))


def backup(dest):
    if os.path.exists(dest):
        raise SystemExit('backup exists: ' + dest)
    for r in ps.ROOTS:
        if r.startswith(ps.HCEEK):
            dst = os.path.join(dest, os.path.relpath(r, ps.HCEEK))     # tags\weapons, data\sound ...
        elif r.endswith('halo1'):
            dst = os.path.join(dest, 'tool', 'halo1')
        else:
            dst = os.path.join(dest, 'tool', os.path.basename(r))
        print('backup', r, '->', dst, flush=True)
        if os.path.isdir(r):
            shutil.copytree(r, dst)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(r, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rev', required=True, help='git revision holding the OLD tools')
    ap.add_argument('--tools', nargs='+', required=True, help='changed tools (sprint_toolkit file names)')
    ap.add_argument('--backup', required=True, help=r'E:\HaloBackups\<this> (must not exist)')
    ap.add_argument('--tag', required=True, help='snapshot name prefix')
    ap.add_argument('--exclude', nargs='*', default=[], help='config keys left out of the regen')
    a = ap.parse_args()
    secs = set()
    for s in ('model', 'retarget', 'sounds', 'pickable'):
        secs |= set(ports_h1.section(s))
    keys = sorted(k for k in secs if k not in a.exclude)
    dest = os.path.join('E:' + os.sep, 'HaloBackups', a.backup)
    backup(dest)
    run('port_sha_snapshot.py', 'snap', a.tag + '_pre')
    new = {t: open(os.path.join(HERE, t), 'rb').read() for t in a.tools}
    try:
        for t in a.tools:
            old = subprocess.run(['git', 'show', '%s:sprint_toolkit/%s' % (a.rev, t)], cwd=HERE,
                                 capture_output=True).stdout
            if not old:
                raise SystemExit('%s not in %s' % (t, a.rev))
            open(os.path.join(HERE, t), 'wb').write(old)
        run('port_sha_snapshot.py', 'regen', *keys)
        run('port_sha_snapshot.py', 'snap', a.tag + '_old')
    finally:
        for t, b in new.items():
            open(os.path.join(HERE, t), 'wb').write(b)
    run('port_sha_snapshot.py', 'regen', *keys)
    run('port_sha_snapshot.py', 'snap', a.tag + '_new')
    run('port_sha_snapshot.py', 'diff', a.tag + '_old', a.tag + '_new', ok=(0, 1))
    run('port_sha_snapshot.py', 'restore', a.tag + '_pre', a.tag + '_new', dest)
    run('port_sha_snapshot.py', 'snap', a.tag + '_restored')
    run('port_sha_snapshot.py', 'diff', a.tag + '_pre', a.tag + '_restored')
    print('PROOF DONE -- read the old/new diff above; the restore diff must say 0 changed')


if __name__ == '__main__':
    main()
