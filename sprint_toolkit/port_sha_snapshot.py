r"""Prove a pipeline change is BYTE-IDENTICAL for the ports already built: a SHA-1 snapshot of
every file the Halo 1 port pipeline's --write runs touch, before and after (phase 0's proof,
H1_PORT_PLAN "0.2"; made a tool for the DMR, the wave-B pilot, 2026-10-10).

Files: HCEEK tags weapons / sound / ui / characters / levels / effects, HCEEK data weapons /
sound, tool\port_sounds\halo1, weapon_ports_catalog.json, ai_firing_profiles.json.

    python port_sha_snapshot.py snap <name>               hash the set -> out\sha_<name>.json
    python port_sha_snapshot.py diff <a> <b>              files added / removed / changed
    python port_sha_snapshot.py restore <a> <b> <backup>  every file differing a -> b back from
                                                          a backup taken at a (then snap + diff)
    python port_sha_snapshot.py regen [key ...]           the wave-A --write chain, per config:
        h1_h3_weapon_model <key> -> h1_fp_retarget <key> --write + tool animations <h1_dir>
        -> h1_port_sounds <key> --write -> h1_pickable_weapons --only <key> --write
        (default: every config with that section, Reach ports excluded -- the proof is about
        the ports that were built BEFORE the change)

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


def files():
    for r in ROOTS:
        if os.path.isfile(r):
            yield r
            continue
        for d, _ds, fs in os.walk(r):
            for f in fs:
                yield os.path.join(d, f)


def sha(path):
    return hashlib.sha1(open(path, 'rb').read()).hexdigest()


def bitmap_pixels(path):
    """SHA-1 of a Halo 1 bitmap tag's PIXEL data only (the processed_pixel_data blob)."""
    sys.path.insert(0, HERE)
    import port_env  # noqa: F401
    from reclaimer.hek.defs.bitm import bitm_def
    t = bitm_def.build(filepath=path)
    return hashlib.sha1(bytes(t.data.tagdata.processed_pixel_data.data)).hexdigest()


def snap(name):
    out = {}
    for p in files():
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
    print('%d files -> %s' % (len(out), path))


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
    for k in added:
        print('ADDED   ', k)
    for k in removed:
        print('REMOVED ', k)
    for k in other:
        print('CHANGED ', k)
    for k in bitm:
        print('BITMAP  ', k, '(header only: pixels identical)')
    print('%d files compared: %d added, %d removed, %d changed (+%d bitmap tags, pixels identical)'
          % (len(keys(A) | keys(B)), len(added), len(removed), len(other), len(bitm)))
    return not (added or removed or other)


def restore(a, b, backup):
    """Put back every file that differs between snapshots a (the state to return to) and b
    (now), from `backup` -- a copy of ROOTS taken with snapshot a: <backup>\\tags\\<d>,
    <backup>\\data\\<d>, <backup>\\tool\\halo1, <backup>\\tool\\<json> (the layout the DMR pilot's
    backups used). Files only in b are deleted. A regen run must be followed by this: the
    wave-A chain re-writes 12 tested files as content-equal tag noise (H1_PORT_PLAN "B1")."""
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
    n = 0
    for k in sorted(keys(A) | keys(B_)):
        if A.get(k) == B_.get(k):
            continue
        if k not in A:
            os.remove(real(k))
        else:
            shutil.copy2(back(k), real(k))
        n += 1
    print('%d file(s) restored from %s -- snap again and diff against %s to prove it' % (n, backup, a))


def run(*cmd):
    print('>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, errors='replace')
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit('failed: %s' % ' '.join(cmd))
    return r.stdout


def regen(keys):
    sys.path.insert(0, HERE)
    import ports_h1
    secs = {s: ports_h1.section(s) for s in ('model', 'retarget', 'sounds', 'pickable')}
    allk = sorted(set().union(*secs.values()))
    src = {k: getattr(__import__('ports_h1.' + k, fromlist=['PORT']), 'PORT').get('source') for k in allk}
    keys = keys or [k for k in allk if src[k] != 'Halo Reach']
    py = sys.executable
    for k in keys:
        if k in secs['model']:
            run(py, 'h1_h3_weapon_model.py', k)
        if k in secs['retarget']:
            run(py, 'h1_fp_retarget.py', k, '--write')
            r = subprocess.run([os.path.join(HCEEK, 'tool.exe'), 'animations',
                                secs['retarget'][k]['h1_dir']], cwd=HCEEK,
                               capture_output=True, text=True, errors='replace')
            print('  tool animations %s: %s' % (secs['retarget'][k]['h1_dir'],
                                                (r.stdout + r.stderr).strip().splitlines()[-1:]))
        if k in secs['sounds']:
            run(py, 'h1_port_sounds.py', k, '--write')
        if k in secs['pickable']:
            run(py, 'h1_pickable_weapons.py', '--only', k, '--write')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('snap', 'diff', 'regen', 'restore'))
    ap.add_argument('args', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'snap':
        snap(a.args[0])
    elif a.cmd == 'diff':
        sys.exit(0 if diff(a.args[0], a.args[1]) else 1)
    elif a.cmd == 'restore':
        restore(a.args[0], a.args[1], a.args[2])
    else:
        regen(a.args)


if __name__ == '__main__':
    main()
