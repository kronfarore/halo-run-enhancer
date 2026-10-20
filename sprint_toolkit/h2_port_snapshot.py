r"""Halo 2 port proofs: a SHA-1 snapshot of every H2EK file the port pipeline writes, before and
after, so a pipeline change is shown BYTE-IDENTICAL for the ports already built (H2_PORT_PLAN.md
0.2 / 0.6; the Halo 2 counterpart of port_sha_snapshot.py).

Files (H2EK): tags objects\weapons, objects\characters\*\fp\weapons, effects\objects\weapons,
ui\hud, sound\weapons, every campaign .scenario + weapons resource, h2_fonts; data
objects\weapons, ui\hud, sound\weapons and every data_*\ui\hud\hud_messages.txt; the tool's
weapon_ports_catalog.json and ai_firing_profiles.json.

DONE PORTS ONLY: the folders and files a port NOT 'done' owns (ports_h2.owned_dirs/owned_files)
are never hashed, backed up or restored -- a parallel session's port changes under the proof by
design. The size-test stand-ins (h2_size_test_map.py's manifest) are skipped too.

    python h2_port_snapshot.py snap <name>                 -> out\h2sha_<name>.json
    python h2_port_snapshot.py backup <name>               copy the snapshot's files to
                                                           E:\HaloBackups\h2_proof_<name>
    python h2_port_snapshot.py diff <a> <b>                added / removed / changed
    python h2_port_snapshot.py restore <a> <b> [<backup name>]   every file changed or removed
                                                           a -> b put back from a's backup; files
                                                           NEW in b are listed EXTRA (left, unless
                                                           --delete-new); then snap + diff again
KNOWN run-to-run noise (Halo 1's, to be confirmed for Halo 2 by its own proofs): `tool bitmaps`
may write a different header into a .bitmap whose pixels are identical -- `diff` lists bitmaps
apart (BITMAP) so they can be checked by export.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ports_h2  # noqa: E402

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
OUT = os.path.join(HERE, 'out')
BACKUPS = os.path.join('E:' + os.sep, 'HaloBackups')
STANDINS = os.path.join(OUT, 'h2_size_test.json')


def roots():
    t, d = os.path.join(H2EK, 'tags'), os.path.join(H2EK, 'data')
    out = [os.path.join(t, *p.split('\\')) for p in
           (r'objects\weapons', r'effects\objects\weapons', r'ui\hud', r'sound\weapons')]
    chars = os.path.join(t, 'objects', 'characters')
    out += [os.path.join(chars, c, 'fp', 'weapons') for c in sorted(os.listdir(chars))
            if os.path.isdir(os.path.join(chars, c, 'fp', 'weapons'))]
    out += [os.path.join(H2EK, 'h2_fonts')]
    out += [os.path.join(d, *p.split('\\')) for p in (r'objects\weapons', r'ui\hud', r'sound\weapons')]
    files = []
    for lvl in ports_h2.LEVELS:
        base = os.path.join(t, 'scenarios', 'solo', lvl)
        files += [os.path.join(base, lvl + '.scenario'),
                  os.path.join(base, 'resources', lvl + '.scenario_weapons_resource')]
    for dd in sorted(os.listdir(H2EK)):
        p = os.path.join(H2EK, dd, 'ui', 'hud', 'hud_messages.txt')
        if dd.startswith('data_') and os.path.exists(p):
            files.append(p)
    files += [os.path.join(TOOL, 'weapon_ports_catalog.json'), os.path.join(TOOL, 'ai_firing_profiles.json')]
    return out, files


def skipped():
    """(dir prefixes, files) never touched: ports not 'done' + the size-test stand-ins."""
    dirs, files = [], set()
    for _k, p in ports_h2.all_ports():
        if p.get('status') == 'done':
            continue
        for d in ports_h2.owned_dirs(p):
            for root in ('tags', 'data'):
                dirs.append(os.path.join(H2EK, root, d).lower() + os.sep)
        for f in ports_h2.owned_files(p):
            files.add(os.path.join(H2EK, 'tags', f).lower())
    if os.path.exists(STANDINS):
        for f in json.load(open(STANDINS))['files']:
            files.add(f.lower())
    return dirs, files


def files():
    dirs, roots_files = roots()
    sk_dirs, sk_files = skipped()
    for r in dirs:
        for d, _ds, fs in os.walk(r):
            dl = d.lower() + os.sep
            if any(dl.startswith(s) for s in sk_dirs):
                continue
            for f in fs:
                p = os.path.join(d, f)
                if p.lower() not in sk_files:
                    yield p
    for p in roots_files:
        if os.path.exists(p) and p.lower() not in sk_files:
            yield p


def sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def snap(name):
    got = {p: sha(p) for p in files()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(got, open(os.path.join(OUT, 'h2sha_%s.json' % name), 'w'), indent=0)
    print('snap %s: %d files' % (name, len(got)))
    return got


def load(name):
    return json.load(open(os.path.join(OUT, 'h2sha_%s.json' % name)))


def diff(a, b, quiet=False):
    A, Bs = load(a), load(b)
    added = sorted(set(Bs) - set(A))
    removed = sorted(set(A) - set(Bs))
    changed = sorted(p for p in set(A) & set(Bs) if A[p] != Bs[p])
    if not quiet:
        for tag, lst in (('ADDED', added), ('REMOVED', removed), ('CHANGED', changed)):
            for p in lst:
                kind = 'BITMAP ' if p.endswith('.bitmap') and tag == 'CHANGED' else ''
                print('%-8s %s%s' % (tag, kind, p))
        print('%s -> %s: %d added, %d removed, %d changed' % (a, b, len(added), len(removed), len(changed)))
    return added, removed, changed


def backup(name):
    dst = os.path.join(BACKUPS, 'h2_proof_%s' % name)
    n = 0
    for p in load(name):
        rel = os.path.relpath(p, os.path.splitdrive(p)[0] + os.sep)
        out = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(p, out)
        n += 1
    print('backed up %d files -> %s' % (n, dst))


def restore(a, b, name=None, delete_new=False):
    src = os.path.join(BACKUPS, 'h2_proof_%s' % (name or a))
    added, removed, changed = diff(a, b, quiet=True)
    n = 0
    for p in removed + changed:
        rel = os.path.relpath(p, os.path.splitdrive(p)[0] + os.sep)
        shutil.copy2(os.path.join(src, rel), p)
        n += 1
    for p in added:
        if delete_new:
            os.remove(p)
        print('%s %s' % ('DELETED' if delete_new else 'EXTRA  ', p))
    print('restored %d file(s) from %s' % (n, src))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=('snap', 'backup', 'diff', 'restore'))
    ap.add_argument('names', nargs='+')
    ap.add_argument('--delete-new', action='store_true')
    a = ap.parse_args()
    import kit_lock
    with kit_lock.held('h2_port_snapshot %s %s' % (a.verb, ' '.join(a.names)), owner='proof', kit='h2'):
        if a.verb == 'snap':
            snap(a.names[0])
        elif a.verb == 'backup':
            backup(a.names[0])
        elif a.verb == 'diff':
            diff(a.names[0], a.names[1])
        else:
            restore(a.names[0], a.names[1], a.names[2] if len(a.names) > 2 else None, a.delete_new)


if __name__ == '__main__':
    main()
