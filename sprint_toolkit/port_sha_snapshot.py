r"""Prove a pipeline change is BYTE-IDENTICAL for the ports already built: a SHA-1 snapshot of
every file the Halo 1 port pipeline's --write runs touch, before and after (phase 0's proof,
H1_PORT_PLAN "0.2"; made a tool for the DMR, the wave-B pilot, 2026-10-10).

Files: HCEEK tags weapons / sound / ui / characters / levels / effects, HCEEK data weapons /
sound, tool\port_sounds\halo1, weapon_ports_catalog.json, ai_firing_profiles.json.

    python port_sha_snapshot.py snap <name>               hash the set -> out\sha_<name>.json
    python port_sha_snapshot.py diff <a> <b>              files added / removed / changed
    python port_sha_snapshot.py restore <a> <b> <backup>  every file changed / removed a -> b back
                                                          from a backup taken at a (then snap +
                                                          diff); files new in b are LEFT (EXTRA)
    diff lists apart, without failing: NOWDONE (a port done since a: not in a), EXTRA (left by
    `restore a`), NOWBUSY (a port in progress at b: not in b) -- each snap records its
    in-progress folders in sha_<name>.meta.json
    python port_sha_snapshot.py regen [key ...]           the wave-A --write chain, per config:
        h1_h3_weapon_model <key> -> h1_fp_retarget <key> --write + tool animations <h1_dir>
        -> h1_port_sounds <key> --write -> h1_pickable_weapons --only <key> --write
        (default: every config with that section, Reach ports excluded -- the proof is about
        the ports that were built BEFORE the change)
        --steps model,retarget,sounds,pickable  only those steps (port_tool_proof's narrowed
        proof: the steps whose scripts use the changed tools)

IN A SCRATCH KIT ONLY (port_tool_proof --with-busy, 2026-10-13): `snap --busy` hashes the
in-progress ports' folders too and `regen --busy <keys>` regenerates those keys whatever their
status -- refused unless this copy's kit IS the scratch kit the proof made (environment
PORT_PROOF_SCRATCH), so the other session's port in the real kit is never written.

KNOWN run-to-run difference (phase 0): `tool bitmaps` writes a garbage `base_address` pointer
(and the header checksum) into .bitmap tags; the pixels are identical. `diff` lists those
apart as BITMAP when their PIXELS (processed_pixel_data, hashed at snap time) are equal.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
ROOTS = ([os.path.join(HCEEK, 'tags', d) for d in ('weapons', 'sound', 'ui', 'characters', 'levels', 'effects')]
         + [os.path.join(HCEEK, 'data', d) for d in ('weapons', 'sound')]
         + [os.path.join(TOOL, 'port_sounds', 'halo1'),
            os.path.join(TOOL, 'weapon_ports_catalog.json'),
            os.path.join(TOOL, 'ai_firing_profiles.json')])
OUT = os.path.join(HERE, 'out')
#: snapshot keys the regen never writes (the catalog / firing-profile writers are not in it)
OUTSIDE = {'weapon_ports_catalog.json', 'ai_firing_profiles.json'}


def in_progress():
    """Paths of the ports NOT 'done' (lower case): their tag / data folders and their bank files.
    Two port sessions may run in parallel (H1_PORT_PLAN.md): a proof never snapshots, regenerates
    or RESTORES the other session's port -- its files change under the proof, by design."""
    sys.path.insert(0, HERE)
    import ports_h1
    dirs, bank = [], set()
    for key, p in ports_h1.all_ports():
        if p.get('status') == 'done':
            continue
        r = p.get('reservations') or {}
        ds = {r.get('weapon_dir'), r.get('sound_dir'), (p.get('model') or {}).get('dir'),
              (p.get('retarget') or {}).get('h1_dir'), (p.get('sounds') or {}).get('dir')}
        w = (p.get('pickable') or {}).get('weapon')
        if w:
            ds.add(os.path.dirname(w))
        for d in filter(None, ds):
            for root in ('tags', 'data'):
                dirs.append(os.path.join(HCEEK, root, d).lower() + os.sep)
        man = os.path.join(TOOL, 'port_sounds', 'halo1', 'port_%s.json' % key)
        bank.add(man.lower())
        try:
            for snd in json.load(open(man, encoding='utf-8')).get('sounds', []):
                for f in snd.get('perms', []):
                    bank.add(os.path.join(TOOL, 'port_sounds', 'halo1', f).lower())
        except (OSError, ValueError):
            pass
    return dirs, bank


