r"""A by-path commit that cannot sweep in ANOTHER session's hunks (two port sessions in parallel,
H1_PORT_PLAN.md "Running two ports in parallel"). `git commit -- <paths>` commits the WHOLE
working copy of each path: twice in pair 1 a session committed the other's uncommitted edit with
its own (20200bf h1_pickable_weapons.py; 7e1babd weapon_ports_catalog.json, a whole-file
regeneration carrying the other port's new entry).

    python kit_commit.py show <paths>                          every hunk vs HEAD, with its id
    python kit_commit.py commit --mine <id> ... -m MSG -- <paths>

`show` prints each hunk (git diff -U0: the smallest hunks, so two sessions' edits a few lines
apart stay apart) under an id -- a hash of the file name and the changed lines, not the line
numbers, so it survives the other session's edits elsewhere in the file. A new (untracked) or
binary file is one hunk. `commit` REFUSES when a path holds a hunk not listed in --mine (it
prints them: the other session's, or forgotten) or a listed id is gone (the file changed since
`show`: show again); otherwise `git commit -F <msg> -- <paths>`. Refused: wait for the other
session's commit, or ask the user (rule 1) -- never list a hunk that is not yours.

SHARED JSON RECORDS (weapon_ports_catalog.json, ai_firing_profiles.json; 2026-10-13, after
pair 1: 7e1babd carried B7's entry, the enhancer's 'hands' vanished between write and commit).
Their writers -- make_port_catalog_h1_ports, ai_firing_profile, port_catalog_keys -- use:
    head_json(path)                  the file as committed (HEAD), {} when untracked
    report_foreign(label, head, cur, mine)
                                     prints every FOREIGN item (not this run's) whose working
                                     value differs from HEAD: another session's uncommitted edit,
                                     kept as read, never rewritten
    commit_json(path, apply, msg)    `--commit`: commits THIS run's change only -- apply() run on
                                     HEAD's JSON, serialized as the writers write it, committed
                                     through a temporary index (the working copy's foreign edits
                                     stay uncommitted). Called INSIDE the writer's kit-lock hold, so
                                     nothing can write the file between the write and the commit.
"""
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time


def git(*args, ok=(0,), cwd=None, env=None, data=None):
    r = subprocess.run(['git'] + list(args), capture_output=True, cwd=cwd, env=env, input=data)
    if r.returncode not in ok:
        raise SystemExit('git %s: %s' % (' '.join(args), r.stderr.decode('utf-8', 'replace').strip()))
    return r.stdout.decode('utf-8', 'replace')


def hunk_id(path, body):
    h = hashlib.sha1(path.replace('\\', '/').lower().encode())
    h.update('\n'.join(body).encode('utf-8', 'replace'))
    return h.hexdigest()[:10]


def hunks(path):
    """[(id, header, lines)] of `path` against HEAD; [] when unchanged."""
    if git('ls-files', '--others', '--exclude-standard', '--', path).strip():
        data = open(path, 'rb').read()
        return [(hunk_id(path, [hashlib.sha1(data).hexdigest()]), 'NEW FILE (untracked, %d bytes)'
                 % len(data), [])]
    out = git('diff', 'HEAD', '-U0', '--no-color', '--no-ext-diff', '--', path)
    if not out.strip():
        return []
    res, cur = [], None
    for line in out.splitlines():
        if line.startswith('@@'):
            cur = [line, []]
            res.append(cur)
        elif cur is not None and line[:1] in '+-\\' and not line.startswith(('+++', '---')):
            cur[1].append(line)
    if not res:                                   # binary, mode-only, deleted without text
        return [(hunk_id(path, [out]), out.strip().splitlines()[-1], [])]
    return [(hunk_id(path, body), head, body) for head, body in res]


def show(paths):
    ids = []
    for p in paths:
        hs = hunks(p)
        print('=== %s: %d hunk(s)' % (p, len(hs)))
        for i, head, body in hs:
            print('--- [%s] %s' % (i, head))
            for line in body:
                print('    ' + line)
            ids.append(i)
    return ids


