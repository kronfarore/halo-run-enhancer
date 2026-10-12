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
then restored).

NARROWED (default, user 2026-10-12): regen runs only the chain STEPS whose script imports a
changed tool (the import closure, read from the source): a model-tool change regenerates the
models of every port, not their animations / sounds / weapon tags. A later step can still read
an earlier step's OUTPUT (retarget reads the FP gbxmodel's binds, pickable edits the compiled FP
animations): when the narrowed diff shows a port's files changed, its later steps were not
compared -- the proof names them; the wave check covers them.
FULL (`--full`, at the END OF EVERY WAVE, user 2026-10-12): every step of every port, against the
wave's start revision; `--tools` may be left out: every sprint_toolkit tool the chain imports
that changed since --rev (git diff, working copy included) is rolled back.

    python port_tool_proof.py --full --rev <wave start> --backup h1_wave_<x>_check_<date> --tag wB

~20 minutes full (two regens of every step), a few minutes narrowed.
A reticle-only change (h1_add_reticle) is proven faster by h1_reticle_proof.py.
"""
import argparse
import ast
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_sha_snapshot as ps  # noqa: E402
import ports_h1  # noqa: E402


def run(*cmd, ok=(0,), cwd=None):
    print('>', ' '.join(cmd), flush=True)
    t = time.time()
    r = subprocess.run([sys.executable] + list(cmd), cwd=cwd or HERE, capture_output=True, text=True,
                       errors='replace')
    print(r.stdout[-3000:], r.stderr[-3000:], 'rc', r.returncode, '%.0fs' % (time.time() - t), flush=True)
    if r.returncode not in ok:
        raise SystemExit('failed: %s' % ' '.join(cmd))


#: each chain step's script (port_sha_snapshot.STEPS)
SCRIPTS = {'model': 'h1_h3_weapon_model.py', 'retarget': 'h1_fp_retarget.py',
           'sounds': 'h1_port_sounds.py', 'pickable': 'h1_pickable_weapons.py'}
#: later steps that READ an earlier step's output (not its code)
READS = {'model': ('retarget', 'pickable'), 'retarget': ('pickable',), 'sounds': (), 'pickable': ()}
#: the proof's own machinery: never rolled back
SELF = {'port_tool_proof.py', 'port_sha_snapshot.py'}


def closure(script, seen=None):
    """Every sprint_toolkit .py that `script` imports, itself included (transitively)."""
    seen = set() if seen is None else seen
    if script in seen or not os.path.exists(os.path.join(HERE, script)):
        return seen
    seen.add(script)
    for n in ast.walk(ast.parse(open(os.path.join(HERE, script), encoding='utf-8').read())):
        names = ([x.name for x in n.names] if isinstance(n, ast.Import)
                 else [n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        for m in names:
            closure(m.split('.')[0] + '.py', seen)
    return seen


def changed_since(rev):
    """sprint_toolkit/*.py (not ports_h1, not the proof itself) changed since rev, that rev has."""
    r = subprocess.run(['git', 'diff', '--name-only', rev, '--', '.'], cwd=HERE, capture_output=True, text=True)
    out = []
    for f in r.stdout.split():
        f = f.split('sprint_toolkit/', 1)[-1]
        if '/' in f or not f.endswith('.py') or f in SELF:
            continue
        if subprocess.run(['git', 'cat-file', '-e', '%s:sprint_toolkit/%s' % (rev, f)], cwd=HERE,
                          stderr=subprocess.DEVNULL).returncode == 0:
            out.append(f)
    return out


def port_dirs(keys):
    """{port key: lower-case folders its files live under} (model / FP / sound / weapon dirs)."""
    out = {}
    for k in keys:
        ds = set()
        for sec, f in (('model', 'dir'), ('retarget', 'h1_dir'), ('sounds', 'dir'), ('pickable', 'weapon')):
            v = ports_h1.section(sec).get(k, {}).get(f)
            if v:
                ds.add((os.path.dirname(v) if sec == 'pickable' else v).lower())
        out[k] = ds
    return out


def unproven(a, b, keys, steps):
    """Ports whose files changed old -> new while a step that READS them was left out."""
    later = sorted({x for s in steps for x in READS[s]} - set(steps), key=ps.STEPS.index)
    if not later:
        return
    A = ps.json.load(open(os.path.join(ps.OUT, 'sha_%s.json' % a)))
    B = ps.json.load(open(os.path.join(ps.OUT, 'sha_%s.json' % b)))
    ch = [k.lower() for k in set(A) | set(B) if not k.startswith('px:') and A.get(k) != B.get(k)
          and not (k.lower().endswith('.bitmap') and A.get('px:' + k) == B.get('px:' + k))]
    hit = sorted(p for p, ds in port_dirs(keys).items() if any('\\' + d + '\\' in c for d in ds for c in ch))
    if hit:
        print('NOT COMPARED: %s changed in step(s) %s; their later step(s) %s read that output and '
              'were not regenerated -- the wave check (--full) covers them'
              % (', '.join(hit), ', '.join(steps), ', '.join(later)))


def old_toolkit(tag, rev, tools):
    """tool\\_proof_<tag>_toolkit: the toolkit's top-level files + ports_h1 copied, every other
    folder (pylibs, out, assets ...) a JUNCTION to the real one, and `tools` at `rev`. Its
    parent is the tool folder, so every script's paths (ROOT, port_sounds) resolve as usual."""
    dst = os.path.join(os.path.dirname(HERE), '_proof_%s_toolkit' % tag)
    if os.path.exists(dst):
        drop_toolkit(dst)
    os.makedirs(dst)
    for f in os.listdir(HERE):
        p = os.path.join(HERE, f)
        if os.path.isfile(p) and os.path.getsize(p) < 5 * 1024 * 1024:
            shutil.copy2(p, os.path.join(dst, f))
        elif os.path.isdir(p) and f == 'ports_h1':
            shutil.copytree(p, os.path.join(dst, f), ignore=shutil.ignore_patterns('__pycache__'))
        elif os.path.isdir(p) and f != '__pycache__':
            subprocess.run(['cmd', '/c', 'mklink', '/J', os.path.join(dst, f), p],
                           capture_output=True, check=True)
    for t in tools:
        old = subprocess.run(['git', 'show', '%s:sprint_toolkit/%s' % (rev, t)], cwd=HERE,
                             capture_output=True).stdout
        if not old:
            drop_toolkit(dst)
            raise SystemExit('%s not in %s' % (t, rev))
        open(os.path.join(dst, t), 'wb').write(old)
    print('old tools (%s) in %s' % (' '.join(tools), dst), flush=True)
    return dst


def drop_toolkit(dst):
    """Remove the temporary toolkit: junctions UNLINKED first (never followed into the real
    folders)."""
    for f in os.listdir(dst):
        p = os.path.join(dst, f)
        if os.path.isjunction(p):
            os.rmdir(p)
    shutil.rmtree(dst)


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
    ap.add_argument('--tools', nargs='+', help='changed tools (sprint_toolkit file names); --full: '
                    'default every chain tool changed since --rev')
    ap.add_argument('--full', action='store_true', help='every step of every port (the wave check)')
    ap.add_argument('--backup', required=True, help=r'E:\HaloBackups\<this> (must not exist)')
    ap.add_argument('--tag', required=True, help='snapshot name prefix')
    ap.add_argument('--exclude', nargs='*', default=[], help='config keys left out of the regen')
    a = ap.parse_args()
    secs = set()
    for s in ('model', 'retarget', 'sounds', 'pickable'):
        secs |= set(ports_h1.section(s))
    done = {k for k, p in ports_h1.all_ports() if p.get('status') == 'done'}
    keys = sorted(k for k in secs if k not in a.exclude and k in done)
    busy = sorted(k for k in secs if k not in a.exclude and k not in done)
    if busy:
        print('not in the proof (not done -- another session may be on them): %s' % ', '.join(busy))
    uses = {st: closure(SCRIPTS[st]) for st in ps.STEPS}
    if not a.tools:
        if not a.full:
            raise SystemExit('--tools is required without --full')
        a.tools = sorted(t for t in changed_since(a.rev) if any(t in u for u in uses.values()))
        print('tools changed since %s: %s' % (a.rev, ' '.join(a.tools) or '(none)'))
    if set(a.tools) & SELF:
        raise SystemExit('the proof cannot roll itself back: %s' % ' '.join(set(a.tools) & SELF))
    steps = list(ps.STEPS) if a.full else [st for st in ps.STEPS if set(a.tools) & uses[st]]
    if not steps:
        raise SystemExit('no chain step imports %s: nothing for this proof to compare' % ' '.join(a.tools))
    print('steps: %s%s' % (', '.join(steps), ' (full)' if a.full else ''), flush=True)
    regen_args = ('regen', '--steps', ','.join(steps)) + tuple(keys)
    dest = os.path.join('E:' + os.sep, 'HaloBackups', a.backup)
    backup(dest)
    run('port_sha_snapshot.py', 'snap', a.tag + '_pre')
    # the OLD tools run from a temporary COPY of the toolkit, never written over the working
    # copy: a second port session may be running these very scripts (H1_PORT_PLAN.md, parallel)
    copy = old_toolkit(a.tag, a.rev, a.tools)
    try:
        run('port_sha_snapshot.py', *regen_args, cwd=copy)
        run('port_sha_snapshot.py', 'snap', a.tag + '_old')
    finally:
        drop_toolkit(copy)
    run('port_sha_snapshot.py', *regen_args)
    run('port_sha_snapshot.py', 'snap', a.tag + '_new')
    run('port_sha_snapshot.py', 'diff', a.tag + '_old', a.tag + '_new', ok=(0, 1))
    unproven(a.tag + '_old', a.tag + '_new', keys, steps)
    run('port_sha_snapshot.py', 'restore', a.tag + '_pre', a.tag + '_new', dest)
    run('port_sha_snapshot.py', 'snap', a.tag + '_restored')
    run('port_sha_snapshot.py', 'diff', a.tag + '_pre', a.tag + '_restored')
    print('PROOF DONE -- read the old/new diff above; the restore diff must say 0 changed')


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('port_tool_proof'):
        main()