def files(busy=False):
    skip_dirs, skip_files = ([], set()) if busy else in_progress()
    for r in ROOTS:
        if os.path.isfile(r):
            yield r
            continue
        for d, _ds, fs in os.walk(r):
            dl = d.lower() + os.sep
            if any(dl.startswith(s) for s in skip_dirs):
                continue
            for f in fs:
                p = os.path.join(d, f)
                if p.lower() not in skip_files:
                    yield p


def sha(path):
    return hashlib.sha1(open(path, 'rb').read()).hexdigest()


def bitmap_pixels(path):
    """SHA-1 of a Halo 1 bitmap tag's PIXEL data only (the processed_pixel_data blob)."""
    sys.path.insert(0, HERE)
    import port_env  # noqa: F401
    from reclaimer.hek.defs.bitm import bitm_def
    t = bitm_def.build(filepath=path)
    return hashlib.sha1(bytes(t.data.tagdata.processed_pixel_data.data)).hexdigest()


SCRATCH_ENV = 'PORT_PROOF_SCRATCH'


def scratch_only(what):
    """--busy runs only in the scratch kit port_tool_proof --with-busy made (never the real kit)."""
    want = os.environ.get(SCRATCH_ENV)
    if not want or os.path.normcase(os.path.abspath(want)) != os.path.normcase(os.path.abspath(HCEEK)):
        raise SystemExit('%s --busy: only in a port_tool_proof scratch kit (this kit is %s, %s=%s)'
                         % (what, HCEEK, SCRATCH_ENV, want))


def snap(name, busy=False):
    if busy:
        scratch_only('snap')
    out = {}
    for p in files(busy):
        k = os.path.relpath(p, os.path.dirname(HCEEK) if p.startswith(HCEEK) else TOOL)
        out[k] = sha(p)
        if k.lower().endswith('.bitmap'):            # the pixels alone (see the docstring)
            try:
                out['px:' + k] = bitmap_pixels(p)
            except Exception as e:                   # noqa: BLE001 -- recorded, not fatal
                out['px:' + k] = 'unreadable: %s' % e
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'sha_%s.json' % name)
    json.dump(out, open(path, 'w'), indent=0, sort_keys=True)
    # the folders left out as in progress AT THIS SNAP: diff tells a port that turned done
    # since (its folders ADDED) from a real addition
    json.dump({'in_progress': [] if busy else in_progress()[0]}, open(meta_path(name), 'w'), indent=0)
    if os.path.exists(extras_path(name)):            # a new snap: an older restore's record is stale
        os.remove(extras_path(name))
    print('%d files -> %s' % (len(out), path))


def meta_path(name):
    return os.path.join(OUT, 'sha_%s.meta.json' % name)


def busy_at(name):
    """The in-progress folders recorded with snap `name` ([] for a snap older than the record)."""
    try:
        return json.load(open(meta_path(name))).get('in_progress', [])
    except (OSError, ValueError):
        return []


def extras_path(name):
    """The files `restore <name> ...` found added and LEFT in place (not the regen's to delete)."""
    return os.path.join(OUT, 'sha_%s.extras.json' % name)


def rel_lower(k):
    """A snapshot key as a lower-case absolute path (the form in_progress() lists)."""
    return (os.path.join(os.path.dirname(HCEEK), k) if k.startswith('HCEEK') else os.path.join(TOOL, k)).lower()


