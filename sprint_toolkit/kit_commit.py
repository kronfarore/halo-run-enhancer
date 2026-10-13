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
"""
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile


def git(*args, ok=(0,)):
    r = subprocess.run(['git'] + list(args), capture_output=True)
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