def _repo(path):
    """(work tree top, path relative to it with forward slashes)."""
    path = os.path.abspath(path)
    top = git('rev-parse', '--show-toplevel', cwd=os.path.dirname(path)).strip()
    return top, os.path.relpath(path, os.path.normpath(top)).replace('\\', '/')


def _head_text(top, rel, rev='HEAD'):
    r = subprocess.run(['git', 'show', '%s:%s' % (rev, rel)], capture_output=True, cwd=top)
    return r.stdout.decode('utf-8').replace('\r\n', '\n') if r.returncode == 0 else None


def head_json(path, rev='HEAD'):
    """The JSON file as committed at `rev`; {} when it is not in the commit."""
    top, rel = _repo(path)
    text = _head_text(top, rel, rev)
    return json.loads(text) if text is not None else {}


def _items(data):
    """{(game, weapon): value} -- the catalog's lists keyed by 'weapon', the profiles' dicts."""
    out = {}
    for game, v in (data or {}).items():
        if isinstance(v, list):
            for i, e in enumerate(v):
                out[(game, e.get('weapon') if isinstance(e, dict) else i)] = e
        elif isinstance(v, dict):
            for k, e in v.items():
                out[(game, k)] = e
        else:
            out[(game,)] = v
    return out


def report_foreign(label, head, cur, mine):
    """Print every item that is NOT this run's and differs between HEAD and the working copy as
    read under the lock. `mine` = {(game, weapon): None (the whole item) | field names (only
    those fields are this run's; the item's other fields are compared)}. Returns the lines."""
    h, c = _items(head), _items(cur)
    lines = []
    for k in sorted(set(h) | set(c), key=lambda k: [str(x) for x in k]):
        hv, cv = h.get(k), c.get(k)
        if k in mine and mine[k] is None:
            continue
        if k in mine and isinstance(hv, dict) and isinstance(cv, dict):
            skip = set(mine[k])
            hv = {f: v for f, v in hv.items() if f not in skip}
            cv = {f: v for f, v in cv.items() if f not in skip}
        if hv == cv:
            continue
        if hv is None:
            what = 'ADDED (not in HEAD)'
        elif cv is None:
            what = 'REMOVED (in HEAD)'
        elif isinstance(hv, dict) and isinstance(cv, dict):
            diff = sorted(f for f in set(hv) | set(cv) if hv.get(f) != cv.get(f))
            what = 'changed: %s' % ', '.join(diff)
        else:
            what = 'changed'
        lines.append('FOREIGN %s %s: %s -- uncommitted, kept as read (not this run\'s)'
                     % (label, ' / '.join(str(x) for x in k), what))
    for line in lines:
        print(line)
    return lines