def diff(a, b):
    A = json.load(open(os.path.join(OUT, 'sha_%s.json' % a)))
    B = json.load(open(os.path.join(OUT, 'sha_%s.json' % b)))
    keys = lambda D: {k for k in D if not k.startswith('px:')}
    added = sorted(keys(B) - keys(A))
    removed = sorted(keys(A) - keys(B))
    changed = sorted(k for k in keys(A) & keys(B) if A[k] != B[k])
    bitm = [k for k in changed if k.lower().endswith('.bitmap')
            and A.get('px:' + k) == B.get('px:' + k) and 'unreadable' not in str(A.get('px:' + k))]
    other = [k for k in changed if k not in bitm]
    # ADDED, not a failure: under a port in progress at snap a (it turned done since: fo3, 196 of
    # the Concussion Rifle's), or left in place by `restore a ...` (another session's file)
    was_busy, now_busy = busy_at(a), busy_at(b)
    # REMOVED, not a failure: under a port in progress at snap b (set to 'rework' since)
    busy = [k for k in removed if any(rel_lower(k).startswith(d) for d in now_busy)]
    removed = [k for k in removed if k not in busy]
    for k in busy:
        print('NOWBUSY ', k, '(its port is in progress at %s: not in that snapshot)' % b)
    try:
        left = set(json.load(open(extras_path(a))))
    except (OSError, ValueError):
        left = set()
    now_done = [k for k in added if any(rel_lower(k).startswith(d) for d in was_busy)]
    extra = [k for k in added if k in left and k not in now_done]
    added = [k for k in added if k not in now_done and k not in extra]
    for k in now_done:
        print('NOWDONE ', k, '(its port was in progress at %s: not in that snapshot)' % a)
    for k in extra:
        print('EXTRA   ', k, '(not in %s: left in place by the restore, not the regen\'s)' % a)
    for k in added:
        print('ADDED   ', k)
    for k in removed:
        print('REMOVED ', k)
    for k in other:
        print('CHANGED ', k)
    for k in bitm:
        print('BITMAP  ', k, '(header only: pixels identical)')
    print('%d files compared: %d added, %d removed, %d changed (+%d bitmap tags, pixels identical; '
          '+%d of ports done since, +%d extras left by the restore, -%d of ports in progress since)'
          % (len(keys(A) | keys(B)), len(added), len(removed), len(other), len(bitm),
             len(now_done), len(extra), len(busy)))
    return not (added or removed or other)


def restore(a, b, backup):
    """Put back every file that differs between snapshots a (the state to return to) and b
    (now), from `backup` -- a copy of ROOTS taken with snapshot a: <backup>\\tags\\<d>,
    <backup>\\data\\<d>, <backup>\\tool\\halo1, <backup>\\tool\\<json> (the layout the DMR pilot's
    backups used). Files only in b are NOT deleted: they are reported (EXTRA) and recorded
    (extras_path(a)), so the restore check lists them apart -- the regen rewrites existing files,
    a new file is another session's (fo-proof, 2026-10-13: the delete took the B7 session's test
    copy under weapons\\spartan laser\\test). A regen run must be followed by this: the wave-A
    chain re-writes 12 tested files as content-equal tag noise (H1_PORT_PLAN "B1")."""
    A = json.load(open(os.path.join(OUT, 'sha_%s.json' % a)))
    B_ = json.load(open(os.path.join(OUT, 'sha_%s.json' % b)))
    keys = lambda D: {k for k in D if not k.startswith('px:')}  # noqa: E731

    def real(k):
        return os.path.join(os.path.dirname(HCEEK), k) if k.startswith('HCEEK') else os.path.join(TOOL, k)

    def back(k):
        p = k.split(os.sep)
        if k.startswith('HCEEK'):
            return os.path.join(backup, p[1], *p[2:])
        if k.startswith('port_sounds'):
            return os.path.join(backup, 'tool', *p[1:])
        return os.path.join(backup, 'tool', k)
    was_busy, now_busy = busy_at(a), busy_at(b)
    n, extras = 0, []
    for k in sorted(keys(A) | keys(B_)):
        if A.get(k) == B_.get(k):
            continue
        if k in OUTSIDE:
            # the regen chain never writes these: a change is ANOTHER SESSION's (rp4, 2026-10-12:
            # the restore wiped the enhancer's catalog commit made while the proof ran)
            print('LEFT    %s (changed by another writer during the proof, not by the regen)' % k)
            continue
        if k not in B_ and any(rel_lower(k).startswith(d) for d in now_busy):
            # its port went to 'rework' during the proof: another session's files now
            print('LEFT    %s (its port is in progress at %s)' % (k, b))
            continue
        if k not in A:
            done_since = any(rel_lower(k).startswith(d) for d in was_busy)
            print('EXTRA   %s (not in %s: left in place%s)'
                  % (k, a, '; its port turned done since' if done_since else ''))
            extras.append(k)
            continue
        shutil.copy2(back(k), real(k))
        n += 1
    json.dump(extras, open(extras_path(a), 'w'), indent=0)
    print('%d file(s) restored from %s, %d extra(s) left -- snap again and diff against %s to prove it'
          % (n, backup, len(extras), a))


