r"""Prove the Halo 2 port tools regenerate the DONE ports byte-identically (H2_PORT_PLAN.md 0.2 / 0.6).

Every step of the pipeline is run twice from the same kit state -- the OLD tools, then the NEW
ones -- with a SHA-1 snapshot of every H2EK file the pipeline writes after each run
(h2_port_snapshot.py; ports not 'done' and the size-test stand-ins are never touched), and the
kit is put back from a backup between and after:

    pre  -> OLD run -> snap old -> restore pre -> NEW run -> snap new -> restore pre -> snap end
    reported: old vs new (the tool change), pre vs new (what regenerating changes against what
    is shipped), pre vs end (must be 0: the kit restored exactly)

    python h2_port_tool_proof.py --tag p2 --rev <commit before the change> [--steps meter,reticle]
                                 [--keys saw,assault_rifle]

OLD tools = the toolkit as it was at --rev: its sprint_toolkit\*.py and ports_h2\ are extracted
(git archive) to tool\_proof_<tag>_toolkit\sprint_toolkit and the same commands run from there
(each script puts its own folder first on sys.path, so every module it imports is the old one);
removed after. NEW = the working copy. The narrowed proof for a change to a shared tool: --steps
naming the steps that use it. --rev HEAD with no change is a pure noise run.

tool's own outputs (bitmaps, render / collision models) differ run to run in the header checksum
and the import stamps: check a CHANGED one with h2_tool_noise_check.py (pixels + tool's XML).

Phase 0's proof (sawp1, 2026-10-20) ran the SAW's ORIGINAL h2_saw_*.py bodies on the OLD side
(git 39487c0; those names are wrappers since): H2_PORT_PLAN 0.2. Not run by any proof: h2_anim_retime
(a re-run resamples an already-retimed graph through tool, which can truncate a tag -- PORTING
"Retiming"); h2_saw_yardstick (a guarded one-time move).
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit_lock  # noqa: E402
import h2_port_snapshot as S  # noqa: E402

PY = sys.executable
H2EK = S.H2EK

#: step -> commands; {key} is the port
STEPS = [
    ('geometry', [['h2_port_geometry.py', '{key}']]),
    ('render', [['h2_port_geometry.py', '{key}', '--only=none', '--render']]),
    ('textures', [['h2_port_textures.py', '{key}']]),
    ('weapon', [['h2_port_weapon.py', '{key}']]),
    ('numbers', [['h2_port_numbers.py', '{key}']]),
    ('collision', [['h2_port_collision.py', '{key}', '--write']]),
    ('meter', [['h2_port_meter.py', '{key}']]),
    ('hud_plate', [['h2_port_hud_plate.py', '{key}', '--write']]),
    ('reticle', [['h2_port_reticle.py', '{key}', '--write']]),
    ('scope', [['h2_port_scope.py', '{key}', '--write']]),
    ('glyph', [['h2_port_glyph.py', '{key}', '--write']]),
    ('messages', [['h2_port_messages.py', '{key}', '--write', '--repoint']]),
    ('animations', [['h2_port_animations.py', '{key}']]),
    ('sounds', [['h2_port_sounds.py', '{key}', '--write']]),
    ('catalog', [['make_port_catalog_h2.py', '{key}', '--write']]),
]


def extract(rev, tag):
    """The toolkit at `rev` -> tool\\_proof_<tag>_toolkit\\sprint_toolkit (scripts + configs)."""
    root = os.path.join(TOOL, '_proof_%s_toolkit' % tag)
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)
    names = subprocess.run(['git', '-C', TOOL, 'ls-tree', '-r', '--name-only', rev, 'sprint_toolkit'],
                           capture_output=True, text=True, check=True).stdout.split('\n')
    want = [n for n in names if n.endswith(('.py', '.json')) and '/pylibs/' not in n]
    for n in want:
        data = subprocess.run(['git', '-C', TOOL, 'show', '%s:%s' % (rev, n)], capture_output=True,
                              check=True).stdout
        out = os.path.join(root, *n.split('/'))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'wb').write(data)
    print('old toolkit at %s: %d files -> %s' % (rev, len(want), root), flush=True)
    return os.path.join(root, 'sprint_toolkit')


def run(cmd, here, log):
    full = [PY, os.path.join(here, cmd[0])] + cmd[1:]
    # the REAL toolkit last on the path, for what the old copy does not carry (pylibs, out\)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([here, os.path.dirname(here), HERE, TOOL]))
    t0 = time.time()
    p = subprocess.run(full, cwd=here, capture_output=True, text=True, errors='replace', env=env)
    out = (p.stdout or '') + (p.stderr or '')
    log.write('\n$ [%s] %s   (exit %d, %.0f s)\n%s\n' % (here, ' '.join(cmd), p.returncode,
                                                         time.time() - t0, out))
    log.flush()
    return p.returncode, out


def side(name, steps, keys, here, log):
    for step, cmds in STEPS:
        if steps and step not in steps:
            continue
        for k in keys:
            for cmd in cmds:
                rc, out = run([c.replace('{key}', k) for c in cmd], here, log)
                tail = ' '.join(out.split())[-110:]
                print('   %-4s %-10s %-14s exit %d  %s' % (name, step, k, rc, tail), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--rev', required=True)
    ap.add_argument('--steps', default='')
    ap.add_argument('--keys', default='')
    a = ap.parse_args()
    import ports_h2
    steps = [s for s in a.steps.split(',') if s]
    keys = [k for k in a.keys.split(',') if k] or ports_h2.done_keys()
    busy = [k for k in keys if k not in ports_h2.done_keys()]
    if busy:
        raise SystemExit('not done (proofs cover DONE ports only): %s' % ', '.join(busy))
    t = a.tag
    logp = os.path.join(S.OUT, 'h2_proof_%s.log' % t)
    with kit_lock.held('h2_port_tool_proof %s' % t, owner='proof', kit='h2'), open(logp, 'w') as log:
        old = extract(a.rev, t)
        print('[%s] snap + backup pre' % t, flush=True)
        S.snap(t + '_pre')
        S.backup(t + '_pre')
        try:
            print('[%s] OLD tools (%s)' % (t, a.rev), flush=True)
            side('old', steps, keys, old, log)
            S.snap(t + '_old')
            S.restore(t + '_pre', t + '_old', t + '_pre', delete_new=True)
            print('[%s] NEW tools' % t, flush=True)
            side('new', steps, keys, HERE, log)
            S.snap(t + '_new')
        finally:
            S.snap(t + '_last')
            S.restore(t + '_pre', t + '_last', t + '_pre', delete_new=True)
            S.snap(t + '_end')
            shutil.rmtree(os.path.dirname(old), ignore_errors=True)
        print('\n=== OLD vs NEW (the tool change)')
        S.diff(t + '_old', t + '_new')
        print('\n=== PRE vs NEW (regenerated against what is shipped)')
        S.diff(t + '_pre', t + '_new')
        print('\n=== PRE vs END (the kit restored)')
        S.diff(t + '_pre', t + '_end')
        print('log: %s' % logp)


if __name__ == '__main__':
    main()