def commit_json(path, apply, message, tries=30):
    """Commit THIS run's change to a shared JSON record and nothing else: apply(data) mutates
    HEAD's JSON, which is serialized as the writers write it (json indent 1) and committed
    through a temporary index; the working copy's other uncommitted edits stay uncommitted.
    Call it INSIDE the kit-lock hold that wrote the file. Returns the new commit id, or None when
    the change is already in HEAD."""
    top, rel = _repo(path)
    if git('diff', '--cached', '--name-only', '--', rel, cwd=top).strip():
        raise SystemExit('%s is STAGED in the index: commit_json will not guess -- unstage it '
                         '(git reset -q -- %s) or commit it first' % (rel, rel))
    if isinstance(message, (list, tuple)):
        message = '\n\n'.join(message)
    for attempt in range(tries):
        head = git('rev-parse', 'HEAD', cwd=top).strip()
        text = _head_text(top, rel, head)
        data = json.loads(text) if text is not None else {}
        if text is not None and json.dumps(data, indent=1) != text:
            raise SystemExit('%s at HEAD is not in the writers\' format (json indent 1): '
                             'commit_json would rewrite more than this change' % rel)
        new = copy.deepcopy(data)
        apply(new)
        if text is not None and new == data:
            print('%s: this change is already in HEAD, nothing to commit' % rel)
            return None
        blob = git('hash-object', '-w', '--path', rel, '--stdin', cwd=top,
                   data=json.dumps(new, indent=1).encode('utf-8')).strip()
        fd, idx = tempfile.mkstemp(suffix='.index')
        os.close(fd)
        os.remove(idx)
        env = dict(os.environ, GIT_INDEX_FILE=idx)
        try:
            git('read-tree', head, cwd=top, env=env)
            git('update-index', '--add', '--cacheinfo', '100644,%s,%s' % (blob, rel), cwd=top, env=env)
            tree = git('write-tree', cwd=top, env=env).strip()
        finally:
            if os.path.exists(idx):
                os.remove(idx)
        commit = git('commit-tree', tree, '-p', head, '-F', '-', cwd=top,
                     data=(message.rstrip('\n') + '\n').encode('utf-8')).strip()
        # compare-and-swap: fails when the other session committed since rev-parse -> again
        r = subprocess.run(['git', 'update-ref', '-m', 'kit_commit: %s' % rel, 'HEAD', commit, head],
                           capture_output=True, cwd=top)
        if r.returncode == 0:
            break
        time.sleep(1)
    else:
        raise SystemExit('commit_json: HEAD kept moving (or update-ref failed: %s)'
                         % r.stderr.decode('utf-8', 'replace').strip())
    for attempt in range(tries):                 # the real index: this path's entry = new HEAD
        r = subprocess.run(['git', 'reset', '-q', '--', rel], capture_output=True, cwd=top)
        if r.returncode == 0:
            break
        time.sleep(1)                            # index.lock: the other session is committing
    else:
        print('WARNING: the index still holds the old %s -- run `git reset -q -- %s`' % (rel, rel))
    print('committed %s %s: this run\'s change only' % (commit[:7], rel))
    return commit


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('show')
    s.add_argument('paths', nargs='+')
    c = sub.add_parser('commit')
    c.add_argument('--mine', nargs='+', required=True, metavar='ID', help='the hunk ids that are yours')
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument('-m', action='append', dest='msg', help='message paragraph (repeatable, as git)')
    g.add_argument('-F', dest='msg_file', help='message file')
    c.add_argument('paths', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'show':
        ids = show(a.paths)
        print('\n%d hunk(s). Commit only YOURS: kit_commit.py commit --mine <ids> -m ... -- <paths>'
              % len(ids))
        return
    mine = set(a.mine)
    found, foreign = set(), []
    for p in a.paths:
        hs = hunks(p)
        if not hs:
            raise SystemExit('%s: no change against HEAD' % p)
        for i, head, body in hs:
            found.add(i)
            if i not in mine:
                foreign.append((p, i, head, body))
    stale = sorted(mine - found)
    for p, i, head, body in foreign:
        print('NOT LISTED %s [%s] %s' % (p, i, head))
        for line in body[:12]:
            print('    ' + line)
        if len(body) > 12:
            print('    ... %d more line(s)' % (len(body) - 12))
    if stale:
        print('GONE: %s (not in these paths now -- the file changed since `show`?)' % ' '.join(stale))
    if foreign or stale:
        raise SystemExit('REFUSED: %d hunk(s) not listed, %d listed id(s) gone. Another session\'s '
                         'uncommitted edit in a shared file: wait for its commit or ask the user '
                         '(H1_PORT_PLAN rule 1).' % (len(foreign), len(stale)))
    if a.msg_file:
        msg_file, tmp = a.msg_file, None
    else:
        fd, tmp = tempfile.mkstemp(suffix='.txt')
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n\n'.join(a.msg) + '\n')
        msg_file = tmp
    new = [p for p in a.paths if git('ls-files', '--others', '--exclude-standard', '--', p).strip()]
    if new:                                      # `git commit -- <new file>` needs it known first
        git('add', '--', *new)
    try:
        r = subprocess.run(['git', 'commit', '-F', msg_file, '--'] + a.paths)
    finally:
        if tmp:
            os.remove(tmp)
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