def run(*cmd):
    print('>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, errors='replace')
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit('failed: %s' % ' '.join(cmd))
    return r.stdout


#: the chain, in order; each step's script ('retarget' also runs tool animations)
STEPS = ('model', 'retarget', 'sounds', 'pickable')


def regen(keys, steps=STEPS, busy=False):
    sys.path.insert(0, HERE)
    import ports_h1
    secs = {s: ports_h1.section(s) for s in ('model', 'retarget', 'sounds', 'pickable')}
    allk = sorted(set().union(*secs.values()))
    src = {k: getattr(__import__('ports_h1.' + k, fromlist=['PORT']), 'PORT').get('source') for k in allk}
    keys = keys or [k for k in allk if src[k] != 'Halo Reach']
    # never another session's port in progress (H1_PORT_PLAN.md, parallel ports)
    done = {k for k, p in ports_h1.all_ports() if p.get('status') == 'done'}
    if busy:                                     # the scratch kit: the named keys, any status
        scratch_only('regen')
        if not keys:
            raise SystemExit('regen --busy: name the keys')
        done = set(keys)
    skipped = [k for k in keys if k not in done]
    if skipped:
        print('regen: skipping port(s) not done (another session may be on them): %s'
              % ', '.join(skipped))
    keys = [k for k in keys if k in done]
    py = sys.executable
    for k in keys:
        if k in secs['model'] and 'model' in steps:
            run(py, 'h1_h3_weapon_model.py', k)
        if k in secs['retarget'] and 'retarget' in steps:
            run(py, 'h1_fp_retarget.py', k, '--write')
            r = subprocess.run([os.path.join(HCEEK, 'tool.exe'), 'animations',
                                secs['retarget'][k]['h1_dir']], cwd=HCEEK,
                               capture_output=True, text=True, errors='replace')
            print('  tool animations %s: %s' % (secs['retarget'][k]['h1_dir'],
                                                (r.stdout + r.stderr).strip().splitlines()[-1:]))
        if k in secs['sounds'] and 'sounds' in steps:
            run(py, 'h1_port_sounds.py', k, '--write')
        if k in secs['pickable'] and 'pickable' in steps:
            run(py, 'h1_pickable_weapons.py', '--only', k, '--write')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('snap', 'diff', 'regen', 'restore'))
    ap.add_argument('args', nargs='*')
    ap.add_argument('--steps', help='regen: comma-separated subset of ' + ','.join(STEPS))
    ap.add_argument('--busy', action='store_true', help='snap / regen in a port_tool_proof '
                    'scratch kit: in-progress ports included (refused in the real kit)')
    a = ap.parse_args()
    if a.cmd == 'snap':
        snap(a.args[0], a.busy)
    elif a.cmd == 'diff':
        sys.exit(0 if diff(a.args[0], a.args[1]) else 1)
    elif a.cmd == 'restore':
        restore(a.args[0], a.args[1], a.args[2])
    else:
        steps = tuple(a.steps.split(',')) if a.steps else STEPS
        bad = set(steps) - set(STEPS)
        if bad:
            raise SystemExit('unknown step(s): %s' % ', '.join(sorted(bad)))
        regen(a.args, steps, a.busy)


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('port_sha_snapshot'):
        main()
