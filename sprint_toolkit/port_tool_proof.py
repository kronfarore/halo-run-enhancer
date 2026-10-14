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
  It CANNOT run across a wave whose port CONFIGS gained keys the old tools do not know (wave B,
  2026-10-14: the beam recipe / ground points -- the old model tool crashed on the Spartan Laser).
  Then THE REPRODUCTION CHECK is the wave check: today's tools regenerate every step of every
  DONE port and must reproduce the kit exactly (diff pre / new), then the kit is restored:
    python port_tool_proof.py --reproduce --backup h1_wave_<x>_reproduce_<date> --tag wBr
ANY FAILURE after the backup restores the kit to <tag>_pre and proves it (wB left 108 files of
old-tool output behind before this, recovered by hand).

WITH BUSY (`--with-busy`, opt-in, user 2026-10-13): the ports IN PROGRESS (the other parallel
session's) are left out above, so a shared-tool change met them only at the wave's --full. This
adds the same narrowed steps for them, old tools vs new, in TWO SCRATCH KITS
(`F:\...\common\_proof_<tag>_busy\{old,new}`: the ROOTS copied, the rest junctioned, the
toolkit copies' kit path rewritten -- a kit path the rewrite does not know refuses the run), so
the real kit and the other session's files are never written; removed after. A port that fails
to regenerate is reported (with one side's tools only: the change broke or fixed it).
`--busy-only` skips the done ports' proof (no --backup); `--busy-also <keys>` checks done ports
the busy way too. The scratch copy costs ~10 minutes (629 s measured, robocopy).

    python port_tool_proof.py --rev <rev> --tools <changed> --backup <b> --tag <t> --with-busy
    python port_tool_proof.py --rev <rev> --tools <changed> --tag <t> --busy-only

~20 minutes full (two regens of every step), a few minutes narrowed.
A reticle-only change (h1_add_reticle) is proven faster by h1_reticle_proof.py.
"""
import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit_lock  # noqa: E402
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
    return r


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


#: the kit path as the chain tools spell it -> the scratch kit (rewrite_kit)
KIT_SPELLINGS = (re.compile(r"os\.path\.join\('F:' \+ (?:os\.sep|B), 'SteamLibrary', 'steamapps', "
                            r"'common', 'HCEEK'"),
                 re.compile(r"""r(['"])F:\\SteamLibrary\\steamapps\\common\\HCEEK"""))
#: a kit path the rewrite missed (checked on every file the chain imports + the configs)
KIT_LEFT = re.compile(r"""'common', 'HCEEK'|common\\HCEEK|STEAM, 'HCEEK'|'HCEEK', 'tags'""")


#: sprint_toolkit\out folders the chain WRITES (h1_port_sounds WORK, h1_fp_retarget / reach_tags
#: export caches): each scratch side gets its own copy -- the other session's port works there
OUT_WORK = ('h3_sounds', 'h3_export', 'reach_export')


def _copytree(src, dst):
    """A folder copy for the scratch, multi-threaded (robocopy /MT: shutil took 12 minutes for
    the kit ROOTS twice); robocopy exit codes below 8 are success."""
    r = subprocess.run(['robocopy', src, dst, '/E', '/COPY:DAT', '/DCOPY:T', '/MT:16', '/R:2', '/W:1',
                        '/NFL', '/NDL', '/NJH', '/NJS', '/NP'], capture_output=True, text=True,
                       errors='replace')
    if r.returncode >= 8:
        raise SystemExit('robocopy %s -> %s failed (%d): %s' % (src, dst, r.returncode,
                                                               r.stdout[-1500:]))


def _junction(link, target):
    subprocess.run(['cmd', '/c', 'mklink', '/J', link, target], capture_output=True, check=True)


def drop_tree(d):
    """Remove a scratch tree: every junction in it UNLINKED first, never followed."""
    if not os.path.exists(d):
        return
    for root, dirs, _fs in os.walk(d, topdown=True):
        keep = []
        for x in dirs:
            p = os.path.join(root, x)
            if os.path.isjunction(p):
                os.rmdir(p)
            else:
                keep.append(x)
        dirs[:] = keep
    shutil.rmtree(d)


def _is_root(p):
    return os.path.normcase(p) in {os.path.normcase(r) for r in ps.ROOTS}


def scratch_side(side, src):
    """One side (old / new) of the --with-busy scratch, laid out like the MCC folder so every
    tool's own path arithmetic holds: <side>\\HCEEK (the proof's ROOTS copied -- from `src`, the
    old side, for new: both start identical whatever the other session writes meanwhile --
    everything else of the kit junctioned, small top-level files copied for tool.exe),
    <side>\\tool (top-level files copied, port_sounds\\halo1 copied, sprint_toolkit copied as
    old_toolkit does, every other folder junctioned) and junctions to the MCC game folders
    (h1_port_sounds reads the source banks two levels above the toolkit)."""
    kit = os.path.join(side, 'HCEEK')
    tool = os.path.join(side, 'tool')
    os.makedirs(kit)
    src_kit = os.path.join(src, 'HCEEK') if src else ps.HCEEK
    src_tool = os.path.join(src, 'tool') if src else ps.TOOL
    for f in os.listdir(ps.HCEEK):
        p = os.path.join(ps.HCEEK, f)
        if f in ('tags', 'data'):
            os.makedirs(os.path.join(kit, f))
            for sub in os.listdir(p):
                sp = os.path.join(p, sub)
                if _is_root(sp):
                    _copytree(os.path.join(src_kit, f, sub), os.path.join(kit, f, sub))
                elif os.path.isdir(sp):
                    _junction(os.path.join(kit, f, sub), sp)
                else:
                    shutil.copy2(sp, os.path.join(kit, f, sub))
        elif os.path.isdir(p):
            _junction(os.path.join(kit, f), p)
        elif os.path.getsize(p) < 64 * 1024 * 1024 and f != os.path.basename(kit_lock.LOCK):
            shutil.copy2(p, os.path.join(kit, f))
    mcc = os.path.dirname(ps.TOOL)
    for f in os.listdir(mcc):
        if f != 'tool' and os.path.isdir(os.path.join(mcc, f)):
            _junction(os.path.join(side, f), os.path.join(mcc, f))
    os.makedirs(tool)
    for f in os.listdir(ps.TOOL):
        p = os.path.join(ps.TOOL, f)
        if f.startswith('_proof_') or f == 'sprint_toolkit':
            continue
        if os.path.isfile(p):
            shutil.copy2(os.path.join(src_tool, f), os.path.join(tool, f))
        elif f == 'port_sounds':
            os.makedirs(os.path.join(tool, f))
            for sub in os.listdir(p):
                if sub == 'halo1':
                    _copytree(os.path.join(src_tool, f, sub), os.path.join(tool, f, sub))
                else:
                    _junction(os.path.join(tool, f, sub), os.path.join(p, sub))
        else:
            _junction(os.path.join(tool, f), p)
    kt = os.path.join(tool, 'sprint_toolkit')
    os.makedirs(kt)
    src_kt = os.path.join(src_tool, 'sprint_toolkit') if src else HERE
    for f in os.listdir(HERE):
        p = os.path.join(HERE, f)
        if os.path.isfile(p) and os.path.getsize(p) < 5 * 1024 * 1024:
            shutil.copy2(os.path.join(src_kt, f), os.path.join(kt, f))
        elif os.path.isdir(p) and f == 'ports_h1':
            shutil.copytree(os.path.join(src_kt, f), os.path.join(kt, f),
                            ignore=shutil.ignore_patterns('__pycache__'))
        elif f == 'out':                         # the chain's work folders its own, the rest shared
            os.makedirs(os.path.join(kt, f))
            for sub in os.listdir(p):
                if sub in OUT_WORK and os.path.isdir(os.path.join(p, sub)):
                    _copytree(os.path.join(src_kt, f, sub), os.path.join(kt, f, sub))
                elif os.path.isdir(os.path.join(p, sub)):
                    _junction(os.path.join(kt, f, sub), os.path.join(p, sub))
        elif os.path.isdir(p) and f != '__pycache__':
            _junction(os.path.join(kt, f), p)
    return kit, kt


def rewrite_kit(kt, kit, uses):
    """Point the scratch toolkit `kt` at the scratch kit: every .py's kit path rewritten,
    kit_lock.py excepted (the lock stays the real one -- the proof holds it). A kit path left
    in a file the chain imports (`uses`) or in a config refuses the run."""
    left = []
    for d in (kt, os.path.join(kt, 'ports_h1')):
        for f in os.listdir(d):
            if not f.endswith('.py') or f == 'kit_lock.py':
                continue
            p = os.path.join(d, f)
            s = open(p, encoding='utf-8', errors='surrogateescape', newline='').read()
            t = KIT_SPELLINGS[0].sub(lambda m: 'os.path.join(%r' % kit, s)
            t = KIT_SPELLINGS[1].sub(lambda m: 'r' + m.group(1) + kit, t)
            if t != s:
                open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='').write(t)
            if d != kt or f in uses or f == 'port_sha_snapshot.py':
                left += ['%s:%d' % (f, i + 1) for i, line in enumerate(t.splitlines())
                         if KIT_LEFT.search(line.split('#')[0])]
    if left:
        raise SystemExit('--with-busy: a kit path the scratch rewrite does not know, in %s -- '
                         'the chain would write the REAL kit; not run' % ', '.join(left))


def busy_check(a, keys, steps, uses):
    """--with-busy: the narrowed chain over `keys` (the ports in progress) in TWO scratch kits,
    old tools vs new, never the real kit (the other session is writing its port there)."""
    root = os.path.join(os.path.dirname(ps.HCEEK), '_proof_%s_busy' % a.tag)
    drop_tree(root)
    old, new = os.path.join(root, 'old'), os.path.join(root, 'new')
    print('busy scratch: %s (copying)' % root, flush=True)
    t = time.time()
    failed = {}
    try:
        kit_o, kt_o = scratch_side(old, None)
        kit_n, kt_n = scratch_side(new, old)
        print('  copied in %.0fs' % (time.time() - t), flush=True)
        for tl in a.tools:                       # the OLD tools on the old side only
            blob = subprocess.run(['git', 'show', '%s:sprint_toolkit/%s' % (a.rev, tl)], cwd=HERE,
                                  capture_output=True).stdout
            if not blob:
                raise SystemExit('%s not in %s' % (tl, a.rev))
            open(os.path.join(kt_o, tl), 'wb').write(blob)
        allu = set().union(*uses.values())
        rewrite_kit(kt_o, kit_o, allu)
        rewrite_kit(kt_n, kit_n, allu)
        for side, kit, kt in (('old', kit_o, kt_o), ('new', kit_n, kt_n)):
            os.environ[ps.SCRATCH_ENV] = kit
            try:
                for k in keys:                   # one at a time: a half-built port may fail
                    r = run('port_sha_snapshot.py', 'regen', '--busy', '--steps', ','.join(steps), k,
                            cwd=kt, ok=(0, 1))
                    if r.returncode:
                        failed.setdefault(k, []).append(side)
                name = '%s_busy%s' % (a.tag, side)
                run('port_sha_snapshot.py', 'snap', '--busy', name, cwd=kt)
                for f in ('sha_%s.json' % name, 'sha_%s.meta.json' % name):   # to the real out
                    shutil.copy2(os.path.join(kt, 'out', f), os.path.join(ps.OUT, f))
            finally:
                del os.environ[ps.SCRATCH_ENV]
    finally:
        drop_tree(root)
    for k, sides in sorted(failed.items()):
        print('BUSY REGEN FAILED %s with the %s tools%s' % (k, ' and '.join(sides),
              ' -- the change broke (or fixed) it' if len(sides) == 1 else
              ' -- half-built, or broken before the change: not compared'))
    run('port_sha_snapshot.py', 'diff', a.tag + '_busyold', a.tag + '_busynew', ok=(0, 1))
    unproven(a.tag + '_busyold', a.tag + '_busynew', keys, steps)
    print('BUSY CHECK DONE (%s; scratch removed) -- read the diff above' % ', '.join(keys))


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
    ap.add_argument('--rev', help='git revision holding the OLD tools (not with --reproduce)')
    ap.add_argument('--reproduce', action='store_true',
                    help='THE WAVE CHECK: every step of every done port with TODAY\'s tools must '
                         'reproduce the kit exactly (no old tools; implies --full)')
    ap.add_argument('--tools', nargs='+', help='changed tools (sprint_toolkit file names); --full: '
                    'default every chain tool changed since --rev')
    ap.add_argument('--full', action='store_true', help='every step of every port (the wave check)')
    ap.add_argument('--backup', help=r'E:\HaloBackups\<this> (must not exist; not with --busy-only)')
    ap.add_argument('--tag', required=True, help='snapshot name prefix')
    ap.add_argument('--exclude', nargs='*', default=[], help='config keys left out of the regen')
    ap.add_argument('--with-busy', action='store_true', help='also the ports IN PROGRESS, old vs '
                    'new tools, in two scratch kits (never the real kit)')
    ap.add_argument('--busy-only', action='store_true', help='only the --with-busy check (the '
                    'done ports\' proof already ran): no backup, the real kit untouched')
    ap.add_argument('--busy-also', nargs='*', default=[], help='--with-busy: done ports checked '
                    'the busy way too (a test of the scratch, or one port\'s check alone)')
    a = ap.parse_args()
    if a.reproduce:
        if a.with_busy or a.busy_only or a.busy_also:
            ap.error('--reproduce compares the kit with itself: no --with-busy')
        a.full = True
        a.tools = a.tools or ['(none: --reproduce)']
    elif not a.rev:
        ap.error('--rev is required (but with --reproduce)')
    if a.busy_only or a.busy_also:
        a.with_busy = True
    if not a.busy_only and not a.backup:
        ap.error('--backup is required (but with --busy-only)')
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
    busy_keys = sorted(set(busy) | (set(a.busy_also) & secs))
    if a.with_busy and not busy_keys:
        print('--with-busy: no port in progress has a chain section -- nothing for the busy check')
    if a.busy_only:
        if busy_keys:
            busy_check(a, busy_keys, steps, uses)
        return
    regen_args = ('regen', '--steps', ','.join(steps)) + tuple(keys)
    dest = os.path.join('E:' + os.sep, 'HaloBackups', a.backup)
    backup(dest)
    run('port_sha_snapshot.py', 'snap', a.tag + '_pre')
    try:
        if a.reproduce:
            # THE REPRODUCTION CHECK (the wave check, 2026-10-14): today's tools + today's
            # configs must regenerate the kit EXACTLY as it is. Old tools vs new cannot run
            # across a wave whose CONFIGS gained keys the old tools do not know (wave B: the
            # beam recipe on the Spartan Laser, ground points everywhere -- wB crashed on
            # the Spartan Laser's model step); this catches what the narrowed proofs could
            # miss (a later step reading an earlier step's changed output, a hand edit).
            run('port_sha_snapshot.py', *regen_args)
            run('port_sha_snapshot.py', 'snap', a.tag + '_new')
            run('port_sha_snapshot.py', 'diff', a.tag + '_pre', a.tag + '_new', ok=(0, 1))
        else:
            # the OLD tools run from a temporary COPY of the toolkit, never written over the
            # working copy: a second port session may be running these very scripts
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
    except BaseException:
        # a regen that FAILS halfway leaves the kit part-regenerated (wB, 2026-10-14: 108 files
        # of old-tool output left behind) -- put the pre state back before giving up
        print('PROOF FAILED -- restoring the kit to %s_pre from %s' % (a.tag, dest), flush=True)
        run('port_sha_snapshot.py', 'snap', a.tag + '_abort')
        run('port_sha_snapshot.py', 'restore', a.tag + '_pre', a.tag + '_abort', dest)
        run('port_sha_snapshot.py', 'snap', a.tag + '_restored')
        run('port_sha_snapshot.py', 'diff', a.tag + '_pre', a.tag + '_restored')
        raise
    run('port_sha_snapshot.py', 'restore', a.tag + '_pre', a.tag + '_new', dest)
    run('port_sha_snapshot.py', 'snap', a.tag + '_restored')
    run('port_sha_snapshot.py', 'diff', a.tag + '_pre', a.tag + '_restored')
    print('PROOF DONE -- read the old/new diff above; the restore diff must say 0 changed')
    if a.with_busy and busy_keys:
        busy_check(a, busy_keys, steps, uses)


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('port_tool_proof'):
        main()
